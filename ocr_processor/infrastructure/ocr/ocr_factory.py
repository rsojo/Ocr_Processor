from ocr_processor.config import Settings
from ocr_processor.domain.contracts import IOCREngine
from ocr_processor.domain.value_objects import OCREngine


class OCREngineFactory:
    """Factory that creates the configured OCR engine."""

    @staticmethod
    def create(config: Settings) -> IOCREngine:
        engine = config.ocr_engine.lower()
        if engine == OCREngine.TESSERACT:
            from ocr_processor.infrastructure.ocr.tesseract_engine import (
                TesseractOCREngine,
            )

            return TesseractOCREngine()
        if engine == OCREngine.PADDLEOCR:
            from ocr_processor.infrastructure.ocr.paddleocr_engine import (
                PaddleOCREngine,
            )

            return PaddleOCREngine()
        if engine == OCREngine.PDF_INSPECTOR:
            from ocr_processor.infrastructure.ocr.pdf_inspector_engine import (
                PdfInspectorEngine,
            )

            return PdfInspectorEngine()
        if engine == OCREngine.HYBRID_PDF:
            from ocr_processor.infrastructure.ocr.hybrid_pdf_engine import (
                HybridPdfEngine,
            )

            return HybridPdfEngine()
        raise ValueError(
            f"Unknown OCR engine '{engine}'. Supported: "
            "hybrid_pdf, pdf_inspector, tesseract, paddleocr"
        )
