#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化Web邮件客户端启动脚本
"""

import subprocess
import sys
import os
from pathlib import Path


def main():
    print("🚀 启动简化Web邮件客户端")
    print("=" * 50)
    print("📧 基于CLI底层实现，避免复杂封装")
    print("💡 直接复用CLI的稳定邮件发送逻辑")
    print("🌐 访问地址: http://localhost:3000")
    print("=" * 50)

    # 检查是否在正确的目录
    if not Path("cli").exists():
        print("❌ 错误：请在项目根目录运行此脚本")
        sys.exit(1)

    # 检查依赖
    try:
        import flask

        print("✅ Flask 已安装")
    except ImportError:
        print("❌ 错误：Flask 未安装")
        print("请运行: pip install flask")
        sys.exit(1)

    # 启动应用
    try:
        print("\n🔄 正在启动应用...")
        subprocess.run([sys.executable, "simple_web_client.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
