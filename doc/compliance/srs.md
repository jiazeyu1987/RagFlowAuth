# 软件需求规格

版本: v1.0
更新时间: 2026-04-13

| SRS ID | 对应 URS | 软件需求 | 主要实现证据 |
|---|---|---|---|
| SRS-014 | URS-014 | 紧急变更状态机必须覆盖授权、部署、复盘和 CAPA 字段校验。 | `backend/services/emergency_change.py` |
| SRS-016 | URS-016 | 供应商评估与环境确认状态必须通过服务与路由暴露受控接口。 | `backend/services/supplier_qualification.py` |
| SRS-017 | URS-017 | 培训合规服务必须校验课程版本、培训成效和上岗资格有效期。 | `backend/services/training_compliance.py` |
