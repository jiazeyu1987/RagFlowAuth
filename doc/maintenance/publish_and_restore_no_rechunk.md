# 发布/还原后“立刻可用且不重拆 chunk”——两条硬规则（SOP）

本文把经验结论写成可执行流程，目标是：  
**发布到测试/正式后，RAGFlow 数据可直接检索与引用，不需要重新“拆分 chunk/重建索引”。**

> 重要背景：  
> RAGFlow 的检索可用性依赖三类数据同时一致：
> - 元数据（通常在 `ragflow_compose_mysql_data`）
> - 文档原文对象（通常在 `ragflow_compose_minio_data`）
> - 向量/索引（通常在 `ragflow_compose_esdata01`）
>
> 只要其中任意一块缺失/不一致，就会出现“看得到数据集/文档，但检索/引用找不到 chunk”，从而表现为“必须重拆 chunk 才能识别”。

---

## 规则 1：LOCAL → TEST 仅发布镜像不够，必须保证 TEST 的 RAGFlow 数据与目标一致

### 结论
如果你希望 **LOCAL → TEST 发布后立刻可用且不重拆**，那么在“发布镜像”之后必须满足下面条件之一：

1) **TEST 上本来就运行着正确的数据**（已是目标数据集、索引完好、版本/配置一致）；或  
2) **再做一次数据同步/还原**，把 RAGFlow 的关键数据面同步到 TEST（MySQL/MinIO/ES volumes）。

### 为什么
工具的“发布镜像”只会更新 `ragflowauth-backend/frontend`（应用层）。  
它**不会自动迁移** TEST 上的 RAGFlow 数据（`ragflow_compose_*` volumes）。  
因此 TEST 上的向量索引/元数据如果不是同一套，就会出现“检索不到/引用不到 chunk”，你重拆 chunk 实际是在 TEST 上重新生成派生数据使其匹配。

### 操作建议（非代码用户版）
- 发布镜像（LOCAL → TEST）后，若发现“检索/引用异常”：
  - 不要第一时间重拆 chunk；
  - 先确认 TEST 的 `ragflow_compose_*` volumes 是否与期望一致（是否来自同一套备份/同一环境）；
  - 必要时用工具的“数据还原（只到测试服务器）”把本机备份同步到 TEST。

### 工具已落地（推荐用法）
在工具的 **发布 → ① 本机 → 测试** 页签：
- 勾选：`发布后同步数据到测试（auth.db + RAGFlow volumes；覆盖测试数据）`
- （可选）在“选择备份”下拉框里选择要同步的 `migration_pack_*`；不选则默认最新
- 点击：`发布本机到测试`

工具会自动选择本机固定目录 `D:\datas\RagflowAuth` 下**最新**的 `migration_pack_*` 备份，把：
- `auth.db`
- `volumes/`（包含 `*_mysql_data`、`*_minio_data`、`*_esdata01` 等）
同步到测试服务器。

> 注意：此同步是“数据面”操作，**不会**还原 `images.tar`，避免覆盖刚发布的镜像版本。

---

## 规则 2：发布数据/还原时，必须“确实停干净”再打包/还原 ES volume（否则必然有概率要重建）

### 结论
对“测试数据发布到正式”或“本机备份还原到测试”，在处理以下内容之前：
- 打包 `ragflow_compose_*` volumes
- 还原 `ragflow_compose_esdata01`（ES 索引/向量）

必须保证：
- `ragflowauth-backend` / `ragflowauth-frontend` 已停止
- 所有 `ragflow_compose-*` 容器已停止

### 为什么（重点）
ES/Lucene 索引在运行时持续写入。  
如果容器仍在运行就对 `ragflow_compose_esdata01` 做快照（tar）或覆盖还原，会产生“逻辑不一致的索引快照”，恢复后常见症状：
- 数据集/文档列表还能看到（MySQL/MinIO 正常）
- 检索/引用为空或异常（ES 索引损坏/不一致）
- 只能通过“重拆 chunk/重建索引”修复

### 可执行检查（服务器上）
在打包/还原前执行：

- 查看是否还有相关容器在跑：
  - `docker ps --format '{{.Names}}' | grep -E '^(ragflowauth-(backend|frontend)|ragflow_compose-)' || true`
  - 期望输出为空

- 停止（推荐顺序）：
  - `docker stop ragflowauth-backend ragflowauth-frontend || true`
  - `cd /opt/ragflowauth/ragflow_compose && docker compose down || true`
  - `docker ps --format '{{.Names}}' | grep -E '^ragflow_compose-' | xargs -r docker stop || true`

### 工具侧已做的增强（避免误操作）
- `tool/maintenance/tool.py` 的“数据还原”流程已加入 **严格 stop + verify**：  
  - 校验 `ragflowauth-*` 与 `ragflow_compose-*` 容器全部停止后，才允许进入下一步还原。
  - 如果 90 秒内无法停干净会直接中止，并打印 `docker ps -a` 诊断信息。

---

## 快速判断：这次备份/还原是否“包含 chunk/索引数据”

只要备份目录里包含：
- `volumes/*_mysql_data.tar.gz`
- `volumes/*_minio_data.tar.gz`
- `volumes/*_esdata01.tar.gz`

就说明 **RAGFlow 的元数据 + 原文对象 + 向量索引**都被打包了（chunk/索引相关数据未遗漏）。
