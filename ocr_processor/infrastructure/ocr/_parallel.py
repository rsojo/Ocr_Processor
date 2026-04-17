"""Shared parallel-OCR utilities used by Tesseract-based engines."""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytesseract

from ocr_processor.domain.exceptions import OCRProcessingError

logger = logging.getLogger(__name__)

# 200 DPI is sufficient for OCR accuracy while using ~44% less memory than 300 DPI.
_OCR_DPI = 200


def _cgroup_cpu_count() -> int:
    """CPUs available to this process — respects container cgroup limits."""
    try:
        return len(os.sched_getaffinity(0)) or 1
    except AttributeError:
        return os.cpu_count() or 1


# One persistent pool per worker process — not recreated per request.
_POOL: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=_cgroup_cpu_count())


def convert_pdf_to_images(file_path: Path) -> list:
    """Rasterise all pages of a PDF to PIL Images at 200 DPI.

    Uses pdf2image's internal thread_count to parallelise page rendering.
    """
    try:
        from pdf2image import convert_from_path

        thread_count = _cgroup_cpu_count()
        return convert_from_path(str(file_path), dpi=_OCR_DPI, thread_count=thread_count)
    except Exception as exc:  # noqa: BLE001
        raise OCRProcessingError(f"PDF conversion failed: {exc}") from exc


def ocr_pages_parallel(pages: list, language: str) -> list[str]:
    """Run Tesseract on *pages* concurrently using the module-level thread pool.

    Returns an ordered list of extracted strings, one per page.
    Tesseract's native C extension releases the GIL so threads run truly parallel.
    """
    if not pages:
        return []

    if len(pages) == 1:
        return [pytesseract.image_to_string(pages[0], lang=language)]

    ordered: list[str] = [""] * len(pages)
    futures = {
        _POOL.submit(pytesseract.image_to_string, page, lang=language): idx
        for idx, page in enumerate(pages)
    }
    for future in as_completed(futures):
        idx = futures[future]
        try:
            ordered[idx] = future.result()
        except Exception as exc:  # noqa: BLE001
            raise OCRProcessingError(
                f"OCR failed for page {idx + 1} of {len(pages)}: {exc}"
            ) from exc
    return ordered
