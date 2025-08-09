#!/bin/bash

# 一行命令构建脚本 (本地部署版本)
# 使用方法: ./build.sh

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🏗️  BookSite 一键构建 (本地部署)${NC}"
echo -e "${BLUE}======================================${NC}"

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: Python3 未安装${NC}"
    echo "请先安装 Python3: https://www.python.org/downloads/"
    exit 1
fi

# 检查 pip
if ! python3 -m pip --version &> /dev/null; then
    echo -e "${RED}❌ 错误: pip 未安装${NC}"
    echo "请先安装 pip"
    exit 1
fi

echo -e "${YELLOW}📋 构建信息:${NC}"
echo -e "  项目路径: $PROJECT_ROOT"
echo -e "  Python 版本: $(python3 --version)"
echo -e "  pip 版本: $(python3 -m pip --version)"
echo ""

# 检查系统依赖
echo -e "${GREEN}🔍 检查系统依赖...${NC}"
if command -v brew &> /dev/null; then
    echo -e "${GREEN}✅ Homebrew 已安装${NC}"
    
    # 检查 MongoDB
    if brew list mongodb-community &> /dev/null; then
        echo -e "${GREEN}✅ MongoDB 已安装${NC}"
    else
        echo -e "${YELLOW}⚠️  MongoDB 未安装，建议安装:${NC}"
        echo -e "    brew tap mongodb/brew"
        echo -e "    brew install mongodb-community"
    fi
    
    # 检查 Redis
    if brew list redis &> /dev/null; then
        echo -e "${GREEN}✅ Redis 已安装${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis 未安装，建议安装:${NC}"
        echo -e "    brew install redis"
    fi
else
    echo -e "${YELLOW}⚠️  建议安装 Homebrew 来管理系统依赖${NC}"
    echo -e "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
fi

# 创建虚拟环境
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}🏗️  创建虚拟环境...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✅ 虚拟环境创建完成${NC}"
else
    echo -e "${GREEN}✅ 虚拟环境已存在${NC}"
fi

# 激活虚拟环境并安装依赖
echo -e "${GREEN}📦 安装 Python 依赖...${NC}"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# 检查项目配置
echo -e "${GREEN}� 检查项目配置...${NC}"
python manage.py check --deploy --fail-level WARNING || echo -e "${YELLOW}⚠️  配置检查有警告，但可以继续${NC}"

# 创建必要的目录
echo -e "${GREEN}📁 创建必要目录...${NC}"
mkdir -p logs
mkdir -p media
mkdir -p static

# 显示构建结果
echo -e "${GREEN}✅ 构建完成!${NC}"
echo ""
echo -e "${GREEN}🎉 构建成功!${NC}"
echo -e "${BLUE}下一步:${NC}"
echo -e "  开发环境: make dev"
echo -e "  生产部署: make deploy"
echo -e "  查看帮助: make help"
echo ""
echo -e "${YELLOW}注意事项:${NC}"
echo -e "  1. 确保 MongoDB 和 Redis 服务已启动"
echo -e "  2. 配置环境变量文件 (.env)"
echo -e "  3. 运行数据库迁移: make migrate"
