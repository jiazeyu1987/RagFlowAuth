# GMP 监管基线

版本: v1.0
更新时间: 2026-04-14
最新已发布 GMP 基线核对日期: 2026-04-14
下次基线复核截止日期: 2026-10-14

## 1. 用途

本文件用于记录 R7 在仓库内采用的 GMP 监管依据基线，以及“当前有效要求 / 最新已发布要求 / 需复核动作”的差异状态。本文档只记录仓库内可追溯的基线结论，不替代线下签字版法规适用性评审。

## 2. 官方基线

| 基线 ID | 类型 | 官方依据 | 发布日期 | 生效日期 | 当前状态 | 仓库结论 |
|---|---|---|---|---|---|---|
| GMP-CN-001 | 最新已发布 | 《医疗器械生产质量管理规范》（国家药监局令第64号） | 2025-11-04 | 2026-11-01 | latest_published_pending_effective | latest_published_pending_effective |

## 3. 仓库内映射结论

1. 截至 2026-04-14，仓库已补齐受控文档基线、配置变更原因、风险/测试追踪矩阵和 R7 仓库内一致性门禁脚本。
2. 由于国家药监局令第64号生效日期为 2026-11-01，当前结论保持为 `latest_published_pending_effective`。
3. 仓库内门禁只验证文档、映射、测试和周期复核状态的一致性，不自动伪造线下签字或真实环境执行证据。

## 4. 与仓库实现的对应关系

- 需求映射: `docs/compliance/urs.md`, `docs/compliance/srs.md`
- 风险与证据: `docs/compliance/risk_assessment.md`, `docs/compliance/traceability_matrix.md`
- 周期复核状态: `docs/compliance/r7_periodic_review_status.md`
- 校验脚本: `scripts/validate_r7_repo_compliance.py`
- 校验实现: `backend/services/compliance/r7_validator.py`
