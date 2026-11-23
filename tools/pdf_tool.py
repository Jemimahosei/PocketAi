import os

from pypdf import PdfReader


def read_pdf(path: str) -> str:
    """Read text content from a PDF file."""
    try:
        full_path = os.path.expanduser(path)
        reader = PdfReader(full_path)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        if not text.strip():
            return f"Error: No readable text found in '{path}' (may be scanned/image-only)."
        if len(text) > 30000:
            text = text[:30000] + "\n… (document truncated here)"
        return f"Contents of '{path}':\n\n{text}"
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
