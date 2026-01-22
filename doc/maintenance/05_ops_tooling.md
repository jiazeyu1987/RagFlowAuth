# 05 推荐的开源运维工具

目标：运维人员能“看状态、看日志、重启、更新、回滚”，且学习成本低。

## 1) Portainer CE（推荐）

用途：

- Web 界面管理 Docker：容器状态、重启、日志、卷、网络

仓库：

- https://github.com/portainer/portainer

建议：

- 内网部署，限制访问网段

## 2) 远程管理 Docker（SSH 方式）

Docker 自带支持通过 SSH 管远程 Docker（无需暴露 2375/2376）。

适用：

- 你在自己电脑上通过 SSH 连接服务器，查看容器状态、执行 compose

## 3) 监控/告警（可选）

稳定优先建议至少监控：

- CPU/RAM
- 磁盘容量（尤其 ES/MinIO）
- 容器重启次数

常见组合：

- Prometheus + Grafana + Alertmanager
- Loki + Grafana（日志）

