# app_server/routers/pdf_to_text_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.pdf_to_text_service import pdf_to_text


router = APIRouter(prefix="/api", tags=["pdf-to-text"])


@router.post("/pdf-to-text")
async def pdf_to_text_api(
    file: UploadFile = File(...),
    with_page_sep: bool = Form(True),
    user: dict = Depends(get_current_user),
):
    with session_scope(user["dir_name"], "pdf-to-text") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(400, "上传的文件为空")
        safe_name = (file.filename or "input.pdf").replace("/", "_").replace("\\", "_")
        (input_dir / safe_name).write_bytes(pdf_bytes)

        try:
            src = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise HTTPException(400, f"无法打开 PDF 文件: {e}")

        if src.is_encrypted and not src.is_form_pdf:
            try:
                src.authenticate("")
            except Exception:
                src.close()
                raise HTTPException(400, "PDF 已加密，请先解密")
        if src.page_count == 0:
            src.close()
            raise HTTPException(400, "PDF 文件没有页面")

        try:
            result = pdf_to_text(src, output_dir, safe_name, with_page_sep)
        except Exception as e:
            src.close()
            raise HTTPException(500, f"处理失败: {e}")
        finally:
            try:
                src.close()
            except Exception:
                pass

        if result["chars"] < 10:
            raise HTTPException(
                400,
                "该 PDF 没有可提取的文字（可能是扫描件/图片型 PDF）。",
            )

        return {
            "message": f"提取完成：{result['pages']} 页，共 {result['chars']} 字符",
            "session_id": session_id,
            "output_files": [result["out_name"]],
        }