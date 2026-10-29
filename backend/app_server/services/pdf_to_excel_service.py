# app_server/services/pdf_to_excel_service.py
"""PDF 转 Excel 服务。

三种策略（A/B/C）：
    A. pdfplumber     — 提取文本型 PDF 的规则表格，纯 Python 依赖
    B. camelot-py     — 复杂边框/无边框表格（暂未实现）
    C. OCR 表格识别    — 扫描件表格（暂未实现）
"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


# ==================== 策略 A：pdfplumber ====================
def convert_A_pdfplumber(
    pdf_path: Path,
    output_dir: Path,
    base_name: str,
    per_page_sheet: bool = True,
) -> dict:
    """用 pdfplumber 提取所有表格，写入 xlsx。

    per_page_sheet=True：每个 PDF 页 → Excel 一个 Sheet
    per_page_sheet=False：所有页的表格汇总到 Sheet1
    """
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError(
            "服务器未安装 pdfplumber，请执行：pip install pdfplumber"
        )

    try:
        from openpyxl import Workbook
    except ImportError:
        raise RuntimeError(
            "服务器未安装 openpyxl，请执行：pip install openpyxl"
        )

    wb = Workbook()
    # 删掉默认 Sheet
    default_sheet = wb.active
    wb.remove(default_sheet)

    total_tables = 0
    total_rows = 0
    pages_with_tables = 0

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            if per_page_sheet:
                for pno, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    if not tables:
                        continue
                    pages_with_tables += 1
                    sheet = wb.create_sheet(title=f"第{pno+1}页")

                    row_cursor = 0
                    for t_idx, table in enumerate(tables):
                        # 表格间空一行
                        if t_idx > 0:
                            row_cursor += 1

                        for row in table:
                            row_cursor += 1
                            for c_idx, cell in enumerate(row):
                                # 处理 None 和换行
                                v = "" if cell is None else str(cell).strip()
                                sheet.cell(
                                    row=row_cursor,
                                    column=c_idx + 1,
                                    value=v,
                                )
                            total_rows += 1
                        total_tables += 1
            else:
                # 单 Sheet 汇总
                sheet = wb.create_sheet(title="表格汇总")
                row_cursor = 0
                for pno, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    if not tables:
                        continue
                    pages_with_tables += 1

                    # 页标题
                    row_cursor += 1
                    sheet.cell(row=row_cursor, column=1, value=f"== 第 {pno+1} 页 ==")

                    for table in tables:
                        row_cursor += 1
                        for row in table:
                            row_cursor += 1
                            for c_idx, cell in enumerate(row):
                                v = "" if cell is None else str(cell).strip()
                                sheet.cell(row=row_cursor, column=c_idx + 1, value=v)
                            total_rows += 1
                        total_tables += 1
    except Exception as e:
        raise RuntimeError(f"pdfplumber 解析失败: {e}")

    if total_tables == 0:
        raise RuntimeError(
            "该 PDF 中没有检测到表格。"
            "可能原因：① 表格无边框且列间距不规律；"
            "② PDF 是扫描件（需要 OCR）；"
            "③ 表格以图片形式嵌入。"
        )

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base_name}_tables_{ts}.xlsx"
    out_path = output_dir / out_name
    wb.save(str(out_path))

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("xlsx 文件生成失败")

    return {
        "out_name": out_name,
        "table_count": total_tables,
        "row_count": total_rows,
        "pages_with_tables": pages_with_tables,
        "strategy": "A",
        "strategy_label": "pdfplumber（规则表格）",
    }


# ==================== 策略 B：camelot（占位） ====================
def convert_B_camelot(
    pdf_path: Path, output_dir: Path, base_name: str,
) -> dict:
    """用 camelot 提取复杂表格。

    TODO:
        1. pip install camelot-py[cv]
        2. 依赖 ghostscript / opencv（部分已装）
        3. camelot.read_pdf(pdf_path, flavor='lattice'/'stream')
    """
    raise RuntimeError("方案 B（camelot 复杂表格）暂未实现。")


# ==================== 策略 C：OCR（占位） ====================
def convert_C_ocr(
    pdf_path: Path, output_dir: Path, base_name: str,
) -> dict:
    """扫描件表格识别。

    TODO:
        1. 逐页渲染成图
        2. PaddleOCR / 表格识别模型
        3. 重建 xlsx
    """
    raise RuntimeError("方案 C（OCR 表格识别）暂未实现。")


# ==================== 分发入口 ====================
def dispatch_pdf_to_excel(
    src: fitz.Document,
    pdf_path: Path,
    output_dir: Path,
    safe_name: str,
    strategy: str = "auto",
    per_page_sheet: bool = True,
) -> dict:
    base = sanitize_filename(Path(safe_name).stem, default="output")

    if strategy == "A":
        return convert_A_pdfplumber(pdf_path, output_dir, base, per_page_sheet)
    if strategy == "B":
        return convert_B_camelot(pdf_path, output_dir, base)
    if strategy == "C":
        return convert_C_ocr(pdf_path, output_dir, base)

    # auto：先试 A
    return convert_A_pdfplumber(pdf_path, output_dir, base, per_page_sheet)