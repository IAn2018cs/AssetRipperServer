#!/bin/bash

# AssetRipper API Server - 本地启动脚本
# 用于在 macOS 环境下直接运行服务（不使用 Docker）
#
# 用法:
#   ./start.sh          - 前台启动（占用终端）
#   ./start.sh -d       - 后台启动（daemon 模式）
#   ./start.sh --daemon - 后台启动（daemon 模式）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 解析参数
DAEMON_MODE=false
if [ "$1" = "-d" ] || [ "$1" = "--daemon" ]; then
    DAEMON_MODE=true
fi

echo -e "${BLUE}========================================${NC}"
if [ "$DAEMON_MODE" = true ]; then
    echo -e "${BLUE}  AssetRipper API Server - 后台启动${NC}"
else
    echo -e "${BLUE}  AssetRipper API Server - 前台启动${NC}"
fi
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 Python 版本
echo -e "${YELLOW}[1/7]${NC} 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3，请先安装 Python 3.11+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓${NC} Python 版本: ${PYTHON_VERSION}"

# 检查是否在项目根目录
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 创建虚拟环境（如果不存在）
echo ""
echo -e "${YELLOW}[2/7]${NC} 设置 Python 虚拟环境..."
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
    echo -e "${GREEN}✓${NC} 虚拟环境已创建"
else
    echo -e "${GREEN}✓${NC} 虚拟环境已存在"
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
echo ""
echo -e "${YELLOW}[3/7]${NC} 安装 Python 依赖..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo -e "${GREEN}✓${NC} 依赖安装完成"

# 检查 AssetRipper 二进制文件
echo ""
echo -e "${YELLOW}[4/7]${NC} 检查 AssetRipper 二进制文件..."
if [ -f "local/AssetRipper.GUI.Free" ]; then
    ASSETRIPPER_PATH="$(pwd)/local/AssetRipper.GUI.Free"
    echo -e "${GREEN}✓${NC} 找到 macOS 版本: local/AssetRipper.GUI.Free"
    chmod +x "$ASSETRIPPER_PATH"
elif [ -f "bin/AssetRipper.GUI.Free" ]; then
    ASSETRIPPER_PATH="$(pwd)/bin/AssetRipper.GUI.Free"
    echo -e "${YELLOW}⚠${NC}  使用 Linux 版本: bin/AssetRipper.GUI.Free"
    echo -e "${YELLOW}   注意: 此版本可能无法在 macOS 上运行${NC}"
    chmod +x "$ASSETRIPPER_PATH"
else
    echo -e "${RED}错误: 未找到 AssetRipper.GUI.Free${NC}"
    echo ""
    echo "请将 macOS 版本的 AssetRipper.GUI.Free 放置在以下位置之一："
    echo "  1. local/AssetRipper.GUI.Free (推荐)"
    echo "  2. bin/AssetRipper.GUI.Free"
    echo ""
    echo "下载地址: https://github.com/AssetRipper/AssetRipper/releases"
    exit 1
fi

# 创建必要的目录
echo ""
echo -e "${YELLOW}[5/7]${NC} 创建数据目录..."
mkdir -p data/uploads data/exports data/db logs
echo -e "${GREEN}✓${NC} 目录创建完成"

# 设置环境变量
echo ""
echo -e "${YELLOW}[6/7]${NC} 配置环境变量..."
export ENVIRONMENT=development
export API_HOST=0.0.0.0
export API_PORT=8000
export ASSETRIPPER_PORT=8765
export ASSETRIPPER_BINARY_PATH="$ASSETRIPPER_PATH"
export DATABASE_URL="sqlite+aiosqlite:///$(pwd)/data/db/assetripper.db"
export UPLOAD_DIR="$(pwd)/data/uploads"
export EXPORT_DIR="$(pwd)/data/exports"
export FILE_RETENTION_DAYS=30
export LOG_LEVEL=INFO
export LOG_FILE="$(pwd)/logs/app.log"

echo -e "${GREEN}✓${NC} 环境变量配置完成"
echo "   - API 端口: ${API_PORT}"
echo "   - AssetRipper 路径: ${ASSETRIPPER_PATH}"
echo "   - 数据库: $(pwd)/data/db/assetripper.db"

# 启动服务
echo ""
echo -e "${YELLOW}[7/7]${NC} 启动 AssetRipper API Server..."

if [ "$DAEMON_MODE" = true ]; then
    # 后台启动
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  后台启动服务...${NC}"
    echo -e "${GREEN}========================================${NC}"

    # 将输出重定向到日志文件
    nohup uvicorn app.main:app \
        --host ${API_HOST} \
        --port ${API_PORT} \
        --log-level info \
        > logs/uvicorn.log 2>&1 &

    UVICORN_PID=$!
    echo $UVICORN_PID > logs/uvicorn.pid

    # 等待服务启动
    echo "等待服务启动..."
    sleep 3

    # 检查进程是否还在运行
    if ps -p $UVICORN_PID > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓ 服务已在后台启动成功！${NC}"
        echo ""
        echo -e "进程 ID: ${BLUE}$UVICORN_PID${NC}"
        echo ""
        echo -e "访问地址:"
        echo -e "  - API 根路径:  ${BLUE}http://localhost:${API_PORT}${NC}"
        echo -e "  - API 文档:    ${BLUE}http://localhost:${API_PORT}/docs${NC}"
        echo -e "  - 健康检查:    ${BLUE}http://localhost:${API_PORT}/api/v1/health${NC}"
        echo ""
        echo -e "日志位置:"
        echo -e "  - 应用日志:    ${BLUE}$(pwd)/logs/app.log${NC}"
        echo -e "  - Uvicorn日志: ${BLUE}$(pwd)/logs/uvicorn.log${NC}"
        echo ""
        echo -e "管理命令:"
        echo -e "  - 查看日志:    ${BLUE}tail -f logs/uvicorn.log${NC}"
        echo -e "  - 停止服务:    ${BLUE}./stop.sh${NC}"
        echo -e "  - 重启服务:    ${BLUE}./restart.sh${NC}"
    else
        echo -e "${RED}✗ 服务启动失败${NC}"
        echo "请查看日志: logs/uvicorn.log"
        exit 1
    fi
else
    # 前台启动
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  服务启动成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "访问地址:"
    echo -e "  - API 根路径:  ${BLUE}http://localhost:${API_PORT}${NC}"
    echo -e "  - API 文档:    ${BLUE}http://localhost:${API_PORT}/docs${NC}"
    echo -e "  - 健康检查:    ${BLUE}http://localhost:${API_PORT}/api/v1/health${NC}"
    echo ""
    echo -e "日志位置: ${BLUE}$(pwd)/logs/app.log${NC}"
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    echo ""

    # 启动 uvicorn（前台运行）
    uvicorn app.main:app \
        --host ${API_HOST} \
        --port ${API_PORT} \
        --log-level info \
        --reload
fi

