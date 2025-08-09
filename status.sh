#!/bin/bash

# 检查项目状态脚本 (本地部署版本)
# 使用方法: ./status.sh

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}📊 BookSite 项目状态 (本地部署)${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 检查虚拟环境
echo -e "${YELLOW}🐍 Python 环境:${NC}"
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ 虚拟环境存在: venv/${NC}"
    if [ -f "venv/bin/python" ]; then
        PYTHON_VERSION=$(venv/bin/python --version 2>&1)
        echo -e "${GREEN}  Python 版本: $PYTHON_VERSION${NC}"
    fi
else
    echo -e "${RED}❌ 虚拟环境不存在${NC}"
    echo -e "${YELLOW}  运行 'make build' 创建虚拟环境${NC}"
fi

echo ""

# 检查服务状态
echo -e "${YELLOW}🔧 系统服务状态:${NC}"

# 检查 Django/Gunicorn 服务
if [ -f "gunicorn.pid" ]; then
    PID=$(cat gunicorn.pid)
    if kill -0 $PID 2>/dev/null; then
        echo -e "${GREEN}✅ Gunicorn 服务运行中 (PID: $PID)${NC}"
        PORT=$(ps aux | grep gunicorn | grep -o 'bind [0-9.]*:[0-9]*' | head -1 | cut -d: -f2 || echo "8000")
        echo -e "${GREEN}  访问地址: http://localhost:$PORT${NC}"
        
        # 检查服务响应
        if curl -s http://localhost:$PORT > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Web 服务响应正常${NC}"
        else
            echo -e "${RED}❌ Web 服务无响应${NC}"
        fi
    else
        echo -e "${RED}❌ Gunicorn 服务异常 (PID 文件存在但进程不存在)${NC}"
        rm -f gunicorn.pid
    fi
else
    # 检查是否有开发服务器运行
    if pgrep -f "manage.py runserver" > /dev/null; then
        echo -e "${GREEN}✅ Django 开发服务器运行中${NC}"
        if curl -s http://localhost:8000 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Web 服务响应正常: http://localhost:8000${NC}"
        else
            echo -e "${RED}❌ Web 服务无响应${NC}"
        fi
    else
        echo -e "${RED}❌ 没有运行中的 Web 服务${NC}"
    fi
fi

# 检查 MongoDB
if pgrep -x "mongod" > /dev/null; then
    echo -e "${GREEN}✅ MongoDB 服务运行中${NC}"
    # 尝试连接测试
    if command -v mongosh &> /dev/null; then
        if mongosh --quiet --eval "db.runCommand('ping')" 2>/dev/null | grep -q "ok"; then
            echo -e "${GREEN}  连接测试: 正常${NC}"
        else
            echo -e "${YELLOW}  连接测试: 无法连接${NC}"
        fi
    elif command -v mongo &> /dev/null; then
        if mongo --quiet --eval "db.runCommand('ping')" 2>/dev/null | grep -q "ok"; then
            echo -e "${GREEN}  连接测试: 正常${NC}"
        else
            echo -e "${YELLOW}  连接测试: 无法连接${NC}"
        fi
    fi
else
    echo -e "${RED}❌ MongoDB 服务未运行${NC}"
    if command -v brew &> /dev/null; then
        echo -e "${YELLOW}  启动命令: brew services start mongodb-community${NC}"
    fi
fi

# 检查 Redis
if pgrep -x "redis-server" > /dev/null; then
    echo -e "${GREEN}✅ Redis 服务运行中${NC}"
    # 尝试连接测试
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping 2>/dev/null | grep -q "PONG"; then
            echo -e "${GREEN}  连接测试: 正常${NC}"
        else
            echo -e "${YELLOW}  连接测试: 无法连接${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Redis 服务未运行${NC}"
    if command -v brew &> /dev/null; then
        echo -e "${YELLOW}  启动命令: brew services start redis${NC}"
    fi
fi

echo ""

# 检查日志文件
echo -e "${YELLOW}📋 日志文件:${NC}"
if [ -d "logs" ]; then
    if [ -f "logs/error.log" ]; then
        LOG_SIZE=$(wc -l < logs/error.log)
        echo -e "${GREEN}✅ 错误日志: logs/error.log ($LOG_SIZE 行)${NC}"
        if [ $LOG_SIZE -gt 0 ]; then
            echo -e "${YELLOW}  最近错误:${NC}"
            tail -n 3 logs/error.log | sed 's/^/    /'
        fi
    else
        echo -e "${YELLOW}⚠️  错误日志文件不存在${NC}"
    fi
    
    if [ -f "logs/access.log" ]; then
        LOG_SIZE=$(wc -l < logs/access.log)
        echo -e "${GREEN}✅ 访问日志: logs/access.log ($LOG_SIZE 行)${NC}"
    else
        echo -e "${YELLOW}⚠️  访问日志文件不存在${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  日志目录不存在${NC}"
fi

echo ""

# 系统资源使用情况
echo -e "${YELLOW}💻 系统资源:${NC}"
echo -e "${GREEN}  内存使用:${NC}"
if command -v free &> /dev/null; then
    free -h | grep -E "(Mem|内存)" | awk '{print "    " $1 " " $2 " " $3 " " $4}'
elif command -v vm_stat &> /dev/null; then
    # macOS
    VM_STAT=$(vm_stat)
    PAGES_FREE=$(echo "$VM_STAT" | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
    PAGES_TOTAL=$(echo "$VM_STAT" | grep -E "(Pages free|Pages active|Pages inactive|Pages speculative|Pages wired down)" | awk '{sum += $3} END {print sum}')
    if [ ! -z "$PAGES_FREE" ] && [ ! -z "$PAGES_TOTAL" ]; then
        FREE_MB=$((PAGES_FREE * 4096 / 1024 / 1024))
        TOTAL_MB=$((PAGES_TOTAL * 4096 / 1024 / 1024))
        echo -e "    总内存: ${TOTAL_MB}MB, 可用: ${FREE_MB}MB"
    fi
fi

echo ""
echo -e "${YELLOW}📋 常用命令:${NC}"
if [ -f "gunicorn.pid" ]; then
    echo -e "  make stop     - 停止生产服务"
    echo -e "  make restart  - 重启生产服务"
    echo -e "  make logs     - 查看错误日志"
else
    echo -e "  make dev      - 启动开发环境"
    echo -e "  make deploy   - 部署生产环境"
    echo -e "  make build    - 构建项目"
fi
echo -e "  make shell    - 进入 Django shell"
echo -e "  make migrate  - 运行数据库迁移"
echo -e "  make help     - 查看所有命令"
