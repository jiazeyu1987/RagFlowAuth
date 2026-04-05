# RagflowAuth 快速部署脚本

## 功能说明

快速部署脚本用于将本地代码部署到远程服务器的 Docker 容器中。

**部署流程：**
1. 停止服务器上运行的前后端容器
2. 构建前端和后端的 Docker 镜像
3. 导出镜像为 tar 文件
4. 通过 SCP 传输到服务器
5. 在服务器上加载镜像
6. 保留原容器配置，启动新容器
7. 验证部署状态

## 使用方法

### 方式 1: 双击运行（推荐）

双击 `tool/scripts/quick-deploy.bat` 即可自动完成部署。

### 方式 2: 命令行运行

```powershell
# 基础用法
.\tool\scripts\quick-deploy.ps1

# 指定标签
.\tool\scripts\quick-deploy.ps1 -Tag "v1.0.0"

# 跳过构建（如果镜像已存在）
.\tool\scripts\quick-deploy.ps1 -SkipBuild

# 跳过传输（仅构建本地镜像）
.\tool\scripts\quick-deploy.ps1 -SkipTransfer

# 跳过加载（仅传输镜像）
.\tool\scripts\quick-deploy.ps1 -SkipLoad
```

## 配置文件

脚本读取 `tool/scripts/deploy-config.json` 配置文件：

```json
{
  "server": {
    "host": "172.30.30.57",
    "user": "root",
    "port": 22
  },
  "docker": {
    "tag": "2026-01-22",
    "frontend_port": 3001,
    "backend_port": 8001,
    "network": "ragflowauth-network"
  },
  "paths": {
    "data_dir": "/opt/ragflowauth"
  }
}
```

## 前置要求

### Windows 本地环境

1. **Docker Desktop** 必须运行
   - 确保 Docker 引擎已启动
   - 可以运行 `docker ps` 测试

2. **OpenSSH 客户端**（Windows 10/11 内置）
   - 打开"设置 → 应用 → 可选功能"
   - 安装"OpenSSH 客户端"

3. **SSH 密钥配置**（推荐）
   - 生成密钥：`ssh-keygen -t rsa -b 4096`
   - 复制公钥到服务器：`ssh-copy-id root@172.30.30.57`
   - 或手动复制 `~/.ssh/id_rsa.pub` 内容到服务器的 `~/.ssh/authorized_keys`

   如果未配置密钥，脚本会提示输入密码。

### 服务器环境

1. **Docker 已安装并运行**
2. **网络已创建**：`ragflowauth-network`
   - 如需创建：`docker network create ragflowauth-network`
3. **数据目录存在**：`/opt/ragflowauth/data`
   - 脚本会自动挂载这些卷

## 工作流程详解

### 1. 停止容器

```bash
ssh root@172.30.30.57 "docker stop ragflowauth-frontend ragflowauth-backend"
```

### 2. 构建镜像

**后端镜像：**
```bash
docker build -f docker/backend.Dockerfile -t ragflowauth-backend:2026-01-22-120000 .
```

**前端镜像：**
```bash
cd fronted
docker build -t ragflowauth-frontend:2026-01-22-120000 .
```

### 3. 导出镜像

```bash
docker save ragflowauth-frontend:2026-01-22-120000 -o temp/ragflowauth-frontend-2026-01-22-120000.tar
docker save ragflowauth-backend:2026-01-22-120000 -o temp/ragflowauth-backend-2026-01-22-120000.tar
```

### 4. 传输并验证

```bash
scp temp/*.tar root@172.30.30.57:/tmp/
sha256sum 校验确保传输完整性
```

### 5. 加载镜像

```bash
ssh root@172.30.30.57 "docker load -i /tmp/ragflowauth-frontend-2026-01-22-120000.tar"
ssh root@172.30.30.57 "docker load -i /tmp/ragflowauth-backend-2026-01-22-120000.tar"
```

### 6. 启动容器

脚本会保留原有容器的配置（卷挂载、环境变量等），只替换镜像。

### 7. 验证

检查容器状态：
```bash
docker ps | grep ragflowauth
```

访问服务：
- 前端：http://172.30.30.57:3001
- 后端：http://172.30.30.57:8001

## 高级用法

### 仅构建本地镜像（不部署）

```powershell
.\tool\scripts\quick-deploy.ps1 -SkipTransfer -SkipLoad
```

### 分步部署

```powershell
# 第一步：构建镜像
.\tool\scripts\quick-deploy.ps1 -SkipTransfer -SkipLoad

# 第二步：传输镜像
.\tool\scripts\quick-deploy.ps1 -SkipBuild -SkipLoad

# 第三步：加载并启动
.\tool\scripts\quick-deploy.ps1 -SkipBuild -SkipTransfer
```

## 故障排查

### 1. Docker 连接失败

确保 Docker Desktop 正在运行：
```powershell
docker ps
```

### 2. SSH 连接失败

测试 SSH 连接：
```powershell
ssh root@172.30.30.57
```

### 3. 权限错误

确保用户有访问 Docker 的权限。

### 4. 端口冲突

如果端口被占用，修改 `deploy-config.json` 中的端口配置。

### 5. 容器启动失败

查看容器日志：
```bash
ssh root@172.30.30.57 "docker logs ragflowauth-backend"
ssh root@172.30.30.57 "docker logs ragflowauth-frontend"
```

## 清理临时文件

脚本会自动清理：
- 本地：`tool/scripts/temp/` 目录
- 服务器：`/tmp/*.tar` 文件

手动清理：
```powershell
Remove-Item -Recurse -Force tool/scripts/temp
```

## 与完整部署脚本的区别

- **quick-deploy.ps1**：快速部署，仅更新代码镜像
- **deploy.ps1**：完整部署，包含初始化配置、网络设置等

对于日常开发更新，使用 `quick-deploy.ps1` 更快捷。
