# -*- coding: utf-8 -*-
"""
发送邮件菜单模块
"""

import os
import sys
import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.models import Email, EmailAddress, Attachment, EmailStatus
from client.smtp_client import SMTPClient

# 设置日志
logger = setup_logging("send_menu")


class SendEmailMenu:
    """发送邮件菜单"""

    def __init__(self, main_cli):
        """初始化发送邮件菜单"""
        self.main_cli = main_cli
        self.smtp_client = None

    def show_menu(self):
        """显示发送邮件菜单"""
        while True:
            self.main_cli.clear_screen()
            print("\n===== 发送邮件 =====")
            print("1. 创建新邮件")
            print("2. 回复邮件")
            print("3. 转发邮件")
            print("0. 返回主菜单")

            choice = input("\n请选择操作 [0-3]: ")

            if choice == "1":
                self._create_and_send_email()
            elif choice == "2":
                if not self.main_cli.get_current_email():
                    input("请先选择一封邮件，按回车键继续...")
                    continue
                self._reply_email()
            elif choice == "3":
                if not self.main_cli.get_current_email():
                    input("请先选择一封邮件，按回车键继续...")
                    continue
                self._forward_email()
            elif choice == "0":
                return
            else:
                input("无效选择，请按回车键继续...")

    def _init_smtp_client(self):
        """初始化SMTP客户端"""
        if self.smtp_client:
            return True

        try:
            # 使用本地服务器配置
            print("\n请输入SMTP服务器信息:")
            host = input("服务器地址 (默认: localhost): ") or "localhost"
            port = input("端口 (默认: 465): ") or "465"
            username = input("用户名 (默认: testuser): ") or "testuser"
            
            import getpass
            password = getpass.getpass("密码 (默认: testpass): ") or "testpass"
            
            use_ssl = input("使用SSL? (y/n, 默认: y): ").lower() != "n"

            # 创建SMTP客户端
            self.smtp_client = SMTPClient(
                host=host,
                port=int(port),
                use_ssl=use_ssl,
                username=username,
                password=password,
                auth_method="AUTO"
            )
            
            logger.info(f"SMTP客户端已初始化: {host}:{port} (SSL: {use_ssl})")
            return True

        except Exception as e:
            logger.error(f"初始化SMTP客户端失败: {e}")
            print(f"初始化SMTP客户端失败: {e}")
            return False

    def _create_and_send_email(self):
        """创建并发送新邮件"""
        self.main_cli.clear_screen()
        print("\n===== 创建新邮件 =====")

        # 获取邮件信息
        subject = input("主题: ")
        to_addrs = input("收件人 (多个收件人用逗号分隔): ")
        cc_addrs = input("抄送 (可选，多个收件人用逗号分隔): ")
        bcc_addrs = input("密送 (可选，多个收件人用逗号分隔): ")

        print("\n请输入邮件正文 (输入单独一行的 '.' 结束):")
        lines = []
        while True:
            line = input()
            if line == ".":
                break
            lines.append(line)
        text_content = "\n".join(lines)

        # 询问是否添加附件
        attachments = []
        while True:
            add_attachment = input("\n是否添加附件? (y/n): ").lower()
            if add_attachment != "y":
                break

            filepath = input("请输入附件路径: ")
            if not os.path.exists(filepath):
                print(f"文件不存在: {filepath}")
                continue

            try:
                with open(filepath, "rb") as f:
                    content = f.read()

                filename = os.path.basename(filepath)
                content_type = self._guess_content_type(filename)

                attachment = Attachment(
                    filename=filename, content_type=content_type, content=content
                )
                attachments.append(attachment)
                print(f"已添加附件: {filename}")
            except Exception as e:
                print(f"添加附件失败: {e}")

        # 创建邮件对象
        try:
            # 解析收件人地址
            to_addr_list = [
                self._parse_email_address(addr.strip())
                for addr in to_addrs.split(",")
                if addr.strip()
            ]
            cc_addr_list = [
                self._parse_email_address(addr.strip())
                for addr in cc_addrs.split(",")
                if addr.strip()
            ]
            bcc_addr_list = [
                self._parse_email_address(addr.strip())
                for addr in bcc_addrs.split(",")
                if addr.strip()
            ]

            # 确保SMTP客户端已初始化
            if not self._init_smtp_client():
                input("\n按回车键继续...")
                return

            # 创建邮件
            email = Email(
                message_id=f"<{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{id(self)}@localhost>",
                subject=subject,
                from_addr=EmailAddress(name="", address=self.smtp_client.username),
                to_addrs=to_addr_list,
                cc_addrs=cc_addr_list,
                bcc_addrs=bcc_addr_list,
                text_content=text_content,
                attachments=attachments,
                date=None,  # 自动设置为当前时间
                status=EmailStatus.DRAFT,
            )

            # 发送邮件
            print("\n正在发送邮件...")
            result = self.smtp_client.send_email(email)

            if result:
                print("邮件发送成功！")
            else:
                print("邮件发送失败！")
        except Exception as e:
            logger.error(f"发送邮件时出错: {e}")
            print(f"发送邮件时出错: {e}")

        input("\n按回车键继续...")

    def _reply_email(self):
        """回复邮件"""
        print("\n回复邮件功能暂未实现")
        input("按回车键继续...")

    def _forward_email(self):
        """转发邮件"""
        print("\n转发邮件功能暂未实现")
        input("按回车键继续...")

    def _parse_email_address(self, addr_str: str) -> EmailAddress:
        """解析邮件地址字符串为EmailAddress对象"""
        # 简单解析，格式可以是 "名称 <地址>" 或 "地址"
        if "<" in addr_str and ">" in addr_str:
            name = addr_str.split("<")[0].strip()
            address = addr_str.split("<")[1].split(">")[0].strip()
        else:
            name = ""
            address = addr_str.strip()

        return EmailAddress(name=name, address=address)

    def _guess_content_type(self, filename: str) -> str:
        """根据文件名猜测内容类型"""
        import mimetypes

        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"
