# app_server/routers/pdf_reorder_router.py
import json

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.pdf_reorder_service import reorder_pages


router = APIRouter(prefix="/api", tags=["pdf-reorder"])


@router.post("/pdf-reorder")
async def pdf_reorder(
    file: UploadFile = File(...),
    order_json: str = Form(...),   # JSON: [3, 1, 2, 4] （1-indexed）
    user: dict = Depends(get_current_user),
):
    try:
        raw = json.loads(order_json)
    except Exception as e:
        raise HTTPException(400, f"order_json 解析失败: {e}")

    if not isinstance(raw, list) or not raw:
        raise HTTPException(400, "order_json 必须是非空数组")

    try:
        new_order_1based = [int(x) for x in raw]
    except (ValueError, TypeError):
        raise HTTPException(400, "order_json 里必须都是整数")

    with session_scope(user["dir_name"], "pdf-reorder") as (session_id, sroot):
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

        # 1-indexed → 0-indexed
        new_order_0based = [p - 1 for p in new_order_1based]

        try:
            result = reorder_pages(src, output_dir, safe_name, new_order_0based)
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

        return {
            "message": f"页面已重排（共 {result['pages']} 页）",
            "session_id": session_id,
            "output_files": [result["out_name"]],
        }