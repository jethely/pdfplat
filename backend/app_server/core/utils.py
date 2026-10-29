# app_server/core/utils.py
"""通用工具函数：文件名清洗、字节格式化、页码解析、硬件检测。"""
import os
import re

from config.config import settings


# ==================== 文件名清洗 ====================
_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def sanitize_filename(name: str, default: str = "merged") -> str:
    if not name:
        return default

    cleaned = _INVALID_CHARS.sub("_", name)
    cleaned = re.sub(r"[\s_]+", "_", cleaned)
    cleaned = cleaned.strip("_ .")

    if not cleaned or set(cleaned) <= {".", "_"}:
        return default

    if len(cleaned) > settings.MAX_STEM_LEN:
        cleaned = cleaned[:settings.MAX_STEM_LEN].rstrip("_ .")
        if not cleaned:
            return default

    return cleaned


# ==================== 字节格式化 ====================
def format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for unit in ("KB", "MB", "GB"):
        n /= 1024.0
        if n < 1024:
            return f"{n:.1f} {unit}"
    return f"{n:.1f} TB"


# ==================== 页码解析 ====================
def parse_page_ranges(spec: str, total: int) -> tuple[list[int], list[int]]:
    if not spec or not spec.strip():
        raise ValueError("请输入页码")

    valid: set[int] = set()
    out_of_range: list[int] = []

    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            pieces = part.split("-")
            if len(pieces) != 2:
                raise ValueError(f"页码范围格式错误: {part}")
            try:
                a = int(pieces[0].strip())
                b = int(pieces[1].strip())
            except ValueError:
                raise ValueError(f"页码不是整数: {part}")
            lo, hi = (a, b) if a <= b else (b, a)
            for p in range(lo, hi + 1):
                if 1 <= p <= total:
                    valid.add(p - 1)
                else:
                    out_of_range.append(p)
        else:
            try:
                p = int(part)
            except ValueError:
                raise ValueError(f"页码不是整数: {part}")
            if 1 <= p <= total:
                valid.add(p - 1)
            else:
                out_of_range.append(p)

    if not valid:
        if out_of_range:
            raise ValueError(f"所有页码都超出范围（PDF 共 {total} 页）")
        raise ValueError("请输入页码")

    return sorted(valid), sorted(set(out_of_range))


# ==================== 硬件扫描 ====================
def detect_worker_count() -> dict:
    try:
        cpu_logical = os.cpu_count() or 4
    except Exception:
        cpu_logical = 4

    mem_gb = 8.0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_gb = int(line.split()[1]) / (1024 * 1024)
                    break
    except Exception:
        pass

    by_cpu = max(1, int(cpu_logical * settings.CRACK_CPU_TARGET_PCT / 100))
    by_mem = max(1, int(mem_gb * 1024 / settings.CRACK_MEM_PER_WORKER_MB))
    workers = min(by_cpu, by_mem, settings.CRACK_MAX_WORKERS)

    return {
        "cpu_logical": cpu_logical,
        "mem_gb": round(mem_gb, 1),
        "workers": workers,
        "cpu_target_pct": settings.CRACK_CPU_TARGET_PCT,
    }