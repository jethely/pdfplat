# app_server/routers/pdf_watermark_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.core.utils import parse_page_ranges
from app_server.services.storage_service import session_scope
from app_server.services.watermark_service import add_watermark


router = APIRouter(prefix="/api", tags=["pdf-watermark"])


ALLOWED_POSITIONS = {
    "center", "top-left", "top-right",
    "bottom-left", "bottom-right", "tile",
}


def _hex_to_rgb(hex_color: str) -> tuple:
    """'#888888' → (0.53, 0.53, 0.53)"""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0.5, 0.5, 0.5)
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b)
    except Exception:
        return (0.5, 0.5, 0.5)


@router.post("/pdf-watermark")
async def pdf_watermark(
    file: UploadFile = File(...),
    text: str = Form(...),
    position: str = Form("center"),
    rotation: float = Form(45),
    fontsize: float = Form(60),
    color: str = Form("#888888"),
    opacity: float = Form(0.3),
    pages: str = Form(""),
    user: dict = Depends(get_current_user),
):
    # ---- 参数校验 ----
    if not text.strip():
        raise HTTPException(400, "水印文字不能为空")
    if len(text) > 100:
        raise HTTPException(400, "水印文字过长（≤ 100 字符）")
    if position not in ALLOWED_POSITIONS:
        raise HTTPException(400, f"不支持的位置: {position}")
    if not (0 <= rotation <= 360):
        raise HTTPException(400, "旋转角度需在 0~360 之间")
    if not (6 <= fontsize <= 400):
        raise HTTPException(400, "字号需在 6~400 之间")
    if not (0.0 <= opacity <= 1.0):
        raise HTTPException(400, "透明度需在 0.0~1.0 之间")

    rgb = _hex_to_rgb(color)

    with session_scope(user["dir_name"], "pdf-watermark") as (session_id, sroot):
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

        # 解析页码范围
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
            result = add_watermark(
                src,
                text.strip(),
                position=position,
                rotation=rotation,
                fontsize=fontsize,
                color=rgb,
                opacity=opacity,
                pages=target_pages,
                safe_name=safe_name,
                output_dir=output_dir,
            )
        except Exception as e:
            src.close()
            raise HTTPException(500, f"添加水印失败: {e}")
        finally:
            try:
                src.close()
            except Exception:
                pass

        scope_hint = f"（第 {pages} 页）" if pages.strip() else "（全部页面）"
        msg = (
            f"水印添加完成{scope_hint}，共 {result['pages_processed']} 页"
            f"（每页 {result['instances_per_page']} 个水印）"
        )

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
            "pages_processed": result["pages_processed"],
        }