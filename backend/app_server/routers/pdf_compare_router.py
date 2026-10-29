# app_server/routers/pdf_compare_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from typing import List

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import session_scope
from app_server.services.pdf_compare_service import dispatch_pdf_compare


router = APIRouter(prefix="/api", tags=["pdf-compare"])


@router.post("/pdf-compare")
async def pdf_compare(
    files: List[UploadFile] = File(...),
    strategy: str = Form("auto"),
    user: dict = Depends(get_current_user),
):
    if len(files) != 2:
        raise HTTPException(400, "请上传恰好 2 个 PDF 文件进行对比")
    if strategy not in ("auto", "A", "B", "C"):
        raise HTTPException(400, f"不支持的策略: {strategy}")

    with session_scope(user["dir_name"], "pdf-compare") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        # 保存 2 个文件
        saved_paths = []
        saved_names = []
        for f in files:
            data = await f.read()
            if not data:
                raise HTTPException(400, f"文件「{f.filename}」为空")
            safe = (f.filename or "input.pdf").replace("/", "_").replace("\\", "_")
            p = input_dir / safe
            p.write_bytes(data)
            saved_paths.append(p)
            saved_names.append(safe)

        # 校验是两个 PDF
        for p, n in zip(saved_paths, saved_names):
            try:
                d = fitz.open(str(p))
                if d.is_encrypted and not d.is_form_pdf:
                    try:
                        d.authenticate("")
                    except Exception:
                        d.close()
                        raise HTTPException(400, f"「{n}」已加密，请先解密")
                d.close()
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(400, f"无法打开「{n}」: {e}")

        # 对比
        try:
            result = dispatch_pdf_compare(
                saved_paths[0], saved_paths[1],
                output_dir, saved_names[0], saved_names[1],
                strategy=strategy,
            )
        except RuntimeError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(500, f"对比失败: {e}")

        msg = (
            f"对比完成（{result['pages_total']} 页："
            f"相同 {result['pages_same']}，差异 {result['pages_diff']}）"
            f" — {result['strategy_label']}"
        )

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": [result["out_name"]],
            "pages_total": result["pages_total"],
            "pages_same": result["pages_same"],
            "pages_diff": result["pages_diff"],
        }