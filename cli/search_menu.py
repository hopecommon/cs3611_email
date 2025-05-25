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

        sender = input("📧 请输入发件人: ").strip()
        if not sender:
            print("❌ 发件人不能为空")
            input("\n按回车键继续...")
            return

        try:
            print(f"🔍 正在搜索发件人包含 '{sender}' 的邮件...")

            # 搜索邮件
            db = self.main_cli.get_db()
            emails = db.search_emails(sender, search_fields=["from_addr"])

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

        subject = input("🔍 请输入主题关键词: ").strip()
        if not subject:
            print("❌ 主题关键词不能为空")
            input("\n按回车键继续...")
            return

        try:
            print(f"🔍 正在搜索主题包含 '{subject}' 的邮件...")

            # 搜索邮件
            db = self.main_cli.get_db()
            emails = db.search_emails(subject, search_fields=["subject"])

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
        print(f"{'ID':<5} {'状态':<6} {'日期':<20} {'发件人':<30} {'主题':<40}")
        print("-" * 100)

        for i, email in enumerate(emails):
            status = "✅已读" if email.get("is_read") else "📬未读"
            date = email.get("date", "")
            sender = email.get("from_addr", email.get("sender", ""))
            subject = email.get("subject", "")

            # 截断过长的字段以适应显示
            sender = sender[:28] + ".." if len(sender) > 30 else sender
            subject = subject[:38] + ".." if len(subject) > 40 else subject

            print(f"{i+1:<5} {status:<6} {date:<20} {sender:<30} {subject:<40}")

        # 选择邮件
        print("-" * 100)
        while True:
            choice = input("\n📧 请输入要查看的邮件ID (或按回车返回): ").strip()
            if not choice:
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(emails):
                    self.main_cli.set_current_email(emails[idx])
                    # 这里可以调用查看详情功能
                    print(f"✅ 已选择邮件: {emails[idx].get('subject', '(无主题)')}")
                    input("按回车键继续...")
                    break
                else:
                    print("❌ 无效的ID")
            except ValueError:
                print("❌ 请输入有效的数字")
