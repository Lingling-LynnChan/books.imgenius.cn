# BookSite Docker 部署指南

这个文件夹包含了 BookSite Django 应用的 Docker 容器化部署脚本。

## 🚀 快速开始 (推荐)

### 一行命令构建和部署

**从项目根目录运行：**

```bash
# 构建项目
../build.sh

# 部署开发环境
../deploy.sh dev

# 部署生产环境  
../deploy.sh prod
```

**或使用 Make 命令：**

```bash
# 构建项目
make build

# 开发环境
make dev

# 生产环境
make deploy
```

## 📁 文件说明

- `Dockerfile` - Django 应用的 Docker 镜像构建文件
- `docker-compose.yml` - 完整的服务编排配置（包含 Django、Redis、MongoDB、Nginx）
- `docker-compose.dev.yml` - 开发环境覆盖配置
- `nginx.conf` - Nginx 反向代理配置
- `mongo-init.js` - MongoDB 初始化脚本
- `.env.example` - 环境变量示例文件
- `deploy.sh` - 生产环境部署脚本
- `dev.sh` - 开发环境启动脚本

## 🔧 传统方式 (手动步骤)

### 开发环境

1. 确保已安装 Docker 和 Docker Compose
2. 进入 docker 目录：
   ```bash
   cd docker
   ```
3. 运行开发环境：
   ```bash
   ./dev.sh
   ```
4. 访问应用：http://localhost:8000

### 生产环境

1. 进入 docker 目录：
   ```bash
   cd docker
   ```
2. 复制并编辑环境变量文件：
   ```bash
   cp .env.example .env
   nano .env  # 修改配置
   ```
3. 运行部署脚本：
   ```bash
   ./deploy.sh
   ```
4. 访问应用：http://localhost

## 服务说明

### 包含的服务

- **web**: Django 应用服务器 (端口 8000)
- **redis**: Redis 缓存服务 (端口 6379)
- **mongodb**: MongoDB 数据库 (端口 27017)
- **nginx**: Nginx 反向代理 (端口 80/443)

### 数据持久化

- MongoDB 数据存储在 `mongodb_data` 卷中
- Redis 数据存储在 `redis_data` 卷中
- 用户上传的媒体文件存储在 `media_volume` 卷中
- 静态文件存储在 `static_volume` 卷中

## 常用命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
docker-compose logs -f [service_name]
```

### 进入容器
```bash
docker-compose exec web bash
docker-compose exec mongodb mongosh
docker-compose exec redis redis-cli
```

### 重启服务
```bash
docker-compose restart [service_name]
```

### 停止所有服务
```bash
docker-compose down
```

### 完全清理（删除数据卷）
```bash
docker-compose down -v
```

## Django 管理命令

### 数据库迁移
```bash
docker-compose exec web python manage.py migrate
```

### 创建超级用户
```bash
docker-compose exec web python manage.py createsuperuser
```

### 收集静态文件
```bash
docker-compose exec web python manage.py collectstatic
```

### 进入 Django Shell
```bash
docker-compose exec web python manage.py shell
```

## 配置说明

### 环境变量

关键的环境变量包括：

- `SECRET_KEY`: Django 密钥（生产环境必须修改）
- `DEBUG`: 调试模式（生产环境设为 False）
- `ALLOWED_HOSTS`: 允许的主机名
- `MONGODB_URI`: MongoDB 连接字符串
- `REDIS_HOST`, `REDIS_PORT`: Redis 连接配置
- `EMAIL_*`: 邮件服务配置
- `AI_CHECK_API_*`: AI 检查 API 配置

### 数据库配置

默认使用 MongoDB 作为主要数据存储，Redis 作为缓存。MongoDB 会自动创建：

- 用户: `booksite_user`
- 密码: `booksite_password`
- 数据库: `booksite`

### SSL/HTTPS 配置

要启用 HTTPS：

1. 将 SSL 证书文件放在 `docker/ssl/` 目录下
2. 修改 `nginx.conf` 中的 HTTPS 配置部分
3. 取消注释相关的 server 块

## 故障排除

### 常见问题

1. **端口冲突**: 确保端口 80、443、6379、27017、8000 未被占用
2. **权限问题**: 确保 Docker 有读写项目目录的权限
3. **内存不足**: MongoDB 和 Redis 需要足够的内存
4. **网络问题**: 检查 Docker 网络配置

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs web
docker-compose logs mongodb
docker-compose logs redis
docker-compose logs nginx
```

### 重新构建镜像

```bash
docker-compose build --no-cache
```

## 监控和维护

### 备份数据

```bash
# 备份 MongoDB
docker-compose exec mongodb mongodump --out /data/backup

# 备份媒体文件
docker run --rm -v book_media_volume:/data -v $(pwd):/backup alpine tar czf /backup/media-backup.tar.gz -C /data .
```

### 恢复数据

```bash
# 恢复 MongoDB
docker-compose exec mongodb mongorestore /data/backup

# 恢复媒体文件
docker run --rm -v book_media_volume:/data -v $(pwd):/backup alpine tar xzf /backup/media-backup.tar.gz -C /data
```

## 扩展部署

### 水平扩展

```bash
# 扩展 web 服务到 3 个实例
docker-compose up -d --scale web=3
```

### 生产环境优化

1. 使用外部 Redis 和 MongoDB 服务
2. 配置 CDN 用于静态文件服务
3. 使用 Load Balancer
4. 配置日志聚合
5. 设置监控和告警

## 安全建议

1. 修改所有默认密码
2. 使用强密钥
3. 启用 HTTPS
4. 定期更新镜像
5. 限制网络访问
6. 配置防火墙规则
