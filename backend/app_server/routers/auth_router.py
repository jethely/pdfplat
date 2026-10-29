# app_server/routers/auth_router.py
"""认证路由：注册 / 登录 / 当前用户。"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from config.config import settings
from app_server.services.auth_service import (
    create_user,
    authenticate,
    create_token,
)
from app_server.core.dependencies import get_current_user


router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthReq(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(req: AuthReq):
    username = req.username.strip()
    if not (settings.USERNAME_MIN_LEN <= len(username) <= settings.USERNAME_MAX_LEN):
        raise HTTPException(
            400,
            f"用户名长度需 {settings.USERNAME_MIN_LEN}~{settings.USERNAME_MAX_LEN} 位",
        )
    if len(req.password) < settings.PASSWORD_MIN_LEN:
        raise HTTPException(400, f"密码至少 {settings.PASSWORD_MIN_LEN} 位")
    if len(req.password) > settings.PASSWORD_MAX_LEN:
        raise HTTPException(400, f"密码过长（≤ {settings.PASSWORD_MAX_LEN} 字符）")

    try:
        user = create_user(username, req.password)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {"token": create_token(user["id"]), "user": user}


@router.post("/login")
async def login(req: AuthReq):
    user = authenticate(req.username.strip(), req.password)
    if not user:
        raise HTTPException(401, "用户名或密码错误")
    return {"token": create_token(user["id"]), "user": user}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user