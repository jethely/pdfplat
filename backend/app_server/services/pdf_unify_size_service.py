# app_server/services/pdf_unify_size_service.py
"""把所有页面统一缩放到指定尺寸。"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


PAPER_SIZES = {
    "A4":     (595, 842),
    "A3":     (842, 1191),
    "A5":     (420, 595),
    "Letter": (612, 792),
}


def unify_size(
    src: fitz.Document,
    output_dir: Path,
    safe_name: str,
    target_size: str = "A4",
    orientation: str = "auto",   # auto | portrait | landscape
    fit_mode: str = "fit",       # fit（等比缩放居中） | fill（拉伸铺满）
) -> dict:
    if target_size not in PAPER_SIZES:
        raise ValueError(f"不支持的尺寸: {target_size}")
    if orientation not in ("auto", "portrait", "landscape"):
        raise ValueError(f"不支持的方向: {orientation}")
    if fit_mode not in ("fit", "fill"):
        raise ValueError(f"不支持的适应方式: {fit_mode}")

    base_w, base_h = PAPER_SIZES[target_size]

    new_doc = fitz.open()
    for i in range(src.page_count):
        page = src.load_page(i)
        pw, ph = page.rect.width, page.rect.height

        # 方向
        if orientation == "auto":
            landscape = pw > ph
        elif orientation == "landscape":
            landscape = True
        else:
            landscape = False

        target_w, target_h = (base_h, base_w) if landscape else (base_w, base_h)
        new_page = new_doc.new_page(width=target_w, height=target_h)

        if fit_mode == "fit":
            # 等比缩放，居中留白
            scale = min(target_w / pw, target_h / ph)
            scaled_w = pw * scale
            scaled_h = ph * scale
            x0 = (target_w - scaled_w) / 2
            y0 = (target_h - scaled_h) / 2
            rect = fitz.Rect(x0, y0, x0 + scaled_w, y0 + scaled_h)
        else:
            # 拉伸铺满
            rect = fitz.Rect(0, 0, target_w, target_h)

        try:
            new_page.show_pdf_page(rect, src, i)
        except Exception:
            continue

    base = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_unified_{target_size}_{ts}.pdf"
    new_doc.save(str(output_dir / out_name), garbage=4, deflate=True)
    new_doc.close()

    return {
        "out_name": out_name,
        "pages": src.page_count,
        "target_size": target_size,
    }