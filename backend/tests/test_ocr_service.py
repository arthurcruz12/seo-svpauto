import unittest
from io import BytesIO
from unittest.mock import patch

import pymupdf
from PIL import Image

from backend.app.services.ocr_service import OcrValidationError, join_page_texts, read_full_file


def text_pdf(*texts: str) -> bytes:
    document = pymupdf.open()
    for text in texts:
        page = document.new_page()
        page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def scanned_pdf() -> bytes:
    image = Image.new("RGB", (500, 300), "white")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    image.close()
    document = pymupdf.open()
    page = document.new_page(width=500, height=300)
    page.insert_image(page.rect, stream=image_bytes.getvalue())
    content = document.tobytes()
    document.close()
    return content


class OcrServiceTests(unittest.TestCase):
    def test_rejects_unsupported_empty_and_invalid_content(self):
        with self.assertRaises(OcrValidationError):
            read_full_file("malware.exe", "application/octet-stream", b"x")
        with self.assertRaises(OcrValidationError):
            read_full_file("empty.png", "image/png", b"")
        with self.assertRaises(OcrValidationError):
            read_full_file("fake.pdf", "application/pdf", b"not-pdf")

    def test_reads_all_embedded_pdf_pages_in_order(self):
        result = read_full_file("digital.pdf", "application/pdf", text_pdf("Conteúdo digital da página um com texto suficiente.", "Conteúdo digital da página dois com texto suficiente."))
        self.assertEqual(result["page_count"], 2)
        self.assertEqual([page["method"] for page in result["pages"]], ["embedded_text", "embedded_text"])
        self.assertLess(result["full_text"].index("PÁGINA 1"), result["full_text"].index("PÁGINA 2"))

    @patch("backend.app.services.ocr_service.run_ocr", return_value="Texto reconhecido por OCR")
    def test_reads_scanned_pdf_with_ocr(self, run_ocr):
        result = read_full_file("scan.pdf", "application/pdf", scanned_pdf())
        self.assertEqual(result["pages"][0]["method"], "ocr")
        self.assertEqual(result["pages"][0]["text"], "Texto reconhecido por OCR")
        run_ocr.assert_called_once()

    @patch("backend.app.services.ocr_service.run_ocr", return_value="Imagem reconhecida")
    def test_reads_jpg_and_png(self, _run_ocr):
        for image_format, filename, mime in [("JPEG", "foto.jpg", "image/jpeg"), ("PNG", "foto.png", "image/png")]:
            image = Image.new("RGB", (200, 100), "white")
            output = BytesIO()
            image.save(output, format=image_format)
            image.close()
            result = read_full_file(filename, mime, output.getvalue())
            self.assertEqual(result["page_count"], 1)
            self.assertEqual(result["pages"][0]["method"], "ocr")

    @patch("backend.app.services.ocr_service.run_ocr", side_effect=["TIFF página 1", "TIFF página 2"])
    def test_reads_multipage_tiff(self, _run_ocr):
        first = Image.new("RGB", (200, 100), "white")
        second = Image.new("RGB", (200, 100), "black")
        output = BytesIO()
        first.save(output, format="TIFF", save_all=True, append_images=[second])
        first.close(); second.close()
        result = read_full_file("arquivo.tiff", "image/tiff", output.getvalue())
        self.assertEqual(result["page_count"], 2)
        self.assertEqual([page["text"] for page in result["pages"]], ["TIFF página 1", "TIFF página 2"])
        self.assertEqual(result["full_text"], join_page_texts(result["pages"]))


if __name__ == "__main__":
    unittest.main()
