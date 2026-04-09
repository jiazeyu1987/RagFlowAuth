# PRD

- Task ID: `auth-db-20260409T092009`
- Created: `2026-04-09T09:20:09`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `为数据安全页面实现真实恢复功能，允许用备份包真实覆盖当前 auth.db，并提供前端危险确认入口与测试`

## Goal

为数据安全页面新增一个独立于“恢复演练”的“真实恢复”能力。管理员选择一份服务器本机备份后，系统在显式危险确认和变更原因都满足的前提下，将备份包中的 `auth.db` 真正恢复到当前运行中的 live `auth.db`，并对恢复前提、包完整性和恢复结果做严格校验与审计。

## Scope

- 后端数据安全模块新增真实恢复请求解析、服务实现、路由入口与审计。
- 真实恢复仅接受服务器本机备份目录中的备份包，不读取 Windows 副本。
- 真实恢复使用现有 SQLite 在线备份能力将备份包中的 `auth.db` 覆盖到当前 live `auth.db`。
- 前端数据安全页面新增独立的危险恢复按钮与确认交互。
- 补充后端单测与前端页面/Hook 测试。
- 将本次交付过程与验证记录写入 `docs/tasks/auth-db-20260409T092009/`。

## Non-Goals

- 不改造现有“恢复演练”行为为真实恢复。
- 不恢复除 `auth.db` 之外的其他运行数据或 Docker 卷。
- 不引入自动 fallback、兼容分支或静默降级逻辑。
- 不新增新的 Windows 备份或挂载依赖。
- 不实现跨机器远程恢复。

## Preconditions

- 仓库工作区 `D:\ProjectPackage\RagflowAuth` 可读写。
- 后端与前端测试命令在当前环境可执行。
- 现有备份包结构继续包含 `auth.db` 与 `backup_settings.json`。
- 现有训练合规控制 `restore_drill_execute` 在当前实现中可复用，避免额外扩面。
- 若缺少测试依赖、数据库 schema 或 task scripts，不继续执行并记录到 `task-state.json.blocking_prereqs`。

## Impacted Areas

- 后端路由入口：`backend/app/modules/data_security/router.py`
- 后端请求/审计辅助：`backend/app/modules/data_security/support.py`
- 后端恢复实现：`backend/services/data_security/restore_service.py`
- SQLite 复制原语：`backend/services/data_security/sqlite_backup.py`
- 后端数据安全测试：`backend/tests/test_backup_restore_audit_unit.py`
- 前端 API：`fronted/src/features/dataSecurity/api.js`
- 前端页面与 Hook：`fronted/src/pages/DataSecurity.js`
- 前端恢复区块：`fronted/src/features/dataSecurity/components/DataSecurityRestoreDrillsSection.js`
- 前端状态管理：`fronted/src/features/dataSecurity/useDataSecurityPage.js`
- 前端恢复表单逻辑：`fronted/src/features/dataSecurity/useRestoreDrillForm.js`
- 前端测试：`fronted/src/pages/DataSecurity.test.js`, `fronted/src/features/dataSecurity/useDataSecurityPage.test.js`

## Phase Plan

### P1: 后端真实恢复链路

- Objective: 新增一个 fail-fast 的真实恢复 API，请求必须匹配现有本机备份任务，并在校验成功后真实覆盖 live `auth.db`。
- Owned paths:
  - `backend/app/modules/data_security/router.py`
  - `backend/app/modules/data_security/support.py`
  - `backend/services/data_security/restore_service.py`
  - `backend/tests/test_backup_restore_audit_unit.py`
- Dependencies:
  - `DataSecurityStore`
  - `_resolve_auth_db_path`
  - `_compute_backup_package_hash`
  - `sqlite_online_backup`
  - 现有审计与 training gate
- Deliverables:
  - 真实恢复请求解析
  - 真实恢复服务方法
  - 新 API 路由
  - 后端单元/集成测试

### P2: 前端危险恢复入口

- Objective: 在数据安全页面增加“真实恢复当前数据”入口，并要求输入恢复原因与 `RESTORE` 确认字样。
- Owned paths:
  - `fronted/src/features/dataSecurity/api.js`
  - `fronted/src/features/dataSecurity/useDataSecurityPage.js`
  - `fronted/src/features/dataSecurity/useRestoreDrillForm.js`
  - `fronted/src/features/dataSecurity/components/DataSecurityRestoreDrillsSection.js`
  - `fronted/src/pages/DataSecurity.js`
  - `fronted/src/pages/DataSecurity.test.js`
  - `fronted/src/features/dataSecurity/useDataSecurityPage.test.js`
- Dependencies:
  - 新后端真实恢复 API
  - 当前 restore-eligible backup 选择逻辑
- Deliverables:
  - 前端 API 封装
  - 危险操作按钮和提示文案
  - 原因与确认输入流程
  - 前端测试

### P3: 交付验证与工件收口

- Objective: 跑通本次改动涉及的后端与前端测试，并将执行证据写入任务工件。
- Owned paths:
  - `docs/tasks/auth-db-20260409T092009/execution-log.md`
  - `docs/tasks/auth-db-20260409T092009/test-report.md`
  - `docs/tasks/auth-db-20260409T092009/task-state.json`
- Dependencies:
  - P1 与 P2 已完成
  - spec-driven-delivery 脚本
- Deliverables:
  - 通过的验证命令记录
  - phase review / test review 记录
  - 完整任务状态

## Phase Acceptance Criteria

### P1

- P1-AC1: 后端提供独立真实恢复入口，且请求必须包含 `job_id`、`backup_path`、`backup_hash`、`change_reason`、`confirmation_text`。
- P1-AC2: 真实恢复仅接受与已记录本机备份任务完全匹配的备份包；路径、哈希、包内容不匹配时必须 fail fast。
- P1-AC3: 真实恢复执行后必须用恢复源 `auth.db` 覆盖 live `auth.db`，并校验恢复后的 SQLite 逻辑内容签名与源库一致。
- P1-AC4: 当存在运行中的备份任务、确认字样错误或变更原因为空时，API 必须拒绝执行并返回明确错误。
- P1-AC5: 真实恢复会写入数据安全审计事件，记录 job、hash、compare 结果和 live `auth.db` 路径。
- Evidence expectation: 后端测试覆盖成功路径与关键拒绝路径，并在 `execution-log.md` 记录命令与结果。

### P2

- P2-AC1: 前端为真实恢复提供独立于“恢复演练（仅校验）”的按钮和危险提示文案。
- P2-AC2: 用户触发真实恢复时，前端必须先采集恢复原因，再要求输入 `RESTORE` 作为显式确认。
- P2-AC3: 取消任一确认步骤或当前备份不可恢复时，前端不得调用真实恢复 API。
- P2-AC4: 前端真实恢复调用必须传递所选 job 的 `output_dir`、`package_hash`、恢复原因和确认字样。
- Evidence expectation: 前端测试验证按钮、提示、prompt 流程与 API payload。

### P3

- P3-AC1: 后端目标测试命令全部通过。
- P3-AC2: 前端目标测试命令全部通过。
- P3-AC3: `execution-log.md`、`test-report.md` 和 `task-state.json` 记录的 acceptance ids 与验证证据一致。
- Evidence expectation: 命令输出、task scripts 校验结果和任务状态更新记录。

## Done Definition

- P1、P2、P3 全部完成且对应 acceptance ids 标记为 `completed`。
- 真实恢复与恢复演练在 API、UI 与文案层面明确分离。
- 真实恢复成功时会真实覆盖当前 live `auth.db`，失败时 fail fast，不留下伪成功状态。
- 后端与前端目标测试通过。
- `execution-log.md`、`test-report.md`、`task-state.json` 均已更新，`check_completion.py --apply` 可通过。

## Blocking Conditions

- live `auth.db` 路径无法解析或不可写。
- 备份包不存在、不是目录、缺少 `auth.db` 或缺少 `backup_settings.json`。
- 备份包哈希与记录任务不一致。
- 当前存在运行中的备份任务。
- 训练合规 gate、测试依赖或 task workflow 脚本缺失。
- 任一验证命令失败且未修复前，不进入完成态。
