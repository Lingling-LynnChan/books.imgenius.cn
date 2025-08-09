#!/bin/bash

# 检查项目状态脚本
# 使用方法: ./status.sh

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}📊 BookSite 项目状态${NC}"
echo -e "${BLUE}========================${NC}"
echo ""

# 检查 Docker 服务状态
cd docker

echo -e "${YELLOW}🐳 Docker 服务状态:${NC}"
if docker-compose ps 2>/dev/null | grep -q "Up"; then
    docker-compose ps
    echo ""
    
    # 检查服务健康状态
    echo -e "${YELLOW}🏥 服务健康检查:${NC}"
    
    # 检查 Web 服务
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Web 服务 (开发环境): http://localhost:8000${NC}"
    elif curl -s http://localhost > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Web 服务 (生产环境): http://localhost${NC}"
    else
        echo -e "${RED}❌ Web 服务无响应${NC}"
    fi
    
    # 检查 MongoDB
    if docker-compose exec mongodb mongosh --quiet --eval "db.runCommand('ping')" 2>/dev/null | grep -q "ok"; then
        echo -e "${GREEN}✅ MongoDB 服务正常${NC}"
    else
        echo -e "${RED}❌ MongoDB 服务异常${NC}"
    fi
    
    # 检查 Redis
    if docker-compose exec redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo -e "${GREEN}✅ Redis 服务正常${NC}"
    else
        echo -e "${RED}❌ Redis 服务异常${NC}"
    fi
    
else
    echo -e "${RED}❌ 没有运行中的服务${NC}"
    echo ""
    echo -e "${YELLOW}启动服务:${NC}"
    echo -e "  开发环境: make dev"
    echo -e "  生产环境: make deploy"
fi

echo ""
echo -e "${YELLOW}📋 常用命令:${NC}"
echo -e "  make logs    - 查看日志"
echo -e "  make stop    - 停止服务"
echo -e "  make restart - 重启服务"
echo -e "  make shell   - 进入 Django shell"
