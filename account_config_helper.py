#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账户配置助手
支持可见密码输入和连接测试的账户管理工具
"""

import sys
import getpass
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli.account_manager import AccountManager
from cli.provider_manager import ProviderManager


def main_menu():
    """主菜单"""
    account_manager = AccountManager()
    provider_manager = ProviderManager()

    while True:
        print("\n" + "=" * 60)
        print("🔧 邮箱账户配置助手")
        print("=" * 60)
        print("1. 📋 查看现有账户")
        print("2. 🔐 更新账户密码（可见输入）")
        print("3. 🧪 测试SMTP连接")
        print("4. 🧪 测试POP3连接")
        print("5. ⚙️  重新配置服务器设置")
        print("6. 📝 添加新账户（可见输入）")
        print("0. 🔙 退出")
        print("-" * 60)

        choice = input("\n请选择操作 [0-6]: ").strip()

        if choice == "1":
            list_accounts(account_manager, provider_manager)
        elif choice == "2":
            update_password_visible(account_manager, provider_manager)
        elif choice == "3":
            test_smtp_connection(account_manager)
        elif choice == "4":
            test_pop3_connection(account_manager)
        elif choice == "5":
            reconfigure_servers(account_manager, provider_manager)
        elif choice == "6":
            add_account_visible(account_manager, provider_manager)
        elif choice == "0":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择")


def list_accounts(account_manager, provider_manager):
    """列出所有账户"""
    print("\n" + "=" * 60)
    print("📋 账户列表")
    print("=" * 60)

    accounts = account_manager.list_accounts()
    if not accounts:
        print("📭 暂无配置的账户")
        return

    for i, account_name in enumerate(accounts, 1):
        account_info = account_manager.get_account(account_name)
        if account_info:
            email = account_info["email"]
            print(f"\n{i}. 账户名: {account_name}")
            print(f"   📧 邮箱: {email}")
            print(f"   👤 显示名: {account_info.get('display_name', '未设置')}")

            # 识别服务商
            provider_result = provider_manager.get_provider_by_email(email)
            if provider_result:
                provider_id, provider_config = provider_result
                print(f"   📮 服务商: {provider_config['name']}")

            # 显示服务器配置
            smtp_config = account_info.get("smtp", {})
            pop3_config = account_info.get("pop3", {})
            print(
                f"   📤 SMTP: {smtp_config.get('host', '未配置')}:{smtp_config.get('port', '未配置')}"
            )
            print(
                f"   📥 POP3: {pop3_config.get('host', '未配置')}:{pop3_config.get('port', '未配置')}"
            )

            # 密码长度（不显示实际密码）
            password_len = len(account_info.get("password", ""))
            print(f"   🔐 密码长度: {password_len} 字符")


def update_password_visible(account_manager, provider_manager):
    """更新密码（可见输入）"""
    print("\n" + "=" * 60)
    print("🔐 更新账户密码")
    print("=" * 60)

    accounts = account_manager.list_accounts()
    if not accounts:
        print("📭 暂无配置的账户")
        return

    # 选择账户
    print("📋 选择要更新的账户:")
    for i, account_name in enumerate(accounts, 1):
        account_info = account_manager.get_account(account_name)
        print(f"{i}. {account_name}: {account_info['email']}")

    try:
        choice = int(input(f"\n请选择账户 [1-{len(accounts)}]: ")) - 1
        if choice < 0 or choice >= len(accounts):
            print("❌ 选择超出范围")
            return

        account_name = accounts[choice]
        account_info = account_manager.get_account(account_name)
        email = account_info["email"]

        # 识别服务商并显示说明
        provider_result = provider_manager.get_provider_by_email(email)
        if provider_result:
            provider_id, provider_config = provider_result
            print(f"\n📮 服务商: {provider_config['name']}")

            if provider_id == "qq":
                print("\n💡 QQ邮箱授权码获取步骤:")
                print("   1. 登录 https://mail.qq.com")
                print(
                    "   2. 设置 -> 账户 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
                )
                print("   3. 开启 SMTP 服务")
                print("   4. 生成授权码（16位字符）")
                print("   ⚠️  必须使用授权码，不能使用QQ密码！")
            elif provider_id == "gmail":
                print("\n💡 Gmail应用专用密码获取步骤:")
                print("   1. 登录 Google 账户")
                print("   2. 开启两步验证")
                print("   3. 生成应用专用密码")
            elif provider_id in ["163", "126"]:
                print("\n💡 网易邮箱授权码获取步骤:")
                print("   1. 登录邮箱网页版")
                print("   2. 设置 -> POP3/SMTP/IMAP")
                print("   3. 开启服务并生成授权码")

        print(f"\n🔐 为账户 '{account_name}' 输入新密码/授权码:")
        print("💡 提示: 输入将可见，请确保周围环境安全")

        # 提供两种输入方式
        input_mode = input("\n选择输入方式 [1=可见输入, 2=隐藏输入]: ").strip()

        if input_mode == "1":
            new_password = input("请输入密码/授权码: ").strip()
        else:
            new_password = getpass.getpass("请输入密码/授权码: ")

        if not new_password:
            print("❌ 密码不能为空")
            return

        print(f"\n📊 您输入的密码长度: {len(new_password)} 字符")

        # 格式验证
        if provider_result:
            provider_id, _ = provider_result
            if provider_id == "qq" and len(new_password) != 16:
                print(f"⚠️  QQ邮箱授权码通常是16位字符")
            elif provider_id == "gmail" and len(new_password.replace(" ", "")) != 16:
                print(f"⚠️  Gmail应用专用密码通常是16位字符")

        confirm = input("\n确认更新密码? (Y/n): ").strip().lower()
        if confirm in ["n", "no"]:
            print("❌ 操作已取消")
            return

        # 更新密码
        smtp_config = account_info["smtp"].copy()
        pop3_config = account_info["pop3"].copy()
        smtp_config["password"] = new_password
        pop3_config["password"] = new_password

        success = account_manager.update_account(
            account_name, password=new_password, smtp=smtp_config, pop3=pop3_config
        )

        if success:
            print("✅ 密码更新成功")
            print("💡 建议立即测试连接以验证配置")
        else:
            print("❌ 密码更新失败")

    except ValueError:
        print("❌ 请输入有效数字")
    except Exception as e:
        print(f"❌ 更新失败: {e}")


def test_smtp_connection(account_manager):
    """测试SMTP连接"""
    print("\n" + "=" * 60)
    print("🧪 测试SMTP连接")
    print("=" * 60)

    accounts = account_manager.list_accounts()
    if not accounts:
        print("📭 暂无配置的账户")
        return

    # 选择账户
    print("📋 选择要测试的账户:")
    for i, account_name in enumerate(accounts, 1):
        account_info = account_manager.get_account(account_name)
        print(f"{i}. {account_name}: {account_info['email']}")

    try:
        choice = int(input(f"\n请选择账户 [1-{len(accounts)}]: ")) - 1
        if choice < 0 or choice >= len(accounts):
            print("❌ 选择超出范围")
            return

        account_name = accounts[choice]
        account_info = account_manager.get_account(account_name)
        smtp_config = account_info.get("smtp", {})

        print(f"\n🔄 正在测试SMTP连接...")
        print(f"📤 服务器: {smtp_config.get('host')}:{smtp_config.get('port')}")
        print(f"🔐 用户名: {smtp_config.get('username')}")
        print(f"🔒 SSL: {smtp_config.get('use_ssl', True)}")

        # 实际测试连接
        success = _test_smtp_connection_real(smtp_config)

        if success:
            print("✅ SMTP连接测试成功！")
            print("💡 您的邮箱配置正确，可以发送邮件")
        else:
            print("❌ SMTP连接测试失败")
            print("💡 请检查:")
            print("   • 密码/授权码是否正确")
            print("   • 是否已开启SMTP服务")
            print("   • 网络连接是否正常")

    except ValueError:
        print("❌ 请输入有效数字")
    except Exception as e:
        print(f"❌ 测试失败: {e}")


def _test_smtp_connection_real(smtp_config):
    """实际测试SMTP连接"""
    try:
        import smtplib
        import ssl

        host = smtp_config.get("host")
        port = smtp_config.get("port")
        username = smtp_config.get("username")
        password = smtp_config.get("password")
        use_ssl = smtp_config.get("use_ssl", True)

        if not all([host, port, username, password]):
            print("❌ SMTP配置不完整")
            return False

        print(f"🔗 连接到 {host}:{port}...")

        if use_ssl and port == 465:
            # SSL连接
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context)
        else:
            # TLS连接
            server = smtplib.SMTP(host, port)
            if use_ssl:
                server.starttls()

        print("🔐 正在认证...")
        server.login(username, password)

        print("✅ 认证成功")
        server.quit()
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 认证失败: {e}")
        print("💡 请检查用户名和密码/授权码")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"❌ 连接失败: {e}")
        print("💡 请检查服务器地址和端口")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


def test_pop3_connection(account_manager):
    """测试POP3连接"""
    print("\n" + "=" * 60)
    print("🧪 测试POP3连接")
    print("=" * 60)

    accounts = account_manager.list_accounts()
    if not accounts:
        print("📭 暂无配置的账户")
        return

    # 选择账户
    print("📋 选择要测试的账户:")
    for i, account_name in enumerate(accounts, 1):
        account_info = account_manager.get_account(account_name)
        print(f"{i}. {account_name}: {account_info['email']}")

    try:
        choice = int(input(f"\n请选择账户 [1-{len(accounts)}]: ")) - 1
        if choice < 0 or choice >= len(accounts):
            print("❌ 选择超出范围")
            return

        account_name = accounts[choice]
        account_info = account_manager.get_account(account_name)
        pop3_config = account_info.get("pop3", {})

        print(f"\n🔄 正在测试POP3连接...")
        print(f"📥 服务器: {pop3_config.get('host')}:{pop3_config.get('port')}")
        print(f"🔐 用户名: {pop3_config.get('username')}")
        print(f"🔒 SSL: {pop3_config.get('use_ssl', True)}")

        # 实际测试连接
        success = _test_pop3_connection_real(pop3_config)

        if success:
            print("✅ POP3连接测试成功！")
            print("💡 您的邮箱配置正确，可以接收邮件")
        else:
            print("❌ POP3连接测试失败")
            print("💡 请检查:")
            print("   • 密码/授权码是否正确")
            print("   • 是否已开启POP3服务")
            print("   • 网络连接是否正常")

    except ValueError:
        print("❌ 请输入有效数字")
    except Exception as e:
        print(f"❌ 测试失败: {e}")


def _test_pop3_connection_real(pop3_config):
    """实际测试POP3连接"""
    try:
        import poplib
        import ssl

        host = pop3_config.get("host")
        port = pop3_config.get("port")
        username = pop3_config.get("username")
        password = pop3_config.get("password")
        use_ssl = pop3_config.get("use_ssl", True)

        if not all([host, port, username, password]):
            print("❌ POP3配置不完整")
            return False

        print(f"🔗 连接到 {host}:{port}...")

        if use_ssl:
            # SSL连接
            context = ssl.create_default_context()
            server = poplib.POP3_SSL(host, port, context=context)
        else:
            server = poplib.POP3(host, port)

        print("🔐 正在认证...")
        server.user(username)
        server.pass_(password)

        # 获取邮件统计信息
        stat = server.stat()
        print(f"✅ 认证成功")
        print(f"📊 邮箱统计: {stat[0]} 封邮件")

        server.quit()
        return True

    except poplib.error_proto as e:
        print(f"❌ 认证失败: {e}")
        print("💡 请检查用户名和密码/授权码")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


def reconfigure_servers(account_manager, provider_manager):
    """重新配置服务器设置"""
    print("\n" + "=" * 60)
    print("⚙️  重新配置服务器设置")
    print("=" * 60)

    accounts = account_manager.list_accounts()
    if not accounts:
        print("📭 暂无配置的账户")
        return

    # 选择账户
    print("📋 选择要重新配置的账户:")
    for i, account_name in enumerate(accounts, 1):
        account_info = account_manager.get_account(account_name)
        print(f"{i}. {account_name}: {account_info['email']}")

    try:
        choice = int(input(f"\n请选择账户 [1-{len(accounts)}]: ")) - 1
        if choice < 0 or choice >= len(accounts):
            print("❌ 选择超出范围")
            return

        account_name = accounts[choice]
        account_info = account_manager.get_account(account_name)
        email = account_info["email"]

        # 识别服务商
        provider_result = provider_manager.get_provider_by_email(email)
        if not provider_result:
            print("❌ 无法识别邮件服务商")
            return

        provider_id, provider_config = provider_result
        print(f"\n📮 服务商: {provider_config['name']}")

        # 获取推荐配置
        smtp_config = provider_manager.get_smtp_config(provider_id)
        pop3_config = provider_manager.get_pop3_config(provider_id)

        if smtp_config and pop3_config:
            # 保留用户名和密码
            smtp_config["username"] = email
            smtp_config["password"] = account_info["password"]
            pop3_config["username"] = email
            pop3_config["password"] = account_info["password"]

            print(f"\n📤 新SMTP配置: {smtp_config['host']}:{smtp_config['port']}")
            print(f"📥 新POP3配置: {pop3_config['host']}:{pop3_config['port']}")

            confirm = input("\n确认更新服务器配置? (Y/n): ").strip().lower()
            if confirm in ["n", "no"]:
                print("❌ 操作已取消")
                return

            success = account_manager.update_account(
                account_name, smtp=smtp_config, pop3=pop3_config
            )

            if success:
                print("✅ 服务器配置更新成功")
            else:
                print("❌ 服务器配置更新失败")
        else:
            print("❌ 无法获取推荐配置")

    except ValueError:
        print("❌ 请输入有效数字")
    except Exception as e:
        print(f"❌ 配置失败: {e}")


def add_account_visible(account_manager, provider_manager):
    """添加新账户（可见输入）"""
    print("\n" + "=" * 60)
    print("📝 添加新账户")
    print("=" * 60)
    print("💡 此功能提供可见密码输入，请确保周围环境安全")

    # 输入邮箱地址
    email = input("\n📧 请输入邮箱地址: ").strip()
    if not email or not provider_manager.validate_email_format(email):
        print("❌ 邮箱地址格式不正确")
        return

    # 检查是否已存在
    existing_accounts = account_manager.list_accounts()
    if any(
        account_manager.get_account(name)["email"] == email
        for name in existing_accounts
    ):
        print("❌ 该邮箱账户已存在")
        return

    # 识别服务商
    provider_result = provider_manager.get_provider_by_email(email)
    if provider_result:
        provider_id, provider_config = provider_result
        print(f"\n✅ 自动识别服务商: {provider_config['name']}")

        # 显示设置说明
        if provider_id == "qq":
            print("\n💡 QQ邮箱设置说明:")
            print("   1. 登录 https://mail.qq.com")
            print("   2. 设置 -> 账户 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务")
            print("   3. 开启 SMTP 和 POP3 服务")
            print("   4. 生成授权码（16位字符）")
            print("   ⚠️  必须使用授权码，不能使用QQ密码！")
    else:
        print("⚠️  未能识别邮件服务商")
        provider_id = "custom"

    # 输入账户信息
    account_name = (
        input(f"\n账户名称 (默认: {email.split('@')[0]}): ").strip()
        or email.split("@")[0]
    )
    display_name = input(f"显示名称 (默认: {account_name}): ").strip() or account_name

    # 输入密码
    input_mode = input("\n选择密码输入方式 [1=可见输入, 2=隐藏输入]: ").strip()

    if input_mode == "1":
        password = input("请输入密码/授权码: ").strip()
    else:
        password = getpass.getpass("请输入密码/授权码: ")

    if not password:
        print("❌ 密码不能为空")
        return

    print(f"\n📊 密码长度: {len(password)} 字符")

    # 配置服务器设置
    if provider_id == "custom":
        print("❌ 自定义服务器配置功能暂未在此工具中实现")
        print("💡 请使用主程序的账户设置功能")
        return
    else:
        smtp_config = provider_manager.get_smtp_config(provider_id)
        pop3_config = provider_manager.get_pop3_config(provider_id)

        smtp_config["username"] = email
        smtp_config["password"] = password
        pop3_config["username"] = email
        pop3_config["password"] = password

    # 保存账户
    notes = provider_manager.get_provider_notes(provider_id)
    success = account_manager.add_account(
        account_name=account_name,
        email=email,
        password=password,
        smtp_config=smtp_config,
        pop3_config=pop3_config,
        display_name=display_name,
        notes=notes,
    )

    if success:
        print(f"\n✅ 账户 '{account_name}' 添加成功！")
        print("💡 建议立即测试连接以验证配置")
    else:
        print("\n❌ 账户添加失败")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 程序运行时出错: {e}")
        import traceback

        traceback.print_exc()
