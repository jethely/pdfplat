# app_server/db/users_repo.py
"""users 表 CRUD。纯 SQL，不做密码哈希。"""
import sqlite3

from db.connection import transaction, get_conn


def insert_user(
    username: str,
    password_hash: str,
    salt: str,
    dir_name: str,
) -> int:
    """插入用户，返回 user_id。

    若用户名冲突抛 ValueError("用户名已存在")。
    """
    try:
        with transaction() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, salt, dir_name) "
                "VALUES (?, ?, ?, ?)",
                (username, password_hash, salt, dir_name),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            raise ValueError("用户名已存在")
        raise


def find_by_username(username: str) -> dict | None:
    """返回包含所有列的 dict（密码验证在 service 层做）。"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def find_by_id(uid: int) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (uid,)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None