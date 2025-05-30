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

    def _validate_search_input(self, keyword, min_length=1, max_length=100):
        """验证搜索输入的有效性"""
        if not keyword:
            return False, "搜索关键词不能为空"
        if len(keyword) < min_length:
            return False, f"搜索关键词至少需要{min_length}个字符"
        if len(keyword) > max_length:
            return False, f"搜索关键词不能超过{max_length}个字符"

        # 检查危险字符
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "\\"]
        for char in dangerous_chars:
            if char in keyword:
                return False, f"搜索关键词不能包含特殊字符: {char}"
        return True, ""

    def _get_current_user_email(self):
        """获取当前用户邮箱，处理登录验证"""
        current_account = self.main_cli.get_current_account()
        if not current_account:
            print("❌ 未找到当前账户信息，请先登录")
            input("\n按回车键继续...")
            return None
        return current_account["email"]

    def _handle_search_error(self, error, operation="搜索邮件"):
        """统一处理搜索错误"""
        logger.error(f"{operation}时出错: {error}")
        print(f"❌ {operation}时出错: {error}")
        input("\n按回车键继续...")

    def _execute_basic_search(self, keyword, search_fields, title_prefix, user_email):
        """执行基础搜索的通用逻辑"""
        try:
            print(f"🔍 正在搜索{title_prefix}包含 '{keyword}' 的邮件...")

            db = self.main_cli.get_db()
            all_emails = db.search_emails(keyword, search_fields=search_fields)
            emails = self._filter_emails_by_user(all_emails, user_email)

            if not emails:
                print(f"📭 未找到{title_prefix}包含 '{keyword}' 的邮件")
                input("\n按回车键继续...")
                return

            self._display_search_results(
                emails, f"{title_prefix}包含 '{keyword}' 的邮件"
            )
        except Exception as e:
            self._handle_search_error(e)

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

        user_email = self._get_current_user_email()
        if not user_email:
            return

        print(f"📧 搜索范围: {user_email} 的邮件")
        sender = input("👤 请输入发件人: ").strip()

        if not sender:
            print("❌ 发件人不能为空")
            input("\n按回车键继续...")
            return

        is_valid, error_msg = self._validate_search_input(sender)
        if not is_valid:
            print(f"❌ {error_msg}")
            input("\n按回车键继续...")
            return

        self._execute_basic_search(sender, ["from_addr"], "👤 发件人", user_email)

    def _search_by_subject(self):
        """按主题搜索邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📋 按主题搜索")
        print("=" * 60)

        user_email = self._get_current_user_email()
        if not user_email:
            return

        print(f"📧 搜索范围: {user_email} 的邮件")
        subject = input("🔍 请输入主题关键词: ").strip()

        if not subject:
            print("❌ 主题关键词不能为空")
            input("\n按回车键继续...")
            return

        is_valid, error_msg = self._validate_search_input(subject)
        if not is_valid:
            print(f"❌ {error_msg}")
            input("\n按回车键继续...")
            return

        self._execute_basic_search(subject, ["subject"], "📋 主题", user_email)

    def _search_by_content(self):
        """按内容搜索邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📝 按内容搜索")
        print("=" * 60)

        user_email = self._get_current_user_email()
        if not user_email:
            return

        print(f"📧 搜索范围: {user_email} 的邮件")
        print("⚠️  内容搜索可能需要较长时间，请耐心等待...")

        content_keyword = input("🔍 请输入内容关键词: ").strip()
        if not content_keyword:
            print("❌ 内容关键词不能为空")
            input("\n按回车键继续...")
            return

        is_valid, error_msg = self._validate_search_input(content_keyword, min_length=2)
        if not is_valid:
            print(f"❌ {error_msg}")
            input("\n按回车键继续...")
            return

        search_limit = self._get_content_search_limit()
        if search_limit is None:
            return

        self._execute_content_search(content_keyword, user_email, search_limit)

    def _get_content_search_limit(self):
        """获取内容搜索限制"""
        print(f"\n⚙️  搜索设置:")
        print("为了提高搜索速度，建议限制搜索范围")
        limit_choice = input("最大搜索邮件数量 (默认500，输入0表示不限制): ").strip()

        try:
            search_limit = int(limit_choice) if limit_choice else 500
            if search_limit < 0:
                search_limit = 500
        except ValueError:
            search_limit = 500

        if search_limit == 0:
            print("⚠️  将搜索所有邮件，这可能需要很长时间")
            confirm = input("确认继续? [y/N]: ").strip().lower()
            if confirm != "y" and confirm != "yes":
                return None
            search_limit = 2000

        return search_limit

    def _execute_content_search(self, content_keyword, user_email, search_limit):
        """执行内容搜索"""
        try:
            print(f"🔍 正在搜索内容包含 '{content_keyword}' 的邮件...")
            print("正在扫描邮件内容，请稍候...")

            # 获取邮件数据
            all_emails = self._get_emails_for_content_search(user_email, search_limit)
            if not all_emails:
                print("📭 没有找到任何邮件")
                input("\n按回车键继续...")
                return

            # 搜索匹配邮件
            matching_emails, stats = self._search_content_in_emails(
                all_emails, content_keyword
            )

            # 显示结果
            self._display_content_search_results(
                matching_emails, content_keyword, stats
            )

        except Exception as e:
            self._handle_search_error(e, "搜索邮件内容")

    def _get_emails_for_content_search(self, user_email, search_limit):
        """获取用于内容搜索的邮件列表"""
        db = self.main_cli.get_db()
        all_emails = []

        # 获取收件箱邮件
        received_emails = db.list_emails(user_email=user_email, limit=search_limit // 2)
        if received_emails:
            all_emails.extend(received_emails)

        # 获取已发送邮件
        sent_emails = db.list_sent_emails(from_addr=user_email, limit=search_limit // 2)
        if sent_emails:
            for email in sent_emails:
                email["type"] = "sent"
            all_emails.extend(sent_emails)

        # 限制搜索范围
        if len(all_emails) > search_limit:
            all_emails = all_emails[:search_limit]
            print(f"🔄 已限制搜索范围为最新的 {search_limit} 封邮件")

        return all_emails

    def _search_content_in_emails(self, all_emails, content_keyword):
        """在邮件列表中搜索内容"""
        matching_emails = []
        processed_count = 0
        failed_count = 0
        total_emails = len(all_emails)
        db = self.main_cli.get_db()

        print(f"📊 开始搜索 {total_emails} 封邮件的内容...")

        for email in all_emails:
            processed_count += 1

            # 进度更新
            if processed_count % 5 == 0 or processed_count == total_emails:
                percentage = (processed_count / total_emails) * 100
                print(
                    f"📊 搜索进度: {processed_count}/{total_emails} ({percentage:.1f}%) - 已找到 {len(matching_emails)} 封匹配邮件"
                )

            try:
                message_id = email.get("message_id")
                if not message_id:
                    failed_count += 1
                    continue

                # 获取邮件内容
                email_type = email.get("type", "received")
                raw_content = (
                    db.get_sent_email_content(message_id)
                    if email_type == "sent"
                    else db.get_email_content(message_id)
                )

                if raw_content:
                    search_content = self._extract_searchable_content(raw_content)
                    if (
                        search_content
                        and content_keyword.lower() in search_content.lower()
                    ):
                        matching_emails.append(email)
                        subject = email.get("subject", "(无主题)")[:30]
                        print(f"✅ 找到匹配: {subject}")

            except Exception as e:
                failed_count += 1
                logger.warning(f"搜索邮件内容时出错 {message_id}: {e}")

        return matching_emails, {
            "total": total_emails,
            "matched": len(matching_emails),
            "failed": failed_count,
        }

    def _display_content_search_results(self, matching_emails, content_keyword, stats):
        """显示内容搜索结果"""
        print(f"\n🎯 搜索完成统计:")
        print(f"   📊 搜索邮件总数: {stats['total']}")
        print(f"   ✅ 匹配邮件数量: {stats['matched']}")
        print(f"   ❌ 搜索失败数量: {stats['failed']}")

        if not matching_emails:
            print(f"\n📭 未找到内容包含 '{content_keyword}' 的邮件")
            if stats["failed"] > 0:
                print(f"⚠️  有 {stats['failed']} 封邮件无法读取内容")
            input("\n按回车键继续...")
            return

        print(f"\n✅ 搜索成功！找到 {len(matching_emails)} 封匹配的邮件")
        self._display_search_results(
            matching_emails, f"📝 内容包含 '{content_keyword}' 的邮件"
        )

    def _search_by_date(self):
        """按日期搜索邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📅 按日期搜索")
        print("=" * 60)

        user_email = self._get_current_user_email()
        if not user_email:
            return

        print(f"📧 搜索范围: {user_email} 的邮件")

        date_range = self._get_date_range()
        if not date_range:
            return

        start_date, end_date, date_desc = date_range
        self._execute_date_search(user_email, start_date, end_date, date_desc)

    def _get_date_range(self):
        """获取日期范围选择"""
        print("\n🗓️  选择日期范围:")
        print("1. 今天")
        print("2. 昨天")
        print("3. 最近7天")
        print("4. 最近30天")
        print("5. 自定义日期范围")
        print("0. 返回")

        choice = input("\n请选择日期范围 [0-5]: ").strip()
        if choice == "0":
            return None

        try:
            from datetime import datetime, timedelta
            import re

            today = datetime.now()
            date_ranges = {
                "1": (
                    today.replace(hour=0, minute=0, second=0, microsecond=0),
                    today.replace(hour=23, minute=59, second=59, microsecond=999999),
                    "今天",
                ),
                "2": (
                    (today - timedelta(days=1)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ),
                    (today - timedelta(days=1)).replace(
                        hour=23, minute=59, second=59, microsecond=999999
                    ),
                    "昨天",
                ),
                "3": (
                    (today - timedelta(days=7)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ),
                    today.replace(hour=23, minute=59, second=59, microsecond=999999),
                    "最近7天",
                ),
                "4": (
                    (today - timedelta(days=30)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ),
                    today.replace(hour=23, minute=59, second=59, microsecond=999999),
                    "最近30天",
                ),
            }

            if choice in date_ranges:
                return date_ranges[choice]
            elif choice == "5":
                return self._get_custom_date_range(today)
            else:
                print("❌ 无效选择")
                input("\n按回车键继续...")
                return None

        except Exception as e:
            self._handle_search_error(e, "处理日期范围")
            return None

    def _get_custom_date_range(self, today):
        """获取自定义日期范围"""
        import re
        from datetime import datetime

        print("\n📅 自定义日期范围")
        print("日期格式: YYYY-MM-DD (例如: 2024-01-01)")

        start_input = input("请输入开始日期: ").strip()
        if not start_input:
            print("❌ 开始日期不能为空")
            input("\n按回车键继续...")
            return None

        end_input = input("请输入结束日期 (留空表示今天): ").strip()
        if not end_input:
            end_input = today.strftime("%Y-%m-%d")

        # 验证日期格式
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(date_pattern, start_input) or not re.match(
            date_pattern, end_input
        ):
            print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            input("\n按回车键继续...")
            return None

        try:
            start_date = datetime.strptime(start_input, "%Y-%m-%d")
            end_date = datetime.strptime(end_input, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

            if start_date > end_date:
                print("❌ 开始日期不能晚于结束日期")
                input("\n按回车键继续...")
                return None

            return start_date, end_date, f"{start_input} 到 {end_input}"
        except ValueError:
            print("❌ 日期格式错误")
            input("\n按回车键继续...")
            return None

    def _execute_date_search(self, user_email, start_date, end_date, date_desc):
        """执行日期搜索"""
        try:
            print(f"\n🔍 正在搜索 {date_desc} 的邮件...")

            # 获取所有邮件
            all_emails = self._get_emails_for_content_search(user_email, 1000)
            if not all_emails:
                print("📭 没有找到任何邮件")
                input("\n按回车键继续...")
                return

            # 按日期筛选
            matching_emails = []
            for email in all_emails:
                try:
                    email_date_str = email.get("date", "")
                    if not email_date_str:
                        continue

                    email_date = self._parse_email_date(email_date_str)
                    if email_date and start_date <= email_date <= end_date:
                        matching_emails.append(email)

                except Exception as e:
                    logger.warning(
                        f"解析邮件日期时出错 {email.get('message_id', '')}: {e}"
                    )

            if not matching_emails:
                print(f"📭 未找到 {date_desc} 的邮件")
                print(f"📊 已搜索 {len(all_emails)} 封邮件")
                input("\n按回车键继续...")
                return

            print(
                f"✅ 搜索完成！在 {len(all_emails)} 封邮件中找到 {len(matching_emails)} 封匹配的邮件"
            )
            self._display_search_results(matching_emails, f"📅 {date_desc} 的邮件")

        except Exception as e:
            self._handle_search_error(e, "按日期搜索邮件")

    def _advanced_search(self):
        """高级搜索"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("🔧 高级搜索")
        print("=" * 60)

        user_email = self._get_current_user_email()
        if not user_email:
            return

        print(f"📧 搜索范围: {user_email} 的邮件")

        # 收集搜索条件
        search_conditions = self._collect_advanced_search_conditions()
        if not search_conditions:
            return

        # 执行高级搜索
        self._execute_advanced_search(user_email, search_conditions)

    def _collect_advanced_search_conditions(self):
        """收集高级搜索条件"""
        search_conditions = {}

        print("\n🔍 请设置搜索条件 (留空表示不筛选该项):")
        print("💡 提示: 所有条件都可以留空，这样将显示全部邮件")
        print("-" * 60)

        # 基本搜索条件
        sender = input("👤 发件人 (支持部分匹配，留空=不筛选): ").strip()
        if sender:
            search_conditions["sender"] = sender

        subject = input("📋 主题关键词 (留空=不筛选): ").strip()
        if subject:
            search_conditions["subject"] = subject

        content = input("📝 内容关键词 (可能较慢，留空=不筛选): ").strip()
        if content:
            search_conditions["content"] = content

        # 邮件类型和已读状态
        email_type, include_received, include_sent = self._get_email_type_filter()
        search_conditions["type"] = email_type
        search_conditions["include_received"] = include_received
        search_conditions["include_sent"] = include_sent

        read_status, read_filter = self._get_read_status_filter()
        search_conditions["read_status"] = read_status
        search_conditions["read_filter"] = read_filter

        # 确认搜索条件
        return self._confirm_advanced_search_conditions(search_conditions)

    def _get_email_type_filter(self):
        """获取邮件类型筛选条件"""
        print("\n📂 邮件类型:")
        print("1. 收件箱和已发送 (默认)")
        print("2. 仅收件箱")
        print("3. 仅已发送")

        type_choice = input("请选择邮件类型 [1-3]: ").strip()

        if type_choice == "2":
            return "仅收件箱", True, False
        elif type_choice == "3":
            return "仅已发送", False, True
        else:
            return "收件箱和已发送", True, True

    def _get_read_status_filter(self):
        """获取已读状态筛选条件"""
        print("\n📬 已读状态:")
        print("1. 全部 (默认)")
        print("2. 仅未读")
        print("3. 仅已读")

        read_choice = input("请选择已读状态 [1-3]: ").strip()

        if read_choice == "2":
            return "仅未读", False
        elif read_choice == "3":
            return "仅已读", True
        else:
            return "全部", None

    def _confirm_advanced_search_conditions(self, search_conditions):
        """确认高级搜索条件"""
        has_search_conditions = any(
            key in search_conditions for key in ["sender", "subject", "content"]
        )

        if not has_search_conditions:
            print("\n⚠️  您没有设置任何搜索条件")
            print("📋 这将显示所有符合邮件类型和已读状态筛选的邮件")
            print("💡 如果邮件数量很多，可能需要较长时间处理")

            confirm_all = input("\n确认显示所有邮件? [y/N]: ").strip().lower()
            if confirm_all != "y" and confirm_all != "yes":
                print("已取消搜索")
                input("按回车键继续...")
                return None

        # 显示搜索条件确认
        print("\n" + "=" * 60)
        print("🔍 搜索条件确认:")
        print("-" * 60)

        key_names = {
            "sender": "👤 发件人",
            "subject": "📋 主题",
            "content": "📝 内容",
            "type": "📂 邮件类型",
            "read_status": "📬 已读状态",
        }

        for key, value in search_conditions.items():
            if key in key_names:
                print(f"{key_names[key]}: {value}")

        confirm = input("\n确认搜索? [Y/n]: ").strip().lower()
        if confirm and confirm != "y" and confirm != "yes":
            return None

        return search_conditions

    def _execute_advanced_search(self, user_email, search_conditions):
        """执行高级搜索"""
        try:
            print("\n🔍 正在执行高级搜索...")

            # 获取邮件数据
            all_emails = self._get_emails_for_advanced_search(
                user_email,
                search_conditions["include_received"],
                search_conditions["include_sent"],
            )

            if not all_emails:
                print("📭 没有找到任何邮件")
                input("\n按回车键继续...")
                return

            # 筛选邮件
            matching_emails = self._filter_advanced_search_emails(
                all_emails, search_conditions
            )

            # 显示结果
            self._display_advanced_search_results(
                matching_emails, search_conditions, len(all_emails)
            )

        except Exception as e:
            self._handle_search_error(e, "高级搜索")

    def _get_emails_for_advanced_search(
        self, user_email, include_received, include_sent
    ):
        """获取用于高级搜索的邮件"""
        db = self.main_cli.get_db()
        all_emails = []

        if include_received:
            received_emails = db.list_emails(user_email=user_email, limit=1000)
            if received_emails:
                all_emails.extend(received_emails)

        if include_sent:
            sent_emails = db.list_sent_emails(from_addr=user_email, limit=1000)
            if sent_emails:
                for email in sent_emails:
                    email["type"] = "sent"
                all_emails.extend(sent_emails)

        return self._filter_emails_by_user(all_emails, user_email)

    def _filter_advanced_search_emails(self, all_emails, search_conditions):
        """根据高级搜索条件筛选邮件"""
        matching_emails = []
        total_emails = len(all_emails)
        processed_count = 0
        db = self.main_cli.get_db()

        for email in all_emails:
            processed_count += 1
            if processed_count % 20 == 0:
                print(f"📊 已处理 {processed_count}/{total_emails} 封邮件...")

            try:
                # 基本条件检查
                if not self._check_basic_search_conditions(email, search_conditions):
                    continue

                # 内容搜索（最耗时，放最后）
                if "content" in search_conditions:
                    if not self._check_content_condition(
                        email, search_conditions["content"], db
                    ):
                        continue

                    # 内容匹配成功，添加到结果列表
                    matching_emails.append(email)
                    subject = email.get("subject", "(无主题)")[:30]
                    print(f"✅ 找到匹配: {subject}")
                else:
                    # 没有内容搜索条件，且通过了前面所有检查，直接添加邮件
                    matching_emails.append(email)
                    subject = email.get("subject", "(无主题)")[:30]
                    print(f"✅ 找到匹配: {subject}")

            except Exception as e:
                logger.warning(f"筛选邮件时出错 {email.get('message_id', '')}: {e}")

        return matching_emails

    def _check_basic_search_conditions(self, email, search_conditions):
        """检查基本搜索条件"""
        # 发件人条件
        if "sender" in search_conditions:
            sender_addr = email.get("from_addr", "")
            if search_conditions["sender"].lower() not in sender_addr.lower():
                return False

        # 主题条件
        if "subject" in search_conditions:
            email_subject = email.get("subject", "")
            if search_conditions["subject"].lower() not in email_subject.lower():
                return False

        # 已读状态
        if search_conditions["read_filter"] is not None:
            email_read_status = email.get("is_read", False)
            if email_read_status != search_conditions["read_filter"]:
                return False

        return True

    def _check_content_condition(self, email, content_keyword, db):
        """检查内容搜索条件"""
        message_id = email.get("message_id")
        if not message_id:
            return False

        email_type = email.get("type", "received")
        raw_content = (
            db.get_sent_email_content(message_id)
            if email_type == "sent"
            else db.get_email_content(message_id)
        )

        if raw_content:
            search_content = self._extract_searchable_content(raw_content)
            return search_content and content_keyword.lower() in search_content.lower()

        return False

    def _display_advanced_search_results(
        self, matching_emails, search_conditions, total_emails
    ):
        """显示高级搜索结果"""
        if not matching_emails:
            print(f"📭 未找到符合条件的邮件")
            print(f"📊 已搜索 {total_emails} 封邮件")
            input("\n按回车键继续...")
            return

        print(
            f"✅ 高级搜索完成！在 {total_emails} 封邮件中找到 {len(matching_emails)} 封匹配的邮件"
        )

        # 构建结果描述
        conditions_desc = []
        if "sender" in search_conditions:
            conditions_desc.append(f"发件人: {search_conditions['sender']}")
        if "subject" in search_conditions:
            conditions_desc.append(f"主题: {search_conditions['subject']}")
        if "content" in search_conditions:
            conditions_desc.append(f"内容: {search_conditions['content']}")

        # 添加筛选条件
        filter_desc = []
        if search_conditions.get("type") != "收件箱和已发送":
            filter_desc.append(search_conditions.get("type", ""))
        if search_conditions.get("read_status") != "全部":
            filter_desc.append(search_conditions.get("read_status", ""))

        if conditions_desc:
            if filter_desc:
                result_title = f"🔧 高级搜索结果 ({', '.join(conditions_desc)}, {', '.join(filter_desc)})"
            else:
                result_title = f"🔧 高级搜索结果 ({', '.join(conditions_desc)})"
        else:
            if filter_desc:
                result_title = f"🔧 高级搜索结果 (全部邮件, {', '.join(filter_desc)})"
            else:
                result_title = f"🔧 高级搜索结果 (全部邮件)"

        self._display_search_results(matching_emails, result_title)

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
                # 获取邮件类型，兼容不同的数据源
                email_type = email.get("type", "")

                # 如果没有明确的type字段，尝试根据其他字段判断
                if not email_type:
                    # 检查是否有sent_emails表的特征字段
                    if email.get("sent_at") or email.get("sent_date"):
                        email_type = "sent"
                    else:
                        email_type = "received"

                # 首先检查发件人（适用于已发送邮件和自己发给自己的邮件）
                from_addr = email.get("from_addr", "")
                if self._is_user_email_match(from_addr, user_email):
                    filtered_emails.append(email)
                    continue

                # 如果发件人不匹配，且明确标识为已发送邮件，则跳过
                if email_type == "sent":
                    continue

                # 对于收件邮件，检查收件人字段
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

        # 处理多种格式的收件人字段：
        # 1. 字符串格式的列表: "['user@domain.com']"
        # 2. JSON数组格式: ["user@domain.com"]
        # 3. 逗号分隔格式: "user1@domain.com, user2@domain.com"
        # 4. 显示名格式: "Name <user@domain.com>"

        # 基本字符串匹配
        if (
            user_email_lower in recipients_str
            or f'"{user_email_lower}"' in recipients_str
            or f"<{user_email_lower}>" in recipients_str
            or f"'{user_email_lower}'" in recipients_str
        ):
            return True

        # 尝试解析列表格式
        try:
            import ast
            import json

            # 尝试作为Python字面量解析（如 "['email@domain.com']"）
            if recipients_str.startswith("[") and recipients_str.endswith("]"):
                try:
                    recipients_list = ast.literal_eval(recipients_str)
                    if isinstance(recipients_list, list):
                        for recipient in recipients_list:
                            if user_email_lower in str(recipient).lower():
                                return True
                except:
                    # 如果ast解析失败，尝试JSON解析
                    try:
                        recipients_list = json.loads(recipients_str)
                        if isinstance(recipients_list, list):
                            for recipient in recipients_list:
                                if user_email_lower in str(recipient).lower():
                                    return True
                    except:
                        pass
        except:
            pass

        return False

    def _display_search_results(self, emails, title):
        """显示搜索结果"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print(f"🔍 搜索结果")
        print("=" * 60)
        print(f"📊 {title} - 共找到 {len(emails)} 封邮件")

        # 排序邮件
        if len(emails) > 1:
            emails = self._sort_emails(emails)

        # 保存和显示邮件列表
        self.main_cli.set_email_list(emails)
        self._display_email_list(emails)

        # 邮件选择
        self._handle_email_selection(emails)

    def _sort_emails(self, emails):
        """排序邮件列表"""
        print("\n📊 排序选项:")
        print("1. 按日期排序 (最新优先) - 默认")
        print("2. 按日期排序 (最旧优先)")
        print("3. 按发件人排序")
        print("4. 按主题排序")

        sort_choice = input("请选择排序方式 [1-4]: ").strip()

        try:
            from common.email_header_processor import EmailHeaderProcessor

            sort_functions = {
                "2": lambda x: x.get("date", ""),
                "3": lambda x: EmailHeaderProcessor.decode_header_value(
                    x.get("from_addr", "")
                ).lower(),
                "4": lambda x: EmailHeaderProcessor.decode_header_value(
                    x.get("subject", "")
                ).lower(),
                "1": lambda x: x.get("date", ""),  # 默认
            }

            sort_key = sort_functions.get(sort_choice, sort_functions["1"])
            reverse = sort_choice == "1"  # 只有默认排序是降序

            emails.sort(key=sort_key, reverse=reverse)
            print("✅ 排序完成")

        except Exception as e:
            logger.warning(f"排序时出错: {e}")
            print("⚠️  排序失败，使用默认顺序")

        return emails

    def _display_email_list(self, emails):
        """显示邮件列表"""
        from common.email_header_processor import EmailHeaderProcessor

        print("-" * 60)
        print(
            f"{'ID':<5} {'类型':<6} {'状态':<6} {'日期':<20} {'发件人':<30} {'主题':<30}"
        )
        print("-" * 110)

        for i, email in enumerate(emails):
            # 邮件信息
            email_type = "📤发送" if email.get("type") == "sent" else "📥收件"
            status = "✅已读" if email.get("is_read") else "📬未读"
            date = email.get("date", "")

            # 解码和截断显示字段
            sender = EmailHeaderProcessor.decode_header_value(
                email.get("from_addr", "")
            )
            subject = EmailHeaderProcessor.decode_header_value(email.get("subject", ""))

            sender = sender[:28] + ".." if len(sender) > 30 else sender
            subject = subject[:28] + ".." if len(subject) > 30 else subject

            print(
                f"{i+1:<5} {email_type:<6} {status:<6} {date:<20} {sender:<30} {subject:<30}"
            )

    def _handle_email_selection(self, emails):
        """处理邮件选择"""
        from common.email_header_processor import EmailHeaderProcessor

        print("-" * 110)
        while True:
            choice = input("\n📧 请输入要查看的邮件ID (或按回车返回): ").strip()
            if not choice:
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(emails):
                    self.main_cli.set_current_email(emails[idx])

                    # 设置当前文件夹
                    folder = "sent" if emails[idx].get("type") == "sent" else "inbox"
                    self.main_cli.set_current_folder(folder)

                    # 显示确认
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

    def _extract_searchable_content(self, raw_content):
        """
        从原始邮件内容中提取可搜索的纯文本

        Args:
            raw_content: 原始邮件内容（MIME格式）

        Returns:
            提取的纯文本内容
        """
        if not raw_content:
            return ""

        try:
            # 使用邮件解析器解析MIME内容
            from common.email_format_handler import EmailFormatHandler

            parsed_email = EmailFormatHandler.parse_mime_message(raw_content)

            # 组合文本内容进行搜索
            search_content = ""

            # 添加主题
            if parsed_email.subject:
                search_content += parsed_email.subject + "\n"

            # 添加纯文本内容
            if parsed_email.text_content:
                search_content += parsed_email.text_content + "\n"

            # 如果没有纯文本，尝试从HTML中提取文本
            if not parsed_email.text_content and parsed_email.html_content:
                try:
                    import re

                    # 简单的HTML标签移除
                    html_text = re.sub(r"<[^>]+>", " ", parsed_email.html_content)
                    # 解码HTML实体
                    import html

                    html_text = html.unescape(html_text)
                    # 清理多余空白
                    html_text = re.sub(r"\s+", " ", html_text).strip()
                    search_content += html_text + "\n"
                except Exception as e:
                    logger.debug(f"HTML内容解析失败: {e}")

            return search_content.strip()

        except Exception as e:
            logger.debug(f"邮件内容解析失败，使用简单搜索: {e}")
            # 解析失败时，直接在原始内容中搜索
            return self._simple_text_extraction(raw_content)

    def _simple_text_extraction(self, raw_content):
        """
        简单的文本提取方法，作为解析失败时的备选方案

        Args:
            raw_content: 原始邮件内容

        Returns:
            提取的文本内容
        """
        try:
            import email
            import re

            # 尝试基本的邮件解析
            msg = email.message_from_string(raw_content)

            extracted_text = ""

            # 提取主题
            subject = msg.get("Subject", "")
            if subject:
                # 解码主题
                from email.header import decode_header

                decoded_parts = decode_header(subject)
                subject_text = ""
                for part, encoding in decoded_parts:
                    if isinstance(part, bytes):
                        subject_text += part.decode(
                            encoding or "utf-8", errors="ignore"
                        )
                    else:
                        subject_text += str(part)
                extracted_text += subject_text + "\n"

            # 提取邮件正文
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            try:
                                charset = part.get_content_charset() or "utf-8"
                                text_content = payload.decode(charset, errors="ignore")
                                extracted_text += text_content + "\n"
                            except:
                                continue
                    elif part.get_content_type() == "text/html":
                        # 如果没有纯文本，尝试从HTML提取
                        if "text/plain" not in str(msg):
                            payload = part.get_payload(decode=True)
                            if payload:
                                try:
                                    charset = part.get_content_charset() or "utf-8"
                                    html_content = payload.decode(
                                        charset, errors="ignore"
                                    )
                                    # 简单HTML标签移除
                                    text_content = re.sub(r"<[^>]+>", " ", html_content)
                                    text_content = re.sub(
                                        r"\s+", " ", text_content
                                    ).strip()
                                    extracted_text += text_content + "\n"
                                except:
                                    continue
            else:
                # 单部分邮件
                if msg.get_content_type() == "text/plain":
                    payload = msg.get_payload(decode=True)
                    if payload:
                        try:
                            charset = msg.get_content_charset() or "utf-8"
                            extracted_text += payload.decode(charset, errors="ignore")
                        except:
                            pass

            return extracted_text.strip()

        except Exception as e:
            logger.debug(f"简单文本提取失败: {e}")
            # 最后的备选方案：直接在原始内容中搜索（但这效果可能不好）
            return raw_content[:1000]  # 只搜索前1000字符

    def _parse_email_date(self, date_str):
        """
        解析邮件日期 - 支持多种格式包括ISO 8601

        Args:
            date_str: 日期字符串

        Returns:
            解析后的日期对象（无时区信息，转换为本地时间）
        """
        try:
            from datetime import datetime
            import re

            if not date_str:
                return None

            # 1. 首先尝试解析 ISO 8601 格式（如：2025-05-29T22:40:01+08:00）
            try:
                from dateutil import parser as date_parser

                # 使用dateutil库解析，它可以处理大部分ISO格式
                parsed_date = date_parser.isoparse(date_str)
                # 转换为无时区的本地时间进行比较
                if parsed_date.tzinfo:
                    # 转换为本地时间
                    local_date = parsed_date.astimezone().replace(tzinfo=None)
                    return local_date
                else:
                    return parsed_date
            except (ImportError, ValueError):
                # 如果没有dateutil库或解析失败，继续尝试其他方法
                pass

            # 2. 手动解析ISO 8601格式
            # 处理格式如：2025-05-29T22:40:01+08:00
            iso_pattern = r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})([+-]\d{2}:\d{2})?"
            match = re.match(iso_pattern, date_str)
            if match:
                date_part = match.group(1)
                time_part = match.group(2)
                timezone_part = match.group(3)

                # 构建基础日期时间
                base_datetime = datetime.strptime(
                    f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S"
                )

                # 如果有时区信息，进行转换（假设是北京时间+08:00）
                if timezone_part:
                    # 简单处理：如果是+08:00，认为是北京时间，直接使用
                    # 如果是其他时区，暂时也当作本地时间处理
                    return base_datetime
                else:
                    return base_datetime

            # 3. 尝试标准日期格式
            date_formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S",
                "%d %b %Y %H:%M:%S",
            ]

            for fmt in date_formats:
                try:
                    # 移除微秒部分
                    clean_date_str = (
                        date_str.split(".")[0] if "." in date_str else date_str
                    )
                    return datetime.strptime(clean_date_str, fmt)
                except ValueError:
                    continue

            # 如果所有格式都解析失败，返回None
            logger.debug(f"无法解析日期格式: {date_str}")
            return None

        except Exception as e:
            logger.warning(f"解析邮件日期时出错: {e}")
            return None
