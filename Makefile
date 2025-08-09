# BookSite 项目管理 Makefile
# 使用方法:
#   make build  - 构建项目
#   make deploy - 部署到生产环境
#   make dev    - 启动开发环境
#   make stop   - 停止所有服务
#   make clean  - 清理所有容器和数据

.PHONY: help build deploy dev stop clean logs shell migrate collectstatic backup restore

# 默认目标
help:
	@echo "BookSite 项目管理命令:"
	@echo ""
	@echo "构建和部署:"
	@echo "  make build   - 构建 Docker 镜像"
	@echo "  make deploy  - 部署到生产环境"
	@echo "  make dev     - 启动开发环境"
	@echo ""
	@echo "服务管理:"
	@echo "  make stop    - 停止所有服务"
	@echo "  make restart - 重启所有服务"
	@echo "  make logs    - 查看服务日志"
	@echo "  make status  - 查看服务状态"
	@echo ""
	@echo "Django 管理:"
	@echo "  make shell   - 进入 Django shell"
	@echo "  make migrate - 运行数据库迁移"
	@echo "  make collectstatic - 收集静态文件"
	@echo "  make superuser - 创建超级用户"
	@echo ""
	@echo "维护工具:"
	@echo "  make clean   - 清理所有容器和数据"
	@echo "  make backup  - 备份数据"
	@echo "  make restore - 恢复数据"

# 构建项目 (一行命令构建)
build:
	@echo "🏗️  构建 BookSite 项目..."
	@cd docker && docker-compose build --no-cache
	@echo "✅ 构建完成!"

# 部署到生产环境 (一行命令部署)
deploy:
	@echo "🚀 部署 BookSite 到生产环境..."
	@cd docker && ./deploy.sh
	@echo "✅ 部署完成! 访问: http://localhost"

# 启动开发环境
dev:
	@echo "🔧 启动开发环境..."
	@cd docker && ./dev.sh
	@echo "✅ 开发环境已启动! 访问: http://localhost:8000"

# 停止所有服务
stop:
	@echo "🛑 停止所有服务..."
	@cd docker && docker-compose down
	@echo "✅ 所有服务已停止"

# 重启服务
restart:
	@echo "🔄 重启服务..."
	@cd docker && docker-compose restart
	@echo "✅ 服务重启完成"

# 查看服务状态
status:
	@echo "📊 服务状态:"
	@cd docker && docker-compose ps

# 查看日志
logs:
	@echo "📋 查看服务日志:"
	@cd docker && docker-compose logs -f

# 进入 Django shell
shell:
	@echo "🐍 进入 Django shell..."
	@cd docker && docker-compose exec web python manage.py shell

# 运行数据库迁移
migrate:
	@echo "🗄️  运行数据库迁移..."
	@cd docker && docker-compose exec web python manage.py migrate
	@echo "✅ 数据库迁移完成"

# 收集静态文件
collectstatic:
	@echo "📁 收集静态文件..."
	@cd docker && docker-compose exec web python manage.py collectstatic --noinput
	@echo "✅ 静态文件收集完成"

# 创建超级用户
superuser:
	@echo "👤 创建 Django 超级用户..."
	@cd docker && docker-compose exec web python manage.py createsuperuser

# 清理所有容器和数据
clean:
	@echo "🧹 清理所有容器和数据..."
	@echo "⚠️  警告: 这将删除所有数据!"
	@read -p "确认继续? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@cd docker && docker-compose down -v --remove-orphans
	@docker system prune -f
	@echo "✅ 清理完成"

# 备份数据
backup:
	@echo "💾 备份数据..."
	@mkdir -p backups
	@cd docker && docker-compose exec mongodb mongodump --out /data/backup
	@docker run --rm -v book_media_volume:/data -v $(PWD)/backups:/backup alpine tar czf /backup/media-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .
	@echo "✅ 数据备份完成"

# 恢复数据 (需要指定备份文件)
restore:
	@echo "🔄 恢复数据..."
	@echo "请手动运行恢复命令:"
	@echo "  MongoDB: cd docker && docker-compose exec mongodb mongorestore /data/backup"
	@echo "  媒体文件: docker run --rm -v book_media_volume:/data -v \$$(PWD)/backups:/backup alpine tar xzf /backup/media-backup-YYYYMMDD-HHMMSS.tar.gz -C /data"

# 快速启动 (for CI/CD)
quick-deploy: build deploy

# 开发环境完整设置
dev-setup: build dev migrate collectstatic
	@echo "✅ 开发环境设置完成!"

# 生产环境完整设置
prod-setup: build deploy
	@echo "✅ 生产环境设置完成!"
