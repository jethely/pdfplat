# app_server/routers/pdf_compress_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pathlib import Path
import shutil
import time

import pymupdf as fitz

from config.config import settings
from app_server.core.dependencies import get_current_user
from app_server.core.utils import sanitize_filename, format_bytes
from app_server.services.storage_service import session_scope
from app_server.services.ghostscript import run_ghostscript


router = APIRouter(prefix="/api", tags=["pdf-compress"])


@router.post("/pdf-compress")
async def pdf_compress(
    file: UploadFile = File(...),
    level: str = Form("light"),
    user: dict = Depends(get_current_user),
):
    if level not in settings.GS_PRESETS:
        raise HTTPException(400, f"不支持的压缩级别: {level}")
    preset = settings.GS_PRESETS[level]

    with session_scope(user["dir_name"], "pdf-compress") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        pdf_bytes = await file.read()
        original_size = len(pdf_bytes)
        if original_size == 0:
            raise HTTPException(400, "上传的文件为空")

        safe_name = (file.filename or "input.pdf").replace("/", "_").replace("\\", "_")
        in_path = input_dir / safe_name
        in_path.write_bytes(pdf_bytes)

        # 快速验证 PDF
        try:
            probe = fitz.open(stream=pdf_bytes, filetype="pdf")
            if probe.page_count == 0:
                probe.close()
                raise HTTPException(400, "PDF 文件没有页面")
            if probe.is_encrypted and not probe.is_form_pdf:
                try:
                    probe.authenticate("")
                except Exception:
                    probe.close()
                    raise HTTPException(400, "PDF 已加密，请先解密")
            probe.close()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"无法打开 PDF 文件: {e}")

        base_name = sanitize_filename(Path(safe_name).stem, default="output")
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_name = f"{base_name}_compressed_{level}_{ts}.pdf"
        out_path = output_dir / out_name

        try:
            run_ghostscript(in_path, out_path, preset)
        except RuntimeError as e:
            raise HTTPException(500, str(e))

        compressed_size = out_path.stat().st_size

        if compressed_size >= original_size:
            shutil.copy(in_path, out_path)
            compressed_size = original_size
            saved_pct = 0.0
            msg = (
                f"该 PDF 已是最优，无法进一步压缩"
                f"（原文件 {format_bytes(original_size)}）"
            )
        else:
            saved_pct = (1 - compressed_size / original_size) * 100
            msg = (
                f"压缩完成（{format_bytes(original_size)} → "
                f"{format_bytes(compressed_size)}，节省 {saved_pct:.1f}%）"
            )

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [out_name],
            "original_size": original_size,
            "compressed_size": compressed_size,
            "saved_percent": round(saved_pct, 1),
        }