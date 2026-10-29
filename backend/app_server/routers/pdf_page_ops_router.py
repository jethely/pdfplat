# app_server/routers/pdf_page_ops_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.core.utils import parse_page_ranges
from app_server.services.storage_service import session_scope
from app_server.services.pdf_page_ops_service import (
    delete_pages, extract_pages, rotate_pages,
)

router = APIRouter(prefix="/api", tags=["pdf-page-ops"])

# ==================== 删除页面 ====================
@router.post("/pdf-delete-pages")
async def pdf_delete_pages(
    file: UploadFile = File(...),
    pages: str = Form(...),             # "1, 3, 5-7"
    mode: str = Form("delete"),         # delete=删除指定页 | keep=保留指定页
    user: dict = Depends(get_current_user),
):
    if mode not in ("delete", "keep"):
        raise HTTPException(400, f"不支持的模式: {mode}")
    if not pages or not pages.strip():
        raise HTTPException(400, "请填写页码")

    with session_scope(user["dir_name"], "pdf-delete-pages") as (session_id, sroot):
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

        total = src.page_count

        # 解析页码
        try:
            page_list, _oor = parse_page_ranges(pages, total)
        except ValueError as e:
            src.close()
            raise HTTPException(400, f"页码格式错误: {e}")
        if not page_list:
            src.close()
            raise HTTPException(400, "没有有效的页码")

        try:
            if mode == "delete":
                result = delete_pages(src, page_list, safe_name, output_dir)
                msg = (
                    f"删除完成：从 {total} 页中删除 {result['deleted_count']} 页，"
                    f"剩余 {result['remaining_count']} 页"
                )
            else:  # keep
                result = extract_pages(src, page_list, safe_name, output_dir)
                msg = (
                    f"提取完成：从 {total} 页中保留 {result['kept_count']} 页"
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

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
        }


# ==================== 旋转页面 ====================
@router.post("/pdf-rotate-pages")
async def pdf_rotate_pages(
    file: UploadFile = File(...),
    angle: int = Form(90),              # 90 | 180 | 270
    pages: str = Form(""),              # 空 = 全部页
    user: dict = Depends(get_current_user),
):
    if angle not in (90, 180, 270):
        raise HTTPException(400, "旋转角度只能是 90/180/270")

    with session_scope(user["dir_name"], "pdf-rotate-pages") as (session_id, sroot):
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

        total = src.page_count

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

        try:
            result = rotate_pages(src, target_pages, angle, safe_name, output_dir)
        except Exception as e:
            src.close()
            raise HTTPException(500, f"旋转失败: {e}")
        finally:
            try:
                src.close()
            except Exception:
                pass

        scope_hint = f"（第 {pages} 页）" if pages.strip() else "（全部页面）"
        msg = f"旋转完成{scope_hint}，共 {result['pages_processed']} 页，旋转 {angle}°"

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
        }