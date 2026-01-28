# 大文件传输问题解决方案

## 问题描述

在使用 tool.py 还原备份时，上传 9GB 的 images.tar 文件失败，错误信息：
```
[ERROR] 上传 images.tar 失败: Connection to 172.30.30.57 closed by remote host
scp: Couldn't send packet: Broken pipe
```

## 根本原因

1. **网络超时**：传输大文件（9GB）需要3-5分钟，超过网络设备的超时限制
2. **无断点续传**：SCP 传输中断后必须重新开始
3. **SSH Keepalive 未配置**：服务器未发送 keepalive 包保持连接活跃

## 解决方案

### ✅ 方案1：已修复 tool.py（推荐）

**修改内容**：
- 使用 rsync 替代 scp（支持断点续传）
- 添加自动重试机制（最多3次）
- 添加 SSH keepalive 选项（`ServerAliveInterval=15`）
- 设置30分钟超时

**位置**：[tool.py:1170-1238](../tool.py#L1170-L1238)

### ✅ 方案2：SSH Keepalive 已配置

**服务器配置**：
```bash
# /etc/ssh/sshd_config
ClientAliveInterval 15
ClientAliveCountMax 3
```

**说明**：
- 每15秒发送一次 keepalive 包
- 最多发送3次（总共45秒无响应才断开）

### ✅ 方案3：手动上传脚本（备用）

**使用方法**：
```powershell
# 上传 images.tar
.\tool\scripts\upload-large-file.ps1 -LocalFile "dist\backup\images.tar"

# 上传其他文件
.\tool\scripts\upload-large-file.ps1 -LocalFile "path\to\file.tar" -RemotePath "/tmp/file.tar"
```

**功能**：
- 自动重试（最多5次）
- 进度显示
- 文件验证
- 错误诊断

## 验证修复

### 测试自动还原

1. 打开 `tool.py`
2. 进入"数据还原"页签
3. 选择备份文件夹
4. 勾选"images"
5. 点击"开始还原"

### 手动测试上传

```powershell
# 测试上传一个小文件
.\tool\scripts\upload-large-file.ps1 -LocalFile "tool\scripts\ensure-env.sh" -RemotePath "/tmp/test.sh"

# 测试上传大文件
.\tool\scripts\upload-large-file.ps1 -LocalFile "dist\backup\images.tar"
```

## 其他建议

### 1. 分卷备份（超大文件）

如果文件超过10GB，考虑分卷压缩：

```bash
# 分卷压缩
split -b 2G images.tar images.tar.part

# 分卷上传
for part in images.tar.part*; do
  rsync -avz -e "ssh -o BatchMode=yes" $part root@172.30.30.57:/var/lib/docker/tmp/
done

# 服务器端合并
cat /var/lib/docker/tmp/images.tar.part* > /var/lib/docker/tmp/images.tar
```

### 2. 使用本地 NFS/SMB

如果网络持续不稳定：

1. **挂载 Windows 共享到服务器**：
   ```bash
   # 在服务器上挂载 Windows 共享
   mount -t cifs //192.168.112.72/backup /mnt/backup -o username=user,password=pass

   # 直接复制文件
   cp /mnt/backup/migration_pack_*/images.tar /var/lib/docker/tmp/
   ```

2. **使用 NFS**：
   ```bash
   # Windows 上安装 NFS 服务
   # 服务器上挂载
   mount -t nfs <Windows IP>:/path/to/files /mnt/nfs
   ```

### 3. 减小备份大小

**方法1：排除 images**
```python
# 在 tool.py 中还原时，不勾选"images"选项
# 只还原 auth.db, uploads, volumes
```

**方法2：使用增量备份**
```python
# 在数据安全页面选择"增量备份"模式
# 只备份 auth.db，不包含 images 和 volumes
```

## 故障排查

### 检查网络稳定性

```bash
# 测试带宽和延迟
ping 172.30.30.57
iperf3 -c 172.30.30.57 -t 60

# 检查丢包
ping -c 1000 172.30.30.57 | grep "packet loss"
```

### 检查服务器资源

```bash
ssh root@172.30.30.57

# 磁盘空间
df -h /var/lib/docker

# 内存
free -h

# Docker 状态
docker ps
docker system df
```

### 查看详细日志

```bash
# tool.py 日志
type data\restore.log | Select-String "images"

# SSH 日志
ssh root@172.30.30.57 "journalctl -u sshd -n 50"
```

## 性能优化

### 1. 压缩传输（对已压缩文件效果不大）

```bash
rsync -avzz -e "ssh -o BatchMode=yes" images.tar root@172.30.30.57:/var/lib/docker/tmp/
```

### 2. 限制带宽（避免占满网络）

```bash
rsync -avz --bwlimit=10m -e "ssh -o BatchMode=yes" images.tar root@172.30.30.57:/var/lib/docker/tmp/
```

### 3. 并行传输（分卷场景）

```bash
# 同时上传多个分卷
for part in images.tar.part*; do
  rsync -avz -e "ssh -o BatchMode=yes" $part root@172.30.30.57:/var/lib/docker/tmp/ &
done
wait
```

## 联系支持

如果问题持续：
1. 收集日志：`data\restore.log`
2. 网络测试结果
3. 服务器资源状态
