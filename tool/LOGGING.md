# tool.py 日志系统说明

## 概述

`tool.py` 现在包含一个全面的日志系统，将所有操作、输出、错误和调试信息记录到 `tool_log.log` 文件中。

## 日志文件位置

```
d:\ProjectPackage\RagflowAuth\tool_log.log
```

日志文件与 `tool.py` 位于同一目录。

## 日志格式

每条日志记录包含时间戳、日志级别和消息：

```
2026-01-27 14:30:45 [INFO] RagflowAuth 工具启动
2026-01-27 14:30:45 [INFO] UI 初始化完成，默认服务器: root@172.30.30.57
2026-01-27 14:31:12 [INFO] [TOOL] Connection successful
```

## 日志级别

- **DEBUG**: 详细的调试信息（SSH 命令、文件操作等）
- **INFO**: 一般信息（配置保存、连接测试、操作完成等）
- **WARNING**: 警告信息（无效的 URL、缺失的文件等）
- **ERROR**: 错误信息（连接失败、命令执行失败、还原失败等）

## 记录的内容

### 1. 应用启动

```
================================================================================
RagflowAuth 工具启动
日志文件: d:\ProjectPackage\RagflowAuth\tool_log.log
================================================================================
```

### 2. 配置操作

- 配置加载成功/失败
- 配置保存操作
- 连接测试结果

### 3. SSH 命令执行

所有 SSH 命令都会被记录：

```
2026-01-27 14:31:00 [DEBUG] [SSH] 执行命令: docker ps
2026-01-27 14:31:01 [DEBUG] [SSH] 命令执行成功
```

失败的命令会记录详细错误：

```
2026-01-27 14:32:00 [ERROR] [SSH] 命令执行失败 (返回码: 1)
2026-01-27 14:32:00 [ERROR] [SSH] 错误输出: Error: No such container
```

### 4. 工具执行

- Docker 镜像清理
- 容器快速重启
- 日志查看操作

```
2026-01-27 14:33:00 [INFO] [TOOL] Connection successful
2026-01-27 14:33:05 [INFO] [SSH-CMD] ragflowauth-backend
```

### 5. URL 访问

```
2026-01-27 14:34:00 [INFO] [URL] 打开自定义 URL: http://172.30.30.57:3001
```

### 6. 数据还原操作

完整记录数据还原的每个步骤：

```
2026-01-27 14:35:00 [INFO] [RESTORE] 选择备份文件夹: D:\datas\RagflowAuth\backup-2026-01-27
2026-01-27 14:35:01 [INFO] [RESTORE] 备份验证结果:
✅ 找到数据库: 2.45 MB
✅ 找到 uploads 目录: 1234 个文件
✅ 找到 Docker 镜像: 1250.00 MB
✅ 找到 RAGFlow 数据 (volumes): 5678 个文件

2026-01-27 14:36:00 [INFO] [RESTORE] 用户确认还原操作
2026-01-27 14:36:00 [INFO] [RESTORE] 源文件夹: D:\datas\RagflowAuth\backup-2026-01-27
2026-01-27 14:36:00 [INFO] [RESTORE] 目标服务器: root@172.30.30.57
2026-01-27 14:36:00 [INFO] [RESTORE] 还原内容: RagflowAuth 数据 和 Docker 镜像 和 RAGFlow 数据 (volumes)

2026-01-27 14:36:10 [INFO] [RESTORE-STATUS] 正在停止容器...
2026-01-27 14:36:15 [INFO] [RESTORE]   停止 RagflowAuth 容器...
2026-01-27 14:36:20 [INFO] [RESTORE]   ✅ 容器已停止

2026-01-27 14:37:00 [INFO] [RESTORE] images.tar 上传完成: 1250.00 MB 用时 45.2 秒 (27.65 MB/s)
2026-01-27 14:38:00 [INFO] [RESTORE] volumes.tar.gz 上传完成: 234.56 MB 用时 12.3 秒 (19.07 MB/s)
```

### 7. 文件上传性能

记录文件上传的详细信息：

- 文件大小（MB）
- 上传耗时（秒）
- 上传速度（MB/s）

```
2026-01-27 14:37:00 [INFO] [RESTORE] images.tar 上传完成: 1250.00 MB 用时 45.2 秒 (27.65 MB/s)
```

### 8. 异常和错误

所有异常都会被记录，包括完整的堆栈跟踪：

```
2026-01-27 14:40:00 [ERROR] [RESTORE] 还原失败: 上传 images.tar 失败: Permission denied
```

未捕获的异常会记录完整的堆栈跟踪：

```
2026-01-27 14:41:00 [ERROR] 未捕获的异常: division by zero
Traceback (most recent call last):
  File "tool.py", line 1234, in some_function
    result = x / 0
ZeroDivisionError: division by zero
```

## 查看日志

### 实时查看日志（Windows PowerShell）

```powershell
Get-Content tool_log.log -Wait -Tail 50
```

### 查看最近的错误

```powershell
Select-String -Path tool_log.log -Pattern "\[ERROR\]" | Select-Object -Last 20
```

### 查看今天的日志

```powershell
Get-Content tool_log.log | Select-String -Pattern "^2026-01-27"
```

## 日志文件管理

### 日志轮转

日志文件以追加模式写入（`mode='a'`），不会自动删除旧日志。

建议定期清理或归档日志文件：

```powershell
# 归档当前日志
Rename-Item -Path tool_log.log -NewName "tool_log_2026-01-27.log"

# 或直接删除
Remove-Item tool_log.log
```

### 日志文件大小

由于日志包含详细的 SSH 命令和文件操作信息，日志文件可能会随时间增长。建议：

1. 每月归档一次日志
2. 或当日志文件超过 10 MB 时清理

## 调试问题

当遇到问题时，检查 `tool_log.log` 文件可以：

1. **追踪 SSH 命令执行**：查看哪些命令被执行，返回结果是什么
2. **诊断网络问题**：查看文件上传速度和耗时
3. **定位错误原因**：查看完整的错误消息和堆栈跟踪
4. **审计操作历史**：查看谁在什么时候执行了什么操作

## 示例：排查还原失败问题

如果数据还原失败，按以下步骤查看日志：

1. **查找错误**：
   ```powershell
   Select-String -Path tool_log.log -Pattern "\[ERROR\]" | Select-Object -Last 10
   ```

2. **查看还原过程**：
   ```powershell
   Select-String -Path tool_log.log -Pattern "\[RESTORE\]" | Select-Object -Last 50
   ```

3. **检查上传性能**：
   ```powershell
   Select-String -Path tool_log.log -Pattern "上传完成" | Select-Object -Last 10
   ```

4. **查看 SSH 命令**：
   ```powershell
   Select-String -Path tool_log.log -Pattern "\[SSH\]" | Select-Object -Last 20
   ```

## 注意事项

1. **日志文件权限**：确保运行 tool.py 的用户对 tool_log.log 有读写权限
2. **敏感信息**：日志中可能包含服务器 IP 和路径信息，但不包含密码
3. **编码**：日志文件使用 UTF-8 编码，支持中文字符
4. **性能影响**：日志记录对性能影响极小（< 1%）

## 配置日志级别

如需修改日志级别，编辑 `tool.py` 中的日志配置：

```python
# 仅记录 INFO 及以上级别（减少日志量）
logger.setLevel(logging.INFO)

# 或记录所有级别（包括 DEBUG）
logger.setLevel(logging.DEBUG)
```

## 相关文件

- `tool.py` - 主程序，包含日志系统
- `tool_log.log` - 日志文件（自动生成）
- `tool/LOGGING.md` - 本说明文档
