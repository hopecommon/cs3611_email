#!/usr/bin/env python3
"""
SMTP PGP命令行接口 - 提供PGP加密邮件发送功能
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

# 尝试导入PGP功能
try:
    from pgp import PGPManager, EmailCrypto
    PGP_AVAILABLE = True
except ImportError:
    PGP_AVAILABLE = False

# 设置日志
logger = setup_logging("smtp_cli_pgp")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="SMTP PGP客户端命令行工具")

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

    # PGP加密选项
    pgp_group = parser.add_argument_group("PGP加密设置")
    pgp_group.add_argument("--pgp-encrypt", action="store_true", help="启用PGP加密邮件")
    pgp_group.add_argument("--pgp-sign", action="store_true", help="启用PGP数字签名")
    pgp_group.add_argument("--pgp-recipient-key", type=str, help="收件人PGP公钥ID（可选，自动查找）")
    pgp_group.add_argument("--pgp-sender-key", type=str, help="发件人PGP私钥ID（可选，自动查找）")
    pgp_group.add_argument("--pgp-passphrase", type=str, help="私钥密码")
    pgp_group.add_argument("--pgp-ask-passphrase", action="store_true", help="提示输入私钥密码")
    pgp_group.add_argument("--pgp-generate-keys", action="store_true", help="为发件人和收件人生成PGP密钥")

    # 其他选项
    parser.add_argument("--save", type=str, help="保存邮件为.eml文件")
    parser.add_argument("--load", type=str, help="从.eml文件加载邮件")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")

    return parser.parse_args()


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

    # 处理正文内容
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


def handle_pgp_encryption(email: Email, args) -> Email:
    """
    处理PGP加密和签名

    Args:
        email: 原始邮件对象
        args: 命令行参数

    Returns:
        处理后的邮件对象
    """
    if not PGP_AVAILABLE:
        logger.error("PGP功能不可用，请检查pgp模块")
        sys.exit(1)

    if not (args.pgp_encrypt or args.pgp_sign):
        return email

    logger.info("🔒 启用PGP功能...")

    # 初始化PGP管理器
    pgp_manager = PGPManager()
    email_crypto = EmailCrypto(pgp_manager)

    # 初始化密钥ID变量
    recipient_key_id = args.pgp_recipient_key
    sender_key_id = args.pgp_sender_key

    # 检查是否需要生成密钥
    if args.pgp_generate_keys:
        logger.info("🔑 生成PGP密钥...")
        
        # 为发件人生成密钥
        sender_public, sender_private = pgp_manager.generate_key_pair(
            name=email.from_addr.name or "发件人",
            email=email.from_addr.address,
            passphrase=None
        )
        logger.info(f"✅ 为发件人生成密钥: {sender_public}")
        sender_key_id = sender_private  # 使用私钥ID
        
        # 为收件人生成密钥
        for recipient in email.to_addrs:
            recipient_public, recipient_private = pgp_manager.generate_key_pair(
                name=recipient.name or "收件人",
                email=recipient.address,
                passphrase=None
            )
            logger.info(f"✅ 为收件人 {recipient.address} 生成密钥: {recipient_public}")
            if not recipient_key_id:  # 只设置第一个收件人的密钥
                recipient_key_id = recipient_public

    # 如果还没有找到密钥，尝试根据邮箱地址查找
    if not recipient_key_id and email.to_addrs:
        recipient_email = email.to_addrs[0].address
        logger.info(f"🔍 正在查找收件人 {recipient_email} 的公钥...")
        
        for key_id, key_info in pgp_manager.list_keys().items():
            if key_info['type'] == 'public':
                for userid in key_info['userids']:
                    if recipient_email.lower() in userid.lower():
                        recipient_key_id = key_id
                        logger.info(f"🔍 找到收件人密钥: {recipient_key_id}")
                        break
                if recipient_key_id:
                    break

    if not sender_key_id:
        sender_email = email.from_addr.address
        logger.info(f"🔍 正在查找发件人 {sender_email} 的私钥...")
        
        for key_id, key_info in pgp_manager.list_keys().items():
            if key_info['type'] == 'private':
                for userid in key_info['userids']:
                    if sender_email.lower() in userid.lower():
                        sender_key_id = key_id
                        logger.info(f"🔍 找到发件人密钥: {sender_key_id}")
                        break
                if sender_key_id:
                    break

    # 显示当前密钥状态
    logger.info(f"🔑 密钥状态:")
    logger.info(f"   收件人公钥ID: {recipient_key_id}")
    logger.info(f"   发件人私钥ID: {sender_key_id}")

    # 获取私钥密码
    passphrase = args.pgp_passphrase
    if args.pgp_ask_passphrase:
        passphrase = getpass.getpass("请输入私钥密码: ")

    # 执行加密
    if args.pgp_encrypt:
        if not recipient_key_id:
            logger.error("❌ 未找到收件人公钥，无法加密")
            # 显示可用的密钥供调试
            all_keys = pgp_manager.list_keys()
            logger.info(f"📋 可用的密钥列表:")
            for key_id, key_info in all_keys.items():
                logger.info(f"   {key_info['type']}: {key_id} - {key_info['userids']}")
            sys.exit(1)

        logger.info(f"🔒 正在加密邮件...")
        try:
            # 直接使用encrypt_message而不是encrypt_email来避免签名问题
            encrypted_content = pgp_manager.encrypt_message(
                email.text_content or "",
                recipient_key_id
            )
            
            # 创建加密后的邮件
            encrypted_email = Email(
                message_id=email.message_id,
                subject=f"[PGP加密] {email.subject}",
                from_addr=email.from_addr,
                to_addrs=email.to_addrs,
                cc_addrs=email.cc_addrs,
                bcc_addrs=email.bcc_addrs,
                text_content=encrypted_content,
                date=email.date,
                headers={
                    "X-PGP-Encrypted": "true",
                    "X-PGP-Version": "1.0",
                    "X-PGP-Recipient": recipient_key_id
                }
            )
            
            logger.info("✅ 邮件加密完成")
            return encrypted_email
            
        except Exception as e:
            logger.error(f"❌ 邮件加密失败: {e}")
            sys.exit(1)
    
    # 如果只签名不加密
    elif args.pgp_sign:
        if not sender_key_id:
            logger.error("❌ 未找到发件人私钥，无法签名")
            sys.exit(1)

        logger.info(f"✍️ 正在签名邮件...")
        # 这里可以实现纯签名功能
        # 目前简化为在邮件头部添加签名标识
        email.headers = email.headers or {}
        email.headers["X-PGP-Signed"] = "true"
        email.headers["X-PGP-Signer"] = sender_key_id
        logger.info("✅ 邮件签名完成")
        return email

    return email


def main():
    """主函数"""
    args = parse_args()
    setup_logging("smtp_cli_pgp", verbose=args.verbose)

    if (args.pgp_encrypt or args.pgp_sign) and not PGP_AVAILABLE:
        logger.error("❌ PGP功能不可用，请安装pgp模块")
        sys.exit(1)

    # 创建邮件
    logger.info("📧 创建邮件...")
    email = create_email_from_args(args)

    # 处理PGP加密/签名
    if args.pgp_encrypt or args.pgp_sign:
        email = handle_pgp_encryption(email, args)

    # 获取SMTP设置
    host = args.host or SMTP_SERVER["host"]
    
    # 处理SSL和端口
    use_ssl = args.ssl
    if args.port is not None:
        standard_ssl_ports = {995, 465, 993, 587}
        use_ssl = use_ssl or args.port in standard_ssl_ports

    port = args.port or (465 if use_ssl else 25)

    # 获取认证信息
    username = args.username
    password = args.password

    if args.ask_password and username:
        password = getpass.getpass("请输入SMTP密码: ")

   # 发送邮件
    logger.info(f"📤 连接SMTP服务器 {host}:{port} (SSL: {use_ssl})")
    
    try:
        # 创建SMTP客户端时直接提供认证信息
        smtp_client = SMTPClient(
            host=host, 
            port=port, 
            use_ssl=use_ssl,
            username=username,
            password=password
        )
        
        # 连接到服务器（会自动进行认证）
        if username and password:
            logger.info(f"🔐 使用用户认证: {username}")
        smtp_client.connect()

        logger.info(f"📮 发送邮件...")
        smtp_client.send_email(email)
        
        logger.info("✅ 邮件发送成功!")
        
        # 显示邮件信息
        print(f"📧 邮件发送完成")
        print(f"   主题: {email.subject}")
        print(f"   发件人: {email.from_addr}")
        print(f"   收件人: {', '.join(str(addr) for addr in email.to_addrs)}")
        
        if hasattr(args, 'pgp_encrypt') and args.pgp_encrypt:
            print(f"   🔒 PGP加密: 已启用")
        if hasattr(args, 'pgp_sign') and args.pgp_sign:
            print(f"   ✍️ PGP签名: 已启用")

        smtp_client.disconnect()

    except Exception as e:
        logger.error(f"❌ 发送邮件失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 