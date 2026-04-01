import io

import pytest

from app.services.pdf_parser import extract_text_from_pdf


class TestExtractTextFromPdf:
    def test_empty_bytes_raises(self):
        with pytest.raises(Exception):
            extract_text_from_pdf(b"")

    def test_invalid_pdf_raises(self):
        with pytest.raises(Exception):
            extract_text_from_pdf(b"this is not a pdf")
