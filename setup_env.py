#!/usr/bin/env python3
"""
虚拟环境设置脚本
Virtual Environment Setup Script
"""

import subprocess
import sys
import os

def create_and_setup_venv():
    """创建虚拟环境并安装依赖"""
    venv_name = "venv"

    print("🔧 创建虚拟环境...")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", venv_name])
        print(f"✅ 虚拟环境 '{venv_name}' 创建成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 创建虚拟环境失败: {e}")
        return False

    # 根据操作系统确定激活脚本路径
    if os.name == 'nt':  # Windows
        pip_path = os.path.join(venv_name, "Scripts", "pip")
        python_path = os.path.join(venv_name, "Scripts", "python")
    else:  # Linux/Mac
        pip_path = os.path.join(venv_name, "bin", "pip")
        python_path = os.path.join(venv_name, "bin", "python")

    print("📦 安装依赖库...")
    try:
        subprocess.check_call([pip_path, "install", "-r", "requirements.txt"])
        print("✅ 依赖库安装成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装依赖库失败: {e}")
        return False

    print("\n🎉 环境设置完成!")
    print("\n运行方式:")
    if os.name == 'nt':
        print(f"1. 激活虚拟环境: {venv_name}\\Scripts\\activate")
        print(f"2. 运行登录页面: python login_page.py")
    else:
        print(f"1. 激活虚拟环境: source {venv_name}/bin/activate")
        print(f"2. 运行登录页面: python login_page.py")

    return True

if __name__ == "__main__":
    if create_and_setup_venv():
        sys.exit(0)
    else:
        sys.exit(1)