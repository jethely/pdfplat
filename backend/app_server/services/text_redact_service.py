# app_server/services/text_redact_service.py
"""文字遮掩/擦除核心逻辑：按 PDF 类型分发处理。

不依赖 FastAPI，直接操作 PyMuPDF 文档。
"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename
from app_server.services.pdf_common import detect_pdf_type
from app_server.services.font_service import match_pdf_font

def _redact_core(
    src: fitz.Document,
    text_to_redact: str,
    target_pages: list[int],
    fill_color: tuple,
    output_dir: Path,
    base_name: str,
    count_skipped: bool = False,
) -> dict:
    """红act 核心逻辑：先删除底层文字，再画纯色矩形保证遮罩清晰。"""
    redacted_count = 0
    pages_with_hits = 0
    skipped_pages: list[int] = []

    for pno in target_pages:
        page = src.load_page(pno)
        rects = page.search_for(text_to_redact)

        if not rects:
            if count_skipped:
                skipped_pages.append(pno + 1)
            continue

        # ---- 1. 标记 + 删除底层文字/图形 ----
        for r in rects:
            page.add_redact_annot(r, fill=fill_color)

        try:
            page.apply_redactions(images=2, graphics=1, text=0)
        except Exception:
            if count_skipped:
                skipped_pages.append(pno + 1)
            continue

        # ---- 2. 画纯色矩形（关键：保证遮罩 100% 不透明）----
        for r in rects:
            # 稍微扩大一点（左右 5%，上下 10%），让遮罩更明显
            expanded = fitz.Rect(
                r.x0 - r.width * 0.05,
                r.y0 - r.height * 0.10,
                r.x1 + r.width * 0.05,
                r.y1 + r.height * 0.10,
            )
            try:
                page.draw_rect(
                    expanded,
                    color=None,           # 不画边框
                    fill=fill_color,      # 纯色填充
                    overlay=True,         # 画在所有内容之上
                )
            except Exception:
                pass

        redacted_count += len(rects)
        pages_with_hits += 1

    out_name = ""
    if redacted_count > 0:
        ts = time.strftime("%Y%m%d_%H%M%S")
        action_tag = "masked" if fill_color == (0, 0, 0) else "erased"
        out_name = f"{base_name}_{action_tag}_{ts}.pdf"
        src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {
        "out_name": out_name,
        "redacted_count": redacted_count,
        "pages_with_hits": pages_with_hits,
        "skipped_pages": skipped_pages,
    }


# ==================== 类型分支 ====================

def handle_text_pdf(
    src: fitz.Document,
    safe_name: str,
    text: str,
    target_pages: list[int],
    fill_color: tuple,
    output_dir: Path,
    pages: str,
) -> dict:
    """text 型：完整处理。"""
    base_name = sanitize_filename(Path(safe_name).stem, default="output")
    r = _redact_core(
        src, text, target_pages, fill_color, output_dir, base_name,
        count_skipped=False,
    )

    if r["redacted_count"] == 0:
        scope = f"第 {pages} 页" if pages.strip() else "全文"
        raise ValueError(f"在{scope}中未找到「{text}」")

    return r


def handle_mixed_pdf(
    src: fitz.Document,
    safe_name: str,
    text: str,
    target_pages: list[int],
    fill_color: tuple,
    output_dir: Path,
    pages: str,
) -> dict:
    """mixed 型：处理有文字层的页，跳过图片页。"""
    base_name = sanitize_filename(Path(safe_name).stem, default="output")
    r = _redact_core(
        src, text, target_pages, fill_color, output_dir, base_name,
        count_skipped=True,
    )

    if r["redacted_count"] == 0:
        scope = f"第 {pages} 页" if pages.strip() else "全文"
        raise ValueError(
            f"在{scope}中未找到「{text}」"
            "（该 PDF 为混合型，目标文字可能位于图片页中）"
        )

    return r


def handle_image_pdf(
    src: fitz.Document,
    text: str,
) -> None:
    """image 型：直接报错。"""
    src.close()
    raise RuntimeError(
        "该 PDF 是扫描件/图片型，无法按文字内容遮掩。"
        "建议：① 使用 OCR 工具先转成可编辑 PDF；"
        "② 在图片上手动打码（用图像处理工具）。"
    )


def handle_unknown_pdf(src: fitz.Document) -> None:
    """unknown 型：报错。"""
    src.close()
    raise RuntimeError(
        "无法识别该 PDF 的内容类型，可能是空白文档或文件已损坏。"
    )


# ==================== 分发入口 ====================

def dispatch_redact(
    src: fitz.Document,
    safe_name: str,
    text: str,
    target_pages: list[int],
    redact_action: str,
    output_dir: Path,
    pages: str,
) -> dict:
    """按 PDF 类型分发。返回统计信息 dict。

    异常：
        ValueError  —— 未找到 / 校验失败
        RuntimeError —— image / unknown 类型
    """
    pdf_type = detect_pdf_type(src)

    # 填充色
    fill_color = (0, 0, 0) if redact_action == "mask" else (1, 1, 1)

    if pdf_type == "text":
        r = handle_text_pdf(
            src, safe_name, text, target_pages, fill_color, output_dir, pages,
        )
        r["pdf_type"] = "text"
        return r

    if pdf_type == "mixed":
        r = handle_mixed_pdf(
            src, safe_name, text, target_pages, fill_color, output_dir, pages,
        )
        r["pdf_type"] = "mixed"
        return r

    if pdf_type == "image":
        handle_image_pdf(src, text)   # 内部 raise

    # unknown
    handle_unknown_pdf(src)           # 内部 raise