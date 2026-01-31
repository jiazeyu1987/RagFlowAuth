# 备份与挂载（关键逻辑锁定说明）

目的：把“备份 + 复制到 Windows + 挂载”这条链路的**不变量**、关键路径、日志定位方式写清楚，避免后续改动导致备份/挂载静默失效。

本目录文档面向未来维护者（包含 LLM 修改代码时的约束）。如涉及账号/密码等敏感信息，统一参考：`doc/maintenance/current/server_config.md`。

---

## 一句话总结

1. **备份**由后端定时/手动触发，生成 `migration_pack_...` 目录。
2. **复制到 Windows**不是走 UNC 路径，而是要求服务器把 Windows 共享以 CIFS 挂载到 **固定挂载点** `/mnt/replica`，并把备份复制到 **固定目录** `/mnt/replica/RagflowAuth`。
3. 挂载/卸载/检查由 `tool/maintenance/tool.py` 通过 PowerShell 脚本 SSH 到服务器执行。

---

## 目录索引

- `doc/function/backup/backup_flow.md`：备份与复制（后端 + 定时）详细流程与关键不变量
- `doc/function/backup/mount_flow.md`：挂载/卸载/检查（tool.py + ps1）详细流程与关键不变量
- `doc/function/backup/troubleshooting.md`：第二天没有备份时，如何用日志定位原因（逐步排查）

