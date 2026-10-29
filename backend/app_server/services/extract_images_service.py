# app_server/services/extract_images_service.py
"""PDF 提取图片服务。

三种策略（A/B/C）：
    A. 提取原图     — 提取所有内嵌图片原始文件，不去重（最简单）
    B. 去重提取     — 按图像 hash 去重（暂未实现）
    C. 智能提取     — 去重 + 位置报告 + 低清过滤（暂未实现）
"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


# ==================== 策略 A：提取原图 ====================
def extract_A_raw(src: fitz.Document, output_dir: Path, base_name: str) -> dict:
    """提取所有内嵌图片的原始文件（png/jpg/...）。"""
    seen_xrefs: set[int] = set()
    out_files: list[str] = []
    total_found = 0

    for pno in range(src.page_count):
        page = src.load_page(pno)
        try:
            images = page.get_images(full=True)
        except Exception:
            continue

        for idx, img in enumerate(images):
            try:
                xref = img[0]
            except Exception:
                continue

            total_found += 1
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                base = src.extract_image(xref)
            except Exception:
                continue

            if not base or not base.get("image"):
                continue

            ext = base.get("ext", "png") or "png"
            data = base["image"]
            name = f"{base_name}_p{pno+1:03d}_{xref:04d}.{ext}"
            (output_dir / name).write_bytes(data)
            out_files.append(name)

    if total_found == 0:
        raise RuntimeError("该 PDF 没有可提取的图片。")

    if not out_files:
        raise RuntimeError("找到图片引用，但无法提取（可能是破损文件）。")

    return {
        "out_names": out_files,
        "count_found": total_found,
        "count_saved": len(out_files),
        "strategy": "A",
        "strategy_label": "提取原图（不去重）",
    }


# ==================== 策略 B：去重提取（占位） ====================
def extract_B_dedup(src: fitz.Document, output_dir: Path, base_name: str) -> dict:
    """按图像内容 hash 去重。

    TODO:
        1. 对每张图的 bytes 计算 md5
        2. 相同 hash 只保存一份
        3. 生成引用清单（哪些页用了哪张图）
    """
    raise RuntimeError("方案 B（去重提取）暂未实现。")


# ==================== 策略 C：智能提取（占位） ====================
def extract_C_smart(src: fitz.Document, output_dir: Path, base_name: str) -> dict:
    """去重 + 位置信息 + 低清过滤。

    TODO:
        1. 去重
        2. 记录每张图出现的位置（页码 + bbox）
        3. 过滤掉过小的图（如 1x1 像素的占位图）
        4. 输出 JSON 清单
    """
    raise RuntimeError("方案 C（智能提取）暂未实现。")


# ==================== 分发入口 ====================
def dispatch_extract_images(
    src: fitz.Document,
    output_dir: Path,
    safe_name: str,
    strategy: str = "auto",
) -> dict:
    base = sanitize_filename(Path(safe_name).stem, default="images")

    if strategy == "A":
        return extract_A_raw(src, output_dir, base)
    if strategy == "B":
        return extract_B_dedup(src, output_dir, base)
    if strategy == "C":
        return extract_C_smart(src, output_dir, base)

    # auto 先走 A
    return extract_A_raw(src, output_dir, base)