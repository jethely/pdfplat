# app_server/db/connection.py
"""SQLite 连接与事务上下文。"""
import sqlite3
from contextlib import contextmanager

from config.config import settings


def get_conn() -> sqlite3.Connection:
    """返回一个新连接（调用方负责关闭）。"""
    c = sqlite3.connect(settings.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


@contextmanager
def transaction():
    """自动 commit/rollback + 关闭连接。

    用法：
        with transaction() as conn:
            conn.execute("INSERT ...")
            # 退出 with 自动 commit
    """
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()