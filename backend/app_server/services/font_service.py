# app_server/services/font_service.py
"""字体库管理：扫描、映射、解析。"""
from pathlib import Path

from config.config import settings


# PDF 里常见的字体名 → storage/fonts 下的文件名
FONT_ALIAS = {
    # 中文
    "simsun": "simsun.ttc",
    "nsimsun": "simsun.ttc",
    "宋体": "simsun.ttc",
    "simhei": "simhei.ttf",
    "黑体": "simhei.ttf",
    "simfang": "simfang.ttf",
    "仿宋": "simfang.ttf",
    "simli": "SIMLI.TTF",
    "隶书": "SIMLI.TTF",
    "simyou": "SIMYOU.TTF",
    "幼圆": "SIMYOU.TTF",
    # 微软雅黑
    "microsoft yahei": "msyh.ttf",
    "msyh": "msyh.ttf",
    "微软雅黑": "msyh.ttf",
    "msyhbd": "msyhbd.ttf",
    # 方正系列
    "fzssk": "FZSSK.TTF",
    "方正书宋": "FZSSK.TTF",
    "fzhtk": "FZHTK.TTF",
    "方正黑体": "FZHTK.TTF",
    "fzfsk": "FZFSK.TTF",
    "方正仿宋": "FZFSK.TTF",
    "fzktk": "FZKTK.TTF",
    "方正楷体": "FZKTK.TTF",
}

# 友好名称（给前端显示）
FONT_DISPLAY_NAME = {
    "simsun.ttc": "宋体",
    "simhei.ttf": "黑体",
    "simfang.ttf": "仿宋",
    "SIMLI.TTF": "隶书",
    "SIMYOU.TTF": "幼圆",
    "msyh.ttf": "微软雅黑",
    "msyhbd.ttf": "微软雅黑粗体",
    "MSYH.TTC": "微软雅黑（TTC）",
    "MSYHBD.TTC": "微软雅黑粗体（TTC）",
    "FZSSK.TTF": "方正书宋",
    "FZHTK.TTF": "方正黑体",
    "FZFSK.TTF": "方正仿宋",
    "FZKTK.TTF": "方正楷体",
    "FZLSK.TTF": "方正隶书",
    "FZWBK.TTF": "方正魏碑",
    "FZXBSK.TTF": "方正小标宋",
    "FZXH1K.TTF": "方正细黑一",
    "FZXKK.TTF": "方正细楷",
    "FZYTK.TTF": "方正姚体",
    "FZCCHK.TTF": "方正粗黑",
}

# 推荐字体（前端默认排序靠前）
PREFERRED_ORDER = [
    "simsun.ttc", "simhei.ttf", "simfang.ttf",
    "msyh.ttf", "msyhbd.ttf",
    "FZSSK.TTF", "FZHTK.TTF", "FZFSK.TTF", "FZKTK.TTF",
]

# 支持的后缀
_ALLOWED_EXTS = {".ttf", ".ttc", ".otf"}


def list_fonts() -> list[dict]:
    """扫描 storage/fonts，返回清单。"""
    if not settings.FONTS_DIR.exists():
        return []

    out = []
    for f in sorted(settings.FONTS_DIR.iterdir()):
        if not f.is_file() or f.suffix.lower() not in _ALLOWED_EXTS:
            continue
        out.append({
            "file": f.name,
            "path": str(f),
            "display_name": FONT_DISPLAY_NAME.get(f.name, f.stem),
            "size_kb": round(f.stat().st_size / 1024, 1),
            "preferred": f.name in PREFERRED_ORDER,
        })

    # 排序：推荐字体在前，然后按文件名
    out.sort(key=lambda x: (
        0 if x["preferred"] else 1,
        PREFERRED_ORDER.index(x["file"]) if x["file"] in PREFERRED_ORDER else 999,
        x["file"],
    ))
    return out


def resolve_font_path(name_or_file: str) -> Path | None:
    """接受「文件名」或「友好名」或「PDF 字体名」，返回 storage/fonts 下的路径。"""
    if not name_or_file:
        return None
    key = name_or_file.strip().lower()

    # 1. 直接文件名
    for f in settings.FONTS_DIR.iterdir() if settings.FONTS_DIR.exists() else []:
        if f.name.lower() == key:
            return f

    # 2. 别名映射
    file_name = FONT_ALIAS.get(key)
    if file_name:
        p = settings.FONTS_DIR / file_name
        if p.exists():
            return p

    return None


def match_pdf_font(pdf_font_name: str) -> Path | None:
    """把 PDF 里提取的字体名匹配到本地字体。

    PDF 字体名常带子集前缀，如 "ABCDEF+SimSun"。
    """
    if not pdf_font_name:
        return None

    # 去掉子集前缀
    name = pdf_font_name.split("+", 1)[-1] if "+" in pdf_font_name else pdf_font_name
    name = name.strip().lower()

    # 去掉常见后缀
    for suffix in ("-bold", "-italic", "-bolditalic", "bold", "italic",
                   "mt", "regular", "ps", "pro"):
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip("-_ ")
            break

    return resolve_font_path(name)