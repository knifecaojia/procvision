#!/bin/bash

echo "==================================="
echo " 工业视觉登录页面启动脚本"
echo " Industrial Vision Login Page"
echo "==================================="
echo

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "虚拟环境不存在，正在创建..."
    python3 setup_env.py
    if [ $? -ne 0 ]; then
        echo "环境设置失败，请检查Python和pip是否正确安装"
        exit 1
    fi
fi

echo "激活虚拟环境..."
source venv/bin/activate

echo "启动登录页面..."
python3 login_page.py

echo "程序已退出"