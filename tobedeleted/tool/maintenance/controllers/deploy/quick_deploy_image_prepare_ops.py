from __future__ import annotations


def step_1_stop_containers(pipeline) -> None:
    pipeline._status("Step 1/7: stopping remote containers...")
    pipeline.log("[Step 1/7] stopping remote containers")

    cmd = [
        "ssh",
        f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}",
        "docker",
        "stop",
        "ragflowauth-frontend",
        "ragflowauth-backend",
    ]
    pipeline._run(cmd)
    pipeline.log("[Step 1/7] stop command executed")


def step_2_build_images(pipeline) -> None:
    pipeline._status("Step 2/7: building images...")
    pipeline.log("[Step 2/7] building backend image")
    pipeline._run_or_raise(
        ["docker", "build", "-f", "backend/Dockerfile", "-t", pipeline.ctx.backend_image, "."],
        cwd=pipeline.ctx.repo_root,
        error="build backend image failed",
    )

    pipeline.log("[Step 2/7] building frontend image")
    pipeline._run_or_raise(
        ["docker", "build", "-f", "fronted/Dockerfile", "-t", pipeline.ctx.frontend_image, "."],
        cwd=pipeline.ctx.repo_root,
        error="build frontend image failed",
    )
    pipeline.log("[Step 2/7] image build completed")
