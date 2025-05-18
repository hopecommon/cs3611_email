"""
电子邮件客户端应用程序入口点
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == "win32":
    try:
        # 尝试设置控制台代码页为UTF-8
        os.system("chcp 65001 > nul")
    except:
        pass

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.utils import setup_logging
from common.config import (
    SMTP_SERVER,
    POP3_SERVER,
    WEB_HOST,
    WEB_PORT,
    SPAM_FILTER_ENABLED,
    PGP_ENABLED,
    RECALL_ENABLED,
)

# 设置日志
logger = setup_logging("main")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="电子邮件客户端应用程序")

    # 主要模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--client", action="store_true", help="启动客户端")
    mode_group.add_argument("--server", action="store_true", help="启动服务器")
    mode_group.add_argument("--web", action="store_true", help="启动Web界面")

    # 服务器选项
    server_group = parser.add_argument_group("服务器选项")
    server_group.add_argument("--smtp", action="store_true", help="启动SMTP服务器")
    server_group.add_argument("--pop3", action="store_true", help="启动POP3服务器")
    server_group.add_argument("--host", type=str, help="服务器主机名")
    server_group.add_argument("--port", type=int, help="服务器端口")

    # 客户端选项
    client_group = parser.add_argument_group("客户端选项")
    client_group.add_argument("--gui", action="store_true", help="启动图形界面")
    client_group.add_argument("--send", type=str, help="发送邮件（指定邮件文件路径）")
    client_group.add_argument("--receive", action="store_true", help="接收邮件")
    client_group.add_argument("--username", type=str, help="认证用户名")
    client_group.add_argument("--password", type=str, help="认证密码")

    # 邮件接收选项
    receive_group = parser.add_argument_group("邮件接收选项")
    receive_group.add_argument("--limit", type=int, help="最多接收的邮件数量")
    receive_group.add_argument(
        "--since", type=str, help="只接收指定日期之后的邮件（格式：YYYY-MM-DD）"
    )
    receive_group.add_argument(
        "--from", dest="from_addr", type=str, help="只接收来自特定发件人的邮件"
    )
    receive_group.add_argument(
        "--subject", type=str, help="只接收主题包含特定字符串的邮件"
    )
    receive_group.add_argument("--unread", action="store_true", help="只接收未读邮件")

    # 扩展功能
    ext_group = parser.add_argument_group("扩展功能")
    ext_group.add_argument(
        "--spam-filter", action="store_true", help="启用垃圾邮件过滤"
    )
    ext_group.add_argument("--pgp", action="store_true", help="启用PGP加密")
    ext_group.add_argument("--recall", action="store_true", help="启用邮件撤回功能")

    return parser.parse_args()


def start_client(args):
    """启动客户端"""
    logger.info("启动客户端...")

    if args.gui:
        logger.info("启动图形界面...")
        # TODO: 导入并启动GUI
        print("GUI功能尚未实现")
    elif args.send:
        logger.info(f"发送邮件: {args.send}")
        try:
            from client.mime_handler import MIMEHandler
            from client.smtp_client import SMTPClient

            # 解析.eml文件
            email = MIMEHandler.parse_eml_file(args.send)

            # 创建SMTP客户端
            smtp_client = SMTPClient(
                host=args.host or SMTP_SERVER["host"],
                port=args.port or SMTP_SERVER["port"],
                use_ssl=SMTP_SERVER["use_ssl"],
                ssl_port=SMTP_SERVER["ssl_port"],
                username=args.username,
                password=args.password,
                save_sent_emails=True,
            )

            # 连接到服务器
            smtp_client.connect()

            # 发送邮件
            smtp_client.send_email(email)

            # 断开连接
            smtp_client.disconnect()

            print(
                f"邮件已成功发送到 {', '.join([addr.address for addr in email.to_addrs])}"
            )
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            print(f"发送邮件失败: {e}")
    elif args.receive:
        logger.info("接收邮件...")
        try:
            from client.pop3_client import POP3Client
            import datetime

            # 创建POP3客户端
            pop3_client = POP3Client(
                host=args.host or POP3_SERVER["host"],
                port=args.port or POP3_SERVER["port"],
                use_ssl=True,  # 强制使用SSL
                ssl_port=POP3_SERVER["ssl_port"],
                username=args.username,
                password=args.password,
            )

            # 连接到服务器
            pop3_client.connect()

            # 获取邮件列表
            emails = pop3_client.list_emails()
            print(f"邮箱中有{len(emails)}封邮件")

            # 处理日期过滤
            since_date = None
            if args.since:
                try:
                    since_date = datetime.datetime.strptime(args.since, "%Y-%m-%d")
                    print(f"只接收 {args.since} 之后的邮件")
                except ValueError:
                    print(f"日期格式错误: {args.since}，应为YYYY-MM-DD格式")
                    since_date = None

            # 获取邮件，应用过滤条件
            received_emails = pop3_client.retrieve_all_emails(
                limit=args.limit,
                since_date=since_date,
                only_unread=args.unread,
                from_addr=args.from_addr,
                subject_contains=args.subject,
            )

            if received_emails:
                print(f"已接收{len(received_emails)}封邮件")
                for email in received_emails:
                    # 保存邮件
                    eml_path = pop3_client.save_email_as_eml(email)
                    print(f"邮件已保存为: {eml_path}")
            else:
                print("没有符合条件的新邮件")

            # 断开连接
            pop3_client.disconnect()
        except Exception as e:
            logger.error(f"接收邮件失败: {e}")
            print(f"接收邮件失败: {e}")
    else:
        logger.error("未指定客户端操作")
        print("请指定客户端操作: --gui, --send 或 --receive")


def start_server(args):
    """启动服务器"""
    logger.info("启动服务器...")

    if args.smtp:
        host = args.host or SMTP_SERVER["host"]
        port = args.port or SMTP_SERVER["port"]
        logger.info(f"启动SMTP服务器: {host}:{port}")
        # TODO: 导入并启动SMTP服务器
        print(f"SMTP服务器功能尚未实现 ({host}:{port})")
    elif args.pop3:
        host = args.host or POP3_SERVER["host"]
        port = args.port or POP3_SERVER["port"]
        logger.info(f"启动POP3服务器: {host}:{port}")
        # TODO: 导入并启动POP3服务器
        print(f"POP3服务器功能尚未实现 ({host}:{port})")
    else:
        logger.error("未指定服务器类型")
        print("请指定服务器类型: --smtp 或 --pop3")


def start_web(args):
    """启动Web界面"""
    logger.info("启动Web界面...")
    host = args.host or WEB_HOST
    port = args.port or WEB_PORT

    # TODO: 导入并启动Web服务器
    print(f"Web界面功能尚未实现 ({host}:{port})")


def main():
    """主函数"""
    args = parse_args()

    # 设置扩展功能
    if args.spam_filter:
        os.environ["SPAM_FILTER_ENABLED"] = "True"
    if args.pgp:
        os.environ["PGP_ENABLED"] = "True"
    if args.recall:
        os.environ["RECALL_ENABLED"] = "True"

    try:
        if args.client:
            start_client(args)
        elif args.server:
            start_server(args)
        elif args.web:
            start_web(args)
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.exception(f"程序异常: {e}")
    finally:
        logger.info("程序退出")


if __name__ == "__main__":
    main()
