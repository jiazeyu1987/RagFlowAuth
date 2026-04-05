# To Be Deleted

这些内容已经从仓库根目录移到 `tobedeleted/`，原因是它们不属于主系统前端、后端源码，也不属于本次自动化测试主链路本身。

目前已移动的内容分为几类：

- AI/助手本地配置：`.claude`、`.codex`
- 代理/探针运行产物：`.super`
- Python 本地缓存：`.pytest_cache`
- 构建或打包产物：`dist`、`backups`
- 根目录临时日志与运行输出：
  `backend-start.stderr.log`、`backend-start.stdout.log`、`backend_start.err.log`、`backend_start.out.log`、`run.log`、`tmp_backend_run.err.log`、`tmp_backend_run.out.log`、`tmp_backend_single.err.log`、`tmp_backend_single.out.log`、`tmp_fronted_run.err.log`、`tmp_fronted_run.out.log`
- 临时恢复文件：`todolist.recover.tmp`
- 外来业务文档：`ai_clinical_tool_brief.docx`
- 运维/部署目录：`docker`、`ragflow_compose`、`tool`
- 运维启动入口：`运维工具.bat`
- 助手说明文档：`CLAUDE.md`

这次刻意没有移动以下内容，因为它们仍然直接和主系统运行或自动化测试有关：

- `backend/`
- `fronted/`
- `scripts/`
- `doc/e2e/`
- `doc/test/`
- `data/`
- `VALIDATION.md`
- `ragflow_config.json`
- `start_ragflowauth.bat`
- `start_ragflowauth.ps1`
- `自动测试.bat`
- `全真链路自动测试.bat`
- `文档E2E自动测试.bat`

额外说明：

- 根目录里的 `nul` 在 Windows 下属于保留设备名。目录列表里能看到它，但常规方式无法像普通文件那样移动，所以这次仍然留在根目录。
- `AGENTS.md`、`.gitignore`、`.dockerignore`、`.env`、`.version` 这类仓库规则或环境说明文件暂时保留，没有一并移动。
