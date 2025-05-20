#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
POP3服务器启动脚本
"""

import sys
import argparse
import signal
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.pop3_server import POP3Server
from common.utils import setup_logging
from common.port_config import save_port_config

# 设置日志
logger = setup_logging("run_pop3_server")

# 全局变量
server = None


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="启动POP3服务器")
    parser.add_argument(
        "--host", type=str, default="localhost", help="服务器主机名或IP地址"
    )
    parser.add_argument("--port", type=int, default=110, help="服务器端口")
    parser.add_argument("--ssl", action="store_true", help="是否使用SSL/TLS")
    parser.add_argument("--ssl-port", type=int, default=995, help="SSL/TLS端口")
    parser.add_argument("--max-connections", type=int, default=10, help="最大连接数")
    parser.add_argument(
        "--ssl-cert", type=str, default="certs/server.crt", help="SSL证书文件"
    )
    parser.add_argument(
        "--ssl-key", type=str, default="certs/server.key", help="SSL密钥文件"
    )
    return parser.parse_args()


def signal_handler(sig, _):
    """处理信号"""
    logger.info(f"收到信号 {sig}，正在停止服务器...")
    if server:
        server.stop()
    sys.exit(0)


def main():
    """主函数"""
    global server

    # 解析命令行参数
    args = parse_args()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建服务器
    try:
        # 检查SSL证书文件是否存在
        if args.ssl:
            ssl_cert_path = Path(args.ssl_cert)
            ssl_key_path = Path(args.ssl_key)

            if not ssl_cert_path.exists():
                logger.error(f"SSL证书文件不存在: {args.ssl_cert}")
                print(f"错误: SSL证书文件不存在: {args.ssl_cert}")
                print("创建临时自签名证书...")

                # 如果证书不存在，尝试创建证书目录
                certs_dir = Path("certs")
                certs_dir.mkdir(exist_ok=True)

                # 尝试使用 OpenSSL 创建自签名证书
                try:
                    import os

                    # 创建自签名证书
                    cert_cmd = f'openssl req -x509 -newkey rsa:4096 -keyout {args.ssl_key} -out {args.ssl_cert} -days 365 -nodes -subj "/CN=localhost"'
                    os.system(cert_cmd)
                    print(f"已创建临时自签名证书: {args.ssl_cert}")
                except Exception as e:
                    print(f"创建证书时出错: {e}")
                    print("请手动创建SSL证书或禁用SSL模式")
                    return 1

            if not ssl_key_path.exists():
                logger.error(f"SSL密钥文件不存在: {args.ssl_key}")
                print(f"错误: SSL密钥文件不存在: {args.ssl_key}")
                return 1

            print(f"使用SSL证书: {args.ssl_cert}")
            print(f"使用SSL密钥: {args.ssl_key}")

        # 创建POP3服务器
        # 如果启用SSL，使用指定的SSL端口
        port = args.ssl_port if args.ssl else args.port

        # 确保端口使用指定的值
        print(
            f"启动POP3服务器在端口 {port} {'(SSL模式)' if args.ssl else '(非SSL模式)'}"
        )

        server = POP3Server(
            host=args.host,
            port=port,
            use_ssl=args.ssl,
            ssl_port=args.ssl_port,
            max_connections=args.max_connections,
            ssl_cert_file=args.ssl_cert,
            ssl_key_file=args.ssl_key,
        )

        # 启动服务器
        server.start()

        # 保持程序运行
        # 显示实际使用的端口（可能与指定的端口不同）
        actual_port = server.port

        # 保存实际使用的端口到配置文件
        if args.ssl:
            save_port_config("pop3_ssl_port", actual_port)
            print(f"已保存POP3 SSL端口配置: {actual_port}")
        else:
            save_port_config("pop3_port", actual_port)
            print(f"已保存POP3端口配置: {actual_port}")

        print(f"POP3服务器已启动: {args.host}:{actual_port}")
        print(f"服务器绑定地址: {args.host}:{actual_port}")
        print(f"SSL: {'启用' if args.ssl else '禁用'}")
        print("按Ctrl+C停止服务器")

        # 保持程序运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到键盘中断，停止服务器")
    except Exception as e:
        logger.error(f"启动POP3服务器时出错: {e}")
        import traceback

        logger.error(f"异常详情: {traceback.format_exc()}")
        return 1
    finally:
        # 停止服务器
        if server:
            server.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
