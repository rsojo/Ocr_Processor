class OCRProcessorError(Exception):
    """Base exception for the OCR Processor."""


class InvalidFileTypeError(OCRProcessorError):
    """Raised when an uploaded file has an unsupported MIME type."""

    def __init__(self, content_type: str) -> None:
        super().__init__(f"Unsupported file type: {content_type}")
        self.content_type = content_type


class FileTooLargeError(OCRProcessorError):
    """Raised when an uploaded file exceeds the allowed size."""

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            f"File size {size_bytes} bytes exceeds maximum {max_bytes} bytes"
        )
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


class UnsafeURLError(OCRProcessorError):
    """Raised when a URL is considered unsafe (SSRF protection)."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Unsafe URL: {reason}")
        self.reason = reason


class DownloadError(OCRProcessorError):
    """Raised when downloading a remote file fails."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"Failed to download {url}: {reason}")
        self.url = url
        self.reason = reason


class OCRProcessingError(OCRProcessorError):
    """Raised when the OCR engine fails to process a document."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"OCR processing failed: {reason}")
        self.reason = reason
