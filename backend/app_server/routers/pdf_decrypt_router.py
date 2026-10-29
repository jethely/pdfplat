# app_server/routers/pdf_decrypt_router.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from typing import Optional
from pathlib import Path
import time

import pymupdf as fitz

from app_server.core.dependencies import get_current_user
from app_server.core.utils import sanitize_filename
from app_server.services.storage_service import (
    session_scope,
    get_builtin_dict_path,
    get_user_dict_dir,
)
from app_server.services import crack_manager


router = APIRouter(prefix="/api/pdf-decrypt", tags=["pdf-decrypt"])


@router.post("/start")
async def pdf_decrypt_start(
    file: UploadFile = File(...),
    mode: str = Form("smart"),
    charset: str = Form("0123456789"),
    min_len: int = Form(1),
    max_len: int = Form(6),
    mask: str = Form(""),
    dict_source: str = Form("builtin-simple"),
    dict_file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    # ---- 参数校验 ----
    if mode not in ("smart", "dictionary", "brute", "mask"):
        raise HTTPException(400, f"不支持的破解模式: {mode}")
    if mode == "brute":
        if not charset:
            raise HTTPException(400, "暴力破解需要指定字符集")
        if min_len < 1 or max_len < min_len or max_len > 11:
            raise HTTPException(400, "长度范围需在 1~11 之间")
    if mode == "mask":
        if not mask or "?" not in mask:
            raise HTTPException(400, "掩码必须包含至少一个 ?")
        if len(mask) > 16:
            raise HTTPException(400, "掩码过长（≤ 16 字符）")

    with session_scope(user["dir_name"], "pdf-decrypt") as (session_id, sroot):
        input_dir = sroot / "input"

        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(400, "上传的文件为空")
        safe_name = (file.filename or "input.pdf").replace("/", "_").replace("\\", "_")
        (input_dir / safe_name).write_bytes(pdf_bytes)

        # ---- 字典处理 ----
        dict_path = None
        if mode == "dictionary":
            if dict_source == "custom":
                if not dict_file:
                    raise HTTPException(400, "自定义字典模式需要上传字典文件")
                dict_bytes = await dict_file.read()
                if not dict_bytes:
                    raise HTTPException(400, "字典文件为空")
                user_dict_dir = get_user_dict_dir(user["dir_name"])
                ts = time.strftime("%Y%m%d_%H%M%S")
                raw = (dict_file.filename or "custom.txt").replace("/", "_").replace("\\", "_")
                dict_path = user_dict_dir / f"{ts}_{raw}"
                dict_path.write_bytes(dict_bytes)
            else:
                level = dict_source.replace("builtin-", "")
                if level not in ("simple", "medium", "complex"):
                    raise HTTPException(400, f"未知的内置字典: {dict_source}")
                dict_path = get_builtin_dict_path(level)
                if not dict_path.exists() or dict_path.stat().st_size == 0:
                    raise HTTPException(
                        400,
                        f"内置「{level}」字典为空，请先在服务器上放置字典文件：{dict_path}",
                    )

        options = {
            "mode": mode,
            "charset": charset,
            "min_len": min_len,
            "max_len": max_len,
            "mask": mask,
            "dict_path": dict_path,
        }

        task_id = crack_manager.start_task(
            user_dir_name=user["dir_name"],
            session_id=session_id,
            sroot=sroot,
            mode=mode,
            options=options,
            pdf_bytes=pdf_bytes,
        )

        return {"task_id": task_id, "session_id": session_id}


@router.get("/tasks")
async def pdf_decrypt_tasks(user: dict = Depends(get_current_user)):
    """列出当前用户最近的破解任务（最多 20 条）"""
    return {"tasks": crack_manager.list_tasks(user["dir_name"], limit=20)}


@router.get("/status/{task_id}")
async def pdf_decrypt_status(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    resp = crack_manager.get_task(task_id, user["dir_name"])
    if not resp:
        raise HTTPException(404, "任务不存在")
    return resp


@router.post("/cancel/{task_id}")
async def pdf_decrypt_cancel(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    ok = crack_manager.cancel_task(task_id, user["dir_name"])
    if not ok:
        # 内存里没有 —— 要么已完成，要么不存在
        from db import crack_tasks_repo
        db_task = crack_tasks_repo.find_task(task_id)
        if not db_task or db_task["user_dir_name"] != user["dir_name"]:
            raise HTTPException(404, "任务不存在")
        raise HTTPException(400, "任务已不在运行中，无法取消")
    return {"ok": True}


@router.post("/apply/{task_id}")
async def pdf_decrypt_apply(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    task = crack_manager.get_task_for_apply(task_id, user["dir_name"])
    if not task:
        raise HTTPException(400, "尚未破解成功或任务不存在")

    sroot = Path(task["sroot"])
    input_dir = sroot / "input"
    output_dir = sroot / "output"
    if not input_dir.exists():
        raise HTTPException(404, "原文件已被删除，无法解密")

    pdf_files = [
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    ]
    if not pdf_files:
        raise HTTPException(404, "找不到原文件")
    in_path = pdf_files[0]

    try:
        doc = fitz.open(str(in_path))
        if not doc.authenticate(task["found_password"]):
            doc.close()
            raise HTTPException(500, "密码验证失败")
        base_name = sanitize_filename(in_path.stem, default="output")
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_name = f"{base_name}_decrypted_{ts}.pdf"
        doc.save(str(output_dir / out_name), garbage=4, deflate=True)
        doc.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"保存解密文件失败: {e}")

    return {
        "message": f"解密完成（密码：{task['found_password']}）",
        "session_id": task["session_id"],
        "output_files": [out_name],
    }