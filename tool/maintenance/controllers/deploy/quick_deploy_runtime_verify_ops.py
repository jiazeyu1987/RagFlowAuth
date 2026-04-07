from __future__ import annotations


def step_7_verify(pipeline) -> None:
    pipeline._status("Step 7/7: verifying deployment...")
    pipeline.log("[Step 7/7] verifying containers")

    frontend_status = pipeline._container_status("ragflowauth-frontend")
    backend_status = pipeline._container_status("ragflowauth-backend")

    if frontend_status != "running" or backend_status != "running":
        raise RuntimeError(f"verify failed: frontend={frontend_status or 'unknown'}, backend={backend_status or 'unknown'}")

    pipeline._status("Deployment completed: frontend and backend are running")
    pipeline.log("[Step 7/7] verify passed")
    pipeline.log(f"frontend status: {frontend_status}")
    pipeline.log(f"backend status: {backend_status}")
    pipeline.log(f"frontend URL: http://{pipeline.ctx.server_host}:{pipeline.ctx.frontend_port}")
    pipeline.log(f"backend URL: http://{pipeline.ctx.server_host}:{pipeline.ctx.backend_port}")
    pipeline.log(f"image tag: {pipeline.ctx.tag}")
