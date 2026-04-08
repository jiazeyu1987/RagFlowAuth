# 备份

## 文档范围

本文只描述当前仓库里已经实现的备份、拉取与恢复能力，内容以现有代码为准，不假设旧的 CIFS/挂载链路仍然属于正式备份流程。

主要事实来源：

- `backend/services/data_security/backup_service.py`
- `backend/app/modules/data_security/support.py`
- `tool/maintenance/server_backup_pull_tool.py`
- `tool/maintenance/features/server_backup_pull.py`
- `tool/maintenance/features/local_backup_catalog.py`
- `tool/maintenance/features/local_backup_restore.py`

## 当前正式备份逻辑

正式逻辑只要求服务器本机备份。

- 正式备份任务只以服务器本机备份结果判定成功或失败。
- 正式备份页面只展示服务器本机备份路径、进度、记录和恢复演练入口。
- 正式逻辑不再检查 Windows 挂载点，不再统计 Windows 副本，不再提示 Windows 备份状态。
- Windows 端如需副本，使用独立手动拉取工具，不属于正式自动备份链路。

当前接口返回给页面的正式备份目录是：

- `/app/data/backups`

## 服务器备份拉取工具

仓库提供了一个独立的 Windows GUI，用于从服务器读取备份列表并把选中的备份拉到本机：

- `tool/maintenance/server_backup_pull_tool.py`

该工具的当前事实：

- 正式服务器 IP：`172.30.30.57`
- 测试服务器 IP：`172.30.30.58`
- 服务器备份根目录：`/opt/ragflowauth/backups`
- 本地默认保存目录：`D:\datas\RagflowAuth`

当前可识别的服务器备份目录前缀包括：

- `migration_pack_*`
- `full_backup_pack_*`

## 正确流程

如果需要在 Windows 上保留一份副本，当前正确流程是：

1. 启动 `python tool/maintenance/server_backup_pull_tool.py`
2. 在下拉框中选择正式服务器或测试服务器
3. 点击“加载服务器备份列表”
4. 在服务器备份列表中选中一个备份
5. 选择本地保存目录
6. 点击拉取，把服务器备份复制到 Windows 本地
7. 拉取完成后，从本地备份列表中选择一个本地备份
8. 如需验证或恢复，再从本地列表发起恢复

也就是说，恢复动作先依赖“拉取到本地”，然后才依赖“从本地列表恢复”，不再直接从服务器列表恢复。

## 本地恢复行为

从本地列表恢复时，当前实现会执行以下检查和动作：

1. 校验所选本地备份目录存在
2. 校验备份目录内存在 `auth.db`
3. 校验当前仓库 `data/auth.db` 存在
4. 校验本地 `127.0.0.1:8001` 上的 RagflowAuth 后端未运行
5. 用备份中的 `auth.db` 覆盖当前仓库的 `data/auth.db`
6. 如果备份中包含 `volumes/*.tar.gz`，则尝试恢复到本机匹配的 Docker volumes
7. 恢复 volume 时会先停止占用这些 volume 的本机 Docker 容器，再在结束后尝试重新启动

以下情况会直接失败，不做 fallback：

- 本地备份目录不存在
- 备份缺少 `auth.db`
- 当前仓库缺少 `data/auth.db`
- 本地后端仍在 `127.0.0.1:8001` 运行
- 备份包含 volume 归档，但本机没有可用 Docker
- 备份 volume 不能唯一映射到本机 Docker volume

## 与 Windows 挂载点的关系

当前正式逻辑不再依赖以下能力：

- `/mnt/replica`
- CIFS 挂载
- SMB 挂载状态检测

独立拉取工具的工作方式是“Windows 本机主动通过 SSH/SCP 到服务器拉取备份”，因此即使服务器上没有正确挂载 Windows 共享，正式备份和独立拉取工具仍然可以各自工作，只要各自所需前提满足。
