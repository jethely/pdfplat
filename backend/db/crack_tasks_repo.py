# app_server/db/crack_tasks_repo.py
"""crack_tasks 表 CRUD。"""
import json
import time

from db.connection import transaction, get_conn


def insert_task(task: dict) -> None:
    with transaction() as conn:
        conn.execute("""
            INSERT INTO crack_tasks
            (task_id, user_dir_name, session_id, sroot, mode, status, phase,
             attempts, speed, progress, eta_seconds, total_estimate,
             found_password, success, error, elapsed, workers,
             hardware_json, started_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task["task_id"],
            task["user_dir_name"],
            task["session_id"],
            task["sroot"],
            task.get("mode"),
            task.get("status", "running"),
            task.get("phase"),
            task.get("attempts", 0),
            task.get("speed", 0),
            task.get("progress", 0.0),
            task.get("eta_seconds"),
            task.get("total_estimate"),
            task.get("found_password"),
            (1 if task.get("success") is True else
             0 if task.get("success") is False else None),
            task.get("error"),
            task.get("elapsed", 0.0),
            task.get("workers", 0),
            json.dumps(task.get("hardware")) if task.get("hardware") else None,
            task.get("started_at", time.time()),
            time.time(),
        ))


def update_task(task_id: str, **fields) -> None:
    if not fields:
        return

    # 特殊字段预处理
    if "hardware" in fields:
        hw = fields.pop("hardware")
        fields["hardware_json"] = json.dumps(hw) if hw else None
    if "success" in fields:
        v = fields["success"]
        fields["success"] = 1 if v is True else (0 if v is False else None)

    fields["updated_at"] = time.time()
    cols = ", ".join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [task_id]

    with transaction() as conn:
        conn.execute(f"UPDATE crack_tasks SET {cols} WHERE task_id = ?", vals)


def _row_to_dict(row) -> dict:
    d = dict(row)
    if d.get("hardware_json"):
        try:
            d["hardware"] = json.loads(d["hardware_json"])
        except Exception:
            d["hardware"] = None
    else:
        d["hardware"] = None
    d.pop("hardware_json", None)
    if d.get("success") is not None:
        d["success"] = bool(d["success"])
    return d


def find_task(task_id: str) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM crack_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row) if row else None


def list_tasks(user_dir_name: str, limit: int = 20) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM crack_tasks WHERE user_dir_name = ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (user_dir_name, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def mark_running_as_interrupted() -> int:
    """服务启动时调用：把所有 running 改成 interrupted。

    返回受影响的行数。
    """
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE crack_tasks SET status = 'interrupted', "
            "error = '服务重启，任务已中断', updated_at = ? "
            "WHERE status = 'running'",
            (time.time(),),
        )
        return cur.rowcount