#!/bin/bash

# 部署脚本 - 用于生产环境部署

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始部署 BookSite 应用...${NC}"

# 检查Docker和Docker Compose是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    exit 1
fi

# 切换到docker目录
cd "$(dirname "$0")"

# 检查.env文件是否存在
if [ ! -f .env ]; then
    echo -e "${YELLOW}警告: .env 文件不存在，复制示例配置文件...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}请编辑 .env 文件并设置正确的环境变量${NC}"
    read -p "按回车键继续..."
fi

# 构建镜像
echo -e "${GREEN}构建Docker镜像...${NC}"
docker-compose build --no-cache

# 启动服务
echo -e "${GREEN}启动服务...${NC}"
docker-compose up -d

# 等待服务启动
echo -e "${GREEN}等待服务启动...${NC}"
sleep 30

# 运行数据库迁移
echo -e "${GREEN}运行数据库迁移...${NC}"
docker-compose exec web python manage.py migrate

# 创建超级用户 (可选)
echo -e "${YELLOW}是否要创建Django超级用户? (y/n)${NC}"
read -r create_superuser
if [ "$create_superuser" = "y" ] || [ "$create_superuser" = "Y" ]; then
    docker-compose exec web python manage.py createsuperuser
fi

# 收集静态文件
echo -e "${GREEN}收集静态文件...${NC}"
docker-compose exec web python manage.py collectstatic --noinput

# 检查服务状态
echo -e "${GREEN}检查服务状态...${NC}"
docker-compose ps

# 显示访问信息
echo -e "${GREEN}部署完成!${NC}"
echo -e "${GREEN}应用访问地址:${NC}"
echo -e "  HTTP: http://localhost"
echo -e "  Django Admin: http://localhost/admin/"
echo -e "  API: http://localhost/api/"
echo ""
echo -e "${GREEN}服务管理命令:${NC}"
echo -e "  查看日志: docker-compose logs -f"
echo -e "  停止服务: docker-compose down"
echo -e "  重启服务: docker-compose restart"
echo -e "  查看状态: docker-compose ps"
