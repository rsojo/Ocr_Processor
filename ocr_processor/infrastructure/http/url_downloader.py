import logging
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse, unquote

import httpx

from ocr_processor.config import settings
from ocr_processor.domain.contracts import IURLDownloader
from ocr_processor.domain.exceptions import DownloadError

logger = logging.getLogger(__name__)


def _ext_for_content_type(content_type: str) -> str:
    mapping = {
        "application/pdf": ".pdf",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
        "image/bmp": ".bmp",
        "image/webp": ".webp",
    }
    return mapping.get(content_type.split(";")[0].strip(), "")


def _filename_from_url(url: str, content_type: str) -> str:
    """Derive a safe filename from URL path or content-type."""
    path = unquote(urlparse(url).path)
    name = Path(path).name if path and path != "/" else ""
    if not name:
        ext = _ext_for_content_type(content_type)
        name = f"download{ext}"
    return name


class HTTPURLDownloader(IURLDownloader):
    """Downloads remote files with timeout and size limits."""

    def download(self, url: str) -> Tuple[bytes, str, str]:
        timeout = httpx.Timeout(settings.download_timeout_seconds)
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content_type = (
                        response.headers.get("content-type", "application/octet-stream")
                        .split(";")[0]
                        .strip()
                    )
                    chunks = []
                    total = 0
                    for chunk in response.iter_bytes(chunk_size=65536):
                        total += len(chunk)
                        if total > settings.max_download_size_bytes:
                            raise DownloadError(
                                url,
                                f"response exceeds maximum size "
                                f"({settings.max_download_size_mb} MB)",
                            )
                        chunks.append(chunk)
                    data = b"".join(chunks)
        except DownloadError:
            raise
        except httpx.HTTPStatusError as exc:
            raise DownloadError(url, f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise DownloadError(url, str(exc)) from exc

        filename = _filename_from_url(url, content_type)
        logger.info("Downloaded %s (%d bytes, %s)", url, len(data), content_type)
        return data, content_type, filename
