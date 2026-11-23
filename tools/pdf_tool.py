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
        if len(text) > 30000:
            text = text[:30000] + "\n… (document truncated here)"
        return f"Contents of '{path}':\n\n{text}"
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
