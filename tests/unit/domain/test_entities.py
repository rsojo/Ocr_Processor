from datetime import datetime
from uuid import uuid4

from ocr_processor.domain.entities import Document, OCRResult


def test_document_defaults():
    doc = Document()
    assert doc.filename == ""
    assert doc.content_type == ""
    assert doc.size_bytes == 0
    assert doc.source_url is None
    assert doc.id is not None
    assert isinstance(doc.created_at, datetime)


def test_document_custom_values():
    uid = uuid4()
    doc = Document(
        id=uid,
        filename="test.png",
        content_type="image/png",
        size_bytes=1024,
        source_url="https://example.com/test.png",
    )
    assert doc.id == uid
    assert doc.filename == "test.png"
    assert doc.content_type == "image/png"
    assert doc.size_bytes == 1024
    assert doc.source_url == "https://example.com/test.png"


def test_ocr_result_fields():
    doc_id = uuid4()
    result = OCRResult(
        document_id=doc_id,
        text="Hello World",
        language="en",
        page_count=1,
        processing_time_ms=42.5,
        engine="tesseract",
    )
    assert result.document_id == doc_id
    assert result.text == "Hello World"
    assert result.language == "en"
    assert result.page_count == 1
    assert result.processing_time_ms == 42.5
    assert result.engine == "tesseract"
    assert result.confidence is None
    assert isinstance(result.created_at, datetime)
