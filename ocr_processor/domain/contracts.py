from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple

from ocr_processor.domain.entities import OCRResult


class IOCREngine(ABC):
    """Strategy contract for OCR engines."""

    @abstractmethod
    def process(self, file_path: Path, language: str = "eng") -> OCRResult:
        """Process a document and return the OCR result."""


class IFileStorage(ABC):
    """Contract for temporary file storage."""

    @abstractmethod
    def save(self, data: bytes, filename: str) -> Path:
        """Persist bytes to a temporary file and return its path."""

    @abstractmethod
    def cleanup(self, path: Path) -> None:
        """Remove a temporary file."""


class IURLDownloader(ABC):
    """Contract for downloading remote files."""

    @abstractmethod
    def download(self, url: str) -> Tuple[bytes, str, str]:
        """Download a URL.

        Returns:
            Tuple of (content bytes, content_type, filename).
        """
