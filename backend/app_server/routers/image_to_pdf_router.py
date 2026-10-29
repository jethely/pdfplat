# app_server/routers/image_to_pdf_router.py
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import List
from pathlib import Path
import fitz
import time

from app_server.core.dependencies import get_current_user
from app_server.core.utils import sanitize_filename
from app_server.services.storage_service import session_scope
from app_server.services.pdf_common import ALLOWED_IMAGE_EXTS


router = APIRouter(prefix="/api", tags=["image-to-pdf"])


@router.post("/image-to-pdf")
async def image_to_pdf(
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
):
    if not files:
        raise HTTPException(400, "请至少上传一张图片")

    with session_scope(user["dir_name"], "image-to-pdf") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        # ---- 1. 按上传顺序保存图片 ----
        saved: list[tuple[str, bytes]] = []
        for f in files:
            data = await f.read()
            if not data:
                continue

            raw_name = f.filename or "img"
            ext = Path(raw_name).suffix.lower()
            if ext and ext not in ALLOWED_IMAGE_EXTS:
                raise HTTPException(400, f"不支持的图片格式: {raw_name}")

            safe = raw_name.replace("/", "_").replace("\\", "_")
            (input_dir / safe).write_bytes(data)
            saved.append((safe, data))

        if not saved:
            raise HTTPException(400, "上传的图片为空")

        # ---- 2. 逐张创建 PDF 页面 ----
        doc = fitz.open()
        try:
            for name, data in saved:
                try:
                    img = fitz.open(stream=data, filetype=None)
                except Exception as e:
                    raise HTTPException(400, f"无法识别图片「{name}」: {e}")

                if img.page_count == 0:
                    img.close()
                    raise HTTPException(400, f"图片「{name}」没有内容")

                rect = img[0].rect
                page = doc.new_page(width=rect.width, height=rect.height)
                page.insert_image(rect, stream=data)
                img.close()

            # ---- 3. 保存 PDF ----
            first_stem = Path(saved[0][0]).stem
            safe_stem = sanitize_filename(first_stem)
            ts = time.strftime("%Y%m%d_%H%M%S")
            output_name = f"{safe_stem}_merged_{ts}.pdf"
            doc.save(str(output_dir / output_name))
        finally:
            doc.close()

        page_count = len(saved)
        return {
            "message": f"合并完成（{page_count} 张图片 → {page_count} 页）",
            "session_id": session_id,
            "output_files": [output_name],
            "page_count": page_count,
        }