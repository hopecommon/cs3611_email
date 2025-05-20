"""
SMTP命令行接口 - 提供命令行发送邮件的功能
"""

import os
import sys
import argparse
import getpass
from typing import List, Optional, Dict, Any
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging, generate_message_id, is_valid_email
from common.models import Email, EmailAddress, Attachment, EmailStatus, EmailPriority
from common.config import SMTP_SERVER
from client.smtp_client import SMTPClient
from client.mime_handler import MIMEHandler
from common.port_config import resolve_port

# 设置日志
logger = setup_logging("smtp_cli")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="SMTP客户端命令行工具")

    # 服务器设置
    server_group = parser.add_argument_group("服务器设置")
    server_group.add_argument("--host", type=str, help="SMTP服务器主机名")
    server_group.add_argument("--port", type=int, help="SMTP服务器端口")
    server_group.add_argument("--ssl", action="store_true", help="使用SSL/TLS")
    server_group.add_argument("--ssl-port", type=int, help="SSL/TLS端口")

    # 认证设置
    auth_group = parser.add_argument_group("认证设置")
    auth_group.add_argument("--username", type=str, help="认证用户名")
    auth_group.add_argument("--password", type=str, help="认证密码")
    auth_group.add_argument("--ask-password", action="store_true", help="提示输入密码")

    # 邮件设置
    mail_group = parser.add_argument_group("邮件设置")
    mail_group.add_argument(
        "--from", dest="from_addr", type=str, required=True, help="发件人地址"
    )
    mail_group.add_argument("--from-name", type=str, help="发件人名称")
    mail_group.add_argument(
        "--to",
        dest="to_addrs",
        type=str,
        required=True,
        help="收件人地址，多个地址用逗号分隔",
    )
    mail_group.add_argument(
        "--cc", dest="cc_addrs", type=str, help="抄送地址，多个地址用逗号分隔"
    )
    mail_group.add_argument(
        "--bcc", dest="bcc_addrs", type=str, help="密送地址，多个地址用逗号分隔"
    )
    mail_group.add_argument("--subject", type=str, required=True, help="邮件主题")
    mail_group.add_argument("--body", type=str, help="邮件正文")
    mail_group.add_argument("--text", type=str, help="邮件正文（与--body相同）")
    mail_group.add_argument("--body-file", type=str, help="包含邮件正文的文件")
    mail_group.add_argument("--html", action="store_true", help="正文是HTML格式")
    mail_group.add_argument(
        "--attachment", action="append", help="附件文件路径，可多次使用"
    )
    mail_group.add_argument(
        "--priority",
        choices=["low", "normal", "high"],
        default="normal",
        help="邮件优先级",
    )

    # 其他选项
    parser.add_argument("--save", type=str, help="保存邮件为.eml文件")
    parser.add_argument("--load", type=str, help="从.eml文件加载邮件")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")

    return parser.parse_args()


def load_config(config_path: str) -> Dict[str, Any]:
    """
    从配置文件加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        logger.info(f"已加载配置文件: {config_path}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        sys.exit(1)


def create_email_from_args(args) -> Email:
    """
    从命令行参数创建Email对象

    Args:
        args: 命令行参数

    Returns:
        Email对象
    """
    # 解析发件人
    from_name = args.from_name or ""
    from_addr = EmailAddress(name=from_name, address=args.from_addr)

    # 解析收件人
    to_addrs = []
    for addr in args.to_addrs.split(","):
        addr = addr.strip()
        if is_valid_email(addr):
            to_addrs.append(EmailAddress(name="", address=addr))
        else:
            logger.warning(f"无效的收件人地址: {addr}")

    # 解析抄送
    cc_addrs = []
    if args.cc_addrs:
        for addr in args.cc_addrs.split(","):
            addr = addr.strip()
            if is_valid_email(addr):
                cc_addrs.append(EmailAddress(name="", address=addr))
            else:
                logger.warning(f"无效的抄送地址: {addr}")

    # 解析密送
    bcc_addrs = []
    if args.bcc_addrs:
        for addr in args.bcc_addrs.split(","):
            addr = addr.strip()
            if is_valid_email(addr):
                bcc_addrs.append(EmailAddress(name="", address=addr))
            else:
                logger.warning(f"无效的密送地址: {addr}")

    # 获取邮件正文
    text_content = ""
    html_content = ""

    # 处理正文内容 (支持--body和--text参数)
    body_content = args.body or args.text
    if body_content:
        if args.html:
            html_content = body_content
        else:
            text_content = body_content
    elif args.body_file:
        try:
            with open(args.body_file, "r", encoding="utf-8") as f:
                content = f.read()

            if args.html:
                html_content = content
            else:
                text_content = content
        except Exception as e:
            logger.error(f"读取正文文件失败: {e}")
            sys.exit(1)

    # 处理附件
    attachments = []
    if args.attachment:
        for file_path in args.attachment:
            try:
                attachment = MIMEHandler.encode_attachment(file_path)
                attachments.append(attachment)
            except Exception as e:
                logger.error(f"处理附件失败: {e}")
                sys.exit(1)

    # 设置优先级
    priority = EmailPriority.NORMAL
    if args.priority == "low":
        priority = EmailPriority.LOW
    elif args.priority == "high":
        priority = EmailPriority.HIGH

    # 创建Email对象
    email = Email(
        message_id=generate_message_id(),
        subject=args.subject,
        from_addr=from_addr,
        to_addrs=to_addrs,
        cc_addrs=cc_addrs,
        bcc_addrs=bcc_addrs,
        text_content=text_content,
        html_content=html_content,
        attachments=attachments,
        date=datetime.now(),
        status=EmailStatus.DRAFT,
        priority=priority,
    )

    return email


def main():
    """主函数"""
    args = parse_args()
    setup_logging("smtp_cli", verbose=args.verbose)

    # 创建邮件对象
    email = create_email_from_args(args)

    # 加载配置
    config = {}
    if args.config:
        config = load_config(args.config)

    # 设置SMTP客户端参数
    smtp_params = {}

    # 服务器设置
    smtp_params["host"] = args.host or config.get("host") or SMTP_SERVER["host"]
    use_ssl = args.ssl or config.get("use_ssl") or SMTP_SERVER["use_ssl"]
    smtp_params["use_ssl"] = use_ssl

    # 使用统一的端口管理逻辑
    cmd_port = args.port if args.port is not None else None
    cmd_ssl_port = args.ssl_port if args.ssl_port is not None else None

    # 根据是否使用SSL选择要解析的端口
    if use_ssl:
        port, changed, message = resolve_port(
            "smtp", cmd_ssl_port, use_ssl=True, auto_detect=False, is_client=True
        )
    else:
        port, changed, message = resolve_port(
            "smtp", cmd_port, use_ssl=False, auto_detect=False, is_client=True
        )

    if port == 0:
        print(f"错误: {message}")
        sys.exit(1)

    if changed:
        print(f"提示: {message}")

    smtp_params["port"] = port

    # 认证设置
    smtp_params["username"] = args.username or config.get("username")

    # 处理密码
    if args.ask_password:
        smtp_params["password"] = getpass.getpass("请输入SMTP密码: ")
    else:
        smtp_params["password"] = args.password or config.get("password")

    # 创建SMTP客户端
    smtp_client = SMTPClient(**smtp_params)

    try:
        # 连接到服务器
        smtp_client.connect()

        # 发送邮件
        smtp_client.send_email(email)

        print(
            f"邮件已成功发送到 {', '.join([addr.address for addr in email.to_addrs])}"
        )

        # 断开连接
        smtp_client.disconnect()
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        print(f"发送邮件失败: {e}")
        if "connection refused" in str(e).lower():
            print(
                f"连接被拒绝，请检查服务器 {smtp_params['host']}:{smtp_params['port']} 是否正在运行"
            )
            print("建议运行 python check_ports.py --check 检查端口配置")
        import traceback

        logger.debug(f"错误详情: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
