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
            print("\n" + "=" * 60)
            print("📋 查看邮件")
            print("=" * 60)
            print("1. 📥 收件箱")
            print("2. 📤 已发送")
            print("3. 📖 查看邮件详情")
            print("4. 🗑️  删除邮件")
            print("5. 👁️  标记为已读/未读")
            print("6. 🔙 撤回邮件")
            print("0. 🔙 返回主菜单")
            print("-" * 60)

            choice = input("\n请选择操作 [0-6]: ").strip()

            if choice == "1":
                self.main_cli.set_current_folder("inbox")
                self._list_emails()
            elif choice == "2":
                self.main_cli.set_current_folder("sent")
                self._list_emails()
            elif choice == "3":
                if not self.main_cli.get_email_list():
                    input("❌ 邮件列表为空，请先获取邮件，按回车键继续...")
                    continue
                self._view_email_details()
            elif choice == "4":
                self._delete_email()
            elif choice == "5":
                self._toggle_read_status()
            elif choice == "6":
                self._recall_email()
            elif choice == "0":
                return
            else:
                input("❌ 无效选择，请按回车键继续...")

    def _list_emails(self):
        """列出邮件"""
        self.main_cli.clear_screen()
        folder = (
            "📤 已发送" if self.main_cli.get_current_folder() == "sent" else "📥 收件箱"
        )
        print(f"\n" + "=" * 60)
        print(f"{folder}")
        print("=" * 60)

        # +++ 新增过滤选项 +++
        print("\n🔍 过滤选项:")
        print("1. 显示所有邮件")
        print("2. 仅显示正常邮件")
        print("3. 仅显示垃圾邮件")
        filter_choice = input("请选择过滤方式 [1-3]: ").strip() or "1"

        # 设置过滤参数
        include_spam = True
        if filter_choice == "2":
            include_spam = False
        elif filter_choice == "3":
            include_spam = True  # 仅显示垃圾邮件需要调整数据库查询条件

        # 从数据库获取邮件列表
        try:
            db = self.main_cli.get_db()

            # 修复：获取当前账户信息，确保邮件隔离
            current_account = self.main_cli.get_current_account()
            if not current_account:
                print("❌ 未找到当前账户信息，请先登录")
                input("\n按回车键继续...")
                return

            current_user_email = current_account["email"]
            print(f"📧 当前账户: {current_user_email}")

            if self.main_cli.get_current_folder() == "sent":
                # 查询已发送邮件：按发件人过滤
                emails = db.list_sent_emails(
                    from_addr=current_user_email,  # 修复：按发件人过滤
                    include_spam=(filter_choice != "2"),
                    is_spam=((filter_choice == "3") if filter_choice == "3" else None),
                )
            else:
                # 查询收到的邮件：按收件人过滤
                emails = db.list_emails(
                    user_email=current_user_email,  # 关键修复：按收件人过滤
                    include_spam=(filter_choice != "2"),
                    is_spam=(filter_choice == "3"),
                )

            if not emails:
                print(f"📭 {folder}中没有邮件")
                input("\n按回车键继续...")
                return

            # 保存邮件列表
            self.main_cli.set_email_list(emails)

            # 显示邮件列表
            print(f"\n📊 共找到 {len(emails)} 封邮件")
            print("-" * 60)
            print(f"{'ID':<5} {'状态':<6} {'日期':<20} {'发件人':<30} {'主题':<40}")
            print("-" * 100)

            # 导入RFC 2047解码器
            from common.email_header_processor import EmailHeaderProcessor

            for i, email in enumerate(emails):
                # 基础状态显示
                if email.get("is_recalled"):
                    status = "🔙已撤回"
                else:
                    status = "✅已读" if email.get("is_read") else "📬未读"

                date = email.get("date", "")
                sender = email.get("from_addr", email.get("sender", ""))
                subject = email.get("subject", "")

                # 解码RFC 2047编码的主题和发件人
                if subject:
                    subject = EmailHeaderProcessor.decode_header_value(subject)
                if sender:
                    sender = EmailHeaderProcessor.decode_header_value(sender)

                # 如果是撤回的邮件，在主题前加标记
                if email.get("is_recalled"):
                    subject = f"[已撤回] {subject}"

                # 截断过长的字段以适应显示
                sender = sender[:28] + ".." if len(sender) > 30 else sender
                subject = subject[:38] + ".." if len(subject) > 40 else subject

                print(f"{i+1:<5} {status:<8} {date:<20} {sender:<30} {subject:<40}")

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
                        self._view_email_details()
                        break
                    else:
                        print("❌ 无效的ID")
                except ValueError:
                    print("❌ 请输入有效的数字")
        except Exception as e:
            logger.error(f"获取邮件列表时出错: {e}")
            print(f"❌ 获取邮件列表时出错: {e}")
            input("\n按回车键继续...")

    def _view_email_details(self):
        """查看邮件详情"""
        current_email = self.main_cli.get_current_email()
        if not current_email:
            print("❌ 未选择邮件")
            input("\n按回车键继续...")
            return

        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📖 邮件详情")
        print("=" * 60)

        # 获取并解析邮件内容以获取完整信息
        try:
            db = self.main_cli.get_db()
            message_id = current_email.get("message_id")

            # 判断邮件类型：检查当前文件夹或邮件来源
            current_folder = self.main_cli.get_current_folder()
            is_sent_email = (current_folder == "sent") or current_email.get(
                "type"
            ) == "sent"

            # 根据邮件类型选择不同的获取方法
            if is_sent_email:
                content_str = db.get_sent_email_content(message_id)
                logger.debug(f"获取已发送邮件内容: {message_id}")
            else:
                content_str = db.get_email_content(message_id)
                logger.debug(f"获取接收邮件内容: {message_id}")

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

                    print(f"📋 主题: {subject}")
                    print(f"📤 发件人: {from_addr}")
                    print(f"📧 收件人: {to_addrs}")
                    print(f"📅 日期: {date}")

                    # 显示邮件类型
                    email_type = "已发送" if is_sent_email else "收件箱"
                    print(f"📁 类型: {email_type}")

                    # 显示附件信息
                    if parsed_email.attachments:
                        print(f"\n📎 附件 ({len(parsed_email.attachments)} 个):")
                        for i, attachment in enumerate(parsed_email.attachments, 1):
                            size_str = (
                                f"{attachment.size} 字节"
                                if attachment.size
                                else "未知大小"
                            )
                            print(f"  {i}. {attachment.filename} ({size_str})")

                        # 询问是否保存附件
                        save_choice = input("\n是否保存附件? (y/n): ").lower()
                        if save_choice == "y":
                            self._save_attachments(parsed_email.attachments)

                    # 显示邮件内容
                    print("\n" + "-" * 60)
                    print("📝 邮件内容:")
                    print("-" * 60)

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
                message_id = current_email.get("message_id")

                # 判断邮件类型，用于显示信息
                current_folder = self.main_cli.get_current_folder()
                is_sent_email = (current_folder == "sent") or current_email.get(
                    "type"
                ) == "sent"
                email_type = "已发送邮件" if is_sent_email else "邮件"

                # 使用统一的update_email方法，它内部会自动判断邮件类型
                success = db.update_email(message_id, is_read=True)

                if success:
                    print(f"\n📬 {email_type}已标记为已读")
                    # 更新本地邮件列表中的状态
                    current_email["is_read"] = True
                else:
                    logger.warning(f"标记{email_type}为已读失败: {message_id}")
        except Exception as e:
            logger.error(f"标记邮件为已读时出错: {e}")
            print(f"❌ 标记邮件为已读时出错: {e}")

        input("\n按回车键继续...")

    def _save_attachments(self, attachments):
        """保存附件"""
        try:
            # 创建附件保存目录
            attachments_dir = Path("attachments")
            attachments_dir.mkdir(exist_ok=True)

            print(f"\n💾 正在保存附件到 '{attachments_dir}' 目录...")

            from client.mime_handler import MIMEHandler

            saved_count = 0
            for i, attachment in enumerate(attachments, 1):
                try:
                    saved_path = MIMEHandler.decode_attachment(
                        attachment, str(attachments_dir)
                    )
                    print(f"  ✅ 附件 {i}: {attachment.filename} -> {saved_path}")
                    saved_count += 1
                except Exception as e:
                    print(f"  ❌ 附件 {i}: {attachment.filename} 保存失败 - {e}")

            print(f"\n🎉 成功保存 {saved_count}/{len(attachments)} 个附件")

        except Exception as e:
            logger.error(f"保存附件时出错: {e}")
            print(f"❌ 保存附件时出错: {e}")

    def _delete_email(self):
        """删除邮件"""
        email_list = self.main_cli.get_email_list()

        # 如果邮件列表为空，引导用户先查看邮件列表
        if not email_list:
            self.main_cli.clear_screen()
            print("\n" + "=" * 60)
            print("🗑️  删除邮件")
            print("=" * 60)
            print("❌ 当前没有邮件列表")
            print("💡 请先选择 '收件箱' 或 '已发送' 来查看邮件列表")
            input("\n按回车键返回...")
            return

        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("🗑️  删除邮件")
        print("=" * 60)

        # 显示当前邮件列表
        print(f"\n📊 当前邮件列表 (共 {len(email_list)} 封)")
        print("-" * 60)
        print(f"{'ID':<5} {'状态':<6} {'日期':<20} {'发件人':<30} {'主题':<40}")
        print("-" * 100)

        for i, email in enumerate(email_list):
            status = "✅已读" if email.get("is_read") else "📬未读"
            date = email.get("date", "")
            sender = email.get("from_addr", email.get("sender", ""))
            subject = email.get("subject", "")

            # 解码RFC 2047编码的主题和发件人
            from common.email_header_processor import EmailHeaderProcessor

            if subject:
                subject = EmailHeaderProcessor.decode_header_value(subject)
            if sender:
                sender = EmailHeaderProcessor.decode_header_value(sender)

            # 截断过长的字段以适应显示
            sender = sender[:28] + ".." if len(sender) > 30 else sender
            subject = subject[:38] + ".." if len(subject) > 40 else subject

            print(f"{i+1:<5} {status:<6} {date:<20} {sender:<30} {subject:<40}")

        # 选择要删除的邮件
        print("-" * 100)
        while True:
            choice = input("\n🗑️  请输入要删除的邮件ID (或按回车返回): ").strip()
            if not choice:
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(email_list):
                    email = email_list[idx]
                    subject = email.get("subject", "(无主题)")

                    # 解码主题用于显示
                    from common.email_header_processor import EmailHeaderProcessor

                    display_subject = EmailHeaderProcessor.decode_header_value(subject)

                    # 确认删除
                    print(f"\n⚠️  确认删除操作")
                    print(f"📧 邮件主题: {display_subject}")
                    print(f"📤 发件人: {email.get('from_addr', '未知')}")
                    print(f"📅 日期: {email.get('date', '未知')}")

                    confirm = (
                        input(f"\n❓ 确定要删除这封邮件吗? (y/N): ").strip().lower()
                    )

                    if confirm in ["y", "yes"]:
                        try:
                            # 执行删除操作
                            db = self.main_cli.get_db()
                            message_id = email.get("message_id")

                            # 判断是否为已发送邮件
                            current_folder = self.main_cli.get_current_folder()
                            is_sent_email = (current_folder == "sent") or email.get(
                                "type"
                            ) == "sent"

                            if is_sent_email:
                                # 删除已发送邮件
                                success = db.delete_sent_email_metadata(message_id)
                                email_type = "已发送邮件"
                            else:
                                # 软删除接收邮件（标记为已删除）
                                success = db.update_email(message_id, is_deleted=True)
                                email_type = "邮件"

                            if success:
                                print(f"✅ {email_type}删除成功！")

                                # 从本地列表中移除
                                email_list.pop(idx)
                                self.main_cli.set_email_list(email_list)

                                # 如果列表为空，提示用户
                                if not email_list:
                                    print("📭 邮件列表已清空")
                                    input("\n按回车键返回...")
                                    return

                                # 询问是否继续删除
                                continue_choice = (
                                    input(f"\n❓ 是否继续删除其他邮件? (y/N): ")
                                    .strip()
                                    .lower()
                                )
                                if continue_choice not in ["y", "yes"]:
                                    input("\n按回车键返回...")
                                    return

                                # 重新显示列表
                                break
                            else:
                                print(f"❌ {email_type}删除失败！")
                                input("\n按回车键继续...")
                        except Exception as e:
                            logger.error(f"删除邮件时出错: {e}")
                            print(f"❌ 删除邮件时出错: {e}")
                            input("\n按回车键继续...")
                    else:
                        print("❌ 删除操作已取消")
                        input("\n按回车键继续...")
                        return
                else:
                    print("❌ 无效的邮件ID")
            except ValueError:
                print("❌ 请输入有效的数字")

    def _toggle_read_status(self):
        """切换邮件已读/未读状态"""
        email_list = self.main_cli.get_email_list()

        # 如果邮件列表为空，引导用户先查看邮件列表
        if not email_list:
            self.main_cli.clear_screen()
            print("\n" + "=" * 60)
            print("👁️  标记邮件状态")
            print("=" * 60)
            print("❌ 当前没有邮件列表")
            print("💡 请先选择 '收件箱' 或 '已发送' 来查看邮件列表")
            input("\n按回车键返回...")
            return

        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("👁️  标记邮件状态")
        print("=" * 60)

        # 显示当前邮件列表
        print(f"\n📊 当前邮件列表 (共 {len(email_list)} 封)")
        print("-" * 60)
        print(f"{'ID':<5} {'状态':<6} {'日期':<20} {'发件人':<30} {'主题':<40}")
        print("-" * 100)

        for i, email in enumerate(email_list):
            status = "✅已读" if email.get("is_read") else "📬未读"
            date = email.get("date", "")
            sender = email.get("from_addr", email.get("sender", ""))
            subject = email.get("subject", "")

            # 解码RFC 2047编码的主题和发件人
            from common.email_header_processor import EmailHeaderProcessor

            if subject:
                subject = EmailHeaderProcessor.decode_header_value(subject)
            if sender:
                sender = EmailHeaderProcessor.decode_header_value(sender)

            # 截断过长的字段以适应显示
            sender = sender[:28] + ".." if len(sender) > 30 else sender
            subject = subject[:38] + ".." if len(subject) > 40 else subject

            print(f"{i+1:<5} {status:<6} {date:<20} {sender:<30} {subject:<40}")

        # 选择要修改状态的邮件
        print("-" * 100)
        while True:
            choice = input("\n👁️  请输入要修改状态的邮件ID (或按回车返回): ").strip()
            if not choice:
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(email_list):
                    email = email_list[idx]
                    current_status = email.get("is_read", False)
                    new_status = not current_status
                    status_text = "已读" if new_status else "未读"

                    subject = email.get("subject", "(无主题)")
                    from common.email_header_processor import EmailHeaderProcessor

                    display_subject = EmailHeaderProcessor.decode_header_value(subject)

                    # 确认操作
                    print(f"\n📧 邮件: {display_subject}")
                    print(f"🔄 当前状态: {'已读' if current_status else '未读'}")
                    print(f"🎯 将变更为: {status_text}")

                    confirm = (
                        input(f"\n❓ 确认将邮件标记为{status_text}? (y/N): ")
                        .strip()
                        .lower()
                    )

                    if confirm in ["y", "yes"]:
                        try:
                            # 执行状态更新
                            db = self.main_cli.get_db()
                            message_id = email.get("message_id")

                            success = db.update_email(message_id, is_read=new_status)

                            if success:
                                print(f"✅ 邮件已标记为{status_text}！")

                                # 更新本地列表状态
                                email["is_read"] = new_status

                                input("\n按回车键继续...")
                                break
                            else:
                                print(f"❌ 状态更新失败！")
                                input("\n按回车键继续...")
                        except Exception as e:
                            logger.error(f"更新邮件状态时出错: {e}")
                            print(f"❌ 更新邮件状态时出错: {e}")
                            input("\n按回车键继续...")
                    else:
                        print("❌ 操作已取消")
                        input("\n按回车键继续...")
                        return
                else:
                    print("❌ 无效的邮件ID")
            except ValueError:
                print("❌ 请输入有效的数字")

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

        print(f"📋 主题: {subject}")
        print(f"📤 发件人: {from_addr}")
        print(f"📧 收件人: {to_addrs}")
        print(f"📅 日期: {email_data.get('date', '(未知日期)')}")
        print("\n📝 邮件内容: (无法获取)")

    def _display_fallback_email_info(self, email_data, content_str):
        """回退显示方法，当EmailFormatHandler解析失败时使用"""
        # 显示基本信息
        self._display_basic_email_info(email_data)

        # 尝试简单的内容提取和附件检测
        print("\n" + "-" * 60)
        print("📝 邮件正文")
        print("-" * 60)
        readable_content, attachments_info = (
            self._extract_readable_content_and_attachments(content_str)
        )

        if len(readable_content) > 2000:
            print(readable_content[:2000] + "\n...(内容过长，已截断)")
        else:
            print(readable_content)

        # 显示检测到的附件信息
        if attachments_info:
            print(f"\n📎 检测到附件:")
            for i, att_info in enumerate(attachments_info, 1):
                print(f"  {i}. {att_info}")

    def _extract_readable_content_and_attachments(self, content_str: str):
        """
        从MIME内容中提取可读的文本内容和附件信息

        Args:
            content_str: 原始MIME内容字符串

        Returns:
            (可读的文本内容, 附件信息列表)
        """
        try:
            import email
            import base64
            import re

            # 解析MIME消息
            msg = email.message_from_string(content_str)

            # 提取文本内容
            text_content = []
            attachments_info = []

            if msg.is_multipart():
                # 多部分消息，遍历所有部分
                for part in msg.walk():
                    # 跳过multipart容器本身
                    if part.get_content_maintype() == "multipart":
                        continue

                    content_type = part.get_content_type()
                    content_disposition = part.get_content_disposition()

                    # 检查是否是附件
                    if content_disposition == "attachment" or (
                        content_disposition and "attachment" in content_disposition
                    ):
                        filename = part.get_filename() or "未知文件"
                        try:
                            payload = part.get_payload(decode=True)
                            size = len(payload) if payload else 0
                            size_str = (
                                f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
                            )
                            attachments_info.append(
                                f"📄 {filename} ({content_type}, {size_str})"
                            )
                        except:
                            attachments_info.append(f"📄 {filename} ({content_type})")
                        continue

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
                content_disposition = msg.get_content_disposition()

                # 检查是否是附件
                if content_disposition == "attachment":
                    filename = msg.get_filename() or "未知文件"
                    try:
                        payload = msg.get_payload(decode=True)
                        size = len(payload) if payload else 0
                        size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
                        attachments_info.append(
                            f"📄 {filename} ({content_type}, {size_str})"
                        )
                    except:
                        attachments_info.append(f"📄 {filename} ({content_type})")
                elif content_type.startswith("text/"):
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

            # 返回合并的文本内容和附件信息
            if text_content:
                result = "\n\n".join(text_content).strip()
                return (result if result else "邮件内容为空", attachments_info)
            else:
                return (
                    f"无法解析邮件内容，原始内容摘要:\n{content_str[:300]}...",
                    attachments_info,
                )

        except Exception as e:
            logger.error(f"提取可读内容失败: {e}")
            return (f"内容解析失败: {e}\n\n原始内容:\n{content_str[:300]}...", [])

    def _recall_email(self):
        """撤回邮件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("🔙 撤回邮件")
        print("=" * 60)

        # 获取当前账户信息
        current_account = self.main_cli.get_current_account()
        if not current_account:
            print("❌ 未找到当前账户信息，请先登录")
            input("\n按回车键继续...")
            return

        current_user_email = current_account["email"]

        # 获取可撤回的邮件列表
        try:
            db = self.main_cli.get_db()

            print(f"📧 正在获取您可撤回的邮件列表...")
            recallable_emails = db.get_recallable_emails(current_user_email)

            if not recallable_emails:
                print("\n📭 您当前没有可撤回的邮件")
                print("💡 提示:")
                print("   • 只能撤回24小时内发送的邮件")
                print("   • 已撤回的邮件无法再次撤回")
                print("   • 只能撤回您自己发送的邮件")
                input("\n按回车键返回...")
                return

            # 显示可撤回邮件列表
            print(f"\n📊 可撤回邮件列表 (共 {len(recallable_emails)} 封)")
            print("-" * 60)
            print(f"{'ID':<5} {'日期':<20} {'收件人':<30} {'主题':<40}")
            print("-" * 100)

            for i, email in enumerate(recallable_emails):
                date = email.get("date", "")
                # 获取收件人信息
                to_addrs = email.get("to_addrs", "")
                if isinstance(to_addrs, list):
                    recipients = ", ".join(
                        [str(addr) for addr in to_addrs[:2]]
                    )  # 最多显示2个收件人
                    if len(to_addrs) > 2:
                        recipients += f" (+{len(to_addrs)-2})"
                else:
                    recipients = str(to_addrs)

                subject = email.get("subject", "")

                # 解码RFC 2047编码的主题
                from common.email_header_processor import EmailHeaderProcessor

                if subject:
                    subject = EmailHeaderProcessor.decode_header_value(subject)

                # 截断过长的字段以适应显示
                recipients = (
                    recipients[:28] + ".." if len(recipients) > 30 else recipients
                )
                subject = subject[:38] + ".." if len(subject) > 40 else subject

                print(f"{i+1:<5} {date:<20} {recipients:<30} {subject:<40}")

            # 选择要撤回的邮件
            print("-" * 100)
            while True:
                choice = input("\n🔙 请输入要撤回的邮件ID (或按回车返回): ").strip()
                if not choice:
                    return

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(recallable_emails):
                        email = recallable_emails[idx]
                        subject = email.get("subject", "(无主题)")
                        message_id = email.get("message_id")

                        # 解码主题用于显示
                        from common.email_header_processor import EmailHeaderProcessor

                        display_subject = EmailHeaderProcessor.decode_header_value(
                            subject
                        )

                        # 显示详细信息和确认
                        print(f"\n⚠️  确认撤回操作")
                        print(f"📧 邮件主题: {display_subject}")

                        # 显示收件人
                        to_addrs = email.get("to_addrs", [])
                        if isinstance(to_addrs, list):
                            print(
                                f"📨 收件人: {', '.join([str(addr) for addr in to_addrs])}"
                            )
                        else:
                            print(f"📨 收件人: {to_addrs}")

                        print(f"📅 发送时间: {email.get('date', '未知')}")
                        print("\n🔔 注意: 撤回后收件人将无法查看此邮件内容")

                        confirm = (
                            input(f"\n❓ 确定要撤回这封邮件吗? (y/N): ").strip().lower()
                        )

                        if confirm in ["y", "yes"]:
                            try:
                                # 执行撤回操作
                                print("🔄 正在撤回邮件...")
                                result = db.recall_email(message_id, current_user_email)

                                if result["success"]:
                                    print(f"✅ {result['message']}")
                                    print("📧 收件人将无法再查看此邮件")

                                    # 从列表中移除已撤回的邮件
                                    recallable_emails.pop(idx)

                                    # 如果列表为空，提示用户
                                    if not recallable_emails:
                                        print("\n📭 所有可撤回邮件已处理完毕")
                                        input("\n按回车键返回...")
                                        return

                                    # 询问是否继续撤回
                                    continue_choice = (
                                        input(f"\n❓ 是否继续撤回其他邮件? (y/N): ")
                                        .strip()
                                        .lower()
                                    )
                                    if continue_choice not in ["y", "yes"]:
                                        input("\n按回车键返回...")
                                        return

                                    # 重新显示列表
                                    break
                                else:
                                    print(f"❌ {result['message']}")
                                    input("\n按回车键继续...")
                            except Exception as e:
                                logger.error(f"撤回邮件时出错: {e}")
                                print(f"❌ 撤回邮件时出错: {e}")
                                input("\n按回车键继续...")
                        else:
                            print("❌ 撤回操作已取消")
                            input("\n按回车键继续...")
                            return
                    else:
                        print("❌ 无效的邮件ID")
                except ValueError:
                    print("❌ 请输入有效的数字")

        except Exception as e:
            logger.error(f"获取可撤回邮件列表时出错: {e}")
            print(f"❌ 获取邮件列表时出错: {e}")
            input("\n按回车键继续...")
