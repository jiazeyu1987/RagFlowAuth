from ._shared import _tool_mod, _delegate
from .publish_local_confirm_ops import (
    confirm_publish_local_to_test,
    resolve_local_sync_selection,
)
from .publish_local_worker_ops import run_publish_local_to_test_worker

def publish_local_to_test(app, *args, **kwargs):
    return _delegate(app, "_publish_local_to_test_impl", "publish_local_to_test", *args, **kwargs)

def publish_local_to_test_impl(app):
    tool_mod = _tool_mod()
    self = app

    want_sync_data, selected_pack = resolve_local_sync_selection(self)
    confirmed, want_sync_data = confirm_publish_local_to_test(
        messagebox=tool_mod.messagebox,
        test_server_ip=tool_mod.TEST_SERVER_IP,
        want_sync_data=want_sync_data,
        selected_pack=selected_pack,
    )
    if not confirmed:
        return

    def worker():
        run_publish_local_to_test_worker(
            self,
            tk=tool_mod.tk,
            log_to_file=tool_mod.log_to_file,
            test_server_ip=tool_mod.TEST_SERVER_IP,
            feature_publish_from_local_to_test=tool_mod.feature_publish_from_local_to_test,
            want_sync_data=want_sync_data,
            selected_pack=selected_pack,
        )

    self.task_runner.run(name="publish_test_data_to_prod", fn=worker)
