# app_server/services/storage_service.py
"""存储层：session 目录、文件管理、字典。"""
import json
import re
import secrets
import shutil
import time
from contextlib import contextmanager
from pathlib import Path

from config.config import settings


# ==================== session 目录 ====================
def make_session_dir(user_dir_name: str, tool_id: str) -> str:
    session_id = f"{int(time.time())}_{secrets.token_hex(4)}"
    root = settings.USERS_ROOT / user_dir_name / session_id
    (root / "input").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)
    (root / "meta.json").write_text(
        json.dumps({"tool": tool_id, "created_at": int(time.time())}, ensure_ascii=False),
        encoding="utf-8",
    )
    return session_id


def get_session_path(user_dir_name: str, session_id: str) -> Path:
    return settings.USERS_ROOT / user_dir_name / session_id


def delete_session(user_dir_name: str, session_id: str) -> bool:
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", session_id):
        return False
    p = get_session_path(user_dir_name, session_id)
    user_root = settings.USERS_ROOT / user_dir_name
    try:
        p.resolve().relative_to(user_root.resolve())
    except ValueError:
        return False
    if p.exists():
        shutil.rmtree(p)
        return True
    return False


def list_sessions(user_dir_name: str) -> list[dict]:
    root = settings.USERS_ROOT / user_dir_name
    if not root.exists():
        return []
    out = []
    for child in sorted(root.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        meta = {}
        meta_file = child / "meta.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        out.append({"session_id": child.name, **meta})
    return out


# ==================== session 文件 ====================
def list_session_files(user_dir_name: str, session_id: str) -> dict | None:
    root = get_session_path(user_dir_name, session_id)
    if not root.exists():
        return None
    result = {"session_id": session_id, "input": [], "output": []}
    meta_file = root / "meta.json"
    if meta_file.exists():
        try:
            result.update(json.loads(meta_file.read_text(encoding="utf-8")))
        except Exception:
            pass
    for sub in ("input", "output"):
        sub_dir = root / sub
        if sub_dir.exists():
            for f in sorted(sub_dir.iterdir()):
                if f.is_file():
                    result[sub].append({
                        "name": f.name,
                        "size": f.stat().st_size,
                        "subdir": sub,
                    })
    return result


def get_session_file_path(
    user_dir_name: str, session_id: str, subdir: str, filename: str
) -> Path | None:
    if subdir not in ("input", "output"):
        return None
    safe = Path(filename).name
    p = get_session_path(user_dir_name, session_id) / subdir / safe
    return p if p.is_file() else None


def delete_session_file(
    user_dir_name: str, session_id: str, subdir: str, filename: str
) -> bool:
    p = get_session_file_path(user_dir_name, session_id, subdir, filename)
    if p:
        p.unlink()
        return True
    return False


@contextmanager
def session_scope(user_dir_name: str, tool_id: str):
    session_id = make_session_dir(user_dir_name, tool_id)
    success = False
    try:
        yield session_id, get_session_path(user_dir_name, session_id)
        success = True
    finally:
        if not success:
            delete_session(user_dir_name, session_id)


# ==================== 字典 ====================
def get_builtin_dict_path(level: str) -> Path:
    return settings.DICTS_DIR / f"{level}.txt"


def get_user_dict_dir(user_dir_name: str) -> Path:
    d = settings.USERS_ROOT / user_dir_name / "dicts"
    d.mkdir(parents=True, exist_ok=True)
    return d