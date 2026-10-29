from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

from app_server.core.dependencies import get_current_user
from app_server.services.storage_service import make_session_dir, get_session_path
from app_server.services.stamp_operation_service import dispatch_stamp_erase


router = APIRouter(prefix="/api", tags=["stamp-operation"])


@router.post("/stamp-operation")
async def stamp_operation(
    file: UploadFile = File(...),
    pages: str = Form("all"),
    user: dict = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")

    session_id = make_session_dir(user["dir_name"], "stamp-operation")
    sroot = get_session_path(user["dir_name"], session_id)

    pdf_bytes = await file.read()

    try:
        info = dispatch_stamp_erase(
            pdf_bytes=pdf_bytes,
            output_dir=sroot / "output",
            safe_name=file.filename or "input.pdf",
            pages=pages,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": (
            f"{info['action_label']}完成：{info['out_name']} "
            f"(共 {info['pages_affected']} 页, 擦除 {info['stamps_erased']} 个印章)"
        ),
        "session_id": session_id,
        "download_url": f"/download/{user['dir_name']}/{session_id}/{info['out_name']}",
        "meta": {
            "action": info["action"],
            "pages_affected": info["pages_affected"],
            "stamps_erased": info["stamps_erased"],
        },
    }
