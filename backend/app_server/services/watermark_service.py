# app_server/services/watermark_service.py
"""PDF 水印服务：文字水印（支持旋转、平铺、透明度模拟）。"""
import math
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


# ==================== 透明度 → 灰阶混合 ====================
def _blend_with_white(color: tuple, opacity: float) -> tuple:
    """把颜色按透明度混合到白底上（模拟半透明效果）。

    PyMuPDF 的 insert_text 不支持 alpha，用灰阶近似。
    用户看到的就是浅灰色文字，视觉上跟半透明一样。
    """
    r, g, b = color
    return (
        r * opacity + 1.0 * (1 - opacity),
        g * opacity + 1.0 * (1 - opacity),
        b * opacity + 1.0 * (1 - opacity),
    )


# ==================== 单点绘制 ====================
def _draw_one(
    page: fitz.Page,
    text: str,
    anchor: fitz.Point,
    fontsize: float,
    color: tuple,
    rotation: float,
) -> None:
    """在 anchor 点画一个旋转 angle 度的文字（文字中心对齐 anchor）。"""
    try:
        font = fitz.Font("china-s")
        text_width = font.text_length(text, fontsize=fontsize)
    except Exception:
        # 字体不可用时退化为估算
        text_width = len(text) * fontsize * 0.6

    # 未旋转时，让文字中心在 anchor 上
    x0 = anchor.x - text_width / 2
    y0 = anchor.y + fontsize * 0.35   # 让垂直中心大致在 anchor

    # 绕 anchor 旋转
    mat = fitz.Matrix(1, 0, 0, 1, 0, 0).prerotate(rotation)

    try:
        page.insert_text(
            fitz.Point(x0, y0),
            text,
            fontname="china-s",
            fontsize=fontsize,
            color=color,
            morph=(anchor, mat),
        )
    except Exception:
        # 单点失败不影响整体
        pass


# ==================== 位置计算 ====================
def _position_anchors(page: fitz.Page, position: str) -> list[fitz.Point]:
    """返回要绘制水印的锚点列表。"""
    w, h = page.rect.width, page.rect.height

    if position == "tile":
        # 平铺：覆盖整页，间距约为页面的 1/3
        anchors = []
        step_x = w / 3
        step_y = h / 3
        cols = int(w / step_x) + 3
        rows = int(h / step_y) + 3
        for i in range(-1, cols):
            for j in range(-1, rows):
                anchors.append(fitz.Point(i * step_x + step_x / 2,
                                          j * step_y + step_y / 2))
        return anchors

    if position == "center":
        return [fitz.Point(w / 2, h / 2)]
    if position == "top-left":
        return [fitz.Point(w * 0.2, h * 0.15)]
    if position == "top-right":
        return [fitz.Point(w * 0.8, h * 0.15)]
    if position == "bottom-left":
        return [fitz.Point(w * 0.2, h * 0.85)]
    if position == "bottom-right":
        return [fitz.Point(w * 0.8, h * 0.85)]

    # 默认居中
    return [fitz.Point(w / 2, h / 2)]


# ==================== 主入口 ====================
def add_watermark(
    src: fitz.Document,
    text: str,
    *,
    position: str = "center",         # center|top-left|top-right|bottom-left|bottom-right|tile
    rotation: float = 45,
    fontsize: float = 60,
    color: tuple = (0.5, 0.5, 0.5),   # RGB 0~1
    opacity: float = 0.3,
    pages: list[int] | None = None,   # None = 全部页
    safe_name: str = "input.pdf",
    output_dir: Path | None = None,
) -> dict:
    """给 PDF 加水印，保存到 output_dir，返回 out_name 与页数。"""
    # 混合透明度
    draw_color = _blend_with_white(color, opacity)

    if pages is None:
        pages = list(range(src.page_count))

    for pno in pages:
        page = src.load_page(pno)
        anchors = _position_anchors(page, position)
        for anchor in anchors:
            _draw_one(page, text, anchor, fontsize, draw_color, rotation)

    # 保存
    base_name = sanitize_filename(Path(safe_name).stem, default="output")
    import time
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base_name}_watermark_{ts}.pdf"
    src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {
        "out_name": out_name,
        "pages_processed": len(pages),
        "instances_per_page": len(_position_anchors(src.load_page(0), position)),
    }