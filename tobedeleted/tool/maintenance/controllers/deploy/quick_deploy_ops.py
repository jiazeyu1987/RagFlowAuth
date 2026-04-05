from ._shared import _tool_mod
from .quick_deploy_context import QuickDeployContext
from .quick_deploy_pipeline import QuickDeployPipeline


def run_quick_deploy(app, *args, **kwargs):
    return run_quick_deploy_impl(app, *args, **kwargs)


def run_quick_deploy_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()
    self = app

    self.status_bar.config(text="Step 1/7: preparing deployment...")

    def execute():
        try:
            tool_file = tool_mod.Path(tool_mod.__file__).resolve()
            repo_root = tool_file.parents[2]
            config_path = tool_file.parent / "scripts" / "deploy-config.json"

            ctx = QuickDeployContext(
                app=self,
                subprocess=tool_mod.subprocess,
                log_to_file=tool_mod.log_to_file,
                repo_root=repo_root,
                config_path=config_path,
            )
            QuickDeployPipeline(ctx).run()
        except Exception as exc:
            self.status_bar.config(text="Deployment failed")
            msg = f"[ERROR] quick deploy failed: {exc}"
            print(msg)
            tool_mod.log_to_file(msg, "ERROR")

    self.task_runner.run(name="stop_services", fn=execute)
