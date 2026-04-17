import os
from pathlib import Path
from uuid import uuid4

from ocr_processor.config import settings
from ocr_processor.domain.contracts import IFileStorage


class TempFileStorage(IFileStorage):
    """Stores files in a configured temporary directory."""

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = Path(base_dir or settings.temp_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, filename: str) -> Path:
        safe_name = Path(filename).name  # strip any directory components
        if not safe_name:
            safe_name = "upload"
        dest = self._base_dir / f"{uuid4().hex}_{safe_name}"
        dest.write_bytes(data)
        return dest

    def cleanup(self, path: Path) -> None:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
