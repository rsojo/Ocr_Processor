"""Integration tests for all API endpoints.

OCR engine and URL downloader are mocked so these tests run without
Tesseract or internet access.
"""
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ocr_processor.domain.entities import OCRResult
from ocr_processor.domain.value_objects import OCREngine
from ocr_processor.presentation.main import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_ocr_result() -> OCRResult:
    return OCRResult(
        document_id=uuid4(),
        text="Hello, World!",
        language="en",
        page_count=1,
        processing_time_ms=12.3,
        engine=OCREngine.TESSERACT,
        markdown="<!-- Page 1 -->\n\n## Page 1\n\nHello, World!",
    )


@pytest.fixture()
def mock_engine(mocker):
    engine = mocker.MagicMock()
    engine.process.return_value = _make_ocr_result()
    return engine


@pytest.fixture()
def mock_downloader(mocker):
    downloader = mocker.MagicMock()
    # Returns (bytes, content_type, filename)
    downloader.download.return_value = (b"fake-image-bytes", "image/png", "photo.png")
    return downloader


@pytest.fixture()
def client(mock_engine, mock_downloader, mocker):
    # Patch factories so DI returns our mocks
    mocker.patch(
        "ocr_processor.presentation.api.routes.ocr_upload.OCREngineFactory.create",
        return_value=mock_engine,
    )
    mocker.patch(
        "ocr_processor.presentation.api.routes.ocr_url.OCREngineFactory.create",
        return_value=mock_engine,
    )
    mocker.patch(
        "ocr_processor.presentation.api.routes.ocr_url.HTTPURLDownloader",
        return_value=mock_downloader,
    )
    # Patch validate_file so size/mime checks pass for our fake data
    mocker.patch(
        "ocr_processor.application.use_cases.process_file.validate_file"
    )
    mocker.patch(
        "ocr_processor.application.use_cases.process_from_url.validate_file"
    )
    mocker.patch(
        "ocr_processor.application.use_cases.process_from_url.validate_url"
    )
    # Storage: save returns a temp path, cleanup is a no-op
    tmp_path = Path("/tmp/test_upload.png")
    mock_storage = mocker.MagicMock()
    mock_storage.save.return_value = tmp_path
    mocker.patch(
        "ocr_processor.presentation.api.routes.ocr_upload.TempFileStorage",
        return_value=mock_storage,
    )
    mocker.patch(
        "ocr_processor.presentation.api.routes.ocr_url.TempFileStorage",
        return_value=mock_storage,
    )

    app = create_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# POST /api/v1/ocr/upload
# ---------------------------------------------------------------------------

def test_upload_success(client):
    resp = client.post(
        "/api/v1/ocr/upload",
        files={"file": ("test.png", b"fake-png-data", "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["text"] == "Hello, World!"
    assert body["markdown"] is not None
    assert body["engine"] == "tesseract"
    assert body["page_count"] == 1
    assert "request_id" in body


def test_upload_invalid_file_type(mocker):
    """When validate_file is NOT patched, invalid types should return 422."""
    app = create_app()
    with TestClient(app) as c:
        resp = c.post(
            "/api/v1/ocr/upload",
            files={"file": ("malware.exe", b"MZ\x00", "application/x-msdownload")},
        )
    assert resp.status_code == 422


def test_upload_request_id_header(client):
    resp = client.post(
        "/api/v1/ocr/upload",
        files={"file": ("test.png", b"fake", "image/png")},
        headers={"X-Request-ID": "my-custom-id"},
    )
    assert resp.headers.get("X-Request-ID") == "my-custom-id"


# ---------------------------------------------------------------------------
# POST /api/v1/ocr/url
# ---------------------------------------------------------------------------

def test_url_success(client):
    resp = client.post(
        "/api/v1/ocr/url",
        json={"url": "https://example.com/photo.png", "language": "eng"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["text"] == "Hello, World!"


def test_url_unsafe(mocker):
    """Private-IP URLs must be rejected with 400."""
    app = create_app()
    with TestClient(app) as c:
        resp = c.post(
            "/api/v1/ocr/url",
            json={"url": "http://192.168.1.1/secret.png"},
        )
    assert resp.status_code == 400
    assert resp.json()["type"] == "unsafe_url"


def test_url_invalid_scheme(mocker):
    app = create_app()
    with TestClient(app) as c:
        resp = c.post(
            "/api/v1/ocr/url",
            json={"url": "ftp://example.com/file.png"},
        )
    # Pydantic HttpUrl validation rejects non-http(s) → 422
    assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# POST /api/v1/ocr/searchable-pdf
# ---------------------------------------------------------------------------

_SEARCHABLE_PDF_HEADERS = (
    "X-OCR-Request-Id",
    "X-OCR-Page-Count",
    "X-OCR-Engine",
    "X-OCR-Language",
    "X-OCR-Dpi",
    "X-OCR-Psm",
    "X-OCR-Processing-Ms",
)


@pytest.fixture()
def mock_searchable_pdf_engine(mocker):
    from ocr_processor.infrastructure.ocr.searchable_pdf_engine import SearchablePdfResult

    engine = mocker.MagicMock()
    engine.to_searchable_pdf.return_value = SearchablePdfResult(
        pdf_bytes=b"%PDF-1.4 fake searchable pdf",
        page_count=1,
        language="spa",
        dpi=300,
        psm=6,
        processing_time_ms=42.0,
    )
    return engine


@pytest.fixture()
def searchable_pdf_client(mock_searchable_pdf_engine, mocker):
    mocker.patch(
        "ocr_processor.presentation.api.routes.ocr_searchable_pdf.TesseractSearchablePdfEngine",
        return_value=mock_searchable_pdf_engine,
    )
    tmp_path = Path("/tmp/test_searchable_pdf.pdf")
    mock_storage = mocker.MagicMock()
    mock_storage.save.return_value = tmp_path
    mocker.patch(
        "ocr_processor.presentation.api.routes.ocr_searchable_pdf.TempFileStorage",
        return_value=mock_storage,
    )
    app = create_app()
    return TestClient(app)


def test_searchable_pdf_success_headers_and_content_type(searchable_pdf_client):
    resp = searchable_pdf_client.post(
        "/api/v1/ocr/searchable-pdf",
        files={"file": ("statement.pdf", b"%PDF-1.4 fake", "application/pdf")},
        params={"language": "spa", "dpi": 300, "psm": 6},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    for header in _SEARCHABLE_PDF_HEADERS:
        assert header in resp.headers
    assert resp.headers["X-OCR-Page-Count"] == "1"
    assert resp.headers["X-OCR-Language"] == "spa"
    assert resp.headers["X-OCR-Dpi"] == "300"
    assert resp.headers["X-OCR-Psm"] == "6"
    assert resp.content == b"%PDF-1.4 fake searchable pdf"


def test_searchable_pdf_defaults_are_generic_not_bank_specific(
    searchable_pdf_client, mock_searchable_pdf_engine
):
    resp = searchable_pdf_client.post(
        "/api/v1/ocr/searchable-pdf",
        files={"file": ("statement.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 200
    _, kwargs = mock_searchable_pdf_engine.to_searchable_pdf.call_args
    assert kwargs["dpi"] == 300
    assert kwargs["psm"] == 3  # Tesseract's own default, not the bank's psm 6


@pytest.mark.parametrize(
    "params",
    [
        {"psm": 99},
        {"dpi": 5000},
        {"language": "../etc"},
    ],
)
def test_searchable_pdf_rejects_out_of_range_params(searchable_pdf_client, params):
    resp = searchable_pdf_client.post(
        "/api/v1/ocr/searchable-pdf",
        files={"file": ("statement.pdf", b"%PDF-1.4 fake", "application/pdf")},
        params=params,
    )
    assert resp.status_code == 422


def test_searchable_pdf_invalid_mime_type(mocker):
    """When validate_file is NOT patched, an unsupported type must 422."""
    app = create_app()
    with TestClient(app) as c:
        resp = c.post(
            "/api/v1/ocr/searchable-pdf",
            files={"file": ("malware.exe", b"MZ\x00", "application/x-msdownload")},
        )
    assert resp.status_code == 422
