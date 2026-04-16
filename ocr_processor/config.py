from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OCR engine
    ocr_engine: str = "tesseract"
    tesseract_cmd: str = "/usr/bin/tesseract"
    default_ocr_language: str = "eng"

    # File limits
    max_file_size_mb: int = 20
    allowed_mime_types: List[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/bmp",
        "image/webp",
    ]

    # URL download
    allowed_url_schemes: List[str] = ["http", "https"]
    download_timeout_seconds: int = 30
    max_download_size_mb: int = 20

    # Storage
    temp_dir: str = "/tmp/ocr_processor"

    # Server
    workers: int = 4
    log_level: str = "INFO"

    # CORS
    cors_origins: List[str] = ["*"]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_download_size_bytes(self) -> int:
        return self.max_download_size_mb * 1024 * 1024


settings = Settings()
