from __future__ import annotations

import shutil


def cleanup_local_temp(pipeline) -> None:
    if pipeline.ctx.temp_dir and pipeline.ctx.temp_dir.exists():
        shutil.rmtree(pipeline.ctx.temp_dir, ignore_errors=True)
        pipeline.log("local temp files cleaned")
