# app_server/routers/pdf_to_image_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pathlib import Path
import fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.pdf_common import IMAGE_FORMAT_MAP


router = APIRouter(prefix="/api", tags=["pdf-to-image"])


@router.post("/pdf-to-image")
async def pdf_to_image(
    file: UploadFile = File(...),
    image_format: str = Form("png"),
    dpi: int = Form(150),
    user: dict = Depends(get_current_user),
):
    # ---- 参数校验 ----
    fmt_key = image_format.lower().strip()
    if fmt_key not in IMAGE_FORMAT_MAP:
        raise HTTPException(400, f"不支持的图片格式: {image_format}")
    pix_fmt, ext, _mime = IMAGE_FORMAT_MAP[fmt_key]

    if dpi < 36 or dpi > 1200:
        raise HTTPException(400, "DPI 需在 36~1200 之间")

    with session_scope(user["dir_name"], "pdf-to-image") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        # 保存原始 PDF
        pdf_bytes = await file.read()
        safe_name = (file.filename or "input.pdf").replace("/", "_").replace("\\", "_")
        (input_dir / safe_name).write_bytes(pdf_bytes)

        # 打开 PDF
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise HTTPException(400, f"无法打开 PDF 文件: {e}")

        if doc.is_encrypted and not doc.is_form_pdf:
            try:
                doc.authenticate("")
            except Exception:
                doc.close()
                raise HTTPException(400, "PDF 已加密，请先解密")

        if doc.page_count == 0:
            doc.close()
            raise HTTPException(400, "PDF 文件没有页面")

        page_count = doc.page_count
        base_name = Path(safe_name).stem
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)

        rendered: list[str] = []
        try:
            for i in range(page_count):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                data = pix.tobytes(pix_fmt)
                name = f"{base_name}_page_{i + 1:03d}.{ext}"
                (output_dir / name).write_bytes(data)
                rendered.append(name)
        finally:
            doc.close()

        return {
            "message": f"转换完成（{page_count} 页）",
            "page_count": page_count,
            "session_id": session_id,
            "output_files": rendered,
        }