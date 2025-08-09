#!/bin/bash

# 一行命令构建脚本
# 使用方法: ./build.sh

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🏗️  BookSite 一键构建${NC}"
echo -e "${BLUE}========================${NC}"

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ 错误: Docker Compose 未安装${NC}"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${YELLOW}📋 构建信息:${NC}"
echo -e "  项目路径: $PROJECT_ROOT"
echo -e "  Docker 版本: $(docker --version)"
echo -e "  Docker Compose 版本: $(docker-compose --version)"
echo ""

# 进入 docker 目录
cd docker

# 拉取最新的基础镜像
echo -e "${GREEN}🔄 更新基础镜像...${NC}"
docker-compose pull || true

# 构建项目镜像
echo -e "${GREEN}🏗️  构建项目镜像...${NC}"
docker-compose build --no-cache --parallel

# 验证构建结果
echo -e "${GREEN}✅ 验证构建结果...${NC}"
if docker-compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker Compose 配置验证通过${NC}"
else
    echo -e "${RED}❌ Docker Compose 配置有误${NC}"
    exit 1
fi

# 显示镜像信息
echo -e "${GREEN}📦 构建的镜像:${NC}"
docker images | grep -E "(book|booksite)" || echo "  无相关镜像"

echo ""
echo -e "${GREEN}🎉 构建完成!${NC}"
echo -e "${BLUE}下一步:${NC}"
echo -e "  开发环境: make dev 或 ./docker/dev.sh"
echo -e "  生产部署: make deploy 或 ./deploy.sh"
