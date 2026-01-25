# Playwright 自动化测试索引

本目录把“已实现用例”和“待补齐用例”拆开，方便持续补覆盖、避免遗漏/重复。

目录结构：
- `doc/test/implemented/`：已落地的自动化测试（按模块拆分，列出对应 spec）
- `doc/test/pending/`：尚未覆盖或覆盖不完整的点（按模块拆分，写清要补的场景）

建议从这里开始读：
- 已实现索引：`doc/test/implemented/README.md`
- 待补齐索引：`doc/test/pending/README.md`
- 后端 API 覆盖面（已实现/待补齐）：`doc/test/implemented/api_surface.md`、`doc/test/pending/api_surface.md`
- 给其他 LLM 的编写指南：`doc/test/llm/README.md`

运行入口（前端 Playwright 用例都在 `fronted/e2e/`）：
- 回归（默认跳过 `@integration`）：`cd fronted; npm run e2e`
- 冒烟：`cd fronted; npm run e2e:smoke`
- 集成（真实后端/外部依赖）：`cd fronted; npm run e2e:integration`
- 跑单个 spec：`cd fronted; npm run e2e -- e2e/tests/<name>.spec.js`
- 查看报告：`cd fronted; npm run e2e:report`

维护建议：
- 新增/修改 spec 后：同步更新 `doc/test/implemented/*.md` 与 `doc/test/pending/*.md`
- 用例命名建议以模块前缀区分（例如 `documents.*`, `upload.*`, `admin.users.*`）
