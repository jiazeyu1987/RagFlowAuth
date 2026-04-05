def _tool_mod():
    from tool.maintenance import tool as tool_mod

    return tool_mod


def setup_ui_impl(app):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    ttk = tool_mod.ttk
    ENVIRONMENTS = tool_mod.ENVIRONMENTS
    TaskRunner = tool_mod.TaskRunner

    # Button style used by tool tabs.
    style = ttk.Style()
    style.configure("Large.TButton", font=("Arial", 12, "bold"), padding=10)

    config_frame = ttk.LabelFrame(self.root, text="Server Config", padding=10)
    config_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

    ttk.Label(config_frame, text="Environment:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
    self.env_var = tk.StringVar(value=self.config.environment)
    env_combo = ttk.Combobox(
        config_frame,
        textvariable=self.env_var,
        values=list(ENVIRONMENTS.keys()),
        state="readonly",
        width=15,
    )
    env_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
    env_combo.bind("<<ComboboxSelected>>", self.on_environment_changed)

    ttk.Label(config_frame, text="Server IP:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
    self.ip_var = tk.StringVar(value=self.config.ip)
    self.ip_entry = ttk.Entry(config_frame, textvariable=self.ip_var, width=18)
    self.ip_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

    ttk.Label(config_frame, text="User:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
    self.user_var = tk.StringVar(value=self.config.user)
    self.user_entry = ttk.Entry(config_frame, textvariable=self.user_var, width=12)
    self.user_entry.grid(row=0, column=5, sticky=tk.W, padx=(0, 20))

    save_btn = ttk.Button(config_frame, text="Save Config", command=self.save_config)
    save_btn.grid(row=0, column=6, padx=(5, 0))

    test_btn = ttk.Button(config_frame, text="Test Connection", command=self.test_connection)
    test_btn.grid(row=0, column=7, padx=(5, 0))

    self.notebook = ttk.Notebook(self.root)
    self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    self.task_runner = TaskRunner(ui_call=lambda fn: self.root.after(0, fn))

    self.create_tools_tab()
    self.create_web_links_tab()
    self.create_restore_tab()
    self.create_release_tab()
    self.create_onlyoffice_tab()
    self.create_smoke_tab()
    self.create_backup_files_tab()
    self.create_replica_backups_tab()
    self.create_logs_tab()
    self.nas_tab = None
    self.nas_tab_controller = None
    self.refresh_admin_tabs()

    self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
    self.status_bar.pack(fill=tk.X, padx=10, pady=(0, 10))
