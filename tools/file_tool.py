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
        with open(full_path, 'r', encoding='utf-8') as f:
            contents = f.read()
        return f"File contents of '{path}':\n\n{contents}"
    except FileNotFoundError:
        return f"Error: File '{path}' not found."
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
        items = os.listdir(full_path)
        dirs = [f"📁 {item}/" for item in items if os.path.isdir(os.path.join(full_path, item))]
        files = [f"📄 {item}" for item in items if os.path.isfile(os.path.join(full_path, item))]
        dirs.sort()
        files.sort()
        result = f"Contents of '{path}':\n\n"
        result += "\n".join(dirs + files)
        return result
    except FileNotFoundError:
        return f"Error: Directory '{path}' not found."
    except Exception as e:
        return f"Error listing directory: {str(e)}"
