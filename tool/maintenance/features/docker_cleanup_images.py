from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tool.maintenance.core.ssh_executor import SSHExecutor


NOISE_MARKERS = (
    "close - IO is still pending",
    "read:",
    "write:",
    "io:",
)


def _clean_ssh_output(text: str) -> str:
    if not text:
        return ""
    return "\n".join(
        line for line in text.splitlines()
        if line.strip() and not any(m in line for m in NOISE_MARKERS)
    ).strip()


@dataclass(frozen=True)
class DockerCleanupResult:
    running_images: set[str]
    all_images: list[str]
    deleted: list[str]
    failed: list[str]
    docker_df: str

    def summary(self) -> str:
        if not self.deleted and not self.failed:
            return (
                "✅ 没有需要清理的镜像\n\n"
                f"当前运行的镜像数量: {len(self.running_images)}\n"
                "所有 ragflowauth 镜像都在使用中"
            )
        msg = ""
        msg += f"删除成功: {len(self.deleted)}\n"
        msg += f"删除失败: {len(self.failed)}\n\n"
        if self.deleted:
            msg += "✅ 已删除镜像:\n" + "\n".join(f"- {x}" for x in self.deleted) + "\n\n"
        if self.failed:
            msg += "❌ 删除失败镜像:\n" + "\n".join(f"- {x}" for x in self.failed) + "\n\n"
        if self.docker_df:
            msg += "Docker 空间使用:\n" + self.docker_df
        return msg.strip()


def cleanup_docker_images(
    *,
    ssh: SSHExecutor,
    log: Callable[[str, str], None],
) -> DockerCleanupResult:
    log("[CLEANUP-IMAGES] Step 1: list running container images", "INFO")
    ok, out = ssh.execute("docker ps --format '{{.Image}}'")
    out = _clean_ssh_output(out or "")
    if not ok:
        raise RuntimeError(f"获取容器列表失败:\n{out}")

    running_images: set[str] = {line.strip() for line in out.splitlines() if line.strip()}
    log(f"[CLEANUP-IMAGES] running_images={sorted(running_images)}", "DEBUG")

    log("[CLEANUP-IMAGES] Step 2: list ragflowauth images", "INFO")
    ok, out = ssh.execute("docker images --format '{{.Repository}}:{{.Tag}}' | grep 'ragflowauth' || echo 'NO_IMAGES'")
    out = _clean_ssh_output(out or "")
    if not ok or out.strip() == "NO_IMAGES":
        raise RuntimeError("获取镜像列表失败或没有镜像")

    all_images = [line.strip() for line in out.splitlines() if line.strip() and "ragflowauth" in line]
    unused = [img for img in all_images if img not in running_images]
    log(f"[CLEANUP-IMAGES] unused_images={unused}", "DEBUG")

    deleted: list[str] = []
    failed: list[str] = []
    for img in unused:
        ok, out = ssh.execute(f"docker rmi {img} 2>&1 || echo 'FAILED'")
        out = _clean_ssh_output(out or "")
        if ok and "FAILED" not in out:
            deleted.append(img)
        else:
            failed.append(img)

    docker_df = ""
    ok, out = ssh.execute("docker system df 2>&1 || true")
    if ok:
        docker_df = _clean_ssh_output(out or "")

    return DockerCleanupResult(
        running_images=running_images,
        all_images=all_images,
        deleted=deleted,
        failed=failed,
        docker_df=docker_df,
    )

