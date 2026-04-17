from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class Document:
    id: UUID = field(default_factory=uuid4)
    filename: str = ""
    content_type: str = ""
    size_bytes: int = 0
    source_url: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class OCRResult:
    document_id: UUID
    text: str
    language: str
    page_count: int
    processing_time_ms: float
    engine: str
    confidence: Optional[float] = None
    markdown: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
