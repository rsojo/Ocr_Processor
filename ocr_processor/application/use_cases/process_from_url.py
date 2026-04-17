from ocr_processor.application.dtos import OCRResultDTO, ProcessURLInput
from ocr_processor.application.validators import validate_file, validate_url
from ocr_processor.domain.contracts import IOCREngine, IFileStorage, IURLDownloader
from ocr_processor.domain.entities import Document
from ocr_processor.domain.value_objects import ProcessingStatus


class ProcessFromURLUseCase:
    """Orchestrates URL → download → validate → OCR → result."""

    def __init__(
        self,
        ocr_engine: IOCREngine,
        storage: IFileStorage,
        downloader: IURLDownloader,
    ) -> None:
        self._engine = ocr_engine
        self._storage = storage
        self._downloader = downloader

    def execute(self, input_data: ProcessURLInput, request_id: str) -> OCRResultDTO:
        validate_url(input_data.url)

        data, content_type, filename = self._downloader.download(input_data.url)
        validate_file(content_type, len(data))

        document = Document(
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            source_url=input_data.url,
        )

        file_path = self._storage.save(data, filename)
        try:
            result = self._engine.process(file_path, language=input_data.language)
        finally:
            self._storage.cleanup(file_path)

        return OCRResultDTO(
            request_id=request_id,
            status=ProcessingStatus.SUCCESS,
            text=None if result.markdown else result.text,
            language=result.language,
            page_count=result.page_count,
            processing_time_ms=result.processing_time_ms,
            engine=result.engine,
            filename=document.filename,
            document_id=document.id,
            created_at=result.created_at,
            markdown=result.markdown,
        )
