# app_server/routers/font_router.py
from fastapi import APIRouter, Depends

from app_server.core.dependencies import get_current_user
from app_server.services.font_service import list_fonts


router = APIRouter(prefix="/api/fonts", tags=["fonts"])


@router.get("")
async def get_fonts(user: dict = Depends(get_current_user)):
    """返回服务器可用的字体列表（无需管理员权限）。"""
    return {"fonts": list_fonts()}