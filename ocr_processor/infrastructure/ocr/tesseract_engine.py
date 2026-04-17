import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from os import cpu_count
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

_PAGE_MARKER_PREFIX = "<!-- Page"
_TABLE_MARKER = "<!-- TABLE -->"
_GRAPHIC_MARKER = "<!-- GRAPHIC -->"
_TABLE_LIKE_LINE = re.compile(r"(\|.+\|)|(\t+)|(\S+\s{2,}\S+)")
_GRAPHIC_LIKE_LINE = re.compile(
    r"\b(graph|chart|figure|figura|grafica|gráfica|plot|diagram)\b",
    re.IGNORECASE,
)


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


def _ocr_pages_concurrently(pages: list, language: str) -> list[str]:
    if not pages:
        return []
    if len(pages) == 1:
        return [pytesseract.image_to_string(pages[0], lang=language)]

    max_workers = min(len(pages), max(cpu_count() or 1, 1))
    ordered_results: list[str] = [""] * len(pages)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(pytesseract.image_to_string, page, lang=language): index
            for index, page in enumerate(pages)
        }
        for future in as_completed(futures):
            page_index = futures[future]
            try:
                ordered_results[page_index] = future.result()
            except Exception as exc:  # noqa: BLE001
                raise OCRProcessingError(f"Page OCR failed: {exc}") from exc
    return ordered_results


def _mark_structural_lines(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if _TABLE_LIKE_LINE.search(stripped):
        return f"{_TABLE_MARKER} {stripped}"
    if _GRAPHIC_LIKE_LINE.search(stripped):
        return f"{_GRAPHIC_MARKER} {stripped}"
    return stripped


def _to_markdown(page_texts: list[str]) -> str:
    markdown_pages: list[str] = []
    for index, page_text in enumerate(page_texts, start=1):
        annotated_lines = [_mark_structural_lines(line) for line in page_text.splitlines()]
        body = "\n".join(line for line in annotated_lines if line).strip()
        markdown_pages.append(
            f"{_PAGE_MARKER_PREFIX} {index} -->\n\n## Page {index}\n\n{body}".strip()
        )
    return "\n\n".join(markdown_pages).strip()


class TesseractOCREngine(IOCREngine):
    """OCR engine backed by Tesseract."""

    def process(self, file_path: Path, language: str = "eng") -> OCRResult:
        document_id = uuid4()
        start = time.monotonic()

        content_type = _guess_content_type(file_path)
        try:
            if content_type == "application/pdf":
                pages = _convert_pdf_to_images(file_path)
                page_texts = _ocr_pages_concurrently(pages, language)
            else:
                image = Image.open(file_path)
                page_texts = _ocr_pages_concurrently([image], language)
        except OCRProcessingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OCRProcessingError(str(exc)) from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        full_text = "\n\n".join(page_texts).strip()
        markdown = _to_markdown(page_texts)
        detected_lang = _detect_language(full_text)

        logger.info(
            "Tesseract OCR complete",
            extra={
                "pages": len(page_texts),
                "language": detected_lang,
                "has_markdown": bool(markdown),
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
            markdown=markdown,
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
