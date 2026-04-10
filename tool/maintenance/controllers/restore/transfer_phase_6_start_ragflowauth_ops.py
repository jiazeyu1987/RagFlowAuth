def start_ragflowauth_containers(self):
    from tool.maintenance.core.constants import NAS_MOUNT_POINT

    ragflowauth_reason = ""

    # 尽量启动已存在的容器；还原阶段不强制删除容器，避免“没镜像/没网络”导致无法启动。
    self.append_restore_log("  检查 RagflowAuth 容器是否存在...")
    success, out_backend_exists = self.ssh_executor.execute(
        "docker inspect ragflowauth-backend >/dev/null 2>&1 && echo YES || echo NO"
    )
    success, out_frontend_exists = self.ssh_executor.execute(
        "docker inspect ragflowauth-frontend >/dev/null 2>&1 && echo YES || echo NO"
    )
    backend_exists = (out_backend_exists or "").strip().endswith("YES")
    frontend_exists = (out_frontend_exists or "").strip().endswith("YES")

    # docker run 需要网络
    self.ssh_executor.execute(
        "docker network inspect ragflowauth-network >/dev/null 2>&1 || docker network create ragflowauth-network"
    )

    if backend_exists and frontend_exists:
        self.append_restore_log("  启动已存在的 RagflowAuth 容器...")
        success, output = self.ssh_executor.execute("docker start ragflowauth-backend ragflowauth-frontend 2>/dev/null || true")
        if output:
            self.append_restore_log(f"  {output}")
        return ragflowauth_reason

    self.append_restore_log("  RagflowAuth 容器不存在，尝试从本地镜像创建容器（不会联网拉取）...")
    success, backend_image = self.ssh_executor.execute(
        "docker images ragflowauth-backend --format '{{.Repository}}:{{.Tag}}' | grep -v '<none>' | head -n 1"
    )
    success, frontend_image = self.ssh_executor.execute(
        "docker images ragflowauth-frontend --format '{{.Repository}}:{{.Tag}}' | grep -v '<none>' | head -n 1"
    )
    backend_image = (backend_image or "").strip()
    frontend_image = (frontend_image or "").strip()

    if not backend_image or not frontend_image:
        ragflowauth_reason = (
            "未找到 ragflowauth-backend/frontend 本地镜像。"
            "如果本次还原未包含 images.tar，请先使用【发布】把镜像发布到测试服务器，再启动容器。"
        )
        self.append_restore_log(f"  ⚠️  {ragflowauth_reason}")
        return ragflowauth_reason

    self.append_restore_log(f"  使用镜像: backend={backend_image} frontend={frontend_image}")

    # 可选挂载：backup_config.json
    success, has_backup_cfg = self.ssh_executor.execute("test -f /opt/ragflowauth/backup_config.json && echo YES || echo NO")
    has_backup_cfg = (has_backup_cfg or "").strip().endswith("YES")
    backup_cfg_mount = " -v /opt/ragflowauth/backup_config.json:/app/backup_config.json:ro" if has_backup_cfg else ""

    run_front = (
        "docker run -d --name ragflowauth-frontend --network ragflowauth-network "
        f"-p 3001:80 --restart unless-stopped {frontend_image}"
    )
    run_back = (
        "docker run -d --name ragflowauth-backend --network ragflowauth-network -p 8001:8001 "
        "-e TZ=Asia/Shanghai -e HOST=0.0.0.0 -e PORT=8001 -e DATABASE_PATH=data/auth.db -e UPLOAD_DIR=data/uploads "
        "-v /opt/ragflowauth/data:/app/data "
        "-v /opt/ragflowauth/uploads:/app/uploads "
        "-v /opt/ragflowauth/ragflow_config.json:/app/ragflow_config.json:ro "
        "-v /opt/ragflowauth/ragflow_compose:/app/ragflow_compose:ro "
        f"{backup_cfg_mount} "
        "-v /opt/ragflowauth/backups:/app/data/backups "
        f"-v {NAS_MOUNT_POINT}:{NAS_MOUNT_POINT} "
        "-v /mnt/replica:/mnt/replica "
        "-v /var/run/docker.sock:/var/run/docker.sock:ro "
        f"--restart unless-stopped {backend_image}"
    ).replace("  ", " ").strip()

    self.append_restore_log(f"  run frontend: {run_front}")
    success, output = self.ssh_executor.execute(run_front)
    if not success:
        ragflowauth_reason = f"前端容器创建失败: {output}"
        self.append_restore_log(f"  ⚠️  {ragflowauth_reason}")
    elif output:
        self.append_restore_log(f"  frontend started: {output.strip()}")

    self.append_restore_log(f"  run backend: {run_back}")
    success, output = self.ssh_executor.execute(run_back)
    if not success:
        ragflowauth_reason = f"后端容器创建失败: {output}"
        self.append_restore_log(f"  ⚠️  {ragflowauth_reason}")
    elif output:
        self.append_restore_log(f"  backend started: {output.strip()}")

    return ragflowauth_reason
