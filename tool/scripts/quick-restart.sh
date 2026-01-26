#!/bin/bash
# RagflowAuth 快速重启脚本
# 用途：重启容器（不重新构建镜像，仅加载新镜像并重启）
# 适用场景：镜像已通过其他方式传输到服务器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_step() {
    echo -e "${CYAN}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "  $1"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 默认参数
TAG="${TAG:-production}"
DATA_DIR="${DATA_DIR:-/opt/ragflowauth}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
CLEANUP_IMAGES="${CLEANUP_IMAGES:-true}"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            TAG="$2"
            shift 2
            ;;
        --no-cleanup)
            CLEANUP_IMAGES=false
            shift
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --tag TAG         镜像标签 (默认: production)"
            echo "  --no-cleanup      不清理旧镜像"
            echo "  --help            显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                           # 使用 production tag"
            echo "  $0 --tag 2025-01-26-snapshot # 使用指定 tag"
            echo "  $0 --no-cleanup              # 不清理旧镜像"
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

print_step "RagflowAuth 快速重启"
echo ""
print_info "镜像标签: $TAG"
print_info "清理旧镜像: $CLEANUP_IMAGES"
echo ""

# 检查镜像是否存在
print_step "检查镜像"
if ! docker images | grep -q "ragflowauth-backend.*$TAG"; then
    print_error "未找到镜像: ragflowauth-backend:$TAG"
    print_info "请先加载镜像: docker load -i /path/to/images.tar"
    exit 1
fi

if ! docker images | grep -q "ragflowauth-frontend.*$TAG"; then
    print_error "未找到镜像: ragflowauth-frontend:$TAG"
    print_info "请先加载镜像: docker load -i /path/to/images.tar"
    exit 1
fi

print_success "镜像检查通过"
echo ""

# 停止并删除旧容器
print_step "停止旧容器"
docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true
docker rm ragflowauth-backend ragflowauth-frontend 2>/dev/null || true
print_success "旧容器已清理"
echo ""

# 启动后端
print_step "启动后端容器"
docker run -d \
  --name ragflowauth-backend \
  --network ragflowauth-network \
  -p "${BACKEND_PORT}:8001" \
  -v "$DATA_DIR/data:/app/data" \
  -v "$DATA_DIR/uploads:/app/uploads" \
  -v "$DATA_DIR/ragflow_config.json:/app/ragflow_config.json:ro" \
  -v "$DATA_DIR/backup_config.json:/app/backup_config.json:ro" \
  -v "$DATA_DIR/ragflow_compose:/app/ragflow_compose:ro" \
  -v /mnt/replica:/mnt/replica \
  -v /var/run/docker.sock:/var/run/docker.sock \
  "ragflowauth-backend:$TAG"

if [ $? -eq 0 ]; then
    print_success "后端容器已启动"
else
    print_error "后端容器启动失败"
    exit 1
fi

# 启动前端
print_step "启动前端容器"
docker run -d \
  --name ragflowauth-frontend \
  --network ragflowauth-network \
  -p 3001:80 \
  --link ragflowauth-backend:backend \
  "ragflowauth-frontend:$TAG"

if [ $? -eq 0 ]; then
    print_success "前端容器已启动"
else
    print_error "前端容器启动失败"
    exit 1
fi

echo ""

# 等待容器启动
print_step "等待容器启动"
sleep 3

# 检查容器状态
print_step "检查容器状态"
echo ""
docker ps | grep ragflowauth
echo ""

# 清理旧镜像（可选）
if [ "$CLEANUP_IMAGES" = true ]; then
    if [ -f "/tmp/cleanup-images.sh" ]; then
        print_step "清理旧镜像"
        /tmp/cleanup-images.sh --keep 2
        echo ""
    else
        print_warn "清理脚本不存在，跳过镜像清理"
    fi
fi

# 显示访问信息
SERVER_IP=$(hostname -I | awk '{print $1}')

print_step "重启完成！"
echo ""
echo -e "${CYAN}访问地址:${NC}"
echo -e "  前端: ${GREEN}http://${SERVER_IP}:3001${NC}"
echo -e "  后端: ${GREEN}http://${SERVER_IP}:${BACKEND_PORT}${NC}"
echo ""

print_success "RagflowAuth 快速重启成功！"
