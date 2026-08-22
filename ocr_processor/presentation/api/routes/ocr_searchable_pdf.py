import asyncio

from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile

from ocr_processor.application.validators import validate_file
from ocr_processor.config import settings
from ocr_processor.infrastructure.ocr.searchable_pdf_engine import (
    TesseractSearchablePdfEngine,
)
from ocr_processor.infrastructure.storage.temp_storage import TempFileStorage

router = APIRouter()

_LANGUAGE_PATTERN = r"^[a-z]{3}(\+[a-z]{3})*$"


def get_searchable_pdf_engine() -> TesseractSearchablePdfEngine:
    return TesseractSearchablePdfEngine()


def get_storage() -> TempFileStorage:
    return TempFileStorage()


@router.post("/ocr/searchable-pdf", tags=["ocr"])
async def ocr_searchable_pdf(
    request: Request,
    file: UploadFile,
    language: str | None = Query(default=None, pattern=_LANGUAGE_PATTERN),
    dpi: int = Query(default=300, ge=72, le=600),
    psm: int = Query(default=3, ge=0, le=13),
    engine: TesseractSearchablePdfEngine = Depends(get_searchable_pdf_engine),
    storage: TempFileStorage = Depends(get_storage),
):
    """OCR every page of a document and re-emit it as a PDF with an invisible text layer.

    Generic capability only: the service has no bank-statement-specific default —
    ``psm`` defaults to Tesseract's own default (3), not the 6 a tabular statement needs.
    Callers with domain knowledge pass their own ``psm``/``dpi``/``language``.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    resolved_language = language or settings.default_ocr_language

    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    validate_file(content_type, len(data))

    file_path = storage.save(data, file.filename or "upload")
    try:
        result = await asyncio.to_thread(
            engine.to_searchable_pdf,
            file_path,
            language=resolved_language,
            dpi=dpi,
            psm=psm,
        )
    finally:
        storage.cleanup(file_path)

    return Response(
        content=result.pdf_bytes,
        media_type="application/pdf",
        headers={
            "X-OCR-Request-Id": request_id,
            "X-OCR-Page-Count": str(result.page_count),
            "X-OCR-Engine": result.engine,
            "X-OCR-Language": result.language,
            "X-OCR-Dpi": str(result.dpi),
            "X-OCR-Psm": str(result.psm),
            "X-OCR-Processing-Ms": str(result.processing_time_ms),
        },
    )
