import os

def read_file(path: str) -> str:
    """
    Reads a file from the local filesystem and returns its contents.

    Args:
        path: The path to the file to read

    Returns:
        The contents of the file as a string, or an error message
    """
    try:
        full_path = os.path.expanduser(path)
        if os.path.isdir(full_path):
            # Models reach for read_file when they mean "look at this
            # place" — listing the folder keeps the search moving
            # instead of dead-ending on an "is a directory" error.
            return list_directory(path)
        if full_path.lower().endswith('.pdf'):
            # PDFs are binary — hand off to the PDF extractor instead of
            # failing with a UTF-8 decode error.
            try:
                from tools.pdf_tool import read_pdf
            except ImportError:
                from pdf_tool import read_pdf
            return read_pdf(path)
        with open(full_path, 'r', encoding='utf-8') as f:
            contents = f.read()
        return f"File contents of '{path}':\n\n{contents}"
    except FileNotFoundError:
        return (f"Error: File '{path}' not found. Check the spelling, or list "
                f"the folder it should be in to see the files that are "
                f"actually there — do not give up after one miss.")
    except PermissionError:
        return f"Error: Permission denied reading '{path}'."
    except Exception as e:
        return f"Error reading file: {str(e)}"


def list_directory(path: str = ".") -> str:
    """
    Lists all files and folders in a directory.

    Args:
        path: The directory path to list (defaults to current directory)

    Returns:
        A formatted list of files and directories
    """
    try:
        full_path = os.path.expanduser(path)
        if os.path.isfile(full_path):
            # Mirror of the read_file forgiveness: asked to list a
            # file, return its contents.
            return read_file(path)
        items = os.listdir(full_path)
        dirs = [f"📁 {item}/" for item in items if os.path.isdir(os.path.join(full_path, item))]
        files = [f"📄 {item}" for item in items if os.path.isfile(os.path.join(full_path, item))]
        dirs.sort()
        files.sort()
        result = f"Contents of '{path}':\n\n"
        result += "\n".join(dirs + files)
        return result
    except FileNotFoundError:
        # Ground truth beats guessing: say which of the standard folders
        # DO exist and what the home folder holds, so the next step is
        # obvious instead of another blind try.
        home = os.path.expanduser("~")
        existing = [name for name in ("Desktop", "Downloads", "Documents")
                    if os.path.isdir(os.path.join(home, name))]
        try:
            home_items = sorted(os.listdir(home))
            home_items = [i for i in home_items if not i.startswith(".")]
        except Exception:
            home_items = []
        detail = ""
        if existing:
            detail += (" Folders that do exist: "
                       + ", ".join(f"~/{name}" for name in existing) + ".")
        if home_items:
            detail += (" The home folder ~ contains: "
                       + ", ".join(home_items[:20]) + ".")
        return (f"Error: Directory '{path}' not found. It may simply not "
                f"exist on this computer — try another folder before "
                f"giving up.{detail}")
    except Exception as e:
        return f"Error listing directory: {str(e)}"
