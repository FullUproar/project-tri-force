from io import BytesIO

from pypdf import PdfReader

from app.core.logging import logger


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text content from a PDF file.

    Args:
        file_bytes: Raw PDF file bytes.

    Returns:
        Concatenated text from all pages.
    """
    reader = PdfReader(BytesIO(file_bytes))
    pages_text = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages_text.append(text)

    full_text = "\n\n".join(pages_text)
    logger.info("Extracted text from PDF: %d pages, %d characters", len(reader.pages), len(full_text))
    return full_text
