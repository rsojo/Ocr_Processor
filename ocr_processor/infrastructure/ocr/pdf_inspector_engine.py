import logging
import time
from pathlib import Path
from uuid import uuid4

from ocr_processor.domain.contracts import IOCREngine
from ocr_processor.domain.entities import OCRResult
from ocr_processor.domain.exceptions import OCRProcessingError
from ocr_processor.domain.value_objects import OCREngine
from ocr_processor.infrastructure.ocr.markdown_cleaner import clean_markdown

logger = logging.getLogger(__name__)

# Marker inserted by pdf-inspector between pages when page-break mode is used.
_PAGE_MARKER = "<!-- Page"


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
    """Best-effort language detection; fallback to 'und' (undetermined)."""
    if not text.strip():
        return "und"
    try:
        from langdetect import detect

        return detect(text)
    except Exception:  # noqa: BLE001
        return "und"


def _tesseract_fallback(file_path: Path, language: str = "eng") -> tuple[str, int]:
    """Extract plain text via Tesseract; returns (text, page_count)."""
    try:
        import pytesseract
        from PIL import Image

        from ocr_processor.config import settings

        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

        content_type = _guess_content_type(file_path)
        if content_type == "application/pdf":
            from pdf2image import convert_from_path

            pages = convert_from_path(str(file_path))
            page_texts = [
                pytesseract.image_to_string(page, lang=language) for page in pages
            ]
        else:
            image = Image.open(file_path)
            page_texts = [pytesseract.image_to_string(image, lang=language)]

        return "\n\n".join(page_texts).strip(), len(page_texts)
    except Exception as exc:  # noqa: BLE001
        raise OCRProcessingError(f"Tesseract fallback failed: {exc}") from exc


class PdfInspectorEngine(IOCREngine):
    """OCR engine that uses *pdf-inspector* for text-based PDFs.

    For PDFs classified as text-based or mixed, the library extracts text
    and converts it to clean Markdown in one pass (no OCR required).
    For scanned PDFs and raster images, it falls back to Tesseract and
    returns the plain text in the ``text`` field (``markdown`` is *None*
    for those cases because there is no structured layout to convert).
    """

    def process(self, file_path: Path, language: str = "eng") -> OCRResult:
        document_id = uuid4()
        start = time.monotonic()

        try:
            import pdf_inspector  # type: ignore[import]
        except ImportError as exc:
            raise OCRProcessingError(
                "pdf_inspector is not installed. "
                "Build it with: pip install maturin && "
                "git clone https://github.com/firecrawl/pdf-inspector && "
                "cd pdf-inspector && maturin develop --release"
            ) from exc

        content_type = _guess_content_type(file_path)

        markdown: str | None = None
        text: str = ""
        page_count: int = 1

        if content_type == "application/pdf":
            try:
                result = pdf_inspector.process_pdf(str(file_path), page_break=True)
            except TypeError:
                # Older builds that don't support page_break — call without it.
                try:
                    result = pdf_inspector.process_pdf(str(file_path))
                except Exception as exc:  # noqa: BLE001
                    raise OCRProcessingError(f"pdf-inspector failed: {exc}") from exc
            except Exception as exc:  # noqa: BLE001
                raise OCRProcessingError(f"pdf-inspector failed: {exc}") from exc

            pdf_type: str = (result.pdf_type or "").lower()
            logger.info(
                "pdf-inspector classification",
                extra={"pdf_type": pdf_type, "file": file_path.name},
            )

            if pdf_type in ("text_based", "mixed") and result.markdown:
                markdown = clean_markdown(result.markdown)
                text = ""  # text is not returned in API when markdown is present
                # page_count is not part of pdf-inspector's public Python API;
                # estimate it from embedded page markers when present.
                marker_count = markdown.count(_PAGE_MARKER)
                page_count = marker_count if marker_count > 0 else 1
            else:
                # Scanned PDF — fall back to Tesseract OCR.
                logger.info(
                    "pdf-inspector: scanned PDF detected, falling back to Tesseract",
                    extra={"pdf_type": pdf_type},
                )
                text, page_count = _tesseract_fallback(file_path, language)
        else:
            # Raster image — Tesseract only.
            text, page_count = _tesseract_fallback(file_path, language)

        elapsed_ms = (time.monotonic() - start) * 1000
        detected_lang = _detect_language(markdown or text)

        logger.info(
            "pdf-inspector engine complete",
            extra={
                "pages": page_count,
                "language": detected_lang,
                "has_markdown": markdown is not None,
                "processing_time_ms": round(elapsed_ms, 2),
            },
        )

        return OCRResult(
            document_id=document_id,
            text=text,
            language=detected_lang,
            page_count=page_count,
            processing_time_ms=round(elapsed_ms, 2),
            engine=OCREngine.PDF_INSPECTOR,
            markdown=markdown,
        )
