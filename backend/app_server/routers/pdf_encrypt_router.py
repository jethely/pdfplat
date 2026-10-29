# app_server/routers/pdf_encrypt_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pathlib import Path
import time

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.core.utils import sanitize_filename
from app_server.services.storage_service import session_scope


router = APIRouter(prefix="/api", tags=["pdf-encrypt"])


def _compute_permissions(
    level: str,
    perm_print: bool,
    perm_copy: bool,
    perm_modify: bool,
    perm_annotate: bool,
    perm_form: bool,
    perm_accessibility: bool,
) -> int:
    if level == "all":
        return (
            fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_MODIFY
            | fitz.PDF_PERM_ANNOTATE
            | fitz.PDF_PERM_FORM
            | fitz.PDF_PERM_ACCESSIBILITY
        )
    if level == "print-only":
        return fitz.PDF_PERM_PRINT | fitz.PDF_PERM_ACCESSIBILITY
    if level == "readonly":
        return fitz.PDF_PERM_ACCESSIBILITY

    perm = 0
    if perm_print:         perm |= fitz.PDF_PERM_PRINT
    if perm_copy:          perm |= fitz.PDF_PERM_COPY
    if perm_modify:        perm |= fitz.PDF_PERM_MODIFY
    if perm_annotate:      perm |= fitz.PDF_PERM_ANNOTATE
    if perm_form:          perm |= fitz.PDF_PERM_FORM
    if perm_accessibility: perm |= fitz.PDF_PERM_ACCESSIBILITY
    return perm


def _describe_permissions(level: str, perm: int) -> str:
    if level == "all":
        return "全权限（仅加密）"
    if level == "print-only":
        return "仅阅读 + 打印"
    if level == "readonly":
        return "仅阅读"

    parts = []
    if perm & fitz.PDF_PERM_PRINT:         parts.append("打印")
    if perm & fitz.PDF_PERM_COPY:          parts.append("复制")
    if perm & fitz.PDF_PERM_MODIFY:        parts.append("修改")
    if perm & fitz.PDF_PERM_ANNOTATE:      parts.append("批注")
    if perm & fitz.PDF_PERM_FORM:          parts.append("填表")
    if perm & fitz.PDF_PERM_ACCESSIBILITY: parts.append("无障碍")
    return "自定义（" + "、".join(parts) + "）" if parts else "无任何权限"


@router.post("/pdf-encrypt")
async def pdf_encrypt(
    file: UploadFile = File(...),
    password: str = Form(...),
    owner_password: str = Form(""),
    perm_level: str = Form("all"),
    perm_print: bool = Form(True),
    perm_copy: bool = Form(True),
    perm_modify: bool = Form(True),
    perm_annotate: bool = Form(True),
    perm_form: bool = Form(True),
    perm_accessibility: bool = Form(True),
    user: dict = Depends(get_current_user),
):
    if not password or len(password) < 1:
        raise HTTPException(400, "打开密码不能为空")
    if len(password) > 64:
        raise HTTPException(400, "密码过长（≤ 64 字符）")
    if perm_level not in ("all", "print-only", "readonly", "custom"):
        raise HTTPException(400, f"不支持的权限级别: {perm_level}")

    owner_pw = owner_password.strip() if owner_password else ""

    with session_scope(user["dir_name"], "pdf-encrypt") as (session_id, sroot):
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

        if src.is_encrypted:
            src.close()
            raise HTTPException(400, "PDF 已加密，不能重复加密")

        if src.page_count == 0:
            src.close()
            raise HTTPException(400, "PDF 文件没有页面")

        perm = _compute_permissions(
            perm_level, perm_print, perm_copy, perm_modify,
            perm_annotate, perm_form, perm_accessibility,
        )

        base_name = sanitize_filename(Path(safe_name).stem, default="output")
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_name = f"{base_name}_encrypted_{ts}.pdf"
        out_path = output_dir / out_name

        try:
            save_kwargs = {
                "encryption": fitz.PDF_ENCRYPT_AES_256,
                "user_pw": password,
                "permissions": perm,
                "garbage": 4,
                "deflate": True,
            }
            if owner_pw:
                save_kwargs["owner_pw"] = owner_pw
            src.save(str(out_path), **save_kwargs)
        except Exception as e:
            raise HTTPException(500, f"加密失败: {e}")
        finally:
            src.close()

        perm_desc = _describe_permissions(perm_level, perm)
        msg = f"加密完成（AES-256，权限：{perm_desc}）"

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [out_name],
        }