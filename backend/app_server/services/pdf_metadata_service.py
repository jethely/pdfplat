# app_server/services/pdf_metadata_service.py
"""PDF 元数据编辑。"""
import time
from pathlib import Path

import pymupdf as fitz

from app_server.core.utils import sanitize_filename


METADATA_FIELDS = ("title", "author", "subject", "keywords", "creator", "producer")


def update_metadata(
    src: fitz.Document,
    output_dir: Path,
    safe_name: str,
    *,
    title: str = "",
    author: str = "",
    subject: str = "",
    keywords: str = "",
    creator: str = "",
    producer: str = "",
) -> dict:
    """只更新非空字段，其他保留原值。"""
    old = dict(src.metadata or {})

    new = dict(old)
    updates = {
        "title": title, "author": author, "subject": subject,
        "keywords": keywords, "creator": creator, "producer": producer,
    }
    changed = []
    for k, v in updates.items():
        if v and v.strip():
            new[k] = v.strip()
            changed.append(k)

    if not changed:
        raise ValueError("请至少填写一个字段")

    src.set_metadata(new)

    base = sanitize_filename(Path(safe_name).stem, default="output")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_metadata_{ts}.pdf"
    src.save(str(output_dir / out_name), garbage=4, deflate=True)

    return {
        "out_name": out_name,
        "changed_fields": changed,
    }