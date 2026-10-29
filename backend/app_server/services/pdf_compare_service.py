# app_server/services/pdf_compare_service.py
"""PDF 对比服务。

三种策略（A/B/C）：
    A. 文本对比     — 逐页提取文字，用 difflib 比较差异（最简单）
    B. 视觉对比     — 逐页渲染成图，像素级对比（暂未实现）
    C. 结构对比     — 对象/书签/元数据对比（暂未实现）
"""
import difflib
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


# ==================== 策略 A：文本对比 ====================
def compare_A_text(
    pdf1_path: Path,
    pdf2_path: Path,
    output_dir: Path,
    base_name1: str,
    base_name2: str,
) -> dict:
    """逐页提取文字，比较差异。生成一份文本报告。"""
    try:
        doc1 = fitz.open(str(pdf1_path))
        doc2 = fitz.open(str(pdf2_path))
    except Exception as e:
        raise RuntimeError(f"无法打开 PDF: {e}")

    try:
        n1, n2 = doc1.page_count, doc2.page_count
        max_pages = max(n1, n2)

        lines = []
        lines.append(f"=== PDF 对比报告 ===")
        lines.append(f"文件 A: {base_name1}（{n1} 页）")
        lines.append(f"文件 B: {base_name2}（{n2} 页）")
        lines.append("")

        if n1 != n2:
            lines.append(f"⚠️ 页数不同：{n1} vs {n2}")
            lines.append("")

        diff_pages = 0
        same_pages = 0

        for i in range(max_pages):
            t1 = doc1[i].get_text() if i < n1 else ""
            t2 = doc2[i].get_text() if i < n2 else ""

            if t1 == t2:
                same_pages += 1
                continue

            diff_pages += 1
            lines.append(f"--- 第 {i+1} 页 ---")

            diff = list(difflib.unified_diff(
                t1.splitlines(),
                t2.splitlines(),
                fromfile=f"A-第{i+1}页",
                tofile=f"B-第{i+1}页",
                lineterm="",
                n=1,
            ))

            if not diff:
                lines.append("（内容相同，仅格式差异）")
            else:
                # 单页差异最多显示 100 行，防止报告过大
                for dline in diff[:100]:
                    lines.append(dline)
                if len(diff) > 100:
                    lines.append(f"...（本页还有 {len(diff) - 100} 行差异）")
            lines.append("")

        lines.append("=== 总结 ===")
        lines.append(f"相同页数：{same_pages}")
        lines.append(f"差异页数：{diff_pages}")

        ts = time.strftime("%Y%m%d_%H%M%S")
        out_name = f"compare_report_{ts}.txt"
        (output_dir / out_name).write_text("\n".join(lines), encoding="utf-8")

        return {
            "out_name": out_name,
            "pages_total": max_pages,
            "pages_same": same_pages,
            "pages_diff": diff_pages,
            "strategy": "A",
            "strategy_label": "文本对比（difflib）",
        }
    finally:
        doc1.close()
        doc2.close()


# ==================== 策略 B：视觉对比（占位） ====================
def compare_B_visual(pdf1_path: Path, pdf2_path: Path, output_dir: Path,
                    base_name1: str, base_name2: str) -> dict:
    """逐页渲染成图，用图像差异算法对比。

    TODO:
        1. 逐页渲染成 PNG（150 DPI）
        2. 用 PIL.ImageChops.difference 或 SSIM 计算差异
        3. 生成差异热力图 + 汇总报告
    """
    raise RuntimeError("方案 B（视觉对比）暂未实现。")


# ==================== 策略 C：结构对比（占位） ====================
def compare_C_structure(pdf1_path: Path, pdf2_path: Path, output_dir: Path,
                       base_name1: str, base_name2: str) -> dict:
    """对比元数据、书签、页面尺寸、字体等结构信息。

    TODO:
        1. 提取 doc.metadata / doc.get_toc() / page.rect
        2. 逐项 diff
        3. 输出 JSON 报告
    """
    raise RuntimeError("方案 C（结构对比）暂未实现。")


# ==================== 分发入口 ====================
def dispatch_pdf_compare(
    pdf1_path: Path,
    pdf2_path: Path,
    output_dir: Path,
    safe_name1: str,
    safe_name2: str,
    strategy: str = "auto",
) -> dict:
    base1 = sanitize_filename(Path(safe_name1).stem, default="A")
    base2 = sanitize_filename(Path(safe_name2).stem, default="B")

    if strategy == "A":
        return compare_A_text(pdf1_path, pdf2_path, output_dir, base1, base2)
    if strategy == "B":
        return compare_B_visual(pdf1_path, pdf2_path, output_dir, base1, base2)
    if strategy == "C":
        return compare_C_structure(pdf1_path, pdf2_path, output_dir, base1, base2)

    # auto：先试 A
    return compare_A_text(pdf1_path, pdf2_path, output_dir, base1, base2)