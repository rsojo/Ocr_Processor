from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class OCRURLRequest(BaseModel):
    url: HttpUrl
    language: str = "eng"


class OCRResponse(BaseModel):
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
