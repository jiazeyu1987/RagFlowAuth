def upload_restore_auth_db(self, *, subprocess_mod):
    # 上传 auth.db
    auth_db_local = self.selected_restore_folder / "auth.db"
    if auth_db_local.exists():
        self.append_restore_log(f"  上传 auth.db ({auth_db_local.stat().st_size / 1024 / 1024:.2f} MB)...")
        result = subprocess_mod.run(
            [
                "scp",
                "-o",
                "BatchMode=yes",
                str(auth_db_local),
                f"{self.restore_target_user}@{self.restore_target_ip}:/opt/ragflowauth/data/auth.db",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            self.append_restore_log("  ✅ auth.db 上传成功")
        else:
            raise Exception(f"上传 auth.db 失败: {result.stderr}")

    # 注意：按需求仅还原 auth.db + volumes（若存在 images.tar 也还原镜像），不还原 uploads
