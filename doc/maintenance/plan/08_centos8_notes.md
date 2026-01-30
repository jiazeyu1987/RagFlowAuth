# 08 CentOS 8.1 部署注意事项（稳定优先）

你当前服务器是 `CentOS 8.1`，可以部署运行，但建议注意以下事项以提升稳定性与可维护性。

## 1) CentOS 8 已 EOL（重要）

CentOS 8 已停止官方维护（安全更新停止）。从“稳定运维体系”角度，建议后续迁移到：

- Rocky Linux 8/9
- AlmaLinux 8/9
- Alibaba Cloud Linux 3

短期不迁移也能用，但要意识到：系统层漏洞不会再有官方修复。

## 2) Docker 安装建议

- 使用官方 Docker Engine + compose 插件
- 配置 Docker 开机自启
- 建议将 Docker 的数据目录放到大数据盘（如果你的系统盘较小）

## 3) SELinux / 防火墙

- 若开启 SELinux，容器挂载宿主机目录可能需要额外标签/权限配置（否则会出现“能启动但读写失败”）
- Firewalld 建议只放行内网需要的端口（例如 8080/8001/RAGFlow 端口）

## 4) 磁盘与文件系统

- 建议使用 XFS/EXT4，数据盘单独挂载（例如 `/data`）
- RAGFlow 的 ES/MinIO 强烈依赖磁盘空间与 IOPS：
  - 爆盘会导致写入失败/索引异常，属于高危故障

## 5) 变更管理建议

- 任何更新前先做迁移包备份（`migration_pack_...`）
- 不使用 `docker compose down -v`
- 每周至少一次抽样恢复演练（见 `doc/maintenance/07_daily_checklist.md`）

