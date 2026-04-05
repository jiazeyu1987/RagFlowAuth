from ._shared import _tool_mod, _delegate
from .publish_test_confirm_ops import confirm_publish_test_to_prod
from .publish_test_worker_ops import run_publish_test_to_prod_worker

def publish_test_to_prod(app, *args, **kwargs):
    return _delegate(app, "_publish_test_to_prod_impl", "publish_test_to_prod", *args, **kwargs)

def publish_test_to_prod_impl(app):
    tool_mod = _tool_mod()
    self = app

    if not confirm_publish_test_to_prod(
        messagebox=tool_mod.messagebox,
        test_server_ip=tool_mod.TEST_SERVER_IP,
        prod_server_ip=tool_mod.PROD_SERVER_IP,
    ):
        return

    def worker():
        run_publish_test_to_prod_worker(
            self,
            tk=tool_mod.tk,
            log_to_file=tool_mod.log_to_file,
            prod_server_ip=tool_mod.PROD_SERVER_IP,
            feature_publish_from_test_to_prod=tool_mod.feature_publish_from_test_to_prod,
        )

    self.task_runner.run(name="publish_test_to_prod", fn=worker)
