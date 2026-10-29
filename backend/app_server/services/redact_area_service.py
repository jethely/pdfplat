# app_server/services/redact_area_service.py
"""按坐标区域遮掩：接收矩形列表，在对应页面画纯色块。"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


# ==================== 生成预览 ====================
def render_previews(
    src: fitz.Document,
    preview_dir: Path,
    target_width: int = 600,
    max_pages: int = 100,
) -> list[dict]:
    """渲染每页缩略图为 JPEG，返回元信息列表。"""
    import base64

    preview_dir.mkdir(parents=True, exist_ok=True)
    pages_meta: list[dict] = []

    total = min(src.page_count, max_pages)

    for i in range(total):
        page = src.load_page(i)
        rect = page.rect
        w_pt, h_pt = rect.width, rect.height

        # 按目标宽度缩放
        scale = target_width / w_pt
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_bytes = pix.tobytes("jpeg", jpg_quality=75)

        # 落盘一份（可选，方便调试）
        (preview_dir / f"page_{i+1:03d}.jpg").write_bytes(img_bytes)

        # base64 给前端
        b64 = base64.b64encode(img_bytes).decode("ascii")

        pages_meta.append({
            "index": i,
            "width_pt": round(w_pt, 2),
            "height_pt": round(h_pt, 2),
            "preview_width": pix.width,
            "preview_height": pix.height,
            "scale": round(w_pt / pix.width, 6),   # 显示坐标 → PDF points
            "preview": f"data:image/jpeg;base64,{b64}",
        })

    return pages_meta


# ==================== 应用圈定图形 ====================
def _point_in_ellipse(px, py, cx, cy, rx, ry) -> bool:
    """判断点 (px,py) 是否在椭圆内。"""
    if rx <= 0 or ry <= 0:
        return False
    return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1.0


def _collect_ellipse_redacts(
    page: fitz.Page,
    x0: float, y0: float, x1: float, y1: float,
    shape: str,
) -> list[fitz.Rect]:
    """找出中心点落在椭圆/圆内的所有词的 bbox。"""
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    if shape == "circle":
        r = min(x1 - x0, y1 - y0) / 2
        rx = ry = r
    else:  # ellipse
        rx = (x1 - x0) / 2
        ry = (y1 - y0) / 2

    rects: list[fitz.Rect] = []
    try:
        words = page.get_text("words")   # [(x0,y0,x1,y1,word,block,line,word_no), ...]
    except Exception:
        return rects

    for w in words:
        try:
            wx0, wy0, wx1, wy1 = w[0], w[1], w[2], w[3]
        except Exception:
            continue
        # 词中心
        wcx = (wx0 + wx1) / 2
        wcy = (wy0 + wy1) / 2
        if _point_in_ellipse(wcx, wcy, cx, cy, rx, ry):
            rects.append(fitz.Rect(wx0, wy0, wx1, wy1))

    # 如果页面没有文字层（扫描件），退化为整个椭圆 bbox（用 draw_oval 覆盖即可）
    if not rects:
        if shape == "circle":
            r = min(x1 - x0, y1 - y0) / 2
            rects.append(fitz.Rect(cx - r, cy - r, cx + r, cy + r))
        else:
            rects.append(fitz.Rect(x0, y0, x1, y1))

    return rects

def apply_rects(
    src: fitz.Document,
    rects: list[dict],
    safe_name: str,
    output_dir: Path,
    fill_mode: str = "black",
    shape: str = "rect",
) -> dict:
    if not rects:
        raise ValueError("请至少选择一个区域")
    if shape not in ("rect", "ellipse", "circle"):
        raise ValueError(f"不支持的形状: {shape}")

    fill_color = (0, 0, 0) if fill_mode == "black" else (1, 1, 1)
    total = src.page_count
    pages_affected: set[int] = set()
    applied = 0

    by_page: dict[int, list[tuple]] = {}
    for r in rects:
        try:
            pno = int(r["page"])
            x0 = float(r["x0"]); y0 = float(r["y0"])
            x1 = float(r["x1"]); y1 = float(r["y1"])
        except (KeyError, ValueError, TypeError):
            continue
        if not (0 <= pno < total):
            continue
        if x0 > x1: x0, x1 = x1, x0
        if y0 > y1: y0, y1 = y1, y0
        by_page.setdefault(pno, []).append((x0, y0, x1, y1))

    for pno, boxes in by_page.items():
        page = src.load_page(pno)

        # ============ 1. 矩形：删文字 + 画黑块 ============
        if shape == "rect":
            # 标记要删除的区域
            for (x0, y0, x1, y1) in boxes:
                page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=fill_color)

            # ⭐ 关键：只删文字，不删图片（images=0），不删矢量图（graphics=0）
            try:
                page.apply_redactions(images=0, graphics=0, text=0)
            except Exception:
                pass

            # 画不透明矩形
            for (x0, y0, x1, y1) in boxes:
                try:
                    page.draw_rect(
                        fitz.Rect(x0, y0, x1, y1),
                        color=None, fill=fill_color, overlay=True,
                    )
                    applied += 1
                    pages_affected.add(pno)
                except Exception:
                    continue

        # ============ 2. 椭圆 / 圆形：只画色块（不做 redact）============
        else:
            for (x0, y0, x1, y1) in boxes:
                try:
                    if shape == "circle":
                        cx = (x0 + x1) / 2
                        cy = (y0 + y1) / 2
                        r = min(x1 - x0, y1 - y0) / 2
                        draw_rect = fitz.Rect(cx - r, cy - r, cx + r, cy + r)
                    else:  # ellipse
                        draw_rect = fitz.Rect(x0, y0, x1, y1)

                    page.draw_oval(
                        draw_rect,
                        color=None,
                        fill=fill_color,
                        overlay=True,   # 画在最顶层，覆盖底层内容
                    )
                    applied += 1
                    pages_affected.add(pno)
                except Exception:
                    continue

    if applied == 0:
        raise ValueError("没有有效的区域")

    base_name = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base_name}_areas_{fill_mode}_{shape}_{ts}.pdf"
    src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {
        "out_name": out_name,
        "applied_count": applied,
        "pages_affected": sorted(p + 1 for p in pages_affected),
    }