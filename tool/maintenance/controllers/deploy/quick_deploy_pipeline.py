from __future__ import annotations

from pathlib import Path

from .quick_deploy_context import QuickDeployContext
from .quick_deploy_steps import (
    cleanup_local_temp,
    load_config,
    prepare_runtime_values,
    step_1_stop_containers,
    step_2_build_images,
    step_3_export_images,
    step_4_transfer_images,
    step_5_load_images,
    step_6_start_containers,
    step_7_verify,
)


class QuickDeployPipeline:
    def __init__(self, ctx: QuickDeployContext):
        self.ctx = ctx
        self.app = ctx.app
        self.subprocess = ctx.subprocess
        self.log = ctx.log_to_file

    def run(self) -> None:
        load_config(self)
        prepare_runtime_values(self)
        step_1_stop_containers(self)
        step_2_build_images(self)
        step_3_export_images(self)
        step_4_transfer_images(self)
        step_5_load_images(self)
        step_6_start_containers(self)
        step_7_verify(self)
        cleanup_local_temp(self)

    def _status(self, text: str) -> None:
        self.app.status_bar.config(text=text)

    def _run(self, cmd, *, shell: bool = False, cwd: Path | None = None):
        return self.subprocess.run(cmd, shell=shell, cwd=str(cwd) if cwd else None, capture_output=True, text=True)

    def _run_or_raise(self, cmd, *, shell: bool = False, cwd: Path | None = None, error: str = "Command failed"):
        result = self._run(cmd, shell=shell, cwd=cwd)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"{error}: {detail}")
        return result

    def _container_status(self, name: str) -> str:
        result = self._run(
            ["ssh", f"{self.ctx.server_user}@{self.ctx.server_host}", "docker", "inspect", name, "--format", "{{.State.Status}}"]
        )
        if result.returncode != 0:
            return ""
        return (result.stdout or "").strip()

