# app_server/routers/extract_images_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.extract_images_service import dispatch_extract_images


router = APIRouter(prefix="/api", tags=["extract-images"])


@router.post("/extract-images")
async def extract_images(
    file: UploadFile = File(...),
    strategy: str = Form("auto"),
    user: dict = Depends(get_current_user),
):
    if strategy not in ("auto", "A", "B", "C"):
        raise HTTPException(400, f"不支持的策略: {strategy}")

    with session_scope(user["dir_name"], "extract-images") as (session_id, sroot):
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
            result = dispatch_extract_images(src, output_dir, safe_name, strategy=strategy)
        except RuntimeError as e:
            src.close()
            raise HTTPException(400, str(e))
        except Exception as e:
            src.close()
            raise HTTPException(500, f"提取失败: {e}")
        finally:
            try:
                src.close()
            except Exception:
                pass

        msg = (
            f"提取完成：共 {result['count_saved']} 张图片"
            f"（发现 {result['count_found']} 处引用）"
            f" — {result['strategy_label']}"
        )

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": result["out_names"],
            "count_saved": result["count_saved"],
        }