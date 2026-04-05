# RagflowAuth 部署指南

## 快速开始

### 方式 1: 双击部署（推荐）

双击项目根目录的 `quick-deploy.bat` 文件，即可完成自动部署：

- ✅ 自动递增版本号（1.0.0 → 1.0.1 → 1.0.2）
- ✅ 构建 Docker 镜像
- ✅ 上传到服务器
- ✅ 自动清理旧镜像

### 方式 2: PowerShell 命令

```powershell
# 默认部署（自动递增 patch 版本）
.\tool\scripts\deploy.ps1

# 递增次版本号（1.0.0 → 1.1.0）
.\tool\scripts\deploy.ps1 -IncrementMinor

# 递增主版本号（1.0.0 → 2.0.0）
.\tool\scripts\deploy.ps1 -IncrementMajor

# 不递增版本，使用当前版本号
.\tool\scripts\deploy.ps1 -NoAutoIncrement

# 使用自定义标签（不修改版本号）
.\tool\scripts\deploy.ps1 -Tag "custom-tag"
```

## 版本管理

### 版本号格式

使用语义化版本（Semantic Versioning）：`主版本.次版本.补丁版本`

- **主版本（Major）**：不兼容的 API 修改
- **次版本（Minor）**：向下兼容的功能性新增
- **补丁版本（Patch）**：向下兼容的问题修正

示例：
```
1.0.0 → 1.0.1 → 1.0.2 (Bug 修复)
1.0.2 → 1.1.0 → 1.2.0 (新功能)
1.2.0 → 2.0.0      (重大变更)
```

### 版本文件

项目根目录的 `.version` 文件存储当前版本号：

```
1.0.0
```

**⚠️ 不要手动修改此文件**，除非您知道自己在做什么。

## 部署流程说明

完整的部署流程包括：

### 1. 版本管理
- 读取 `.version` 文件
- 根据参数递增版本号（默认递增 patch）
- 更新 `.version` 文件

### 2. 构建镜像
```bash
docker compose -f docker/docker-compose.yml build
```
镜像标签：`ragflowauth-backend:1.0.1`, `ragflowauth-frontend:1.0.1`

### 3. 导出镜像
```bash
docker save -o dist/ragflowauth-images_1.0.1.tar ragflowauth-backend:1.0.1 ragflowauth-frontend:1.0.1
```

### 4. 上传到服务器
```bash
scp dist/ragflowauth-images_1.0.1.tar root@172.30.30.57:/tmp/
```

### 5. 部署到服务器
- 加载镜像
- 停止旧容器
- 启动新容器
- 自动清理旧镜像

### 6. 清理
- 删除本地 tar 文件
- 清理服务器上的旧镜像（只保留当前版本）

## 高级选项

### 跳过特定步骤

```powershell
# 跳过镜像构建（仅修改配置文件时使用）
.\tool\scripts\deploy.ps1 -SkipBuild

# 跳过文件传输（镜像已在服务器上）
.\tool\scripts\deploy.ps1 -SkipTransfer

# 跳过服务器部署（仅构建和上传）
.\tool\scripts\deploy.ps1 -SkipDeploy

# 跳过清理（保留旧镜像）
.\tool\scripts\deploy.ps1 -SkipCleanup
```

### 指定服务器

```powershell
# 部署到不同服务器
.\tool\scripts\deploy.ps1 -ServerHost "192.168.1.100" -ServerUser "admin"
```

### 自定义输出目录

```powershell
.\tool\scripts\deploy.ps1 -OutDir "my-dist"
```

## 镜像清理策略

默认情况下，部署脚本会自动清理服务器上的旧镜像：

- **保留策略**：只保留当前运行的版本
- **清理对象**：所有未被容器使用的 ragflowauth 镜像
- **安全保证**：永不删除运行中容器使用的镜像

如需保留更多版本（用于回滚），可以在服务器上手动运行：

```bash
ssh root@172.30.30.57
/tmp/cleanup-images.sh --keep 3  # 保留最近 3 个版本
```

## 故障排查

### 问题：部署失败，容器未启动

**检查容器状态：**
```bash
ssh root@172.30.30.57 "docker ps -a | grep ragflowauth"
```

**查看容器日志：**
```bash
ssh root@172.30.30.57 "docker logs ragflowauth-backend"
ssh root@172.30.30.57 "docker logs ragflowauth-frontend"
```

### 问题：镜像上传失败

**检查网络连接：**
```powershell
Test-NetConnection -ComputerName 172.30.30.57 -Port 22
```

**手动上传：**
```powershell
scp dist/ragflowauth-images_*.tar root@172.30.30.57:/tmp/
```

### 问题：版本号异常

**查看当前版本：**
```powershell
cat .version
```

**重置版本号：**
```powershell
echo "1.0.0" > .version
```

## 回滚到旧版本

如果新版本有问题，可以快速回滚：

```bash
# 1. 查看可用的镜像版本
ssh root@172.30.30.57 "docker images | grep ragflowauth"

# 2. 停止当前容器
ssh root@172.30.30.57 "docker stop ragflowauth-backend ragflowauth-frontend"

# 3. 删除当前容器
ssh root@172.30.30.57 "docker rm ragflowauth-backend ragflowauth-frontend"

# 4. 使用旧版本镜像启动（例如 1.0.0）
ssh root@172.30.30.57 "docker run -d --name ragflowauth-backend --network ragflowauth-network -p 8001:8001 -v /opt/ragflowauth/data:/app/data -v /opt/ragflowauth/uploads:/app/uploads -v /opt/ragflowauth/ragflow_config.json:/app/ragflow_config.json:ro -v /opt/ragflowauth/ragflow_compose:/app/ragflow_compose:ro -v /opt/ragflowauth/backups:/app/data/backups -v /var/run/docker.sock:/var/run/docker.sock ragflowauth-backend:1.0.0"

ssh root@172.30.30.57 "docker run -d --name ragflowauth-frontend --network ragflowauth-network -p 3001:80 --link ragflowauth-backend:backend ragflowauth-frontend:1.0.0"
```

或者使用快捷脚本：
```bash
ssh root@172.30.30.57 "/opt/ragflowauth/quick-restart.sh --tag 1.0.0"
```

## 最佳实践

1. **小步提交**：频繁部署小改动，而不是累积大改动
2. **测试先行**：在本地测试通过后再部署
3. **查看日志**：部署后检查容器日志确保没有错误
4. **保留回滚版本**：重要版本发布时，使用 `--keep 3` 保留旧版本
5. **版本规范**：
   - Bug 修复：递增 patch 版本（默认）
   - 新功能：递增 minor 版本（`-IncrementMinor`）
   - 重大变更：递增 major 版本（`-IncrementMajor`）

## 相关文件

- `tool/scripts/deploy.ps1` - 主部署脚本
- `tool/scripts/remote-deploy.sh` - 服务器端部署脚本
- `tool/scripts/cleanup-images.sh` - 镜像清理脚本
- `.version` - 版本号文件
- `quick-deploy.bat` - 快速部署入口
- `docker/docker-compose.yml` - Docker Compose 配置
