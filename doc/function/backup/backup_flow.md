# 数据安全备份流程

## 核心规则

- 本地正式备份目录固定为 `/app/data/backups`。
- 备份先在 staging 目录构建，再分别投递到本地正式目录和 Windows 目录。
- Windows 目录优先使用 `replica_target_path`，为空时回退到 `target_mode/target_ip/target_share_name/target_subdir/target_local_dir` 解析结果。
- 任务总状态按聚合结果计算。
  - 本地成功且 Windows 成功: `completed`
  - 本地成功且 Windows 失败或跳过: `completed`
  - 本地失败且 Windows 成功: `completed`
  - 本地失败且 Windows 失败: `failed`
- 恢复演练只允许使用 `backup_jobs.output_dir` 指向的本地正式备份。

## 备份执行顺序

1. 在 `/app/data/backups/_staging/job_<id>/migration_pack_<timestamp>` 创建 staging 包目录。
2. 向 staging 包写入：
   - `auth.db`
   - `volumes/*.tar.gz`
   - `images.tar`（全量且开启镜像备份时）
   - `backup_settings.json`
3. 对 staging 包计算一次 `package_hash`。
4. 将 staging 包原子移动到 `/app/data/backups/migration_pack_<timestamp>`。
   - 成功后写入 `backup_jobs.output_dir`
5. 如果启用了 Windows 复制，再把迁移包复制到 Windows 目标目录。
   - 成功后写入 `backup_jobs.replica_path`
   - `replication_status` 只表示 Windows 复制结果，不表示整单结果
6. 根据本地结果和 Windows 结果计算最终 `status/message/detail`。

## 关键字段语义

- `backup_jobs.output_dir`
  - 本地正式备份目录
  - 存在时代表本地备份成功
- `backup_jobs.replica_path`
  - Windows 备份目录
  - 存在且 `replication_status=succeeded` 时代表 Windows 备份成功
- `backup_jobs.replication_status`
  - `succeeded`: Windows 备份成功
  - `failed`: Windows 备份失败
  - `skipped`: Windows 未启用、未配置或未执行
- `backup_jobs.status`
  - 整个任务的聚合结果

## 页面展示约定

- 数据安全页同时展示：
  - 本地备份路径与数量
  - Windows 备份路径与数量
- 任务详情和任务列表同时展示：
  - 本地备份状态
  - Windows 备份状态
- 恢复演练下拉框只列出 `output_dir` 非空的任务。

## 运维检查点

- 本地正式备份应出现在 `/app/data/backups/migration_pack_*`
- Windows 备份应出现在目标目录 `migration_pack_*`
- Windows 复制成功目录应包含：
  - `auth.db`
  - `replication_manifest.json`
  - `DONE`
- 如果 Windows 目录在 `/mnt/replica` 下，复制前仍要求 `/mnt/replica` 是有效 CIFS 挂载。
