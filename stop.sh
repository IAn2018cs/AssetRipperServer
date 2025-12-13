#!/bin/bash

# AssetRipper API Server - 停止脚本
# 用于停止本地运行的服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AssetRipper API Server - 停止服务${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 查找并停止 uvicorn 进程
echo -e "${YELLOW}[1/2]${NC} 查找 uvicorn 进程..."
UVICORN_PIDS=$(pgrep -f "uvicorn app.main:app" || true)

if [ -z "$UVICORN_PIDS" ]; then
    echo -e "${YELLOW}⚠${NC}  未找到运行中的 uvicorn 进程"
else
    echo -e "${GREEN}✓${NC} 找到 uvicorn 进程: $UVICORN_PIDS"
    echo "正在停止 uvicorn..."

    for PID in $UVICORN_PIDS; do
        kill -TERM $PID 2>/dev/null || true
        echo "  - 已发送停止信号到进程 $PID"
    done

    # 等待进程优雅退出
    sleep 2

    # 检查是否还有残留进程
    REMAINING=$(pgrep -f "uvicorn app.main:app" || true)
    if [ ! -z "$REMAINING" ]; then
        echo -e "${YELLOW}⚠${NC}  进程未正常退出，强制终止..."
        kill -9 $REMAINING 2>/dev/null || true
    fi

    echo -e "${GREEN}✓${NC} uvicorn 服务已停止"
fi

# 查找并停止 AssetRipper 进程
echo ""
echo -e "${YELLOW}[2/2]${NC} 查找 AssetRipper 进程..."
ASSETRIPPER_PIDS=$(pgrep -f "AssetRipper.GUI.Free" || true)

if [ -z "$ASSETRIPPER_PIDS" ]; then
    echo -e "${YELLOW}⚠${NC}  未找到运行中的 AssetRipper 进程"
else
    echo -e "${GREEN}✓${NC} 找到 AssetRipper 进程: $ASSETRIPPER_PIDS"
    echo "正在停止 AssetRipper..."

    for PID in $ASSETRIPPER_PIDS; do
        kill -TERM $PID 2>/dev/null || true
        echo "  - 已发送停止信号到进程 $PID"
    done

    # 等待进程优雅退出
    sleep 2

    # 检查是否还有残留进程
    REMAINING=$(pgrep -f "AssetRipper.GUI.Free" || true)
    if [ ! -z "$REMAINING" ]; then
        echo -e "${YELLOW}⚠${NC}  进程未正常退出，强制终止..."
        kill -9 $REMAINING 2>/dev/null || true
    fi

    echo -e "${GREEN}✓${NC} AssetRipper 进程已停止"
fi

# 显示结果
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  服务停止完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否还有任何相关进程
REMAINING_UVICORN=$(pgrep -f "uvicorn app.main:app" || true)
REMAINING_ASSETRIPPER=$(pgrep -f "AssetRipper.GUI.Free" || true)

if [ -z "$REMAINING_UVICORN" ] && [ -z "$REMAINING_ASSETRIPPER" ]; then
    echo -e "${GREEN}✓${NC} 所有服务已完全停止"
else
    echo -e "${RED}⚠${NC}  警告: 仍有进程在运行"
    [ ! -z "$REMAINING_UVICORN" ] && echo "  - uvicorn: $REMAINING_UVICORN"
    [ ! -z "$REMAINING_ASSETRIPPER" ] && echo "  - AssetRipper: $REMAINING_ASSETRIPPER"
    echo ""
    echo "如需强制终止，请运行:"
    echo -e "  ${BLUE}pkill -9 -f 'uvicorn app.main:app'${NC}"
    echo -e "  ${BLUE}pkill -9 -f 'AssetRipper.GUI.Free'${NC}"
fi

echo ""
