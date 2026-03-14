#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

# Ensure repository root is importable when executing the script directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from authx import TokenPayload
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import backend.services.nas_browser_service as nas_browser_module
from backend.app.core.authz import AuthContext, get_auth_context
from backend.app.modules.tasks.router import router as tasks_router
from backend.database.schema.ensure import ensure_schema
from backend.services.data_security_store import DataSecurityStore
from backend.services.nas_task_store import NasTaskStore


@dataclass
class PhaseStats:
    requests: int
    errors: int
    avg_ms: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    rps: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "errors": self.errors,
            "error_rate": 0.0 if self.requests <= 0 else round(self.errors / self.requests, 6),
            "avg_ms": round(self.avg_ms, 3),
            "p50_ms": round(self.p50_ms, 3),
            "p90_ms": round(self.p90_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "p99_ms": round(self.p99_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "rps": round(self.rps, 3),
        }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if pct <= 0:
        return float(values[0])
    if pct >= 100:
        return float(values[-1])
    pos = (len(values) - 1) * (pct / 100.0)
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    if lo == hi:
        return float(values[lo])
    frac = pos - lo
    return float(values[lo] + (values[hi] - values[lo]) * frac)


def _build_phase_stats(*, latencies_ms: list[float], errors: int, elapsed_s: float) -> PhaseStats:
    ordered = sorted(latencies_ms)
    requests = len(ordered)
    avg_ms = (sum(ordered) / requests) if requests else 0.0
    max_ms = ordered[-1] if ordered else 0.0
    return PhaseStats(
        requests=requests,
        errors=int(errors),
        avg_ms=float(avg_ms),
        p50_ms=_percentile(ordered, 50),
        p90_ms=_percentile(ordered, 90),
        p95_ms=_percentile(ordered, 95),
        p99_ms=_percentile(ordered, 99),
        max_ms=float(max_ms),
        rps=(requests / elapsed_s) if elapsed_s > 0 else 0.0,
    )


def _seed_tasks(
    *,
    nas_store: NasTaskStore,
    backup_store: DataSecurityStore,
    nas_count: int,
    backup_count: int,
) -> tuple[list[str], list[str], list[int]]:
    all_nas_ids: list[str] = []
    terminal_nas_ids: list[str] = []
    active_statuses = ["pending", "running", "canceling", "pausing"]
    terminal_statuses = ["completed", "failed", "canceled", "paused"]

    for i in range(max(1, nas_count)):
        task_id = f"perf_nas_{i:04d}_{uuid4().hex[:8]}"
        if i % 3 == 0:
            status = random.choice(active_statuses)
            pending_files = [f"folder/{task_id}/doc_{j}.pdf" for j in range(random.randint(1, 3))]
        else:
            status = random.choice(terminal_statuses)
            pending_files = []
            terminal_nas_ids.append(task_id)

        total_files = max(len(pending_files), random.randint(1, 8))
        processed = 0 if pending_files else random.randint(0, total_files)
        failed_count = random.randint(0, 2) if status == "failed" else 0
        imported_count = max(0, processed - failed_count)

        nas_store.create_task(
            task_id=task_id,
            folder_path=f"folder/{i:04d}",
            kb_ref=f"kb_{i % 4}",
            created_by_user_id=f"user_{i % 6}",
            total_files=total_files,
            processed_files=processed,
            imported_count=imported_count,
            failed_count=failed_count,
            skipped_count=random.randint(0, 1),
            status=status,
            pending_files=pending_files,
            priority=random.randint(1, 200),
            failed=[{"path": f"folder/{i:04d}/bad.pdf", "reason": "ingestion_failed", "detail": "simulated"}]
            if failed_count > 0
            else [],
        )
        all_nas_ids.append(task_id)

    if not terminal_nas_ids:
        terminal_nas_ids = list(all_nas_ids[: min(10, len(all_nas_ids))])

    backup_ids: list[int] = []
    backup_statuses = ["queued", "running", "completed", "failed", "canceling", "canceled"]
    for i in range(max(1, backup_count)):
        status = random.choice(backup_statuses)
        job = backup_store.create_job_v2(
            kind="full" if i % 4 == 0 else "incremental",
            status=status,
            message=f"perf seed {status}",
        )
        progress = 100 if status in ("completed", "failed", "canceled") else random.randint(0, 95)
        kwargs: dict[str, Any] = {
            "progress": progress,
            "message": f"perf seed {status}",
        }
        if status in ("completed", "failed", "canceled"):
            now_ms = int(time.time() * 1000)
            kwargs["finished_at_ms"] = now_ms
            kwargs["started_at_ms"] = now_ms - random.randint(1000, 90_000)
        backup_store.update_job(job.id, status=status, **kwargs)
        backup_ids.append(job.id)

    return all_nas_ids, terminal_nas_ids, backup_ids


def _build_perf_app(*, nas_store: NasTaskStore, backup_store: DataSecurityStore) -> FastAPI:
    app = FastAPI()
    app.include_router(tasks_router, prefix="/api")
    deps = SimpleNamespace(nas_task_store=nas_store, data_security_store=backup_store)
    ctx = AuthContext(
        deps=deps,
        payload=TokenPayload(sub="perf_admin"),
        user=SimpleNamespace(user_id="perf_admin"),
        snapshot=SimpleNamespace(is_admin=True),
    )
    app.dependency_overrides[get_auth_context] = lambda: ctx
    return app


async def _run_read_phase(
    *,
    client: AsyncClient,
    duration_s: float,
    concurrency: int,
    terminal_nas_ids: list[str],
    backup_ids: list[int],
) -> PhaseStats:
    start = time.perf_counter()
    deadline = start + duration_s

    def sample_endpoint() -> str:
        roll = random.random()
        if roll < 0.45:
            return "/api/tasks/metrics?kind=all"
        if roll < 0.70:
            return "/api/tasks/metrics?kind=nas_import"
        if roll < 0.90 and backup_ids:
            return f"/api/tasks/{random.choice(backup_ids)}?kind=auto"
        if terminal_nas_ids:
            return f"/api/tasks/{random.choice(terminal_nas_ids)}?kind=auto"
        return "/api/tasks/metrics?kind=all"

    async def worker() -> tuple[list[float], int]:
        latencies: list[float] = []
        errors = 0
        while time.perf_counter() < deadline:
            endpoint = sample_endpoint()
            t0 = time.perf_counter()
            status_code = 599
            try:
                response = await client.get(endpoint)
                status_code = int(response.status_code)
            except Exception:
                status_code = 599
            latencies.append((time.perf_counter() - t0) * 1000.0)
            if status_code >= 400:
                errors += 1
        return latencies, errors

    results = await asyncio.gather(*(worker() for _ in range(max(1, concurrency))))
    elapsed = max(time.perf_counter() - start, 0.001)
    merged_latencies: list[float] = []
    merged_errors = 0
    for latencies, errors in results:
        merged_latencies.extend(latencies)
        merged_errors += errors
    return _build_phase_stats(latencies_ms=merged_latencies, errors=merged_errors, elapsed_s=elapsed)


async def _run_writer(
    *,
    stop_event: asyncio.Event,
    nas_store: NasTaskStore,
    backup_store: DataSecurityStore,
    nas_ids: list[str],
    backup_ids: list[int],
    write_qps: float,
) -> None:
    interval = 1.0 / max(write_qps, 1.0)
    nas_statuses = ["pending", "running", "canceling", "pausing", "completed", "failed", "canceled", "paused"]
    backup_statuses = ["queued", "running", "canceling", "completed", "failed", "canceled"]

    async def one_write() -> None:
        op = random.random()
        try:
            if op < 0.50 and nas_ids:
                task_id = random.choice(nas_ids)
                status = random.choice(nas_statuses)
                pending_files = [f"folder/{task_id}/rw_{random.randint(1, 1000)}.pdf"] if status in (
                    "pending",
                    "running",
                    "canceling",
                    "pausing",
                ) else []
                await asyncio.to_thread(
                    nas_store.update_task,
                    task_id,
                    status=status,
                    current_file="",
                    pending_files=pending_files,
                    processed_files=random.randint(0, 6),
                    imported_count=random.randint(0, 6),
                    failed_count=random.randint(0, 2),
                )
                return

            if op < 0.80 and backup_ids:
                job_id = random.choice(backup_ids)
                status = random.choice(backup_statuses)
                progress = 100 if status in ("completed", "failed", "canceled") else random.randint(0, 95)
                kwargs: dict[str, Any] = {
                    "status": status,
                    "progress": progress,
                    "message": f"writer::{status}",
                }
                if status in ("completed", "failed", "canceled"):
                    now_ms = int(time.time() * 1000)
                    kwargs["finished_at_ms"] = now_ms
                    kwargs["started_at_ms"] = now_ms - random.randint(500, 60_000)
                await asyncio.to_thread(backup_store.update_job, job_id, **kwargs)
                return

            if backup_ids:
                job_id = random.choice(backup_ids)
                await asyncio.to_thread(backup_store.request_cancel_job, job_id, reason="perf_mix_writer")
        except Exception:
            # ignore write errors during stress phase
            return

    while not stop_event.is_set():
        await one_write()
        await asyncio.sleep(interval)


def _report_markdown(
    *,
    generated_at: str,
    config: dict[str, Any],
    baseline: PhaseStats,
    mixed: PhaseStats,
    degradation_pct: float,
    threshold_pct: float,
    verdict: str,
) -> str:
    baseline_dict = baseline.as_dict()
    mixed_dict = mixed.as_dict()
    rps_drop_pct = 0.0
    if float(baseline_dict["rps"]) > 0:
        rps_drop_pct = ((float(baseline_dict["rps"]) - float(mixed_dict["rps"])) / float(baseline_dict["rps"])) * 100.0

    bottlenecks: list[str] = []
    if degradation_pct > threshold_pct:
        bottlenecks.append("混合写入阶段存在 sqlite 读写争用，P95 退化超过阈值。")
    if rps_drop_pct >= 8.0:
        bottlenecks.append("读吞吐下降明显，建议继续优化 metrics/read 路径热点查询。")
    if not bottlenecks:
        bottlenecks.append("当前场景未发现明显性能瓶颈，建议在 SIT/UAT 用真实流量画像复测。")

    lines = [
        "# PERF-TASK-MIX-001 混合负载回归报告",
        "",
        f"- 生成时间: {generated_at}",
        "- 测试模式: in-process ASGI（统一任务接口）",
        f"- 场景参数: duration={config['duration_s']}s, concurrency={config['read_concurrency']}, writer_qps={config['write_qps']}",
        "",
        "## 结果汇总",
        "",
        "| Phase | Requests | Error Rate | Avg(ms) | P95(ms) | P99(ms) | Max(ms) | RPS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| baseline_read | {baseline_dict['requests']} | {baseline_dict['error_rate']:.4f} | "
            f"{baseline_dict['avg_ms']:.3f} | {baseline_dict['p95_ms']:.3f} | {baseline_dict['p99_ms']:.3f} | "
            f"{baseline_dict['max_ms']:.3f} | {baseline_dict['rps']:.3f} |"
        ),
        (
            f"| mixed_read | {mixed_dict['requests']} | {mixed_dict['error_rate']:.4f} | "
            f"{mixed_dict['avg_ms']:.3f} | {mixed_dict['p95_ms']:.3f} | {mixed_dict['p99_ms']:.3f} | "
            f"{mixed_dict['max_ms']:.3f} | {mixed_dict['rps']:.3f} |"
        ),
        "",
        "## DoD 检查",
        "",
        (
            f"- P95 退化比例: `{degradation_pct:.3f}%`（阈值 `<= {threshold_pct:.1f}%`）"
        ),
        f"- RPS 下降比例: `{rps_drop_pct:.3f}%`",
        f"- 结论: **{verdict}**",
        "",
        "## 瓶颈清单",
        "",
        *[f"- {item}" for item in bottlenecks],
        "",
        "## 已落地优化",
        "",
        "- 任务指标告警日志增加按 alert_id 冷却去重，避免高并发重复刷屏。",
        "- 任务指标查询增加短 TTL 快照缓存，降低混合读写下的统计查询争用。",
        "",
        "## 说明",
        "",
        "- 本报告用于 W02-T07 回归自动化基线；建议在 SIT/UAT 使用真实服务地址重复执行并归档。",
    ]
    return "\n".join(lines) + "\n"


async def _run(args: argparse.Namespace) -> int:
    random.seed(int(args.seed))
    tmp_root = Path(tempfile.gettempdir()) / f"ragflowauth_perf_mix_{uuid4().hex}"
    tmp_root.mkdir(parents=True, exist_ok=True)
    db_path = tmp_root / "auth.db"

    ensure_schema(db_path)
    nas_store = NasTaskStore(db_path=str(db_path))
    backup_store = DataSecurityStore(db_path=str(db_path))

    nas_ids, terminal_nas_ids, backup_ids = _seed_tasks(
        nas_store=nas_store,
        backup_store=backup_store,
        nas_count=int(args.nas_tasks),
        backup_count=int(args.backup_tasks),
    )

    app = _build_perf_app(nas_store=nas_store, backup_store=backup_store)
    transport = ASGITransport(app=app)

    original_schedule = nas_browser_module.NasBrowserService._schedule_folder_import_task
    nas_browser_module.NasBrowserService._schedule_folder_import_task = lambda *_args, **_kwargs: None
    nas_browser_module._ACTIVE_TASKS.clear()
    nas_browser_module._RUNNING_TASK_META.clear()
    nas_browser_module._QUEUED_TASK_IDS.clear()
    nas_browser_module._QUEUED_TASK_HEAP.clear()

    try:
        async with AsyncClient(transport=transport, base_url="http://perf.local") as client:
            baseline = await _run_read_phase(
                client=client,
                duration_s=float(args.duration_s),
                concurrency=int(args.read_concurrency),
                terminal_nas_ids=terminal_nas_ids,
                backup_ids=backup_ids,
            )

            stop_event = asyncio.Event()
            writer_task = asyncio.create_task(
                _run_writer(
                    stop_event=stop_event,
                    nas_store=nas_store,
                    backup_store=backup_store,
                    nas_ids=nas_ids,
                    backup_ids=backup_ids,
                    write_qps=float(args.write_qps),
                )
            )
            try:
                mixed = await _run_read_phase(
                    client=client,
                    duration_s=float(args.duration_s),
                    concurrency=int(args.read_concurrency),
                    terminal_nas_ids=terminal_nas_ids,
                    backup_ids=backup_ids,
                )
            finally:
                stop_event.set()
                await writer_task
    finally:
        nas_browser_module.NasBrowserService._schedule_folder_import_task = original_schedule
        nas_browser_module._ACTIVE_TASKS.clear()
        nas_browser_module._RUNNING_TASK_META.clear()
        nas_browser_module._QUEUED_TASK_IDS.clear()
        nas_browser_module._QUEUED_TASK_HEAP.clear()

    baseline_p95 = baseline.p95_ms
    mixed_p95 = mixed.p95_ms
    if baseline_p95 <= 0:
        degradation_pct = 0.0
    else:
        degradation_pct = ((mixed_p95 - baseline_p95) / baseline_p95) * 100.0
    threshold_pct = float(args.max_p95_degradation_pct)
    verdict = "PASS" if degradation_pct <= threshold_pct else "FAIL"

    report_dir = Path("doc/test/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "duration_s": float(args.duration_s),
            "read_concurrency": int(args.read_concurrency),
            "write_qps": float(args.write_qps),
            "nas_tasks": int(args.nas_tasks),
            "backup_tasks": int(args.backup_tasks),
            "seed": int(args.seed),
            "max_p95_degradation_pct": threshold_pct,
        },
        "baseline": baseline.as_dict(),
        "mixed": mixed.as_dict(),
        "p95_degradation_pct": round(degradation_pct, 6),
        "threshold_pct": threshold_pct,
        "verdict": verdict,
    }

    md_text = _report_markdown(
        generated_at=str(payload["generated_at"]),
        config=payload["config"],
        baseline=baseline,
        mixed=mixed,
        degradation_pct=degradation_pct,
        threshold_pct=threshold_pct,
        verdict=verdict,
    )

    md_output = report_dir / f"perf_task_mix_report_{timestamp}.md"
    md_latest = report_dir / "perf_task_mix_report_latest.md"
    json_output = report_dir / f"perf_task_mix_report_{timestamp}.json"
    json_latest = report_dir / "perf_task_mix_report_latest.json"

    md_output.write_text(md_text, encoding="utf-8")
    md_latest.write_text(md_text, encoding="utf-8")
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    json_latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[PERF] baseline p95={baseline.p95_ms:.3f}ms mixed p95={mixed.p95_ms:.3f}ms")
    print(f"[PERF] p95 degradation={degradation_pct:.3f}% threshold={threshold_pct:.3f}% verdict={verdict}")
    print(f"[PERF] report: {md_output}")
    print(f"[PERF] report: {md_latest}")
    print(f"[PERF] json:   {json_output}")
    print(f"[PERF] json:   {json_latest}")

    return 0 if verdict == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PERF-TASK-MIX-001 mixed-load benchmark.")
    parser.add_argument("--duration-s", type=float, default=12.0, help="Read phase duration for baseline/mixed.")
    parser.add_argument("--read-concurrency", type=int, default=24, help="Concurrent read workers.")
    parser.add_argument("--write-qps", type=float, default=35.0, help="Background write operations per second.")
    parser.add_argument("--nas-tasks", type=int, default=120, help="Seeded NAS tasks.")
    parser.add_argument("--backup-tasks", type=int, default=80, help="Seeded backup jobs.")
    parser.add_argument("--seed", type=int, default=20260313, help="Random seed.")
    parser.add_argument(
        "--max-p95-degradation-pct",
        type=float,
        default=20.0,
        help="DoD threshold. Benchmark passes when mixed p95 degradation <= this value.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
