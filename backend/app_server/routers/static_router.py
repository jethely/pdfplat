# app_server/routers/static_router.py
"""静态文件托管 + SPA fallback。

由于 FastAPI 的 mount 只能挂在 app 上，不能挂在 router 上，
这里提供一个 mount_static(app) 函数供 server.py 调用。
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.config import BASE_DIR


STATIC_DIR = BASE_DIR / "static"


def mount_static(app: FastAPI) -> None:
    if not STATIC_DIR.exists():
        # 前端还没构建
        @app.get("/")
        async def no_static():
            return {
                "message": "前端未构建，请在 frontend/ 执行 npm run build:backend"
            }
        return

    # 1) 静态资源目录（/assets/*）
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    # 2) SPA fallback（所有未命中 /api/* 和 /assets/* 的路径）
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        last_seg = full_path.split("/")[-1]
        is_asset = full_path.startswith("assets/") or "." in last_seg

        if is_asset:
            file = STATIC_DIR / full_path
            if file.is_file():
                return FileResponse(file)
            raise HTTPException(status_code=404, detail=f"Not found: {full_path}")

        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="index.html not found")