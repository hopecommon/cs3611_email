#!/usr/bin/env python
"""
交互式命令行界面 - 提供基于菜单的邮件客户端操作界面
"""

import os
import sys
import argparse
import getpass
import datetime
from typing import List, Dict, Any, Optional

from common.utils import setup_logging
from common.models import Email, EmailAddress, Attachment, EmailStatus
from client.smtp_client import SMTPClient
from client.pop3_client_refactored import POP3Client
from server.new_db_handler import EmailService
from common.config import SMTP_SERVER, POP3_SERVER, EMAIL_STORAGE_DIR, DB_PATH

# 设置日志
logger = setup_logging("cli")


class EmailCLI:
    """邮件客户端命令行界面"""

    def __init__(self):
        """初始化命令行界面"""
        self.db = EmailService()  # 使用新的EmailService接口
        self.smtp_client = None
        self.pop3_client = None
        self.current_email = None
        self.email_list = []
        self.current_folder = "inbox"  # inbox 或 sent

    def main_menu(self):
        """显示主菜单并处理用户输入"""
        while True:
            self._clear_screen()
            print("\n===== 邮件客户端 =====")
            print("1. 发送邮件")
            print("2. 接收邮件")
            print("3. 查看邮件列表")
            print("4. 搜索邮件")
            print("5. 账户设置")
            print("0. 退出")

            choice = input("\n请选择操作 [0-5]: ")

            if choice == "1":
                self.send_email_menu()
            elif choice == "2":
                self.receive_email_menu()
            elif choice == "3":
                self.view_emails_menu()
            elif choice == "4":
                self.search_emails_menu()
            elif choice == "5":
                self.account_settings_menu()
            elif choice == "0":
                print("感谢使用，再见！")
                sys.exit(0)
            else:
                input("无效选择，请按回车键继续...")

    def send_email_menu(self):
        """发送邮件菜单"""
        while True:
            self._clear_screen()
            print("\n===== 发送邮件 =====")
            print("1. 创建新邮件")
            print("2. 回复邮件")
            print("3. 转发邮件")
            print("0. 返回主菜单")

            choice = input("\n请选择操作 [0-3]: ")

            if choice == "1":
                self._create_and_send_email()
            elif choice == "2":
                if not self.current_email:
                    input("请先选择一封邮件，按回车键继续...")
                    continue
                self._reply_email()
            elif choice == "3":
                if not self.current_email:
                    input("请先选择一封邮件，按回车键继续...")
                    continue
                self._forward_email()
            elif choice == "0":
                return
            else:
                input("无效选择，请按回车键继续...")

    def receive_email_menu(self):
        """接收邮件菜单"""
        while True:
            self._clear_screen()
            print("\n===== 接收邮件 =====")
            print("1. 接收所有邮件")
            print("2. 接收最新邮件")
            print("3. 接收未读邮件")
            print("4. 设置过滤条件")
            print("0. 返回主菜单")

            choice = input("\n请选择操作 [0-4]: ")

            if choice == "1":
                self._receive_all_emails()
            elif choice == "2":
                self._receive_latest_emails()
            elif choice == "3":
                self._receive_unread_emails()
            elif choice == "4":
                self._set_email_filters()
            elif choice == "0":
                return
            else:
                input("无效选择，请按回车键继续...")

    def view_emails_menu(self):
        """查看邮件列表菜单"""
        while True:
            self._clear_screen()
            print("\n===== 查看邮件 =====")
            print("1. 收件箱")
            print("2. 已发送")
            print("3. 查看邮件详情")
            print("4. 删除邮件")
            print("5. 标记为已读/未读")
            print("0. 返回主菜单")

            choice = input("\n请选择操作 [0-5]: ")

            if choice == "1":
                self.current_folder = "inbox"
                self._list_emails()
            elif choice == "2":
                self.current_folder = "sent"
                self._list_emails()
            elif choice == "3":
                if not self.email_list:
                    input("邮件列表为空，请先获取邮件，按回车键继续...")
                    continue
                self._view_email_details()
            elif choice == "4":
                if not self.email_list:
                    input("邮件列表为空，请先获取邮件，按回车键继续...")
                    continue
                self._delete_email()
            elif choice == "5":
                if not self.email_list:
                    input("邮件列表为空，请先获取邮件，按回车键继续...")
                    continue
                self._toggle_read_status()
            elif choice == "0":
                return
            else:
                input("无效选择，请按回车键继续...")

    def search_emails_menu(self):
        """搜索邮件菜单"""
        while True:
            self._clear_screen()
            print("\n===== 搜索邮件 =====")
            print("1. 按发件人搜索")
            print("2. 按主题搜索")
            print("3. 按内容搜索")
            print("4. 按日期搜索")
            print("5. 高级搜索")
            print("0. 返回主菜单")

            choice = input("\n请选择操作 [0-5]: ")

            if choice == "1":
                self._search_by_sender()
            elif choice == "2":
                self._search_by_subject()
            elif choice == "3":
                self._search_by_content()
            elif choice == "4":
                self._search_by_date()
            elif choice == "5":
                self._advanced_search()
            elif choice == "0":
                return
            else:
                input("无效选择，请按回车键继续...")

    def account_settings_menu(self):
        """账户设置菜单"""
        while True:
            self._clear_screen()
            print("\n===== 账户设置 =====")
            print("1. 设置SMTP服务器")
            print("2. 设置POP3服务器")
            print("3. 查看当前设置")
            print("0. 返回主菜单")

            choice = input("\n请选择操作 [0-3]: ")

            if choice == "1":
                self._set_smtp_server()
            elif choice == "2":
                self._set_pop3_server()
            elif choice == "3":
                self._view_current_settings()
            elif choice == "0":
                return
            else:
                input("无效选择，请按回车键继续...")

    # 辅助方法
    def _clear_screen(self):
        """清屏"""
        os.system("cls" if os.name == "nt" else "clear")

    def _create_and_send_email(self):
        """创建并发送新邮件"""
        self._clear_screen()
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
            if not self.smtp_client:
                self._init_smtp_client()

            # 创建邮件
            email = Email(
                message_id=f"<{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{id(self)}@example.com>",
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
            self.smtp_client.connect()
            result = self.smtp_client.send_email(email)
            self.smtp_client.disconnect()

            if result:
                print("邮件发送成功！")
            else:
                print("邮件发送失败！")
        except Exception as e:
            print(f"发送邮件时出错: {e}")

        input("\n按回车键继续...")

    def _init_smtp_client(self):
        """初始化SMTP客户端"""
        # 如果已经有配置，使用现有配置
        if hasattr(self, "smtp_config") and self.smtp_config:
            config = self.smtp_config
        else:
            # 否则使用默认配置
            config = SMTP_SERVER.copy()  # 创建副本，避免修改原始配置

            # 如果没有用户名和密码，请求输入
            if not config.get("username") or not config.get("password"):
                print("\n请输入SMTP服务器账号信息:")
                config["username"] = input("用户名: ")
                config["password"] = getpass.getpass("密码: ")

        # 确保所有字符串都是 str 类型，而不是 bytes 类型
        host = str(config.get("host", ""))
        username = str(config.get("username", ""))
        password = str(config.get("password", ""))

        # 创建SMTP客户端
        self.smtp_client = SMTPClient(
            host=host,
            port=config.get("port"),
            use_ssl=config.get("use_ssl", True),
            username=username,
            password=password,
            auth_method=config.get("auth_method", "AUTO"),
        )

    def _init_pop3_client(self):
        """初始化POP3客户端"""
        # 如果已经有配置，使用现有配置
        if hasattr(self, "pop3_config") and self.pop3_config:
            config = self.pop3_config
        else:
            # 否则使用默认配置
            config = POP3_SERVER.copy()  # 创建副本，避免修改原始配置

            # 如果没有用户名和密码，请求输入
            if not config.get("username") or not config.get("password"):
                print("\n请输入POP3服务器账号信息:")
                config["username"] = input("用户名: ")
                config["password"] = getpass.getpass("密码: ")

        # 确保所有字符串都是 str 类型，而不是 bytes 类型
        host = str(config.get("host", ""))
        username = str(config.get("username", ""))
        password = str(config.get("password", ""))

        # 创建POP3客户端
        self.pop3_client = POP3Client(
            host=host,
            port=config.get("port"),
            use_ssl=config.get("use_ssl", True),
            username=username,
            password=password,
            auth_method=config.get("auth_method", "AUTO"),
        )

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

    def _receive_all_emails(self):
        """接收所有邮件"""
        try:
            # 确保POP3客户端已初始化
            if not self.pop3_client:
                self._init_pop3_client()

            print("\n正在连接到邮箱...")
            self.pop3_client.connect()

            # 获取邮箱状态
            status = self.pop3_client.get_mailbox_status()
            print(f"邮箱状态: {status[0]}封邮件, {status[1]}字节")

            # 获取所有邮件
            print("正在获取邮件...")
            emails = self.pop3_client.retrieve_all_emails(delete=False)

            # 断开连接
            self.pop3_client.disconnect()

            # 保存邮件
            print(f"成功获取了{len(emails)}封邮件，正在保存...")
            for email in emails:
                filepath = self.pop3_client.save_email_as_eml(email, EMAIL_STORAGE_DIR)
                print(f"已保存邮件: {os.path.basename(filepath)}")

            print(f"所有邮件已保存到: {EMAIL_STORAGE_DIR}")
        except Exception as e:
            print(f"接收邮件时出错: {e}")

        input("\n按回车键继续...")

    def _receive_latest_emails(self):
        """接收最新邮件"""
        try:
            # 确保POP3客户端已初始化
            if not self.pop3_client:
                self._init_pop3_client()

            # 获取要接收的邮件数量
            try:
                num = int(input("\n请输入要接收的最新邮件数量: "))
                if num <= 0:
                    print("数量必须大于0")
                    return
            except ValueError:
                print("请输入有效的数字")
                return

            print("\n正在连接到邮箱...")
            self.pop3_client.connect()

            # 获取邮件列表
            email_list = self.pop3_client.list_emails()

            if not email_list:
                print("邮箱中没有邮件")
                self.pop3_client.disconnect()
                return

            # 获取最新的N封邮件
            latest_emails = email_list[-num:] if len(email_list) >= num else email_list

            print(f"正在获取最新的{len(latest_emails)}封邮件...")
            emails = []
            for msg_num, _ in latest_emails:
                email = self.pop3_client.retrieve_email(msg_num, delete=False)
                if email:
                    emails.append(email)
                    print(f"已获取邮件: {email.subject}")

            # 断开连接
            self.pop3_client.disconnect()

            # 保存邮件
            print(f"成功获取了{len(emails)}封邮件，正在保存...")
            for email in emails:
                filepath = self.pop3_client.save_email_as_eml(email, EMAIL_STORAGE_DIR)
                print(f"已保存邮件: {os.path.basename(filepath)}")

            print(f"所有邮件已保存到: {EMAIL_STORAGE_DIR}")
        except Exception as e:
            print(f"接收邮件时出错: {e}")

        input("\n按回车键继续...")

    def _receive_unread_emails(self):
        """接收未读邮件"""
        print("\n注意: POP3协议不支持直接获取未读邮件。")
        print("此功能将获取所有邮件，并在本地标记为未读。")
        input("按回车键继续...")
        self._receive_all_emails()

    def _set_email_filters(self):
        """设置邮件过滤条件"""
        self._clear_screen()
        print("\n===== 设置邮件过滤条件 =====")
        print("注意: 过滤条件将应用于下次接收邮件时")

        # 获取过滤条件
        sender = input("发件人 (留空表示不过滤): ")
        subject = input("主题包含 (留空表示不过滤): ")
        since_date = input("起始日期 (格式: YYYY-MM-DD, 留空表示不过滤): ")

        # 保存过滤条件
        self.email_filters = {
            "sender": sender if sender else None,
            "subject": subject if subject else None,
            "since_date": since_date if since_date else None,
        }

        print("\n过滤条件已设置")
        input("按回车键继续...")

    def _list_emails(self):
        """列出邮件"""
        self._clear_screen()
        folder = "已发送" if self.current_folder == "sent" else "收件箱"
        print(f"\n===== {folder} =====")

        # 从数据库获取邮件列表
        try:
            if self.current_folder == "sent":
                emails = self.db.list_sent_emails()
            else:
                emails = self.db.list_emails()

            if not emails:
                print(f"{folder}中没有邮件")
                input("\n按回车键继续...")
                return

            # 保存邮件列表
            self.email_list = emails

            # 显示邮件列表
            print(f"{'ID':<5} {'状态':<4} {'日期':<20} {'发件人':<30} {'主题':<40}")
            print("-" * 100)

            for i, email in enumerate(emails):
                status = "已读" if email.get("is_read") else "未读"
                date = email.get("date", "")
                sender = email.get("from_addr", email.get("sender", ""))
                subject = email.get("subject", "")

                print(f"{i+1:<5} {status:<4} {date:<20} {sender:<30} {subject:<40}")

            # 选择邮件
            while True:
                choice = input("\n请输入要查看的邮件ID (或按回车返回): ")
                if not choice:
                    return

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(emails):
                        self.current_email = emails[idx]
                        self._view_email_details()
                        break
                    else:
                        print("无效的ID")
                except ValueError:
                    print("请输入有效的数字")
        except Exception as e:
            print(f"获取邮件列表时出错: {e}")
            input("\n按回车键继续...")

    def _view_email_details(self):
        """查看邮件详情"""
        if not self.current_email:
            print("未选择邮件")
            input("\n按回车键继续...")
            return

        self._clear_screen()
        print("\n===== 邮件详情 =====")

        # 显示邮件基本信息
        print(f"主题: {self.current_email.get('subject', '')}")
        print(f"发件人: {self.current_email.get('sender', '')}")
        print(f"收件人: {self.current_email.get('recipients', '')}")
        print(f"日期: {self.current_email.get('date', '')}")

        # 获取完整邮件内容
        try:
            message_id = self.current_email.get("message_id")

            # 根据邮件类型选择不同的获取方法
            email_type = self.current_email.get("type", "received")
            if email_type == "sent":
                content_str = self.db.get_sent_email_content(message_id)
            else:
                content_str = self.db.get_email_content(message_id)

            if content_str:
                # 解析邮件内容
                from email import policy
                from email.parser import Parser

                # 解析邮件
                msg = Parser(policy=policy.default).parsestr(content_str)

                # 提取内容
                text_content = ""
                html_content = ""
                attachments = []

                # 处理邮件部分
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    # 处理纯文本内容
                    if (
                        content_type == "text/plain"
                        and "attachment" not in content_disposition
                    ):
                        text_content += part.get_content()

                    # 处理HTML内容
                    elif (
                        content_type == "text/html"
                        and "attachment" not in content_disposition
                    ):
                        html_content += part.get_content()

                    # 处理附件
                    elif "attachment" in content_disposition or content_type.startswith(
                        "application/"
                    ):
                        filename = part.get_filename()
                        if filename:
                            content = part.get_payload(decode=True)
                            attachments.append(
                                {
                                    "filename": filename,
                                    "content_type": content_type,
                                    "content": content,
                                }
                            )

                # 显示邮件内容
                print("\n----- 邮件正文 -----")
                if html_content:
                    print("[HTML内容可用]")
                    view_html = input("是否查看HTML内容? (y/n): ").lower() == "y"
                    if view_html:
                        print("\n" + html_content)
                    else:
                        print("\n" + (text_content or "无纯文本内容"))
                else:
                    print("\n" + (text_content or "无内容"))

                # 显示附件信息
                if attachments:
                    print("\n----- 附件 -----")
                    for i, attachment in enumerate(attachments):
                        print(
                            f"{i+1}. {attachment.get('filename')} ({attachment.get('content_type')})"
                        )

                    # 提供保存附件选项
                    save_option = input("\n是否保存附件? (y/n): ").lower()
                    if save_option == "y":
                        attachment_idx = input(
                            "请输入要保存的附件编号 (或输入'all'保存所有): "
                        )
                        if attachment_idx.lower() == "all":
                            # 保存所有附件
                            for attachment in attachments:
                                self._save_attachment(attachment)
                        else:
                            try:
                                idx = int(attachment_idx) - 1
                                if 0 <= idx < len(attachments):
                                    self._save_attachment(attachments[idx])
                                else:
                                    print("无效的附件编号")
                            except ValueError:
                                print("请输入有效的数字")
            else:
                print("\n无法获取邮件内容")
        except Exception as e:
            print(f"查看邮件详情时出错: {e}")

        # 标记为已读
        try:
            if not self.current_email.get("is_read"):
                self.db.update_email(self.current_email.get("message_id"), is_read=True)
                print("\n邮件已标记为已读")
        except Exception as e:
            print(f"标记邮件为已读时出错: {e}")

        input("\n按回车键继续...")

    def _save_attachment(self, attachment):
        """保存附件"""
        try:
            filename = attachment.get("filename")
            content = attachment.get("content")

            if not filename or not content:
                print("附件信息不完整")
                return

            # 获取保存路径
            save_dir = input(f"请输入保存目录 (默认为当前目录): ") or "."
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            filepath = os.path.join(save_dir, filename)

            # 检查文件是否已存在
            if os.path.exists(filepath):
                overwrite = input(f"文件 {filename} 已存在，是否覆盖? (y/n): ").lower()
                if overwrite != "y":
                    new_filename = input("请输入新的文件名: ")
                    filepath = os.path.join(save_dir, new_filename)

            # 保存文件
            with open(filepath, "wb") as f:
                f.write(content)

            print(f"附件已保存到: {filepath}")
        except Exception as e:
            print(f"保存附件时出错: {e}")

    def _delete_email(self):
        """删除邮件"""
        if not self.email_list:
            print("邮件列表为空")
            input("\n按回车键继续...")
            return

        # 选择要删除的邮件
        self._clear_screen()
        print("\n===== 删除邮件 =====")

        print(f"{'ID':<5} {'状态':<4} {'日期':<20} {'发件人':<30} {'主题':<40}")
        print("-" * 100)

        for i, email in enumerate(self.email_list):
            status = "已读" if email.get("is_read") else "未读"
            date = email.get("date", "")
            sender = email.get("from_addr", email.get("sender", ""))
            subject = email.get("subject", "")

            print(f"{i+1:<5} {status:<4} {date:<20} {sender:<30} {subject:<40}")

        # 选择邮件
        choice = input("\n请输入要删除的邮件ID (或按回车返回): ")
        if not choice:
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.email_list):
                email = self.email_list[idx]
                confirm = input(
                    f"确定要删除邮件 '{email.get('subject')}'? (y/n): "
                ).lower()

                if confirm == "y":
                    # 删除邮件
                    try:
                        message_id = email.get("message_id")
                        self.db.update_email(message_id, is_deleted=True)
                        print("邮件已标记为删除")

                        # 更新邮件列表
                        self.email_list.pop(idx)
                    except Exception as e:
                        print(f"删除邮件时出错: {e}")
            else:
                print("无效的ID")
        except ValueError:
            print("请输入有效的数字")

        input("\n按回车键继续...")

    def _toggle_read_status(self):
        """切换邮件已读/未读状态"""
        if not self.email_list:
            print("邮件列表为空")
            input("\n按回车键继续...")
            return

        # 选择要切换状态的邮件
        self._clear_screen()
        print("\n===== 切换邮件状态 =====")

        print(f"{'ID':<5} {'状态':<4} {'日期':<20} {'发件人':<30} {'主题':<40}")
        print("-" * 100)

        for i, email in enumerate(self.email_list):
            status = "已读" if email.get("is_read") else "未读"
            date = email.get("date", "")
            sender = email.get("from_addr", email.get("sender", ""))
            subject = email.get("subject", "")

            print(f"{i+1:<5} {status:<4} {date:<20} {sender:<30} {subject:<40}")

        # 选择邮件
        choice = input("\n请输入要切换状态的邮件ID (或按回车返回): ")
        if not choice:
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.email_list):
                email = self.email_list[idx]
                is_read = email.get("is_read", False)

                # 切换状态
                try:
                    message_id = email.get("message_id")
                    if is_read:
                        # 使用EmailService的update_email方法
                        self.db.update_email(message_id, is_read=False)
                        print("邮件已标记为未读")
                    else:
                        self.db.update_email(message_id, is_read=True)
                        print("邮件已标记为已读")

                    # 更新邮件列表中的状态
                    self.email_list[idx]["is_read"] = not is_read
                except Exception as e:
                    print(f"切换邮件状态时出错: {e}")
            else:
                print("无效的ID")
        except ValueError:
            print("请输入有效的数字")

        input("\n按回车键继续...")

    def _search_by_sender(self):
        """按发件人搜索邮件"""
        self._clear_screen()
        print("\n===== 按发件人搜索 =====")

        sender = input("请输入发件人: ")
        if not sender:
            print("发件人不能为空")
            input("\n按回车键继续...")
            return

        try:
            # 搜索邮件
            emails = self.db.search_emails(sender, search_fields=["from_addr"])

            if not emails:
                print(f"未找到发件人包含 '{sender}' 的邮件")
                input("\n按回车键继续...")
                return

            # 显示搜索结果
            self._display_search_results(emails, f"发件人包含 '{sender}' 的邮件")
        except Exception as e:
            print(f"搜索邮件时出错: {e}")
            input("\n按回车键继续...")

    def _search_by_subject(self):
        """按主题搜索邮件"""
        self._clear_screen()
        print("\n===== 按主题搜索 =====")

        subject = input("请输入主题关键词: ")
        if not subject:
            print("主题关键词不能为空")
            input("\n按回车键继续...")
            return

        try:
            # 搜索邮件
            emails = self.db.search_emails(subject, search_fields=["subject"])

            if not emails:
                print(f"未找到主题包含 '{subject}' 的邮件")
                input("\n按回车键继续...")
                return

            # 显示搜索结果
            self._display_search_results(emails, f"主题包含 '{subject}' 的邮件")
        except Exception as e:
            print(f"搜索邮件时出错: {e}")
            input("\n按回车键继续...")

    def _search_by_content(self):
        """按内容搜索邮件"""
        self._clear_screen()
        print("\n===== 按内容搜索 =====")

        content = input("请输入内容关键词: ")
        if not content:
            print("内容关键词不能为空")
            input("\n按回车键继续...")
            return

        try:
            # 搜索邮件，暂时使用主题和发件人字段搜索
            # 注意：新的search_emails还不直接支持内容搜索，这里使用基本字段搜索
            emails = self.db.search_emails(
                content, search_fields=["subject", "from_addr"]
            )

            if not emails:
                print(f"未找到内容包含 '{content}' 的邮件")
                input("\n按回车键继续...")
                return

            # 显示搜索结果
            self._display_search_results(emails, f"内容包含 '{content}' 的邮件")
        except Exception as e:
            print(f"搜索邮件时出错: {e}")
            input("\n按回车键继续...")

    def _search_by_date(self):
        """按日期搜索邮件"""
        self._clear_screen()
        print("\n===== 按日期搜索 =====")

        date = input("请输入日期 (格式: YYYY-MM-DD): ")
        if not date:
            print("日期不能为空")
            input("\n按回车键继续...")
            return

        try:
            # 验证日期格式
            target_date = datetime.datetime.strptime(date, "%Y-%m-%d")

            # 使用新的EmailService获取所有邮件然后过滤
            all_emails = self.db.list_emails(limit=10000)  # 获取大量邮件

            # 按日期过滤
            emails = []
            for email in all_emails:
                email_date_str = email.get("date", "")
                try:
                    if email_date_str:
                        # 尝试解析日期
                        if isinstance(email_date_str, str):
                            email_date = datetime.datetime.fromisoformat(email_date_str)
                        else:
                            continue

                        # 检查是否是同一天
                        if email_date.date() == target_date.date():
                            emails.append(email)
                except (ValueError, TypeError):
                    continue

            if not emails:
                print(f"未找到日期为 '{date}' 的邮件")
                input("\n按回车键继续...")
                return

            # 显示搜索结果
            self._display_search_results(emails, f"日期为 '{date}' 的邮件")
        except ValueError:
            print("日期格式无效，请使用 YYYY-MM-DD 格式")
            input("\n按回车键继续...")
        except Exception as e:
            print(f"搜索邮件时出错: {e}")
            input("\n按回车键继续...")

    def _advanced_search(self):
        """高级搜索"""
        self._clear_screen()
        print("\n===== 高级搜索 =====")

        # 获取搜索条件
        sender = input("发件人 (留空表示不限): ")
        subject = input("主题包含 (留空表示不限): ")
        content = input("内容包含 (留空表示不限): ")
        date_from = input("起始日期 (格式: YYYY-MM-DD, 留空表示不限): ")
        date_to = input("结束日期 (格式: YYYY-MM-DD, 留空表示不限): ")
        include_sent = input("包含已发送邮件? (y/n, 默认y): ").lower() != "n"
        include_received = input("包含收到的邮件? (y/n, 默认y): ").lower() != "n"

        # 构建搜索条件
        search_params = {}
        if sender:
            search_params["sender"] = sender
        if subject:
            search_params["subject"] = subject
        if content:
            search_params["content"] = content
        if date_from:
            try:
                search_params["date_from"] = datetime.datetime.strptime(
                    date_from, "%Y-%m-%d"
                )
            except ValueError:
                print("起始日期格式无效，将被忽略")
        if date_to:
            try:
                search_params["date_to"] = datetime.datetime.strptime(
                    date_to, "%Y-%m-%d"
                )
            except ValueError:
                print("结束日期格式无效，将被忽略")

        try:
            # 搜索邮件 - 使用新的EmailService的search_emails方法
            # 构建搜索关键词
            search_terms = []
            if sender:
                search_terms.append(sender)
            if subject:
                search_terms.append(subject)
            if content:
                search_terms.append(content)

            if search_terms:
                query = " ".join(search_terms)
                emails = self.db.search_emails(
                    query,
                    include_sent=include_sent,
                    include_received=include_received,
                    limit=100,
                )
            else:
                # 如果没有搜索条件，获取所有邮件
                received_emails = (
                    self.db.list_emails(limit=100) if include_received else []
                )
                sent_emails = (
                    self.db.list_sent_emails(limit=100) if include_sent else []
                )
                emails = received_emails + sent_emails

                # 添加type字段以区分邮件类型
                for email in received_emails:
                    email["type"] = "received"
                for email in sent_emails:
                    email["type"] = "sent"

            if not emails:
                print("未找到符合条件的邮件")
                input("\n按回车键继续...")
                return

            # 显示搜索结果
            self._display_search_results(emails, "高级搜索结果")
        except Exception as e:
            print(f"搜索邮件时出错: {e}")
            input("\n按回车键继续...")

    def _display_search_results(self, emails, title):
        """显示搜索结果"""
        self._clear_screen()
        print(f"\n===== {title} =====")

        # 保存邮件列表
        self.email_list = emails

        # 显示邮件列表
        print(f"{'ID':<5} {'状态':<4} {'日期':<20} {'发件人':<30} {'主题':<40}")
        print("-" * 100)

        for i, email in enumerate(emails):
            status = "已读" if email.get("is_read") else "未读"
            date = email.get("date", "")
            sender = email.get("from_addr", email.get("sender", ""))
            subject = email.get("subject", "")

            print(f"{i+1:<5} {status:<4} {date:<20} {sender:<30} {subject:<40}")

        # 选择邮件
        while True:
            choice = input("\n请输入要查看的邮件ID (或按回车返回): ")
            if not choice:
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(emails):
                    self.current_email = emails[idx]
                    self._view_email_details()
                    break
                else:
                    print("无效的ID")
            except ValueError:
                print("请输入有效的数字")

    def _set_smtp_server(self):
        """设置SMTP服务器"""
        self._clear_screen()
        print("\n===== 设置SMTP服务器 =====")

        host = input(
            f"服务器地址 (默认: {SMTP_SERVER.get('host', '')}): "
        ) or SMTP_SERVER.get("host", "")
        port = input(
            f"端口 (默认: {SMTP_SERVER.get('port', '')}): "
        ) or SMTP_SERVER.get("port", "")
        use_ssl = input(
            f"使用SSL (y/n, 默认: {'y' if SMTP_SERVER.get('use_ssl', True) else 'n'}): "
        )
        use_ssl = (
            use_ssl.lower() == "y" if use_ssl else SMTP_SERVER.get("use_ssl", True)
        )
        username = input(
            f"用户名 (默认: {SMTP_SERVER.get('username', '')}): "
        ) or SMTP_SERVER.get("username", "")
        password = getpass.getpass(f"密码 (留空使用默认): ") or SMTP_SERVER.get(
            "password", ""
        )
        auth_method = input(
            f"认证方法 (AUTO/LOGIN/PLAIN, 默认: {SMTP_SERVER.get('auth_method', 'AUTO')}): "
        ) or SMTP_SERVER.get("auth_method", "AUTO")

        # 保存设置
        self.smtp_config = {
            "host": host,
            "port": int(port) if port.isdigit() else port,
            "use_ssl": use_ssl,
            "username": username,
            "password": password,
            "auth_method": auth_method,
        }

        # 重新初始化SMTP客户端
        if self.smtp_client:
            self.smtp_client = None

        print("\nSMTP服务器设置已保存")
        input("按回车键继续...")

    def _set_pop3_server(self):
        """设置POP3服务器"""
        self._clear_screen()
        print("\n===== 设置POP3服务器 =====")

        host = input(
            f"服务器地址 (默认: {POP3_SERVER.get('host', '')}): "
        ) or POP3_SERVER.get("host", "")
        port = input(
            f"端口 (默认: {POP3_SERVER.get('port', '')}): "
        ) or POP3_SERVER.get("port", "")
        use_ssl = input(
            f"使用SSL (y/n, 默认: {'y' if POP3_SERVER.get('use_ssl', True) else 'n'}): "
        )
        use_ssl = (
            use_ssl.lower() == "y" if use_ssl else POP3_SERVER.get("use_ssl", True)
        )
        username = input(
            f"用户名 (默认: {POP3_SERVER.get('username', '')}): "
        ) or POP3_SERVER.get("username", "")
        password = getpass.getpass(f"密码 (留空使用默认): ") or POP3_SERVER.get(
            "password", ""
        )
        auth_method = input(
            f"认证方法 (AUTO/BASIC/APOP, 默认: {POP3_SERVER.get('auth_method', 'AUTO')}): "
        ) or POP3_SERVER.get("auth_method", "AUTO")

        # 保存设置
        self.pop3_config = {
            "host": host,
            "port": int(port) if port.isdigit() else port,
            "use_ssl": use_ssl,
            "username": username,
            "password": password,
            "auth_method": auth_method,
        }

        # 重新初始化POP3客户端
        if self.pop3_client:
            self.pop3_client = None

        print("\nPOP3服务器设置已保存")
        input("按回车键继续...")

    def _view_current_settings(self):
        """查看当前设置"""
        self._clear_screen()
        print("\n===== 当前设置 =====")

        # 显示SMTP设置
        print("SMTP服务器设置:")
        smtp_config = (
            self.smtp_config
            if hasattr(self, "smtp_config") and self.smtp_config
            else SMTP_SERVER
        )
        print(f"  服务器地址: {smtp_config.get('host', '')}")
        print(f"  端口: {smtp_config.get('port', '')}")
        print(f"  使用SSL: {'是' if smtp_config.get('use_ssl', True) else '否'}")
        print(f"  用户名: {smtp_config.get('username', '')}")
        print(f"  密码: {'已设置' if smtp_config.get('password') else '未设置'}")
        print(f"  认证方法: {smtp_config.get('auth_method', 'AUTO')}")

        print("\nPOP3服务器设置:")
        pop3_config = (
            self.pop3_config
            if hasattr(self, "pop3_config") and self.pop3_config
            else POP3_SERVER
        )
        print(f"  服务器地址: {pop3_config.get('host', '')}")
        print(f"  端口: {pop3_config.get('port', '')}")
        print(f"  使用SSL: {'是' if pop3_config.get('use_ssl', True) else '否'}")
        print(f"  用户名: {pop3_config.get('username', '')}")
        print(f"  密码: {'已设置' if pop3_config.get('password') else '未设置'}")
        print(f"  认证方法: {pop3_config.get('auth_method', 'AUTO')}")

        print("\n存储设置:")
        print(f"  邮件存储目录: {EMAIL_STORAGE_DIR}")
        print(f"  数据库路径: {DB_PATH}")

        input("\n按回车键继续...")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="邮件客户端命令行界面")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="启动交互式界面"
    )
    parser.add_argument("--send", "-s", help="发送指定的.eml文件")
    parser.add_argument("--receive", "-r", action="store_true", help="接收邮件")
    parser.add_argument("--list", "-l", action="store_true", help="列出邮件")
    parser.add_argument("--view", "-v", help="查看指定ID的邮件")
    parser.add_argument("--username", "-u", help="邮箱用户名")
    parser.add_argument("--password", "-p", help="邮箱密码或授权码")

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 创建CLI实例
    cli = EmailCLI()

    # 处理命令行参数
    if args.interactive or not (args.send or args.receive or args.list or args.view):
        # 如果指定了交互模式或没有指定其他操作，启动交互式界面
        cli.main_menu()
    else:
        # 否则，执行指定的操作
        if args.send:
            # 发送邮件
            pass
        elif args.receive:
            # 接收邮件
            pass
        elif args.list:
            # 列出邮件
            pass
        elif args.view:
            # 查看邮件
            pass


if __name__ == "__main__":
    main()
