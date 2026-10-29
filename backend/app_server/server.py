# app_server/server.py
"""FastAPI 应用组装。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.config import settings
from db.schema import init_schema
from db import crack_tasks_repo
from app_server.routers.all_router import all_router
from app_server.routers.static_router import mount_static
from app_server.services.crack_manager import ensure_builtin_dicts


def create_app() -> FastAPI:
    app = FastAPI(title="PDF Tools API", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_schema()

    cnt = crack_tasks_repo.mark_running_as_interrupted()
    if cnt:
        print(f"[crack] 标记了 {cnt} 个中断任务")

    ensure_builtin_dicts()

    # 业务路由
    app.include_router(all_router)

    # 静态托管（必须在业务路由之后，否则会吞掉 /api/*）
    mount_static(app)

    return app


app = create_app()