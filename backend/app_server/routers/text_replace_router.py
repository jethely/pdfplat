# app_server/routers/text_replace_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pathlib import Path
import re

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.core.utils import sanitize_filename
from app_server.services.storage_service import session_scope
from app_server.services.text_replace_stream_service import replace_text_stream

router = APIRouter(prefix="/api", tags=["text-replace"])


def _parse_pages(pages_text: str, total: int) -> list:
    if not pages_text or pages_text.strip().lower() == "all":
        return list(range(total))
    pages = set()
    for part in re.split(r"[,，\s]+", pages_text.strip()):
        if not part:
            continue
        m = re.match(r"^(\d+)-(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            pages.update(range(a - 1, b))
        else:
            pages.add(int(part) - 1)
    return sorted(p for p in pages if 0 <= p < total)


@router.post("/text-replace")
async def text_replace(
    file: UploadFile = File(...),
    old_text: str = Form(...),
    new_text: str = Form(...),
    pages: str = Form(""),
    user: dict = Depends(get_current_user),
):
    if not old_text.strip():
        raise HTTPException(400, "查找文字不能为空")

    with session_scope(user["dir_name"], "text-replace") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(400, "上传的文件为空")

        safe_name = sanitize_filename(
            (file.filename or "input.pdf").replace("/", "_").replace("\\", "_"),
            default="input.pdf",
        )
        pdf_path = input_dir / safe_name
        pdf_path.write_bytes(pdf_bytes)

        # 快速探测 PDF
        try:
            probe = fitz.open(str(pdf_path))
            total_pages = probe.page_count
            probe.close()
        except Exception as e:
            raise HTTPException(400, f"无法打开 PDF 文件: {e}")

        if total_pages == 0:
            raise HTTPException(400, "PDF 文件没有页面")

        target_pages = _parse_pages(pages, total_pages)

        try:
            result = replace_text_stream(
                pdf_path=pdf_path,
                target_str=old_text,
                new_str=new_text,
                output_dir=output_dir,
                safe_name=safe_name,
                target_pages=target_pages,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(500, f"替换失败: {e}")

        skipped = result.get("skipped_pages", [])
        replaced = result.get("replaced_count", 0)

        if replaced == 0 and not skipped:
            raise HTTPException(400, f"在指定页面中未找到「{old_text}」")

        scope_label = f"指定 {len(target_pages)} 页" if pages.strip() else "全文"
        msg_parts = [f"替换成功，共找到 {replaced} 处（{scope_label}）"]
        if skipped:
            msg_parts.append(f"{len(skipped)} 页无匹配：第 {skipped} 页")

        return {
            "message": "，".join(msg_parts),
            "session_id": session_id,
            "output_files": [result["out_name"]],
            "replaced_count": replaced,
            "skipped_pages": skipped,
            "page_details": result.get("page_details", {}),
        }