import pdfplumber
import re
from docx import Document
from pathlib import Path


def extract_text(file_path: str) -> str:
    """
    Entry point. Routes to PDF or DOCX extractor based on file extension.
    Returns a single cleaned string of the full contract text.
    """
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return _extract_from_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        return _extract_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Only PDF and DOCX are supported.")


def _extract_from_pdf(file_path: str) -> str:
    """
    Extract text from each page using pdfplumber.
    Labels each page so Claude can later reference page numbers in its evidence quotes.
    """
    pages = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages.append(f"[Page {page_num}]\n{text.strip()}")

    if not pages:
        raise ValueError(
            "No text extracted. The PDF may be scanned or image-based. "
            "OCR support is not included in the prototype."
        )

    return "\n\n".join(pages)


def _extract_from_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file paragraph by paragraph.
    Preserves structure without pulling in XML noise.
    """
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    if not paragraphs:
        raise ValueError("No text could be extracted from the DOCX file.")

    return "\n\n".join(paragraphs)


def clean_text(text: str) -> str:
    """
    Clean raw extracted text before chunking.
    - Collapses excessive blank lines
    - Strips standalone page numbers and junk lines
    """
    # Collapse 3+ blank lines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        # Skip pure page-number lines like "- 4 -" or "4"
        if re.match(r'^-?\s*\d+\s*-?$', stripped):
            continue
        # Skip lines that are only symbols or whitespace
        if stripped and not re.match(r'^[\s\W]+$', stripped):
            lines.append(line)

    return '\n'.join(lines)