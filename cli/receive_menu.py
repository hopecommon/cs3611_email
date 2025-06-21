# -*- coding: utf-8 -*-
"""
接收邮件菜单模块
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from client.pop3_client_refactored import POP3ClientRefactored
from common.config import EMAIL_STORAGE_DIR

# 设置日志
logger = setup_logging("receive_menu")


class ReceiveEmailMenu:
    """接收邮件菜单"""

    def __init__(self, main_cli):
        """初始化接收邮件菜单"""
        self.main_cli = main_cli
        self.pop3_client = None

    def show_menu(self):
        """显示接收邮件菜单"""
        while True:
            self.main_cli.clear_screen()
            print("\n" + "=" * 60)
            print("📥 接收邮件")
            print("=" * 60)

            # 显示当前账户信息
            current_account = self.main_cli.get_current_account_info()
            if current_account:
                print(
                    f"📧 当前收件账户: {current_account['display_name']} ({current_account['email']})"
                )
            else:
                print("❌ 未配置收件账户")
                input("请先在账户设置中配置邮箱账户，按回车键返回...")
                return

            print("\n" + "-" * 60)
            print("1. 📬 接收所有邮件")
            print("2. 📮 接收最新邮件")
            print("3. 📭 接收未读邮件")
            print("4. 📁 导入现有邮件文件")
            print("5. 🔍 设置过滤条件")
            print("0. 🔙 返回主菜单")
            print("-" * 60)

            choice = input("\n请选择操作 [0-5]: ").strip()

            if choice == "1":
                self._receive_all_emails()
            elif choice == "2":
                self._receive_latest_emails()
            elif choice == "3":
                self._receive_unread_emails()
            elif choice == "4":
                self._import_existing_emails()
            elif choice == "5":
                self._set_email_filters()
            elif choice == "0":
                return
            else:
                input("❌ 无效选择，请按回车键继续...")

    def _init_pop3_client(self):
        """初始化POP3客户端"""
        try:
            # 获取当前账户的POP3配置
            pop3_config = self.main_cli.get_pop3_config()
            if not pop3_config:
                print("❌ 未找到POP3配置，请先在账户设置中配置邮箱账户")
                return False

            # 检查是否已有客户端，且配置是否发生变化
            if self.pop3_client:
                # 检查配置是否有变化
                current_config = {
                    "host": pop3_config["host"],
                    "port": pop3_config["port"],
                    "username": pop3_config["username"],
                    "use_ssl": pop3_config.get("use_ssl", True),
                }

                # 如果有记录的配置且与当前配置相同，直接返回
                if (
                    hasattr(self, "_last_pop3_config")
                    and self._last_pop3_config == current_config
                ):
                    return True
                else:
                    # 配置有变化，清理旧客户端
                    try:
                        if hasattr(self.pop3_client, "disconnect"):
                            self.pop3_client.disconnect()
                    except Exception as e:
                        logger.debug(f"清理旧POP3连接时出错: {e}")
                    self.pop3_client = None
                    print("🔄 检测到账号配置变更，正在重新连接...")

            print(f"🔄 正在连接到 {pop3_config['host']}:{pop3_config['port']}...")

            # 创建POP3客户端
            self.pop3_client = POP3ClientRefactored(
                host=pop3_config["host"],
                port=pop3_config["port"],
                use_ssl=pop3_config.get("use_ssl", True),
                username=pop3_config["username"],
                password=pop3_config["password"],
            )

            # 记录当前配置，用于下次比较
            self._last_pop3_config = {
                "host": pop3_config["host"],
                "port": pop3_config["port"],
                "username": pop3_config["username"],
                "use_ssl": pop3_config.get("use_ssl", True),
            }

            logger.info(
                f"POP3客户端已初始化: {pop3_config['host']}:{pop3_config['port']}"
            )
            print(f"✅ 已连接到邮件服务器")
            return True

        except Exception as e:
            logger.error(f"初始化POP3客户端失败: {e}")
            print(f"❌ 连接邮件服务器失败: {e}")
            print("💡 请检查网络连接和账户配置")
            return False

    def _receive_all_emails(self):
        """接收所有邮件"""
        try:
            if not self._init_pop3_client():
                input("\n按回车键继续...")
                return

            print(f"\n🔄 正在连接到邮箱...")

            # 使用上下文管理器确保连接正确关闭
            with self.pop3_client as client:
                # 连接时会自动进行认证

                # 获取邮件列表
                email_list = client.list_emails()
                if not email_list:
                    print("📭 邮箱中没有邮件")
                    input("\n按回车键继续...")
                    return

                print(f"📊 邮箱中有 {len(email_list)} 封邮件")

                # 确认是否继续
                if len(email_list) > 10:
                    confirm = (
                        input(
                            f"⚠️  邮件数量较多({len(email_list)}封)，确认接收所有邮件? (Y/n): "
                        )
                        .strip()
                        .lower()
                    )
                    if confirm in ["n", "no"]:
                        print("❌ 操作已取消")
                        input("按回车键继续...")
                        return

                # 获取所有邮件
                print("🚀 正在获取邮件...")
                emails = client.retrieve_all_emails()

                if emails:
                    print(f"✅ 成功获取了 {len(emails)} 封邮件")

                    # 保存邮件
                    saved_count = 0
                    db_saved_count = 0

                    # 获取数据库服务
                    db = self.main_cli.get_db()

                    for i, email in enumerate(emails, 1):
                        try:
                            print(
                                f"📧 处理邮件 {i}/{len(emails)}: {email.subject or '(无主题)'}"
                            )

                            # 确保目录存在
                            inbox_dir = os.path.join(EMAIL_STORAGE_DIR, "inbox")
                            os.makedirs(inbox_dir, exist_ok=True)

                            # 保存邮件文件
                            filepath = client.save_email_as_eml(email, inbox_dir)
                            if filepath:
                                saved_count += 1

                                # 保存到数据库
                                try:
                                    # 读取EML文件内容
                                    with open(filepath, "r", encoding="utf-8") as f:
                                        eml_content = f.read()

                                    # 提取邮件基本信息
                                    from_addr = (
                                        str(email.from_addr)
                                        if email.from_addr
                                        else "unknown@localhost"
                                    )
                                    to_addrs = (
                                        [str(addr) for addr in email.to_addrs]
                                        if email.to_addrs
                                        else ["unknown@localhost"]
                                    )

                                    # 修复：获取当前账户信息，确保邮件归属正确
                                    current_account = (
                                        self.main_cli.get_current_account()
                                    )
                                    if current_account:
                                        current_user_email = current_account["email"]
                                        # 确保当前用户在收件人列表中（如果不在，添加到抄送）
                                        if current_user_email not in to_addrs:
                                            # 检查是否在原始邮件的To, CC, BCC中
                                            if (
                                                hasattr(email, "cc_addrs")
                                                and email.cc_addrs
                                            ):
                                                cc_addrs = [
                                                    str(addr) for addr in email.cc_addrs
                                                ]
                                                if current_user_email not in cc_addrs:
                                                    to_addrs.append(current_user_email)
                                            else:
                                                to_addrs.append(current_user_email)

                                    # 提取纯文本内容用于垃圾过滤分析
                                    plain_text_content = email.text_content or ""
                                    if not plain_text_content and email.html_content:
                                        # 如果没有纯文本，从HTML中提取
                                        try:
                                            from bs4 import BeautifulSoup

                                            soup = BeautifulSoup(
                                                email.html_content, "html.parser"
                                            )
                                            plain_text_content = soup.get_text()
                                        except ImportError:
                                            # 如果没有BeautifulSoup，使用简单的HTML标签移除
                                            import re

                                            plain_text_content = re.sub(
                                                r"<[^>]+>", "", email.html_content or ""
                                            )

                                    success = db.save_email(
                                        message_id=email.message_id,
                                        from_addr=from_addr,
                                        to_addrs=to_addrs,
                                        subject=email.subject or "",
                                        content=plain_text_content,  # 传递纯文本内容用于垃圾过滤
                                        full_content_for_storage=eml_content,  # 传递完整EML内容用于存储
                                        date=email.date,
                                    )

                                    if success:
                                        db_saved_count += 1

                                except Exception as db_err:
                                    logger.error(f"保存邮件到数据库失败: {db_err}")
                                    print(f"⚠️  保存邮件到数据库失败: {db_err}")

                        except Exception as e:
                            logger.error(f"保存邮件失败: {e}")
                            print(f"❌ 保存邮件失败: {e}")

                    print(f"\n🎉 接收完成!")
                    print(f"✅ 成功保存了 {saved_count} 封邮件到: {inbox_dir}")
                    print(f"✅ 成功保存了 {db_saved_count} 封邮件到数据库")
                else:
                    print("❌ 未获取到任何邮件")

        except Exception as e:
            logger.error(f"接收邮件时出错: {e}")
            print(f"❌ 接收邮件时出错: {e}")

        # 自动进行垃圾邮件重新扫描
        if db_saved_count > 0:
            self._auto_spam_rescan(db_saved_count)

        input("\n按回车键继续...")

    def _receive_latest_emails(self):
        """接收最新邮件"""
        try:
            if not self._init_pop3_client():
                input("\n按回车键继续...")
                return

            # 获取要接收的邮件数量
            try:
                count = int(input("📊 请输入要接收的最新邮件数量 (默认: 5): ") or "5")
                if count <= 0:
                    print("❌ 邮件数量必须大于0")
                    input("按回车键继续...")
                    return
            except ValueError:
                print("❌ 请输入有效的数字")
                input("按回车键继续...")
                return

            print(f"\n🔄 正在连接到邮箱...")

            with self.pop3_client as client:
                # 获取邮件列表
                email_list = client.list_emails()
                if not email_list:
                    print("📭 邮箱中没有邮件")
                    input("\n按回车键继续...")
                    return

                print(f"📊 邮箱中有 {len(email_list)} 封邮件")

                # 计算实际要获取的邮件数量
                actual_count = min(count, len(email_list))
                print(f"🚀 正在获取最新 {actual_count} 封邮件...")

                # 获取最新的邮件（从列表末尾开始）
                latest_emails = []
                for i in range(len(email_list) - actual_count, len(email_list)):
                    email_info = email_list[i]
                    email = client.retrieve_email(
                        email_info[0]
                    )  # email_info[0] 是邮件ID
                    if email:
                        latest_emails.append(email)

                if latest_emails:
                    print(f"✅ 成功获取了 {len(latest_emails)} 封邮件")

                    # 保存邮件
                    saved_count = 0
                    db_saved_count = 0
                    db = self.main_cli.get_db()

                    for i, email in enumerate(latest_emails, 1):
                        try:
                            print(
                                f"📧 处理邮件 {i}/{len(latest_emails)}: {email.subject or '(无主题)'}"
                            )

                            # 确保目录存在
                            inbox_dir = os.path.join(EMAIL_STORAGE_DIR, "inbox")
                            os.makedirs(inbox_dir, exist_ok=True)

                            # 保存邮件文件
                            filepath = client.save_email_as_eml(email, inbox_dir)
                            if filepath:
                                saved_count += 1

                                # 保存到数据库
                                try:
                                    with open(filepath, "r", encoding="utf-8") as f:
                                        eml_content = f.read()

                                    from_addr = (
                                        str(email.from_addr)
                                        if email.from_addr
                                        else "unknown@localhost"
                                    )
                                    to_addrs = (
                                        [str(addr) for addr in email.to_addrs]
                                        if email.to_addrs
                                        else ["unknown@localhost"]
                                    )

                                    # 修复：获取当前账户信息，确保邮件归属正确
                                    current_account = (
                                        self.main_cli.get_current_account()
                                    )
                                    if current_account:
                                        current_user_email = current_account["email"]
                                        # 确保当前用户在收件人列表中（如果不在，添加到抄送）
                                        if current_user_email not in to_addrs:
                                            # 检查是否在原始邮件的To, CC, BCC中
                                            if (
                                                hasattr(email, "cc_addrs")
                                                and email.cc_addrs
                                            ):
                                                cc_addrs = [
                                                    str(addr) for addr in email.cc_addrs
                                                ]
                                                if current_user_email not in cc_addrs:
                                                    to_addrs.append(current_user_email)
                                            else:
                                                to_addrs.append(current_user_email)

                                    # 提取纯文本内容用于垃圾过滤分析
                                    plain_text_content = email.text_content or ""
                                    if not plain_text_content and email.html_content:
                                        # 如果没有纯文本，从HTML中提取
                                        try:
                                            from bs4 import BeautifulSoup

                                            soup = BeautifulSoup(
                                                email.html_content, "html.parser"
                                            )
                                            plain_text_content = soup.get_text()
                                        except ImportError:
                                            # 如果没有BeautifulSoup，使用简单的HTML标签移除
                                            import re

                                            plain_text_content = re.sub(
                                                r"<[^>]+>", "", email.html_content or ""
                                            )

                                    success = db.save_email(
                                        message_id=email.message_id,
                                        from_addr=from_addr,
                                        to_addrs=to_addrs,
                                        subject=email.subject or "",
                                        content=plain_text_content,  # 传递纯文本内容用于垃圾过滤
                                        full_content_for_storage=eml_content,  # 传递完整EML内容用于存储
                                        date=email.date,
                                    )

                                    if success:
                                        db_saved_count += 1

                                except Exception as db_err:
                                    logger.error(f"保存邮件到数据库失败: {db_err}")
                                    print(f"⚠️  保存邮件到数据库失败: {db_err}")

                        except Exception as e:
                            logger.error(f"保存邮件失败: {e}")
                            print(f"❌ 保存邮件失败: {e}")

                    print(f"\n🎉 接收完成!")
                    print(f"✅ 成功保存了 {saved_count} 封邮件到: {inbox_dir}")
                    print(f"✅ 成功保存了 {db_saved_count} 封邮件到数据库")

                    # 自动进行垃圾邮件重新扫描
                    if db_saved_count > 0:
                        self._auto_spam_rescan(db_saved_count)
                else:
                    print("❌ 未获取到任何邮件")

        except Exception as e:
            logger.error(f"接收最新邮件时出错: {e}")
            print(f"❌ 接收最新邮件时出错: {e}")

        input("\n按回车键继续...")

    def _receive_unread_emails(self):
        """接收未读邮件"""
        print("\n⚠️  接收未读邮件功能正在开发中...")
        print("💡 您可以使用 '接收所有邮件' 或 '接收最新邮件' 功能")
        input("\n按回车键继续...")

    def _set_email_filters(self):
        """设置邮件过滤条件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("🔍 邮件过滤设置")
        print("=" * 60)
        print("⚠️  邮件过滤功能正在开发中...")
        print("\n💡 计划支持的过滤条件:")
        print("   • 发件人过滤")
        print("   • 主题关键词过滤")
        print("   • 日期范围过滤")
        print("   • 附件类型过滤")
        print("   • 邮件大小过滤")
        input("\n按回车键继续...")

    def _import_existing_emails(self):
        """导入现有邮件文件"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📁 导入邮件文件")
        print("=" * 60)

        import_path = input("📂 请输入邮件文件或目录路径: ").strip()
        if not import_path:
            print("❌ 路径不能为空")
            input("按回车键继续...")
            return

        if not os.path.exists(import_path):
            print(f"❌ 路径不存在: {import_path}")
            input("按回车键继续...")
            return

        try:
            imported_count = 0
            db = self.main_cli.get_db()

            if os.path.isfile(import_path):
                # 单个文件
                if import_path.lower().endswith(".eml"):
                    print(f"🔄 正在导入邮件文件: {os.path.basename(import_path)}")

                    with open(import_path, "r", encoding="utf-8") as f:
                        eml_content = f.read()

                    # 这里可以添加解析EML文件的逻辑
                    # 暂时使用简单的保存方式
                    success = db.save_email(
                        message_id=f"imported_{os.path.basename(import_path)}",
                        from_addr="imported@localhost",
                        to_addrs=["user@localhost"],
                        subject=f"导入的邮件: {os.path.basename(import_path)}",
                        date=None,
                        content=eml_content,
                    )

                    if success:
                        imported_count = 1
                        print("✅ 邮件导入成功")
                    else:
                        print("❌ 邮件导入失败")
                else:
                    print("❌ 不支持的文件格式，请选择.eml文件")

            elif os.path.isdir(import_path):
                # 目录
                print(f"🔄 正在扫描目录: {import_path}")
                eml_files = []
                for root, dirs, files in os.walk(import_path):
                    for file in files:
                        if file.lower().endswith(".eml"):
                            eml_files.append(os.path.join(root, file))

                if not eml_files:
                    print("❌ 目录中没有找到.eml文件")
                else:
                    print(f"📊 找到 {len(eml_files)} 个邮件文件")
                    confirm = input("确认导入所有邮件文件? (Y/n): ").strip().lower()

                    if confirm not in ["n", "no"]:
                        for eml_file in eml_files:
                            try:
                                print(f"📧 导入: {os.path.basename(eml_file)}")

                                with open(eml_file, "r", encoding="utf-8") as f:
                                    eml_content = f.read()

                                success = db.save_email(
                                    message_id=f"imported_{os.path.basename(eml_file)}",
                                    from_addr="imported@localhost",
                                    to_addrs=["user@localhost"],
                                    subject=f"导入的邮件: {os.path.basename(eml_file)}",
                                    date=None,
                                    content=eml_content,
                                )

                                if success:
                                    imported_count += 1

                            except Exception as e:
                                logger.error(f"导入邮件失败: {eml_file}, 错误: {e}")
                                print(f"❌ 导入失败: {os.path.basename(eml_file)}")
                    else:
                        print("❌ 导入操作已取消")

            print(f"\n🎉 导入完成! 成功导入 {imported_count} 封邮件")

        except Exception as e:
            logger.error(f"导入邮件时出错: {e}")
            print(f"❌ 导入邮件时出错: {e}")

        input("\n按回车键继续...")

    def _auto_spam_rescan(self, new_emails_count: int):
        """
        自动进行垃圾邮件重新扫描

        Args:
            new_emails_count: 新接收的邮件数量
        """
        try:
            print(f"\n🔍 正在进行垃圾邮件自动扫描...")

            # 获取数据库服务
            db = self.main_cli.get_db()

            # 获取垃圾过滤器
            from spam_filter.spam_filter import KeywordSpamFilter

            spam_filter = KeywordSpamFilter()

            # 获取最近的邮件进行扫描（包括刚接收的邮件）
            recent_emails = db.list_emails(
                limit=new_emails_count * 2, include_spam=True
            )

            if not recent_emails:
                print("   📭 没有邮件需要扫描")
                return

            print(f"   📊 正在扫描 {len(recent_emails)} 封邮件...")

            updated_count = 0
            spam_found = 0
            normal_found = 0

            for email in recent_emails:
                try:
                    message_id = email.get("message_id", "")
                    subject = email.get("subject", "")
                    from_addr = email.get("from_addr", "")
                    current_is_spam = email.get("is_spam", False)
                    current_spam_score = email.get("spam_score", 0.0)

                    # 获取邮件内容用于分析
                    email_with_content = db.get_email(message_id, include_content=True)
                    content = ""
                    if email_with_content:
                        content = email_with_content.get("content", "")

                    # 使用垃圾过滤器重新分析
                    analysis_data = {
                        "from_addr": from_addr,
                        "subject": subject,
                        "content": content,
                    }

                    result = spam_filter.analyze_email(analysis_data)
                    new_is_spam = result["is_spam"]
                    new_spam_score = result["score"]

                    # 检查是否需要更新
                    if (
                        new_is_spam != current_is_spam
                        or abs(new_spam_score - current_spam_score) > 0.1
                    ):
                        # 更新数据库
                        success = db.update_email(
                            message_id, is_spam=new_is_spam, spam_score=new_spam_score
                        )

                        if success:
                            updated_count += 1
                            status_old = "垃圾" if current_is_spam else "正常"
                            status_new = "垃圾" if new_is_spam else "正常"
                            print(
                                f"   📧 更新: {subject[:30]}... [{status_old}→{status_new}]"
                            )

                    # 统计
                    if new_is_spam:
                        spam_found += 1
                    else:
                        normal_found += 1

                except Exception as e:
                    logger.error(f"扫描邮件时出错: {e}")
                    continue

            # 显示扫描结果
            print(f"\n📊 垃圾邮件扫描完成:")
            print(f"   📧 扫描邮件数: {len(recent_emails)}")
            print(f"   🔄 更新邮件数: {updated_count}")
            print(f"   🚫 垃圾邮件数: {spam_found}")
            print(f"   ✅ 正常邮件数: {normal_found}")

            if spam_found > 0:
                print(f"   ⚠️  发现 {spam_found} 封垃圾邮件，已自动标记")

            if updated_count > 0:
                print(f"   ✅ 成功更新了 {updated_count} 封邮件的垃圾状态")
            else:
                print(f"   ✅ 所有邮件的垃圾状态都是正确的")

        except Exception as e:
            logger.error(f"自动垃圾邮件扫描失败: {e}")
            print(f"   ❌ 垃圾邮件扫描失败: {e}")
            print(f"   💡 您可以稍后在垃圾邮件管理中手动重新扫描")
