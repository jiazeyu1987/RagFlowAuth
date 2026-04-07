# 可靠性说明

## 1. 运行时可靠性基线

当前仓库的可靠性不是靠复杂分布式机制实现，而是靠若干明确的应用级约束：

- `backend/app/main.py` 在启动时统一装配依赖
- `RequestIdMiddleware` 为请求链路提供 request id
- 异常处理器集中注册，避免错误表现碎片化
- `backend/services/data_security_scheduler_v2.py` 在应用生命周期中托管备份 `scheduler`
- `fronted/nginx.conf` 用同源反代减少前后端网络偏差

## 2. 数据与路径约束

### 2.1 主库路径

`backend/database/paths.py` 明确拒绝旧路径 `backend/data/auth.db`，要求统一使用 `data/auth.db`。这是一个很好的 fail-fast 设计，因为它避免新旧路径悄悄混用。

### 2.2 多租户路径

`backend/database/tenant_paths.py` 基于主库推导 tenant 库目录：

- 主库：`data/auth.db`
- tenant 库：`data/tenants/company_<id>/auth.db`

如果 `company_id` 非法，会立即报错，而不是退回默认库。

## 3. backup 与 scheduler

`backup` 是当前可靠性设计里最重要的业务子系统之一：

- 配置表：`data_security_settings`
- 作业表：`backup_jobs`
- 锁表：`backup_locks`
- 恢复演练：`restore_drills`

`scheduler` 在启动阶段根据 `BACKUP_SCHEDULER_ENABLED` 决定是否工作，并从数据表中的 cron 字段推导下次触发窗口。当前实现会：

- 尽量避免同一窗口重复触发
- 对陈旧运行中作业做超时失败标记
- 在增量和全量同时到期时优先全量

## 4. 诊断入口

当你怀疑系统状态不一致时，优先看这些入口：

- `/health`
- `/api/diagnostics/build`
- `/api/diagnostics/permissions`
- `/api/diagnostics/ragflow`
- `/api/diagnostics/routes`
- `/api/admin/data-security/*`

这些入口比直接猜日志更适合作为第一层排障入口。

## 5. 当前外部依赖

| 依赖 | 代码锚点 | 缺失时预期 |
| --- | --- | --- |
| RAGFlow | `ragflow_config.json`、`backend/services/ragflow*` | 相关知识库/聊天能力失败，不能伪装成功 |
| OnlyOffice | `.env`、`backend/app/core/config.py`、`/api/onlyoffice/*` | 文档编辑/受控预览能力受限，应显式报错 |
| SMTP / DingTalk | `backend/app/core/config.py`、通知模块 | 通知发送失败但应记录 job 与错误 |
| SMB / NAS | `smbprotocol`、`/api/nas/*` | NAS 浏览/导入失败，应显式返回错误 |
| Docker CLI | `backend/Dockerfile`、数据安全链路 | 备份/发布相关能力依赖环境准备，缺失时必须 fail fast |

## 6. 当前已知漂移

`VALIDATION.md` 仍列出了与 `doc/e2e` 相关的检查命令，但当前工作区没有 `doc/` 目录。这意味着：

- 这些命令在当前工作区大概率会因缺少路径而失败
- 失败应该被当作“验证入口漂移”，而不是被 fallback 掩盖
- 修复验证入口本身应成为后续执行计划项

## 7. 维护建议

- 先校验路径与环境，再校验业务现象。
- 遇到跨租户问题，优先确认 `tenant` 解析是否命中了正确数据库。
- 遇到备份问题，优先看 `backup_jobs`、`backup_locks` 和 admin data-security 路由，而不是先手改脚本。
- 遇到“本地能跑、服务器不行”的情况，优先对照 `backend/Dockerfile`、`fronted/Dockerfile` 和 Nginx 配置。

## 8. 当前可靠性结论

- 应用内的 fail-fast 倾向是明确存在的，这是优点。
- 可靠性最大的不确定性来自外部依赖和验证入口漂移，而不是应用主干结构本身。
