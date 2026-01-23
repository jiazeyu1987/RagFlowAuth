# RagflowAuth 部署工具

一键自动化部署 RagflowAuth 到远程服务器。

## 功能特性

- ✅ 自动构建前端和后端 Docker 镜像
- ✅ 导出镜像为 tar 文件（带 SHA256 校验）
- ✅ 自动传输到远程服务器
- ✅ 在服务器上加载并启动容器
- ✅ 自动配置数据持久化
- ✅ 支持自定义配置

## 前置要求

### 本地环境（Windows）

- PowerShell 5.1 或更高版本
- Docker Desktop
- OpenSSH 客户端（Windows 10/11 自带）
- Git（可选，用于版本管理）

### 远程服务器

- Linux 服务器（Ubuntu/CentOS 等）
- Docker 已安装
- SSH 访问权限

## 快速开始

### 1. 一键部署（推荐）

```powershell
# 使用默认配置部署
.\deploy.ps1
```

这将执行以下步骤：
1. 构建前端和后端镜像（tag: 当前日期，如 2026-01-22）
2. 导出镜像到 `dist/ragflowauth-images_YYYY-MM-DD.tar`
3. 传输到服务器（172.30.30.57）
4. 在服务器上加载并启动容器
5. 自动清理临时文件

### 2. 自定义部署

```powershell
# 指定服务器地址
.\deploy.ps1 -ServerHost "192.168.1.100" -ServerUser "ubuntu"

# 使用自定义标签
.\deploy.ps1 -Tag "v1.0.0"

# 只构建镜像，不部署
.\deploy.ps1 -SkipDeploy

# 使用已有镜像文件部署
.\deploy.ps1 -SkipBuild -SkipTransfer
```

### 3. 高级选项

```powershell
# 完整的参数示例
.\deploy.ps1 `
  -Tag "production" `
  -ServerHost "172.30.30.57" `
  -ServerUser "root" `
  -ComposeFile "docker/docker-compose.yml" `
  -OutDir "dist" `
  -SkipCleanup
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-Tag` | String | 当前日期 (YYYY-MM-DD) | Docker 镜像标签 |
| `-ServerHost` | String | 172.30.30.57 | 服务器地址 |
| `-ServerUser` | String | root | SSH 用户名 |
| `-ComposeFile` | String | docker/docker-compose.yml | Docker Compose 文件路径 |
| `-SkipBuild` | Switch | false | 跳过镜像构建 |
| `-SkipTransfer` | Switch | false | 跳过文件传输 |
| `-SkipDeploy` | Switch | false | 跳过服务器部署 |
| `-SkipCleanup` | Switch | false | 跳过临时文件清理 |
| `-OutDir` | String | dist | 输出目录 |

## 分步部署

如果你想分步执行部署流程：

### 步骤 1: 构建并导出镜像

```powershell
.\deploy.ps1 -SkipTransfer -SkipDeploy -SkipCleanup
```

生成的文件：
- `dist/ragflowauth-images_YYYY-MM-DD.tar` - Docker 镜像
- `dist/ragflowauth-images_YYYY-MM-DD.tar.sha256` - SHA256 校验和

### 步骤 2: 手动传输镜像

```powershell
scp dist\ragflowauth-images_YYYY-MM-DD.tar root@172.30.30.57:/tmp/
```

### 步骤 3: 在服务器上部署

#### 方式 A: 使用部署脚本

```bash
# 上传部署脚本到服务器
scp scripts/remote-deploy.sh root@172.30.30.57:/tmp/

# 在服务器上执行
ssh root@172.30.30.57 "bash /tmp/remote-deploy.sh --tag 2026-01-22"
```

#### 方式 B: 手动部署

```bash
ssh root@172.30.30.57

# 加载镜像
docker load -i /tmp/ragflowauth-images_YYYY-MM-DD.tar

# 创建数据目录
mkdir -p /opt/ragflowauth/data /opt/ragflowauth/uploads

# 启动容器
docker run -d \
  --name ragflowauth-backend \
  --network ragflowauth-network \
  -p 8001:8001 \
  -v /opt/ragflowauth/data:/app/data \
  -v /opt/ragflowauth/uploads:/app/uploads \
  -v /opt/ragflowauth/ragflow_config.json:/app/ragflow_config.json:ro \
  ragflowauth-backend:2026-01-22

docker run -d \
  --name ragflowauth-frontend \
  --network ragflowauth-network \
  -p 3001:80 \
  --link ragflowauth-backend:backend \
  ragflowauth-frontend:2026-01-22
```

## 配置管理

### 修改 RAGFlow API Key

部署后，你可以随时修改配置：

```bash
# 登录服务器
ssh root@172.30.30.57

# 编辑配置文件
vi /opt/ragflowauth/ragflow_config.json

# 重启后端容器使配置生效
docker restart ragflowauth-backend
```

### 配置文件位置

- **服务器**: `/opt/ragflowauth/ragflow_config.json`
- **本地**: `ragflow_config.json`（项目根目录）

## 访问地址

部署成功后，你可以通过以下地址访问：

- **前端**: http://172.30.30.57:3001
- **后端 API**: http://172.30.30.57:8001
- **API 文档**: http://172.30.30.57:8001/docs

## 容器管理

```bash
# 查看运行中的容器
docker ps | grep ragflowauth

# 查看后端日志
docker logs -f ragflowauth-backend

# 查看前端日志
docker logs -f ragflowauth-frontend

# 重启服务
docker restart ragflowauth-backend ragflowauth-frontend

# 停止服务
docker stop ragflowauth-backend ragflowauth-frontend

# 删除容器（保留数据）
docker rm ragflowauth-backend ragflowauth-frontend

# 完全清理（包括数据）
docker stop ragflowauth-backend ragflowauth-frontend
docker rm ragflowauth-backend ragflowauth-frontend
rm -rf /opt/ragflowauth
```

## 数据持久化

以下目录会被持久化到宿主机：

| 容器内路径 | 宿主机路径 | 说明 |
|-----------|-----------|------|
| `/app/data` | `/opt/ragflowauth/data` | SQLite 数据库 |
| `/app/uploads` | `/opt/ragflowauth/uploads` | 上传文件 |
| `/app/ragflow_config.json` | `/opt/ragflowauth/ragflow_config.json` | 配置文件（只读） |
| `/app/ragflow_compose` | `/opt/ragflowauth/ragflow_compose` | RAGFlow Compose 文件（只读，用于备份） |

## 故障排查

### 1. 容器无法启动

```bash
# 查看容器日志
docker logs ragflowauth-backend
docker logs ragflowauth-frontend

# 检查容器状态
docker ps -a | grep ragflowauth
```

### 2. 前端无法连接后端

确保前端容器使用了 `--link` 参数连接到后端：

```bash
docker inspect ragflowauth-frontend | grep -A 10 Links
```

### 3. 端口冲突

如果端口被占用，可以修改端口映射：

```bash
# 停止并删除旧容器
docker stop ragflowauth-backend ragflowauth-frontend
docker rm ragflowauth-backend ragflowauth-frontend

# 使用新端口启动
docker run -d --name ragflowauth-backend -p 8081:8001 ...
docker run -d --name ragflowauth-frontend -p 8080:80 ...
```

### 4. SSH 连接失败

- 确保 OpenSSH 客户端已启用（Windows 设置 -> 应用 -> 可选功能）
- 检查服务器地址和用户名是否正确
- 确保服务器允许 SSH 连接

## 高级用法

### 使用配置文件

编辑 `deploy-config.json`：

```json
{
  "server": {
    "host": "192.168.1.100",
    "user": "ubuntu"
  },
  "docker": {
    "tag": "production",
    "frontend_port": 80,
    "backend_port": 8001
  }
}
```

然后在部署时引用：

```powershell
$config = Get-Content deploy-config.json | ConvertFrom-Json
.\deploy.ps1 -ServerHost $config.server.host -ServerUser $config.server.user
```

### 多环境部署

为不同环境创建不同的配置：

```powershell
# 开发环境
.\deploy.ps1 -Tag "dev" -ServerHost "dev.example.com"

# 测试环境
.\deploy.ps1 -Tag "staging" -ServerHost "staging.example.com"

# 生产环境
.\deploy.ps1 -Tag "prod" -ServerHost "prod.example.com"
```

## 工作流程图

```
┌─────────────────┐
│  本地开发环境    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 1. 构建镜像      │
│   - 前端镜像     │
│   - 后端镜像     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 导出镜像      │
│   - 生成 tar 文件│
│   - SHA256 校验  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 传输到服务器  │
│   - SCP 传输     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 服务器部署    │
│   - 加载镜像     │
│   - 启动容器     │
│   - 配置挂载     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. 验证部署     │
│   - 检查容器状态 │
│   - 查看日志     │
└─────────────────┘
```

## 常见问题

**Q: 如何更新已部署的应用？**

A: 重新运行部署脚本即可。脚本会自动停止旧容器并启动新容器。

```powershell
.\deploy.ps1
```

**Q: 数据会丢失吗？**

A: 不会。数据存储在宿主机的 `/opt/ragflowauth/` 目录中，容器更新不会影响数据。

**Q: 如何回滚到旧版本？**

A: 使用旧版本的镜像标签重新部署：

```powershell
.\deploy.ps1 -Tag "2026-01-21"
```

**Q: 镜像文件很大，传输很慢怎么办？**

A: 可以：
1. 在服务器上直接构建（需要安装 docker-compose）
2. 使用压缩传输工具
3. 使用内网传输

**Q: 如何在多个服务器上部署？**

A: 使用不同的服务器地址运行多次：

```powershell
.\deploy.ps1 -ServerHost "server1.example.com"
.\deploy.ps1 -ServerHost "server2.example.com"
```

## 许可证

MIT License
