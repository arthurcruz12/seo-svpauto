from __future__ import annotations

from io import BytesIO
import os
from pathlib import PurePath

import pymupdf
import pytesseract
from PIL import Image, ImageEnhance, ImageOps, ImageSequence, UnidentifiedImageError


OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "por+eng")
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/tiff", "image/webp"}
MAX_PDF_PAGES = 100
MIN_EMBEDDED_TEXT_CHARS = 30


class OcrValidationError(ValueError):
    """The uploaded content cannot be safely processed as the declared format."""


class OcrExecutionError(RuntimeError):
    """The local OCR engine failed or exceeded its time limit."""


def prepare_image(image: Image.Image) -> Image.Image:
    prepared = ImageOps.exif_transpose(image).convert("RGB")
    if prepared.width < 1800:
        prepared = prepared.resize((prepared.width * 2, prepared.height * 2), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(prepared)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    return ImageEnhance.Contrast(gray).enhance(1.2)


def run_ocr(image: Image.Image) -> str:
    try:
        return pytesseract.image_to_string(
            prepare_image(image),
            lang=OCR_LANGUAGE,
            config="--oem 3 --psm 6",
            timeout=60,
        ).strip()
    except pytesseract.TesseractNotFoundError:
        # O ambiente de desenvolvimento já inclui RapidOCR. Mantemos este
        # fallback local para Windows sem Tesseract, sem enviar dados à cloud.
        from ..local_ocr import extract_image_text

        output = BytesIO()
        image.save(output, format="PNG")
        return extract_image_text(output.getvalue()).strip()
    except RuntimeError as exc:
        raise OcrExecutionError("O OCR local excedeu o tempo limite por página.") from exc
    except pytesseract.TesseractError as exc:
        raise OcrExecutionError("O motor OCR local não conseguiu ler a página.") from exc


def read_pdf(file_bytes: bytes) -> list[dict]:
    try:
        document = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise OcrValidationError("O conteúdo não é um PDF válido.") from exc
    try:
        if document.page_count < 1:
            raise OcrValidationError("O PDF não contém páginas.")
        if document.page_count > MAX_PDF_PAGES:
            raise OcrValidationError(f"O PDF excede o limite de {MAX_PDF_PAGES} páginas.")
        pages = []
        for index, page in enumerate(document):
            embedded = page.get_text("text", sort=True).strip()
            if len(embedded) >= MIN_EMBEDDED_TEXT_CHARS:
                text, method = embedded, "embedded_text"
            else:
                pixmap = page.get_pixmap(dpi=300, colorspace=pymupdf.csRGB, alpha=False)
                try:
                    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                    try:
                        text = run_ocr(image)
                    finally:
                        image.close()
                finally:
                    pixmap = None
                method = "ocr"
            pages.append({"page": index + 1, "method": method, "text": text})
        return pages
    finally:
        document.close()


def read_image(file_bytes: bytes, extension: str) -> list[dict]:
    try:
        with Image.open(BytesIO(file_bytes)) as source:
            frames = list(ImageSequence.Iterator(source)) if extension in {".tif", ".tiff"} else [source]
            pages = []
            for index, frame in enumerate(frames):
                frame_copy = frame.copy()
                try:
                    text = run_ocr(frame_copy)
                finally:
                    frame_copy.close()
                pages.append({"page": index + 1, "method": "ocr", "text": text})
            return pages
    except (UnidentifiedImageError, OSError) as exc:
        raise OcrValidationError("O conteúdo não é uma imagem válida.") from exc


def join_page_texts(pages: list[dict]) -> str:
    return "\n\n".join(f"--- PÁGINA {page['page']} ---\n{page['text']}" for page in pages)


def validate_upload(filename: str, content_type: str | None, file_bytes: bytes) -> str:
    extension = PurePath(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise OcrValidationError("Formato não suportado. Use PDF, PNG, JPG, TIFF ou WEBP.")
    if not file_bytes:
        raise OcrValidationError("O ficheiro está vazio.")
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    accepted_types = {"", "application/octet-stream", "application/pdf"} if extension == ".pdf" else {"", "application/octet-stream", *IMAGE_MIME_TYPES}
    if normalized_type not in accepted_types:
        raise OcrValidationError("O tipo MIME não corresponde ao formato enviado.")
    if extension == ".pdf" and not file_bytes.startswith(b"%PDF"):
        raise OcrValidationError("O conteúdo não corresponde a um PDF.")
    return extension


def read_full_file(filename: str, content_type: str | None, file_bytes: bytes) -> dict:
    safe_filename = PurePath(filename.replace("\\", "/")).name or "documento"
    extension = validate_upload(safe_filename, content_type, file_bytes)
    pages = read_pdf(file_bytes) if extension == ".pdf" else read_image(file_bytes, extension)
    return {
        "filename": safe_filename,
        "content_type": content_type or "application/octet-stream",
        "page_count": len(pages),
        "pages": pages,
        "full_text": join_page_texts(pages),
    }
