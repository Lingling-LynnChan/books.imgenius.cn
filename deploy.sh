#!/bin/bash

# 一行命令部署脚本
# 使用方法: ./deploy.sh [dev|prod]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取环境参数，默认为生产环境
ENVIRONMENT="${1:-prod}"

echo -e "${BLUE}🚀 BookSite 一键部署${NC}"
echo -e "${BLUE}========================${NC}"
echo -e "${YELLOW}环境: $ENVIRONMENT${NC}"
echo ""

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 检查依赖
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ 错误: Docker 未安装${NC}"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ 错误: Docker Compose 未安装${NC}"
        exit 1
    fi
}

# 构建项目
build_project() {
    echo -e "${GREEN}🏗️  构建项目...${NC}"
    ./build.sh
}

# 部署开发环境
deploy_dev() {
    echo -e "${GREEN}🔧 部署开发环境...${NC}"
    cd docker
    ./dev.sh
    
    # 等待服务启动
    echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
    sleep 10
    
    # 运行初始化
    echo -e "${GREEN}🗄️  初始化数据库...${NC}"
    docker-compose exec web python manage.py migrate || echo -e "${YELLOW}⚠️  数据库迁移失败，请手动运行${NC}"
    
    echo -e "${GREEN}✅ 开发环境部署完成!${NC}"
    echo -e "${BLUE}访问地址: http://localhost:8000${NC}"
}

# 部署生产环境
deploy_prod() {
    echo -e "${GREEN}🚀 部署生产环境...${NC}"
    cd docker
    
    # 检查环境配置
    if [ ! -f .env ]; then
        echo -e "${YELLOW}⚠️  创建生产环境配置...${NC}"
        if [ -f .env.example ]; then
            cp .env.example .env
            echo -e "${YELLOW}请编辑 .env 文件设置生产环境变量${NC}"
        else
            # 创建基本的生产环境配置
            cat > .env << EOF
SECRET_KEY=CHANGE-THIS-SECRET-KEY-IN-PRODUCTION
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
MONGODB_URI=mongodb://mongodb:27017/booksite
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
AI_CHECK_API_URL=https://api.example.com/check
AI_CHECK_API_KEY=your-api-key
EOF
            echo -e "${YELLOW}⚠️  已创建默认配置文件 .env，请修改其中的配置${NC}"
        fi
        echo -e "${YELLOW}按回车键继续部署...${NC}"
        read
    fi
    
    # 启动服务
    echo -e "${GREEN}🚀 启动生产服务...${NC}"
    docker-compose up -d
    
    # 等待服务启动
    echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
    sleep 30
    
    # 初始化数据库
    echo -e "${GREEN}🗄️  运行数据库迁移...${NC}"
    docker-compose exec web python manage.py migrate
    
    # 收集静态文件
    echo -e "${GREEN}📁 收集静态文件...${NC}"
    docker-compose exec web python manage.py collectstatic --noinput
    
    # 检查服务状态
    echo -e "${GREEN}📊 检查服务状态...${NC}"
    docker-compose ps
    
    echo -e "${GREEN}✅ 生产环境部署完成!${NC}"
    echo -e "${BLUE}访问地址: http://localhost${NC}"
    echo -e "${BLUE}管理后台: http://localhost/admin/${NC}"
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 [dev|prod]"
    echo ""
    echo "选项:"
    echo "  dev   - 部署开发环境 (默认端口 8000)"
    echo "  prod  - 部署生产环境 (默认端口 80)"
    echo ""
    echo "示例:"
    echo "  $0 dev    # 部署开发环境"
    echo "  $0 prod   # 部署生产环境"
    echo "  $0        # 默认部署生产环境"
}

# 主流程
main() {
    case "$ENVIRONMENT" in
        "dev")
            check_dependencies
            build_project
            deploy_dev
            ;;
        "prod")
            check_dependencies
            build_project
            deploy_prod
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            echo -e "${RED}❌ 未知环境: $ENVIRONMENT${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 执行主流程
main

echo ""
echo -e "${GREEN}🎉 部署完成!${NC}"
echo -e "${BLUE}常用命令:${NC}"
echo -e "  查看日志: cd docker && docker-compose logs -f"
echo -e "  停止服务: cd docker && docker-compose down"
echo -e "  重启服务: cd docker && docker-compose restart"
echo -e "  进入容器: cd docker && docker-compose exec web bash"
