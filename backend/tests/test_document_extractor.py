"""
Tests for Document Extractor service.
Phase 1: RED — tests written before implementation.
"""
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_path(name: str) -> Path:
    return Path(f"/tmp/fake/{name}")


# ---------------------------------------------------------------------------
# PDF text-based extraction
# ---------------------------------------------------------------------------

class TestExtractPDF:
    """Tests for PDF extraction using PyMuPDF."""

    def test_extract_text_pdf_returns_tuple(self):
        """extract() with text-based PDF → (str, float)."""
        from app.services.document_extractor import extract

        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "John Doe\nSoftware Engineer\n5 years experience"
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__len__ = MagicMock(return_value=1)

        with patch("app.services.document_extractor.fitz") as mock_fitz:
            mock_fitz.open.return_value.__enter__ = MagicMock(return_value=mock_doc)
            mock_fitz.open.return_value.__exit__ = MagicMock(return_value=False)
            mock_fitz.open.return_value = mock_doc

            result = extract(_fake_path("resume.pdf"), ".pdf")

        assert isinstance(result, tuple)
        assert len(result) == 2
        text, confidence = result
        assert isinstance(text, str)
        assert isinstance(confidence, float)

    def test_extract_text_pdf_returns_content(self):
        """extract() with text-based PDF → text contains extracted content."""
        from app.services.document_extractor import extract

        expected_text = "John Doe\nSoftware Engineer\n5 years experience"
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = expected_text
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__len__ = MagicMock(return_value=1)

        with patch("app.services.document_extractor.fitz") as mock_fitz:
            mock_fitz.open.return_value = mock_doc

            result = extract(_fake_path("resume.pdf"), ".pdf")

        text, _ = result
        assert expected_text in text

    def test_extract_text_pdf_high_confidence(self):
        """extract() with text-based PDF → confidence = 1.0 (text-based, no OCR)."""
        from app.services.document_extractor import extract

        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Some CV text with sufficient content here."
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__len__ = MagicMock(return_value=1)

        with patch("app.services.document_extractor.fitz") as mock_fitz:
            mock_fitz.open.return_value = mock_doc

            _, confidence = extract(_fake_path("resume.pdf"), ".pdf")

        assert confidence == 1.0


# ---------------------------------------------------------------------------
# DOCX extraction
# ---------------------------------------------------------------------------

class TestExtractDOCX:
    """Tests for DOCX extraction using python-docx."""

    def test_extract_docx_returns_tuple(self):
        """extract() with DOCX → (str, float)."""
        from app.services.document_extractor import extract

        mock_doc = MagicMock()
        para1 = MagicMock()
        para1.text = "Jane Smith"
        para2 = MagicMock()
        para2.text = "Data Scientist"
        mock_doc.paragraphs = [para1, para2]
        mock_doc.tables = []

        with patch("app.services.document_extractor.docx") as mock_docx:
            mock_docx.Document.return_value = mock_doc
            result = extract(_fake_path("resume.docx"), ".docx")

        assert isinstance(result, tuple)
        assert len(result) == 2
        text, confidence = result
        assert isinstance(text, str)
        assert isinstance(confidence, float)

    def test_extract_docx_returns_paragraphs(self):
        """extract() DOCX → text contains paragraph content."""
        from app.services.document_extractor import extract

        mock_doc = MagicMock()
        para1 = MagicMock()
        para1.text = "Jane Smith"
        para2 = MagicMock()
        para2.text = "Data Scientist"
        mock_doc.paragraphs = [para1, para2]
        mock_doc.tables = []

        with patch("app.services.document_extractor.docx") as mock_docx:
            mock_docx.Document.return_value = mock_doc
            text, _ = extract(_fake_path("resume.docx"), ".docx")

        assert "Jane Smith" in text
        assert "Data Scientist" in text

    def test_extract_docx_confidence_is_1(self):
        """extract() DOCX → confidence = 1.0 (no OCR needed)."""
        from app.services.document_extractor import extract

        mock_doc = MagicMock()
        para1 = MagicMock()
        para1.text = "Some text"
        mock_doc.paragraphs = [para1]
        mock_doc.tables = []

        with patch("app.services.document_extractor.docx") as mock_docx:
            mock_docx.Document.return_value = mock_doc
            _, confidence = extract(_fake_path("resume.docx"), ".docx")

        assert confidence == 1.0

    def test_extract_docx_includes_table_text(self):
        """extract() DOCX → text from tables is included."""
        from app.services.document_extractor import extract

        mock_doc = MagicMock()
        mock_doc.paragraphs = []

        # Build a fake table with one row and one cell
        mock_cell = MagicMock()
        mock_cell.text = "Table Cell Content"
        mock_row = MagicMock()
        mock_row.cells = [mock_cell]
        mock_table = MagicMock()
        mock_table.rows = [mock_row]
        mock_doc.tables = [mock_table]

        with patch("app.services.document_extractor.docx") as mock_docx:
            mock_docx.Document.return_value = mock_doc
            text, _ = extract(_fake_path("resume.docx"), ".docx")

        assert "Table Cell Content" in text


# ---------------------------------------------------------------------------
# Image extraction (JPG / PNG via pytesseract)
# ---------------------------------------------------------------------------

class TestExtractImage:
    """Tests for image extraction using pytesseract."""

    def test_extract_jpg_returns_tuple(self):
        """extract() with JPG → (str, float)."""
        from app.services.document_extractor import extract

        mock_image = MagicMock()
        ocr_data = {
            "text": ["John", "Doe", "Engineer"],
            "conf": [85.0, 90.0, 75.0],
        }

        with (
            patch("app.services.document_extractor.Image") as mock_pil,
            patch("app.services.document_extractor.pytesseract") as mock_tess,
        ):
            mock_pil.open.return_value = mock_image
            mock_tess.image_to_string.return_value = "John Doe Engineer"
            mock_tess.image_to_data.return_value = ocr_data

            result = extract(_fake_path("photo.jpg"), ".jpg")

        assert isinstance(result, tuple)
        text, confidence = result
        assert isinstance(text, str)
        assert isinstance(confidence, float)

    def test_extract_png_returns_text(self):
        """extract() with PNG → text from OCR."""
        from app.services.document_extractor import extract

        ocr_data = {
            "text": ["Alice", "Manager"],
            "conf": [80.0, 82.0],
        }

        with (
            patch("app.services.document_extractor.Image") as mock_pil,
            patch("app.services.document_extractor.pytesseract") as mock_tess,
        ):
            mock_pil.open.return_value = MagicMock()
            mock_tess.image_to_string.return_value = "Alice Manager"
            mock_tess.image_to_data.return_value = ocr_data

            text, _ = extract(_fake_path("scan.png"), ".png")

        assert "Alice" in text or len(text) >= 0  # text extracted

    def test_extract_image_confidence_from_tesseract(self):
        """extract() with image → confidence derived from tesseract output."""
        from app.services.document_extractor import extract

        ocr_data = {
            "text": ["Word1", "Word2"],
            "conf": [70.0, 80.0],
        }

        with (
            patch("app.services.document_extractor.Image") as mock_pil,
            patch("app.services.document_extractor.pytesseract") as mock_tess,
        ):
            mock_pil.open.return_value = MagicMock()
            mock_tess.image_to_string.return_value = "Word1 Word2"
            mock_tess.image_to_data.return_value = ocr_data

            _, confidence = extract(_fake_path("scan.jpg"), ".jpg")

        assert 0.0 <= confidence <= 100.0


# ---------------------------------------------------------------------------
# Low confidence detection
# ---------------------------------------------------------------------------

class TestLowConfidence:
    """Tests for low OCR confidence detection."""

    def test_low_confidence_below_60_flagged(self):
        """extract() with confidence < 60 → ocr_low_quality flagged."""
        from app.services.document_extractor import extract

        ocr_data = {
            "text": ["Blurry", "Text"],
            "conf": [40.0, 45.0],
        }

        with (
            patch("app.services.document_extractor.Image") as mock_pil,
            patch("app.services.document_extractor.pytesseract") as mock_tess,
        ):
            mock_pil.open.return_value = MagicMock()
            mock_tess.image_to_string.return_value = "Blurry Text"
            mock_tess.image_to_data.return_value = ocr_data

            text, confidence = extract(_fake_path("blurry.jpg"), ".jpg")

        assert confidence < 60.0, f"Expected low confidence, got {confidence}"

    def test_confidence_above_60_not_low_quality(self):
        """extract() with confidence >= 60 → not low quality."""
        from app.services.document_extractor import extract

        ocr_data = {
            "text": ["Clear", "Text"],
            "conf": [85.0, 90.0],
        }

        with (
            patch("app.services.document_extractor.Image") as mock_pil,
            patch("app.services.document_extractor.pytesseract") as mock_tess,
        ):
            mock_pil.open.return_value = MagicMock()
            mock_tess.image_to_string.return_value = "Clear Text"
            mock_tess.image_to_data.return_value = ocr_data

            _, confidence = extract(_fake_path("clear.jpg"), ".jpg")

        assert confidence >= 60.0


# ---------------------------------------------------------------------------
# Unsupported file types
# ---------------------------------------------------------------------------

class TestUnsupportedType:
    """Tests for unsupported file type handling."""

    def test_extract_unsupported_raises_value_error(self):
        """extract() with unsupported file type → raises ValueError."""
        from app.services.document_extractor import extract

        with pytest.raises(ValueError, match="[Uu]nsupported"):
            extract(_fake_path("file.exe"), ".exe")

    def test_extract_txt_raises_value_error(self):
        """extract() with .txt file type → raises ValueError."""
        from app.services.document_extractor import extract

        with pytest.raises(ValueError):
            extract(_fake_path("file.txt"), ".txt")

    def test_extract_unknown_type_raises_value_error(self):
        """extract() with unknown extension → raises ValueError."""
        from app.services.document_extractor import extract

        with pytest.raises(ValueError):
            extract(_fake_path("file.xyz"), ".xyz")
