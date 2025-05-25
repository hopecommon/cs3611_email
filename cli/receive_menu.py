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
            print("\n===== 接收邮件 =====")
            print("1. 接收所有邮件")
            print("2. 接收最新邮件")
            print("3. 接收未读邮件")
            print("4. 导入现有邮件文件")
            print("5. 设置过滤条件")
            print("0. 返回主菜单")

            choice = input("\n请选择操作 [0-5]: ")

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
                input("无效选择，请按回车键继续...")

    def _init_pop3_client(self):
        """初始化POP3客户端"""
        if self.pop3_client:
            return True

        try:
            # 使用本地服务器配置
            print("\n请输入POP3服务器信息:")
            host = input("服务器地址 (默认: localhost): ") or "localhost"
            port = input("端口 (默认: 995): ") or "995"
            username = input("用户名 (默认: testuser): ") or "testuser"

            import getpass

            password = getpass.getpass("密码 (默认: testpass): ") or "testpass"

            use_ssl = input("使用SSL? (y/n, 默认: y): ").lower() != "n"

            # 创建POP3客户端（包含认证信息）
            self.pop3_client = POP3ClientRefactored(
                host=host,
                port=int(port),
                use_ssl=use_ssl,
                username=username,
                password=password,
            )

            logger.info(f"POP3客户端已初始化: {host}:{port} (SSL: {use_ssl})")
            return True

        except Exception as e:
            logger.error(f"初始化POP3客户端失败: {e}")
            print(f"初始化POP3客户端失败: {e}")
            return False

    def _receive_all_emails(self):
        """接收所有邮件"""
        try:
            if not self._init_pop3_client():
                input("\n按回车键继续...")
                return

            print("\n正在连接到邮箱...")

            # 使用上下文管理器确保连接正确关闭
            with self.pop3_client as client:
                # 连接时会自动进行认证

                # 获取邮件列表
                email_list = client.list_emails()
                if not email_list:
                    print("邮箱中没有邮件")
                    input("\n按回车键继续...")
                    return

                print(f"邮箱中有 {len(email_list)} 封邮件")

                # 获取所有邮件
                print("正在获取邮件...")
                emails = client.retrieve_all_emails()

                if emails:
                    print(f"成功获取了 {len(emails)} 封邮件")

                    # 保存邮件
                    saved_count = 0
                    db_saved_count = 0

                    # 获取数据库服务
                    db = self.main_cli.get_db()

                    for email in emails:
                        try:
                            # 确保目录存在
                            inbox_dir = os.path.join(EMAIL_STORAGE_DIR, "inbox")
                            os.makedirs(inbox_dir, exist_ok=True)

                            # 保存邮件文件
                            filepath = client.save_email_as_eml(email, inbox_dir)
                            if filepath:
                                saved_count += 1
                                print(f"已保存邮件: {os.path.basename(filepath)}")

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

                                    success = db.save_email(
                                        message_id=email.message_id,
                                        from_addr=from_addr,
                                        to_addrs=to_addrs,
                                        subject=email.subject or "",
                                        date=email.date,
                                        content=eml_content,
                                    )

                                    if success:
                                        db_saved_count += 1
                                        print(f"已保存到数据库: {email.message_id}")
                                    else:
                                        print(f"保存到数据库失败: {email.message_id}")

                                except Exception as db_err:
                                    logger.error(f"保存邮件到数据库失败: {db_err}")
                                    print(f"保存到数据库失败: {db_err}")

                        except Exception as e:
                            logger.error(f"保存邮件失败: {e}")
                            print(f"保存邮件失败: {e}")

                    print(f"\n成功保存了 {saved_count} 封邮件到: {inbox_dir}")
                    print(f"成功保存了 {db_saved_count} 封邮件到数据库")
                else:
                    print("未获取到任何邮件")

        except Exception as e:
            logger.error(f"接收邮件时出错: {e}")
            print(f"接收邮件时出错: {e}")

        input("\n按回车键继续...")

    def _receive_latest_emails(self):
        """接收最新邮件"""
        try:
            if not self._init_pop3_client():
                input("\n按回车键继续...")
                return

            # 获取要接收的邮件数量
            try:
                num = int(input("\n请输入要接收的最新邮件数量: "))
                if num <= 0:
                    print("数量必须大于0")
                    input("\n按回车键继续...")
                    return
            except ValueError:
                print("请输入有效的数字")
                input("\n按回车键继续...")
                return

            print("\n正在连接到邮箱...")

            # 使用上下文管理器
            with self.pop3_client as client:
                # 连接时会自动进行认证

                # 获取邮件列表
                email_list = client.list_emails()
                if not email_list:
                    print("邮箱中没有邮件")
                    input("\n按回车键继续...")
                    return

                # 获取最新的N封邮件
                total_emails = len(email_list)
                actual_num = min(num, total_emails)

                print(f"正在获取最新的 {actual_num} 封邮件...")
                emails = client.retrieve_all_emails(limit=actual_num)

                if emails:
                    print(f"成功获取了 {len(emails)} 封邮件")

                    # 保存邮件
                    saved_count = 0
                    for email in emails:
                        try:
                            # 确保目录存在
                            inbox_dir = os.path.join(EMAIL_STORAGE_DIR, "inbox")
                            os.makedirs(inbox_dir, exist_ok=True)

                            # 保存邮件
                            filepath = client.save_email_as_eml(email, inbox_dir)
                            if filepath:
                                saved_count += 1
                                print(f"已保存邮件: {email.subject}")
                        except Exception as e:
                            logger.error(f"保存邮件失败: {e}")
                            print(f"保存邮件失败: {e}")

                    print(f"\n成功保存了 {saved_count} 封邮件到: {inbox_dir}")
                else:
                    print("未获取到任何邮件")

        except Exception as e:
            logger.error(f"接收邮件时出错: {e}")
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
        self.main_cli.clear_screen()
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

    def _import_existing_emails(self):
        """导入现有的邮件文件到数据库"""
        self.main_cli.clear_screen()
        print("\n===== 导入现有邮件文件 =====")

        import glob

        # 查找所有.eml文件
        inbox_dir = os.path.join(EMAIL_STORAGE_DIR, "inbox")
        if not os.path.exists(inbox_dir):
            print(f"收件箱目录不存在: {inbox_dir}")
            input("\n按回车键继续...")
            return

        eml_files = glob.glob(os.path.join(inbox_dir, "*.eml"))

        if not eml_files:
            print(f"在 {inbox_dir} 中没有找到.eml文件")
            input("\n按回车键继续...")
            return

        print(f"找到 {len(eml_files)} 个邮件文件")

        # 询问是否继续
        confirm = input("\n是否导入这些邮件到数据库? (y/n): ").lower()
        if confirm != "y":
            print("已取消导入")
            input("\n按回车键继续...")
            return

        # 获取数据库服务
        db = self.main_cli.get_db()

        imported_count = 0
        skipped_count = 0
        failed_count = 0

        print("\n开始导入邮件...")

        for eml_file in eml_files:
            file_name = os.path.basename(eml_file)
            print(f"\n处理文件: {file_name}")

            try:
                # 读取邮件文件
                with open(eml_file, "r", encoding="utf-8") as f:
                    eml_content = f.read()

                # 解析邮件
                from common.email_format_handler import EmailFormatHandler

                try:
                    parsed_email = EmailFormatHandler.parse_mime_message(eml_content)

                    print(f"  Message-ID: {parsed_email.message_id}")
                    print(f"  Subject: {parsed_email.subject}")
                    print(f"  From: {parsed_email.from_addr}")

                    # 检查是否已存在
                    existing = db.get_email(parsed_email.message_id)
                    if existing:
                        print(f"  ⚠️ 邮件已存在，跳过")
                        skipped_count += 1
                        continue

                    # 保存新邮件
                    success = db.save_email(
                        message_id=parsed_email.message_id,
                        from_addr=str(parsed_email.from_addr),
                        to_addrs=[str(addr) for addr in parsed_email.to_addrs],
                        subject=parsed_email.subject or "",
                        date=parsed_email.date,
                        content=eml_content,
                    )

                    if success:
                        print(f"  ✓ 导入成功")
                        imported_count += 1
                    else:
                        print(f"  ✗ 导入失败")
                        failed_count += 1

                except Exception as parse_e:
                    print(f"  ✗ 解析失败: {parse_e}")
                    failed_count += 1

            except Exception as e:
                print(f"  ✗ 读取文件失败: {e}")
                failed_count += 1

        print(f"\n=== 导入完成 ===")
        print(f"成功导入: {imported_count} 封")
        print(f"跳过重复: {skipped_count} 封")
        print(f"导入失败: {failed_count} 封")

        input("\n按回车键继续...")
