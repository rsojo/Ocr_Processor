from pathlib import Path

import fitz
import pytest

from ocr_processor.domain.exceptions import OCRProcessingError
from ocr_processor.infrastructure.ocr.searchable_pdf_engine import (
    TesseractSearchablePdfEngine,
)


def _make_pdf(tmp_path: Path, page_texts: list[str]) -> Path:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    path = tmp_path / "input.pdf"
    doc.save(path)
    doc.close()
    return path


def _fake_page_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture()
def fake_render(mocker):
    """Stand in for PyMuPDF rasterisation: returns opaque page tokens, no real images."""
    return mocker.patch(
        "ocr_processor.infrastructure.ocr.searchable_pdf_engine.render_pdf_pages",
        side_effect=lambda path, page_numbers, dpi: [f"image-{n}" for n in page_numbers],
    )


def test_single_page_pdf_gets_nonempty_text_layer(tmp_path, fake_render, mocker):
    input_path = _make_pdf(tmp_path, ["hello"])
    mocker.patch(
        "ocr_processor.infrastructure.ocr.searchable_pdf_engine.pytesseract.image_to_pdf_or_hocr",
        side_effect=lambda image, lang, extension, config: _fake_page_pdf_bytes(
            f"OCR:{image}:{lang}:{config}"
        ),
    )

    engine = TesseractSearchablePdfEngine()
    result = engine.to_searchable_pdf(input_path, language="spa", dpi=300, psm=6)

    assert result.page_count == 1
    assert result.language == "spa"
    assert result.dpi == 300
    assert result.psm == 6
    assert result.engine == "tesseract-searchable-pdf"

    with fitz.open("pdf", result.pdf_bytes) as doc:
        assert doc.page_count == 1
        text = doc[0].get_text("text")
    assert "OCR:image-1:spa:--psm 6" in text


def test_page_order_preserved_for_multipage_document(tmp_path, fake_render, mocker):
    input_path = _make_pdf(tmp_path, ["p1", "p2", "p3"])
    mocker.patch(
        "ocr_processor.infrastructure.ocr.searchable_pdf_engine.pytesseract.image_to_pdf_or_hocr",
        side_effect=lambda image, lang, extension, config: _fake_page_pdf_bytes(
            f"TEXT-FOR-{image}"
        ),
    )

    engine = TesseractSearchablePdfEngine()
    result = engine.to_searchable_pdf(input_path, language="eng", dpi=300, psm=3)

    assert result.page_count == 3
    with fitz.open("pdf", result.pdf_bytes) as doc:
        for index in range(3):
            text = doc[index].get_text("text")
            assert f"TEXT-FOR-image-{index + 1}" in text


def test_image_input_skips_rasterization(tmp_path, mocker):
    input_path = tmp_path / "photo.png"
    input_path.write_bytes(b"fake-png-bytes")

    render_spy = mocker.patch(
        "ocr_processor.infrastructure.ocr.searchable_pdf_engine.render_pdf_pages"
    )
    mocker.patch("PIL.Image.open", return_value="PIL-IMAGE")
    mocker.patch(
        "ocr_processor.infrastructure.ocr.searchable_pdf_engine.pytesseract.image_to_pdf_or_hocr",
        side_effect=lambda image, lang, extension, config: _fake_page_pdf_bytes(f"IMG:{image}"),
    )

    engine = TesseractSearchablePdfEngine()
    result = engine.to_searchable_pdf(input_path, language="eng", dpi=300, psm=3)

    render_spy.assert_not_called()
    assert result.page_count == 1
    with fitz.open("pdf", result.pdf_bytes) as doc:
        text = doc[0].get_text("text")
    assert "IMG:PIL-IMAGE" in text


def test_ocr_failure_wrapped_in_ocr_processing_error(tmp_path, fake_render, mocker):
    input_path = _make_pdf(tmp_path, ["hello"])
    mocker.patch(
        "ocr_processor.infrastructure.ocr.searchable_pdf_engine.pytesseract.image_to_pdf_or_hocr",
        side_effect=RuntimeError("tesseract exploded"),
    )

    engine = TesseractSearchablePdfEngine()
    with pytest.raises(OCRProcessingError):
        engine.to_searchable_pdf(input_path, language="eng", dpi=300, psm=3)
