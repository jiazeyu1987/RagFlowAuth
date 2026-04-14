# P3：文控单一受控根迁移工作包

- Parent Task: `iso-13485-20260413T153016`
- Source PRD: `docs/tasks/docs-tasks-iso-13485-20260413t153016-prd-md-iso--20260414T122156/prd.md`
- Owner Type: backend / docs / compliance
- Parallelism: 与 `p0-p1-quality-permission-api.md`、`p2-quality-system-frontend.md`、`p4-batch-records.md` 基本独立

## 目标

把受控合规文档根从 `doc/compliance` 收敛到 `docs/compliance`，并同步运行时代码、校验器、种子数据和测试引用，保证仓库内只存在一个受控主根。

## Owned Paths

- `docs/compliance/*`
- `backend/services/document_control/compliance_root.py`
- `backend/services/compliance/*.py`
- `backend/services/compliance/review_package.py`
- `backend/database/schema/training_compliance.py`
- `scripts/validate_*_repo_compliance.py`
- `backend/tests/test_*compliance*`
- `backend/tests/test_training_compliance_api_unit.py`

## 不在本工作包内

- 不负责质量权限 capability
- 不负责前端质量系统接线
- 不负责批记录实现

## 风险提醒

- 这是唯一允许触碰文控主根的工作包，其他 LLM 不得并行修改 `doc/compliance` / `docs/compliance` 路径语义
- 严禁为了兼容而保留双根运行时逻辑
- 如果迁移需要补文档，必须明确哪些文件迁移、哪些文件缺失；不能用空文件占位

## 实施要求

### 1. 单根收敛

- 运行时代码、校验器、训练种子、review package、测试统一指向 `docs/compliance`
- 删除或迁出旧根运行时依赖

### 2. 无 fallback

- 不能做“优先读 `docs/compliance`，否则回退 `doc/compliance`”
- 不能做双写

### 3. 校验器同步

- `validate_fda03_repo_compliance.py`
- `validate_gbz02_repo_compliance.py`
- `validate_gbz04_repo_compliance.py`
- `validate_gbz05_repo_compliance.py`

以上门禁必须一起更新并通过。

### 4. 训练种子同步

- `backend/database/schema/training_compliance.py` 的文档锚点必须迁到新主根

## 验收标准

- 运行时代码、校验器、种子、测试全部引用 `docs/compliance/*`
- 仓库内不存在新的双根兼容逻辑
- 目标校验脚本全部通过
- review package 与 training compliance 相关测试通过

## 建议测试

```powershell
python scripts/validate_fda03_repo_compliance.py --json
python scripts/validate_gbz02_repo_compliance.py --json
python scripts/validate_gbz04_repo_compliance.py --json
python scripts/validate_gbz05_repo_compliance.py --json
rg -n "doc/compliance|docs/compliance|controlled_compliance_relpath" backend scripts
```

## 交付物

- 新主根迁移清单
- 旧根引用清零证据
- 校验脚本输出
- 相关单测输出
