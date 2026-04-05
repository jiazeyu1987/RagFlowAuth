#!/bin/bash
# RAGFlow 数据还原脚本
# 用途：从备份包中还原 RAGFlow 的 Docker volumes

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${CYAN}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "  $1"
}

# 检查参数
if [ $# -lt 1 ]; then
    echo "用法: $0 <backup_pack_directory> [ragflow_compose_dir]"
    echo ""
    echo "示例:"
    echo "  $0 /opt/ragflowauth/backups/migration_pack_20260127_150556"
    echo "  $0 /opt/ragflowauth/backups/migration_pack_20260127_150556 /opt/ragflowauth/ragflow_compose"
    echo ""
    exit 1
fi

BACKUP_DIR="$1"
COMPOSE_DIR="${2:-/opt/ragflowauth/ragflow_compose}"

# 验证备份目录
if [ ! -d "$BACKUP_DIR" ]; then
    print_error "备份目录不存在: $BACKUP_DIR"
    exit 1
fi

if [ ! -d "$BACKUP_DIR/volumes" ]; then
    print_error "备份目录中没有 volumes 子目录: $BACKUP_DIR/volumes"
    exit 1
fi

if [ ! -f "$COMPOSE_DIR/docker-compose.yml" ]; then
    print_error "Docker Compose 文件不存在: $COMPOSE_DIR/docker-compose.yml"
    exit 1
fi

echo ""
print_step "RAGFlow 数据还原"
echo ""
print_info "备份目录: $BACKUP_DIR"
print_info "Compose 目录: $COMPOSE_DIR"
echo ""

# 步骤 1: 停止 RAGFlow 服务
print_step "步骤 1/5: 停止 RAGFlow 服务"
cd "$COMPOSE_DIR"
docker compose down
print_success "RAGFlow 服务已停止"
echo ""

# 步骤 2: 清理旧的 volumes (可选)
read -p "是否清理旧的 RAGFlow volumes? (这会删除当前所有RAGFlow数据) [y/N]: " confirm
if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    print_step "步骤 2/5: 清理旧 volumes"
    docker volume rm ragflow_compose_mysql_data ragflow_compose_minio_data ragflow_compose_esdata01 ragflow_compose_redis_data 2>/dev/null || true
    print_success "旧 volumes 已清理"
    echo ""
else
    print_step "步骤 2/5: 保留现有 volumes"
    print_info "警告: 如果 volumes 已存在，还原可能会覆盖部分文件"
    echo ""
fi

# 步骤 3: 还原 volumes
print_step "步骤 3/5: 还原 RAGFlow volumes"

VOLUME_COUNT=0
for backup_file in "$BACKUP_DIR"/volumes/*.tar.gz; do
    if [ -f "$backup_file" ]; then
        # 提取 volume 名称 (去掉 .tar.gz 后缀和时间戳)
        filename=$(basename "$backup_file")
        volume_name=${filename%.tar.gz}

        print_info "还原 volume: $volume_name"

        # 创建临时容器用于解压
        docker run --rm \
            -v "$volume_name:/data" \
            -v "$BACKUP_DIR:/backup" \
            alpine sh -c "
                cd /data && \
                tar -xzf /backup/volumes/$filename -C /data && \
                echo '  解压成功' || echo '  解压失败 (可能为空目录)'
            "

        ((VOLUME_COUNT++))
    fi
done

print_success "已还原 $VOLUME_COUNT 个 volumes"
echo ""

# 步骤 4: 验证还原结果
print_step "步骤 4/5: 验证还原结果"
docker volume ls | grep ragflow_compose
echo ""

# 步骤 5: 启动 RAGFlow 服务
print_step "步骤 5/5: 启动 RAGFlow 服务"
cd "$COMPOSE_DIR"
docker compose up -d
print_success "RAGFlow 服务已启动"
echo ""

# 等待服务健康
print_info "等待服务启动 (约30秒)..."
sleep 30

echo ""
docker compose ps
echo ""

print_success "RAGFlow 数据还原完成！"
echo ""
print_info "提示:"
print_info "1. 检查知识库数据是否正确"
print_info "2. 检查用户数据是否完整"
print_info "3. 如有问题，查看容器日志: docker compose logs -f"
