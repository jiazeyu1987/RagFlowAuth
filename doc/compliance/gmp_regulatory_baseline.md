# GMP 监管基线

版本: v1.0  
更新时间: 2026-04-02  
最新已发布 GMP 基线核对日期: 2026-04-02  
下次基线复核截止日期: 2026-10-02

## 1. 用途

本文件用于记录 R7 在仓库内采用的 GMP 监管依据基线，以及“当前有效要求 / 最新已发布要求 / 需复核动作”的差异状态。  
本文件只记录仓库内可追溯的基线结论，不替代线下签字版法规适用性评审。

## 2. 官方基线

| 基线 ID | 类型 | 官方依据 | 发布日期 | 生效日期 | 当前状态 | 仓库结论 |
|---|---|---|---|---|---|---|
| GMP-CN-001 | 最新已发布 | 《医疗器械生产质量管理规范》（国家药监局令第64号） | 2025-11-04 | 2026-11-01 | latest_published_pending_effective | latest_published_pending_effective |

## 3. 仓库内映射结论

1. 截至 2026-04-02，仓库已补齐以下系统化控制能力:
   - 受控文档基线与版本链
   - 配置变更原因与独立日志
   - 需求/设计/风险/测试/文档追踪矩阵
   - R7 仓库内一致性门禁脚本
   - 周期复核状态记录
2. 由于国家药监局令第64号生效日期为 2026-11-01，仓库当前结论为 `latest_published_pending_effective`:
   - 已将最新已发布版本纳入受控基线
   - 在生效日前仍需完成一次差异复核并归档线下评审记录
3. 仓库内门禁只验证“文档、映射、测试、周期复核状态”的一致性，不自动伪造线下签字或真实环境执行证据。

## 4. 与仓库实现的对应关系

- 需求映射: `doc/compliance/urs.md`, `doc/compliance/srs.md`
- 风险与证据: `doc/compliance/risk_assessment.md`, `doc/compliance/traceability_matrix.md`
- 周期复核状态: `doc/compliance/r7_periodic_review_status.md`
- 校验脚本: `scripts/validate_r7_repo_compliance.py`
- 校验实现: `backend/services/compliance/r7_validator.py`
