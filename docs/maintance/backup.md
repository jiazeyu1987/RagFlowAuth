# 备份

## 文档范围

这份文档只解释当前维护工具里已经存在的备份、恢复和备份目录管理能力，不推导仓库里没有实现的灾备策略。

主要事实来源：

- `tool/maintenance/ui/backup_files_tab.py`
- `tool/maintenance/ui/replica_backups_tab.py`
- `tool/maintenance/ui/restore_tab.py`
- `tool/maintenance/controllers/release/sync_ops.py`
- `tool/maintenance/controllers/release/sync_precheck_ops.py`
- `tool/maintenance/controllers/release/sync_auth_upload_ops.py`
- `tool/maintenance/controllers/release/sync_volumes_ops.py`
- `tool/maintenance/core/constants.py`

## 备份相关的三类位置

### 1. 本地备份目录

维护工具把本地备份源固定在：

- `D:\datas\RagflowAuth`

当前约定的备份包名称通常是 `migration_pack_*`。代码期望的最小内容是：

- `auth.db`

可选内容：

- `volumes/`

如果缺少 `auth.db`，同步流程会直接失败；如果缺少 `volumes/`，则只同步数据库，不同步 RAGFlow 数据卷。

### 2. 服务器本地备份文件

`tool/maintenance/ui/backup_files_tab.py` 把服务器本地备份拆成两个位置查看：

- `/opt/ragflowauth/data/backups/`
  - 主要存放 `auth.db`
- `/opt/ragflowauth/backups/`
  - 主要存放 `volumes/*.tar.gz`

这个页签支持：

- 刷新文件列表
- 删除选中文件
- 按保留天数清理旧备份

### 3. 服务器本地备份目录

`tool/maintenance/ui/replica_backups_tab.py` 又提供了一个“服务器本地备份目录”视图，目标路径是：

- `/opt/ragflowauth/data/backups`

这里会分开查看：

- 测试服务器 `172.30.30.58`
- 正式服务器 `172.30.30.57`

并允许分别删除对应服务器上的备份目录。

## `/mnt/replica` 不是服务器本地备份目录

`tool/maintenance/core/constants.py` 里当前固定的共享挂载点是：

- `MOUNT_POINT = /mnt/replica`
- `REPLICA_TARGET_DIR = /mnt/replica/RagflowAuth`

需要区分两件事：

- `/opt/ragflowauth/data/backups`、`/opt/ragflowauth/backups`
  - 这是服务器本机磁盘上的备份位置
- `/mnt/replica`
  - 这是挂载出来的共享位置

`replica_backups_tab.py` 的 UI 文案也明确说明：它管理的是服务器本地备份，不是 Windows 共享。

## 恢复与同步只允许到测试服务器

### 恢复页签

`tool/maintenance/ui/restore_tab.py` 在 UI 文案里明确限制：

- 恢复目标只能是测试服务器 `172.30.30.58`
- 不会直接影响正式服务器

恢复页签从本地固定目录 `D:\datas\RagflowAuth` 选择备份，说明中写明恢复内容包括：

- `auth.db`
- volumes
- 如果备份包里存在 `images.tar`，也会恢复镜像

### 发布成功后的“同步数据到测试”

这条能力不是独立页签，而是“本机 -> 测试”发布成功后的可选追加步骤，核心实现位于：

- `tool/maintenance/controllers/release/sync_ops.py`

它的边界和恢复页签不同：

- 只会同步到测试服务器
- 只同步数据，不恢复镜像
- 明确禁止用 `images.tar` 覆盖刚刚发布的新镜像

同步步骤来自 `sync_ops.py` 与相关 helper：

1. 从 `D:\datas\RagflowAuth` 选定一个 `migration_pack_*`
2. 校验必须存在 `auth.db`
3. 如有 `volumes/` 则同时准备 volumes 恢复
4. 检查并修正测试服 `ragflow_config.json` 的 `base_url`
5. 停止测试服相关服务
6. 先对测试服当前 `auth.db` 做 best-effort 备份到 `/tmp/restore_backup_<ts>/auth.db`
7. 把新的 `auth.db` 上传到 `/opt/ragflowauth/data/auth.db`
8. 如果有 `volumes/`，先打包为 `volumes.tar.gz`，上传到 `/var/lib/docker/tmp/`
9. 在测试服用临时目录和临时容器恢复各个 docker volume
10. 重启服务并执行后端健康检查
11. 再次执行测试服 `base_url` 守卫

## 备份与恢复的环境边界

| 能力 | 测试服 | 正式服 |
| --- | --- | --- |
| 查看服务器本地备份文件 | 支持 | 支持 |
| 查看服务器本地备份目录 | 支持 | 支持 |
| 删除服务器本地备份目录 | 支持 | 支持 |
| 从本地备份恢复数据 | 支持 | 不支持 |
| 发布后把本地备份同步到服务器 | 支持 | 不支持 |
| 把测试数据同步到正式 | 作为来源 | 作为目标，且覆盖正式数据 |

这里的设计很明确：

- 本地恢复或同步只允许去测试服
- 正式服的数据覆盖只能走“测试 -> 正式（数据）”那条高风险链路

## 运维注意事项

- 新文档不会复制共享密码、JWT secret、API key 等敏感字面量；如确实需要查看，只能回源代码或安全配置源。
- `/mnt/replica` 的健康状态会在冒烟检查中出现，但它和服务器本地备份目录不是一回事。
- 如果本地备份包缺少 `auth.db`，同步流程会直接失败；如果缺少 `volumes/`，流程会记录 warning 并只同步数据库。
