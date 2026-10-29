# app_server/routers/pdf_page_number_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.core.utils import parse_page_ranges
from app_server.services.storage_service import session_scope
from app_server.services.page_number_service import add_page_numbers


router = APIRouter(prefix="/api", tags=["pdf-page-number"])


ALLOWED_FORMATS = {
    "n", "n/m", "page-n", "page-n-of-m",
    "n-m", "di-n-ye", "di-n-ye-gong-m-ye",
}
ALLOWED_POSITIONS = {
    "bottom-center", "bottom-right", "bottom-left",
    "top-center", "top-right", "top-left",
}


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    try:
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
        )
    except Exception:
        return (0, 0, 0)


@router.post("/pdf-page-number")
async def pdf_page_number(
    file: UploadFile = File(...),
    fmt: str = Form("n"),
    position: str = Form("bottom-center"),
    start_number: int = Form(1),
    fontsize: float = Form(12),
    color: str = Form("#000000"),
    margin: float = Form(30),
    pages: str = Form(""),
    skip_first: int = Form(0),        # 跳过前 N 页（封面）
    user: dict = Depends(get_current_user),
):
    # ---- 参数校验 ----
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(400, f"不支持的页码格式: {fmt}")
    if position not in ALLOWED_POSITIONS:
        raise HTTPException(400, f"不支持的位置: {position}")
    if start_number < 0:
        raise HTTPException(400, "起始编号不能为负")
    if not (6 <= fontsize <= 72):
        raise HTTPException(400, "字号需在 6~72 之间")
    if not (0 <= margin <= 200):
        raise HTTPException(400, "边距需在 0~200 之间")
    if skip_first < 0:
        raise HTTPException(400, "跳过页数不能为负")

    rgb = _hex_to_rgb(color)

    with session_scope(user["dir_name"], "pdf-page-number") as (session_id, sroot):
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

        # ---- 计算要处理的页 ----
        if pages and pages.strip():
            # 用户指定页面
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
            # 默认全部页，可跳过前 N 页
            if skip_first >= total:
                src.close()
                raise HTTPException(
                    400,
                    f"跳过页数（{skip_first}）大于总页数（{total}）",
                )
            target_pages = list(range(skip_first, total))

        try:
            result = add_page_numbers(
                src,
                fmt=fmt,
                position=position,
                start_number=start_number,
                fontsize=fontsize,
                color=rgb,
                margin=margin,
                pages=target_pages,
                safe_name=safe_name,
                output_dir=output_dir,
            )
        except Exception as e:
            src.close()
            raise HTTPException(500, f"添加页码失败: {e}")
        finally:
            try:
                src.close()
            except Exception:
                pass

        # ---- 消息 ----
        scope_parts = []
        if pages and pages.strip():
            scope_parts.append(f"指定页：{pages}")
        elif skip_first > 0:
            scope_parts.append(f"跳过前 {skip_first} 页")
        else:
            scope_parts.append("全部页面")
        scope_hint = f"（{'，'.join(scope_parts)}）"

        msg = (
            f"页码添加完成{scope_hint}，"
            f"共 {result['pages_processed']} 页，"
            f"首页显示「{result['sample_text']}」"
        )

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
            "pages_processed": result["pages_processed"],
        }