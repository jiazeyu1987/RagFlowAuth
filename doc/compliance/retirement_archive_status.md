# 退役归档状态

版本: v1.0  
更新时间: 2026-04-03  
最后仓库复核日期: 2026-04-03  
下次仓库复核截止日期: 2026-07-03  
仓库内证据状态: complete  
仓库外证据状态: pending  
Residual gap 边界: 仓库内只覆盖退役记录生成、保留期内受控查询/预览/下载、管理员记录包导出和审计留痕；纸质批准、介质封存、长期可读性抽检与到期处置仍在线下体系。

## 1. 当前判断

- 已存在可执行的退役记录主链路：`retired_records.py -> retired.py -> audit/router.py`。
- 受控文档已补齐到当前实现路径，不再引用第二套退役归档实现。
- `python -m unittest backend.tests.test_retired_document_access_unit` 已于 2026-04-03 执行通过，仓库内证据状态更新为 `complete`。

## 2. 仓库内证据

| 类型 | 证据 |
|---|---|
| 实现 | `backend/services/compliance/retired_records.py` |
| 接口 | `backend/app/modules/knowledge/routes/retired.py`, `backend/app/modules/audit/router.py` |
| 测试 | `backend/tests/test_retired_document_access_unit.py` |
| 受控文档 | `doc/compliance/release_and_retirement_sop.md`, `doc/compliance/retirement_plan.md`, `doc/compliance/validation_report.md` |

## 3. 最近验证记录

- 命令：`python -m unittest backend.tests.test_retired_document_access_unit`
- 结果：`Ran 3 tests in 0.500s`
- 结论：`OK`

## 4. 仓库外残余项

- 纸质退役审批单和签字页
- 介质封存/移交记录
- 保留期年限批准依据
- 到期销毁或移交签字
