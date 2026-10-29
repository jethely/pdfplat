# app_server/db/schema.py
"""表结构定义与初始化。"""
from db.connection import transaction
from config.config import settings


CREATE_USERS = """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    UNIQUE NOT NULL,
        password_hash TEXT    NOT NULL,
        salt          TEXT    NOT NULL,
        dir_name      TEXT    UNIQUE NOT NULL,
        created_at    TEXT    DEFAULT (datetime('now'))
    )
"""

CREATE_CRACK_TASKS = """
    CREATE TABLE IF NOT EXISTS crack_tasks (
        task_id        TEXT PRIMARY KEY,
        user_dir_name  TEXT NOT NULL,
        session_id     TEXT NOT NULL,
        sroot          TEXT NOT NULL,
        mode           TEXT,
        status         TEXT,
        phase          TEXT,
        attempts       INTEGER DEFAULT 0,
        speed          INTEGER DEFAULT 0,
        progress       REAL    DEFAULT 0,
        eta_seconds    INTEGER,
        total_estimate INTEGER,
        found_password TEXT,
        success        INTEGER,
        error          TEXT,
        elapsed        REAL    DEFAULT 0,
        workers        INTEGER DEFAULT 0,
        hardware_json  TEXT,
        started_at     REAL,
        updated_at     REAL
    )
"""

CREATE_CRACK_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_crack_user
    ON crack_tasks(user_dir_name, updated_at DESC)
"""


def init_schema() -> None:
    """建表 + 建目录。服务启动时调用一次。"""
    # 目录先建好
    settings.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    settings.USERS_ROOT.mkdir(parents=True, exist_ok=True)
    settings.DICTS_DIR.mkdir(parents=True, exist_ok=True)

    with transaction() as conn:
        conn.execute(CREATE_USERS)
        conn.execute(CREATE_CRACK_TASKS)
        conn.execute(CREATE_CRACK_INDEX)