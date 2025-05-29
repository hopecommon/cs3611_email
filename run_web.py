#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web邮件客户端启动脚本 - 使用新的邮箱认证系统
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 使用新的应用工厂
from web import create_app


def main():
    """启动Web应用"""
    try:
        print("🚀 正在启动Web邮件客户端...")
        print("📧 使用新的邮箱认证系统")

        # 创建Flask应用
        app = create_app("development")

        print("✅ Web邮件客户端启动成功！")
        print("🌐 访问地址: http://localhost:5000")
        print("🔧 运行环境: 开发模式")
        print("📝 按 Ctrl+C 停止服务器")
        print("💡 支持直接邮箱登录(QQ、Gmail、163等)")
        print("-" * 50)

        # 启动开发服务器
        app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)

    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
