from dataclasses import dataclass
from pathlib import Path

from ocr_processor.domain.exceptions import OCRProcessingError


@dataclass(frozen=True)
class NativePageExtraction:
    page_number: int
    text: str


def extract_native_pdf_pages(file_path: Path) -> list[NativePageExtraction]:
    """Extract embedded text from each PDF page using PyMuPDF."""
    try:
        import fitz  # type: ignore[import]
    except ImportError as exc:
        raise OCRProcessingError("PyMuPDF is not installed") from exc

    try:
        with fitz.open(file_path) as document:
            return [
                NativePageExtraction(
                    page_number=index + 1,
                    text=_clean_native_text(page.get_text("text")),
                )
                for index, page in enumerate(document)
            ]
    except Exception as exc:  # noqa: BLE001
        raise OCRProcessingError(f"native PDF extraction failed: {exc}") from exc


def render_pdf_pages(file_path: Path, page_numbers: list[int], dpi: int = 250) -> list:
    """Render selected PDF pages to PIL Images for OCR fallback."""
    if not page_numbers:
        return []

    try:
        import fitz  # type: ignore[import]
        from PIL import Image
    except ImportError as exc:
        raise OCRProcessingError("PyMuPDF and Pillow are required to render PDFs") from exc

    scale = dpi / 72
    matrix = fitz.Matrix(scale, scale)
    images = []
    try:
        with fitz.open(file_path) as document:
            for page_number in page_numbers:
                page = document.load_page(page_number - 1)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes(
                    "RGB",
                    (pixmap.width, pixmap.height),
                    pixmap.samples,
                )
                images.append(image)
    except Exception as exc:  # noqa: BLE001
        raise OCRProcessingError(f"PDF rendering failed: {exc}") from exc
    return images


def _clean_native_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines).strip()
