#!/usr/bin/env python3
"""列出 FastAPI 应用所有业务路由。

用法：
    python tools/list_routes.py app_server.server:app
"""
import importlib
import sys
from pathlib import Path

# 把 backend/ 加入 sys.path（脚本在 backend/tools/ 下）
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


# 只关心这些 HTTP 方法
_METHODS = ("get", "post", "put", "delete", "patch", "options", "head")


def main():
    if len(sys.argv) < 2:
        print("用法: python tools/list_routes.py <module:app>", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    if ":" not in target:
        print(f"无效入口: {target}（需要 module:app 格式）", file=sys.stderr)
        sys.exit(1)

    mod_name, app_name = target.split(":", 1)
    mod = importlib.import_module(mod_name)
    app = getattr(mod, app_name)

    # ⭐ 通过 OpenAPI schema 拿完整路径列表
    try:
        schema = app.openapi()
    except Exception as e:
        print(f"生成 OpenAPI schema 失败: {e}", file=sys.stderr)
        sys.exit(2)

    items = []
    for path, methods_dict in schema.get("paths", {}).items():
        methods = sorted(
            m.upper() for m in methods_dict.keys() if m.lower() in _METHODS
        )
        if methods:
            items.append((methods, path))

    # 按路径排序
    items.sort(key=lambda x: x[1])

    for methods, path in items:
        print(f"{methods} {path}")
    print(f"---- 共 {len(items)} 条 ----")


if __name__ == "__main__":
    main()