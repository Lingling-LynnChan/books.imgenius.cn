# BookSite - 图书分享平台

一个基于 Django 的在线图书分享和评论平台。

## ✨ 特性

- 📚 图书信息管理和展示
- 👥 用户注册和认证系统
- 💬 图书评论和讨论
- 🔍 图书搜索和筛选
- 📱 响应式设计
- 🐳 Docker 容器化部署

## 🚀 快速开始

### 一行命令构建
```bash
./build.sh
```
或
```bash
make build
```

### 一行命令部署

**开发环境：**
```bash
./deploy.sh dev
```
或
```bash
make dev
```

**生产环境：**
```bash
./deploy.sh prod
```
或
```bash
make deploy
```

### 🛠️ 更多命令

查看所有可用命令：
```bash
make help
```

常用命令：
- `make build` - 构建 Docker 镜像
- `make dev` - 启动开发环境
- `make deploy` - 部署生产环境
- `make stop` - 停止所有服务
- `make logs` - 查看服务日志
- `make shell` - 进入 Django shell
- `make migrate` - 运行数据库迁移
- `make superuser` - 创建超级用户

## 📁 项目结构

```
book/
├── accounts/           # 用户账户模块
├── books/             # 图书管理模块
├── comments/          # 评论系统模块
├── booksite/          # Django 项目配置
├── docker/            # Docker 配置文件
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── dev.sh         # 开发环境启动脚本
│   └── deploy.sh      # 生产环境部署脚本
├── static/            # 静态文件
├── templates/         # 模板文件
├── build.sh           # 一键构建脚本
├── deploy.sh          # 一键部署脚本
├── Makefile           # Make 命令配置
└── manage.py          # Django 管理脚本
```

## 🌐 访问地址

### 开发环境
- 应用主页: http://localhost:8000
- 管理后台: http://localhost:8000/admin/
- API 接口: http://localhost:8000/api/

### 生产环境
- 应用主页: http://localhost
- 管理后台: http://localhost/admin/
- API 接口: http://localhost/api/

## 🔧 传统部署方式

如果您更喜欢分步骤操作，可以使用传统方式：

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

## 📦 服务说明

### 包含的服务

- **web**: Django 应用服务器 (端口 8000)
- **redis**: Redis 缓存服务 (端口 6379)
- **mongodb**: MongoDB 数据库 (端口 27017)
- **nginx**: Nginx 反向代理 (端口 80/443)

## 🔨 开发指南

### 本地开发

1. 启动开发环境：
   ```bash
   make dev
   ```

2. 运行数据库迁移：
   ```bash
   make migrate
   ```

3. 创建超级用户：
   ```bash
   make superuser
   ```

4. 查看日志：
   ```bash
   make logs
   ```

### 代码更改后

如果修改了 Python 代码，容器会自动重载。如果修改了 Docker 配置，需要重新构建：

```bash
make build
make restart
```

## 🚀 部署到生产环境

1. 构建项目：
   ```bash
   make build
   ```

2. 配置环境变量：
   ```bash
   cd docker
   cp .env.example .env
   # 编辑 .env 文件，设置生产环境配置
   ```

3. 部署：
   ```bash
   make deploy
   ```

## 📋 常见问题

### 端口冲突
如果遇到端口冲突，请检查以下端口是否被占用：
- 80 (nginx)
- 443 (nginx https)
- 8000 (django)
- 6379 (redis)
- 27017 (mongodb)

### 权限问题
确保当前用户有 Docker 运行权限：
```bash
sudo usermod -aG docker $USER
```

### 重新构建
如果遇到镜像问题，可以完全重新构建：
```bash
make clean
make build
```

## 📝 技术栈

- **后端**: Django 4.x, Django REST Framework
- **数据库**: MongoDB
- **缓存**: Redis
- **前端**: HTML, CSS, JavaScript, Bootstrap
- **容器化**: Docker, Docker Compose
- **反向代理**: Nginx

## 📄 许可证

此项目使用 MIT 许可证。

## 🤝 贡献

欢迎提交 Pull Request 和 Issue！

## 📞 联系方式

如有问题，请提交 Issue 或联系项目维护者。
