# app_server/routers/pdf_redact_area_router.py
import json

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import (
    make_session_dir, get_session_path, list_session_files,
)
from app_server.services.redact_area_service import (
    render_previews, apply_rects,
)


router = APIRouter(prefix="/api", tags=["pdf-redact-area"])


# ==================== 第一步：上传 + 生成预览 ====================
@router.post("/pdf-redact-area/prepare")
async def prepare(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    # ⚠️ 不用 session_scope，因为要跨请求保留
    session_id = make_session_dir(user["dir_name"], "pdf-redact-area")
    sroot = get_session_path(user["dir_name"], session_id)
    input_dir = sroot / "input"

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
        pages = render_previews(src, sroot / "preview", target_width=600)
    finally:
        src.close()

    return {
        "session_id": session_id,
        "file_name": safe_name,
        "total_pages": src.page_count if False else len(pages),  # 已在 finally 前
        "pages": pages,
    }


# ==================== 第二步：应用矩形 ====================
@router.post("/pdf-redact-area/apply")
async def apply(
    session_id: str = Form(...),
    rects_json: str = Form(...),
    fill_mode: str = Form("black"),
    shape: str = Form("rect"),
    user: dict = Depends(get_current_user),
):
    if fill_mode not in ("black", "white"):
        raise HTTPException(400, f"不支持的填充模式: {fill_mode}")
    if shape not in ("rect", "ellipse", "circle"):
        raise HTTPException(400, f"不支持的形状: {shape}")

    # 校验 session 归属
    sroot = get_session_path(user["dir_name"], session_id)
    if not sroot.exists():
        raise HTTPException(404, "会话不存在，请重新上传")
    input_dir = sroot / "input"
    output_dir = sroot / "output"

    pdf_files = [
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    ]
    if not pdf_files:
        raise HTTPException(404, "找不到原文件")
    in_path = pdf_files[0]

    # 解析 rects
    try:
        rects = json.loads(rects_json)
    except Exception as e:
        raise HTTPException(400, f"rects_json 解析失败: {e}")
    if not isinstance(rects, list):
        raise HTTPException(400, "rects 必须是数组")
    if len(rects) > 5000:
        raise HTTPException(400, "区域数量过多（≤ 5000）")

    try:
        src = fitz.open(str(in_path))
    except Exception as e:
        raise HTTPException(400, f"无法打开 PDF: {e}")

    try:
        result = apply_rects(
            src, rects, in_path.name, output_dir, fill_mode=fill_mode, shape=shape,
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

    msg = (
        f"遮掩完成：共 {result['applied_count']} 个区域，"
        f"影响 {len(result['pages_affected'])} 页"
    )

    return {
        "message": msg,
        "session_id": session_id,
        "output_files": [result["out_name"]],
    }