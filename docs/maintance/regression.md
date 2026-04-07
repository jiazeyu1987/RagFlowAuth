# 回归

## 文档范围

这里的“回归”对应维护工具里已经落地的只读验证能力，核心是冒烟检查与发布前后 `base_url` 守卫，不等于完整的业务 E2E。

事实来源主要包括：

- `tool/maintenance/features/smoke_test.py`
- `tool/maintenance/core/ragflow_base_url_guard.py`
- `tool/maintenance/ui/smoke_tab.py`
- `tool/maintenance/controllers/release/publish_local_worker_ops.py`
- `tool/maintenance/controllers/release/publish_test_worker_ops.py`
- `tool/maintenance/controllers/release/publish_data_worker_ops.py`

## 回归验证覆盖的两台服务器

| 环境 | IP | 验证关注点 |
| --- | --- | --- |
| 测试服务器 | `172.30.30.58` | 本机发布后是否可用、数据同步后是否仍指向测试 RAGFlow |
| 正式服务器 | `172.30.30.57` | 镜像发布或数据覆盖后是否仍指向正式 RAGFlow、容器与接口是否存活 |

关键访问点：

- 前端：`http://127.0.0.1:3001/`
- 后端健康检查：`http://127.0.0.1:8001/health`
- RAGFlow：`http://127.0.0.1:9380/`

## Base URL 守卫

`tool/maintenance/core/ragflow_base_url_guard.py` 为三种角色定义了固定期望值：

- local: `http://127.0.0.1:9380`
- test: `http://172.30.30.58:9380`
- prod: `http://172.30.30.57:9380`

当前维护工具在这些时机会触发守卫：

- 本机 -> 测试发布前
- 测试 -> 正式（镜像）发布前后
- 测试 -> 正式（数据）发布前后
- 本机备份同步到测试后

作用不是“兼容错误配置”，而是尽快把环境拉回到该环境应读的 RAGFlow 地址，避免测试服误读正式数据，或正式服误读测试数据。

## 冒烟检查做了什么

`feature_run_smoke_test()` 当前执行的检查项如下：

| 检查项 | 命令类型 | 是否硬失败 |
| --- | --- | --- |
| docker 可用性 | `docker --version` | 是 |
| 容器状态快照 | `docker ps` | 是 |
| 后端健康检查 | `curl http://127.0.0.1:8001/health` | 是 |
| 前端 HTTP 状态 | `curl http://127.0.0.1:3001/` | 否 |
| RAGFlow HTTP 状态 | `curl http://127.0.0.1:9380/` | 否 |
| `/mnt/replica` 挂载与磁盘 | `mount` + `df` | 否 |
| `/opt/ragflowauth` 磁盘空间 | `df -h /opt/ragflowauth` | 否 |

代码里的判定细节：

- 前端与 RAGFlow 只把 `200`、`301`、`302` 当成“up”。
- `/mnt/replica` 只要能从输出中识别到挂载点或 `type cifs` 就算通过。
- 真正影响总结果的是硬失败项，也就是 docker、容器状态和后端健康检查。

这意味着：

- 冒烟失败通常先看 docker、容器和后端。
- 前端、RAGFlow、挂载、磁盘更多是运维诊断补充，而不是唯一的总失败条件。

## UI 里的回归入口

`tool/maintenance/ui/smoke_tab.py` 暴露了三个按钮：

1. 运行测试服冒烟
2. 运行正式服冒烟
3. 运行当前下拉框所选服务器的冒烟

UI 文案明确说明这组操作是“只读检查”，不会修改服务器数据。

## 建议的发布后回归顺序

这不是仓库里的新自动化，而是从现有工具能力反推出的最小核对顺序：

1. 刷新 `base_url` 显示，先确认测试服和正式服都仍指向自己。
2. 如果刚执行了“本机 -> 测试”，先对测试服运行一次冒烟。
3. 如果刚执行了“测试 -> 正式（镜像）”，对正式服运行一次冒烟。
4. 如果刚执行了“测试 -> 正式（数据）”，除了正式服冒烟，还要再次确认正式服 `base_url` 没被错误覆盖。
5. 查看发布页签里的版本信息和发布日志，确认前后版本变化符合预期。

## 当前回归能力的边界

这套回归能力当前没有覆盖以下内容：

- 真实用户业务流
- ONLYOFFICE 端到端文档打开与编辑
- SMTP、站内通知等外围集成
- 更深层的权限或多租户业务验证

也就是说，当前“回归”更准确地说是“发布后只读冒烟 + 配置隔离守卫”，而不是完整的产品回归测试。

## 运维注意事项

- 不要把“冒烟通过”理解成“业务全链路通过”。
- 如果 `base_url` 守卫在发布前后连续触发，优先处理配置隔离问题，再看容器健康。
- 文档保留了测试服和正式服的 IP、端口与固定路径，但没有复制任何敏感凭据。
