# app_server/services/pdf_bookmark_service.py
"""PDF 书签/目录编辑。"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


def add_bookmarks(
    src: fitz.Document,
    output_dir: Path,
    safe_name: str,
    bookmarks_text: str,
) -> dict:
    """bookmarks_text 格式（每行）：
        <2空格×层级><页码> <标题>

    例：
        1 第一章
          3 第一节
          8 第二节
        2 第九章
    """
    if not bookmarks_text or not bookmarks_text.strip():
        raise ValueError("书签内容不能为空")

    total = src.page_count
    toc: list[list] = []

    for lineno, raw_line in enumerate(bookmarks_text.splitlines(), start=1):
        if not raw_line.strip():
            continue

        # 计算前导空格数 → 层级
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        level = max(1, indent // 2 + 1)

        parts = raw_line.strip().split(None, 1)
        if len(parts) < 2:
            raise ValueError(f"第 {lineno} 行格式错误：需要「页码 标题」")

        try:
            page_no = int(parts[0])
        except ValueError:
            raise ValueError(f"第 {lineno} 行页码不是整数：{parts[0]}")

        if not (1 <= page_no <= total):
            raise ValueError(
                f"第 {lineno} 行页码 {page_no} 超出范围（1~{total}）"
            )

        toc.append([level, parts[1].strip(), page_no])

    if not toc:
        raise ValueError("没有有效的书签")

    src.set_toc(toc)

    base = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_bookmarked_{ts}.pdf"
    src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {"out_name": out_name, "count": len(toc)}