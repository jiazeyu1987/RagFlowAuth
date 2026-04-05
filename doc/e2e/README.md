# Doc E2E 全真链路说明

`doc/e2e` 用于维护业务文档与真实 Playwright 用例之间的映射关系。当前目录已经完成全量 30 份业务文档的全真链路接入，运行时严格遵循“不 mock、不 fallback、前置不足即 fail-fast”。

## 当前环境

- 前端入口：`fronted/playwright.docs.config.js`
- 后端入口：`python -m backend`
- 测试数据库：`data/e2e/doc_auth.db`
- 真实 bootstrap：`scripts/bootstrap_doc_test_env.py`
- 一键运行入口：`scripts/run_doc_e2e.py`
- 一致性校验入口：`scripts/check_doc_e2e_docs.py`
- 映射清单：`doc/e2e/manifest.json`

默认地址：

- 前端：`http://127.0.0.1:33002`
- 后端：`http://127.0.0.1:38002`

## 一键运行

列出当前文档与 spec 映射：

```powershell
python scripts\run_doc_e2e.py --repo-root . --list
```

执行全量文档套件：

```powershell
python scripts\run_doc_e2e.py --repo-root .
```

校验文档、manifest 与 spec 是否保持一致：

```powershell
python scripts\check_doc_e2e_docs.py --repo-root .
```

报告输出位置：

- `doc/test/reports/doc_e2e_report_latest.md`
- `doc/test/reports/doc_e2e_report_YYYYMMDD_HHMMSS.md`

## 覆盖现状

- 已接入全真链路自动化文档：**30**
- 待补齐文档：**0**
- manifest 对应唯一 spec：**24**
- `unit` 已接入：**19**
- `role` 已接入：**11**

本轮补齐的 13 份文档：

- `doc/e2e/unit/用户管理.md`
- `doc/e2e/unit/权限分组.md`
- `doc/e2e/unit/组织管理.md`
- `doc/e2e/unit/全库搜索.md`
- `doc/e2e/unit/智能对话.md`
- `doc/e2e/unit/日志审计.md`
- `doc/e2e/unit/数据安全.md`
- `doc/e2e/unit/修改密码.md`
- `doc/e2e/unit/实用工具.md`
- `doc/e2e/role/01_账号与权限开通.md`
- `doc/e2e/role/02_权限组与菜单生效.md`
- `doc/e2e/role/10_密码重置与账号状态.md`
- `doc/e2e/role/11_越权访问与数据隔离.md`

## 真实环境约束

- RAGFlow 是强依赖，bootstrap 默认会为每次执行创建一组新的专用 `RagflowAuth E2E Dataset [run-tag]` 与 `RagflowAuth E2E Chat [run-tag]`，并解绑历史 E2E dataset 的本地目录映射，避免旧索引或旧权限范围串入当前全真链路。
- 数据安全场景不伪造备份成功；若宿主机缺少 `ragflowauth-backend:latest` 等真实前置，用例会按真实 400 阻塞结果校验。
- SMTP、钉钉仍属于外部真实通道，若后续要补成“成功路径全真链路”，必须提供可用测试凭据。
