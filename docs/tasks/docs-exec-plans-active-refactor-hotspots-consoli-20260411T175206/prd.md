# PRD

- Task ID: `docs-exec-plans-active-refactor-hotspots-consoli-20260411T175206`
- Created: `2026-04-11T17:52:06`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `按照 docs/exec-plans/active/refactor-hotspots-consolidation-2026-04.md 的方案进行重构。`

## Goal

在不引入 fallback 的前提下，按四类热点问题完成最小且可验证的重构落地：
1) 明确验证入口与文档树的权威边界并修正文档；
2) 安全基线补齐（生产环境 JWT 默认密钥 fail-fast + token 存储策略与迁移约束）；
3) 责任边界最小拆分（选定一个热点域做具体拆分落地）；
4) 降低前后端权限规则双写成本（后端单一事实源 + 前端统一适配层）。

## Scope

- 文档与验证入口边界：`AGENTS.md`, `VALIDATION.md`, `doc/e2e/*`, `docs/*`（必要时补充到 `docs/exec-plans/`）
- 安全基线：`backend/app/core/config.py`, `backend/app/main.py`（或启动入口）, `fronted/src/shared/auth/tokenStore.js`, `SECURITY.md` 或 `docs/design-docs/`
- 责任边界拆分（最小落地，单一热点域）：`backend/services/operation_approval/*`（含路由/服务/通知交互）
- 前后端权限规则统一：`backend/app/core/permission_resolver.py`, `fronted/src/hooks/useAuth.js`, `fronted/src/components/PermissionGuard.js`, `fronted/src/shared/auth/capabilities.js`
- 相关测试：`backend/tests/*`（权限/认证/审批相关）与前端测试命令

## Non-Goals

- 不做全量重写或系统级大改。
- 不迁移或重命名 `doc/` 与 `docs/` 目录结构（除非明确执行单轨迁移方案）。
- 不引入任何隐式 fallback、兼容分支或静默降级。
- 不扩展与本次四类问题无关的功能或 UI 改版。

## Preconditions

- 可用的 Python 运行环境与依赖（`pip install -r backend/requirements.txt`）。
- 可用的 Node 运行环境与依赖（`npm --prefix fronted install`）。
- 可访问 `data/auth.db`（用于后端测试/运行态 spot-check）。
- 如需运行文档 E2E 验证，需满足 `scripts/run_doc_e2e.py` 的真实依赖条件（否则必须 fail-fast 报告缺失前提）。

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- 启动与配置：`backend/app/main.py`, `backend/app/core/config.py`, `.env`
- 权限与认证：`backend/app/core/permission_resolver.py`, `backend/app/core/permission_scopes.py`
- 前端权限消费：`fronted/src/hooks/useAuth.js`, `fronted/src/components/PermissionGuard.js`, `fronted/src/shared/auth/capabilities.js`
- 责任边界热点：`backend/services/operation_approval/*`, `backend/services/notification/*`
- 文档与验证入口：`AGENTS.md`, `VALIDATION.md`, `doc/e2e/*`, `docs/exec-plans/*`
- 测试与回归：`backend/tests/*`, `fronted` 测试脚本, `scripts/run_doc_e2e.py`

## Phase Plan

### P1: 验证入口与文档树权威边界落地

- Objective: 明确 `docs/` 与 `doc/e2e` 的职责边界，修正文档入口与验证命令描述，消除“文档写 A、脚本跑 B”的冲突。
- Owned paths:
  - `AGENTS.md`
  - `VALIDATION.md`
  - `docs/exec-plans/active/refactor-hotspots-consolidation-2026-04.md`（必要时补充说明）
  - `doc/e2e/*`（仅在需要同步说明或 manifest 变更时）
- Dependencies: `scripts/run_doc_e2e.py`, `scripts/check_doc_e2e_docs.py`
- Deliverables:
  - 文档明确双轨边界或单轨迁移的最终决策与执行说明。
  - 验证入口描述与脚本实际路径一致。

### P2: 安全基线补齐（JWT default secret fail-fast + token 策略）

- Objective: 生产环境禁止默认 JWT secret，启动即 fail-fast；前端 token 存储策略形成明确文档与迁移约束。
- Owned paths:
  - `backend/app/core/config.py`
  - `backend/app/main.py` 或启动入口
  - `fronted/src/shared/auth/tokenStore.js`
  - `SECURITY.md` 或 `docs/design-docs/*`
- Dependencies: `.env` 配置, 现有启动流程
- Deliverables:
  - 生产环境未显式配置 JWT secret 时明确报错并拒绝启动。
  - Token 存储策略文档化（短期约束 + 中期替代方向 + 回滚策略）。

### P3: 责任边界最小拆分（Operation Approval）

- Objective: 对 `operation_approval` 域做最小且可验证的职责拆分，入口层只负责编排，存储/通知/动作逻辑下沉到子服务。
- Owned paths:
  - `backend/services/operation_approval/*`
  - `backend/services/notification/*`（仅涉及必要交互）
  - `backend/app/modules/*/router.py`（如入口依赖需要调整）
- Dependencies: 现有审批流程与通知通道
- Deliverables:
  - 至少一个“高风险职责”从主服务剥离（如：审批动作执行或通知派发）。
  - 新职责具备对应 focused tests 或已有测试覆盖更新。

### P4: 前后端权限规则双写降低

- Objective: 后端为单一事实源，前端统一适配层收敛语义分支，避免多处重复实现。
- Owned paths:
  - `backend/app/core/permission_resolver.py`
  - `fronted/src/hooks/useAuth.js`
  - `fronted/src/components/PermissionGuard.js`
  - `fronted/src/shared/auth/capabilities.js`
- Dependencies: 现有权限快照与前端消费路径
- Deliverables:
  - 权限语义集中到后端快照结构；前端 `can()`/`isAuthorized()` 仅做薄适配。
  - 至少一组权限新增/变更回归用例（前后端联动）明确可验证。

## Phase Acceptance Criteria

### P1

- P1-AC1: `AGENTS.md` 与 `VALIDATION.md` 对文档树与验证入口的说明一致且可执行。
- P1-AC2: `doc/e2e` 与 `docs/` 的职责边界有明确、可检索的权威描述。
- Evidence expectation: 文档更新提交 + 验证命令可执行（或明确 fail-fast 的缺失前提）。

### P2

- P2-AC1: 生产环境检测到默认 JWT secret 时，服务启动直接失败并给出可定位错误信息。
- P2-AC2: Token 存储策略形成可执行的约束与迁移说明（含触发条件、风险与回滚点）。
- Evidence expectation: 后端单元/集成测试覆盖 + 文档更新。

### P3

- P3-AC1: Operation Approval 主服务减少至少一个高风险职责，入口层仅负责编排。
- P3-AC2: 拆分后的新边界有 focused tests 或现有测试更新覆盖。
- Evidence expectation: 代码变更 + 对应测试通过。

### P4

- P4-AC1: 新增/变更权限点的主要改动集中在后端 resolver 与前端单一适配层。
- P4-AC2: 前端不再分散实现同一权限语义（重复逻辑被收敛）。
- Evidence expectation: 权限回归用例说明 + 后端/前端测试通过。

## Done Definition

- 所有阶段状态为 completed。
- 每个 acceptance id 都有 `execution-log.md` 或 `test-report.md` 中的证据引用。
- 关键测试命令执行并通过（或缺失前提已 fail-fast 记录）。
- 未引入任何未要求的 fallback 或静默降级逻辑。

## Blocking Conditions

- 无法安装或运行 Python/Node 依赖。
- 缺少 `data/auth.db` 或文档 E2E 所需真实依赖。
- 未知或不可控的外部服务依赖导致无法验证（必须 fail-fast 报告）。
- 任何引入 fallback 或静默降级的要求未被用户显式批准。
