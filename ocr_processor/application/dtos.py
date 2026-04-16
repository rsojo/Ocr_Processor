from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class ProcessFileInput:
    filename: str
    content_type: str
    data: bytes


@dataclass
class ProcessURLInput:
    url: str
    language: str = "eng"


@dataclass
class OCRResultDTO:
    request_id: str
    status: str
    text: str
    language: str
    page_count: int
    processing_time_ms: float
    engine: str
    filename: str
    document_id: UUID
    created_at: datetime
    error: Optional[str] = None
