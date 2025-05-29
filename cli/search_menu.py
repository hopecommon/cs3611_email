# -*- coding: utf-8 -*-
"""
搜索邮件菜单模块
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging

# 设置日志
logger = setup_logging("search_menu")


class SearchEmailMenu:
    """搜索邮件菜单"""

    def __init__(self, main_cli):
        """初始化搜索邮件菜单"""
        self.main_cli = main_cli

    def show_menu(self):
        """显示搜索邮件菜单"""
        while True:
            self.main_cli.clear_screen()
            print("\n" + "=" * 60)
            print("🔍 搜索邮件")
            print("=" * 60)
            print("1. 👤 按发件人搜索")
            print("2. 📋 按主题搜索")
            print("3. 📝 按内容搜索")
            print("4. 📅 按日期搜索")
            print("5. 🔧 高级搜索")
            print("0. 🔙 返回主菜单")
            print("-" * 60)

            choice = input("\n请选择操作 [0-5]: ").strip()

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
                input("❌ 无效选择，请按回车键继续...")

    def _search_by_sender(self):
        """按发件人搜索邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("👤 按发件人搜索")
        print("=" * 60)

        # 获取当前账户信息，确保账户隔离
        current_account = self.main_cli.get_current_account()
        if not current_account:
            print("❌ 未找到当前账户信息，请先登录")
            input("\n按回车键继续...")
            return

        current_user_email = current_account["email"]
        print(f"📧 搜索范围: {current_user_email} 的邮件")

        sender = input("📧 请输入发件人: ").strip()
        if not sender:
            print("❌ 发件人不能为空")
            input("\n按回车键继续...")
            return

        try:
            print(f"🔍 正在搜索发件人包含 '{sender}' 的邮件...")

            # 使用原始搜索方法（避免数据库兼容性问题）
            db = self.main_cli.get_db()
            all_emails = db.search_emails(sender, search_fields=["from_addr"])

            # 在结果中进行账户隔离筛选
            emails = self._filter_emails_by_user(all_emails, current_user_email)

            if not emails:
                print(f"📭 未找到发件人包含 '{sender}' 的邮件")
                input("\n按回车键继续...")
                return

            # 显示搜索结果
            self._display_search_results(emails, f"👤 发件人包含 '{sender}' 的邮件")
        except Exception as e:
            logger.error(f"搜索邮件时出错: {e}")
            print(f"❌ 搜索邮件时出错: {e}")
            input("\n按回车键继续...")

    def _search_by_subject(self):
        """按主题搜索邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📋 按主题搜索")
        print("=" * 60)

        # 获取当前账户信息，确保账户隔离
        current_account = self.main_cli.get_current_account()
        if not current_account:
            print("❌ 未找到当前账户信息，请先登录")
            input("\n按回车键继续...")
            return

        current_user_email = current_account["email"]
        print(f"📧 搜索范围: {current_user_email} 的邮件")

        subject = input("🔍 请输入主题关键词: ").strip()
        if not subject:
            print("❌ 主题关键词不能为空")
            input("\n按回车键继续...")
            return

        try:
            print(f"🔍 正在搜索主题包含 '{subject}' 的邮件...")

            # 使用原始搜索方法（避免数据库兼容性问题）
            db = self.main_cli.get_db()
            all_emails = db.search_emails(subject, search_fields=["subject"])

            # 在结果中进行账户隔离筛选
            emails = self._filter_emails_by_user(all_emails, current_user_email)

            if not emails:
                print(f"📭 未找到主题包含 '{subject}' 的邮件")
                input("\n按回车键继续...")
                return

            # 显示搜索结果
            self._display_search_results(emails, f"📋 主题包含 '{subject}' 的邮件")
        except Exception as e:
            logger.error(f"搜索邮件时出错: {e}")
            print(f"❌ 搜索邮件时出错: {e}")
            input("\n按回车键继续...")

    def _search_by_content(self):
        """按内容搜索邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📝 按内容搜索")
        print("=" * 60)
        print("⚠️  按内容搜索功能正在开发中...")
        print("💡 您可以使用 '按发件人搜索' 或 '按主题搜索' 功能")
        input("\n按回车键继续...")

    def _search_by_date(self):
        """按日期搜索邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📅 按日期搜索")
        print("=" * 60)
        print("⚠️  按日期搜索功能正在开发中...")
        print("💡 计划支持的日期搜索:")
        print("   • 指定日期范围")
        print("   • 今天/昨天/本周/本月")
        print("   • 自定义时间段")
        input("\n按回车键继续...")

    def _advanced_search(self):
        """高级搜索"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("🔧 高级搜索")
        print("=" * 60)
        print("⚠️  高级搜索功能正在开发中...")
        print("💡 计划支持的高级搜索:")
        print("   • 多条件组合搜索")
        print("   • 正则表达式搜索")
        print("   • 附件类型过滤")
        print("   • 邮件大小过滤")
        print("   • 已读/未读状态过滤")
        input("\n按回车键继续...")

    def _filter_emails_by_user(self, emails, user_email):
        """
        根据用户邮箱过滤邮件列表（账户隔离）

        Args:
            emails: 邮件列表
            user_email: 当前用户邮箱

        Returns:
            过滤后的邮件列表
        """
        if not emails or not user_email:
            return []

        filtered_emails = []

        for email in emails:
            try:
                # 获取邮件类型
                email_type = email.get("type", "")

                if email_type == "sent":
                    # 已发送邮件：检查发件人
                    from_addr = email.get("from_addr", "")
                    if self._is_user_email_match(from_addr, user_email):
                        filtered_emails.append(email)

                elif email_type == "received" or not email_type:
                    # 接收邮件：检查收件人字段
                    to_addrs = email.get("to_addrs", "")
                    cc_addrs = email.get("cc_addrs", "")
                    bcc_addrs = email.get("bcc_addrs", "")

                    # 检查是否在任何收件人字段中
                    if (
                        self._is_user_in_recipients(to_addrs, user_email)
                        or self._is_user_in_recipients(cc_addrs, user_email)
                        or self._is_user_in_recipients(bcc_addrs, user_email)
                    ):
                        filtered_emails.append(email)

            except Exception as e:
                logger.warning(f"筛选邮件时出错: {e}")
                continue

        return filtered_emails

    def _is_user_email_match(self, email_field, user_email):
        """检查邮件地址字段是否匹配用户邮箱"""
        if not email_field or not user_email:
            return False

        # 转换为字符串进行比较
        email_str = str(email_field).lower()
        user_email_lower = user_email.lower()

        # 支持多种格式：
        # 1. 直接匹配: user@domain.com
        # 2. 显示名格式: Name <user@domain.com>
        # 3. JSON格式中的部分匹配
        return (
            user_email_lower in email_str
            or email_str == user_email_lower
            or f"<{user_email_lower}>" in email_str
        )

    def _is_user_in_recipients(self, recipients_field, user_email):
        """检查用户是否在收件人字段中"""
        if not recipients_field or not user_email:
            return False

        # 转换为字符串进行比较
        recipients_str = str(recipients_field).lower()
        user_email_lower = user_email.lower()

        # 支持多种格式的收件人字段
        return (
            user_email_lower in recipients_str
            or f'"{user_email_lower}"' in recipients_str
            or f"<{user_email_lower}>" in recipients_str
        )

    def _display_search_results(self, emails, title):
        """显示搜索结果"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print(f"🔍 搜索结果")
        print("=" * 60)
        print(f"📊 {title} - 共找到 {len(emails)} 封邮件")

        # 保存邮件列表
        self.main_cli.set_email_list(emails)

        # 显示邮件列表
        print("-" * 60)
        print(
            f"{'ID':<5} {'类型':<6} {'状态':<6} {'日期':<20} {'发件人':<30} {'主题':<30}"
        )
        print("-" * 110)

        # 导入RFC 2047解码器
        from common.email_header_processor import EmailHeaderProcessor

        for i, email in enumerate(emails):
            # 邮件类型标识
            email_type = "📤发送" if email.get("type") == "sent" else "📥收件"

            # 已读状态
            status = "✅已读" if email.get("is_read") else "📬未读"

            # 基本信息
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
            subject = subject[:28] + ".." if len(subject) > 30 else subject

            print(
                f"{i+1:<5} {email_type:<6} {status:<6} {date:<20} {sender:<30} {subject:<30}"
            )

        # 选择邮件
        print("-" * 110)
        while True:
            choice = input("\n📧 请输入要查看的邮件ID (或按回车返回): ").strip()
            if not choice:
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(emails):
                    self.main_cli.set_current_email(emails[idx])
                    # 设置当前文件夹（用于邮件详情显示）
                    if emails[idx].get("type") == "sent":
                        self.main_cli.set_current_folder("sent")
                    else:
                        self.main_cli.set_current_folder("inbox")

                    # 显示选择确认
                    subject = emails[idx].get("subject", "(无主题)")
                    if subject:
                        subject = EmailHeaderProcessor.decode_header_value(subject)
                    print(f"✅ 已选择邮件: {subject}")
                    print(
                        "💡 提示: 您可以在 '查看邮件' -> '查看邮件详情' 中查看完整内容"
                    )
                    input("按回车键继续...")
                    break
                else:
                    print("❌ 无效的ID")
            except ValueError:
                print("❌ 请输入有效的数字")
