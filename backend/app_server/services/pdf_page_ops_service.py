# app_server/services/pdf_page_ops_service.py
"""PDF 页面操作：删除、旋转等。"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


# ==================== 删除页面 ====================
def delete_pages(
    src: fitz.Document,
    target_pages: list[int],       # 0-indexed，要删除的页
    safe_name: str,
    output_dir: Path,
) -> dict:
    """删除指定页面。target_pages 是被删除的页码（0 起）。

    至少保留 1 页。
    """
    total = src.page_count
    delete_set = set(target_pages)

    # 计算保留页
    keep_pages = [i for i in range(total) if i not in delete_set]

    if not keep_pages:
        raise ValueError("不能删除所有页面，至少保留 1 页")

    # 从后往前删（避免索引错位）
    for pno in sorted(delete_set, reverse=True):
        if 0 <= pno < total:
            src.delete_page(pno)

    # 保存
    base_name = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base_name}_pages_deleted_{ts}.pdf"
    src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {
        "out_name": out_name,
        "deleted_count": len(delete_set),
        "remaining_count": len(keep_pages),
    }


# ==================== 提取页面（保留指定页） ====================
def extract_pages(
    src: fitz.Document,
    target_pages: list[int],       # 0-indexed，要保留的页
    safe_name: str,
    output_dir: Path,
) -> dict:
    """只保留 target_pages 指定的页，其他删除。"""
    if not target_pages:
        raise ValueError("请至少保留 1 页")

    new_doc = fitz.open()
    try:
        for pno in target_pages:
            new_doc.insert_pdf(src, from_page=pno, to_page=pno)

        base_name = sanitize_filename(Path(safe_name).stem, default="output")
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_name = f"{base_name}_pages_kept_{ts}.pdf"
        new_doc.save(str(output_dir / out_name), garbage=4, deflate=True)
    finally:
        new_doc.close()

    return {
        "out_name": out_name,
        "kept_count": len(target_pages),
    }


# ==================== 旋转页面 ====================
def rotate_pages(
    src: fitz.Document,
    target_pages: list[int],
    angle: int,                     # 90 / 180 / 270
    safe_name: str,
    output_dir: Path,
) -> dict:
    """旋转指定页面。angle 必须是 90/180/270。"""
    if angle not in (90, 180, 270):
        raise ValueError("旋转角度只能是 90/180/270")

    for pno in target_pages:
        page = src.load_page(pno)
        page.set_rotation((page.rotation + angle) % 360)

    base_name = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base_name}_rotated_{angle}_{ts}.pdf"
    src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {
        "out_name": out_name,
        "pages_processed": len(target_pages),
        "angle": angle,
    }