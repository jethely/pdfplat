# app_server/services/crack_manager.py
"""PDF 破解任务管理：线程 + 内存状态 + DB 落库。"""
import threading
import time
import uuid
from itertools import product

import pymupdf as fitz

from config.config import settings
from app_server.core.utils import detect_worker_count
from db import crack_tasks_repo


# ==================== 内存状态 ====================
_crack_tasks: dict[str, dict] = {}


# ==================== 常见密码 ====================
COMMON_PASSWORDS = [
    "", "123456", "password", "12345678", "qwerty", "123456789",
    "12345", "1234", "111111", "1234567", "dragon", "123123",
    "baseball", "abc123", "football", "monkey", "letmein", "696969",
    "shadow", "master", "666666", "qwertyuiop", "123321", "mustang",
    "1234567890", "michael", "654321", "superman", "1qaz2wsx",
    "7777777", "121212", "000000", "qazwsx", "123qwe", "killer",
    "trustno1", "jordan", "jennifer", "zxcvbnm", "asdfgh", "hunter",
    "buster", "soccer", "harley", "batman", "andrew", "tigger",
    "sunshine", "iloveyou", "2000", "charlie", "robert", "thomas",
    "hockey", "ranger", "daniel", "starwars", "klaster", "112233",
    "george", "asshole", "computer", "michelle", "jessica", "pepper",
    "1111", "zxcvbn", "555555", "11111111", "131313", "freedom",
    "777777", "pass", "fuck", "maggie", "159753", "aaaaaa",
    "ginger", "princess", "joshua", "cheese", "amanda", "summer",
    "love", "ashley", "6969", "nicole", "chelsea", "biteme",
    "matthew", "access", "yankees", "987654321", "dallas", "austin",
    "thunder", "taylor", "matrix", "admin", "admin123", "root",
    "welcome", "solo", "secret", "qq123456", "123abc", "asdf1234",
    "a123456", "abc123456", "qq123456789", "aa123456", "123456a",
    "123456789a", "wang123456", "woaini", "5201314", "woaini1314",
    "520520", "1314520", "zxcvbnm123", "1122334455", "000000000",
    "88888888", "66666666", "123123123", "1111111111", "11223344",
    "a123456789", "lovely", "doudou", "caonima", "147258", "wang",
    "samsung", "nokia", "12345678910", "9876543210",
    "13800138000", "10086", "10010", "10000", "12345678901",
    "13912345678", "13812345678", "15912345678", "18812345678",
]


# ==================== 内置字典初始化 ====================
def ensure_builtin_dicts() -> None:
    """首次启动时生成 simple.txt；medium/complex 由用户自行放置。"""
    dicts_dir = settings.DICTS_DIR
    dicts_dir.mkdir(parents=True, exist_ok=True)

    simple_path = dicts_dir / "simple.txt"
    if not simple_path.exists():
        lines: set[str] = set()
        for p in COMMON_PASSWORDS:
            if p:
                lines.add(p)
        for n in range(0, 10000):
            lines.add(f"{n:04d}")
            lines.add(f"{n:06d}")
        simple_path.write_text("\n".join(sorted(lines)), encoding="utf-8")
        print(f"[dicts] 已生成内置简单字典: {simple_path}（{len(lines)} 条）")

    for level in ("medium", "complex"):
        p = dicts_dir / f"{level}.txt"
        if not p.exists():
            p.write_text("", encoding="utf-8")
            print(f"[dicts] 提示：{level}.txt 为空。可下载常见密码字典放入 {p}")


# ==================== 辅助 ====================
def _try_password(doc: fitz.Document, password: str) -> bool:
    try:
        return doc.authenticate(password) > 0
    except Exception:
        return False


def _estimate_total(mode: str, options: dict) -> int | None:
    try:
        if mode == "smart":
            return 1000000 + len(COMMON_PASSWORDS)
        if mode == "brute":
            base = len(options["charset"])
            n = 0
            for L in range(options["min_len"], options["max_len"] + 1):
                n += base ** L
            return n
        if mode == "mask":
            return len(options["charset"]) ** options["mask"].count("?")
        return None
    except Exception:
        return None


def _gen_mask_candidates(mask: str, charset: str):
    slots = []
    for ch in mask:
        slots.append(list(charset) if ch == "?" else [ch])
    for combo in product(*slots):
        yield "".join(combo)


def _gen_shard(mode: str, options: dict, shard_idx: int, total_shards: int):
    """每个 shard 负责一部分候选。所有 shard 的并集 = 全量候选。"""
    if mode == "smart":
        if shard_idx == 0:
            yield ""
            for p in COMMON_PASSWORDS:
                if p:
                    yield p
        else:
            n_shards = total_shards - 1
            per = 1000000 // n_shards
            start = (shard_idx - 1) * per
            end = start + per if shard_idx < total_shards - 1 else 1000000
            for n in range(start, end):
                yield f"{n:06d}"
        return

    if mode == "dictionary":
        path = options["dict_path"]
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i % total_shards == shard_idx:
                    pwd = line.rstrip("\r\n")
                    if pwd:
                        yield pwd
        return

    if mode == "brute":
        charset = options["charset"]
        min_len = options["min_len"]
        max_len = options["max_len"]
        total = _estimate_total("brute", options) or 0
        if total == 0:
            return
        per = max(1, total // total_shards)
        my_start = shard_idx * per
        my_end = my_start + per if shard_idx < total_shards - 1 else total

        idx = 0
        base = len(charset)
        for L in range(min_len, max_len + 1):
            cnt = base ** L
            if idx + cnt <= my_start:
                idx += cnt
                continue
            if idx >= my_end:
                return
            for combo in product(charset, repeat=L):
                if my_start <= idx < my_end:
                    yield "".join(combo)
                idx += 1
                if idx >= my_end:
                    return
        return

    if mode == "mask":
        mask = options["mask"]
        charset = options["charset"]
        first_q = mask.index("?")
        base = len(charset)

        if total_shards <= base:
            for ci, ch in enumerate(charset):
                if ci != shard_idx:
                    continue
                new_mask = mask[:first_q] + ch + mask[first_q + 1:]
                yield from _gen_mask_candidates(new_mask, charset)
        else:
            for i, c in enumerate(_gen_mask_candidates(mask, charset)):
                if i % total_shards == shard_idx:
                    yield c
        return


# ==================== 破解主流程 ====================
def _run_crack(task_id: str, pdf_bytes: bytes, options: dict):
    task = _crack_tasks.get(task_id)
    if not task:
        return

    # 快速探测
    try:
        probe = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        task["status"] = "failed"
        task["error"] = f"无法打开 PDF: {e}"
        crack_tasks_repo.update_task(task_id, status="failed", error=task["error"])
        return
    if not probe.is_encrypted:
        probe.close()
        task["status"] = "failed"
        task["error"] = "PDF 未加密，无需破解"
        crack_tasks_repo.update_task(task_id, status="failed", error=task["error"])
        return
    probe.close()

    hw = detect_worker_count()
    workers = hw["workers"]
    task["workers"] = workers
    task["hardware"] = hw
    task["phase"] = f"运行中（{workers} 线程）"
    task["total_estimate"] = _estimate_total(options["mode"], options)

    crack_tasks_repo.update_task(
        task_id,
        workers=workers,
        hardware=hw,
        phase=task["phase"],
        total_estimate=task["total_estimate"],
    )

    stop_event = threading.Event()
    lock = threading.Lock()
    state = {"attempts": 0, "found_password": None}
    start_time = time.time()

    def worker(shard_idx: int):
        doc = None
        local = 0
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for pwd in _gen_shard(options["mode"], options, shard_idx, workers):
                if stop_event.is_set() or task.get("cancelled"):
                    break
                local += 1
                if _try_password(doc, pwd):
                    with lock:
                        if state["found_password"] is None:
                            state["found_password"] = pwd
                    stop_event.set()
                    break
                if local % 200 == 0:
                    with lock:
                        state["attempts"] += 200
                    if time.time() - start_time > settings.CRACK_MAX_DURATION:
                        stop_event.set()
                        break
        except Exception:
            pass
        finally:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass
            with lock:
                if local % 200 != 0:
                    state["attempts"] += local % 200

    threads = [
        threading.Thread(target=worker, args=(i,), daemon=True)
        for i in range(workers)
    ]
    for t in threads:
        t.start()

    last_db_flush = time.time()

    while True:
        if stop_event.is_set():
            break
        if all(not t.is_alive() for t in threads):
            break
        if task.get("cancelled"):
            stop_event.set()
            break
        time.sleep(0.5)
        elapsed = time.time() - start_time
        with lock:
            attempts = state["attempts"]
        task["attempts"] = attempts
        task["elapsed"] = elapsed
        task["speed"] = int(attempts / elapsed) if elapsed > 0 else 0
        if task["total_estimate"]:
            task["progress"] = min(1.0, attempts / task["total_estimate"])
            if task["speed"] > 0:
                remain = max(0, task["total_estimate"] - attempts)
                task["eta_seconds"] = int(remain / task["speed"])

        now = time.time()
        if now - last_db_flush >= 5:
            crack_tasks_repo.update_task(
                task_id,
                attempts=task["attempts"],
                speed=task["speed"],
                progress=task["progress"],
                eta_seconds=task["eta_seconds"],
                elapsed=task["elapsed"],
            )
            last_db_flush = now

    for t in threads:
        t.join(timeout=2)

    elapsed = time.time() - start_time
    with lock:
        final_attempts = state["attempts"]
        found = state["found_password"]

    task["attempts"] = final_attempts
    task["elapsed"] = elapsed

    if found is not None:
        task["success"] = True
        task["found_password"] = found
        task["status"] = "done"
    elif task.get("cancelled"):
        task["status"] = "cancelled"
    else:
        task["success"] = False
        task["status"] = "done"
        task["error"] = "未找到密码（已穷尽所有候选）"

    crack_tasks_repo.update_task(
        task_id,
        status=task["status"],
        attempts=task["attempts"],
        speed=task["speed"],
        progress=task["progress"],
        elapsed=task["elapsed"],
        found_password=task.get("found_password"),
        success=task.get("success"),
        error=task.get("error"),
        phase=task.get("phase"),
    )


# ==================== 对外接口 ====================
def _task_to_response(task: dict) -> dict:
    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "phase": task.get("phase"),
        "attempts": task.get("attempts", 0),
        "speed": task.get("speed", 0),
        "progress": task.get("progress", 0.0),
        "eta_seconds": task.get("eta_seconds"),
        "total_estimate": task.get("total_estimate"),
        "found_password": task.get("found_password"),
        "success": task.get("success"),
        "error": task.get("error"),
        "elapsed": int(task.get("elapsed", 0)),
        "workers": task.get("workers", 0),
        "hardware": task.get("hardware"),
    }


def start_task(
    user_dir_name: str,
    session_id: str,
    sroot,
    mode: str,
    options: dict,
    pdf_bytes: bytes,
) -> str:
    """创建任务、落库、启动线程，返回 task_id。"""
    task_id = uuid.uuid4().hex
    _crack_tasks[task_id] = {
        "task_id": task_id,
        "user_dir_name": user_dir_name,
        "session_id": session_id,
        "sroot": str(sroot),
        "status": "running",
        "mode": mode,
        "phase": "初始化",
        "attempts": 0,
        "speed": 0,
        "progress": 0.0,
        "eta_seconds": None,
        "total_estimate": None,
        "found_password": None,
        "success": None,
        "error": None,
        "cancelled": False,
        "elapsed": 0,
        "workers": 0,
        "hardware": None,
        "started_at": time.time(),
    }
    crack_tasks_repo.insert_task(_crack_tasks[task_id])

    threading.Thread(
        target=_run_crack,
        args=(task_id, pdf_bytes, options),
        daemon=True,
    ).start()

    return task_id


def get_task(task_id: str, user_dir_name: str) -> dict | None:
    """内存优先，DB 兜底。"""
    live = _crack_tasks.get(task_id)
    if live and live["user_dir_name"] == user_dir_name:
        return _task_to_response(live)

    db_task = crack_tasks_repo.find_task(task_id)
    if not db_task or db_task["user_dir_name"] != user_dir_name:
        return None
    return _task_to_response(db_task)


def list_tasks(user_dir_name: str, limit: int = 20) -> list[dict]:
    tasks = crack_tasks_repo.list_tasks(user_dir_name, limit=limit)
    result = []
    for t in tasks:
        live = _crack_tasks.get(t["task_id"])
        if live and live["status"] == "running":
            result.append(_task_to_response(live))
        else:
            result.append(_task_to_response(t))
    return result


def cancel_task(task_id: str, user_dir_name: str) -> bool:
    """True = 已标记取消；False = 不在内存中（已完成或不存在）。"""
    task = _crack_tasks.get(task_id)
    if not task or task["user_dir_name"] != user_dir_name:
        return False
    task["cancelled"] = True
    return True


def get_task_for_apply(task_id: str, user_dir_name: str) -> dict | None:
    """获取可应用的任务（内存或 DB），校验成功且找到密码。"""
    task = _crack_tasks.get(task_id)
    if not task:
        task = crack_tasks_repo.find_task(task_id)
    if not task or task["user_dir_name"] != user_dir_name:
        return None
    if not task.get("success") or not task.get("found_password"):
        return None
    return task