from __future__ import annotations

from pathlib import Path
from typing import List

from langchain_core.documents import Document
from pdf2image import convert_from_path
from pypdf import PdfReader
import pytesseract

from backend.config import settings


class OCRUnavailableError(RuntimeError):
    pass


def _run_ocr(file_path: Path, page_number: int) -> str:
    try:
        images = convert_from_path(
            str(file_path),
            first_page=page_number,
            last_page=page_number,
        )
    except Exception as exc:
        raise OCRUnavailableError(
            "OCR fallback requires poppler. Install it locally and ensure "
            "`pdftoppm` is available on PATH."
        ) from exc

    if not images:
        return ""

    try:
        return pytesseract.image_to_string(
            images[0],
            lang=settings.ocr_language,
        ).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailableError(
            "OCR fallback requires Tesseract OCR. Install `tesseract` locally "
            "and make sure it is available on PATH."
        ) from exc


def _build_document(
    file_path: Path,
    page_number: int,
    text: str,
    extraction_method: str,
) -> Document:
    return Document(
        page_content=text,
        metadata={
            "source": file_path.name,
            "page": page_number,
            "extraction_method": extraction_method,
        },
    )


def parse_pdf(file_path: Path) -> List[Document]:
    reader = PdfReader(str(file_path))
    documents: List[Document] = []

    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            documents.append(
                _build_document(
                    file_path=file_path,
                    page_number=index,
                    text=text,
                    extraction_method="text",
                )
            )
            continue

        ocr_text = _run_ocr(file_path, index)
        if not ocr_text:
            continue

        documents.append(
            _build_document(
                file_path=file_path,
                page_number=index,
                text=ocr_text,
                extraction_method="ocr",
            )
        )

    return documents
