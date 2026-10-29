.PHONY: help install-backend run-backend run-frontend dev stop-dev \
        clean clean-venv deep-clean check-env setup-venv restart-backend list-routes init_dirs frontend_init_dirs

# ==================== 路径配置 ====================
PYTHON = python3
PIP = pip3
PROJECT_ROOT = /mount/nvme0/pdfplat
VENV_DIR = .venv
VENV_PYTHON = $(VENV_DIR)/bin/python
VENV_PIP = $(VENV_DIR)/bin/pip
VENV_UVICORN = $(VENV_DIR)/bin/uvicorn

# ==================== 后端入口 ====================
APP ?= app_server.server:app

# ==================== 端口 ====================
BACKEND_PORT = 8080
FRONTEND_PORT = 8090

# Python 版本检查
PYTHON_VERSION_OK := $(shell $(PYTHON) -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null)

# ==================== 帮助 ====================
help:
	@echo "PDF Tools 开发指令集"
	@echo ""
	@echo "  make install-backend    安装后端依赖"
	@echo "  make setup-venv         重建虚拟环境"
	@echo "  make run-backend        启动后端 (端口 $(BACKEND_PORT)，入口 $(APP))"
	@echo "  make run-frontend       启动前端 (端口 $(FRONTEND_PORT))"
	@echo "  make dev                后台启动前后端"
	@echo "  make stop-dev           停止所有开发服务"
	@echo "  make list-routes        列出当前后端所有路由"
	@echo "  make check-env          检查环境状态"
	@echo "  make restart-backend    重启后端"
	@echo "  make clean / deep-clean 清理"
	@echo "  make init_dirs          初始化后端目录结构（新架构）"
	@echo "  make frontend_init_dirs 初始化前端目录 + 生成默认文件"

# ==================== 虚拟环境 ====================
$(VENV_DIR):
	@echo "检查 Python 版本..."
	@if [ "$(PYTHON_VERSION_OK)" != "True" ]; then \
		echo "错误: 需要 Python 3.10 或更高版本"; \
		exit 1; \
	fi
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip

$(VENV_UVICORN): $(VENV_DIR)
	@if ! $(VENV_PIP) list 2>/dev/null | grep -q "uvicorn"; then \
		$(VENV_PIP) install "uvicorn[standard]"; \
	fi

install-backend: $(VENV_DIR)
	@echo "安装后端依赖..."
	$(VENV_PIP) install -r backend/requirements.txt

setup-venv: clean-venv $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip setuptools wheel

# ==================== 初始化目录 ====================
init_dirs:
	@echo "初始化目录结构..."
	@# ---- backend ----
	@mkdir -p backend/app_server/routers
	@mkdir -p backend/app_server/core
	@mkdir -p backend/app_server/services
	@mkdir -p backend/config
	@mkdir -p backend/storage/users
	@mkdir -p backend/storage/dicts
	@# ---- 生成空的 __init__.py（已存在则跳过）----
	@for d in \
		backend/app_server \
		backend/app_server/routers \
		backend/app_server/core \
		backend/app_server/services \
		backend/config ; do \
		[ -f "$$d/__init__.py" ] || touch "$$d/__init__.py"; \
	done
	@echo "✅ 目录结构初始化完成："
	@echo "   backend/config/"
	@echo "   backend/app_server/{routers,core,services}/"
	@echo "   backend/storage/{users,dicts}/"
	@echo "   backend/storage/{users,dicts}/"

# ==================== 后端 ====================
run-backend: $(VENV_UVICORN)
	@echo "启动后端 (入口 $(APP))..."
	@echo "地址: http://localhost:$(BACKEND_PORT)"
	@echo "文档: http://localhost:$(BACKEND_PORT)/docs"
	cd backend && ../$(VENV_UVICORN) $(APP) --host 0.0.0.0 --port $(BACKEND_PORT) --reload

restart-backend:
	@pkill -f 'uvicorn.*$(BACKEND_PORT)' || true
	@sleep 2
	@$(MAKE) run-backend

# ==================== 前端目录初始化 ====================
frontend_init_dirs:
	@bash scripts/init_frontend.sh

# =================== 编辑前端并拷贝 ===========
build-frontend:
	@echo "构建前端并拷贝到 backend/static/..."
	@cd frontend && npm run build:backend
	@echo "✅ 完成。backend/static/ 已更新"
	@ls -la backend/static/

# ==================== 前端 ====================
run-frontend:
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "前端依赖未安装，请运行: cd frontend && npm install"; \
		exit 1; \
	fi
	@echo "启动前端 (端口 $(FRONTEND_PORT))..."
	cd frontend && npm run dev -- --port $(FRONTEND_PORT) --host 0.0.0.0

# ==================== 组合启动 ====================
dev: $(VENV_UVICORN)
	@echo "启动开发环境..."
	@cd backend && ($(VENV_UVICORN) $(APP) --host 0.0.0.0 --port $(BACKEND_PORT) --reload > /tmp/backend.log 2>&1 &)
	@echo "后端 PID: $$(pgrep -f 'uvicorn.*$(BACKEND_PORT)')"
	@cd frontend && (npm run dev -- --port $(FRONTEND_PORT) --host 0.0.0.0 > /tmp/frontend.log 2>&1 &)
	@echo "前端 PID: $$(pgrep -f 'vite')"
	@echo ""
	@echo "后端: http://localhost:$(BACKEND_PORT)"
	@echo "前端: http://localhost:$(FRONTEND_PORT)"
	@echo "日志: tail -f /tmp/backend.log"
	@echo "      tail -f /tmp/frontend.log"
	@echo "停止: make stop-dev"

stop-dev:
	@pkill -f 'uvicorn.*$(BACKEND_PORT)' || true
	@pkill -f 'vite' || true
	@echo "已停止所有开发服务"

# ==================== 调试 ====================
list-routes: $(VENV_UVICORN)
	@cd backend && PYTHONPATH=. $(CURDIR)/$(VENV_PYTHON) tools/list_routes.py "$(APP)"

check-env:
	@echo "Python: $$($(PYTHON) --version)"
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "虚拟环境: 已创建"; \
		$(VENV_PIP) list 2>/dev/null | grep -q uvicorn && echo "uvicorn: 已安装" || echo "uvicorn: 未安装"; \
	else \
		echo "虚拟环境: 未创建"; \
	fi
	@[ -d "backend/app_server" ] && echo "新架构 app_server: 已存在" || echo "新架构 app_server: 未创建"
	@[ -d "frontend/node_modules" ] && echo "前端依赖: 已安装" || echo "前端依赖: 未安装"

# ==================== 清理 ====================
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

clean-venv:
	rm -rf $(VENV_DIR)

deep-clean: clean clean-venv
	@echo "深度清理完成"
