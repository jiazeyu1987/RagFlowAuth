#!/bin/bash
# RagflowAuth Docker 镜像清理脚本
# 用途：清理服务器上未使用的旧镜像，释放磁盘空间

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

# 配置
PRODUCTION_TAG="${PRODUCTION_TAG:-production}"  # 生产环境 tag

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --production-tag)
            PRODUCTION_TAG="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --production-tag TAG  生产环境镜像 tag (默认: production)"
            echo "  --dry-run             仅显示将要删除的镜像，不实际删除"
            echo "  --help                显示此帮助信息"
            echo ""
            echo "说明:"
            echo "  脚本只会保留当前正在运行的容器使用的镜像，"
            echo "  所有其他版本的镜像都会被删除。"
            echo ""
            echo "示例:"
            echo "  $0 --production-tag latest     # 使用 latest 作为生产 tag"
            echo "  $0 --dry-run                   # 预览将要删除的镜像"
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

print_step "RagflowAuth Docker 镜像清理"
echo ""
print_info "策略: 只保留当前运行的镜像"
print_info "生产环境 tag: $PRODUCTION_TAG"
[ "$DRY_RUN" = true ] && print_info "模式: 预览（不实际删除）"
echo ""

# 获取当前运行的容器使用的镜像
print_step "正在运行的容器"
RUNNING_BACKEND=$(docker ps --filter "name=ragflowauth-backend" --format "{{.Image}}")
RUNNING_FRONTEND=$(docker ps --filter "name=ragflowauth-frontend" --format "{{.Image}}")

if [ -n "$RUNNING_BACKEND" ]; then
    print_info "后端: $RUNNING_BACKEND"
fi
if [ -n "$RUNNING_FRONTEND" ]; then
    print_info "前端: $RUNNING_FRONTEND"
fi
echo ""

# 列出所有 ragflowauth 镜像
print_step "所有 RagflowAuth 镜像"
echo ""
docker images | grep ragflowauth || print_warn "未找到任何 ragflowauth 镜像"
echo ""

# 收集要保留的镜像（仅保留当前运行的）
print_step "分析镜像版本"
KEEP_IMAGES=()
if [ -n "$RUNNING_BACKEND" ]; then
    KEEP_IMAGES+=("$RUNNING_BACKEND")
    print_info "保留后端: $RUNNING_BACKEND"
fi
if [ -n "$RUNNING_FRONTEND" ]; then
    KEEP_IMAGES+=("$RUNNING_FRONTEND")
    print_info "保留前端: $RUNNING_FRONTEND"
fi

# 去重
UNIQUE_KEEP=($(printf "%s\n" "${KEEP_IMAGES[@]}" | sort -u))
echo ""

# 收集要删除的镜像
TO_DELETE=()
ALL_IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "^ragflowauth-")

for img in $ALL_IMAGES; do
    should_delete=true
    for keep in "${UNIQUE_KEEP[@]}"; do
        if [ "$img" = "$keep" ]; then
            should_delete=false
            break
        fi
    done

    if [ "$should_delete" = true ]; then
        TO_DELETE+=("$img")
    fi
done

# 显示将要删除的镜像
if [ ${#TO_DELETE[@]} -eq 0 ]; then
    print_success "没有需要清理的镜像"
    exit 0
fi

print_warn "将要删除 ${#TO_DELETE[@]} 个旧镜像:"
for img in "${TO_DELETE[@]}"; do
    # 显示镜像大小
    size=$(docker images "$img" --format "{{.Size}}")
    echo "  - $img ($size)"
done
echo ""

# 确认删除
if [ "$DRY_RUN" != true ]; then
    read -p "确认删除这些镜像? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_info "取消操作"
        exit 0
    fi
fi

# 删除镜像
print_step "删除旧镜像"
DELETED_COUNT=0
FREED_SPACE=0

for img in "${TO_DELETE[@]}"; do
    if [ "$DRY_RUN" = true ]; then
        print_info "[预览] 删除: $img"
    else
        # 获取镜像大小
        size=$(docker images "$img" --format "{{.Size}}")
        docker rmi "$img" 2>/dev/null || print_warn "删除失败: $img (可能被其他容器使用)"
        print_info "已删除: $img ($size)"
        ((DELETED_COUNT++))
    fi
done

if [ "$DRY_RUN" != true ]; then
    print_success "已删除 $DELETED_COUNT 个镜像"
fi

echo ""

# 清理悬空镜像（dangling images）
print_step "清理悬空镜像"
DANGLING=$(docker images -f "dangling=true" -q)
if [ -n "$DANGLING" ]; then
    DANGLING_COUNT=$(echo "$DANGLING" | wc -l)
    print_info "发现 $DANGLING_COUNT 个悬空镜像"

    if [ "$DRY_RUN" = true ]; then
        echo "$DANGLING" | head -5
        if [ $DANGLING_COUNT -gt 5 ]; then
            print_info "... 还有 $((DANGLING_COUNT - 5)) 个"
        fi
    else
        docker image prune -f
        print_success "悬空镜像已清理"
    fi
else
    print_info "没有悬空镜像"
fi

echo ""

# 显示磁盘使用情况
print_step "当前 Docker 磁盘使用"
docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}"
echo ""

print_success "镜像清理完成！"
