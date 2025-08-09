#!/bin/bash

# 天才俱乐部·阅读专区的启动脚本

echo "=== 天才俱乐部·阅读专区的启动脚本 ==="

# 检查Python版本
python_version=$(python3 --version 2>&1)
echo "检测到Python版本: $python_version"

# 安装依赖
echo "安装Python依赖..."
if pip install -r requirements.txt; then
    echo "✓ 依赖安装成功"
else
    echo "✗ 依赖安装失败"
    exit 1
fi

# 检查环境配置
if [ ! -f .env ]; then
    echo "创建环境配置文件..."
    cp .env.example .env
    echo "⚠ 请编辑 .env 文件配置数据库和其他服务"
    echo "  必须配置: MySQL, MongoDB, Redis, 邮件服务"
fi

# 检查数据库连接
echo "检查数据库连接..."
python3 manage.py check --database default

# 执行数据库迁移
echo "执行数据库迁移..."
python3 manage.py makemigrations
python3 manage.py migrate

# 收集静态文件
echo "收集静态文件..."
python3 manage.py collectstatic --noinput

# 询问是否创建超级用户
read -p "是否创建管理员账户？(y/N): " create_superuser
if [[ $create_superuser == "y" || $create_superuser == "Y" ]]; then
    python3 manage.py createsuperuser
fi

echo ""
echo "=== 启动完成 ==="
echo "运行以下命令启动开发服务器:"
echo "  python3 manage.py runserver"
echo ""
echo "然后访问: http://localhost:8000"
echo ""
echo "管理后台: http://localhost:8000/admin"
echo ""
echo "注意事项:"
echo "1. 确保MySQL、MongoDB、Redis服务已启动"
echo "2. 配置正确的邮件服务用于发送验证码"
echo "3. 如需AI审核功能，请配置AI_CHECK_API_URL"
