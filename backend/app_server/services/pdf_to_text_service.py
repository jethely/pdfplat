# app_server/services/pdf_to_text_service.py
"""PDF 转纯文本。"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


def pdf_to_text(
    src: fitz.Document,
    output_dir: Path,
    safe_name: str,
    with_page_sep: bool = True,
) -> dict:
    lines = []
    for i in range(src.page_count):
        if with_page_sep:
            lines.append(f"========== 第 {i+1} 页 ==========")
        lines.append(src[i].get_text())
        lines.append("")

    text = "\n".join(lines)

    base = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_{ts}.txt"
    (output_dir / out_name).write_text(text, encoding="utf-8")

    return {
        "out_name": out_name,
        "chars": len(text),
        "pages": src.page_count,
    }