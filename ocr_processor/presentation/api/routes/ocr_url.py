from fastapi import APIRouter, Depends, Request

from ocr_processor.application.dtos import ProcessURLInput
from ocr_processor.application.use_cases.process_from_url import ProcessFromURLUseCase
from ocr_processor.config import settings
from ocr_processor.domain.contracts import IOCREngine, IFileStorage, IURLDownloader
from ocr_processor.infrastructure.http.url_downloader import HTTPURLDownloader
from ocr_processor.infrastructure.ocr.ocr_factory import OCREngineFactory
from ocr_processor.infrastructure.storage.temp_storage import TempFileStorage
from ocr_processor.presentation.api.schemas import OCRResponse, OCRURLRequest

router = APIRouter()


def get_ocr_engine() -> IOCREngine:
    return OCREngineFactory.create(settings)


def get_storage() -> IFileStorage:
    return TempFileStorage()


def get_downloader() -> IURLDownloader:
    return HTTPURLDownloader()


def get_process_url_use_case(
    engine: IOCREngine = Depends(get_ocr_engine),
    storage: IFileStorage = Depends(get_storage),
    downloader: IURLDownloader = Depends(get_downloader),
) -> ProcessFromURLUseCase:
    return ProcessFromURLUseCase(
        ocr_engine=engine, storage=storage, downloader=downloader
    )


@router.post("/ocr/url", response_model=OCRResponse, tags=["ocr"])
async def ocr_url(
    request: Request,
    body: OCRURLRequest,
    use_case: ProcessFromURLUseCase = Depends(get_process_url_use_case),
):
    """Download a file from a URL and extract text via OCR."""
    request_id = getattr(request.state, "request_id", "unknown")
    result = use_case.execute(
        ProcessURLInput(url=str(body.url), language=body.language),
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
        markdown=result.markdown,
    )
