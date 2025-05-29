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

    # 加载配置
    config = {}
    if args.config:
        config = load_config(args.config)

    # 获取SMTP设置，确保命令行参数具有最高优先级
    smtp_config = config.get("smtp", {})

    # 主机配置：命令行 > 配置文件 > 默认值
    host = args.host or smtp_config.get("host") or SMTP_SERVER["host"]

    # SSL配置：需要特殊处理以确保命令行优先级
    # 如果用户明确指定了--ssl，使用该设置
    # 如果用户没有指定--ssl，但指定了端口，根据端口判断是否应该使用SSL
    if args.ssl:
        # 用户明确要求SSL
        use_ssl = True
    elif args.port is not None:
        # 用户指定了端口但没有指定SSL，根据端口推断
        # 标准SSL端口(995, 465等)使用SSL，其他端口不使用SSL
        standard_ssl_ports = {995, 465, 993, 587}  # 常见SSL端口
        use_ssl = args.port in standard_ssl_ports
    else:
        # 用户既没有指定SSL也没有指定端口，使用配置文件或默认值
        use_ssl = smtp_config.get("use_ssl") or SMTP_SERVER["use_ssl"]

    # 端口配置：命令行参数具有绝对最高优先级
    cmd_port = args.port if args.port is not None else None
    cmd_ssl_port = args.ssl_port if args.ssl_port is not None else None

    # 根据是否使用SSL选择要解析的端口
    if use_ssl:
        # SSL模式：优先使用用户指定的端口，否则使用SSL端口解析逻辑
        if cmd_port is not None:
            # 用户明确指定了端口，直接使用（即使是非标准SSL端口）
            port = cmd_port
            port_source = "命令行指定端口"
        else:
            # 用户没有指定端口，使用SSL端口解析
            port, changed, message = resolve_port(
                "smtp", cmd_ssl_port, use_ssl=True, auto_detect=False, is_client=True
            )
            port_source = message
    else:
        # 非SSL模式：优先使用用户指定的端口
        if cmd_port is not None:
            # 用户明确指定了端口，直接使用
            port = cmd_port
            port_source = "命令行指定端口"
        else:
            # 用户没有指定端口，使用非SSL端口解析
            port, changed, message = resolve_port(
                "smtp", cmd_port, use_ssl=False, auto_detect=False, is_client=True
            )
            port_source = message

    if port == 0:
        print(f"错误: 无效端口配置")
        sys.exit(1)

    # 显示最终使用的配置（便于用户确认）
    print(
        f"连接配置: {host}:{port} (SSL: {'启用' if use_ssl else '禁用'}) - {port_source}"
    )

    # 获取认证信息
    username = args.username or smtp_config.get("username")
    password = args.password or smtp_config.get("password")

    if args.ask_password or not password:
        password = getpass.getpass("请输入SMTP密码: ")

    # 验证必需的参数
    if not args.from_addr:
        print("错误: 必须指定发件人地址 (--from)")
        sys.exit(1)

    if not args.to_addrs:
        print("错误: 必须指定收件人地址 (--to)")
        sys.exit(1)

    if (
        not args.subject
        and not args.body
        and not args.text
        and not args.html
        and not args.attachment
    ):
        print("错误: 必须指定邮件主题、正文内容或附件")
        sys.exit(1)

    # 创建邮件对象
    email = create_email_from_args(args)

    # 创建SMTP客户端
    smtp_client = SMTPClient(
        host=host,
        port=port,
        use_ssl=use_ssl,
        username=username,
        password=password,
        timeout=getattr(args, "timeout", 30),
        max_retries=getattr(args, "max_retries", 3),
    )

    try:
        # 连接到服务器
        print(f"正在连接到SMTP服务器: {host}:{port}")
        smtp_client.connect()

        # 发送邮件
        result = smtp_client.send_email(email)

        if result:
            print("邮件发送成功!")
            print(
                f"邮件已发送到: {', '.join([addr.address for addr in email.to_addrs])}"
            )
        else:
            print("邮件发送失败!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        print(f"发送邮件失败: {e}")
        if "connection refused" in str(e).lower():
            print(f"连接被拒绝，请检查服务器 {host}:{port} 是否正在运行")
        elif "authentication failed" in str(e).lower():
            print("认证失败，请检查用户名和密码是否正确")
        import traceback

        logger.debug(f"错误详情: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        # 断开连接
        smtp_client.disconnect()


if __name__ == "__main__":
    main()
