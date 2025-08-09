#!/bin/bash

# 一行命令部署脚本 (本地部署版本)
# 使用方法: ./deploy.sh [dev|prod]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取环境参数，默认为生产环境
ENVIRONMENT="${1:-prod}"

echo -e "${BLUE}🚀 BookSite 一键部署 (本地部署)${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "${YELLOW}环境: $ENVIRONMENT${NC}"
echo ""

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Python 和虚拟环境配置
PYTHON="python3"
VENV_DIR="venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
PORT="8000"
WORKERS="4"

# 检查依赖
check_dependencies() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ 错误: Python3 未安装${NC}"
        exit 1
    fi

    if ! command -v python3 -m pip &> /dev/null; then
        echo -e "${RED}❌ 错误: pip 未安装${NC}"
        exit 1
    fi
}

# 检查服务依赖
check_services() {
    echo -e "${GREEN}🔍 检查服务依赖...${NC}"
    
    # 检查 MongoDB
    if ! pgrep -x "mongod" > /dev/null; then
        echo -e "${YELLOW}⚠️  MongoDB 未运行，尝试启动...${NC}"
        if command -v brew &> /dev/null; then
            brew services start mongodb-community || echo -e "${RED}❌ MongoDB 启动失败${NC}"
        else
            echo -e "${YELLOW}请手动启动 MongoDB 服务${NC}"
        fi
    else
        echo -e "${GREEN}✅ MongoDB 正在运行${NC}"
    fi
    
    # 检查 Redis
    if ! pgrep -x "redis-server" > /dev/null; then
        echo -e "${YELLOW}⚠️  Redis 未运行，尝试启动...${NC}"
        if command -v brew &> /dev/null; then
            brew services start redis || echo -e "${RED}❌ Redis 启动失败${NC}"
        else
            echo -e "${YELLOW}请手动启动 Redis 服务${NC}"
        fi
    else
        echo -e "${GREEN}✅ Redis 正在运行${NC}"
    fi
}

# 构建项目
build_project() {
    echo -e "${GREEN}🏗️  构建项目...${NC}"
    
    # 运行构建脚本
    if [ -f "build.sh" ]; then
        ./build.sh
    else
        # 直接执行构建步骤
        if [ ! -d "$VENV_DIR" ]; then
            echo -e "${GREEN}创建虚拟环境...${NC}"
            $PYTHON -m venv "$VENV_DIR"
        fi
        
        echo -e "${GREEN}安装依赖...${NC}"
        $VENV_PIP install --upgrade pip
        $VENV_PIP install -r requirements.txt
    fi
}

# 初始化数据库
init_database() {
    echo -e "${GREEN}🗄️  初始化数据库...${NC}"
    $VENV_PYTHON manage.py makemigrations
    $VENV_PYTHON manage.py migrate
}

# 收集静态文件
collect_static() {
    echo -e "${GREEN}� 收集静态文件...${NC}"
    $VENV_PYTHON manage.py collectstatic --noinput
}

# 创建必要目录
create_directories() {
    echo -e "${GREEN}📁 创建必要目录...${NC}"
    mkdir -p logs
    mkdir -p media
    mkdir -p static
    mkdir -p staticfiles
}

# 检查环境配置
check_env_config() {
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}⚠️  创建环境配置文件...${NC}"
        if [ -f ".env.example" ]; then
            cp .env.example .env
        else
            # 创建基本的环境配置
            cat > .env << EOF
SECRET_KEY=CHANGE-THIS-SECRET-KEY-IN-PRODUCTION
DEBUG=$([[ "$ENVIRONMENT" == "dev" ]] && echo "True" || echo "False")
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
MONGODB_URI=mongodb://localhost:27017/booksite
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
AI_CHECK_API_URL=http://localhost:8000/api/check
AI_CHECK_API_KEY=dev-api-key
EOF
        fi
        echo -e "${YELLOW}已创建环境配置文件 .env${NC}"
        if [ "$ENVIRONMENT" = "prod" ]; then
            echo -e "${YELLOW}⚠️  请修改 .env 文件中的生产环境配置${NC}"
            echo -e "${YELLOW}按回车键继续部署...${NC}"
            read
        fi
    fi
}

# 部署开发环境
deploy_dev() {
    echo -e "${GREEN}� 部署开发环境...${NC}"
    
    check_services
    build_project
    check_env_config
    create_directories
    init_database
    collect_static
    
    echo -e "${GREEN}✅ 开发环境部署完成!${NC}"
    echo -e "${BLUE}启动开发服务器...${NC}"
    echo -e "${BLUE}访问地址: http://localhost:$PORT${NC}"
    echo -e "${BLUE}管理后台: http://localhost:$PORT/admin/${NC}"
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止服务器${NC}"
    
    # 启动开发服务器
    $VENV_PYTHON manage.py runserver $PORT
}

# 部署生产环境
deploy_prod() {
    echo -e "${GREEN}� 部署生产环境...${NC}"
    
    check_services
    build_project
    check_env_config
    create_directories
    init_database
    collect_static
    
    # 停止现有服务
    if [ -f "gunicorn.pid" ]; then
        echo -e "${YELLOW}停止现有服务...${NC}"
        kill -TERM `cat gunicorn.pid` 2>/dev/null || true
        rm -f gunicorn.pid
    fi
    
    # 启动生产服务
    echo -e "${GREEN}� 启动生产服务...${NC}"
    $VENV_PYTHON -m gunicorn booksite.wsgi:application \
        --bind 0.0.0.0:$PORT \
        --workers $WORKERS \
        --daemon \
        --pid gunicorn.pid \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log
    
    # 检查服务状态
    sleep 2
    if [ -f "gunicorn.pid" ] && kill -0 `cat gunicorn.pid` 2>/dev/null; then
        echo -e "${GREEN}✅ 生产环境部署完成!${NC}"
        echo -e "${BLUE}访问地址: http://localhost:$PORT${NC}"
        echo -e "${BLUE}管理后台: http://localhost:$PORT/admin/${NC}"
        echo -e "${BLUE}PID: $(cat gunicorn.pid)${NC}"
    else
        echo -e "${RED}❌ 服务启动失败，请检查日志${NC}"
        if [ -f "logs/error.log" ]; then
            echo -e "${YELLOW}错误日志:${NC}"
            tail -n 10 logs/error.log
        fi
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 [dev|prod]"
    echo ""
    echo "选项:"
    echo "  dev   - 部署开发环境 (Django runserver)"
    echo "  prod  - 部署生产环境 (Gunicorn)"
    echo ""
    echo "示例:"
    echo "  $0 dev    # 部署开发环境"
    echo "  $0 prod   # 部署生产环境"
    echo "  $0        # 默认部署生产环境"
    echo ""
    echo "系统要求:"
    echo "  - Python 3.7+"
    echo "  - MongoDB"
    echo "  - Redis"
}

# 主流程
main() {
    case "$ENVIRONMENT" in
        "dev")
            check_dependencies
            deploy_dev
            ;;
        "prod")
            check_dependencies
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
echo -e "  查看日志: tail -f logs/error.log"
echo -e "  停止服务: make stop"
echo -e "  重启服务: make restart"
echo -e "  查看状态: make status"
