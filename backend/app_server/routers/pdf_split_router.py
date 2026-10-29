# app_server/routers/pdf_split_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pathlib import Path
import fitz
import time

from app_server.core.dependencies import get_current_user
from app_server.core.utils import sanitize_filename, parse_page_ranges
from app_server.services.storage_service import session_scope


router = APIRouter(prefix="/api", tags=["pdf-split"])


@router.post("/pdf-split")
async def pdf_split(
    file: UploadFile = File(...),
    mode: str = Form("extract"),          # extract | per-page | chunk | parity
    pages: str = Form(""),                # mode=extract
    chunk_size: int = Form(1),            # mode=chunk
    parity: str = Form("odd"),            # mode=parity: odd | even
    user: dict = Depends(get_current_user),
):
    # ---- 参数校验 ----
    if mode not in ("extract", "per-page", "chunk", "parity"):
        raise HTTPException(400, f"不支持的拆分方式: {mode}")
    if mode == "chunk" and chunk_size < 1:
        raise HTTPException(400, "每隔页数必须 ≥ 1")
    if mode == "parity" and parity not in ("odd", "even"):
        raise HTTPException(400, "提取类型只能是 odd 或 even")

    with session_scope(user["dir_name"], "pdf-split") as (session_id, sroot):
        input_dir = sroot / "input"
        output_dir = sroot / "output"

        pdf_bytes = await file.read()
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
        base_name = sanitize_filename(Path(safe_name).stem, default="output")
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_files: list[str] = []
        out_pages = 0
        hint = ""

        try:
            # ============ A. 提取指定页 ============
            if mode == "extract":
                try:
                    valid, oor = parse_page_ranges(pages, total)
                except ValueError as e:
                    raise HTTPException(400, str(e))

                if oor:
                    hint = f"（忽略了 {len(oor)} 个越界页码）"

                out_name = f"{base_name}_extracted_{ts}.pdf"
                out = fitz.open()
                try:
                    for p in valid:
                        out.insert_pdf(src, from_page=p, to_page=p)
                    out.save(str(output_dir / out_name))
                finally:
                    out.close()

                output_files = [out_name]
                out_pages = len(valid)
                msg = f"提取完成（{len(valid)} 页 → 1 个文件）{hint}"

            # ============ B. 每页拆开 ============
            elif mode == "per-page":
                for i in range(total):
                    single = fitz.open()
                    try:
                        single.insert_pdf(src, from_page=i, to_page=i)
                        name = f"{base_name}_page_{i+1:03d}_{ts}.pdf"
                        single.save(str(output_dir / name))
                        output_files.append(name)
                    finally:
                        single.close()
                out_pages = total
                msg = f"拆分完成（{total} 页 → {total} 个单页 PDF，请到下方「我的文件」逐个下载）"

            # ============ C. 每隔 N 页抽取 ============
            elif mode == "chunk":
                n = chunk_size
                file_count = 0
                for offset in range(n):
                    picked = list(range(offset, total, n))
                    if not picked:
                        continue
                    file_count += 1
                    out = fitz.open()
                    try:
                        for p in picked:
                            out.insert_pdf(src, from_page=p, to_page=p)
                        name = f"{base_name}_every{n}_{file_count:02d}_{ts}.pdf"
                        out.save(str(output_dir / name))
                        output_files.append(name)
                    finally:
                        out.close()
                out_pages = total
                msg = (
                    f"拆分完成（{total} 页按每隔 {n} 页抽取 "
                    f"→ {file_count} 个 PDF，请到下方「我的文件」逐个下载）"
                )

            # ============ D. 奇数页 / 偶数页 ============
            elif mode == "parity":
                want_odd = (parity == "odd")
                picked = [i for i in range(total) if ((i + 1) % 2 == 1) == want_odd]
                if not picked:
                    label = "奇数" if want_odd else "偶数"
                    raise HTTPException(400, f"该 PDF 没有可提取的{label}页")

                suffix = "odd" if want_odd else "even"
                out_name = f"{base_name}_{suffix}_{ts}.pdf"
                out = fitz.open()
                try:
                    for p in picked:
                        out.insert_pdf(src, from_page=p, to_page=p)
                    out.save(str(output_dir / out_name))
                finally:
                    out.close()

                output_files = [out_name]
                out_pages = len(picked)
                label = "奇数页" if want_odd else "偶数页"
                msg = f"提取完成（{label}共 {len(picked)} 页 → 1 个文件）"

        finally:
            src.close()

        return {
            "message": msg,
            "session_id": session_id,
            "output_files": output_files,
            "page_count": out_pages,
            "file_count": len(output_files),
        }