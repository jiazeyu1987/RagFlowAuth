#!/bin/bash
# RagflowAuth 环境检查和自动修复脚本
# 用途：确保 Docker 网络和容器运行正常
# 建议：添加到 crontab 或 systemd 服务中，在服务器启动后自动运行

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${CYAN}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "  $1"
}

DATA_DIR="${DATA_DIR:-/opt/ragflowauth}"
NETWORK_NAME="ragflowauth-network"

print_step "RagflowAuth 环境检查"
echo ""

# 1. 检查 Docker
print_step "检查 Docker"
if ! command -v docker &> /dev/null; then
    print_error "Docker 未安装"
    exit 1
fi
print_success "Docker 已安装"

# 2. 检查网络
print_step "检查 Docker 网络"
if docker network ls | grep -q "$NETWORK_NAME"; then
    print_success "网络存在: $NETWORK_NAME"
else
    print_warn "网络不存在，创建网络: $NETWORK_NAME"
    docker network create "$NETWORK_NAME"
    print_success "网络已创建"
fi

# 3. 检查镜像
print_step "检查 Docker 镜像"
BACKEND_IMAGE=$(docker ps --filter "name=ragflowauth-backend" --format "{{.Image}}")
FRONTEND_IMAGE=$(docker ps --filter "name=ragflowauth-frontend" --format "{{.Image}}")

if [ -z "$BACKEND_IMAGE" ]; then
    # 尝试从停止的容器获取镜像
    BACKEND_IMAGE=$(docker ps -a --filter "name=ragflowauth-backend" --format "{{.Image}}")
fi

if [ -z "$FRONTEND_IMAGE" ]; then
    FRONTEND_IMAGE=$(docker ps -a --filter "name=ragflowauth-frontend" --format "{{.Image}}")
fi

if [ -z "$BACKEND_IMAGE" ] || [ -z "$FRONTEND_IMAGE" ]; then
    print_warn "镜像不完整，可能需要重新部署"
    print_warn "后端镜像: ${BACKEND_IMAGE:-未找到}"
    print_warn "前端镜像: ${FRONTEND_IMAGE:-未找到}"
else
    print_success "镜像存在"
    print_info "  后端: $BACKEND_IMAGE"
    print_info "  前端: $FRONTEND_IMAGE"
fi

# 4. 检查容器状态
print_step "检查容器状态"

BACKEND_RUNNING=$(docker ps --filter "name=ragflowauth-backend" --filter "status=running" --format "{{.Names}}")
FRONTEND_RUNNING=$(docker ps --filter "name=ragflowauth-frontend" --filter "status=running" --format "{{.Names}}")

if [ -z "$BACKEND_RUNNING" ]; then
    if docker ps -a --filter "name=ragflowauth-backend" --format "{{.Names}}" | grep -q ragflowauth-backend; then
        print_warn "后端容器存在但未运行，尝试启动..."
        if docker start ragflowauth-backend 2>/dev/null; then
            print_success "后端容器已启动"
        else
            print_error "后端容器启动失败"
        fi
    else
        print_warn "后端容器不存在，跳过"
    fi
else
    print_success "后端容器运行中"
fi

if [ -z "$FRONTEND_RUNNING" ]; then
    if docker ps -a --filter "name=ragflowauth-frontend" --format "{{.Names}}" | grep -q ragflowauth-frontend; then
        print_warn "前端容器存在但未运行，尝试启动..."
        if docker start ragflowauth-frontend 2>/dev/null; then
            print_success "前端容器已启动"
        else
            print_error "前端容器启动失败"
        fi
    else
        print_warn "前端容器不存在，跳过"
    fi
else
    print_success "前端容器运行中"
fi

# 5. 最终状态
print_step "最终状态"
echo ""
docker ps --filter "name=ragflowauth" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

print_success "环境检查完成"
