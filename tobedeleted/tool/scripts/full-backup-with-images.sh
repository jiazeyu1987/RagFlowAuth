#!/bin/sh

echo "=== RAGFlow 完整备份（含镜像）到 Windows ==="
echo ""

# 配置
BACKUP_DIR="/opt/ragflowauth/backups/manual_$(date +%Y%m%d_%H%M%S)"
REPLICA_DIR="/mnt/replica/RagflowAuth"
COMPOSE_FILE="/opt/ragflowauth/ragflow_compose/docker-compose.yml"

echo "备份目录: $BACKUP_DIR"
echo "目标目录: $REPLICA_DIR"
echo ""

# 创建目录
mkdir -p "$BACKUP_DIR/volumes"
mkdir -p "$REPLICA_DIR"

# 1. 备份 auth.db
echo "1. 备份 auth.db..."
cp /opt/ragflowauth/data/auth.db "$BACKUP_DIR/"
echo "✓ auth.db 已备份"

# 2. 备份 volumes
echo ""
echo "2. 备份 RAGFlow volumes..."
VOLUMES=$(docker volume ls --format '{{.Name}}' | grep 'ragflow_compose')
count=0
for vol in $VOLUMES; do
    echo "  备份 $vol ..."
    if docker run --rm \
        -v "${vol}:/data:ro" \
        -v "${BACKUP_DIR}/volumes:/backup" \
        ragflowauth-backend:2025-01-25-scheduler-fix-v2 \
        tar czf "/backup/${vol}.tar.gz" -C /data . 2>/dev/null; then
        size=$(du -h "$BACKUP_DIR/volumes/${vol}.tar.gz" | cut -f1)
        echo "  ✓ $vol 备份成功 ($size)"
        count=$((count + 1))
    else
        echo "  ✗ $vol 备份失败"
    fi
done
echo "  成功备份 $count 个volume"

# 3. 备份 Docker 镜像
echo ""
echo "3. 备份 Docker 镜像（可能需要几分钟）..."
IMAGES=$(cd /opt/ragflowauth/ragflow_compose && docker compose -f "$COMPOSE_FILE" config --images 2>/dev/null | sort | uniq)
image_count=$(echo "$IMAGES" | grep -c .)
echo "  找到 $image_count 个镜像"

if docker save -o "$BACKUP_DIR/images.tar" $IMAGES 2>/dev/null; then
    size=$(du -h "$BACKUP_DIR/images.tar" | cut -f1)
    echo "  ✓ 镜像备份成功 ($size)"
else
    echo "  ✗ 镜像备份失败"
fi

# 4. 复制到 Windows 共享
echo ""
echo "4. 复制到 Windows 共享..."
if cp -r "$BACKUP_DIR"/* "$REPLICA_DIR/"; then
    echo "✓ 已复制到 $REPLICA_DIR"
else
    echo "✗ 复制失败"
    exit 1
fi

echo ""
echo "=== 备份完成 ==="
echo ""
echo "本地备份: $BACKUP_DIR"
echo "Windows副本: $REPLICA_DIR"
echo ""
echo "Windows路径: \\\\192.168.112.72\\backup\\RagflowAuth"
echo ""
echo "备份内容:"
echo "  - auth.db"
echo "  - volumes/*.tar.gz (4个RAGFlow数据卷)"
echo "  - images.tar ($image_count个Docker镜像)"
