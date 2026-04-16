import logging
import time
from pathlib import Path
from uuid import uuid4

import pytesseract
from PIL import Image

from ocr_processor.config import settings
from ocr_processor.domain.contracts import IOCREngine
from ocr_processor.domain.entities import OCRResult
from ocr_processor.domain.exceptions import OCRProcessingError
from ocr_processor.domain.value_objects import OCREngine

logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def _convert_pdf_to_images(file_path: Path) -> list:
    """Convert each PDF page to a PIL Image using pdf2image."""
    try:
        from pdf2image import convert_from_path

        return convert_from_path(str(file_path))
    except Exception as exc:  # noqa: BLE001
        raise OCRProcessingError(f"PDF conversion failed: {exc}") from exc


def _detect_language(text: str) -> str:
    """Best-effort language detection; fallback to 'und' (undetermined)."""
    if not text.strip():
        return "und"
    try:
        from langdetect import detect

        return detect(text)
    except Exception:  # noqa: BLE001
        return "und"


class TesseractOCREngine(IOCREngine):
    """OCR engine backed by Tesseract."""

    def process(self, file_path: Path, language: str = "eng") -> OCRResult:
        document_id = uuid4()
        start = time.monotonic()

        content_type = _guess_content_type(file_path)
        try:
            if content_type == "application/pdf":
                pages = _convert_pdf_to_images(file_path)
                page_texts = [
                    pytesseract.image_to_string(page, lang=language) for page in pages
                ]
            else:
                image = Image.open(file_path)
                page_texts = [pytesseract.image_to_string(image, lang=language)]
        except OCRProcessingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OCRProcessingError(str(exc)) from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        full_text = "\n\n".join(page_texts).strip()
        detected_lang = _detect_language(full_text)

        logger.info(
            "Tesseract OCR complete",
            extra={
                "pages": len(page_texts),
                "language": detected_lang,
                "processing_time_ms": round(elapsed_ms, 2),
            },
        )

        return OCRResult(
            document_id=document_id,
            text=full_text,
            language=detected_lang,
            page_count=len(page_texts),
            processing_time_ms=round(elapsed_ms, 2),
            engine=OCREngine.TESSERACT,
        )


def _guess_content_type(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    mapping = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }
    return mapping.get(suffix, "application/octet-stream")
