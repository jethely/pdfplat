# app_server/routers/pdf_to_excel_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.pdf_to_excel_service import dispatch_pdf_to_excel


router = APIRouter(prefix="/api", tags=["pdf-to-excel"])


@router.post("/pdf-to-excel")
async def pdf_to_excel(
    file: UploadFile = File(...),
    strategy: str = Form("auto"),
    per_page_sheet: bool = Form(True),
    user: dict = Depends(get_current_user),
):
    if strategy not in ("auto", "A", "B", "C"):
        raise HTTPException(400, f"不支持的策略: {strategy}")

    with session_scope(user["dir_name"], "pdf-to-excel") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(400, "上传的文件为空")
        safe_name = (file.filename or "input.pdf").replace("/", "_").replace("\\", "_")
        pdf_path = input_dir / safe_name
        pdf_path.write_bytes(pdf_bytes)

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
            result = dispatch_pdf_to_excel(
                src, pdf_path, output_dir, safe_name,
                strategy=strategy,
                per_page_sheet=per_page_sheet,
            )
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

        msg = (
            f"转换完成：{result['pages_with_tables']} 页含表格，"
            f"共 {result['table_count']} 个表格 / {result['row_count']} 行"
            f" — {result['strategy_label']}"
        )

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
            "table_count": result["table_count"],
            "row_count": result["row_count"],
        }