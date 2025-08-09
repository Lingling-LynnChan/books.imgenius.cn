# BookSite 项目管理 Makefile (本地部署版本)
# 使用方法:
#   make build  - 构建项目（安装依赖）
#   make deploy - 部署到生产环境
#   make dev    - 启动开发环境
#   make stop   - 停止所有服务
#   make clean  - 清理虚拟环境和缓存

.PHONY: help build deploy dev stop clean logs shell migrate collectstatic backup restore install check

# Python 配置
PYTHON := /usr/local/bin/python3
PIP := $(PYTHON) -m pip
VENV_DIR := venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

# 项目配置
PROJECT_NAME := booksite
PORT := 8000
WORKERS := 4

# 默认目标
help:
	@echo "BookSite 项目管理命令 (本地部署):"
	@echo ""
	@echo "构建和部署:"
	@echo "  make install - 安装依赖和设置虚拟环境"
	@echo "  make build   - 构建项目（等同于install）"
	@echo "  make deploy  - 部署到生产环境"
	@echo "  make dev     - 启动开发环境"
	@echo ""
	@echo "服务管理:"
	@echo "  make start   - 启动生产服务"
	@echo "  make stop    - 停止所有服务"
	@echo "  make restart - 重启服务"
	@echo "  make status  - 查看服务状态"
	@echo ""
	@echo "Django 管理:"
	@echo "  make shell   - 进入 Django shell"
	@echo "  make migrate - 运行数据库迁移"
	@echo "  make collectstatic - 收集静态文件"
	@echo "  make superuser - 创建超级用户"
	@echo "  make check   - 检查项目配置"
	@echo ""
	@echo "维护工具:"
	@echo "  make clean   - 清理虚拟环境和缓存"
	@echo "  make test    - 运行测试"
	@echo "  make lint    - 代码检查"
	@echo ""
	@echo "依赖服务:"
	@echo "  make services-start - 启动依赖服务 (MongoDB, Redis)"
	@echo "  make services-stop  - 停止依赖服务"

# 检查并安装系统依赖
check-system:
	@echo "� 检查系统依赖..."
	@which python3 > /dev/null || (echo "❌ Python3 未安装" && exit 1)
	@which brew > /dev/null || (echo "⚠️  建议安装 Homebrew 来管理系统依赖" && echo "  /bin/bash -c \"\$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
	@echo "✅ 系统依赖检查完成"

# 创建虚拟环境
$(VENV_DIR):
	@echo "🏗️  创建虚拟环境..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "✅ 虚拟环境创建完成"

# 安装依赖
install: check-system $(VENV_DIR)
	@echo "� 安装 Python 依赖..."
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	@echo "✅ 依赖安装完成"

# 构建项目 (一行命令构建)
build: install
	@echo "🏗️  构建 BookSite 项目..."
	@echo "✅ 构建完成!"

# 检查项目配置
check: $(VENV_DIR)
	@echo "� 检查项目配置..."
	$(VENV_PYTHON) manage.py check
	@echo "✅ 项目配置检查完成"

# 数据库迁移
migrate: $(VENV_DIR)
	@echo "🗄️  运行数据库迁移..."
	$(VENV_PYTHON) manage.py makemigrations
	$(VENV_PYTHON) manage.py migrate
	@echo "✅ 数据库迁移完成"

# 收集静态文件
collectstatic: $(VENV_DIR)
	@echo "📁 收集静态文件..."
	$(VENV_PYTHON) manage.py collectstatic --noinput
	@echo "✅ 静态文件收集完成"

# 创建超级用户
superuser: $(VENV_DIR)
	@echo "👤 创建 Django 超级用户..."
	$(VENV_PYTHON) manage.py createsuperuser

# 启动开发环境 (一行命令开发)
dev: install migrate collectstatic
	@echo "🔧 启动开发环境..."
	@echo "✅ 开发环境准备完成!"
	@echo "🚀 启动开发服务器..."
	@echo "访问地址: http://localhost:$(PORT)"
	@echo "管理后台: http://localhost:$(PORT)/admin/"
	$(VENV_PYTHON) manage.py runserver $(PORT)

# 启动生产服务
start: $(VENV_DIR)
	@echo "🚀 启动生产服务..."
	@echo "访问地址: http://localhost:$(PORT)"
	$(VENV_PYTHON) -m gunicorn $(PROJECT_NAME).wsgi:application \
		--bind 0.0.0.0:$(PORT) \
		--workers $(WORKERS) \
		--daemon \
		--pid gunicorn.pid \
		--access-logfile logs/access.log \
		--error-logfile logs/error.log

# 部署到生产环境 (一行命令部署)
deploy: install migrate collectstatic
	@echo "🚀 部署 BookSite 到生产环境..."
	@mkdir -p logs
	@make start
	@echo "✅ 部署完成! 访问: http://localhost:$(PORT)"

# 停止服务
stop:
	@echo "� 停止服务..."
	@if [ -f gunicorn.pid ]; then \
		kill -TERM `cat gunicorn.pid` && rm gunicorn.pid; \
		echo "✅ Gunicorn 服务已停止"; \
	else \
		echo "ℹ️  没有运行中的 Gunicorn 服务"; \
	fi

# 重启服务
restart: stop deploy

# 查看服务状态
status:
	@echo "📊 服务状态:"
	@if [ -f gunicorn.pid ]; then \
		echo "✅ Gunicorn 服务运行中 (PID: `cat gunicorn.pid`)"; \
		ps aux | grep gunicorn | grep -v grep; \
	else \
		echo "❌ Gunicorn 服务未运行"; \
	fi

# 查看日志
logs:
	@echo "📋 查看服务日志:"
	@if [ -f logs/error.log ]; then \
		echo "=== 错误日志 ==="; \
		tail -f logs/error.log; \
	else \
		echo "❌ 日志文件不存在"; \
	fi

# 进入 Django shell
shell: $(VENV_DIR)
	@echo "🐍 进入 Django shell..."
	$(VENV_PYTHON) manage.py shell

# 运行测试
test: $(VENV_DIR)
	@echo "🧪 运行测试..."
	$(VENV_PYTHON) manage.py test

# 代码检查
lint: $(VENV_DIR)
	@echo "🔍 代码检查..."
	@if $(VENV_PIP) show flake8 > /dev/null 2>&1; then \
		$(VENV_DIR)/bin/flake8 .; \
	else \
		echo "⚠️  flake8 未安装，跳过代码检查"; \
	fi

# 启动依赖服务 (macOS)
services-start:
	@echo "� 启动依赖服务..."
	@echo "启动 MongoDB..."
	@brew services start mongodb-community > /dev/null 2>&1 || echo "⚠️  MongoDB 启动失败，请手动启动"
	@echo "启动 Redis..."
	@brew services start redis > /dev/null 2>&1 || echo "⚠️  Redis 启动失败，请手动启动"
	@echo "✅ 依赖服务启动完成"

# 停止依赖服务
services-stop:
	@echo "🛑 停止依赖服务..."
	@brew services stop mongodb-community > /dev/null 2>&1 || echo "⚠️  MongoDB 停止失败"
	@brew services stop redis > /dev/null 2>&1 || echo "⚠️  Redis 停止失败"
	@echo "✅ 依赖服务停止完成"

# 清理虚拟环境和缓存
clean:
	@echo "🧹 清理项目..."
	@echo "⚠️  这将删除虚拟环境和缓存文件!"
	@read -p "确认继续? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	rm -rf $(VENV_DIR)
	rm -rf __pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -f gunicorn.pid
	rm -rf logs
	@echo "✅ 清理完成"

# 快速启动 (for CI/CD)
quick-deploy: build deploy

# 开发环境完整设置
dev-setup: install services-start migrate collectstatic
	@echo "✅ 开发环境设置完成!"
	@echo "运行 'make dev' 启动开发服务器"

# 生产环境完整设置
prod-setup: install services-start deploy
	@echo "✅ 生产环境设置完成!"
