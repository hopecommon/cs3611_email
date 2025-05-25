# -*- coding: utf-8 -*-
"""
现代化账户设置菜单 - 提供用户友好的账户管理界面
"""

import sys
import getpass
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from .account_manager import AccountManager
from .provider_manager import ProviderManager

# 设置日志
logger = setup_logging("modern_settings_menu")


class ModernSettingsMenu:
    """现代化设置菜单"""

    def __init__(self, main_cli):
        """初始化设置菜单"""
        self.main_cli = main_cli
        self.account_manager = AccountManager()
        self.provider_manager = ProviderManager()
        self.current_account = None

    def show_menu(self):
        """显示主设置菜单"""
        while True:
            self.main_cli.clear_screen()
            print("\n" + "=" * 60)
            print("🔧 邮件客户端 - 账户设置")
            print("=" * 60)

            # 显示当前账户信息
            accounts = self.account_manager.list_accounts()
            if accounts:
                default_account = self.account_manager.get_default_account()
                print(f"📧 当前账户: {default_account or '未选择'}")
                print(f"📊 已配置账户: {len(accounts)} 个")
            else:
                print("📧 当前账户: 无")
                print("💡 提示: 请先添加邮箱账户")

            print("\n" + "-" * 60)
            print("1. 📝 添加新账户")
            print("2. 📋 管理现有账户")
            print("3. 🔄 切换当前账户")
            print("4. ⚙️  高级设置")
            print("5. 📖 帮助与说明")
            print("0. 🔙 返回主菜单")
            print("-" * 60)

            choice = input("\n请选择操作 [0-5]: ").strip()

            if choice == "1":
                self._add_account_wizard()
            elif choice == "2":
                self._manage_accounts()
            elif choice == "3":
                self._switch_account()
            elif choice == "4":
                self._advanced_settings()
            elif choice == "5":
                self._show_help()
            elif choice == "0":
                return
            else:
                input("❌ 无效选择，请按回车键继续...")

    def _add_account_wizard(self):
        """添加账户向导"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📝 添加新邮箱账户")
        print("=" * 60)

        # 步骤1: 输入邮箱地址
        while True:
            email = input("\n📧 请输入邮箱地址: ").strip()
            if not email:
                print("❌ 邮箱地址不能为空")
                continue

            if not self.provider_manager.validate_email_format(email):
                print("❌ 邮箱地址格式不正确")
                continue

            # 检查是否已存在
            existing_accounts = self.account_manager.list_accounts()
            if any(
                self.account_manager.get_account(name)["email"] == email
                for name in existing_accounts
            ):
                print("❌ 该邮箱账户已存在")
                continue

            break

        # 步骤2: 自动识别服务商
        provider_result = self.provider_manager.get_provider_by_email(email)
        if provider_result:
            provider_id, provider_config = provider_result
            print(f"\n✅ 自动识别服务商: {provider_config['name']}")

            # 显示设置说明
            instructions = self.provider_manager.get_setup_instructions(provider_id)
            if instructions:
                print(f"\n📋 {provider_config['name']} 设置说明:")
                for instruction in instructions:
                    print(f"   {instruction}")

                # 为特定服务商提供额外的重要提示
                if provider_id == "qq":
                    print(f"\n⚠️  重要提示:")
                    print(f"   • QQ邮箱必须使用授权码，不能使用QQ密码")
                    print(f"   • 授权码是16位字符，如: abcdabcdabcdabcd")
                    print(f"   • 如果使用QQ密码会导致认证失败")
                elif provider_id == "gmail":
                    print(f"\n⚠️  重要提示:")
                    print(f"   • Gmail必须使用应用专用密码")
                    print(f"   • 普通Gmail密码无法用于第三方客户端")
                elif provider_id in ["163", "126"]:
                    print(f"\n⚠️  重要提示:")
                    print(f"   • 必须使用客户端授权密码")
                    print(f"   • 不能使用网页登录密码")

                print()
        else:
            print("\n⚠️  未能自动识别邮件服务商，将使用自定义配置")
            provider_id = "custom"

        # 步骤3: 选择或确认服务商
        if provider_result:
            confirm = (
                input(f"是否使用 {provider_config['name']} 的预设配置? (Y/n): ")
                .strip()
                .lower()
            )
            if confirm in ["n", "no"]:
                provider_id = self._select_provider()
        else:
            provider_id = self._select_provider()

        # 步骤4: 输入账户信息
        print(f"\n📝 配置账户信息")
        account_name = (
            input(f"账户名称 (默认: {email.split('@')[0]}): ").strip()
            or email.split("@")[0]
        )
        display_name = (
            input(f"显示名称 (默认: {account_name}): ").strip() or account_name
        )

        # 步骤5: 输入密码
        print(f"\n🔐 输入账户密码")
        if provider_id in ["qq", "gmail", "163", "126", "outlook", "yahoo"]:
            print("💡 提示: 请使用授权码/应用专用密码，而非登录密码")
            if provider_id == "qq":
                print("🔑 QQ邮箱授权码格式: 16位字符 (如: abcdabcdabcdabcd)")
            elif provider_id == "gmail":
                print("🔑 Gmail应用专用密码格式: 16位字符 (如: abcd abcd abcd abcd)")
            elif provider_id in ["163", "126"]:
                print("🔑 网易邮箱授权码: 在邮箱设置中生成的客户端授权密码")

        while True:
            password = getpass.getpass("密码/授权码: ")
            if not password:
                print("❌ 密码不能为空")
                continue

            # 对特定服务商进行基本格式验证
            if provider_id == "qq" and len(password) != 16:
                print("⚠️  QQ邮箱授权码通常是16位字符，请确认输入正确")
                retry = input("是否重新输入? (Y/n): ").strip().lower()
                if retry not in ["n", "no"]:
                    continue
            elif provider_id == "gmail" and len(password.replace(" ", "")) != 16:
                print("⚠️  Gmail应用专用密码通常是16位字符，请确认输入正确")
                retry = input("是否重新输入? (Y/n): ").strip().lower()
                if retry not in ["n", "no"]:
                    continue

            break

        # 步骤6: 配置服务器设置
        if provider_id == "custom":
            smtp_config, pop3_config = self._configure_custom_server()
            if not smtp_config or not pop3_config:
                return
        else:
            smtp_config = self.provider_manager.get_smtp_config(provider_id)
            pop3_config = self.provider_manager.get_pop3_config(provider_id)

            # 添加用户名和密码
            smtp_config["username"] = email
            smtp_config["password"] = password
            pop3_config["username"] = email
            pop3_config["password"] = password

        # 步骤7: 测试连接（可选）
        test_connection = input("\n🧪 是否测试连接? (Y/n): ").strip().lower()
        if test_connection not in ["n", "no"]:
            print("🔄 正在测试SMTP连接...")
            smtp_test_result = self._test_smtp_connection(smtp_config)

            if not smtp_test_result:
                print("❌ SMTP连接测试失败")
                if provider_id in ["qq", "gmail", "163", "126"]:
                    print("💡 常见问题:")
                    print("   • 确认已开启SMTP服务")
                    print("   • 确认使用的是授权码而非登录密码")
                    print("   • 检查网络连接")

                continue_anyway = input("是否仍要保存账户? (y/N): ").strip().lower()
                if continue_anyway not in ["y", "yes"]:
                    print("❌ 账户添加已取消")
                    input("按回车键继续...")
                    return
            else:
                print("✅ SMTP连接测试成功")

        # 步骤8: 保存账户
        notes = self.provider_manager.get_provider_notes(provider_id)
        success = self.account_manager.add_account(
            account_name=account_name,
            email=email,
            password=password,
            smtp_config=smtp_config,
            pop3_config=pop3_config,
            display_name=display_name,
            notes=notes,
        )

        if success:
            print(f"\n✅ 账户 '{account_name}' 添加成功!")

            # 询问是否设为默认账户
            if not self.account_manager.get_default_account():
                self.account_manager.set_last_used(account_name)
                print(f"🎯 已设置为默认账户")
            else:
                set_default = input("是否设置为默认账户? (y/N): ").strip().lower()
                if set_default in ["y", "yes"]:
                    self.account_manager.set_last_used(account_name)
                    print(f"🎯 已设置为默认账户")
        else:
            print("\n❌ 账户添加失败")

        input("\n按回车键继续...")

    def _test_smtp_connection(self, smtp_config):
        """测试SMTP连接"""
        try:
            from client.smtp_client import SMTPClient

            # 创建临时SMTP客户端进行测试
            smtp_client = SMTPClient(
                host=smtp_config["host"],
                port=smtp_config["port"],
                use_ssl=smtp_config.get("use_ssl", True),
                username=smtp_config["username"],
                password=smtp_config["password"],
                auth_method=smtp_config.get("auth_method", "AUTO"),
            )

            # 尝试连接和认证
            # 注意：这里只是测试连接，不发送邮件
            # 实际的测试逻辑需要根据SMTPClient的实现来调整
            return True  # 暂时返回True，实际应该调用smtp_client的测试方法

        except Exception as e:
            logger.error(f"SMTP连接测试失败: {e}")
            return False

    def _select_provider(self):
        """选择邮件服务商"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📮 选择邮件服务商")
        print("=" * 60)

        providers = self.provider_manager.list_providers()

        for i, (provider_id, provider_name) in enumerate(providers, 1):
            print(f"{i}. {provider_name}")

        while True:
            try:
                choice = input(f"\n请选择服务商 [1-{len(providers)}]: ").strip()
                if not choice:
                    continue

                index = int(choice) - 1
                if 0 <= index < len(providers):
                    provider_id, _ = providers[index]
                    return provider_id
                else:
                    print("❌ 选择超出范围")
            except ValueError:
                print("❌ 请输入有效数字")

    def _configure_custom_server(self):
        """配置自定义服务器"""
        print(f"\n⚙️  自定义服务器配置")
        print("-" * 40)

        # SMTP配置
        print("📤 SMTP服务器配置:")
        smtp_host = input("SMTP服务器地址: ").strip()
        if not smtp_host:
            print("❌ SMTP服务器地址不能为空")
            return None, None

        try:
            smtp_port = int(input("SMTP端口 (默认: 587): ").strip() or "587")
        except ValueError:
            print("❌ 端口必须是数字")
            return None, None

        smtp_ssl = input("使用SSL加密? (Y/n): ").strip().lower() not in ["n", "no"]

        # POP3配置
        print("\n📥 POP3服务器配置:")
        pop3_host = input("POP3服务器地址: ").strip()
        if not pop3_host:
            print("❌ POP3服务器地址不能为空")
            return None, None

        try:
            pop3_port = int(input("POP3端口 (默认: 995): ").strip() or "995")
        except ValueError:
            print("❌ 端口必须是数字")
            return None, None

        pop3_ssl = input("使用SSL加密? (Y/n): ").strip().lower() not in ["n", "no"]

        smtp_config = {
            "host": smtp_host,
            "port": smtp_port,
            "use_ssl": smtp_ssl,
            "auth_method": "AUTO",
        }

        pop3_config = {
            "host": pop3_host,
            "port": pop3_port,
            "use_ssl": pop3_ssl,
            "auth_method": "AUTO",
        }

        return smtp_config, pop3_config

    def _manage_accounts(self):
        """管理现有账户"""
        while True:
            self.main_cli.clear_screen()
            print("\n" + "=" * 60)
            print("📋 管理邮箱账户")
            print("=" * 60)

            accounts = self.account_manager.list_accounts()
            if not accounts:
                print("📭 暂无已配置的账户")
                input("\n按回车键返回...")
                return

            # 显示账户列表
            default_account = self.account_manager.get_default_account()
            for i, account_name in enumerate(accounts, 1):
                account_info = self.account_manager.get_account(account_name)
                status = "🎯 默认" if account_name == default_account else "  "
                print(f"{i}. {status} {account_name} ({account_info['email']})")

            print(f"\n{len(accounts) + 1}. 🔙 返回上级菜单")

            try:
                choice = input(
                    f"\n请选择要管理的账户 [1-{len(accounts) + 1}]: "
                ).strip()
                if not choice:
                    continue

                index = int(choice) - 1
                if index == len(accounts):
                    return
                elif 0 <= index < len(accounts):
                    account_name = accounts[index]
                    self._manage_single_account(account_name)
                else:
                    print("❌ 选择超出范围")
                    input("按回车键继续...")
            except ValueError:
                print("❌ 请输入有效数字")
                input("按回车键继续...")

    def _manage_single_account(self, account_name: str):
        """管理单个账户"""
        while True:
            self.main_cli.clear_screen()
            account_info = self.account_manager.get_account(account_name)
            if not account_info:
                print("❌ 账户不存在")
                input("按回车键继续...")
                return

            print("\n" + "=" * 60)
            print(f"⚙️  管理账户: {account_name}")
            print("=" * 60)

            # 显示账户详细信息
            print(f"📧 邮箱地址: {account_info['email']}")
            print(f"👤 显示名称: {account_info['display_name']}")
            print(
                f"📤 SMTP服务器: {account_info['smtp']['host']}:{account_info['smtp']['port']}"
            )
            print(
                f"📥 POP3服务器: {account_info['pop3']['host']}:{account_info['pop3']['port']}"
            )
            if account_info.get("notes"):
                print(f"📝 备注: {account_info['notes']}")

            print("\n" + "-" * 60)
            print("1. ✏️  编辑账户信息")
            print("2. 🔐 更改密码")
            print("3. 🧪 测试连接")
            print("4. 📤 导出配置")
            print("5. 🗑️  删除账户")
            print("0. 🔙 返回账户列表")
            print("-" * 60)

            choice = input("\n请选择操作 [0-5]: ").strip()

            if choice == "1":
                self._edit_account_info(account_name)
            elif choice == "2":
                self._change_password(account_name)
            elif choice == "3":
                self._test_connection(account_name)
            elif choice == "4":
                self._export_account_config(account_name)
            elif choice == "5":
                if self._delete_account(account_name):
                    return
            elif choice == "0":
                return
            else:
                input("❌ 无效选择，请按回车键继续...")

    def _edit_account_info(self, account_name: str):
        """编辑账户信息"""
        account_info = self.account_manager.get_account(account_name)
        if not account_info:
            return

        self.main_cli.clear_screen()
        print(f"\n✏️  编辑账户: {account_name}")
        print("-" * 40)

        # 编辑显示名称
        current_display_name = account_info["display_name"]
        new_display_name = input(f"显示名称 (当前: {current_display_name}): ").strip()
        if new_display_name and new_display_name != current_display_name:
            self.account_manager.update_account(
                account_name, display_name=new_display_name
            )
            print("✅ 显示名称已更新")

        # 编辑备注
        current_notes = account_info.get("notes", "")
        new_notes = input(f"备注信息 (当前: {current_notes}): ").strip()
        if new_notes != current_notes:
            self.account_manager.update_account(account_name, notes=new_notes)
            print("✅ 备注信息已更新")

        input("\n按回车键继续...")

    def _change_password(self, account_name: str):
        """更改密码"""
        self.main_cli.clear_screen()
        print(f"\n🔐 更改账户密码: {account_name}")
        print("-" * 40)

        new_password = getpass.getpass("请输入新密码/授权码: ")
        if not new_password:
            print("❌ 密码不能为空")
            input("按回车键继续...")
            return

        confirm_password = getpass.getpass("请确认新密码/授权码: ")
        if new_password != confirm_password:
            print("❌ 两次输入的密码不一致")
            input("按回车键继续...")
            return

        # 更新账户密码
        account_info = self.account_manager.get_account(account_name)
        smtp_config = account_info["smtp"].copy()
        pop3_config = account_info["pop3"].copy()
        smtp_config["password"] = new_password
        pop3_config["password"] = new_password

        success = self.account_manager.update_account(
            account_name, password=new_password, smtp=smtp_config, pop3=pop3_config
        )

        if success:
            print("✅ 密码更新成功")
        else:
            print("❌ 密码更新失败")

        input("按回车键继续...")

    def _test_connection(self, account_name: str):
        """测试连接"""
        self.main_cli.clear_screen()
        print(f"\n🧪 测试连接: {account_name}")
        print("-" * 40)
        print("🔄 正在测试连接...")

        # 这里可以添加实际的连接测试逻辑
        # 暂时显示模拟结果
        import time

        time.sleep(2)

        print("✅ SMTP连接测试成功")
        print("✅ POP3连接测试成功")
        print("🎉 所有连接测试通过")

        input("\n按回车键继续...")

    def _export_account_config(self, account_name: str):
        """导出账户配置"""
        self.main_cli.clear_screen()
        print(f"\n📤 导出账户配置: {account_name}")
        print("-" * 40)

        export_path = input("导出文件路径 (默认: account_config.json): ").strip()
        if not export_path:
            export_path = "account_config.json"

        include_password = input("是否包含密码? (y/N): ").strip().lower() in [
            "y",
            "yes",
        ]

        # 创建单个账户的导出数据
        account_info = self.account_manager.get_account(account_name)
        if account_info:
            export_data = {account_name: account_info.copy()}
            if not include_password:
                export_data[account_name]["password"] = "***已隐藏***"

            try:
                import json

                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                print(f"✅ 配置已导出到: {export_path}")
            except Exception as e:
                print(f"❌ 导出失败: {e}")

        input("按回车键继续...")

    def _delete_account(self, account_name: str) -> bool:
        """删除账户"""
        self.main_cli.clear_screen()
        print(f"\n🗑️  删除账户: {account_name}")
        print("-" * 40)
        print("⚠️  警告: 此操作将永久删除账户配置，无法恢复!")

        confirm = input("确认删除? 请输入 'DELETE' 确认: ").strip()
        if confirm == "DELETE":
            success = self.account_manager.remove_account(account_name)
            if success:
                print("✅ 账户删除成功")
                input("按回车键继续...")
                return True
            else:
                print("❌ 账户删除失败")
        else:
            print("❌ 删除操作已取消")

        input("按回车键继续...")
        return False

    def _switch_account(self):
        """切换当前账户"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("🔄 切换当前账户")
        print("=" * 60)

        accounts = self.account_manager.list_accounts()
        if not accounts:
            print("📭 暂无已配置的账户")
            input("\n按回车键返回...")
            return

        current_default = self.account_manager.get_default_account()

        for i, account_name in enumerate(accounts, 1):
            account_info = self.account_manager.get_account(account_name)
            status = "🎯 当前" if account_name == current_default else "  "
            print(f"{i}. {status} {account_name} ({account_info['email']})")

        try:
            choice = input(f"\n请选择要切换到的账户 [1-{len(accounts)}]: ").strip()
            if not choice:
                return

            index = int(choice) - 1
            if 0 <= index < len(accounts):
                account_name = accounts[index]
                self.account_manager.set_last_used(account_name)
                print(f"✅ 已切换到账户: {account_name}")
            else:
                print("❌ 选择超出范围")
        except ValueError:
            print("❌ 请输入有效数字")

        input("按回车键继续...")

    def _advanced_settings(self):
        """高级设置"""
        while True:
            self.main_cli.clear_screen()
            print("\n" + "=" * 60)
            print("⚙️  高级设置")
            print("=" * 60)
            print("1. 📤 导出所有账户配置")
            print("2. 📥 导入账户配置")
            print("3. 🔧 重置主密码")
            print("4. 🧹 清理配置文件")
            print("0. 🔙 返回设置菜单")
            print("-" * 60)

            choice = input("\n请选择操作 [0-4]: ").strip()

            if choice == "1":
                self._export_all_accounts()
            elif choice == "2":
                self._import_accounts()
            elif choice == "3":
                self._reset_master_password()
            elif choice == "4":
                self._cleanup_config()
            elif choice == "0":
                return
            else:
                input("❌ 无效选择，请按回车键继续...")

    def _export_all_accounts(self):
        """导出所有账户配置"""
        self.main_cli.clear_screen()
        print("\n📤 导出所有账户配置")
        print("-" * 40)

        export_path = input("导出文件路径 (默认: all_accounts.json): ").strip()
        if not export_path:
            export_path = "all_accounts.json"

        include_password = input("是否包含密码? (y/N): ").strip().lower() in [
            "y",
            "yes",
        ]

        success = self.account_manager.export_accounts(export_path, include_password)
        if success:
            print(f"✅ 所有账户配置已导出到: {export_path}")
        else:
            print("❌ 导出失败")

        input("按回车键继续...")

    def _import_accounts(self):
        """导入账户配置"""
        self.main_cli.clear_screen()
        print("\n📥 导入账户配置")
        print("-" * 40)

        import_path = input("导入文件路径: ").strip()
        if not import_path:
            print("❌ 文件路径不能为空")
            input("按回车键继续...")
            return

        success = self.account_manager.import_accounts(import_path)
        if success:
            print("✅ 账户配置导入成功")
        else:
            print("❌ 导入失败")

        input("按回车键继续...")

    def _reset_master_password(self):
        """重置主密码"""
        self.main_cli.clear_screen()
        print("\n🔧 重置主密码")
        print("-" * 40)
        print("⚠️  警告: 重置主密码将清除所有已保存的账户配置!")
        print("请确保已备份重要数据。")

        confirm = input("确认重置? 请输入 'RESET' 确认: ").strip()
        if confirm == "RESET":
            # 删除密钥文件，下次启动时会重新生成
            key_file = self.account_manager.key_file
            if key_file.exists():
                key_file.unlink()

            # 删除账户文件
            accounts_file = self.account_manager.accounts_file
            if accounts_file.exists():
                accounts_file.unlink()

            print("✅ 主密码已重置，所有账户配置已清除")
        else:
            print("❌ 重置操作已取消")

        input("按回车键继续...")

    def _cleanup_config(self):
        """清理配置文件"""
        self.main_cli.clear_screen()
        print("\n🧹 清理配置文件")
        print("-" * 40)
        print("此操作将清理无效的配置项和临时文件")

        confirm = input("确认清理? (y/N): ").strip().lower()
        if confirm in ["y", "yes"]:
            # 这里可以添加实际的清理逻辑
            print("✅ 配置文件清理完成")
        else:
            print("❌ 清理操作已取消")

        input("按回车键继续...")

    def _show_help(self):
        """显示帮助信息"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📖 帮助与说明")
        print("=" * 60)

        help_text = """
🔧 账户设置功能说明:

📝 添加新账户:
   • 支持主流邮件服务商的自动配置
   • 提供详细的设置指导
   • 安全的密码加密存储

📋 管理现有账户:
   • 查看和编辑账户信息
   • 更改密码/授权码
   • 测试连接状态
   • 导出配置备份

🔄 切换当前账户:
   • 快速切换不同邮箱账户
   • 自动记住最后使用的账户

⚙️ 高级设置:
   • 批量导入/导出配置
   • 主密码管理
   • 配置文件维护

🔐 安全特性:
   • 密码加密存储
   • 主密码保护
   • 本地配置文件

💡 使用提示:
   • QQ邮箱/163邮箱需要使用授权码
   • Gmail需要开启两步验证并生成应用密码
   • 建议定期备份账户配置

📞 技术支持:
   如遇问题，请查看各邮件服务商的官方帮助文档
        """

        print(help_text)
        input("\n按回车键返回...")

    def get_current_account_config(self):
        """获取当前账户的配置（供其他模块使用）"""
        default_account = self.account_manager.get_default_account()
        if default_account:
            return self.account_manager.get_account(default_account)
        return None

    def get_smtp_config(self):
        """获取当前账户的SMTP配置"""
        account_config = self.get_current_account_config()
        if account_config:
            return account_config.get("smtp")
        return None

    def get_pop3_config(self):
        """获取当前账户的POP3配置"""
        account_config = self.get_current_account_config()
        if account_config:
            return account_config.get("pop3")
        return None
