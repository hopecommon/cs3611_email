#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账户诊断工具
帮助用户检查和修复账户配置问题
"""

import sys
import getpass
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli.account_manager import AccountManager
from cli.provider_manager import ProviderManager


def diagnose_account():
    """诊断账户配置"""
    print("🔧 邮箱账户诊断工具")
    print("=" * 60)

    account_manager = AccountManager()
    provider_manager = ProviderManager()

    # 列出所有账户
    accounts = account_manager.list_accounts()
    if not accounts:
        print("📭 暂无配置的账户")
        print("💡 请先运行 'python cli.py' 并在账户设置中添加邮箱账户")
        return

    print("📋 已配置的账户:")
    for i, account_name in enumerate(accounts, 1):
        account_info = account_manager.get_account(account_name)
        if account_info:
            print(f"{i}. {account_name}: {account_info['email']}")

    # 选择要诊断的账户
    while True:
        try:
            choice = input(f"\n请选择要诊断的账户 [1-{len(accounts)}]: ").strip()
            if not choice:
                return

            index = int(choice) - 1
            if 0 <= index < len(accounts):
                account_name = accounts[index]
                break
            else:
                print("❌ 选择超出范围")
        except ValueError:
            print("❌ 请输入有效数字")

    # 获取账户信息
    account_info = account_manager.get_account(account_name)
    if not account_info:
        print("❌ 无法获取账户信息")
        return

    print(f"\n🔍 诊断账户: {account_name}")
    print("-" * 40)

    # 基本信息检查
    email = account_info["email"]
    print(f"📧 邮箱地址: {email}")
    print(f"👤 显示名称: {account_info.get('display_name', '未设置')}")

    # 识别服务商
    provider_result = provider_manager.get_provider_by_email(email)
    if provider_result:
        provider_id, provider_config = provider_result
        print(f"📮 服务商: {provider_config['name']}")

        # 检查配置
        smtp_config = account_info.get("smtp", {})
        pop3_config = account_info.get("pop3", {})

        print(
            f"📤 SMTP服务器: {smtp_config.get('host', '未配置')}:{smtp_config.get('port', '未配置')}"
        )
        print(
            f"📥 POP3服务器: {pop3_config.get('host', '未配置')}:{pop3_config.get('port', '未配置')}"
        )

        # 密码检查
        password = account_info.get("password", "")
        print(f"🔐 密码长度: {len(password)} 字符")

        # 针对不同服务商的特殊检查
        if provider_id == "qq":
            print(f"\n⚠️  QQ邮箱特殊要求检查:")
            if len(password) != 16:
                print(f"   ❌ QQ邮箱授权码应该是16位字符，当前是{len(password)}位")
                print(f"   💡 请确认使用的是QQ邮箱授权码，不是QQ密码")
            else:
                print(f"   ✅ 密码长度符合QQ邮箱授权码要求")

            if smtp_config.get("host") != "smtp.qq.com":
                print(f"   ❌ SMTP服务器地址不正确")
            else:
                print(f"   ✅ SMTP服务器地址正确")

            if smtp_config.get("port") not in [465, 587]:
                print(f"   ❌ SMTP端口不正确，应该是465或587")
            else:
                print(f"   ✅ SMTP端口正确")

        elif provider_id == "gmail":
            print(f"\n⚠️  Gmail特殊要求检查:")
            if len(password.replace(" ", "")) != 16:
                print(f"   ❌ Gmail应用专用密码应该是16位字符")
                print(f"   💡 请确认使用的是Gmail应用专用密码")
            else:
                print(f"   ✅ 密码长度符合Gmail要求")

        elif provider_id in ["163", "126"]:
            print(f"\n⚠️  网易邮箱特殊要求检查:")
            print(f"   💡 请确认使用的是客户端授权密码，不是网页登录密码")

        # 提供修复选项
        print(f"\n🔧 修复选项:")
        print(f"1. 🔐 更新密码/授权码")
        print(f"2. ⚙️  重新配置服务器设置")
        print(f"3. 🧪 测试连接")
        print(f"0. 🔙 返回")

        choice = input("\n请选择操作 [0-3]: ").strip()

        if choice == "1":
            update_password(account_manager, account_name, provider_id)
        elif choice == "2":
            reconfigure_servers(
                account_manager, account_name, provider_manager, provider_id
            )
        elif choice == "3":
            test_connection(account_info)

    else:
        print(f"❌ 无法识别邮件服务商")


def update_password(account_manager, account_name, provider_id):
    """更新密码"""
    print(f"\n🔐 更新密码/授权码")
    print("-" * 30)

    if provider_id == "qq":
        print("💡 QQ邮箱授权码获取步骤:")
        print("   1. 登录QQ邮箱网页版")
        print("   2. 进入设置 -> 账户")
        print("   3. 开启SMTP/POP3/IMAP服务")
        print("   4. 生成授权码（16位字符）")
    elif provider_id == "gmail":
        print("💡 Gmail应用专用密码获取步骤:")
        print("   1. 登录Google账户")
        print("   2. 开启两步验证")
        print("   3. 生成应用专用密码")
    elif provider_id in ["163", "126"]:
        print("💡 网易邮箱授权码获取步骤:")
        print("   1. 登录邮箱网页版")
        print("   2. 进入设置 -> POP3/SMTP/IMAP")
        print("   3. 开启服务并生成授权码")

    new_password = getpass.getpass("\n请输入新的密码/授权码: ")
    if not new_password:
        print("❌ 密码不能为空")
        return

    # 基本格式验证
    if provider_id == "qq" and len(new_password) != 16:
        confirm = (
            input(
                f"⚠️  QQ邮箱授权码通常是16位，您输入的是{len(new_password)}位，确认继续? (y/N): "
            )
            .strip()
            .lower()
        )
        if confirm != "y":
            return

    # 更新密码
    account_info = account_manager.get_account(account_name)
    smtp_config = account_info["smtp"].copy()
    pop3_config = account_info["pop3"].copy()
    smtp_config["password"] = new_password
    pop3_config["password"] = new_password

    success = account_manager.update_account(
        account_name, password=new_password, smtp=smtp_config, pop3=pop3_config
    )

    if success:
        print("✅ 密码更新成功")
    else:
        print("❌ 密码更新失败")


def reconfigure_servers(account_manager, account_name, provider_manager, provider_id):
    """重新配置服务器设置"""
    print(f"\n⚙️  重新配置服务器设置")
    print("-" * 30)

    # 获取推荐配置
    smtp_config = provider_manager.get_smtp_config(provider_id)
    pop3_config = provider_manager.get_pop3_config(provider_id)

    if smtp_config and pop3_config:
        account_info = account_manager.get_account(account_name)

        # 保留用户名和密码
        smtp_config["username"] = account_info["email"]
        smtp_config["password"] = account_info["password"]
        pop3_config["username"] = account_info["email"]
        pop3_config["password"] = account_info["password"]

        success = account_manager.update_account(
            account_name, smtp=smtp_config, pop3=pop3_config
        )

        if success:
            print("✅ 服务器配置更新成功")
            print(f"📤 SMTP: {smtp_config['host']}:{smtp_config['port']}")
            print(f"📥 POP3: {pop3_config['host']}:{pop3_config['port']}")
        else:
            print("❌ 服务器配置更新失败")
    else:
        print("❌ 无法获取推荐配置")


def test_connection(account_info):
    """测试连接"""
    print(f"\n🧪 测试连接")
    print("-" * 20)
    print("⚠️  连接测试功能正在开发中...")
    print("💡 您可以尝试发送一封测试邮件来验证配置")


if __name__ == "__main__":
    try:
        diagnose_account()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 程序运行时出错: {e}")
        import traceback

        traceback.print_exc()
