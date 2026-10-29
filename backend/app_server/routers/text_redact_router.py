# app_server/routers/text_redact_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.core.utils import parse_page_ranges
from app_server.services.storage_service import session_scope
from app_server.services.text_redact_service import dispatch_redact


router = APIRouter(prefix="/api", tags=["text-redact"])


@router.post("/text-redact")
async def text_redact(
    file: UploadFile = File(...),
    text_to_redact: str = Form(...),
    redact_action: str = Form("mask"),    # mask | erase
    pages: str = Form(""),
    user: dict = Depends(get_current_user),
):
    if not text_to_redact:
        raise HTTPException(400, "需要遮掩/擦除的文字不能为空")
    if redact_action not in ("mask", "erase"):
        raise HTTPException(400, f"不支持的操作: {redact_action}")

    with session_scope(user["dir_name"], "text-redact") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(400, "上传的文件为空")
        safe_name = (file.filename or "input.pdf").replace("/", "_").replace("\\", "_")
        (input_dir / safe_name).write_bytes(pdf_bytes)

        # ---- 打开 PDF ----
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

        total = src.page_count

        # ---- 解析页码范围 ----
        if pages and pages.strip():
            try:
                page_list, _oor = parse_page_ranges(pages, total)
            except ValueError as e:
                src.close()
                raise HTTPException(400, f"页码格式错误: {e}")
            if not page_list:
                src.close()
                raise HTTPException(400, "没有有效的页码")
            target_pages = page_list
        else:
            target_pages = list(range(total))

        # ---- 分发处理（含类型检测）----
        try:
            r = dispatch_redact(
                src, safe_name, text_to_redact, target_pages,
                redact_action, output_dir, pages,
            )
        except ValueError as e:
            src.close()
            raise HTTPException(400, str(e))
        except RuntimeError as e:
            src.close()
            raise HTTPException(400, str(e))
        finally:
            try:
                src.close()
            except Exception:
                pass

        # ---- 组装返回 ----
        action_label = "遮掩" if redact_action == "mask" else "擦除"
        scope_hint = f"（第 {pages} 页）" if pages.strip() else "（全文）"
        msg = (
            f"{action_label}完成{scope_hint}，"
            f"共 {r['redacted_count']} 处（{r['pages_with_hits']} 页）"
        )
        if r.get("skipped_pages"):
            msg += f"（跳过 {len(r['skipped_pages'])} 个无文字层页面）"

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [r["out_name"]],
            "redacted_count": r["redacted_count"],
            "pages_with_hits": r["pages_with_hits"],
            "skipped_pages": r.get("skipped_pages", []),
            "pdf_type": r.get("pdf_type"),
        }