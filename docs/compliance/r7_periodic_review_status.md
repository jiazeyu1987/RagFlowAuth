# R7 周期复核状态

版本: v1.0
更新时间: 2026-04-14
最后仓库复核日期: 2026-04-14
下次仓库复核截止日期: 2026-10-14
仓库内证据状态: complete
仓库外证据状态: pending_offline_archive
当前结论: repository_ready_with_external_residuals

## 1. 仓库内已完成项

- GMP 基线已受控归档，并记录最新已发布版本与复核截止日期。
- `URS/SRS/风险评估/追踪矩阵/验证计划/验证报告` 已建立 R7 一致性映射。
- 文档版本链与配置变更原因已有代码与自动化测试覆盖。
- R7 仓库内门禁脚本可阻断缺失文档、映射缺口或周期复核过期。

## 2. 仓库外残余项

- 线下签字版 IQ/OQ/PQ 或等效验证执行记录
- 培训完成记录与周期复核签字记录
- 本环境法规适用性差异分析和管理层批准记录

## 3. 复核门禁

- 门禁命令: `python scripts/validate_r7_repo_compliance.py`
- 通过条件:
  - 无 blocking issue
  - `仓库内证据状态 = complete`
  - `下次仓库复核截止日期` 未过期
- 非阻断提示:
  - `仓库外证据状态 != archived` 时输出 residual gap，但不伪装为已归档
