# app_server/routers/pdf_merge_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from typing import List
from pathlib import Path
import fitz
import time

from app_server.core.dependencies import get_current_user
from app_server.core.utils import sanitize_filename, parse_page_ranges
from app_server.services.storage_service import session_scope


router = APIRouter(prefix="/api", tags=["pdf-merge"])


@router.post("/pdf-merge")
async def pdf_merge(
    files: List[UploadFile] = File(...),
    page_ranges: List[str] = Form([]),
    output_name: str = Form(""),
    user: dict = Depends(get_current_user),
):
    if not files:
        raise HTTPException(400, "请至少上传一个 PDF 文件")
    if len(files) < 2:
        raise HTTPException(400, "至少需要 2 个 PDF 文件才能合并")

    with session_scope(user["dir_name"], "pdf-merge") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        # ---- 1. 保存所有上传文件 ----
        saved: list[tuple[str, bytes]] = []
        for f in files:
            data = await f.read()
            if not data:
                continue
            safe = (f.filename or "input.pdf").replace("/", "_").replace("\\", "_")
            (input_dir / safe).write_bytes(data)
            saved.append((safe, data))

        if len(saved) < 2:
            raise HTTPException(400, "至少需要 2 个有效的 PDF 文件")

        # ---- 2. 打开所有 PDF ----
        docs: list[tuple[str, fitz.Document]] = []
        try:
            for name, data in saved:
                try:
                    d = fitz.open(stream=data, filetype="pdf")
                except Exception as e:
                    raise HTTPException(400, f"无法打开「{name}」: {e}")

                if d.is_encrypted and not d.is_form_pdf:
                    try:
                        d.authenticate("")
                    except Exception:
                        d.close()
                        raise HTTPException(400, f"「{name}」已加密，请先解密")

                if d.page_count == 0:
                    d.close()
                    raise HTTPException(400, f"「{name}」没有页面")

                docs.append((name, d))

            # ---- 3. 按顺序合并 ----
            merged = fitz.open()
            total_pages = 0
            try:
                for i, (name, d) in enumerate(docs):
                    spec = page_ranges[i] if i < len(page_ranges) else ""
                    if not spec or not spec.strip():
                        merged.insert_pdf(d)
                        total_pages += d.page_count
                    else:
                        try:
                            valid, _oor = parse_page_ranges(spec, d.page_count)
                        except ValueError as e:
                            raise HTTPException(400, f"文件「{name}」页码错误: {e}")
                        for p in valid:
                            merged.insert_pdf(d, from_page=p, to_page=p)
                        total_pages += len(valid)

                # ---- 4. 保存 ----
                ts = time.strftime("%Y%m%d_%H%M%S")
                if output_name.strip():
                    stem = output_name.strip()
                    if stem.lower().endswith(".pdf"):
                        stem = stem[:-4]
                    safe_stem = sanitize_filename(stem, default="merged")
                    out_name = f"{safe_stem}.pdf"
                else:
                    out_name = f"merged_{ts}.pdf"

                merged.save(str(output_dir / out_name))
            finally:
                merged.close()

            return {
                "message": f"合并完成（{len(saved)} 个文件 → {total_pages} 页）",
                "session_id": session_id,
                "output_files": [out_name],
                "page_count": total_pages,
                "file_count": 1,
            }
        finally:
            for _, d in docs:
                try:
                    d.close()
                except Exception:
                    pass