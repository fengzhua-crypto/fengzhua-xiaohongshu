@echo off
REM setup.bat - Windows 一键安装依赖
setlocal

echo === fengzhua-xiaohongshu 环境安装 ===

REM 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 python，请先安装 Python 3.8+
    exit /b 1
)

REM 安装依赖
echo [1/2] 安装 Python 依赖...
pip install -r "%~dp0scripts\requirements.txt"

REM 安装浏览器
echo [2/2] 安装 Chromium 浏览器...
playwright install chromium

echo.
echo === 安装完成 ===
echo 下一步: python scripts\xhs_scraper.py init  (扫码登录)
