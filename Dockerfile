# Stage 1: build dependencies
FROM python:3.11-slim AS builder

# Install system tools needed to build Rust extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install the Rust toolchain (required to compile pdf-inspector)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --default-toolchain stable
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Clone and build pdf-inspector pinned to a specific commit for reproducibility.
RUN git clone https://github.com/firecrawl/pdf-inspector /tmp/pdf-inspector \
    && git -C /tmp/pdf-inspector checkout 6466e5927107a51d9f12243c433400092f38735f
WORKDIR /tmp/pdf-inspector
RUN pip install maturin
RUN maturin build --release --out /tmp/pdf-inspector-wheels
RUN pip install --prefix=/install /tmp/pdf-inspector-wheels/*.whl

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

CMD ["sh", "-c", "uvicorn ocr_processor.presentation.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-4}"]
