#!/bin/bash

# AssetRipper API Server - 重启脚本
# 停止当前服务并重新启动

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AssetRipper API Server - 重启服务${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 停止服务
echo -e "${YELLOW}步骤 1/2: 停止现有服务${NC}"
echo ""
./stop.sh

echo ""
echo -e "${YELLOW}步骤 2/2: 启动服务${NC}"
echo ""
sleep 1

# 启动服务
./start.sh -d
