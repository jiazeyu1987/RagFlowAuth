# Test Plan

- Task ID: `ragflowauth-docs-20260407T224455`
- Created: `2026-04-07T22:44:55`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `读取 RagflowAuth 前后端代码并按指定 docs 结构编写项目文档。`

## Test Scope

验证本次文档交付是否：

- 落地了用户要求的根目录文档和 `docs/` 结构。
- 以真实代码、配置和 SQLite schema 为依据，而不是模板化猜测。
- 对权限模型、系统架构、外部依赖和数据模型的描述具有可追溯锚点。
- 如实标明当前仓库对 design system、Nixpacks、uv 等参考技术的采用状态。

本次测试不包含：

- 启动前后端服务进行业务回归。
- 执行 Playwright UI 测试。
- 验证 RAGFlow、OnlyOffice、SMTP、Docker 运行时的真实外部可用性。

## Environment

- Shell: `powershell`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- Required tools:
  - `python`
  - `powershell`
- Required readable paths:
  - `backend/`
  - `fronted/`
  - `backend/database/schema/`
  - `data/auth.db`
  - `docs/`

## Accounts and Fixtures

- No login account is required.
- No seeded application user is required.
- `data/auth.db` is required for the schema cross-check case.
- If `data/auth.db` or `backend/database/schema/` is unreadable, testing must fail fast and record the missing prerequisite.

## Commands

1. Required path existence and non-empty content check

```powershell
@'
from pathlib import Path

required_files = [
    "ARCHITECTURE.md",
    "DESIGN.md",
    "FRONTEND.md",
    "PLANS.md",
    "PRODUCT_SENSE.md",
    "QUALITY_SCORE.md",
    "RELIABILITY.md",
    "SECURITY.md",
    "docs/design-docs/index.md",
    "docs/design-docs/core-beliefs.md",
    "docs/exec-plans/active/README.md",
    "docs/exec-plans/completed/README.md",
    "docs/exec-plans/tech-debt-tracker.md",
    "docs/generated/db-schema.md",
    "docs/product-specs/index.md",
    "docs/product-specs/new-user-onboarding.md",
    "docs/references/design-system-reference-llms.txt",
    "docs/references/nixpacks-llms.txt",
    "docs/references/uv-llms.txt",
]

required_dirs = [
    "docs/design-docs",
    "docs/exec-plans/active",
    "docs/exec-plans/completed",
    "docs/generated",
    "docs/product-specs",
    "docs/references",
]

for rel in required_dirs:
    path = Path(rel)
    if not path.is_dir():
        raise SystemExit(f"missing_dir:{rel}")

for rel in required_files:
    path = Path(rel)
    if not path.is_file():
        raise SystemExit(f"missing_file:{rel}")
    if not path.read_text(encoding="utf-8").strip():
        raise SystemExit(f"empty_file:{rel}")

print("docs_structure_ok")
'@ | python -X utf8 -
```

Expected success signal: `docs_structure_ok`

2. Anchor and broken-link scan

```powershell
@'
from pathlib import Path
import re

targets = [
    Path("ARCHITECTURE.md"),
    Path("DESIGN.md"),
    Path("FRONTEND.md"),
    Path("PLANS.md"),
    Path("PRODUCT_SENSE.md"),
    Path("QUALITY_SCORE.md"),
    Path("RELIABILITY.md"),
    Path("SECURITY.md"),
]
targets.extend(sorted(Path("docs").rglob("*.md")))
targets.extend(sorted(Path("docs/references").glob("*.txt")))

required_markers = {
    Path("ARCHITECTURE.md"): [
        "backend/app/main.py",
        "backend/app/dependencies.py",
        "fronted/src/App.js",
    ],
    Path("FRONTEND.md"): [
        "fronted/src/components/Layout.js",
        "fronted/src/hooks/useAuth.js",
        "fronted/src/shared/http/httpClient.js",
    ],
    Path("SECURITY.md"): [
        "JWT",
        "ONLYOFFICE",
        "tenant",
    ],
    Path("RELIABILITY.md"): [
        "backup",
        "scheduler",
        "VALIDATION.md",
    ],
}

for path in targets:
    text = path.read_text(encoding="utf-8")
    for match in re.findall(r"\]\(([^)]+)\)", text):
        if match.startswith("http://") or match.startswith("https://") or match.startswith("#"):
            continue
        target = (path.parent / match).resolve()
        if not target.exists():
            raise SystemExit(f"broken_link:{path}:{match}")

for path, markers in required_markers.items():
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            raise SystemExit(f"missing_marker:{path}:{marker}")

print("docs_anchor_and_links_ok")
'@ | python -X utf8 -
```

Expected success signal: `docs_anchor_and_links_ok`

3. Schema document coverage check against schema source files

```powershell
@'
from pathlib import Path
import re

schema_root = Path("backend/database/schema")
if not schema_root.is_dir():
    raise SystemExit("missing_schema_root")

schema_text = "\n".join(
    path.read_text(encoding="utf-8", errors="ignore")
    for path in sorted(schema_root.glob("*.py"))
)
doc_text = Path("docs/generated/db-schema.md").read_text(encoding="utf-8")

expected_tables = [
    "users",
    "password_history",
    "permission_groups",
    "user_permission_groups",
    "kb_directory_nodes",
    "kb_documents",
    "data_security_settings",
    "backup_jobs",
    "operation_approval_requests",
    "notification_jobs",
]

for table in expected_tables:
    if table not in schema_text:
        raise SystemExit(f"missing_table_in_schema_sources:{table}")
    if table not in doc_text:
        raise SystemExit(f"missing_table_in_doc:{table}")

print("db_schema_doc_ok")
'@ | python -X utf8 -
```

Expected success signal: `db_schema_doc_ok`

4. Schema reality spot-check against `data/auth.db`

```powershell
@'
import sqlite3
from pathlib import Path

db_path = Path("data/auth.db")
if not db_path.is_file():
    raise SystemExit("missing_db:data/auth.db")

conn = sqlite3.connect(db_path)
try:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
finally:
    conn.close()

names = {row[0] for row in rows}
required = {
    "users",
    "permission_groups",
    "user_permission_groups",
    "kb_directory_nodes",
    "kb_documents",
    "operation_approval_requests",
    "notification_jobs",
}

missing = sorted(required - names)
if missing:
    raise SystemExit("missing_tables_in_db:" + ",".join(missing))

print("db_runtime_tables_ok")
'@ | python -X utf8 -
```

Expected success signal: `db_runtime_tables_ok`

5. Manual content review

- Read the generated documentation set.
- Confirm that there are no leftover template fragments or unresolved drafting notes.
- Confirm that claimed integrations and tool choices match the repository.
- Confirm that “not adopted” statements are backed by observable repo evidence.

Expected success signal: reviewer records a pass/fail judgment in `test-report.md`.

## Test Cases

### T1: Requested documentation structure exists

- Covers: P1-AC1, P1-AC2, P1-AC3
- Level: automated
- Command: run command 1
- Expected: all requested files and directories exist and all files are non-empty

### T2: Core content is clean and navigable

- Covers: P2-AC1, P2-AC2, P2-AC3
- Level: automated
- Command: run command 2
- Expected: required architecture and operations anchors are present and no broken relative links

### T3: Schema documentation covers expected source-defined tables

- Covers: P3-AC2
- Level: automated
- Command: run command 3
- Expected: core business tables appear in both schema source files and `docs/generated/db-schema.md`

### T4: Schema documentation matches the current SQLite database at spot-check level

- Covers: P3-AC2, P4-AC2
- Level: automated
- Command: run command 4
- Expected: key tables exist in `data/auth.db`

### T5: Documentation claims match repository reality

- Covers: P3-AC1, P3-AC3, P4-AC1, P4-AC3
- Level: manual
- Command: read the documents and compare against repository anchors
- Expected: no invented adoption states, no unsupported claims, and explicit marking of unverified external dependencies

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | docs structure | requested files and directories exist | automated | P1-AC1, P1-AC2, P1-AC3 | `test-report.md` |
| T2 | documentation hygiene | placeholder-free and navigable markdown | automated | P2-AC1, P2-AC2, P2-AC3 | `test-report.md` |
| T3 | generated schema docs | source-defined table coverage | automated | P3-AC2 | `test-report.md` |
| T4 | runtime schema spot-check | database tables exist in `data/auth.db` | automated | P3-AC2, P4-AC2 | `test-report.md` |
| T5 | factual correctness | claims match code/config reality | manual | P3-AC1, P3-AC3, P4-AC1, P4-AC3 | `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: `python`, `powershell`
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Validate against the real repository checkout and current `data/auth.db`.
- Escalation rule: Do not inspect `execution-log.md` or `task-state.json` until an initial verdict is written.

## Pass / Fail Criteria

- Pass when:
  - All automated checks succeed.
  - Manual review finds no invented or contradictory claims.
  - `test-report.md` records a final `passed` outcome with verified acceptance ids.
- Fail when:
  - Any required file is missing or empty.
  - Schema documentation omits required core tables.
  - Documentation contains template leftovers or broken links.
  - A claimed adoption state or architectural statement cannot be supported by repository evidence.

## Regression Scope

- Existing `VALIDATION.md` content and its command references must remain untouched.
- Existing root files outside the requested documentation set must remain behaviorally unchanged.
- The dirty working tree must not be reverted or normalized by this task.

## Reporting Notes

Write all validation outcomes to `test-report.md`.
