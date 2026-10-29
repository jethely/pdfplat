# app_server/services/pdf_to_word_service.py
"""PDF 转 Word 服务。

三种策略（A/B/C）：
    A. pdf2docx         — 文本型 PDF → docx，效果好，无重依赖
    B. LibreOffice      — 兼容性更广，需安装 LibreOffice（暂未实现）
    C. PaddleOCR        — 处理扫描件，需安装 OCR 依赖（暂未实现）

当前只实现 A。B/C 保留函数骨架，等有需求再填。
"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename
from app_server.services.pdf_common import detect_pdf_type


# ==================== 策略 A：pdf2docx ====================
def pdf_to_word_A_pdf2docx(
    pdf_path: Path,
    output_dir: Path,
    base_name: str,
) -> dict:
    """用 pdf2docx 库转换。适用于文本型 PDF。"""
    try:
        from pdf2docx import Converter
    except ImportError:
        raise RuntimeError(
            "服务器未安装 pdf2docx，请执行：pip install pdf2docx"
        )

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base_name}_{ts}.docx"
    out_path = output_dir / out_name

    cv = None
    try:
        cv = Converter(str(pdf_path))
        cv.convert(str(out_path))
    except Exception as e:
        raise RuntimeError(f"pdf2docx 转换失败: {e}")
    finally:
        if cv is not None:
            try:
                cv.close()
            except Exception:
                pass

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("转换未生成有效的 docx 文件")

    return {
        "out_name": out_name,
        "out_size": out_path.stat().st_size,
        "strategy": "A",
        "strategy_label": "pdf2docx（精确保真）",
    }


# ==================== 策略 B：LibreOffice（占位） ====================
def pdf_to_word_B_libreoffice(
    pdf_path: Path,
    output_dir: Path,
    base_name: str,
) -> dict:
    """用 LibreOffice 命令行转换。

    TODO:
        1. apt install libreoffice
        2. subprocess 调用：soffice --headless --convert-to docx ...
        3. 输出目录参数需要 -env:UserInstallation
    """
    raise RuntimeError(
        "方案 B（LibreOffice）暂未实现。"
        "如需扫描件和复杂 PDF 转换，请联系管理员。"
    )


# ==================== 策略 C：PaddleOCR（占位） ====================
def pdf_to_word_C_ocr(
    pdf_path: Path,
    output_dir: Path,
    base_name: str,
) -> dict:
    """用 PaddleOCR 识别文字，再用 python-docx 重建。

    TODO:
        1. pip install paddleocr paddlepaddle python-docx
        2. 逐页 OCR 出 [(text, bbox, confidence), ...]
        3. 按 bbox 的 y 坐标归行，x 坐标排序
        4. 用 python-docx 逐行写入段落
        5. 处理表格（暂不做）
    """
    raise RuntimeError(
        "方案 C（OCR 扫描件识别）暂未实现。"
        "扫描件转 Word 需要 OCR 支持，敬请期待。"
    )


# ==================== 分发入口 ====================
def dispatch_pdf_to_word(
    src: fitz.Document,
    pdf_path: Path,
    output_dir: Path,
    safe_name: str,
    strategy: str = "auto",     # auto | A | B | C
) -> dict:
    """根据 PDF 类型和用户选择，选择合适策略。

    strategy:
        - "auto"：自动检测 PDF 类型并选最佳策略（推荐）
        - "A" / "B" / "C"：强制使用指定策略

    异常：
        ValueError      —— 参数错误
        RuntimeError    —— 转换失败 / 依赖缺失 / 未实现
    """
    base_name = sanitize_filename(Path(safe_name).stem, default="output")
    pdf_type = detect_pdf_type(src)

    # ---- 强制策略 ----
    if strategy == "A":
        return pdf_to_word_A_pdf2docx(pdf_path, output_dir, base_name)
    if strategy == "B":
        return pdf_to_word_B_libreoffice(pdf_path, output_dir, base_name)
    if strategy == "C":
        return pdf_to_word_C_ocr(pdf_path, output_dir, base_name)

    # ---- auto 模式 ----
    if pdf_type == "text":
        # 文本型：走 A（最精确）
        return pdf_to_word_A_pdf2docx(pdf_path, output_dir, base_name)

    if pdf_type == "mixed":
        # 混合型：A 能处理文字部分，图片部分作为图片嵌入
        try:
            r = pdf_to_word_A_pdf2docx(pdf_path, output_dir, base_name)
            r["warning"] = "该 PDF 为混合型，图片页在 Word 中会以图片形式呈现"
            return r
        except RuntimeError:
            raise

    if pdf_type == "image":
        # 图片型：需要 OCR（方案 C），暂未实现
        raise RuntimeError(
            "该 PDF 是扫描件/图片型，直接转 Word 只能得到一张张图片，无法编辑。"
            "如需识别文字，请使用 OCR 方案（方案 C，暂未实现）。"
            "或者使用 Adobe Acrobat / WPS 等工具的 OCR 功能。"
        )

    if pdf_type == "unknown":
        raise RuntimeError(
            "无法识别该 PDF 的内容类型，可能是空白文档或文件已损坏。"
        )

    raise ValueError(f"未知的 PDF 类型: {pdf_type}")