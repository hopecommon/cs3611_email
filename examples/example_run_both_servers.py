#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动稳定的邮件服务器（SMTP + POP3）
"""

import os
import sys
import time
import signal
import threading
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.smtp_server import StableSMTPServer
from server.pop3_server import StablePOP3Server
from common.utils import setup_logging

# 设置日志
logger = setup_logging("run_stable_servers")

# 全局变量
smtp_server = None
pop3_server = None


def signal_handler(sig, frame):
    """信号处理器"""
    logger.info(f"收到信号 {sig}，正在停止服务器...")

    if smtp_server:
        smtp_server.stop()
    if pop3_server:
        pop3_server.stop()

    sys.exit(0)


def main():
    """主函数"""
    global smtp_server, pop3_server

    import argparse

    parser = argparse.ArgumentParser(description="启动稳定的邮件服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--smtp-port", type=int, default=465, help="SMTP端口")
    parser.add_argument("--pop3-port", type=int, default=995, help="POP3端口")
    parser.add_argument("--no-ssl", dest="ssl", action="store_false", help="禁用SSL")
    parser.add_argument("--smtp-only", action="store_true", help="只启动SMTP服务器")
    parser.add_argument("--pop3-only", action="store_true", help="只启动POP3服务器")
    parser.set_defaults(ssl=True)
    args = parser.parse_args()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 启动SMTP服务器
        if not args.pop3_only:
            print(f"启动稳定SMTP服务器: {args.host}:{args.smtp_port}")
            smtp_server = StableSMTPServer(
                host=args.host,
                port=args.smtp_port,
                use_ssl=args.ssl,
                require_auth=True,
            )
            smtp_server.start()
            print(
                f"[OK] SMTP服务器已启动: {args.host}:{args.smtp_port} (SSL: {'启用' if args.ssl else '禁用'})"
            )

        # 启动POP3服务器
        if not args.smtp_only:
            print(f"启动稳定POP3服务器: {args.host}:{args.pop3_port}")
            pop3_server = StablePOP3Server(
                host=args.host,
                port=args.pop3_port,
                use_ssl=args.ssl,
            )
            pop3_server.start()
            print(
                f"[OK] POP3服务器已启动: {args.host}:{args.pop3_port} (SSL: {'启用' if args.ssl else '禁用'})"
            )

        print("\n=== 服务器状态 ===")
        if smtp_server:
            print(
                f"SMTP: {args.host}:{args.smtp_port} (SSL: {'启用' if args.ssl else '禁用'})"
            )
        if pop3_server:
            print(
                f"POP3: {args.host}:{args.pop3_port} (SSL: {'启用' if args.ssl else '禁用'})"
            )

        print("\n按Ctrl+C停止服务器")

        # 保持程序运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("收到键盘中断，停止服务器")
    except Exception as e:
        logger.error(f"启动服务器时出错: {e}")
        return 1
    finally:
        # 停止服务器
        if smtp_server:
            smtp_server.stop()
        if pop3_server:
            pop3_server.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
