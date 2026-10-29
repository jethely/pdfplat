# config/config.py
"""统一配置加载。

优先级：环境变量 > config.toml > 默认值
"""
import os
import tomllib
from pathlib import Path


# backend/ 目录（config.py 的父目录的父目录）
BASE_DIR = Path(__file__).resolve().parent.parent

# 允许通过环境变量覆盖
_ENV_MAP = {
    ("auth", "secret"):       "APP_SECRET",
    ("server", "host"):       "APP_HOST",
    ("server", "port"):       "APP_PORT",
    ("logging", "level"):     "APP_LOG_LEVEL",
}


def _load_toml() -> dict:
    path = BASE_DIR / "config.toml"
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with open(path, "rb") as f:
        return tomllib.load(f)


def _apply_env_overrides(cfg: dict) -> dict:
    for (section, key), env_name in _ENV_MAP.items():
        value = os.environ.get(env_name)
        if value is None:
            continue
        cfg.setdefault(section, {})
        # 数字型字段自动转换
        if key in ("port", "token_ttl_seconds", "max_duration_seconds",
                   "cpu_target_pct", "mem_per_worker_mb", "max_workers",
                   "timeout_seconds", "password_min_len", "password_max_len",
                   "username_min_len", "username_max_len", "max_stem_len"):
            try:
                value = int(value)
            except ValueError:
                pass
        cfg[section][key] = value
    return cfg


_cfg = _apply_env_overrides(_load_toml())


class Settings:
    # ---------- server ----------
    HOST: str = _cfg["server"]["host"]
    PORT: int = int(_cfg["server"]["port"])

    # ---------- auth ----------
    SECRET: str = _cfg["auth"]["secret"]
    TOKEN_TTL: int = int(_cfg["auth"]["token_ttl_seconds"])
    USERNAME_MIN_LEN: int = int(_cfg["auth"]["username_min_len"])
    USERNAME_MAX_LEN: int = int(_cfg["auth"]["username_max_len"])
    PASSWORD_MIN_LEN: int = int(_cfg["auth"]["password_min_len"])
    PASSWORD_MAX_LEN: int = int(_cfg["auth"]["password_max_len"])

    # ---------- storage ----------
    STORAGE_ROOT: Path = BASE_DIR / _cfg["storage"]["root"]
    USERS_ROOT: Path = STORAGE_ROOT / "users"
    DB_PATH: Path = STORAGE_ROOT / "app.db"
    DICTS_DIR: Path = STORAGE_ROOT / "dicts"
    FONTS_DIR: Path = STORAGE_ROOT / _cfg["storage"].get("fonts_dir", "fonts")
    
    # ---------- crack ----------
    CRACK_MAX_DURATION: int = int(_cfg["crack"]["max_duration_seconds"])
    CRACK_CPU_TARGET_PCT: int = int(_cfg["crack"]["cpu_target_pct"])
    CRACK_MEM_PER_WORKER_MB: int = int(_cfg["crack"]["mem_per_worker_mb"])
    CRACK_MAX_WORKERS: int = int(_cfg["crack"]["max_workers"])

    # ---------- file ----------
    MAX_STEM_LEN: int = int(_cfg["file"]["max_stem_len"])

    # ---------- ghostscript ----------
    GS_PRESETS: dict = {
        "light":  _cfg["ghostscript"]["preset_light"],
        "medium": _cfg["ghostscript"]["preset_medium"],
        "high":   _cfg["ghostscript"]["preset_high"],
    }
    GS_TIMEOUT: int = int(_cfg["ghostscript"]["timeout_seconds"])

    # ---------- logging ----------
    LOG_LEVEL: str = _cfg["logging"]["level"]


settings = Settings()

# 首次加载时把 storage 目录建起来
settings.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
settings.USERS_ROOT.mkdir(parents=True, exist_ok=True)
settings.DICTS_DIR.mkdir(parents=True, exist_ok=True)
settings.FONTS_DIR.mkdir(parents=True, exist_ok=True)