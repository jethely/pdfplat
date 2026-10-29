# app_server/routers/pdf_to_word_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pathlib import Path

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.pdf_to_word_service import dispatch_pdf_to_word


router = APIRouter(prefix="/api", tags=["pdf-to-word"])


@router.post("/pdf-to-word")
async def pdf_to_word(
    file: UploadFile = File(...),
    strategy: str = Form("auto"),     # auto | A | B | C
    user: dict = Depends(get_current_user),
):
    if strategy not in ("auto", "A", "B", "C"):
        raise HTTPException(400, f"不支持的策略: {strategy}")

    with session_scope(user["dir_name"], "pdf-to-word") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(400, "上传的文件为空")
        safe_name = (file.filename or "input.pdf").replace("/", "_").replace("\\", "_")
        pdf_path = input_dir / safe_name
        pdf_path.write_bytes(pdf_bytes)

        # ---- 打开 PDF 校验 ----
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

        # ---- 转换 ----
        try:
            result = dispatch_pdf_to_word(
                src, pdf_path, output_dir, safe_name, strategy=strategy,
            )
        except ValueError as e:
            src.close()
            raise HTTPException(400, str(e))
        except RuntimeError as e:
            src.close()
            raise HTTPException(400, str(e))
        except Exception as e:
            src.close()
            raise HTTPException(500, f"转换失败: {e}")
        finally:
            try:
                src.close()
            except Exception:
                pass

        # ---- 组装返回 ----
        msg = f"转换完成，共 {src.page_count if False else 'N'} 页"
        msg = "转换完成"
        if result.get("warning"):
            msg += f"（{result['warning']}）"
        msg += f" — {result['strategy_label']}"

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
            "strategy": result["strategy"],
            "warning": result.get("warning"),
        }