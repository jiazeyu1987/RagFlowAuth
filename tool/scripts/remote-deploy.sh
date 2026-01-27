#!/bin/bash
# RagflowAuth 服务器端部署脚本
# 用途：在服务器上加载并启动 RagflowAuth 容器

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
TAG="${TAG:-$(date +%Y-%m-%d)}"
TAR_FILE="${TAR_FILE:-/tmp/ragflowauth-images_${TAG}.tar}"
DATA_DIR="${DATA_DIR:-/opt/ragflowauth}"
FRONTEND_PORT="${FRONTEND_PORT:-3001}"
BACKEND_PORT="${BACKEND_PORT:-8001}"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            TAG="$2"
            TAR_FILE="/tmp/ragflowauth-images_${TAG}.tar"
            shift 2
            ;;
        --tar-file)
            TAR_FILE="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --frontend-port)
            FRONTEND_PORT="$2"
            shift 2
            ;;
        --backend-port)
            BACKEND_PORT="$2"
            shift 2
            ;;
        --skip-load)
            SKIP_LOAD=true
            shift
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --tag TAG              镜像标签 (默认: 当前日期)"
            echo "  --tar-file PATH        tar 文件路径"
            echo "  --data-dir PATH        数据目录 (默认: /opt/ragflowauth)"
            echo "  --frontend-port PORT   前端端口 (默认: 3001)"
            echo "  --backend-port PORT    后端端口 (默认: 8001)"
            echo "  --skip-load            跳过镜像加载"
            echo "  --help                 显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 --tag 2026-01-22"
            echo "  $0 --tar-file /tmp/my-images.tar --frontend-port 8080"
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

print_step "RagflowAuth 服务器端部署"
echo ""
print_info "镜像标签: $TAG"
print_info "Tar 文件: $TAR_FILE"
print_info "数据目录: $DATA_DIR"
print_info "前端端口: $FRONTEND_PORT"
print_info "后端端口: $BACKEND_PORT"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    print_error "未找到 Docker，请先安装 Docker"
    exit 1
fi

# 加载镜像
if [ "$SKIP_LOAD" != true ]; then
    if [ ! -f "$TAR_FILE" ]; then
        print_error "未找到 tar 文件: $TAR_FILE"
        exit 1
    fi

    print_step "加载 Docker 镜像"
    docker load -i "$TAR_FILE"
    print_success "镜像加载完成"
else
    print_step "跳过镜像加载"
fi

# 创建数据目录
print_step "创建数据目录"
mkdir -p "$DATA_DIR/data"
mkdir -p "$DATA_DIR/uploads"
print_success "数据目录已创建: $DATA_DIR"

# 创建配置文件（如果不存在）
print_step "检查配置文件"
if [ "$SKIP_CONFIG_CREATE" = "1" ]; then
    print_info "跳过配置文件创建（使用已上传的配置）"
elif [ ! -f "$DATA_DIR/ragflow_config.json" ]; then
    print_warn "配置文件不存在，创建默认配置"
    cat > "$DATA_DIR/ragflow_config.json" << 'EOF'
{
  "api_key": "ragflow-VmYjRmNjIwZjc2MzExZjBhZmMyMDI0Mm",
  "base_url": "http://host.docker.internal:9380",
  "dataset_name": "展厅",
  "default_conversation_name": "展厅聊天",
  "asr": {
    "provider": "dashscope",
    "preprocess": {
      "trim_silence": true,
      "normalize": true
    },
    "dashscope": {
      "api_key": "sk-cd7176a23d484b02b23ba916b261d7ec",
      "model": "paraformer-realtime-v2",
      "kwargs": {
        "disfluency_removal_enabled": false
      }
    }
  },
  "text_cleaning": {
    "enabled": true,
    "show_cleaned_output": false,
    "language": "zh-CN",
    "cleaning_level": "standard",
    "tts_buffer_enabled": true,
    "semantic_chunking": true,
    "max_chunk_size": 260,
    "start_tts_on_first_chunk": true,
    "first_segment_min_chars": 120,
    "segment_flush_interval_s": 1.2,
    "segment_min_chars": 120
  },
  "tts": {
    "provider": "modelscope",
    "mimetype": "audio/wav",
    "debug_dump_dir": "",
    "debug_dump_max_bytes": 0,
    "sovtts1": {
      "enabled": true,
      "url": "http://127.0.0.1:9882",
      "timeout_s": 30,
      "text_lang": "zh",
      "prompt_lang": "zh",
      "ref_audio_path": "Liang/converted_temp_first_90s.wav_0000000000_0000182720.wav",
      "text_language": "zh",
      "prompt_language": "zh",
      "refer_wav_path": "Liang/converted_temp_first_90s.wav_0000000000_0000182720.wav",
      "prompt_text": "平台呢因为从我们的初创团队的理解的角度呢，我们觉得一个初创公司。",
      "media_type": "wav"
    },
    "local": {
      "enabled": true,
      "url": "http://127.0.0.1:9880/tts",
      "timeout_s": 30,
      "text_lang": "zh",
      "prompt_lang": "zh",
      "ref_audio_path": "Liang/converted_temp_first_90s.wav_0000000000_0000182720.wav",
      "prompt_text": "平台呢因为从我们的初创团队的理解的角度呢，我们觉得一个初创公司。",
      "low_latency": true,
      "media_type": "wav"
    },
    "sovtts2": {
      "enabled": true,
      "url": "http://127.0.0.1:9880/tts",
      "timeout_s": 30,
      "text_lang": "zh",
      "prompt_lang": "zh",
      "ref_audio_path": "Liang/converted_temp_first_90s.wav_0000000000_0000182720.wav",
      "prompt_text": "",
      "streaming_mode": true,
      "media_type": "wav"
    },
    "sapi": {
      "enabled": true,
      "voice": "",
      "rate": 0,
      "volume": 100,
      "timeout_s": 30
    },
    "edge": {
      "enabled": true,
      "voice": "zh-CN-XiaoxiaoNeural",
      "output_format": "riff-16khz-16bit-mono-pcm",
      "rate": "+0%",
      "volume": "+0%",
      "first_audio_timeout_s": 12,
      "timeout_s": 30,
      "queue_max_chunks": 256
    },
    "bailian": {
      "mode": "dashscope",
      "model": "cosyvoice-v3-plus",
      "voice": "cosyvoice-v3-plus-myvoice-1d7b061183cf4329ad7709451fa7ecf0",
      "seed": 12382,
      "format": "wav",
      "sample_rate": 16000,
      "use_connection_pool": true,
      "pool_max_size": 3,
      "queue_max_chunks": 256,
      "first_chunk_timeout_s": 12.0,
      "pcm_probe_target_bytes": 32000,
      "volume": 50,
      "speech_rate": 1.0,
      "pitch_rate": 1.0,
      "additional_params": {},
      "url": "",
      "api_key": "sk-cd7176a23d484b02b23ba916b261d7ec",
      "method": "POST",
      "timeout_s": 30,
      "text_field": "text",
      "auth_header": "Authorization",
      "auth_prefix": "Bearer ",
      "extra_json": {},
      "json_audio_field": "",
      "json_audio_b64": true
    }
  },
  "timeout": 10,
  "log_level": "INFO",
  "log_file": "/log",
  "max_retries": 3,
  "retry_delay": 1.0
}
EOF
    print_success "已创建默认配置文件"
else
    print_success "配置文件已存在"
fi

# 创建 Docker 网络
print_step "创建 Docker 网络"
if docker network ls | grep -q ragflowauth-network; then
    print_info "网络已存在"
else
    docker network create ragflowauth-network
    print_success "网络已创建"
fi

# 停止并删除旧容器
print_step "停止旧容器"
docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true
docker rm ragflowauth-backend ragflowauth-frontend 2>/dev/null || true
print_success "旧容器已清理"

# 启动后端
print_step "启动后端容器"
docker run -d \
  --name ragflowauth-backend \
  --network ragflowauth-network \
  -p "${BACKEND_PORT}:8001" \
  -e TZ=Asia/Shanghai \
  -v "$DATA_DIR/data:/app/data" \
  -v "$DATA_DIR/uploads:/app/uploads" \
  -v "$DATA_DIR/ragflow_config.json:/app/ragflow_config.json:ro" \
  -v "$DATA_DIR/ragflow_compose:/app/ragflow_compose:ro" \
  -v "$DATA_DIR/backups:/app/data/backups" \
  -v "$DATA_DIR/data:/opt/ragflowauth/data:ro" \
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
  -p "${FRONTEND_PORT}:80" \
  --link ragflowauth-backend:backend \
  "ragflowauth-frontend:$TAG"

if [ $? -eq 0 ]; then
    print_success "前端容器已启动"
else
    print_error "前端容器启动失败"
    exit 1
fi

# 清理临时文件
print_step "清理临时文件"
if [ -f "$TAR_FILE" ] && [ "$SKIP_LOAD" != true ]; then
    rm -f "$TAR_FILE"
    print_success "已删除 tar 文件"
fi

# 等待容器启动
print_step "等待容器启动"
sleep 5

# 检查容器状态
print_step "检查容器状态"
echo ""
docker ps | grep ragflowauth
echo ""

# 获取服务器 IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# 显示访问信息
print_step "部署完成！"
echo ""
echo -e "${CYAN}访问地址:${NC}"
echo -e "  前端: ${GREEN}http://${SERVER_IP}:${FRONTEND_PORT}${NC}"
echo -e "  后端: ${GREEN}http://${SERVER_IP}:${BACKEND_PORT}${NC}"
echo ""
echo -e "${CYAN}管理命令:${NC}"
echo "  查看容器: docker ps | grep ragflowauth"
echo "  查看日志: docker logs -f ragflowauth-backend"
echo "  查看前端日志: docker logs -f ragflowauth-frontend"
echo "  重启服务: docker restart ragflowauth-backend ragflowauth-frontend"
echo "  停止服务: docker stop ragflowauth-backend ragflowauth-frontend"
echo "  修改配置: vi $DATA_DIR/ragflow_config.json"
echo "  重启后端: docker restart ragflowauth-backend"
echo ""

# 显示容器日志
print_step "容器日志 (后端)"
docker logs --tail 20 ragflowauth-backend 2>&1 | grep -E "(INFO|ERROR|WARNING)" || docker logs --tail 10 ragflowauth-backend

echo ""
print_step "容器日志 (前端)"
docker logs --tail 10 ragflowauth-frontend

echo ""
print_success "RagflowAuth 部署成功！"
