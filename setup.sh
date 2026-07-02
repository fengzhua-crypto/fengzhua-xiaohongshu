#!/usr/bin/env bash
# setup.sh - 一键安装依赖
set -e

echo "=== fengzhua-xiaohongshu 环境安装 ==="

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

# 安装依赖
echo "[1/2] 安装 Python 依赖..."
pip install -r "$(dirname "$0")/scripts/requirements.txt"

# 安装浏览器
echo "[2/2] 安装 Chromium 浏览器..."
playwright install chromium

echo ""
echo "=== 安装完成 ==="
echo "下一步: python scripts/xhs_scraper.py init  (扫码登录)"
