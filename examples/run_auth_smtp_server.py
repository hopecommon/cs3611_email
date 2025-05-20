"""
运行认证SMTP服务器示例
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.authenticated_smtp_server import AuthenticatedSMTPServer
from common.utils import setup_logging
from common.port_config import save_port_config

# 设置日志
logger = setup_logging("run_auth_smtp_server")


def main():
    """主函数"""
    # 解析命令行参数
    import argparse

    parser = argparse.ArgumentParser(description="运行认证SMTP服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--port", type=int, default=8025, help="服务器端口")
    parser.add_argument("--auth", action="store_true", help="启用认证")
    parser.add_argument("--no-auth", dest="auth", action="store_false", help="禁用认证")
    parser.add_argument("--ssl", action="store_true", help="启用SSL")
    parser.add_argument("--no-ssl", dest="ssl", action="store_false", help="禁用SSL")
    parser.add_argument(
        "--cert", type=str, default="certs/server.crt", help="SSL证书文件路径"
    )
    parser.add_argument(
        "--key", type=str, default="certs/server.key", help="SSL密钥文件路径"
    )
    parser.set_defaults(auth=True, ssl=True)  # 默认启用认证和SSL
    args = parser.parse_args()

    # 创建并启动服务器
    server = AuthenticatedSMTPServer(
        host=args.host,
        port=args.port,
        require_auth=args.auth,
        use_ssl=args.ssl,
        ssl_cert_file=args.cert,
        ssl_key_file=args.key,
    )
    server.start()

    try:
        # 保持程序运行
        # 显示实际使用的端口（可能与指定的端口不同）
        actual_port = server.port

        # 保存实际使用的端口到配置文件
        if args.ssl:
            save_port_config("smtp_ssl_port", actual_port)
            print(f"已保存SMTP SSL端口配置: {actual_port}")
        else:
            save_port_config("smtp_port", actual_port)
            print(f"已保存SMTP端口配置: {actual_port}")

        print(f"认证SMTP服务器已启动: {args.host}:{actual_port}")
        print(f"服务器绑定地址: {args.host}:{actual_port}")
        print(f"认证要求: {'启用' if args.auth else '禁用'}")
        print(f"SSL: {'启用' if args.ssl else '禁用'}")
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
