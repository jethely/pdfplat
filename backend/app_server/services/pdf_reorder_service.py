# app_server/services/pdf_reorder_service.py
"""PDF 页面重排：按用户指定的顺序重新排列页面。"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


def reorder_pages(
    src: fitz.Document,
    output_dir: Path,
    safe_name: str,
    new_order: list[int],   # 0-indexed 新顺序
) -> dict:
    total = src.page_count
    if len(new_order) != total:
        raise ValueError(f"新顺序必须包含全部 {total} 页")

    seen = set(new_order)
    if len(seen) != total:
        raise ValueError("新顺序中有重复页码")
    if any(p < 0 or p >= total for p in new_order):
        raise ValueError("新顺序中有越界页码")

    src.select(new_order)

    base = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_reordered_{ts}.pdf"
    src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {"out_name": out_name, "pages": total}