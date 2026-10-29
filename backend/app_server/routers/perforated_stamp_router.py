# app_server/routers/perforated_stamp_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from typing import Optional

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.perforated_stamp_service import dispatch_perforated_stamp


router = APIRouter(prefix="/api", tags=["perforated-stamp"])


@router.post("/perforated-stamp")
async def perforated_stamp(
    file: UploadFile = File(...),
    action: str = Form(...),
    stamp_file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    if action not in ("erase", "replace"):
        raise HTTPException(400, f"不支持的操作: {action}（可选: erase / replace）")

    if action == "replace" and stamp_file is None:
        raise HTTPException(400, "替换骑缝章需要上传新印章文件")

    with session_scope(user["dir_name"], "perforated-stamp") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(400, "上传的 PDF 为空")
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
        src.close()

        stamp_bytes = None
        if action == "replace":
            stamp_bytes = await stamp_file.read()
            if not stamp_bytes:
                raise HTTPException(400, "上传的印章文件为空")
            ssafe = (stamp_file.filename or "stamp.pdf").replace("/", "_").replace("\\", "_")
            (input_dir / ssafe).write_bytes(stamp_bytes)

        try:
            result = dispatch_perforated_stamp(
                pdf_bytes=pdf_bytes,
                output_dir=output_dir,
                safe_name=safe_name,
                action=action,
                stamp_bytes=stamp_bytes,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        except RuntimeError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(500, f"处理失败: {e}")

        msg = (
            f"{result['action_label']}完成，"
            f"共处理 {result['pages_affected']} 页，{result['seal_clusters']} 个骑缝章簇"
        )
        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
            "pages_affected": result["pages_affected"],
            "seal_clusters": result["seal_clusters"],
            "action": result["action"],
        }
