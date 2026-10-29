# app_server/services/remove_watermark_service.py
"""去水印服务。

三种策略（A/B/C）：
    A. 按文字内容去除   — 用户输入水印文字，找到后用背景色填充删除
    B. 按样式特征识别   — 自动检测疑似水印（暂未实现）
    C. 图像处理修复     — 图片水印 inpainting（暂未实现）
"""
import time
from collections import Counter
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


# ==================== 背景色采样 ====================
def _sample_bg_color(page: fitz.Page, rect: fitz.Rect) -> tuple:
    """从矩形外围采样出现频率最高的颜色作为背景色。"""
    try:
        margin = 3
        outer = fitz.Rect(
            rect.x0 - margin, rect.y0 - margin,
            rect.x1 + margin, rect.y1 + margin,
        ) & page.rect
        if outer.is_empty:
            return (1, 1, 1)

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=outer, alpha=False)
        samples = pix.samples
        w, h = pix.width, pix.height
        if w < 2 or h < 2:
            return (1, 1, 1)

        pixels = []
        for x in range(w):
            for y_idx in (0, h - 1):
                idx = (y_idx * w + x) * 3
                pixels.append((samples[idx], samples[idx+1], samples[idx+2]))
        for y in range(h):
            for x_idx in (0, w - 1):
                idx = (y * w + x_idx) * 3
                pixels.append((samples[idx], samples[idx+1], samples[idx+2]))

        if not pixels:
            return (1, 1, 1)
        most = Counter(pixels).most_common(1)[0][0]
        return (most[0] / 255.0, most[1] / 255.0, most[2] / 255.0)
    except Exception:
        return (1, 1, 1)


# ==================== 策略 A：按文字内容去除 ====================
def remove_A_by_text(
    src: fitz.Document,
    text: str,
    target_pages: list[int],
    output_dir: Path,
    safe_name: str,
    fill_mode: str = "auto",       # auto | white | custom
    custom_color: tuple = (1, 1, 1),
) -> dict:
    """按文字内容查找水印并删除。

    fill_mode:
        auto   — 自动采样周围背景色填充（推荐）
        white  — 用纯白填充
        custom — 用户指定颜色
    """
    if not text or not text.strip():
        raise ValueError("请输入要去除的水印文字")

    if fill_mode not in ("auto", "white", "custom"):
        raise ValueError(f"不支持的填充模式: {fill_mode}")

    removed_count = 0
    pages_affected = 0

    for pno in target_pages:
        page = src.load_page(pno)
        rects = page.search_for(text)
        if not rects:
            continue

        # 预处理：确定每个位置要用的填充色
        fills: list[tuple] = []
        for r in rects:
            if fill_mode == "auto":
                color = _sample_bg_color(page, r)
            elif fill_mode == "white":
                color = (1, 1, 1)
            else:
                color = custom_color
            fills.append((r, color))

        # 第一步：用背景色标记要删除的区域
        for r, color in fills:
            page.add_redact_annot(r, fill=color)

        try:
            page.apply_redactions(images=0, graphics=0, text=0)
        except Exception:
            continue

        # 第二步：再次用背景色画一次，确保完全遮盖
        for r, color in fills:
            try:
                page.draw_rect(
                    r,
                    color=None,
                    fill=color,
                    overlay=True,
                )
            except Exception:
                pass

        removed_count += len(rects)
        pages_affected += 1

    if removed_count == 0:
        raise ValueError(f"未找到「{text}」，无法去除。请确认水印文字是否正确。")

    base = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_no_watermark_{ts}.pdf"
    src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {
        "out_name": out_name,
        "removed_count": removed_count,
        "pages_affected": pages_affected,
        "strategy": "A",
        "strategy_label": "按文字内容去除",
    }


# ==================== 策略 B：按样式特征识别（占位） ====================
def remove_B_by_style(
    src: fitz.Document, output_dir: Path, safe_name: str,
) -> dict:
    """自动检测疑似水印的文字对象。

    启发式规则（TODO）：
        1. 颜色偏淡（RGB 各通道 > 180）
        2. 旋转角度非 0 或 90
        3. 同一文字在页面上重复出现 ≥ 3 次
        4. 字号明显大于正文
    """
    raise RuntimeError(
        "方案 B（按样式特征自动识别水印）暂未实现。"
        "当前请使用方案 A，手动输入水印文字。"
    )


# ==================== 策略 C：图像处理（占位） ====================
def remove_C_image(
    src: fitz.Document, output_dir: Path, safe_name: str,
) -> dict:
    """图片水印/扫描件水印修复。

    TODO:
        1. 检测水印区域（可结合用户框选）
        2. 用 cv2.inpaint 或 LaMa 模型修复
        3. 需要 GPU 或模型文件（约 200MB）
    """
    raise RuntimeError(
        "方案 C（图像修复）暂未实现。\n"
        "图片水印和扫描件水印无法完美去除——这是业界难题。\n"
        "建议：联系 PDF 来源方重新生成无水印版本。"
    )


# ==================== 分发入口 ====================
def dispatch_remove_watermark(
    src: fitz.Document,
    output_dir: Path,
    safe_name: str,
    strategy: str = "auto",
    text: str = "",
    target_pages: list[int] | None = None,
    fill_mode: str = "auto",
    custom_color: tuple = (1, 1, 1),
) -> dict:
    if target_pages is None:
        target_pages = list(range(src.page_count))

    if strategy == "A" or strategy == "auto":
        return remove_A_by_text(
            src, text, target_pages, output_dir, safe_name,
            fill_mode=fill_mode, custom_color=custom_color,
        )
    if strategy == "B":
        return remove_B_by_style(src, output_dir, safe_name)
    if strategy == "C":
        return remove_C_image(src, output_dir, safe_name)

    raise ValueError(f"未知策略: {strategy}")