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
            print("\n" + "=" * 60)
            print("📤 发送邮件")
            print("=" * 60)

            # 显示当前账户信息
            current_account = self.main_cli.get_current_account_info()
            if current_account:
                print(
                    f"📧 当前发件账户: {current_account['display_name']} ({current_account['email']})"
                )
            else:
                print("❌ 未配置发件账户")
                input("请先在账户设置中配置邮箱账户，按回车键返回...")
                return

            print("\n" + "-" * 60)
            print("1. 📝 创建新邮件")
            print("2. 💬 回复邮件")
            print("3. 📨 转发邮件")
            print("0. 🔙 返回主菜单")
            print("-" * 60)

            choice = input("\n请选择操作 [0-3]: ").strip()

            if choice == "1":
                self._create_and_send_email()
            elif choice == "2":
                if not self.main_cli.get_current_email():
                    input("❌ 请先选择一封邮件，按回车键继续...")
                    continue
                self._reply_email()
            elif choice == "3":
                if not self.main_cli.get_current_email():
                    input("❌ 请先选择一封邮件，按回车键继续...")
                    continue
                self._forward_email()
            elif choice == "0":
                return
            else:
                input("❌ 无效选择，请按回车键继续...")

    def _init_smtp_client(self):
        """初始化SMTP客户端"""
        try:
            # 获取当前账户的SMTP配置
            smtp_config = self.main_cli.get_smtp_config()
            if not smtp_config:
                print("❌ 未找到SMTP配置，请先在账户设置中配置邮箱账户")
                return False

            # 检查是否已有客户端，且配置是否发生变化
            if self.smtp_client:
                # 检查配置是否有变化
                current_config = {
                    "host": smtp_config["host"],
                    "port": smtp_config["port"],
                    "username": smtp_config["username"],
                    "use_ssl": smtp_config.get("use_ssl", True),
                    "auth_method": smtp_config.get("auth_method", "AUTO"),
                }

                # 如果有记录的配置且与当前配置相同，直接返回
                if (
                    hasattr(self, "_last_smtp_config")
                    and self._last_smtp_config == current_config
                ):
                    return True
                else:
                    # 配置有变化，清理旧客户端
                    try:
                        if hasattr(self.smtp_client, "disconnect"):
                            self.smtp_client.disconnect()
                    except Exception as e:
                        logger.debug(f"清理旧SMTP连接时出错: {e}")
                    self.smtp_client = None
                    print("🔄 检测到账号配置变更，正在重新连接...")

            print(f"🔄 正在连接到 {smtp_config['host']}:{smtp_config['port']}...")

            # 创建SMTP客户端
            self.smtp_client = SMTPClient(
                host=smtp_config["host"],
                port=smtp_config["port"],
                use_ssl=smtp_config.get("use_ssl", True),
                username=smtp_config["username"],
                password=smtp_config["password"],
                auth_method=smtp_config.get("auth_method", "AUTO"),
            )

            # 记录当前配置，用于下次比较
            self._last_smtp_config = {
                "host": smtp_config["host"],
                "port": smtp_config["port"],
                "username": smtp_config["username"],
                "use_ssl": smtp_config.get("use_ssl", True),
                "auth_method": smtp_config.get("auth_method", "AUTO"),
            }

            logger.info(
                f"SMTP客户端已初始化: {smtp_config['host']}:{smtp_config['port']}"
            )
            print(f"✅ 已连接到邮件服务器")
            return True

        except Exception as e:
            logger.error(f"初始化SMTP客户端失败: {e}")
            print(f"❌ 连接邮件服务器失败: {e}")
            print("💡 请检查网络连接和账户配置")
            return False

    def _create_and_send_email(self):
        """创建并发送新邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📝 创建新邮件")
        print("=" * 60)

        # 获取当前账户信息
        current_account = self.main_cli.get_current_account_info()
        if not current_account:
            print("❌ 未配置发件账户")
            input("按回车键返回...")
            return

        # 显示发件人信息
        print(
            f"📤 发件人: {current_account['display_name']} <{current_account['email']}>"
        )
        print("-" * 60)

        # 获取邮件信息
        subject = input("📋 主题: ").strip()
        if not subject:
            print("❌ 主题不能为空")
            input("按回车键继续...")
            return

        to_addrs = input("📧 收件人 (多个收件人用逗号分隔): ").strip()
        if not to_addrs:
            print("❌ 收件人不能为空")
            input("按回车键继续...")
            return

        cc_addrs = input("📄 抄送 (可选，多个收件人用逗号分隔): ").strip()
        bcc_addrs = input("🔒 密送 (可选，多个收件人用逗号分隔): ").strip()

        print(f"\n📝 请输入邮件正文 (输入单独一行的 '.' 结束):")
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
            add_attachment = input(f"\n📎 是否添加附件? (y/n): ").lower()
            if add_attachment != "y":
                break

            filepath = input("📁 请输入附件路径: ").strip()
            if not filepath:
                continue

            if not os.path.exists(filepath):
                print(f"❌ 文件不存在: {filepath}")
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
                print(f"✅ 已添加附件: {filename}")
            except Exception as e:
                print(f"❌ 添加附件失败: {e}")

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
                message_id=f"<{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{id(self)}@{current_account['email'].split('@')[1]}>",
                subject=subject,
                from_addr=EmailAddress(
                    name=current_account["display_name"],
                    address=current_account["email"],
                ),
                to_addrs=to_addr_list,
                cc_addrs=cc_addr_list,
                bcc_addrs=bcc_addr_list,
                text_content=text_content,
                attachments=attachments,
                date=None,  # 自动设置为当前时间
                status=EmailStatus.DRAFT,
            )

            # 显示邮件摘要
            print(f"\n📋 邮件摘要:")
            print(
                f"   📤 发件人: {current_account['display_name']} <{current_account['email']}>"
            )
            print(f"   📧 收件人: {to_addrs}")
            if cc_addrs:
                print(f"   📄 抄送: {cc_addrs}")
            if bcc_addrs:
                print(f"   🔒 密送: {bcc_addrs}")
            print(f"   📋 主题: {subject}")
            if attachments:
                print(f"   📎 附件: {len(attachments)} 个")

            # 确认发送
            confirm = input(f"\n❓ 确认发送邮件? (Y/n): ").strip().lower()
            if confirm in ["n", "no"]:
                print("❌ 邮件发送已取消")
                input("按回车键继续...")
                return

            # 发送邮件
            print(f"\n🚀 正在发送邮件...")
            result = self.smtp_client.send_email(email)

            if result:
                print("✅ 邮件发送成功！")

                # 保存到已发送文件夹（如果有数据库支持）
                try:
                    email.status = EmailStatus.SENT
                    # 这里可以添加保存到数据库的逻辑
                    logger.info(f"邮件发送成功: {subject}")
                except Exception as e:
                    logger.warning(f"保存已发送邮件失败: {e}")
            else:
                print("❌ 邮件发送失败！")
                print("💡 请检查网络连接和账户配置")

        except Exception as e:
            logger.error(f"发送邮件时出错: {e}")
            print(f"❌ 发送邮件时出错: {e}")

        input("\n按回车键继续...")

    def _reply_email(self):
        """回复邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("💬 回复邮件")
        print("=" * 60)
        print("⚠️  回复邮件功能正在开发中...")
        print("💡 您可以使用 '创建新邮件' 功能手动回复")
        input("\n按回车键继续...")

    def _forward_email(self):
        """转发邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📨 转发邮件")
        print("=" * 60)
        print("⚠️  转发邮件功能正在开发中...")
        print("💡 您可以使用 '创建新邮件' 功能手动转发")
        input("\n按回车键继续...")

    def _parse_email_address(self, addr_str: str) -> EmailAddress:
        """解析邮件地址字符串"""
        try:
            if "<" in addr_str and ">" in addr_str:
                # 格式: "Name <email@domain.com>"
                name = addr_str.split("<")[0].strip().strip('"')
                address = addr_str.split("<")[1].split(">")[0].strip()
            else:
                # 格式: "email@domain.com"
                name = ""
                address = addr_str.strip()

            return EmailAddress(name=name, address=address)
        except Exception as e:
            logger.error(f"解析邮件地址失败: {addr_str}, 错误: {e}")
            # 返回原始地址作为fallback
            return EmailAddress(name="", address=addr_str.strip())

    def _guess_content_type(self, filename: str) -> str:
        """根据文件名猜测内容类型"""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            ".txt": "text/plain",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".zip": "application/zip",
            ".rar": "application/x-rar-compressed",
        }
        return content_types.get(ext, "application/octet-stream")
