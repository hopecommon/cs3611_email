"""
运行基础SMTP服务器示例
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.basic_smtp_server import BasicSMTPServer
from common.utils import setup_logging

# 设置日志
logger = setup_logging("run_basic_smtp_server")


def main():
    """主函数"""
    # 解析命令行参数
    import argparse

    parser = argparse.ArgumentParser(description="运行基础SMTP服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--port", type=int, default=8025, help="服务器端口")
    parser.add_argument("--auth", action="store_true", help="启用认证")
    parser.add_argument("--no-auth", dest="auth", action="store_false", help="禁用认证")
    parser.set_defaults(auth=False)  # 默认禁用认证，方便测试
    args = parser.parse_args()

    # 创建并启动服务器
    server = BasicSMTPServer(host=args.host, port=args.port, require_auth=args.auth)
    server.start()

    try:
        # 保持程序运行
        # 显示实际使用的端口（可能与指定的端口不同）
        actual_port = server.port
        print(f"SMTP服务器已启动: {args.host}:{actual_port}")
        print(f"服务器绑定地址: {args.host}:{actual_port}")
        print(f"认证要求: {'启用' if args.auth else '禁用'}")
        print("按Ctrl+C停止服务器")

        # 使用asyncio事件循环运行服务器
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except KeyboardInterrupt:
        print("正在停止服务器...")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
