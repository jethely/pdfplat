# app_server/services/pdf_to_long_image_service.py
"""多页 PDF 竖向拼接成长图。"""
import io
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


# 拼接后最大像素高度（防止内存爆掉 / 图片打不开）
MAX_HEIGHT_PX = 30000


def pdf_to_long_image(
    src: fitz.Document,
    output_dir: Path,
    safe_name: str,
    dpi: int = 150,
    max_width: int = 0,        # 0 = 用最大页宽
    gap: int = 0,              # 页间空白像素
) -> dict:
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("服务器未安装 Pillow，请执行：pip install Pillow")

    if not (36 <= dpi <= 600):
        raise ValueError("DPI 需在 36~600 之间")

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    page_images: list = []
    for i in range(src.page_count):
        page = src.load_page(i)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        page_images.append(img)

    if not page_images:
        raise ValueError("PDF 没有页面")

    # 目标宽度
    target_w = max_width if max_width > 0 else max(img.width for img in page_images)

    # 按目标宽度等比缩放每页
    resized = []
    for img in page_images:
        if img.width != target_w:
            ratio = target_w / img.width
            new_h = int(img.height * ratio)
            img = img.resize((target_w, new_h), Image.LANCZOS)
        resized.append(img)

    # 总高度
    total_h = sum(img.height for img in resized) + gap * (len(resized) - 1)
    if total_h > MAX_HEIGHT_PX:
        raise ValueError(
            f"拼接后高度过大（{total_h}px > {MAX_HEIGHT_PX}px）。"
            f"请降低 DPI 或分批处理。"
        )

    # 拼接
    long_img = Image.new("RGB", (target_w, total_h), "white")
    y = 0
    for idx, img in enumerate(resized):
        x = (target_w - img.width) // 2
        long_img.paste(img, (x, y))
        y += img.height
        if gap and idx < len(resized) - 1:
            y += gap

    base = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_long_{dpi}dpi_{ts}.png"
    long_img.save(str(output_dir / out_name), "PNG", optimize=True)

    return {
        "out_name": out_name,
        "pages": src.page_count,
        "width": target_w,
        "height": total_h,
    }