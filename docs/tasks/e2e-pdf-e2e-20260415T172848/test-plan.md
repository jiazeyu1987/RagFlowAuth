- Task ID: `e2e-pdf-e2e-20260415T172848`
- Created: `2026-04-15T17:28:48`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `查看当前的e2e测试是否符合分析桌面上的这个文件控制流程初稿.pdf的要求,运行e2e测试,查看结果是否符合预期,如果有问题,总结问题`

## Test Scope

验证桌面 PDF 中的文件控制流程与当前三条文控 Playwright e2e 的覆盖匹配程度，并执行这些真实浏览器用例确认是否按预期运行。其它非文控 e2e 套件不在本次测试范围内。

## Environment

- Workspace: `D:\ProjectPackage\RagflowAuth`
- OS: Windows
- PDF 源文件: `C:\Users\BJB110\Desktop\文件控制流程初稿.pdf`
- PDF 渲染副本: `tmp/pdfs/file-control-draft.pdf`
- Playwright 配置: `fronted/playwright.docs.config.js`
- 测试环境引导: `scripts/bootstrap_doc_test_env.py`
- 默认前端地址: `http://127.0.0.1:33002`
- 默认后端地址: `http://127.0.0.1:38002`

## Accounts and Fixtures

- 文控 e2e 依赖 `scripts/bootstrap_doc_test_env.py` 提供真实账号、知识库、组织部门与审批链。
- 测试直接读取桌面流程稿 PDF 作为上传源文件。
- 如果上述账号、库或 PDF 缺失，测试必须 fail-fast。

## Commands

- `python scripts/run_doc_e2e.py --repo-root . --list`
  - Expected success signal: 成功列出当前 doc/e2e 清单与映射。
- `cd fronted; npx playwright test --config playwright.docs.config.js e2e/tests/docs.document-control-pdf-flow.spec.js e2e/tests/docs.document-control-branch-coverage.spec.js e2e/tests/docs.document-control-edge-branches.spec.js --workers=1`
  - Expected success signal: 3 个 spec 全部通过，退出码为 `0`。
- `cd fronted; npx playwright show-report`
  - Expected success signal: 在需要人工追查时可打开最近报告；若主命令失败则至少生成 html 报告或失败产物。

## Test Cases

### T1: 静态覆盖映射检查

- Covers: P1-AC1, P1-AC2, P1-AC3
- Level: analysis
- Command: 阅读 PDF 渲染图与现有三条文控 spec
- Expected: 可产出明确的“流程节点 -> 现有 spec -> 覆盖状态”矩阵

### T2: 文控主流程运行

- Covers: P2-AC1, P2-AC2, P2-AC3
- Level: e2e
- Command: `cd fronted; npx playwright test --config playwright.docs.config.js e2e/tests/docs.document-control-pdf-flow.spec.js --workers=1`
- Expected: 主流程 spec 通过，覆盖审批、培训门禁、发新回旧、部门确认、作废、销毁

### T3: 文控分支流程运行

- Covers: P2-AC1, P2-AC2, P2-AC3
- Level: e2e
- Command: `cd fronted; npx playwright test --config playwright.docs.config.js e2e/tests/docs.document-control-branch-coverage.spec.js e2e/tests/docs.document-control-edge-branches.spec.js --workers=1`
- Expected: 分支 spec 通过，覆盖驳回重提、培训提问解决、加签、审批超时提醒

### T4: 最终符合性结论

- Covers: P3-AC1, P3-AC2, P3-AC3
- Level: review
- Command: 汇总 T1-T3 证据
- Expected: 能清晰区分覆盖缺口、文档映射偏差、以及真实运行失败

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | PDF vs specs | 流程节点映射与缺口识别 | analysis | P1-AC1, P1-AC2, P1-AC3 | `execution-log.md` |
| T2 | Document control | 主流程真实浏览器执行 | e2e | P2-AC1, P2-AC2, P2-AC3 | Playwright output, `test-report.md` |
| T3 | Document control branches | 分支流程真实浏览器执行 | e2e | P2-AC1, P2-AC2, P2-AC3 | Playwright output, `test-report.md` |
| T4 | Final review | 形成符合性结论与问题清单 | review | P3-AC1, P3-AC2, P3-AC3 | `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright, python, node
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 使用真实浏览器、真实前后端、真实种子环境运行文控流程，不接受 mock 或手工伪造成功。
- Escalation rule: 先基于真实运行结果形成初判，再参考执行日志做差异分析。

## Pass / Fail Criteria

- Pass when:
  - 三条文控 spec 可成功运行。
  - 现有用例覆盖了 PDF 的核心流程与关键分支，且未发现明显缺口。
  - 结论有真实证据支撑。
- Fail when:
  - 任一必需前提缺失。
  - 任一目标 spec 执行失败。
  - PDF 中的关键节点或关键分支无对应测试覆盖，或仅部分覆盖但无法满足流程要求。

## Regression Scope

- `doc/e2e/manifest.json` 对文控用例的注册关系
- `doc/e2e/role/04_文档上传审核发布.md` 对文控流程的文字说明
- `fronted/playwright.docs.config.js` 的真实环境引导能力

## Reporting Notes

结果写入 `test-report.md`。若某条用例失败，记录 spec 名称、失败摘要、退出码与证据路径；若覆盖有缺口，记录对应 PDF 节点和缺失点。
