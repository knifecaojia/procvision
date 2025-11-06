@echo off
echo ===================================
echo  工业视觉登录页面启动脚本
echo  Industrial Vision Login Page
echo ===================================
echo.

REM 检查虚拟环境是否存在
if not exist "venv" (
    echo 虚拟环境不存在，正在创建...
    python setup_env.py
    if errorlevel 1 (
        echo 环境设置失败，请检查Python和pip是否正确安装
        pause
        exit /b 1
    )
)

echo 激活虚拟环境...
call venv\Scripts\activate

echo 启动登录页面...
python login_page.py

echo 程序已退出
pause