# 工具页签：备份与还原（Backup/Restore）

更新日期：2026-02-01

工具：`tool/maintenance/tool.py`

重要约束（防呆）：
- “还原数据”**只允许还原到测试服务器**（TEST：`172.30.30.58`）
- 本地备份固定目录：`D:\datas\RagflowAuth`
- 还原时会自动校验/修正测试服务器 `ragflow_config.json.base_url` 指向 TEST（防止误读生产知识库）

本地日志：`tool/maintenance/tool_log.log`

---

## A. 备份管理（服务器备份管理）

页签：备份管理

用途：
- 查看服务器上的备份目录/空间占用
- 查看 Windows 共享上的备份（如果配置了自动复制/挂载）

常用操作（UI 按钮）：
- 查看最近的备份：列出服务器上最近生成的备份目录
- 查看备份磁盘使用：统计备份占用空间
- 查看 Windows 共享备份：查看同步到 Windows 共享目录中的备份

说明：
- 该页以“查看/管理”为主，真正触发备份通常在后端“数据安全”流程中完成

---

## B. 备份文件（服务器备份文件管理）

页签：备份文件

用途：
- 管理服务器上的备份文件（查看/删除/清理旧备份）
- 支持同时查看两个位置（历史原因可能分散在两个目录）

常用操作：
- 刷新列表：重新读取服务器备份目录
- 查看详情：显示某个备份包里的关键文件（例如是否包含 `replication_manifest.json`）
- 删除选中：删除指定备份
- 清空旧备份（30天前）：批量清理

排障建议：
- 如果发现“备份文件分散在两个目录”，优先以当前后端备份实现为准，并保持容器内可见路径一致

---

## C. 数据还原（只还原到 TEST）

页签：数据还原

目标：
- 从本地 `D:\datas\RagflowAuth` 选择一个备份目录，还原到测试服务器
- 还原内容：
  - 必选：`auth.db` + `volumes/`
  - 可选：`images.tar`（如果备份中存在，则一并还原镜像）
- 明确：按需求 **不还原 uploads**（避免误覆盖）

UI 结构：
- 本地备份列表：扫描 `D:\datas\RagflowAuth` 下的备份目录并显示
  - 显示列：备份时间（从目录名解析）、是否有 image 信息
- 开始还原数据：执行还原（会弹确认框）
- 还原日志：显示每一步的执行输出

还原核心流程（工具内部摘要）：
1) 停止 TEST 上的相关容器
2) 备份 TEST 当前数据（用于回滚）
3) 上传并替换 `auth.db`
4) 如存在 `images.tar`：在 TEST `docker load`（保证 ragflowauth 镜像存在）
5) 还原 RAGFlow volumes：
   - 将本地 `volumes/` 打包上传
   - 在 TEST 停止 RAGFlow compose（防写入冲突）
   - 使用临时容器把 tar.gz 解到对应 docker volume
6) 重启服务并验证：
   - RAGFlow compose 启动
   - RagflowAuth 容器启动并健康检查

常见失败与建议处理：
- 备份不包含 `images.tar` 且测试机没有 ragflowauth 镜像、同时服务器不能访问外网拉取镜像：
  - 会出现 `Unable to find image ...` + `Get https://registry-1.docker.io ... timeout`
  - 解决：先在“发布”页签执行【本机 -> 测试】发布镜像，再做还原
