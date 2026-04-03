# 备份与恢复演练 SOP

版本: v1.1  
更新时间: 2026-04-02  
生效日期: 2026-04-02  
适用范围: RagflowAuth 管理后台数据安全模块

## 1. 目的

建立“备份执行、复制校验、恢复演练、审计取证”闭环，满足 R10 对严格审核口径下备份与恢复可审计性的要求。

## 2. 角色职责

- 系统管理员: 发起备份、查看备份状态、发起恢复演练。
- QA/合规: 复核恢复演练结果、抽检 hash 与比对结果、确认验收状态。
- 审计人员: 查阅 `backup_jobs`、`restore_drills` 和审计日志。

## 3. 审核口径

1. 启用复制目标后，复制成功是备份成功的必要条件；复制失败时任务状态必须为 `failed`，不得记为 `completed`。
2. 恢复演练必须由系统执行实际校验路径，不接受人工直接填报 `success/failed` 作为通过依据。
3. 恢复演练至少包含:
   - 备份包 hash 重算
   - 提交 hash 与备份任务已登记 hash 的一致性校验
   - `auth.db`、`backup_settings.json` 等必要文件存在性校验
   - 恢复出的 `auth.db` 与源文件 hash 比对
   - 系统输出 `package_validation_status`、`acceptance_status`、`result`
4. 备份包被篡改、损坏或 hash 不一致时，系统必须阻断验证通过，状态记为 `blocked` 或 `failed`。

## 4. 备份执行流程

1. 管理员在“数据安全”页面发起增量或全量备份。
2. 系统创建 `backup_jobs` 记录并执行备份。
3. 备份完成后系统计算并写入 `package_hash`。
4. 若启用了复制目标:
   - 系统执行复制并校验复制结果。
   - 复制成功: `replication_status=passed`，任务可进入 `completed`。
   - 复制失败: `replication_status=failed`，任务必须置为 `failed`，并记录 `replication_error`。
5. 系统记录任务输出目录、复制目标路径、校验状态与审计事件。

## 5. 恢复演练流程

1. 选择状态为已完成且已生成 `package_hash` 的备份任务。
2. 通过 `POST /api/admin/data-security/restore-drills` 提交以下最小字段:
   - `job_id`
   - `backup_path`
   - `backup_hash`
   - `restore_target`
   - `verification_notes`（可选，仅作操作备注）
3. 系统执行恢复演练校验:
   - 校验备份目录存在
   - 校验提交 hash 与备份任务登记 hash 一致
   - 重算备份包实际 hash
   - 校验 `auth.db` 与 `backup_settings.json` 存在
   - 将 `auth.db` 复制到 `data/restore_drills/<restore_target>/...`
   - 计算源 `auth.db` 与恢复后 `auth.db` hash 并比对
4. 系统落库 `restore_drills`，输出:
   - `actual_backup_hash`
   - `hash_match`
   - `restored_auth_db_path`
   - `restored_auth_db_hash`
   - `compare_match`
   - `package_validation_status`
   - `acceptance_status`
   - `verification_report_json`
5. 仅当系统校验通过时，回写 `backup_jobs.verification_status=passed` 及 `verified_*` 字段；被阻断或失败时不得回写通过状态。

## 6. 验收标准

- 备份任务:
  - 生成备份目录与 `package_hash`
  - 启用复制时复制必须成功
  - 审计日志可追溯发起人、时间、状态与失败原因
- 恢复演练:
  - `hash_match=true`
  - `compare_match=true`
  - `package_validation_status=passed`
  - `acceptance_status=passed`
  - 系统生成可归档的验证报告字段

## 7. 异常处置

- 复制失败: 立即判定备份任务失败，记录错误并重新执行备份；不得以“本地包已生成”为由判成功。
- 备份包 hash 不一致: 阻断恢复演练通过，调查是否篡改、损坏或取错备份包。
- 必要文件缺失: 演练失败，保留失败记录并重新生成合规备份包。
- 恢复后比对失败: 演练失败，保留 `verification_report_json` 作为调查依据。

## 8. 人工补充记录

- 对外部介质保留、轮换、离线归档或 WORM 能力证明，仍需由运维/QA 按受控表单归档。
- 当前系统输出的是验证结果和审计留痕；签字版恢复演练记录应引用系统生成的 drill 编号和验收状态。

## 9. 记录与证据

- 备份任务表: `backup_jobs`
- 恢复演练表: `restore_drills`
- 审计日志: `audit_events`
- 自动化测试: `backend.tests.test_backup_restore_audit_unit`, `fronted/e2e/tests/admin.data-security.restore-drill.spec.js`
