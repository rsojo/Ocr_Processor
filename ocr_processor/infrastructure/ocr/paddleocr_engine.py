from pathlib import Path

from ocr_processor.domain.contracts import IOCREngine
from ocr_processor.domain.entities import OCRResult


class PaddleOCREngine(IOCREngine):
    """PaddleOCR engine — not yet implemented.

    To add PaddleOCR support:
    1. ``pip install paddlepaddle paddleocr``
    2. Implement the ``process`` method using the PaddleOCR API.
    3. Register the engine in ``OCREngineFactory``.
    """

    def process(self, file_path: Path, language: str = "en") -> OCRResult:
        raise NotImplementedError(
            "PaddleOCR engine is not yet implemented. "
            "Set OCR_ENGINE=tesseract or implement this adapter."
        )
