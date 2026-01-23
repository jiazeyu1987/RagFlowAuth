from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from backend.services.data_security_backup import _run


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _convert_container_path_to_host(container_path: Path) -> str:
    """
    Convert container path to host path for Docker volume mounting.
    This is needed when running Docker commands from within a container.
    """
    path_str = str(container_path)
    # Order matters: check more specific paths first
    if path_str.startswith("/app/data/backups/"):
        # Backups directory has its own mount
        return path_str.replace("/app/data/backups", "/opt/ragflowauth/backups", 1)
    elif path_str.startswith("/app/data/"):
        # Main data directory
        return path_str.replace("/app/data", "/opt/ragflowauth/data", 1)
    elif path_str.startswith("/app/uploads/"):
        return path_str.replace("/app/uploads", "/opt/ragflowauth/uploads", 1)
    return path_str


def backup_docker_images(images_dir: Path, include_images: bool = True) -> list[str]:
    """
    Backup all Docker images to tar files.

    Args:
        images_dir: Directory to save image backups
        include_images: If False, skip image backup (images can be pulled)

    Returns:
        List of created archive filenames
    """
    _ensure_dir(images_dir)
    archives: list[str] = []

    if not include_images:
        # Create a note file instead of backing up images
        note_file = images_dir / "images_not_included.txt"
        note_file.write_text(
            "Docker images are not included in this backup.\n"
            "Images can be pulled from their registries using docker pull.\n"
            f"Backup created at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            encoding="utf-8"
        )
        return []

    # List all images
    code, out = _run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"])
    if code != 0:
        raise RuntimeError(f"Failed to list Docker images: {out}")

    images = [line.strip() for line in (out or "").splitlines() if line.strip() and "<none>" not in line]
    if not images:
        return archives

    # Backup each image
    for image in images:
        # Convert image tag to filename (replace : and / with _)
        safe_name = image.replace(":", "_").replace("/", "_")
        archive_name = f"image_{safe_name}_{_timestamp()}.tar"
        archive_path = images_dir / archive_name

        # Convert container path to host path for Docker volume mounting
        host_save_dir = Path(_convert_container_path_to_host(archive_path.parent))
        save_filename = archive_path.name

        # Create directory on host
        _ensure_dir(host_save_dir)

        # Use Docker-in-Docker to save the image
        # Mount Docker socket and host directory to save image
        code, out = _run([
            "docker", "run", "--rm",
            "-v", "/var/run/docker.sock:/var/run/docker.sock",
            "-v", f"{host_save_dir}:/backup_output",
            "ragflowauth-backend:local",
            "sh", "-c", f"docker save {image} > /backup_output/{save_filename}"
        ])
        if code != 0:
            raise RuntimeError(f"Failed to save image {image}: {out}")

        archives.append(archive_name)

    return archives


def backup_docker_containers(config_dir: Path) -> str:
    """
    Backup container configurations (not the running state, just the configuration).

    Args:
        config_dir: Directory to save container configs

    Returns:
        Path to the created JSON file
    """
    _ensure_dir(config_dir)

    code, out = _run(["docker", "ps", "-a", "--format", "{{.Names}}"])
    if code != 0:
        raise RuntimeError(f"Failed to list containers: {out}")

    containers = [line.strip() for line in (out or "").splitlines() if line.strip()]
    container_configs = []

    for container in containers:
        code, out = _run(["docker", "inspect", container])
        if code != 0:
            continue

        try:
            config = json.loads(out)
            if config:
                container_configs.append(config[0])
        except json.JSONDecodeError:
            continue

    config_file = config_dir / f"containers_config_{_timestamp()}.json"
    config_file.write_text(json.dumps(container_configs, indent=2, ensure_ascii=False), encoding="utf-8")

    return config_file.name


def backup_docker_networks(config_dir: Path) -> str:
    """
    Backup Docker network configurations.

    Args:
        config_dir: Directory to save network configs

    Returns:
        Path to the created JSON file
    """
    _ensure_dir(config_dir)

    # Get all networks
    code, out = _run(["docker", "network", "ls", "--format", "{{.Name}}"])
    if code != 0:
        raise RuntimeError(f"Failed to list networks: {out}")

    networks = [line.strip() for line in (out or "").splitlines() if line.strip()]
    network_configs = []

    for network in networks:
        code, out = _run(["docker", "network", "inspect", network])
        if code != 0:
            continue

        try:
            config = json.loads(out)
            if config:
                network_configs.append(config[0])
        except json.JSONDecodeError:
            continue

    config_file = config_dir / f"networks_config_{_timestamp()}.json"
    config_file.write_text(json.dumps(network_configs, indent=2, ensure_ascii=False), encoding="utf-8")

    return config_file.name


def backup_docker_volumes_list(config_dir: Path) -> str:
    """
    Backup list of Docker volumes (actual volume data is backed up by the main backup function).

    Args:
        config_dir: Directory to save volume list

    Returns:
        Path to the created text file
    """
    _ensure_dir(config_dir)

    code, out = _run(["docker", "volume", "ls", "--format", "{{.Name}}"])
    if code != 0:
        raise RuntimeError(f"Failed to list volumes: {out}")

    volumes = [line.strip() for line in (out or "").splitlines() if line.strip()]

    volume_file = config_dir / f"volumes_list_{_timestamp()}.txt"
    volume_file.write_text("\n".join(volumes), encoding="utf-8")

    return volume_file.name


def create_full_backup_manifest(
    pack_dir: Path,
    include_images: bool,
    image_archives: list[str],
    containers_config: str,
    networks_config: str,
    volumes_list: str,
    ragflow_manifest: dict,
) -> None:
    """
    Create a manifest file for the full backup.

    Args:
        pack_dir: Backup package directory
        include_images: Whether images are included
        image_archives: List of image archive filenames
        containers_config: Container config filename
        networks_config: Network config filename
        volumes_list: Volume list filename
        ragflow_manifest: Manifest from RAGFlow backup
    """
    manifest = {
        "backup_type": "full",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "docker": {
            "images_included": include_images,
            "image_archives": image_archives,
            "containers_config": containers_config,
            "networks_config": networks_config,
            "volumes_list": volumes_list,
        },
        "ragflow": ragflow_manifest,
    }

    manifest_file = pack_dir / "full_backup_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
