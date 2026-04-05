# RagflowAuth 部署工具

自动化部署 Docker 镜像到远程服务器的工具集。

## 📁 文件结构

```
tool/
├── deploy.ps1              # 主部署脚本（PowerShell）
├── deploy-quick.bat        # 快速启动脚本（双击运行）
├── deploy-config.json      # 部署配置文件
├── DEPLOY.md               # 详细部署文档
├── DEPLOY-TOOLS-README.md  # 快速入门指南
├── README.md               # 本文件
└── scripts/
    └── remote-deploy.sh    # 服务器端部署脚本
```

## 🚀 快速开始

### 方式 1: 双击运行（推荐）

```
双击 deploy-quick.bat
```

### 方式 2: PowerShell 脚本

```powershell
# 进入 tool 目录
cd tool

# 使用默认配置部署
.\deploy.ps1

# 跳过构建步骤（使用已有镜像）
.\deploy.ps1 -SkipBuild
```

## 📖 详细文档

- **快速入门**: 查看 [DEPLOY-TOOLS-README.md](DEPLOY-TOOLS-README.md)
- **完整文档**: 查看 [DEPLOY.md](DEPLOY.md)

## 📝 使用说明

所有部署脚本都应该从 `tool/` 目录运行。

### 示例

```powershell
# 在项目根目录
cd tool
.\deploy.ps1

# 或者直接指定路径
powershell.exe -ExecutionPolicy Bypass -File tool\deploy.ps1
```

## ⚙️ 配置

编辑 `deploy-config.json` 修改默认配置：

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

## 🔧 故障排查

如遇问题，请查看 [DEPLOY.md](DEPLOY.md) 的故障排查章节。

---

**提示**: 首次使用建议阅读 [DEPLOY-TOOLS-README.md](DEPLOY-TOOLS-README.md) 了解完整功能。
