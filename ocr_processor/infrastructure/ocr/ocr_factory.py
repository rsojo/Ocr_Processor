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
        raise ValueError(
            f"Unknown OCR engine '{engine}'. Supported: tesseract, paddleocr, pdf_inspector"
        )
