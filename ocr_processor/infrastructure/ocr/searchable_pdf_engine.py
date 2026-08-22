import logging
import time
from concurrent.futures import as_completed
from dataclasses import dataclass
from pathlib import Path

import fitz  # type: ignore[import]
import pytesseract

from ocr_processor.domain.exceptions import OCRProcessingError
from ocr_processor.infrastructure.ocr._parallel import _POOL
from ocr_processor.infrastructure.ocr.native_pdf_extractor import render_pdf_pages

logger = logging.getLogger(__name__)

_ENGINE_NAME = "tesseract-searchable-pdf"

_CONTENT_TYPE_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class SearchablePdfResult:
    pdf_bytes: bytes
    page_count: int
    language: str
    dpi: int
    psm: int
    processing_time_ms: float
    engine: str = _ENGINE_NAME


def _guess_content_type(file_path: Path) -> str:
    return _CONTENT_TYPE_BY_SUFFIX.get(file_path.suffix.lower(), "application/octet-stream")


def _ocr_page_to_pdf_bytes(image, *, language: str, psm: int) -> bytes:
    return pytesseract.image_to_pdf_or_hocr(
        image, lang=language, extension="pdf", config=f"--psm {psm}"
    )


def _ocr_pages_to_pdfs_parallel(images: list, *, language: str, psm: int) -> list[bytes]:
    """OCR each page concurrently on the shared pool, reassembled by original index."""
    if not images:
        return []

    if len(images) == 1:
        return [_ocr_page_to_pdf_bytes(images[0], language=language, psm=psm)]

    ordered: list[bytes] = [b""] * len(images)
    futures = {
        _POOL.submit(_ocr_page_to_pdf_bytes, image, language=language, psm=psm): idx
        for idx, image in enumerate(images)
    }
    for future in as_completed(futures):
        idx = futures[future]
        try:
            ordered[idx] = future.result()
        except Exception as exc:  # noqa: BLE001
            raise OCRProcessingError(
                f"searchable PDF OCR failed for page {idx + 1} of {len(images)}: {exc}"
            ) from exc
    return ordered


class TesseractSearchablePdfEngine:
    """Re-emits a document with an invisible Tesseract text layer.

    Every page is OCR'd. This is deliberately NOT the per-page native/OCR
    decision that HybridPdfEngine makes: mixed output would give pages with
    heterogeneous line geometry, and downstream table parsers group lines
    across page boundaries. Homogeneity beats saving CPU here.
    """

    def to_searchable_pdf(
        self, file_path: Path, *, language: str, dpi: int, psm: int
    ) -> SearchablePdfResult:
        start = time.monotonic()
        content_type = _guess_content_type(file_path)

        try:
            if content_type == "application/pdf":
                with fitz.open(file_path) as document:
                    page_count = document.page_count
                images = render_pdf_pages(file_path, list(range(1, page_count + 1)), dpi=dpi)
            else:
                from PIL import Image

                images = [Image.open(file_path)]

            page_pdfs = _ocr_pages_to_pdfs_parallel(images, language=language, psm=psm)

            merged = fitz.open()
            try:
                for page_pdf_bytes in page_pdfs:
                    with fitz.open("pdf", page_pdf_bytes) as page_document:
                        merged.insert_pdf(page_document)
                pdf_bytes = merged.tobytes()
                result_page_count = merged.page_count
            finally:
                merged.close()
        except OCRProcessingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OCRProcessingError(str(exc)) from exc

        elapsed_ms = (time.monotonic() - start) * 1000

        logger.info(
            "Searchable PDF OCR complete",
            extra={
                "pages": result_page_count,
                "language": language,
                "dpi": dpi,
                "psm": psm,
                "processing_time_ms": round(elapsed_ms, 2),
            },
        )

        return SearchablePdfResult(
            pdf_bytes=pdf_bytes,
            page_count=result_page_count,
            language=language,
            dpi=dpi,
            psm=psm,
            processing_time_ms=round(elapsed_ms, 2),
        )
