- Task ID: `e2e-pdf-e2e-20260415T172848`
- Created: `2026-04-15T17:28:48`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `查看当前的e2e测试是否符合分析桌面上的这个文件控制流程初稿.pdf的要求,运行e2e测试,查看结果是否符合预期,如果有问题,总结问题`

## Goal

确认当前文控相关 e2e 测试是否覆盖桌面 `文件控制流程初稿.pdf` 中定义的文件控制主流程，并运行对应 Playwright 用例验证真实执行结果是否符合预期，若存在差距或失败则形成可复查的问题总结。

## Scope

- 桌面流程稿 `C:\Users\BJB110\Desktop\文件控制流程初稿.pdf`
- 文控相关 Playwright e2e 用例：
  - `fronted/e2e/tests/docs.document-control-pdf-flow.spec.js`
  - `fronted/e2e/tests/docs.document-control-branch-coverage.spec.js`
  - `fronted/e2e/tests/docs.document-control-edge-branches.spec.js`
- 文档型 e2e 需求映射：
  - `doc/e2e/manifest.json`
  - `doc/e2e/role/04_文档上传审核发布.md`
- 文控 e2e 运行入口：
  - `fronted/playwright.docs.config.js`
  - `scripts/run_doc_e2e.py`

## Non-Goals

- 不修改业务代码或测试代码来“修通”当前测试。
- 不扩展到与文控流程无关的其它 e2e 套件。
- 不用 mock、占位数据或降级路径替代真实运行。

## Preconditions

- 本机已安装 Python、Node.js、npm 依赖与 Playwright 浏览器。
- `fronted/node_modules` 可用，`npx playwright` 可执行。
- `scripts/bootstrap_doc_test_env.py` 可成功拉起真实文控测试环境。
- `fronted/playwright.docs.config.js` 所需端口 `33002`、`38002` 可用。
- 桌面 `文件控制流程初稿.pdf` 可读取。
- 当前工作树允许写入 `docs/tasks/...` 和 Playwright 产物目录。

如果任何项缺失，本任务应立即停止并在 `task-state.json.blocking_prereqs` 中记录。

## Impacted Areas

- `fronted/e2e/tests/docs.document-control-*.spec.js` 的覆盖边界与断言含义
- `doc/e2e/manifest.json` 与角色业务文档对文控流程的映射准确性
- `fronted/playwright.docs.config.js` 的真实浏览器执行链路
- `scripts/run_doc_e2e.py` 的文档 e2e 执行方式
- Playwright 输出目录、trace/video/screenshot 证据

## Phase Plan

### P1: 提炼流程要求并映射现有覆盖

- Objective: 从 PDF 与仓库现有文档中提炼文件控制流程节点，并映射到当前文控 e2e 用例。
- Owned paths:
  - `tmp/pdfs/file-control-draft.pdf`
  - `tmp/pdfs/rendered/file-control-draft-page-1.png`
  - `doc/e2e/manifest.json`
  - `doc/e2e/role/04_文档上传审核发布.md`
  - `fronted/e2e/tests/docs.document-control-pdf-flow.spec.js`
  - `fronted/e2e/tests/docs.document-control-branch-coverage.spec.js`
  - `fronted/e2e/tests/docs.document-control-edge-branches.spec.js`
- Dependencies:
  - 桌面 PDF 可读取
  - Playwright 测试文件存在
- Deliverables:
  - 覆盖矩阵
  - 初步差距判断

### P2: 运行文控 e2e 并收集执行证据

- Objective: 运行文控相关 Playwright e2e，用真实执行结果验证现有覆盖是否可达成。
- Owned paths:
  - `fronted/playwright.docs.config.js`
  - `scripts/run_doc_e2e.py`
  - `fronted/e2e/tests/docs.document-control-pdf-flow.spec.js`
  - `fronted/e2e/tests/docs.document-control-branch-coverage.spec.js`
  - `fronted/e2e/tests/docs.document-control-edge-branches.spec.js`
  - `test-results/`
  - `fronted/playwright-report/`
- Dependencies:
  - Playwright 运行环境完整
  - 文控测试环境可启动
- Deliverables:
  - 命令执行记录
  - 测试通过/失败结果
  - 失败证据路径

### P3: 汇总符合性与问题结论

- Objective: 基于覆盖映射与执行结果，判断“是否符合 PDF 要求”，并输出问题总结。
- Owned paths:
  - `docs/tasks/e2e-pdf-e2e-20260415T172848/execution-log.md`
  - `docs/tasks/e2e-pdf-e2e-20260415T172848/test-report.md`
- Dependencies:
  - P1 和 P2 完成
- Deliverables:
  - 最终结论
  - 问题列表
  - 剩余风险

## Phase Acceptance Criteria

### P1

- P1-AC1: 已从 PDF 中提炼出文件控制流程的关键节点与分支，包括新建/修订、会签、批准、标准化审核、培训、发新回旧、部门确认、作废、销毁。
- P1-AC2: 已将上述节点与现有文控 e2e 用例逐项映射，并明确标出已覆盖、部分覆盖、未覆盖。
- P1-AC3: 已明确指出仓库中的文档型 e2e 说明与实际文控用例之间是否存在不一致。
- Evidence expectation: `execution-log.md` 中记录 PDF 节点清单、对应 spec、差距说明。

### P2

- P2-AC1: 已运行文控相关 Playwright e2e 命令，且命令、退出码、执行时间被记录。
- P2-AC2: 若测试失败，已记录失败 spec、错误摘要及证据位置；若通过，已记录通过证据位置。
- P2-AC3: 未使用 mock、跳过必需校验或其它降级方式来伪造成功结果。
- Evidence expectation: `execution-log.md` 与 `test-report.md` 中记录命令、退出码、证据文件。

### P3

- P3-AC1: 已给出“当前 e2e 是否符合 PDF 要求”的结论，并区分覆盖差距与运行失败两类问题。
- P3-AC2: 已总结问题的具体表现、影响流程节点、对应 spec 或缺失覆盖。
- P3-AC3: 已标明仍需人工确认或后续补测的剩余风险。
- Evidence expectation: `test-report.md` 中形成最终 verdict 与问题清单。

## Done Definition

- 所有三个阶段均完成并留有证据。
- 每个 acceptance id 都有执行证据或明确的差距说明。
- 已给出基于真实运行结果的结论，而不是只做静态阅读。
- 若存在失败或缺口，已准确说明，不使用 fallback 隐藏问题。

## Blocking Conditions

- 桌面 PDF 无法读取或无法渲染，导致无法确认流程要求。
- Playwright 或前后端测试环境无法启动。
- 文控相关测试依赖的真实种子数据或账号缺失。
- 关键证据目录无法写入，导致不能保存执行结果。
