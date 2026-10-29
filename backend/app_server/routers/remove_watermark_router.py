# app_server/routers/remove_watermark_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.core.utils import parse_page_ranges
from app_server.services.storage_service import session_scope
from app_server.services.remove_watermark_service import dispatch_remove_watermark


router = APIRouter(prefix="/api", tags=["remove-watermark"])


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (1, 1, 1)
    try:
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
        )
    except Exception:
        return (1, 1, 1)


@router.post("/remove-watermark")
async def remove_watermark(
    file: UploadFile = File(...),
    strategy: str = Form("auto"),
    text: str = Form(""),
    pages: str = Form(""),
    fill_mode: str = Form("auto"),      # auto | white | custom
    custom_color: str = Form("#ffffff"),
    user: dict = Depends(get_current_user),
):
    if strategy not in ("auto", "A", "B", "C"):
        raise HTTPException(400, f"不支持的策略: {strategy}")
    if fill_mode not in ("auto", "white", "custom"):
        raise HTTPException(400, f"不支持的填充模式: {fill_mode}")

    # 策略 A 必须提供水印文字
    if strategy in ("A", "auto") and not text.strip():
        raise HTTPException(400, "请输入要去除的水印文字")

    with session_scope(user["dir_name"], "remove-watermark") as (session_id, sroot):
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

        rgb = _hex_to_rgb(custom_color)

        try:
            result = dispatch_remove_watermark(
                src, output_dir, safe_name,
                strategy=strategy,
                text=text,
                target_pages=target_pages,
                fill_mode=fill_mode,
                custom_color=rgb,
            )
        except ValueError as e:
            src.close()
            raise HTTPException(400, str(e))
        except RuntimeError as e:
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

        scope_hint = f"（第 {pages} 页）" if pages.strip() else "（全文）"
        msg = (
            f"去水印完成{scope_hint}，"
            f"共去除 {result['removed_count']} 处（{result['pages_affected']} 页）"
            f" — {result['strategy_label']}"
        )
        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
            "removed_count": result["removed_count"],
        }