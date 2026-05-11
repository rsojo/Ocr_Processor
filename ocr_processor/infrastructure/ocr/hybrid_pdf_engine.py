import logging
import re
import time
from pathlib import Path
from uuid import uuid4

from PIL import Image

from ocr_processor.domain.contracts import IOCREngine
from ocr_processor.domain.entities import OCRResult
from ocr_processor.domain.exceptions import OCRProcessingError
from ocr_processor.domain.value_objects import OCREngine
from ocr_processor.infrastructure.ocr._parallel import ocr_pages_parallel
from ocr_processor.infrastructure.ocr.native_pdf_extractor import (
    extract_native_pdf_pages,
    render_pdf_pages,
)

logger = logging.getLogger(__name__)

_MIN_NATIVE_TEXT_CHARS = 30
_PAGE_MARKER_PREFIX = "<!-- Page"


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


def _detect_language(text: str) -> str:
    if not text.strip():
        return "und"
    try:
        from langdetect import detect

        return detect(text)
    except Exception:  # noqa: BLE001
        return "und"


def _has_useful_native_text(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    return len(compact) >= _MIN_NATIVE_TEXT_CHARS


def _to_markdown(page_texts: list[str]) -> str:
    markdown_pages = []
    for index, page_text in enumerate(page_texts, start=1):
        body = page_text.strip()
        markdown_pages.append(
            f"{_PAGE_MARKER_PREFIX} {index} -->\n\n## Page {index}\n\n{body}".strip()
        )
    return "\n\n".join(markdown_pages).strip()


class HybridPdfEngine(IOCREngine):
    """PDF-first engine that uses native text extraction before OCR fallback."""

    def process(self, file_path: Path, language: str = "eng") -> OCRResult:
        document_id = uuid4()
        start = time.monotonic()
        content_type = _guess_content_type(file_path)

        try:
            if content_type == "application/pdf":
                page_texts, methods = self._process_pdf(file_path, language)
            else:
                image = Image.open(file_path)
                page_texts = ocr_pages_parallel([image], language)
                methods = ["tesseract"]
        except OCRProcessingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OCRProcessingError(str(exc)) from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        full_text = "\n\n".join(text.strip() for text in page_texts if text.strip()).strip()
        markdown = _to_markdown(page_texts)
        detected_lang = _detect_language(full_text)

        logger.info(
            "Hybrid PDF OCR complete",
            extra={
                "pages": len(page_texts),
                "language": detected_lang,
                "methods": methods,
                "processing_time_ms": round(elapsed_ms, 2),
            },
        )

        return OCRResult(
            document_id=document_id,
            text=full_text,
            language=detected_lang,
            page_count=len(page_texts),
            processing_time_ms=round(elapsed_ms, 2),
            engine=OCREngine.HYBRID_PDF,
            markdown=markdown,
        )

    def _process_pdf(self, file_path: Path, language: str) -> tuple[list[str], list[str]]:
        native_pages = extract_native_pdf_pages(file_path)
        page_texts = [page.text for page in native_pages]
        methods = ["native" if _has_useful_native_text(text) else "tesseract" for text in page_texts]
        fallback_page_numbers = [
            page.page_number
            for page, method in zip(native_pages, methods)
            if method == "tesseract"
        ]

        if fallback_page_numbers:
            images = render_pdf_pages(file_path, fallback_page_numbers)
            fallback_texts = ocr_pages_parallel(images, language)
            for page_number, text in zip(fallback_page_numbers, fallback_texts):
                page_texts[page_number - 1] = text

        return page_texts, methods
