# app_server/services/ghostscript.py
"""Ghostscript 封装：调用系统 gs 压缩 PDF。"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from config.config import settings


def _safe_unlink(p: Path) -> None:
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass


def run_ghostscript(in_path: Path, out_path: Path, preset: str) -> None:
    """调用系统 Ghostscript 压缩 PDF。

    gs 输出到 /tmp（AppArmor 白名单目录），再由 Python move 到目标位置。
    失败抛 RuntimeError。
    """
    in_abs = in_path.resolve()
    out_abs = out_path.resolve()

    fd, tmp_str = tempfile.mkstemp(suffix=".pdf", prefix="gs_out_")
    os.close(fd)
    tmp_abs = Path(tmp_str)

    cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.5",
        f"-dPDFSETTINGS={preset}",
        "-dNOPAUSE",
        "-dBATCH",
        "-dQUIET",
        "-dSAFER",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        "-dEmbedAllFonts=true",
        "-dAutoRotatePages=/None",
        f"-sOutputFile={tmp_abs}",
        str(in_abs),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.GS_TIMEOUT,
        )
    except FileNotFoundError:
        _safe_unlink(tmp_abs)
        raise RuntimeError("系统未安装 Ghostscript，请执行：apt install ghostscript")
    except subprocess.TimeoutExpired:
        _safe_unlink(tmp_abs)
        raise RuntimeError(f"Ghostscript 处理超时（>{settings.GS_TIMEOUT} 秒）")

    if result.returncode != 0:
        _safe_unlink(tmp_abs)
        err = (result.stderr or "").strip().splitlines()
        tail = " / ".join(err[-3:]) if err else "未知错误"
        raise RuntimeError(f"Ghostscript 失败: {tail}")

    if not tmp_abs.exists() or tmp_abs.stat().st_size == 0:
        _safe_unlink(tmp_abs)
        raise RuntimeError("Ghostscript 未生成有效输出文件")

    try:
        if out_abs.exists():
            out_abs.unlink()
        shutil.move(str(tmp_abs), str(out_abs))
    except Exception as e:
        _safe_unlink(tmp_abs)
        raise RuntimeError(f"输出文件移动失败: {e}")