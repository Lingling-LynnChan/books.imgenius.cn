#!/bin/bash

# 开发环境启动脚本

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}启动开发环境...${NC}"

# 切换到docker目录
cd "$(dirname "$0")"

# 检查.env文件
if [ ! -f .env.dev ]; then
    echo -e "${YELLOW}创建开发环境配置文件...${NC}"
    cat > .env.dev << EOF
SECRET_KEY=dev-secret-key-not-for-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
MONGODB_URI=mongodb://mongodb:27017/booksite_dev
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
AI_CHECK_API_URL=http://localhost:8000/api/check
AI_CHECK_API_KEY=dev-api-key
EOF
fi

# 使用开发配置启动
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env.dev up -d

echo -e "${GREEN}开发环境启动完成!${NC}"
echo -e "访问地址: http://localhost:8000"
