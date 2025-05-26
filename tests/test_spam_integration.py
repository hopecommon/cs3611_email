#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
垃圾邮件过滤功能综合测试脚本
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spam_filter.spam_filter import KeywordSpamFilter
from server.new_db_handler import EmailService
from cli.spam_menu import SpamManagementMenu


def test_spam_filter_basic():
    """测试垃圾邮件过滤器基本功能"""
    print("=" * 60)
    print("🧪 测试垃圾邮件过滤器基本功能")
    print("=" * 60)

    try:
        # 初始化过滤器
        spam_filter = KeywordSpamFilter()
        print("✅ 垃圾邮件过滤器初始化成功")

        # 测试正常邮件
        normal_email = {
            "from_addr": "colleague@company.com",
            "subject": "项目进度汇报",
            "content": "本周项目进展顺利，预计下周完成第一阶段开发。",
        }

        result = spam_filter.analyze_email(normal_email)
        assert not result["is_spam"], "正常邮件被误判为垃圾邮件"
        print("✅ 正常邮件识别正确")

        # 测试垃圾邮件
        spam_email = {
            "from_addr": "noreply@spam.com",
            "subject": "紧急通知：免费奖金发放",
            "content": "恭喜您中奖！点击领取 http://malicious-site.com",
        }

        result = spam_filter.analyze_email(spam_email)
        assert result["is_spam"], "垃圾邮件未被正确识别"
        assert result["score"] >= 3.0, "垃圾邮件评分过低"
        print("✅ 垃圾邮件识别正确")

        # 测试阈值调整
        original_threshold = spam_filter.threshold
        assert spam_filter.update_threshold(5.0), "阈值更新失败"
        assert spam_filter.threshold == 5.0, "阈值未正确更新"

        # 恢复原始阈值
        spam_filter.update_threshold(original_threshold)
        print("✅ 阈值调整功能正常")

        return True

    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_database_integration():
    """测试数据库集成"""
    print("\n" + "=" * 60)
    print("🗄️ 测试数据库集成")
    print("=" * 60)

    # 创建临时数据库
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_emails.db")

    try:
        # 初始化邮件服务
        email_service = EmailService(temp_db_path)
        print("✅ 邮件服务初始化成功")

        # 测试保存正常邮件
        success = email_service.save_email(
            message_id="<test-normal@example.com>",
            from_addr="sender@example.com",
            to_addrs=["recipient@example.com"],
            subject="测试邮件",
            content="这是一封正常的测试邮件。",
        )
        assert success, "正常邮件保存失败"
        print("✅ 正常邮件保存成功")

        # 测试保存垃圾邮件
        success = email_service.save_email(
            message_id="<test-spam@spam.com>",
            from_addr="noreply@spam.com",
            to_addrs=["victim@example.com"],
            subject="紧急通知：免费奖金",
            content="点击领取您的奖金 http://spam-site.com",
        )
        assert success, "垃圾邮件保存失败"
        print("✅ 垃圾邮件保存成功")

        # 验证垃圾邮件标记
        spam_email = email_service.get_email("<test-spam@spam.com>")
        assert spam_email is not None, "无法获取垃圾邮件"
        assert spam_email["is_spam"], "垃圾邮件未被正确标记"
        assert spam_email["spam_score"] > 0, "垃圾邮件评分为0"
        print(f"✅ 垃圾邮件正确标记 (评分: {spam_email['spam_score']})")

        # 验证正常邮件标记
        normal_email = email_service.get_email("<test-normal@example.com>")
        assert normal_email is not None, "无法获取正常邮件"
        assert not normal_email["is_spam"], "正常邮件被误标记为垃圾邮件"
        print("✅ 正常邮件标记正确")

        # 测试垃圾邮件过滤查询
        all_emails = email_service.list_emails(include_spam=True)
        spam_emails = email_service.list_emails(include_spam=True, is_spam=True)
        normal_emails = email_service.list_emails(include_spam=False)

        assert len(all_emails) == 2, f"总邮件数量错误: {len(all_emails)}"
        assert len(spam_emails) == 1, f"垃圾邮件数量错误: {len(spam_emails)}"
        assert len(normal_emails) == 1, f"正常邮件数量错误: {len(normal_emails)}"
        print("✅ 邮件过滤查询功能正常")

        return True

    except Exception as e:
        print(f"❌ 数据库集成测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def test_keyword_management():
    """测试关键词管理功能"""
    print("\n" + "=" * 60)
    print("🔧 测试关键词管理功能")
    print("=" * 60)

    # 备份原始配置
    config_file = Path("config/spam_keywords.json")
    backup_file = Path("config/spam_keywords.json.backup")

    if config_file.exists():
        shutil.copy2(config_file, backup_file)

    try:
        # 创建测试配置
        test_keywords = {
            "subject": ["测试关键词"],
            "body": ["测试内容"],
            "sender": ["test@spam.com"],
        }

        import json

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(test_keywords, f, indent=2, ensure_ascii=False)

        # 测试过滤器重新加载
        spam_filter = KeywordSpamFilter()
        assert spam_filter.reload_keywords(), "关键词重新加载失败"
        print("✅ 关键词重新加载成功")

        # 测试新关键词生效
        test_email = {
            "from_addr": "test@spam.com",
            "subject": "包含测试关键词的邮件",
            "content": "这里有测试内容",
        }

        result = spam_filter.analyze_email(test_email)
        assert result["is_spam"], "新关键词未生效"
        assert len(result["matched_keywords"]) >= 2, "匹配关键词数量不正确"
        print("✅ 新关键词生效正常")

        return True

    except Exception as e:
        print(f"❌ 关键词管理测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # 恢复原始配置
        try:
            if backup_file.exists():
                shutil.move(backup_file, config_file)
            elif config_file.exists():
                config_file.unlink()
        except:
            pass


def test_performance():
    """测试性能"""
    print("\n" + "=" * 60)
    print("⚡ 测试性能")
    print("=" * 60)

    try:
        import time

        spam_filter = KeywordSpamFilter()

        # 准备测试数据
        test_emails = []
        for i in range(100):
            test_emails.append(
                {
                    "from_addr": f"user{i}@example.com",
                    "subject": f"测试邮件 {i}",
                    "content": f"这是第 {i} 封测试邮件的内容。",
                }
            )

        # 性能测试
        start_time = time.time()
        for email in test_emails:
            spam_filter.analyze_email(email)
        end_time = time.time()

        total_time = end_time - start_time
        # 防止除零错误
        if total_time == 0:
            total_time = 0.001  # 设置最小时间

        emails_per_second = len(test_emails) / total_time

        print(f"✅ 处理 {len(test_emails)} 封邮件用时: {total_time:.3f} 秒")
        print(f"✅ 处理速度: {emails_per_second:.1f} 封/秒")

        # 性能要求：至少每秒处理50封邮件
        assert emails_per_second >= 50, f"性能不达标: {emails_per_second:.1f} 封/秒"
        print("✅ 性能测试通过")

        return True

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始垃圾邮件过滤功能综合测试")
    print("=" * 80)

    tests = [
        ("基本功能测试", test_spam_filter_basic),
        ("数据库集成测试", test_database_integration),
        ("关键词管理测试", test_keyword_management),
        ("性能测试", test_performance),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name} - 通过")
            else:
                failed += 1
                print(f"\n❌ {test_name} - 失败")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} - 异常: {e}")

    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📈 成功率: {passed/(passed+failed)*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有测试通过！垃圾邮件过滤功能运行正常。")
        return True
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查相关功能。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
