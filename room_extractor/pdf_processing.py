from __future__ import annotations

import itertools
from pathlib import Path
from typing import Iterable, Iterator, Tuple

import pdfplumber


def extract_pdf_pages(pdf_dir: Path, max_pages: int | None = None) -> Iterator[Tuple[Path, int, str]]:
    pdf_paths = sorted(
        [p for p in pdf_dir.rglob("*.pdf") if p.is_file()],
        key=lambda p: (str(p.parent), p.name),
    )
    for pdf_path in pdf_paths:
        with pdfplumber.open(pdf_path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                if max_pages is not None and index > max_pages:
                    break
                text = page.extract_text(x_tolerance=1.5, y_tolerance=1.5)
                if text:
                    text = text.strip()
                if not text:
                    text = _ocr_page(page)
                yield pdf_path, index, text or ""


def _ocr_page(page) -> str:
    try:
        import numpy as np  # noqa: F401
        from PIL import Image
        import pytesseract
    except Exception:
        return ""

    try:
        page_image = page.to_image(resolution=300)
        pil_image = Image.fromarray(page_image.original)
        text = pytesseract.image_to_string(pil_image, config="--psm 6")
        return text.strip()
    except Exception:
        return ""
