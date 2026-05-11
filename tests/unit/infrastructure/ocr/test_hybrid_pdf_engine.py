from pathlib import Path

from ocr_processor.domain.value_objects import OCREngine
from ocr_processor.infrastructure.ocr.hybrid_pdf_engine import HybridPdfEngine
from ocr_processor.infrastructure.ocr.native_pdf_extractor import NativePageExtraction


def test_text_based_pdf_uses_native_text_and_preserves_pages(monkeypatch):
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.hybrid_pdf_engine.extract_native_pdf_pages",
        lambda _: [
            NativePageExtraction(1, "CONJUNTO RESIDENCIAL ENTREPINOS P.H."),
            NativePageExtraction(2, "ALCANCE Y PROCEDIMIENTOS DEL EJERCICIO"),
        ],
    )
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.hybrid_pdf_engine._detect_language",
        lambda _: "es",
    )

    result = HybridPdfEngine().process(Path("/tmp/report.pdf"), language="spa")

    assert result.engine == OCREngine.HYBRID_PDF
    assert result.page_count == 2
    assert "CONJUNTO RESIDENCIAL" in result.text
    assert "ALCANCE Y PROCEDIMIENTOS" in result.text
    assert result.markdown is not None
    assert "<!-- Page 1 -->" in result.markdown
    assert "<!-- Page 2 -->" in result.markdown


def test_scanned_pdf_page_falls_back_to_tesseract(monkeypatch):
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.hybrid_pdf_engine.extract_native_pdf_pages",
        lambda _: [NativePageExtraction(1, "")],
    )
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.hybrid_pdf_engine.render_pdf_pages",
        lambda _path, page_numbers: [f"page-{page_numbers[0]}"],
    )
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.hybrid_pdf_engine.ocr_pages_parallel",
        lambda _pages, _language: ["OCR fallback text"],
    )
    monkeypatch.setattr(
        "ocr_processor.infrastructure.ocr.hybrid_pdf_engine._detect_language",
        lambda _: "en",
    )

    result = HybridPdfEngine().process(Path("/tmp/scanned.pdf"))

    assert result.page_count == 1
    assert result.text == "OCR fallback text"
    assert "OCR fallback text" in (result.markdown or "")
