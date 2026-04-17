import time
from pathlib import Path

from ocr_processor.infrastructure.ocr.tesseract_engine import TesseractOCREngine


def test_pdf_concurrent_processing_preserves_order_and_generates_markdown(monkeypatch):
    pages = ["page-1", "page-2", "page-3"]
    delays = {"page-1": 0.05, "page-2": 0.01, "page-3": 0.0}
    outputs = {
        "page-1": "Fila 1 | Columna A | Columna B",
        "page-2": "Gráfica de ventas trimestrales",
        "page-3": "Texto normal en la última página",
    }

    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.tesseract_engine._guess_content_type",
        lambda _: "application/pdf",
    )
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.tesseract_engine._convert_pdf_to_images",
        lambda _: pages,
    )
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.tesseract_engine._detect_language",
        lambda _: "es",
    )

    def fake_image_to_string(page, lang="eng"):
        time.sleep(delays[page])
        return outputs[page]

    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.tesseract_engine.pytesseract.image_to_string",
        fake_image_to_string,
    )

    result = TesseractOCREngine().process(Path("/tmp/sample.pdf"))

    assert result.page_count == 3
    assert result.text == (
        "Fila 1 | Columna A | Columna B\n\n"
        "Gráfica de ventas trimestrales\n\n"
        "Texto normal en la última página"
    )
    assert result.markdown is not None
    assert "<!-- Page 1 -->" in result.markdown
    assert "<!-- Page 2 -->" in result.markdown
    assert "<!-- TABLE --> Fila 1 | Columna A | Columna B" in result.markdown
    assert "<!-- GRAPHIC --> Gráfica de ventas trimestrales" in result.markdown


def test_single_image_generates_markdown(monkeypatch):
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.tesseract_engine._guess_content_type",
        lambda _: "image/png",
    )
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.tesseract_engine._detect_language",
        lambda _: "es",
    )
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.tesseract_engine.Image.open",
        lambda _: "single-page-image",
    )
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.tesseract_engine.pytesseract.image_to_string",
        lambda *_args, **_kwargs: "Solo texto",
    )

    result = TesseractOCREngine().process(Path("/tmp/sample.png"))

    assert result.page_count == 1
    assert result.text == "Solo texto"
    assert result.markdown is not None
    assert "<!-- Page 1 -->" in result.markdown
    assert "## Page 1" in result.markdown
