# app_server/routers/pdf_to_long_image_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.pdf_to_long_image_service import pdf_to_long_image


router = APIRouter(prefix="/api", tags=["pdf-to-long-image"])


@router.post("/pdf-to-long-image")
async def pdf_to_long_image_api(
    file: UploadFile = File(...),
    dpi: int = Form(150),
    gap: int = Form(0),
    user: dict = Depends(get_current_user),
):
    with session_scope(user["dir_name"], "pdf-to-long-image") as (session_id, sroot):
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
            result = pdf_to_long_image(src, output_dir, safe_name, dpi=dpi, gap=gap)
        except ValueError as e:
            src.close()
            raise HTTPException(400, str(e))
        except RuntimeError as e:
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

        msg = (
            f"长图生成完成：{result['pages']} 页 → "
            f"{result['width']}×{result['height']} 像素"
        )
        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
        }