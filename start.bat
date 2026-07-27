@echo off
chcp 65001 >nul
title Agent v5

echo.
echo ╔══════════════════════════════════════╗
echo ║       Agent v5 - 一键启动            ║
echo ╚══════════════════════════════════════╝
echo.

rem ── 配置 ──────────────────────────────
set "AGENT_DIR=%~dp0"
set "VENV=%AGENT_DIR%.venv"
set "AGENT_PROVIDER=deepseek"
set "AGENT_MODEL=deepseek-v4-flash"

rem ── 检查 Python ────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

rem ── 检查虚拟环境 ──────────────────────
if not exist "%VENV%\Scripts\python.exe" (
    echo [初始化] 创建虚拟环境...
    python -m venv "%VENV%"
    call "%VENV%\Scripts\activate.bat"
    pip install httpx flask chromadb pyreadline3 -q
    echo [完成] 依赖已安装
) else (
    call "%VENV%\Scripts\activate.bat"
)

rem ── 检查 API Key ──────────────────────
if "%DEEPSEEK_API_KEY%"=="" (
    if "%OPENAI_API_KEY%"=="" (
        echo [提示] 未设置 API Key
        echo   设置方法: set DEEPSEEK_API_KEY=sk-xxx
        echo   或修改此脚本中的环境变量
        echo.
        echo [演示模式] 启动 Web UI (工具可本地使用)
    )
)

rem ── 选择启动模式 ──────────────────────
echo 选择启动模式:
echo   [1] Web UI (浏览器访问 http://localhost:5000)
echo   [2] CLI 交互模式
echo   [3] 单任务模式
echo   [4] 运行测试
echo.
set /p MODE="输入数字 [1-4]: "

if "%MODE%"=="1" (
    echo.
    echo 启动 Web UI...
    echo 打开浏览器访问: http://localhost:5000
    start http://localhost:5000
    python "%AGENT_DIR%server.py"
) else if "%MODE%"=="2" (
    python -m agent.main --provider %AGENT_PROVIDER% --model %AGENT_MODEL%
) else if "%MODE%"=="3" (
    set /p TASK="输入任务: "
    python -m agent.main "%TASK%"
) else if "%MODE%"=="4" (
    python -m agent.main --test
) else (
    echo 无效选择
)

pause
