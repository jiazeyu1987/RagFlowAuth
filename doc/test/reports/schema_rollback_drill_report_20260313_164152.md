# IT-MIGRATION-ROLLBACK-001 回滚演练报告

- 生成时间: 2026-03-13 16:41:52
- 演练数据库: `C:\Users\BJB110\AppData\Local\Temp\ragflowauth_schema_rollback_a868560ae2f042d79c74991343e10f48\auth.db`
- 目标表数量: 7

## 演练步骤

1. 执行 `ensure_schema` 建立当前目标表。
2. 执行回滚（按依赖顺序 DROP 目标表）。
3. 再次执行 `ensure_schema` 验证可自动恢复。

## 表状态快照

| Table | Before | AfterRollback | AfterRecover |
|---|---|---|---|
| unified_task_events | True | False | True |
| unified_task_jobs | True | False | True |
| unified_tasks | True | False | True |
| paper_plag_hits | True | False | True |
| paper_plag_reports | True | False | True |
| paper_versions | True | False | True |
| egress_decision_audits | True | False | True |

## 结论

- Verdict: **PASS**
- 通过条件: 回滚后目标表全部不存在，恢复后目标表全部存在。

