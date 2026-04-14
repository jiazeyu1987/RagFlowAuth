# 软件需求规格

版本: v1.0
更新时间: 2026-04-14

| SRS ID | 对应 URS | 软件需求 | 主要实现证据 |
|---|---|---|---|
| SRS-007 | URS-007 | 系统必须维护 GMP 基线、风险、版本链、配置变更原因与周期复核状态的一致性校验。 | `backend/services/compliance/r7_validator.py` |
| SRS-011 | URS-011 | 系统必须通过 `/api/audit/evidence-export` 导出带有 `manifest.json` 与 `checksums.json` 的取证包。 | `backend/services/audit/evidence_export.py` |
| SRS-012 | URS-012 | System must provide controlled-document listing and review-package export with manifest and checksum validation. | `backend/services/compliance/review_package.py` |
| SRS-013 | URS-013 | 维护影响判定必须覆盖 os、database、api、config、intended_use，并明确是否需要再确认。 | `backend/services/compliance/gbz01_maintenance.py` |
| SRS-014 | URS-014 | 紧急变更状态机必须覆盖先授权、后部署、复盘和 CAPA 字段校验。 | `backend/services/emergency_change.py` |
| SRS-015 | URS-015 | 退役记录服务必须生成受控归档包，并提供保留期内查询、预览、下载与审计导出接口。 | `backend/services/compliance/retired_records.py` |
| SRS-016 | URS-016 | 供应商评估与环境确认状态必须通过服务与路由暴露受控接口，并保留 IQ/OQ/PQ 状态。 | `backend/services/supplier_qualification.py` |
| SRS-017 | URS-017 | 培训合规服务必须校验课程版本、培训成效和操作员资格有效期。 | `backend/services/training_compliance.py` |
