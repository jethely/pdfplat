# app_server/routers/pdf_metadata_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.pdf_metadata_service import update_metadata


router = APIRouter(prefix="/api", tags=["pdf-metadata"])


@router.post("/pdf-metadata")
async def pdf_metadata(
    file: UploadFile = File(...),
    title: str = Form(""),
    author: str = Form(""),
    subject: str = Form(""),
    keywords: str = Form(""),
    creator: str = Form(""),
    producer: str = Form(""),
    user: dict = Depends(get_current_user),
):
    with session_scope(user["dir_name"], "pdf-metadata") as (session_id, sroot):
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

        try:
            result = update_metadata(
                src, output_dir, safe_name,
                title=title, author=author, subject=subject,
                keywords=keywords, creator=creator, producer=producer,
            )
        except ValueError as e:
            src.close()
            raise HTTPException(400, str(e))
        except Exception as e:
            src.close()
            raise HTTPException(500, f"处理失败: {e}")
        finally:
            try:
                src.close()
            except Exception:
                pass

        msg = f"元数据已更新：{', '.join(result['changed_fields'])}"
        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
        }


@router.post("/pdf-metadata/read")
async def pdf_metadata_read(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """读取 PDF 现有元数据（前端预填用）。"""
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(400, "上传的文件为空")
    try:
        src = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise HTTPException(400, f"无法打开 PDF 文件: {e}")
    md = dict(src.metadata or {})
    src.close()
    return md