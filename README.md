# BookSite - 图书分享平台

一个基于 Django 的在线图书分享和评论平台，支持本地部署和容器化部署。

## ✨ 特性

- 📚 图书信息管理和展示
- 👥 用户注册和认证系统
- 💬 图书评论和讨论
- 🔍 图书搜索和筛选
- 📱 响应式设计
- �️ 本地部署和 �🐳 Docker 容器化部署

## 🚀 快速开始 (本地部署)

### 系统要求

- Python 3.7+
- MongoDB
- Redis
- macOS/Linux (推荐使用 Homebrew 管理依赖)

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

### � 系统依赖安装 (macOS)

```bash
# 安装 Homebrew (如果未安装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 MongoDB
brew tap mongodb/brew
brew install mongodb-community

# 安装 Redis
brew install redis

# 启动服务
brew services start mongodb-community
brew services start redis
```

## �🛠️ 更多命令

查看所有可用命令：
```bash
make help
```

常用命令：
- `make build` - 构建项目（安装依赖）
- `make dev` - 启动开发环境
- `make deploy` - 部署生产环境
- `make stop` - 停止生产服务
- `make status` - 查看服务状态
- `make logs` - 查看服务日志
- `make shell` - 进入 Django shell
- `make migrate` - 运行数据库迁移
- `make superuser` - 创建超级用户
- `make services-start` - 启动依赖服务
- `make services-stop` - 停止依赖服务

## 📁 项目结构

```
book/
├── accounts/           # 用户账户模块
├── books/             # 图书管理模块
├── comments/          # 评论系统模块
├── booksite/          # Django 项目配置
├── docker/            # Docker 配置文件 (可选)
├── static/            # 静态文件
├── templates/         # 模板文件
├── venv/              # Python 虚拟环境 (自动创建)
├── logs/              # 日志文件 (自动创建)
├── build.sh           # 一键构建脚本
├── deploy.sh          # 一键部署脚本
├── status.sh          # 状态检查脚本
├── Makefile           # Make 命令配置
└── manage.py          # Django 管理脚本
```

## 🌐 访问地址

### 开发环境
- 应用主页: http://localhost:8000
- 管理后台: http://localhost:8000/admin/
- API 接口: http://localhost:8000/api/

### 生产环境
- 应用主页: http://localhost:8000
- 管理后台: http://localhost:8000/admin/
- API 接口: http://localhost:8000/api/

## 🔧 开发指南

### 本地开发

1. 安装系统依赖：
   ```bash
   # macOS
   brew tap mongodb/brew
   brew install mongodb-community redis
   brew services start mongodb-community redis
   ```

2. 构建项目：
   ```bash
   make build
   ```

3. 启动开发环境：
   ```bash
   make dev
   ```

4. 创建超级用户：
   ```bash
   make superuser
   ```

### 代码更改后

Python 代码更改后，开发服务器会自动重载。如果修改了依赖或配置，需要重新构建：

```bash
make build
make restart
```

## 🚀 部署到生产环境

1. 确保系统依赖已安装并运行：
   ```bash
   make services-start
   ```

2. 构建项目：
   ```bash
   make build
   ```

3. 部署：
   ```bash
   make deploy
   ```

4. 检查状态：
   ```bash
   make status
   # 或
   ./status.sh
   ```

## � Docker 部署 (可选)

如果您更喜欢使用 Docker，可以查看 [docker/README.md](docker/README.md) 了解容器化部署方式。

## �📋 常见问题

### 端口冲突
默认使用端口 8000。如果遇到端口冲突，可以修改 Makefile 中的 PORT 变量。

### 服务依赖问题
确保 MongoDB 和 Redis 服务正在运行：
```bash
# 检查服务状态
brew services list | grep -E "(mongodb|redis)"

# 启动服务
make services-start
```

### 权限问题
确保当前用户有项目目录的读写权限：
```bash
ls -la /Users/gwen/Documents/imgenius.cn/book/
```

### 重新构建
如果遇到依赖问题，可以完全重新构建：
```bash
make clean
make build
```

### 查看日志
```bash
# 生产环境日志
make logs

# 开发环境日志
# 开发服务器的日志会直接显示在终端
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
