# app_server/services/pdf_nup_service.py
"""N-up：把 N 个原始页面缩小，排列到一页。"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


PAPER_SIZES = {
    "A4":     (595, 842),
    "A3":     (842, 1191),
    "Letter": (612, 792),
}

# n → (列数, 行数)
LAYOUTS = {
    2: (1, 2),   # 一列两行
    4: (2, 2),
    6: (2, 3),
    9: (3, 3),
}


def n_up(
    src: fitz.Document,
    output_dir: Path,
    safe_name: str,
    n_per_page: int = 4,
    paper: str = "A4",
    margin: float = 10,
    gap: float = 6,
) -> dict:
    if n_per_page not in LAYOUTS:
        raise ValueError(f"不支持的每页份数: {n_per_page}（可选：2/4/6/9）")
    if paper not in PAPER_SIZES:
        raise ValueError(f"不支持的纸张: {paper}（可选：A4/A3/Letter）")

    cols, rows = LAYOUTS[n_per_page]
    paper_w, paper_h = PAPER_SIZES[paper]

    new_doc = fitz.open()
    total = src.page_count
    out_pages = 0

    for start in range(0, total, n_per_page):
        page = new_doc.new_page(width=paper_w, height=paper_h)

        # 可用区域
        avail_w = paper_w - 2 * margin
        avail_h = paper_h - 2 * margin

        # 单元格大小
        cell_w = (avail_w - gap * (cols - 1)) / cols
        cell_h = (avail_h - gap * (rows - 1)) / rows

        for k in range(n_per_page):
            idx = start + k
            if idx >= total:
                break

            col = k % cols
            row = k // cols

            x0 = margin + col * (cell_w + gap)
            y0 = margin + row * (cell_h + gap)
            x1 = x0 + cell_w
            y1 = y0 + cell_h

            try:
                page.show_pdf_page(
                    fitz.Rect(x0, y0, x1, y1),
                    src,
                    idx,
                    keep_proportion=True,
                )
            except Exception:
                continue

        out_pages += 1

    base = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_nup{n_per_page}_{paper}_{ts}.pdf"
    new_doc.save(str(output_dir / out_name), garbage=4, deflate=True)
    new_doc.close()

    return {
        "out_name": out_name,
        "in_pages": total,
        "out_pages": out_pages,
        "n_per_page": n_per_page,
    }