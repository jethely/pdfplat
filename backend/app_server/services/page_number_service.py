# app_server/services/page_number_service.py
"""PDF 加页码服务：支持多种格式、位置、起始编号。"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


# ==================== 页码格式 ====================
def _format_page_number(
    fmt: str,
    page_idx: int,        # 当前页在 PDF 里的索引（0 起）
    start_number: int,    # 起始编号
    total_pages: int,     # 总页数（用于 x/y 格式）
) -> str:
    """返回该页要显示的文字。"""
    current = start_number + page_idx
    total_display = start_number + total_pages - 1

    if fmt == "n":
        return str(current)
    if fmt == "n/m":
        return f"{current}/{total_display}"
    if fmt == "page-n":
        return f"Page {current}"
    if fmt == "page-n-of-m":
        return f"Page {current} of {total_display}"
    if fmt == "n-m":                     # 1-20
        return f"{current}-{total_display}"
    if fmt == "di-n-ye":                 # 第 N 页
        return f"第 {current} 页"
    if fmt == "di-n-ye-gong-m-ye":       # 第 N 页 / 共 M 页
        return f"第 {current} 页 / 共 {total_display} 页"
    return str(current)


# ==================== 位置计算 ====================
def _calc_position(
    page: fitz.Page,
    text: str,
    fontsize: float,
    position: str,
    margin: float,
) -> tuple[fitz.Point, float]:
    """返回 (左上角绘制点, 文字宽度)。

    位置参数：
        bottom-center | bottom-right | bottom-left
        top-center    | top-right    | top-left
    """
    # 计算文字宽度
    try:
        font = fitz.Font("china-s")
        text_width = font.text_length(text, fontsize=fontsize)
    except Exception:
        # 退化估算（中文按 fontsize 宽度算，英文按 0.5 算）
        text_width = 0
        for ch in text:
            text_width += fontsize if ord(ch) > 127 else fontsize * 0.5

    w, h = page.rect.width, page.rect.height

    # 垂直位置：底部时 y = h - margin；顶部时 y = margin + fontsize
    if position.startswith("bottom"):
        y = h - margin
    else:  # top
        y = margin + fontsize

    # 水平位置
    if position.endswith("center"):
        x = (w - text_width) / 2
    elif position.endswith("right"):
        x = w - margin - text_width
    else:  # left
        x = margin

    return fitz.Point(x, y), text_width


# ==================== 主入口 ====================
def add_page_numbers(
    src: fitz.Document,
    *,
    fmt: str = "n",
    position: str = "bottom-center",
    start_number: int = 1,
    fontsize: float = 8,
    color: tuple = (0, 0, 0),
    margin: float = 30,
    pages: list[int] | None = None,
    safe_name: str = "input.pdf",
    output_dir: Path | None = None,
) -> dict:
    """给 PDF 加页码，保存到 output_dir，返回统计信息。"""
    if pages is None:
        pages = list(range(src.page_count))

    total_pages = len(pages)
    # 页码编号基于「本次要处理的总页数」，页索引对应该页在处理列表中的位置
    for idx, pno in enumerate(pages):
        page = src.load_page(pno)
        text = _format_page_number(fmt, idx, start_number, total_pages)
        point, _w = _calc_position(page, text, fontsize, position, margin)

        try:
            page.insert_text(
                point,
                text,
                fontname="china-s",
                fontsize=fontsize,
                color=color,
            )
        except Exception:
            # 单页失败不影响整体
            pass

    # 保存
    base_name = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base_name}_numbered_{ts}.pdf"
    src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {
        "out_name": out_name,
        "pages_processed": total_pages,
        "sample_text": _format_page_number(fmt, 0, start_number, total_pages),
    }