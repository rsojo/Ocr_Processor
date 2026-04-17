from ocr_processor.application.dtos import OCRResultDTO, ProcessFileInput
from ocr_processor.application.validators import validate_file
from ocr_processor.domain.contracts import IOCREngine, IFileStorage
from ocr_processor.domain.entities import Document
from ocr_processor.domain.value_objects import ProcessingStatus


class ProcessFileUseCase:
    """Orchestrates file upload → validate → OCR → result."""

    def __init__(self, ocr_engine: IOCREngine, storage: IFileStorage) -> None:
        self._engine = ocr_engine
        self._storage = storage

    def execute(self, input_data: ProcessFileInput, request_id: str) -> OCRResultDTO:
        validate_file(input_data.content_type, len(input_data.data))

        document = Document(
            filename=input_data.filename,
            content_type=input_data.content_type,
            size_bytes=len(input_data.data),
        )

        file_path = self._storage.save(input_data.data, input_data.filename)
        try:
            result = self._engine.process(file_path)
        finally:
            self._storage.cleanup(file_path)

        return OCRResultDTO(
            request_id=request_id,
            status=ProcessingStatus.SUCCESS,
            text=result.text,
            language=result.language,
            page_count=result.page_count,
            processing_time_ms=result.processing_time_ms,
            engine=result.engine,
            filename=document.filename,
            document_id=document.id,
            created_at=result.created_at,
            markdown=result.markdown,
        )
