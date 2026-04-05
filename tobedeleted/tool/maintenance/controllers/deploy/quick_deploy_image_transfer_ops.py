from __future__ import annotations


def step_3_export_images(pipeline) -> None:
    pipeline._status("Step 3/7: exporting images...")
    pipeline.log("[Step 3/7] exporting frontend image")
    pipeline._run_or_raise(
        ["docker", "save", pipeline.ctx.frontend_image, "-o", str(pipeline.ctx.frontend_tar)],
        error="export frontend image failed",
    )

    pipeline.log("[Step 3/7] exporting backend image")
    pipeline._run_or_raise(
        ["docker", "save", pipeline.ctx.backend_image, "-o", str(pipeline.ctx.backend_tar)],
        error="export backend image failed",
    )
    pipeline.log("[Step 3/7] export completed")


def step_4_transfer_images(pipeline) -> None:
    pipeline._status("Step 4/7: transferring images...")
    pipeline.log("[Step 4/7] scp frontend image")
    pipeline._run_or_raise(
        ["scp", str(pipeline.ctx.frontend_tar), f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}:/tmp/"],
        error="transfer frontend image failed",
    )

    pipeline.log("[Step 4/7] scp backend image")
    pipeline._run_or_raise(
        ["scp", str(pipeline.ctx.backend_tar), f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}:/tmp/"],
        error="transfer backend image failed",
    )
    pipeline.log("[Step 4/7] transfer completed")


def step_5_load_images(pipeline) -> None:
    pipeline._status("Step 5/7: loading images on server...")
    frontend_tar_name = pipeline.ctx.frontend_tar.name
    backend_tar_name = pipeline.ctx.backend_tar.name

    pipeline.log("[Step 5/7] docker load frontend image")
    pipeline._run_or_raise(
        ["ssh", f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}", "docker", "load", "-i", f"/tmp/{frontend_tar_name}"],
        error="load frontend image failed",
    )

    pipeline.log("[Step 5/7] docker load backend image")
    pipeline._run_or_raise(
        ["ssh", f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}", "docker", "load", "-i", f"/tmp/{backend_tar_name}"],
        error="load backend image failed",
    )

    pipeline._run(
        [
            "ssh",
            f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}",
            "rm",
            "-f",
            f"/tmp/{frontend_tar_name}",
            f"/tmp/{backend_tar_name}",
        ]
    )
    pipeline.log("[Step 5/7] load completed")
