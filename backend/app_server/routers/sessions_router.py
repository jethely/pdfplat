# app_server/routers/sessions_router.py
"""Session 管理：列表 / 详情 / 下载 / 删除。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from urllib.parse import quote

from app_server.core.dependencies import (
    get_current_user,
    get_current_user_allow_query_token,
)
from app_server.services.storage_service import (
    list_sessions,
    delete_session,
    list_session_files,
    get_session_file_path,
    delete_session_file,
)


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ⚠️ 顺序关键：静态路径 /delete-batch 必须在 /{session_id} 之前注册

@router.get("")
async def get_sessions(user: dict = Depends(get_current_user)):
    return {"sessions": list_sessions(user["dir_name"])}


@router.post("/delete-batch")
async def delete_sessions_batch(
    payload: dict,
    user: dict = Depends(get_current_user),
):
    ids = payload.get("session_ids", [])
    deleted = []
    for sid in ids:
        if delete_session(user["dir_name"], sid):
            deleted.append(sid)
    return {"deleted": deleted}


@router.get("/{session_id}")
async def get_session_detail(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    detail = list_session_files(user["dir_name"], session_id)
    if not detail:
        raise HTTPException(404, "session 不存在")
    return detail


@router.get("/{session_id}/files/{subdir}/{filename}")
async def download_session_file(
    session_id: str,
    subdir: str,
    filename: str,
    user: dict = Depends(get_current_user_allow_query_token),
):
    path = get_session_file_path(user["dir_name"], session_id, subdir, filename)
    if not path:
        raise HTTPException(404, "文件不存在")

    ascii_name = filename.encode("ascii", "replace").decode("ascii").replace("?", "_")
    utf8_name = quote(filename)

    return FileResponse(
        path,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition":
                f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_name}",
        },
    )


@router.delete("/{session_id}/files/{subdir}/{filename}")
async def delete_session_file_api(
    session_id: str,
    subdir: str,
    filename: str,
    user: dict = Depends(get_current_user),
):
    ok = delete_session_file(user["dir_name"], session_id, subdir, filename)
    return {"deleted": ok}


@router.delete("/{session_id}")
async def remove_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    ok = delete_session(user["dir_name"], session_id)
    return {"deleted": ok, "session_id": session_id}