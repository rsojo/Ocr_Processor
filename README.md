# OCR Processor API

A production-ready OCR service built with **Python + FastAPI**, following **Clean Architecture** and SOLID principles. Supports file upload and remote URL processing using native PDF text extraction for text-based PDFs and **Tesseract OCR** for scanned PDFs/images, with pdf-inspector and PaddleOCR extension points.

---

## Architecture

```
ocr_processor/
├── domain/              # Entities, value objects, exceptions, contracts (pure Python)
├── application/         # Use cases, validators, DTOs (business logic)
├── infrastructure/      # Tesseract adapter, URL downloader, temp storage, logging
└── presentation/        # FastAPI app, routes, middleware, Pydantic schemas
```

Key patterns:
- **Strategy** — `IOCREngine` lets you swap OCR providers without touching use cases.
- **Factory** — `OCREngineFactory` creates the engine from the `OCR_ENGINE` env var.
- **Dependency Injection** — FastAPI `Depends()` wires everything together.
- **Repository** — `IFileStorage` / `IURLDownloader` abstract away I/O.
- **Concurrent page OCR** — PDFs are split by page, processed concurrently, and reassembled in original order.
- **Hybrid PDF extraction** — text-based pages use native PDF text via PyMuPDF, while scanned pages fall back to Tesseract OCR.
- **Structured Markdown** — generated output includes page markers for downstream parsing.

---

## Quick Start

### Docker (recommended)

```bash
cp .env.example .env          # review and adjust
docker compose up --build
```

### Local

```bash
# Prerequisites for OCR_ENGINE=tesseract: tesseract-ocr + poppler-utils installed on your OS
pip install -r requirements-dev.txt
cp .env.example .env          # set OCR_ENGINE=tesseract for local setup
uvicorn ocr_processor.presentation.main:app --reload
```

The default engine is `hybrid_pdf`, which is fully provisioned by the Docker image. For a simple local setup, set `OCR_ENGINE=tesseract` unless you have installed PyMuPDF locally.

Interactive docs: http://localhost:8000/docs

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Liveness check |
| `GET` | `/api/v1/ready` | Readiness — verifies dependencies for the configured OCR engine |
| `POST` | `/api/v1/ocr/upload` | Upload a file, get extracted text |
| `POST` | `/api/v1/ocr/url` | Provide a URL, download and extract text |

### Upload a file

```bash
curl -X POST http://localhost:8000/api/v1/ocr/upload \
  -F "file=@invoice.png;type=image/png"
```

### Process a URL

```bash
curl -X POST http://localhost:8000/api/v1/ocr/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/document.pdf", "language": "eng"}'
```

### Example response

```json
{
  "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "success",
  "text": "Invoice #12345\nDate: 2024-01-15\n...",
  "language": "en",
  "page_count": 1,
  "processing_time_ms": 342.5,
  "engine": "tesseract",
  "filename": "invoice.png",
  "document_id": "...",
  "created_at": "2024-01-15T10:30:00Z",
  "error": null
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OCR_ENGINE` | `hybrid_pdf` | OCR engine: `hybrid_pdf`, `pdf_inspector`, `tesseract`, or `paddleocr` (`paddleocr` is not implemented yet) |
| `TESSERACT_CMD` | `/usr/bin/tesseract` | Path to the Tesseract binary |
| `DEFAULT_OCR_LANGUAGE` | `eng` | Tesseract language code |
| `MAX_FILE_SIZE_MB` | `20` | Max upload size in MB |
| `MAX_DOWNLOAD_SIZE_MB` | `20` | Max download size in MB |
| `DOWNLOAD_TIMEOUT_SECONDS` | `30` | Timeout for URL downloads |
| `TEMP_DIR` | `/tmp/ocr_processor` | Directory for temporary files |
| `WORKERS` | `4` | Uvicorn worker count |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins (JSON list) |

---

## Security

- **MIME type enforcement** — only `image/png`, `image/jpeg`, `image/tiff`, `image/bmp`, `image/webp`, `application/pdf` are accepted.
- **Size limits** — configurable via `MAX_FILE_SIZE_MB`.
- **SSRF protection** — URL downloader resolves hostnames and blocks all private/reserved IP ranges (RFC1918, loopback, link-local, AWS metadata endpoint).
- **Temporary file sanitisation** — directory components stripped from uploaded filenames.
- **Non-root Docker user** — runs as `appuser` (UID 1001).

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Extending with a New OCR Engine

1. Create `ocr_processor/infrastructure/ocr/my_engine.py` implementing `IOCREngine`.
2. Register it in `OCREngineFactory.create()`.
3. Set `OCR_ENGINE=my_engine` in your environment.

No changes to use cases or routes are required.
