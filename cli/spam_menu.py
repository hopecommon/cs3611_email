# -*- coding: utf-8 -*-
"""
垃圾邮件管理菜单模块
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from spam_filter.spam_filter import KeywordSpamFilter

# 设置日志
logger = setup_logging("spam_menu")


class SpamManagementMenu:
    """垃圾邮件管理菜单"""

    def __init__(self, main_cli):
        """初始化垃圾邮件管理菜单"""
        self.main_cli = main_cli
        self.keywords_file = Path("config/spam_keywords.json")
        self.keywords = self._load_keywords()
        # 初始化垃圾邮件过滤器实例
        self.spam_filter = KeywordSpamFilter()

    def _load_keywords(self) -> Dict[str, List[str]]:
        """加载垃圾邮件关键词配置"""
        try:
            if not self.keywords_file.exists():
                return {"subject": [], "body": [], "sender": []}

            with open(self.keywords_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载垃圾邮件关键词失败: {e}")
            return {"subject": [], "body": [], "sender": []}

    def _save_keywords(self):
        """保存垃圾邮件关键词配置"""
        try:
            self.keywords_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.keywords_file, "w", encoding="utf-8") as f:
                json.dump(self.keywords, f, indent=2, ensure_ascii=False)
            # 重新加载过滤器的关键词
            self.spam_filter.reload_keywords()
            return True
        except Exception as e:
            logger.error(f"保存关键词失败: {e}")
            return False

    def show_menu(self):
        """显示垃圾邮件管理菜单"""
        while True:
            self.main_cli.clear_screen()
            print("\n" + "=" * 60)
            print("🛡️ 垃圾邮件管理")
            print("=" * 60)
            print("1. 📋 查看当前关键词")
            print("2. ➕ 添加关键词")
            print("3. ❌ 删除关键词")
            print("4. 📈 调整过滤阈值")
            print("5. ⚙️ 高级配置")
            print("6. 📊 过滤器统计")
            print("7. 🧪 测试过滤器")
            print("0. 🔙 返回主菜单")
            print("-" * 60)

            choice = input("\n请选择操作 [0-7]: ").strip()

            if choice == "1":
                self._show_current_keywords()
            elif choice == "2":
                self._add_keyword()
            elif choice == "3":
                self._remove_keyword()
            elif choice == "4":
                self._adjust_threshold()
            elif choice == "5":
                self._advanced_config()
            elif choice == "6":
                self._show_filter_stats()
            elif choice == "7":
                self._test_filter()
            elif choice == "0":
                return
            else:
                input("❌ 无效选择，请按回车键继续...")

    def _show_current_keywords(self):
        """显示当前关键词配置"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📋 当前垃圾邮件关键词")
        print("=" * 60)

        for category in ["subject", "body", "sender"]:
            print(f"\n🔍 {category.upper()} 关键词:")
            if self.keywords.get(category):
                for i, keyword in enumerate(self.keywords[category], 1):
                    print(f"  {i}. {keyword}")
            else:
                print("  (暂无关键词)")

        print(f"\n⚙️ 当前阈值: {self.spam_filter.threshold}")
        input("\n按回车键返回...")

    def _add_keyword(self):
        """添加关键词"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("➕ 添加垃圾邮件关键词")
        print("=" * 60)
        print("1. 主题关键词")
        print("2. 正文关键词")
        print("3. 发件人关键词")
        print("0. 取消")
        print("-" * 60)

        choice = input("\n选择要添加的类别 [0-3]: ").strip()
        category_map = {"1": "subject", "2": "body", "3": "sender"}

        if choice not in category_map:
            return

        category = category_map[choice]
        keyword = input("\n请输入要添加的关键词（支持正则表达式）: ").strip()

        if not keyword:
            input("❌ 关键词不能为空，按回车键继续...")
            return

        if keyword in self.keywords[category]:
            input("⚠️ 关键词已存在，按回车键继续...")
            return

        self.keywords[category].append(keyword)
        if self._save_keywords():
            input(f"✅ 成功添加 {category} 关键词: {keyword}\n按回车键继续...")
        else:
            input("❌ 保存失败，按回车键继续...")

    def _remove_keyword(self):
        """删除关键词"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("❌ 删除垃圾邮件关键词")
        print("=" * 60)
        print("1. 主题关键词")
        print("2. 正文关键词")
        print("3. 发件人关键词")
        print("0. 取消")
        print("-" * 60)

        choice = input("\n选择要删除的类别 [0-3]: ").strip()
        category_map = {"1": "subject", "2": "body", "3": "sender"}

        if choice not in category_map:
            return

        category = category_map[choice]
        if not self.keywords[category]:
            input(f"❌ {category} 类别没有可删除的关键词，按回车键继续...")
            return

        print(f"\n当前 {category} 关键词:")
        for i, kw in enumerate(self.keywords[category], 1):
            print(f"  {i}. {kw}")

        try:
            idx = int(input("\n请输入要删除的关键词序号: ")) - 1
            if 0 <= idx < len(self.keywords[category]):
                removed = self.keywords[category].pop(idx)
                if self._save_keywords():
                    input(f"✅ 已删除关键词: {removed}\n按回车键继续...")
                else:
                    input("❌ 保存失败，按回车键继续...")
            else:
                input("❌ 无效的序号，按回车键继续...")
        except ValueError:
            input("❌ 请输入有效数字，按回车键继续...")

    def _adjust_threshold(self):
        """调整过滤阈值"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📈 调整垃圾邮件过滤阈值")
        print("=" * 60)
        print(f"当前垃圾邮件阈值: {self.spam_filter.threshold}")
        print("\n💡 阈值说明:")
        print("• 阈值越低，过滤越严格（可能误判正常邮件）")
        print("• 阈值越高，过滤越宽松（可能漏过垃圾邮件）")
        print("• 建议范围: 2.0 - 5.0")
        print("• 默认值: 3.0")

        try:
            new_value = float(input("\n请输入新的阈值 (0.0-10.0): "))
            if self.spam_filter.update_threshold(new_value):
                input(f"✅ 已更新阈值为 {new_value}\n按回车键继续...")
            else:
                input("❌ 阈值更新失败，请检查输入范围\n按回车键继续...")
        except ValueError:
            input("❌ 请输入有效数字，按回车键继续...")

    def _test_filter(self):
        """测试垃圾邮件过滤器"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("🧪 测试垃圾邮件过滤器")
        print("=" * 60)

        print("请输入测试邮件信息:")
        from_addr = input("发件人地址: ").strip()
        subject = input("邮件主题: ").strip()
        content = input("邮件内容: ").strip()

        if not any([from_addr, subject, content]):
            input("❌ 请至少输入一项信息，按回车键继续...")
            return

        test_email = {"from_addr": from_addr, "subject": subject, "content": content}

        result = self.spam_filter.analyze_email(test_email)

        print(f"\n📊 分析结果:")
        print(f"判定结果: {'🚫 垃圾邮件' if result['is_spam'] else '✅ 正常邮件'}")
        print(f"垃圾评分: {result['score']:.1f}")
        print(f"当前阈值: {self.spam_filter.threshold}")

        if result["matched_keywords"]:
            print(f"匹配关键词:")
            for keyword in result["matched_keywords"]:
                print(f"  • {keyword}")
        else:
            print("匹配关键词: 无")

        input("\n按回车键继续...")

    def _advanced_config(self):
        """高级配置"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("⚙️ 高级配置")
        print("=" * 60)

        print("当前配置:")
        stats = self.spam_filter.get_filter_stats()
        print(f"基础阈值: {stats['threshold']}")
        print(f"最小阈值: {stats['min_threshold']}")
        print(f"最大阈值: {stats['max_threshold']}")
        print(f"动态阈值: {'启用' if stats['dynamic_threshold'] else '禁用'}")

        print("\n配置选项:")
        print("1. 设置基础阈值")
        print("2. 设置最小阈值")
        print("3. 设置最大阈值")
        print("4. 切换动态阈值")
        print("0. 返回")

        choice = input("\n请选择 [0-4]: ").strip()

        if choice == "1":
            try:
                threshold = float(input("请输入新的基础阈值 (0.0-10.0): "))
                if self.spam_filter.configure_thresholds(base_threshold=threshold):
                    print("✅ 基础阈值设置成功")
                else:
                    print("❌ 设置失败")
            except ValueError:
                print("❌ 请输入有效的数字")

        elif choice == "2":
            try:
                threshold = float(input("请输入新的最小阈值 (0.0-10.0): "))
                if self.spam_filter.configure_thresholds(min_threshold=threshold):
                    print("✅ 最小阈值设置成功")
                else:
                    print("❌ 设置失败")
            except ValueError:
                print("❌ 请输入有效的数字")

        elif choice == "3":
            try:
                threshold = float(input("请输入新的最大阈值 (0.0-10.0): "))
                if self.spam_filter.configure_thresholds(max_threshold=threshold):
                    print("✅ 最大阈值设置成功")
                else:
                    print("❌ 设置失败")
            except ValueError:
                print("❌ 请输入有效的数字")

        elif choice == "4":
            current = self.spam_filter.dynamic_threshold
            new_status = not current
            if self.spam_filter.configure_thresholds(enable_dynamic=new_status):
                status_text = "启用" if new_status else "禁用"
                print(f"✅ 动态阈值已{status_text}")
            else:
                print("❌ 设置失败")

        input("\n按回车键继续...")

    def _show_filter_stats(self):
        """显示过滤器统计信息"""
        self.main_cli.clear_screen()
        print("\n" + "=" * 60)
        print("📊 过滤器统计信息")
        print("=" * 60)

        stats = self.spam_filter.get_filter_stats()

        print("📋 阈值配置:")
        print(f"  基础阈值: {stats['threshold']}")
        print(f"  最小阈值: {stats['min_threshold']}")
        print(f"  最大阈值: {stats['max_threshold']}")
        print(f"  动态阈值: {'启用' if stats['dynamic_threshold'] else '禁用'}")

        print("\n🔤 关键词统计:")
        keyword_counts = stats["keyword_counts"]
        print(f"  主题关键词: {keyword_counts['subject']} 个")
        print(f"  正文关键词: {keyword_counts['body']} 个")
        print(f"  发件人关键词: {keyword_counts['sender']} 个")
        print(f"  总计: {sum(keyword_counts.values())} 个")

        if stats["dynamic_threshold"]:
            print("\n⚙️ 动态阈值规则:")
            print("  • 多重匹配时：阈值降低 0.5")
            print("  • 仅主题匹配时：阈值提高 0.3")
            print("  • 内容过短时：额外 0.5 分")
            print("  • 多重匹配奖励：额外 0.5 × (匹配数-1) 分")

        input("\n按回车键继续...")
