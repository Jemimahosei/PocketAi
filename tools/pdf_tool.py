import fitz  # pymupdf
import os

def read_pdf(path: str) -> str:
    """Read text content from a PDF or DOCX file."""
    try:
        full_path = os.path.expanduser(path)
        doc = fitz.open(full_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        if not text.strip():
            return f"Error: No readable text found in '{path}' (may be scanned/image-only)."
        return f"Contents of '{path}':\n\n{text[:8000]}"
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
