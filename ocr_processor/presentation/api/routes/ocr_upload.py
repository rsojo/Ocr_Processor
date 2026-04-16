from fastapi import APIRouter, Depends, Request, UploadFile

from ocr_processor.application.dtos import ProcessFileInput
from ocr_processor.application.use_cases.process_file import ProcessFileUseCase
from ocr_processor.config import settings
from ocr_processor.domain.contracts import IOCREngine, IFileStorage
from ocr_processor.infrastructure.ocr.ocr_factory import OCREngineFactory
from ocr_processor.infrastructure.storage.temp_storage import TempFileStorage
from ocr_processor.presentation.api.schemas import OCRResponse

router = APIRouter()


def get_ocr_engine() -> IOCREngine:
    return OCREngineFactory.create(settings)


def get_storage() -> IFileStorage:
    return TempFileStorage()


def get_process_file_use_case(
    engine: IOCREngine = Depends(get_ocr_engine),
    storage: IFileStorage = Depends(get_storage),
) -> ProcessFileUseCase:
    return ProcessFileUseCase(ocr_engine=engine, storage=storage)


@router.post("/ocr/upload", response_model=OCRResponse, tags=["ocr"])
async def ocr_upload(
    request: Request,
    file: UploadFile,
    use_case: ProcessFileUseCase = Depends(get_process_file_use_case),
):
    """Upload a file and extract text via OCR."""
    request_id = getattr(request.state, "request_id", "unknown")
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    result = use_case.execute(
        ProcessFileInput(
            filename=file.filename or "upload",
            content_type=content_type,
            data=data,
        ),
        request_id=request_id,
    )
    return OCRResponse(
        request_id=result.request_id,
        status=result.status,
        text=result.text,
        language=result.language,
        page_count=result.page_count,
        processing_time_ms=result.processing_time_ms,
        engine=result.engine,
        filename=result.filename,
        document_id=result.document_id,
        created_at=result.created_at,
        error=result.error,
    )
