# Stage 1: build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: runtime
FROM python:3.11-slim

# Install system dependencies for Tesseract and pdf2image (poppler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-spa \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY ocr_processor/ ocr_processor/

# Temp directory for OCR processing
RUN mkdir -p /tmp/ocr_processor && chown appuser:appuser /tmp/ocr_processor

USER appuser

EXPOSE 8000

CMD ["uvicorn", "ocr_processor.presentation.main:app", "--host", "0.0.0.0", "--port", "8000"]
