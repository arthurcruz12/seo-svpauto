from __future__ import annotations

from collections import OrderedDict
from hashlib import sha256
from io import BytesIO
from threading import Lock

import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from rapidocr_onnxruntime import RapidOCR


_engine: RapidOCR | None = None
_engine_lock = Lock()
_inference_lock = Lock()
_cache_lock = Lock()
_text_cache: OrderedDict[str, str] = OrderedDict()
_CACHE_ITEMS = 24


def _get_engine() -> RapidOCR:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = RapidOCR()
    return _engine


def _cached(key: str) -> str | None:
    with _cache_lock:
        value = _text_cache.get(key)
        if value is not None:
            _text_cache.move_to_end(key)
        return value


def _store(key: str, value: str) -> str:
    with _cache_lock:
        _text_cache[key] = value
        _text_cache.move_to_end(key)
        while len(_text_cache) > _CACHE_ITEMS:
            _text_cache.popitem(last=False)
    return value


def _resize_for_ocr(image: Image.Image) -> Image.Image:
    longest = max(image.size)
    if longest < 1600:
        scale = min(2.5, 1600 / max(longest, 1))
    elif longest > 3200:
        scale = 3200 / longest
    else:
        return image
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )


def _deskew(gray: np.ndarray) -> np.ndarray:
    points = np.column_stack(np.where(gray < 180))
    if len(points) < 100:
        return gray
    angle = cv2.minAreaRect(points[:, ::-1].astype(np.float32))[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.35 or abs(angle) > 8:
        return gray
    height, width = gray.shape
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(gray, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _prepare_image(image: Image.Image) -> np.ndarray:
    image = _resize_for_ocr(ImageOps.exif_transpose(image).convert("RGB"))
    gray_image = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
    gray_image = ImageEnhance.Contrast(gray_image).enhance(1.25).filter(ImageFilter.SHARPEN)
    return _deskew(np.asarray(gray_image))


def _ordered_result(result) -> tuple[str, float, int]:
    accepted = []
    for item in result or []:
        if len(item) < 3 or float(item[2]) < 0.35:
            continue
        box, text, score = item[0], str(item[1]).strip(), float(item[2])
        if not text:
            continue
        x = min(float(point[0]) for point in box)
        y = min(float(point[1]) for point in box)
        accepted.append((y, x, text, score))
    accepted.sort(key=lambda item: (round(item[0] / 12), item[1]))
    if not accepted:
        return "", 0.0, 0
    return "\n".join(item[2] for item in accepted), sum(item[3] for item in accepted) / len(accepted), len(accepted)


def _run(image: np.ndarray) -> tuple[str, float, int]:
    with _inference_lock:
        result, _ = _get_engine()(image)
    return _ordered_result(result)


def _recognize(image: Image.Image) -> str:
    prepared = _prepare_image(image)
    primary = _run(prepared)
    if primary[1] >= 0.72 and primary[2] >= 3:
        return primary[0]

    # A binarização melhora fotografias com sombras, mas só é executada quando
    # a leitura normal não foi suficientemente segura.
    fallback_image = cv2.adaptiveThreshold(
        prepared,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        41,
        15,
    )
    fallback = _run(fallback_image)
    return fallback[0] if (fallback[1], fallback[2]) > (primary[1], primary[2]) else primary[0]


def extract_image_text(content: bytes) -> str:
    cache_key = f"image:{sha256(content).hexdigest()}"
    if (value := _cached(cache_key)) is not None:
        return value
    with Image.open(BytesIO(content)) as image:
        return _store(cache_key, _recognize(image))


def extract_scanned_pdf_text(content: bytes, max_pages: int = 50) -> str:
    cache_key = f"pdf:{max_pages}:{sha256(content).hexdigest()}"
    if (value := _cached(cache_key)) is not None:
        return value
    document = pdfium.PdfDocument(content)
    try:
        pages = []
        for index in range(min(len(document), max_pages)):
            page = document[index]
            width, height = page.get_size()
            scale = max(1.5, min(3.0, 2400 / max(width, height, 1)))
            bitmap = page.render(scale=scale)
            try:
                pages.append(_recognize(bitmap.to_pil()))
            finally:
                bitmap.close()
        return _store(cache_key, "\n\n".join(page for page in pages if page))
    finally:
        document.close()
