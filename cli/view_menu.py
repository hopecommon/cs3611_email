# -*- coding: utf-8 -*-
"""
查看邮件菜单模块
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging

# 设置日志
logger = setup_logging("view_menu")


class ViewEmailMenu:
    """查看邮件菜单"""

    def __init__(self, main_cli):
        """初始化查看邮件菜单"""
        self.main_cli = main_cli

    def show_menu(self):
        """显示查看邮件菜单"""
        while True:
            self.main_cli.clear_screen()
            print("\n===== 查看邮件 =====")
            print("1. 收件箱")
            print("2. 已发送")
            print("3. 查看邮件详情")
            print("4. 删除邮件")
            print("5. 标记为已读/未读")
            print("0. 返回主菜单")

            choice = input("\n请选择操作 [0-5]: ")

            if choice == "1":
                self.main_cli.set_current_folder("inbox")
                self._list_emails()
            elif choice == "2":
                self.main_cli.set_current_folder("sent")
                self._list_emails()
            elif choice == "3":
                if not self.main_cli.get_email_list():
                    input("邮件列表为空，请先获取邮件，按回车键继续...")
                    continue
                self._view_email_details()
            elif choice == "4":
                if not self.main_cli.get_email_list():
                    input("邮件列表为空，请先获取邮件，按回车键继续...")
                    continue
                self._delete_email()
            elif choice == "5":
                if not self.main_cli.get_email_list():
                    input("邮件列表为空，请先获取邮件，按回车键继续...")
                    continue
                self._toggle_read_status()
            elif choice == "0":
                return
            else:
                input("无效选择，请按回车键继续...")

    def _list_emails(self):
        """列出邮件"""
        self.main_cli.clear_screen()
        folder = "已发送" if self.main_cli.get_current_folder() == "sent" else "收件箱"
        print(f"\n===== {folder} =====")

        # 从数据库获取邮件列表
        try:
            db = self.main_cli.get_db()
            if self.main_cli.get_current_folder() == "sent":
                emails = db.list_sent_emails()
            else:
                emails = db.list_emails()

            if not emails:
                print(f"{folder}中没有邮件")
                input("\n按回车键继续...")
                return

            # 保存邮件列表
            self.main_cli.set_email_list(emails)

            # 显示邮件列表
            print(f"{'ID':<5} {'状态':<4} {'日期':<20} {'发件人':<30} {'主题':<40}")
            print("-" * 100)

            # 导入RFC 2047解码器
            from common.email_header_processor import EmailHeaderProcessor

            for i, email in enumerate(emails):
                status = "已读" if email.get("is_read") else "未读"
                date = email.get("date", "")
                sender = email.get("from_addr", email.get("sender", ""))
                subject = email.get("subject", "")

                # 解码RFC 2047编码的主题和发件人
                if subject:
                    subject = EmailHeaderProcessor.decode_header_value(subject)
                if sender:
                    sender = EmailHeaderProcessor.decode_header_value(sender)

                # 截断过长的字段以适应显示
                sender = sender[:28] + ".." if len(sender) > 30 else sender
                subject = subject[:38] + ".." if len(subject) > 40 else subject

                print(f"{i+1:<5} {status:<4} {date:<20} {sender:<30} {subject:<40}")

            # 选择邮件
            while True:
                choice = input("\n请输入要查看的邮件ID (或按回车返回): ")
                if not choice:
                    return

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(emails):
                        self.main_cli.set_current_email(emails[idx])
                        self._view_email_details()
                        break
                    else:
                        print("无效的ID")
                except ValueError:
                    print("请输入有效的数字")
        except Exception as e:
            logger.error(f"获取邮件列表时出错: {e}")
            print(f"获取邮件列表时出错: {e}")
            input("\n按回车键继续...")

    def _view_email_details(self):
        """查看邮件详情"""
        current_email = self.main_cli.get_current_email()
        if not current_email:
            print("未选择邮件")
            input("\n按回车键继续...")
            return

        self.main_cli.clear_screen()
        print("\n===== 邮件详情 =====")

        # 获取并解析邮件内容以获取完整信息
        try:
            db = self.main_cli.get_db()
            message_id = current_email.get("message_id")

            # 根据邮件类型选择不同的获取方法
            email_type = current_email.get("type", "received")
            if email_type == "sent":
                content_str = db.get_sent_email_content(message_id)
            else:
                content_str = db.get_email_content(message_id)

            if content_str:
                # 使用EmailFormatHandler解析完整的邮件信息
                from common.email_format_handler import EmailFormatHandler

                try:
                    parsed_email = EmailFormatHandler.parse_mime_message(content_str)

                    # 显示解析后的邮件基本信息
                    subject = parsed_email.subject or current_email.get(
                        "subject", "(无主题)"
                    )
                    from_addr = (
                        str(parsed_email.from_addr)
                        if parsed_email.from_addr
                        else current_email.get("from_addr", "(未知发件人)")
                    )
                    to_addrs = (
                        ", ".join([str(addr) for addr in parsed_email.to_addrs])
                        if parsed_email.to_addrs
                        else current_email.get("to_addrs", "(未知收件人)")
                    )
                    date = (
                        parsed_email.date.strftime("%Y-%m-%d %H:%M:%S")
                        if parsed_email.date
                        else current_email.get("date", "(未知日期)")
                    )

                    print(f"主题: {subject}")
                    print(f"发件人: {from_addr}")
                    print(f"收件人: {to_addrs}")
                    print(f"日期: {date}")

                    # 显示邮件正文
                    print("\n----- 邮件正文 -----")
                    if parsed_email.text_content:
                        content = parsed_email.text_content.strip()
                        if len(content) > 2000:
                            print(content[:2000] + "\n...(内容过长，已截断)")
                        else:
                            print(content)
                    elif parsed_email.html_content:
                        # 简单处理HTML内容
                        import re

                        html_content = parsed_email.html_content
                        # 移除HTML标签
                        clean_content = re.sub(r"<[^>]+>", "", html_content).strip()
                        if len(clean_content) > 2000:
                            print(clean_content[:2000] + "\n...(内容过长，已截断)")
                        else:
                            print(clean_content)
                    else:
                        print("(邮件内容为空)")

                except Exception as parse_e:
                    logger.warning(f"使用EmailFormatHandler解析失败: {parse_e}")
                    # 回退到原始显示方法
                    self._display_fallback_email_info(current_email, content_str)
            else:
                print("无法获取邮件内容")
                # 显示数据库中的基本信息
                self._display_basic_email_info(current_email)

        except Exception as e:
            logger.error(f"查看邮件详情时出错: {e}")
            print(f"查看邮件详情时出错: {e}")
            # 显示数据库中的基本信息
            self._display_basic_email_info(current_email)

        # 标记为已读
        try:
            if not current_email.get("is_read"):
                db = self.main_cli.get_db()
                db.update_email(current_email.get("message_id"), is_read=True)
                print("\n邮件已标记为已读")
        except Exception as e:
            logger.error(f"标记邮件为已读时出错: {e}")

        input("\n按回车键继续...")

    def _delete_email(self):
        """删除邮件"""
        print("\n删除邮件功能暂未实现")
        input("按回车键继续...")

    def _toggle_read_status(self):
        """切换邮件已读/未读状态"""
        print("\n切换邮件状态功能暂未实现")
        input("按回车键继续...")

    def _display_basic_email_info(self, email_data):
        """显示数据库中的基本邮件信息"""
        from common.email_header_processor import EmailHeaderProcessor

        # 解码可能的RFC 2047编码的主题
        subject = email_data.get("subject", "(无主题)")
        if subject:
            subject = EmailHeaderProcessor.decode_header_value(subject)

        # 处理发件人信息
        from_addr = email_data.get(
            "from_addr", email_data.get("sender", "(未知发件人)")
        )

        # 处理收件人信息
        to_addrs = email_data.get(
            "to_addrs", email_data.get("recipients", "(未知收件人)")
        )
        if isinstance(to_addrs, list):
            to_addrs = ", ".join([str(addr) for addr in to_addrs])

        print(f"主题: {subject}")
        print(f"发件人: {from_addr}")
        print(f"收件人: {to_addrs}")
        print(f"日期: {email_data.get('date', '(未知日期)')}")
        print("\n邮件内容: (无法获取)")

    def _display_fallback_email_info(self, email_data, content_str):
        """回退显示方法，当EmailFormatHandler解析失败时使用"""
        # 显示基本信息
        self._display_basic_email_info(email_data)

        # 尝试简单的内容提取
        print("\n----- 邮件正文 -----")
        readable_content = self._extract_readable_content(content_str)
        if len(readable_content) > 2000:
            print(readable_content[:2000] + "\n...(内容过长，已截断)")
        else:
            print(readable_content)

    def _extract_readable_content(self, content_str: str) -> str:
        """
        从MIME内容中提取可读的文本内容

        Args:
            content_str: 原始MIME内容字符串

        Returns:
            可读的文本内容
        """
        try:
            import email
            import base64
            import re

            # 解析MIME消息
            msg = email.message_from_string(content_str)

            # 提取文本内容
            text_content = []

            if msg.is_multipart():
                # 多部分消息，遍历所有部分
                for part in msg.walk():
                    # 跳过multipart容器本身
                    if part.get_content_maintype() == "multipart":
                        continue

                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        # 获取文本内容
                        payload = part.get_payload(decode=True)
                        if payload:
                            try:
                                # 尝试解码
                                charset = part.get_content_charset() or "utf-8"
                                text = payload.decode(charset, errors="ignore")
                                text_content.append(text)
                            except Exception as e:
                                logger.debug(f"解码文本内容失败: {e}")
                                # 如果payload是字符串，尝试Base64解码
                                try:
                                    if isinstance(payload, str):
                                        decoded = base64.b64decode(payload).decode(
                                            "utf-8", errors="ignore"
                                        )
                                    else:
                                        decoded = payload.decode(
                                            "utf-8", errors="ignore"
                                        )
                                    text_content.append(decoded)
                                except:
                                    text_content.append(str(payload))
                    elif content_type == "text/html":
                        # HTML内容，简单提取文本
                        payload = part.get_payload(decode=True)
                        if payload:
                            try:
                                charset = part.get_content_charset() or "utf-8"
                                html_text = payload.decode(charset, errors="ignore")
                                # 简单的HTML标签移除
                                clean_text = re.sub(r"<[^>]+>", "", html_text)
                                text_content.append(f"[HTML内容]\n{clean_text}")
                            except Exception as e:
                                logger.debug(f"解码HTML内容失败: {e}")
            else:
                # 单部分消息
                content_type = msg.get_content_type()
                if content_type.startswith("text/"):
                    payload = msg.get_payload(decode=True)
                    if payload:
                        try:
                            charset = msg.get_content_charset() or "utf-8"
                            text = payload.decode(charset, errors="ignore")
                            text_content.append(text)
                        except Exception as e:
                            logger.debug(f"解码单部分内容失败: {e}")
                            # 尝试Base64解码
                            try:
                                decoded = base64.b64decode(payload).decode(
                                    "utf-8", errors="ignore"
                                )
                                text_content.append(decoded)
                            except:
                                text_content.append(str(payload))

            # 如果没有提取到文本内容，尝试简单的Base64解码
            if not text_content:
                # 专门处理我们看到的简单Base64情况
                lines = content_str.split("\n")
                for line in lines:
                    line = line.strip()
                    # 查找看起来像Base64的行
                    if line and re.match(r"^[A-Za-z0-9+/=]+$", line) and len(line) > 4:
                        try:
                            decoded = base64.b64decode(line).decode(
                                "utf-8", errors="ignore"
                            )
                            if decoded.strip() and len(decoded) > 1:
                                text_content.append(decoded.strip())
                        except:
                            continue

            # 返回合并的文本内容
            if text_content:
                result = "\n\n".join(text_content).strip()
                return result if result else "邮件内容为空"
            else:
                return f"无法解析邮件内容，原始内容摘要:\n{content_str[:300]}..."

        except Exception as e:
            logger.error(f"提取可读内容失败: {e}")
            return f"内容解析失败: {e}\n\n原始内容:\n{content_str[:300]}..."
