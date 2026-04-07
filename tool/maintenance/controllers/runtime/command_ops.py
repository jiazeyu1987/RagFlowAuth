from ._shared import _tool_mod


SPECIAL_COMMAND_HANDLERS = {
    "quick-deploy": "run_quick_deploy",
    "__restart_ragflow_and_ragflowauth__": "restart_ragflow_and_ragflowauth",
    "__stop_ragflow_and_ragflowauth__": "stop_ragflow_and_ragflowauth",
    "__kill_backup_job__": "kill_running_backup_job",
    "__cleanup_docker_images__": "cleanup_docker_images",
    "__mount_windows_share__": "mount_windows_share",
    "__unmount_windows_share__": "unmount_windows_share",
    "__check_mount_status__": "check_mount_status",
}


def execute_ssh_command_impl(app, command):
    tool_mod = _tool_mod()
    self = app
    log_to_file = tool_mod.log_to_file

    handler_name = SPECIAL_COMMAND_HANDLERS.get(command)
    if handler_name:
        getattr(self, handler_name)()
        return

    if not self.ssh_executor:
        self.update_ssh_executor()

    self.status_bar.config(text=f"Running: {command}")

    def execute():
        def callback(output):
            print(output)
            log_to_file(f"[SSH-CMD] {output.strip()}")

        success, output = self.ssh_executor.execute(command, callback)

        if success:
            self.status_bar.config(text="Command finished")
            msg = f"[INFO] Command succeeded\nOutput:\n{output}"
            print(msg)
            log_to_file(msg)
        else:
            self.status_bar.config(text="Command failed")
            msg = f"[ERROR] Command failed\nError: {output}"
            print(msg)
            log_to_file(msg, "ERROR")

    self.task_runner.run(name="restart_services", fn=execute)

