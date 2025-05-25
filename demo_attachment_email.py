#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件附件功能演示脚本
展示发送带附件的邮件和接收端的完整解析
"""

import sys
import os
import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.utils import setup_logging
from common.models import Email, EmailAddress, Attachment, EmailStatus
from client.smtp_client import SMTPClient
from client.pop3_client_refactored import POP3ClientRefactored as POP3Client
from cli.account_manager import AccountManager
from cli.provider_manager import ProviderManager
from client.mime_handler import MIMEHandler

# 设置日志
logger = setup_logging("demo_attachment")


def create_test_files():
    """创建测试附件文件"""
    test_dir = Path("test_attachments")
    test_dir.mkdir(exist_ok=True)

    # 创建文本文件
    text_file = test_dir / "测试文档.txt"
    with open(text_file, "w", encoding="utf-8") as f:
        f.write("这是一个测试文本文件。\n")
        f.write("用于演示邮件附件功能。\n")
        f.write(f"创建时间: {datetime.datetime.now()}\n")

    # 创建CSV文件
    csv_file = test_dir / "数据表.csv"
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("姓名,年龄,城市\n")
        f.write("张三,25,北京\n")
        f.write("李四,30,上海\n")
        f.write("王五,28,广州\n")

    # 创建JSON文件
    json_file = test_dir / "配置.json"
    with open(json_file, "w", encoding="utf-8") as f:
        f.write("{\n")
        f.write('  "name": "邮件客户端",\n')
        f.write('  "version": "1.0.0",\n')
        f.write('  "features": ["SMTP", "POP3", "附件支持"]\n')
        f.write("}\n")

    return [str(text_file), str(csv_file), str(json_file)]


def demonstrate_send_with_attachments():
    """演示发送带附件的邮件"""
    print("🚀 邮件附件功能演示")
    print("=" * 60)

    # 检查账户配置
    account_manager = AccountManager()
    accounts = account_manager.list_accounts()

    if not accounts:
        print("❌ 未找到配置的账户")
        print("💡 请先运行 'python account_config_helper.py' 配置邮箱账户")
        return False

    # 使用第一个账户
    account_name = accounts[0]
    account_info = account_manager.get_account(account_name)

    print(f"📧 使用账户: {account_info['display_name']} ({account_info['email']})")

    # 创建测试附件
    print(f"\n📎 创建测试附件...")
    test_files = create_test_files()
    for file_path in test_files:
        print(f"  ✅ 创建: {file_path}")

    # 准备附件
    attachments = []
    for file_path in test_files:
        try:
            attachment = MIMEHandler.encode_attachment(file_path)
            attachments.append(attachment)
            print(f"  📎 编码附件: {attachment.filename} ({attachment.size} 字节)")
        except Exception as e:
            print(f"  ❌ 编码附件失败: {file_path} - {e}")

    # 获取收件人
    recipient_email = input(f"\n📧 请输入收件人邮箱地址: ").strip()
    if not recipient_email:
        print("❌ 收件人不能为空")
        return False

    # 创建邮件
    email = Email(
        message_id=f"<demo-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}@{account_info['email'].split('@')[1]}>",
        subject="📎 邮件附件功能演示",
        from_addr=EmailAddress(
            name=account_info["display_name"], address=account_info["email"]
        ),
        to_addrs=[EmailAddress(name="", address=recipient_email)],
        text_content=f"""这是一封演示邮件附件功能的测试邮件。

📎 本邮件包含以下附件:
1. 测试文档.txt - 文本文件
2. 数据表.csv - CSV数据文件  
3. 配置.json - JSON配置文件

请查收并测试附件的接收和解析功能。

发送时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
发送账户: {account_info['email']}

祝好！
邮件客户端演示系统
""",
        attachments=attachments,
        status=EmailStatus.DRAFT,
    )

    # 显示邮件摘要
    print(f"\n📋 邮件摘要:")
    print(f"   📤 发件人: {email.from_addr}")
    print(f"   📧 收件人: {recipient_email}")
    print(f"   📋 主题: {email.subject}")
    print(f"   📎 附件数量: {len(email.attachments)}")
    for i, att in enumerate(email.attachments, 1):
        print(f"      {i}. {att.filename} ({att.content_type}, {att.size} 字节)")

    # 确认发送
    confirm = input(f"\n❓ 确认发送演示邮件? (Y/n): ").strip().lower()
    if confirm in ["n", "no"]:
        print("❌ 发送已取消")
        return False

    # 发送邮件
    try:
        print(f"\n🚀 正在发送邮件...")

        # 创建SMTP客户端
        smtp_config = account_info["smtp"]
        smtp_client = SMTPClient(
            host=smtp_config["host"],
            port=smtp_config["port"],
            use_ssl=smtp_config.get("use_ssl", True),
            username=smtp_config["username"],
            password=smtp_config["password"],
            auth_method=smtp_config.get("auth_method", "AUTO"),
        )

        # 发送邮件
        result = smtp_client.send_email(email)

        if result:
            print("✅ 邮件发送成功！")
            print(f"💡 请检查收件箱: {recipient_email}")
            return True
        else:
            print("❌ 邮件发送失败")
            return False

    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        print(f"❌ 发送邮件失败: {e}")
        return False


def demonstrate_receive_with_attachments():
    """演示接收带附件的邮件"""
    print(f"\n📥 演示接收邮件和附件解析")
    print("=" * 60)

    # 检查账户配置
    account_manager = AccountManager()
    accounts = account_manager.list_accounts()

    if not accounts:
        print("❌ 未找到配置的账户")
        return False

    # 选择账户
    if len(accounts) == 1:
        account_name = accounts[0]
    else:
        print("📋 选择接收账户:")
        for i, name in enumerate(accounts, 1):
            account_info = account_manager.get_account(name)
            print(f"  {i}. {name}: {account_info['email']}")

        try:
            choice = int(input(f"\n请选择账户 [1-{len(accounts)}]: ")) - 1
            account_name = accounts[choice]
        except (ValueError, IndexError):
            print("❌ 无效选择")
            return False

    account_info = account_manager.get_account(account_name)
    print(f"📧 使用账户: {account_info['display_name']} ({account_info['email']})")

    try:
        # 创建POP3客户端
        pop3_config = account_info["pop3"]
        pop3_client = POP3Client(
            host=pop3_config["host"],
            port=pop3_config["port"],
            use_ssl=pop3_config.get("use_ssl", True),
            username=pop3_config["username"],
            password=pop3_config["password"],
            auth_method=pop3_config.get("auth_method", "AUTO"),
        )

        # 连接到服务器
        print(f"🔄 正在连接到 {pop3_config['host']}:{pop3_config['port']}...")
        pop3_client.connect()

        # 获取邮件列表
        print("📋 获取邮件列表...")
        email_list = pop3_client.list_emails()

        if not email_list:
            print("📭 邮箱中没有邮件")
            return False

        print(f"📊 找到 {len(email_list)} 封邮件")

        # 获取最新的几封邮件
        latest_emails = email_list[-5:] if len(email_list) >= 5 else email_list

        print(f"\n📧 处理最新的 {len(latest_emails)} 封邮件:")

        for i, (msg_num, msg_size) in enumerate(latest_emails):
            print(f"\n--- 邮件 {i+1} (编号: {msg_num}) ---")

            # 获取邮件
            email = pop3_client.retrieve_email(msg_num, delete=False)

            if email:
                print(f"📋 主题: {email.subject}")
                print(f"📤 发件人: {email.from_addr}")
                print(f"📅 日期: {email.date}")

                # 显示附件信息
                if email.attachments:
                    print(f"\n📎 附件信息 ({len(email.attachments)} 个):")

                    # 创建附件保存目录
                    attachments_dir = Path("received_attachments")
                    attachments_dir.mkdir(exist_ok=True)

                    for j, attachment in enumerate(email.attachments, 1):
                        print(f"  {j}. 📄 {attachment.filename}")
                        print(f"     📊 类型: {attachment.content_type}")
                        print(f"     📏 大小: {attachment.size} 字节")

                        # 保存附件
                        try:
                            saved_path = MIMEHandler.decode_attachment(
                                attachment, str(attachments_dir)
                            )
                            print(f"     💾 已保存: {saved_path}")

                            # 如果是文本文件，显示内容预览
                            if attachment.content_type.startswith("text/"):
                                try:
                                    with open(saved_path, "r", encoding="utf-8") as f:
                                        content = f.read(200)
                                        if len(content) == 200:
                                            content += "..."
                                        print(f"     👀 内容预览: {content}")
                                except Exception as e:
                                    print(f"     ⚠️  读取预览失败: {e}")

                        except Exception as e:
                            print(f"     ❌ 保存失败: {e}")
                else:
                    print("📎 无附件")

                # 显示邮件内容摘要
                if email.text_content:
                    content_preview = email.text_content[:200]
                    if len(email.text_content) > 200:
                        content_preview += "..."
                    print(f"\n📝 内容预览:\n{content_preview}")
            else:
                print(f"❌ 无法获取邮件 {msg_num}")

        # 断开连接
        pop3_client.disconnect()
        print(f"\n✅ 邮件接收和附件解析演示完成")
        return True

    except Exception as e:
        logger.error(f"接收邮件失败: {e}")
        print(f"❌ 接收邮件失败: {e}")
        return False


def main():
    """主函数"""
    print("🎯 邮件附件功能完整演示")
    print("=" * 60)
    print("本演示将展示:")
    print("1. 📤 发送带附件的邮件")
    print("2. 📥 接收邮件并完整解析附件")
    print("3. 💾 附件的保存和内容预览")

    choice = input(f"\n请选择演示内容 [1=发送, 2=接收, 3=全部]: ").strip()

    if choice in ["1", "3"]:
        print(f"\n{'='*60}")
        print("📤 第一部分: 发送带附件的邮件")
        print("=" * 60)

        if demonstrate_send_with_attachments():
            print("✅ 发送演示完成")
        else:
            print("❌ 发送演示失败")

    if choice in ["2", "3"]:
        print(f"\n{'='*60}")
        print("📥 第二部分: 接收邮件和附件解析")
        print("=" * 60)

        if choice == "3":
            input("\n⏳ 请等待邮件送达后按回车键继续...")

        if demonstrate_receive_with_attachments():
            print("✅ 接收演示完成")
        else:
            print("❌ 接收演示失败")

    print(f"\n🎉 演示结束")
    print("💡 提示:")
    print("   • 测试附件保存在 'test_attachments' 目录")
    print("   • 接收的附件保存在 'received_attachments' 目录")
    print("   • 可以对比发送和接收的附件内容")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 程序运行时出错: {e}")
        import traceback

        traceback.print_exc()
