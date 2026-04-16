import pytest

from ocr_processor.application.validators import validate_file, validate_url
from ocr_processor.domain.exceptions import (
    FileTooLargeError,
    InvalidFileTypeError,
    UnsafeURLError,
)


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------

def test_validate_file_valid():
    validate_file("image/png", 1024)  # should not raise


def test_validate_file_invalid_mime():
    with pytest.raises(InvalidFileTypeError):
        validate_file("application/x-executable", 100)


def test_validate_file_too_large():
    max_bytes = 20 * 1024 * 1024
    with pytest.raises(FileTooLargeError):
        validate_file("image/png", max_bytes + 1)


def test_validate_file_exactly_at_limit():
    max_bytes = 20 * 1024 * 1024
    validate_file("image/png", max_bytes)  # should not raise


def test_validate_file_pdf_allowed():
    validate_file("application/pdf", 512)


# ---------------------------------------------------------------------------
# validate_url
# ---------------------------------------------------------------------------

def test_validate_url_invalid_scheme():
    with pytest.raises(UnsafeURLError, match="scheme"):
        validate_url("ftp://example.com/file.png")


def test_validate_url_localhost():
    with pytest.raises(UnsafeURLError):
        validate_url("http://127.0.0.1/file.png")


def test_validate_url_private_10():
    with pytest.raises(UnsafeURLError):
        validate_url("http://10.0.0.1/file.png")


def test_validate_url_private_172():
    with pytest.raises(UnsafeURLError):
        validate_url("http://172.16.0.1/file.png")


def test_validate_url_private_192():
    with pytest.raises(UnsafeURLError):
        validate_url("http://192.168.1.1/file.png")


def test_validate_url_link_local():
    with pytest.raises(UnsafeURLError):
        validate_url("http://169.254.169.254/latest/meta-data/")


def test_validate_url_missing_hostname():
    with pytest.raises(UnsafeURLError, match="hostname"):
        validate_url("http:///file.png")


def test_validate_url_file_scheme():
    with pytest.raises(UnsafeURLError, match="scheme"):
        validate_url("file:///etc/passwd")
