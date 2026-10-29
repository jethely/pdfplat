# app_server/core/dependencies.py
"""FastAPI 认证依赖。"""
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app_server.services.auth_service import verify_token, get_user_by_id

security = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not cred:
        raise HTTPException(status_code=401, detail="未登录")
    payload = verify_token(cred.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    user = get_user_by_id(payload["uid"])
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def get_current_user_allow_query_token(
    token: str = Query(None),
    cred: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    actual_token = cred.credentials if cred else token
    if not actual_token:
        raise HTTPException(status_code=401, detail="未登录")
    payload = verify_token(actual_token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    user = get_user_by_id(payload["uid"])
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user