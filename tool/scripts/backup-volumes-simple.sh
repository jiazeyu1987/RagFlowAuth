#!/bin/sh

echo "=== RAGFlow Volumes 手动备份到 Windows ==="
echo ""

# 配置
BACKUP_DIR="/opt/ragflowauth/backups/manual_$(date +%Y%m%d_%H%M%S)"
REPLICA_DIR="/mnt/replica/RagflowAuth"

echo "备份目录: $BACKUP_DIR"
echo "目标目录: $REPLICA_DIR"
echo ""

# 创建目录
mkdir -p "$BACKUP_DIR"
mkdir -p "$REPLICA_DIR"
mkdir -p "$BACKUP_DIR/volumes"

# 备份 auth.db
echo "1. 备份 auth.db..."
cp /opt/ragflowauth/data/auth.db "$BACKUP_DIR/"
echo "✓ auth.db 已备份"

# 备份 volumes
echo ""
echo "2. 备份 RAGFlow volumes..."
count=0

# esdata01
echo "  备份 ragflow_compose_esdata01 ..."
if docker run --rm \
    -v "ragflow_compose_esdata01:/data:ro" \
    -v "${BACKUP_DIR}/volumes:/backup" \
    ragflowauth-backend:local \
    tar czf "/backup/ragflow_compose_esdata01.tar.gz" -C /data . 2>/dev/null; then
    size=$(du -h "${BACKUP_DIR}/volumes/ragflow_compose_esdata01.tar.gz" | cut -f1)
    echo "  ✓ ragflow_compose_esdata01 备份成功 ($size)"
    count=$((count + 1))
else
    echo "  ✗ ragflow_compose_esdata01 备份失败"
fi

# minio_data
echo "  备份 ragflow_compose_minio_data ..."
if docker run --rm \
    -v "ragflow_compose_minio_data:/data:ro" \
    -v "${BACKUP_DIR}/volumes:/backup" \
    ragflowauth-backend:local \
    tar czf "/backup/ragflow_compose_minio_data.tar.gz" -C /data . 2>/dev/null; then
    size=$(du -h "${BACKUP_DIR}/volumes/ragflow_compose_minio_data.tar.gz" | cut -f1)
    echo "  ✓ ragflow_compose_minio_data 备份成功 ($size)"
    count=$((count + 1))
else
    echo "  ✗ ragflow_compose_minio_data 备份失败"
fi

# mysql_data
echo "  备份 ragflow_compose_mysql_data ..."
if docker run --rm \
    -v "ragflow_compose_mysql_data:/data:ro" \
    -v "${BACKUP_DIR}/volumes:/backup" \
    ragflowauth-backend:local \
    tar czf "/backup/ragflow_compose_mysql_data.tar.gz" -C /data . 2>/dev/null; then
    size=$(du -h "${BACKUP_DIR}/volumes/ragflow_compose_mysql_data.tar.gz" | cut -f1)
    echo "  ✓ ragflow_compose_mysql_data 备份成功 ($size)"
    count=$((count + 1))
else
    echo "  ✗ ragflow_compose_mysql_data 备份失败"
fi

# redis_data
echo "  备份 ragflow_compose_redis_data ..."
if docker run --rm \
    -v "ragflow_compose_redis_data:/data:ro" \
    -v "${BACKUP_DIR}/volumes:/backup" \
    ragflowauth-backend:local \
    tar czf "/backup/ragflow_compose_redis_data.tar.gz" -C /data . 2>/dev/null; then
    size=$(du -h "${BACKUP_DIR}/volumes/ragflow_compose_redis_data.tar.gz" | cut -f1)
    echo "  ✓ ragflow_compose_redis_data 备份成功 ($size)"
    count=$((count + 1))
else
    echo "  ✗ ragflow_compose_redis_data 备份失败"
fi

echo ""
echo "3. 复制到 Windows 共享..."
if cp -r "$BACKUP_DIR"/* "$REPLICA_DIR/"; then
    echo "✓ 已复制到 $REPLICA_DIR"
else
    echo "✗ 复制失败"
    exit 1
fi

echo ""
echo "=== 备份完成 ==="
echo "成功备份 $count 个volume"
echo ""
echo "本地备份: $BACKUP_DIR"
echo "Windows副本: $REPLICA_DIR"
echo ""
echo "Windows路径: \\\\192.168.112.72\\backup\\RagflowAuth"
