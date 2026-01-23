# RagflowAuth 部署工具

完整的 Docker 镜像打包和服务器部署自动化工具。

## 📦 文件清单

### 核心部署脚本

| 文件 | 说明 | 使用场景 |
|------|------|----------|
| **deploy.ps1** | 主部署脚本（PowerShell） | 完整的自动化部署流程 |
| **deploy-quick.bat** | 快速启动脚本 | 双击运行，使用默认配置 |
| **scripts/remote-deploy.sh** | 服务器端部署脚本 | 在服务器上手动执行 |
| **deploy-config.json** | 部署配置文件 | 存储服务器和 Docker 配置 |
| **DEPLOY.md** | 详细部署文档 | 完整的使用说明和故障排查 |

## 🚀 快速开始

### 方式 1: 双击运行（最简单）

```
双击 deploy-quick.bat
```

### 方式 2: PowerShell 脚本

```powershell
# 使用默认配置
.\deploy.ps1

# 自定义服务器地址
.\deploy.ps1 -ServerHost "192.168.1.100"

# 指定镜像标签
.\deploy.ps1 -Tag "v1.0.0"
```

### 方式 3: 分步部署

```powershell
# 步骤 1: 只构建和导出
.\deploy.ps1 -SkipTransfer -SkipDeploy

# 步骤 2: 手动传输（可选）
scp dist\ragflowauth-images-*.tar root@172.30.30.57:/tmp/

# 步骤 3: 在服务器上部署
scp scripts\remote-deploy.sh root@172.30.30.57:/tmp/
ssh root@172.30.30.57 "bash /tmp/remote-deploy.sh"
```

## 📋 部署流程

```
┌─────────────────────────────────────────────────────────┐
│                    部署流程                              │
└─────────────────────────────────────────────────────────┘

1️⃣ 构建镜像
   ├─ 前端镜像 (Nginx + React 静态文件)
   └─ 后端镜像 (FastAPI + Python 依赖)

2️⃣ 导出镜像
   ├─ 打包为 tar 文件
   └─ 生成 SHA256 校验和

3️⃣ 传输到服务器
   └─ SCP 上传到 /tmp/

4️⃣ 服务器部署
   ├─ 加载 Docker 镜像
   ├─ 创建数据目录
   ├─ 配置文件挂载
   ├─ 启动后端容器 (端口 8001)
   ├─ 启动前端容器 (端口 3001)
   └─ 健康检查

5️⃣ 验证部署
   ├─ 检查容器状态
   ├─ 查看日志输出
   └─ 提供访问地址
```

## 🎯 主要功能

### ✅ 自动化

- 一键构建、打包、传输、部署
- 自动生成 SHA256 校验和
- 自动清理临时文件
- 自动配置容器网络

### 📦 数据持久化

- SQLite 数据库自动挂载到宿主机
- 上传文件持久化存储
- 配置文件外部挂载（便于修改）
- RAGFlow docker-compose.yml 挂载（用于备份功能）

### 🔧 配置管理

- 支持自定义镜像标签
- 支持多环境部署（开发/测试/生产）
- 配置文件热更新（修改后重启容器即可）

### 🛡️ 健康检查

- 自动验证容器启动状态
- 显示容器日志
- 提供详细的错误信息

## 📖 详细文档

完整的使用文档请查看：**[DEPLOY.md](DEPLOY.md)**

包含：
- 完整的参数说明
- 分步部署教程
- 配置管理指南
- 故障排查方法
- 常见问题解答

## 📝 配置说明

### 默认配置

```json
{
  "server": {
    "host": "172.30.30.57",
    "user": "root"
  },
  "docker": {
    "tag": "2026-01-22",
    "frontend_port": 3001,
    "backend_port": 8001
  }
}
```

### 修改配置

编辑 `deploy-config.json` 或使用命令行参数：

```powershell
.\deploy.ps1 -ServerHost "your-server.com" -ServerUser "ubuntu"
```

## 🔧 故障排查

### 常见问题

1. **SSH 连接失败**
   - 检查服务器地址和用户名
   - 确保 SSH 客户端已安装

2. **容器无法启动**
   - 查看容器日志：`docker logs ragflowauth-backend`
   - 检查端口占用：`netstat -ano | findstr :8001`

3. **前端无法访问**
   - 检查容器状态：`docker ps | grep ragflowauth`
   - 验证网络连接：`curl http://172.30.30.57:3001`

### 查看日志

```powershell
# 后端日志
ssh root@172.30.30.57 "docker logs -f ragflowauth-backend"

# 前端日志
ssh root@172.30.30.57 "docker logs -f ragflowauth-frontend"
```

## 🌐 访问地址

部署成功后：

- **前端**: http://172.30.30.57:3001
- **后端 API**: http://172.30.30.57:8001
- **API 文档**: http://172.30.30.57:8001/docs

## 🔄 更新应用

只需重新运行部署脚本：

```powershell
.\deploy.ps1
```

数据不会丢失，因为配置了数据持久化。

## 📞 支持

遇到问题？

1. 查看 [DEPLOY.md](DEPLOY.md) 详细文档
2. 检查容器日志
3. 查看故障排查章节

---

**提示**: 首次部署建议使用 `-SkipCleanup` 参数，保留 tar 文件以便调试。
