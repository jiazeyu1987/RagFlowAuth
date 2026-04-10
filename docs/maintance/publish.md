# 发布

## 文档范围

这份文档只解释 `tool/maintenance/` 当前已经实现的发布链路，不扩展仓库里没有落地的流程。

对应源码入口主要包括：

- `tool/maintenance/tool.py`
- `tool/maintenance/ui/release_tab.py`
- `tool/maintenance/features/release_publish_local_to_test.py`
- `tool/maintenance/features/release_publish.py`
- `tool/maintenance/features/release_publish_data_test_to_prod.py`
- `tool/maintenance/features/release_rollback.py`
- `tool/maintenance/controllers/release/*.py`

## 服务器与固定路径

| 角色 | IP | 默认用户 | 主要用途 |
| --- | --- | --- | --- |
| 本机 | 本地工作区 | 当前 Windows 用户 | 构建镜像、发起 ssh/scp、准备本地备份包 |
| 测试服务器 | `172.30.30.58` | `root` | 接收本机发布、承载测试环境、作为正式发布的镜像与数据来源 |
| 正式服务器 | `172.30.30.57` | `root` | 承载生产环境、接收测试环境镜像或数据 |

固定运行事实来自 `tool/maintenance/core/constants.py` 与发布实现：

- 远端应用目录：`/opt/ragflowauth`
- 前端端口：`3001`
- 后端端口：`8001`
- RAGFlow 端口：`9380`
- 本地 RAGFlow `base_url` 期望值：`http://127.0.0.1:9380`
- 测试服 RAGFlow `base_url` 期望值：`http://172.30.30.58:9380`
- 正式服 RAGFlow `base_url` 期望值：`http://172.30.30.57:9380`

## 发布页签里的三条链路

`tool/maintenance/ui/release_tab.py` 把发布能力拆成三条明确链路：

1. 本机 -> 测试
2. 测试 -> 正式（镜像）
3. 测试 -> 正式（数据）

### 1. 本机 -> 测试

对应实现：

- UI 与确认：`tool/maintenance/ui/release_tab.py`、`tool/maintenance/controllers/release/publish_local_confirm_ops.py`
- 主流程：`tool/maintenance/features/release_publish_local_to_test.py`
- 成功后的可选数据同步：`tool/maintenance/controllers/release/publish_local_outcome_ops.py`、`tool/maintenance/controllers/release/sync_ops.py`

工具当前的发布顺序是：

1. 先做 `base_url` 守卫，确保本机仍指向 `127.0.0.1:9380`，测试服指向 `172.30.30.58:9380`。
2. 本地预拉基础镜像：`python:3.12-slim`、`node:20-alpine`、`nginx:1.27-alpine`。
3. 用仓库根目录构建两张镜像：
   - `backend/Dockerfile`
   - `fronted/Dockerfile`
4. 以同一个版本号打标签：
   - `ragflowauth-backend:<version>`
   - `ragflowauth-frontend:<version>`
5. 把两张镜像合并 `docker save` 为一个 tar 包。
6. 用 `RemoteStagingManager` 在测试服选择有足够可写空间的暂存目录，再通过 `scp` 上传。
7. 在测试服 `docker load`。
8. 优先按现有容器 `inspect` 结果重建 `ragflowauth-backend` 与 `ragflowauth-frontend`。
9. 如果测试服上还没有现成容器，则进入 bootstrap 模式做首次部署。
10. 完成后刷新版本信息与 `base_url`。

如果在 UI 中勾选“发布后同步数据到测试”，工具会在镜像发布成功后追加一次数据同步：

- 来源：本机固定目录 `\\172.30.30.4\Backup\auth`
- 选中规则：优先使用选择的 `migration_pack_*`，否则默认最新备份
- 覆盖内容：
  - `auth.db`
  - RAGFlow volumes

这一步是覆盖测试数据的破坏性操作，因此确认框会二次提醒。

### 2. 测试 -> 正式（镜像）

对应实现：

- UI 与确认：`tool/maintenance/ui/release_tab.py`、`tool/maintenance/controllers/release/publish_test_confirm_ops.py`
- 主流程：`tool/maintenance/features/release_publish.py`
- worker：`tool/maintenance/controllers/release/publish_test_worker_ops.py`

这条链路的核心目标不是重新在正式服构建镜像，而是把测试服当前正在使用的镜像版本原样带到正式服。

流程摘要：

1. 读取测试服当前运行中的 backend 或 frontend 镜像标签。
2. 对测试服和正式服都执行 `base_url` 预检查，拒绝“测试服读正式数据”或“正式服读测试数据”的交叉配置。
3. 在测试服上 `docker save` 当前使用的 `ragflowauth-backend` 与 `ragflowauth-frontend`。
4. 如果 UI 勾选“同步 RAGFlow 镜像”，还会把检测到的 `infiniflow/ragflow:*` 镜像一起打包。
5. 用 `scp -3` 做测试服到正式服的远端到远端传输。
6. 如果能检测到 compose 或 `.env` 文件路径，则把这些发布相关文件一起传到正式服；如果检测不到，则退回到纯容器重建路径。
7. 在正式服 `docker load` 并重建容器。
8. 对正式服执行后置 `base_url` 守卫和健康检查。

这里的“回滚入口”也在同一个页签里，因为它和正式服镜像版本直接相关。

### 3. 测试 -> 正式（数据）

对应实现：

- UI 与双重确认：`tool/maintenance/ui/release_tab.py`、`tool/maintenance/controllers/release/publish_data_confirm_ops.py`
- 主流程：`tool/maintenance/features/release_publish_data_test_to_prod.py`
- worker：`tool/maintenance/controllers/release/publish_data_worker_ops.py`

这是整套工具里风险最高的一条链路。UI 会连续两次确认，因为它会覆盖正式环境数据。

覆盖内容来自 `release_publish_data_test_to_prod.py` 与 UI 文案：

- `auth.db`
- RAGFlow volumes

执行前的关键保护：

1. 读取测试服 `ragflow_config.json`，确认 `base_url` 指向测试服自己或本地环回。
2. 自动修正正式服 `ragflow_config.json` 里的 `base_url`，确保它指向正式服自己的 `9380`。
3. 停止相关服务并验证停止状态。

执行中的关键步骤：

1. 从测试服准备需要同步的数据包。
2. 通过 `scp -3` 直接从测试服传到正式服。
3. 在正式服恢复 `auth.db` 与 volumes。
4. 确保正式服上的 RAGFlow 和 RagflowAuth 重新启动。
5. 针对容器状态、bridge 网络与健康状态做等待和校验。

这条链路不会把“测试服数据”伪装成“正式服数据兼容层”，而是直接覆盖正式数据。

## 正式环境回滚

回滚能力对应：

- UI：`tool/maintenance/ui/release_tab.py`
- 逻辑：`tool/maintenance/features/release_rollback.py`

当前实现方式是：

1. 在正式服上列出同时存在 backend 与 frontend 标签的版本号。
2. 选择一个版本。
3. 读取现有 `ragflowauth-backend` 与 `ragflowauth-frontend` 容器的 `inspect` 结果。
4. 保留当前容器网络、挂载、环境变量、端口等运行形态。
5. 停掉旧容器并按选定版本重建。
6. 对 `http://127.0.0.1:8001/health` 做健康检查。

这意味着当前回滚依赖“正式服上已经存在可 inspect 的容器”这个前提。如果正式服压根没有这两个容器，代码会直接失败并提示先走正常发布。

## 发布记录

成功的发布、数据同步、回滚都会通过 `record_release_event` 追加到本地文件：

- `doc/maintenance/release_history.md`

这里要注意一个仓库事实：

- 本次新增文档目录是 `docs/maintance/`
- 但工具当前仍把发布历史写到 legacy 路径 `doc/maintenance/release_history.md`

这不是本文档新增的行为，而是当前代码现状。

## 运维注意事项

- 文档中只记录服务器角色、路径、端口和流程，不复制密码、共享凭据、API key 或 JWT secret。
- `fronted/` 是当前仓库里真实的前端目录名，发布流程也是按这个名字构建镜像，不应在文档里擅自改写成 `frontend/`。
- 发布到测试与正式之前，维护工具都会主动检查或修正 `ragflow_config.json` 的 `base_url`，这是当前发布安全边界的重要组成部分。
