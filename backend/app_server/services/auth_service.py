# app_server/services/auth_service.py
"""用户认证业务层：密码哈希、token 签发/验证、用户创建与查询。"""
import base64
import hashlib
import hmac
import json
import secrets
import time

from config.config import settings
from db import users_repo


# ==================== 密码哈希 ====================
def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()


def _gen_user_dir() -> str:
    return secrets.token_hex(16)


# ==================== 用户业务 ====================
def create_user(username: str, password: str) -> dict:
    """注册新用户：先建目录，再插 DB。失败时回滚目录。

    Bug fix：原实现先插 DB 再建目录，若 mkdir 失败会数据不一致。
    """
    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(password, salt)
    dir_name = _gen_user_dir()

    user_root = settings.USERS_ROOT / dir_name
    user_root.mkdir(parents=True, exist_ok=False)

    try:
        user_id = users_repo.insert_user(
            username=username,
            password_hash=pwd_hash,
            salt=salt,
            dir_name=dir_name,
        )
    except Exception:
        # DB 插入失败 → 删掉刚建的目录
        try:
            user_root.rmdir()
        except Exception:
            pass
        raise

    return {"id": user_id, "username": username, "dir_name": dir_name}


def authenticate(username: str, password: str) -> dict | None:
    row = users_repo.find_by_username(username)
    if not row:
        return None
    if not hmac.compare_digest(
        _hash_password(password, row["salt"]),
        row["password_hash"],
    ):
        return None
    return {"id": row["id"], "username": row["username"], "dir_name": row["dir_name"]}


def get_user_by_id(uid: int) -> dict | None:
    row = users_repo.find_by_id(uid)
    if not row:
        return None
    return {"id": row["id"], "username": row["username"], "dir_name": row["dir_name"]}


# ==================== Token ====================
def create_token(user_id: int) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + settings.TOKEN_TTL}
    data = base64.urlsafe_b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("ascii").rstrip("=")
    sig = hmac.new(
        settings.SECRET.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:32]
    return f"{data}.{sig}"


def verify_token(token: str) -> dict | None:
    try:
        data, sig = token.rsplit(".", 1)
        expected = hmac.new(
            settings.SECRET.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(data + "=="))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None