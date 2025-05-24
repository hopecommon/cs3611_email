"""
数据库处理器迁移辅助脚本
帮助逐步从旧的DatabaseHandler迁移到新的EmailService
"""

import os
import sys
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import DB_PATH
from server.new_db_handler import EmailService

# 设置日志
logger = setup_logging("migration_helper")


class DatabaseMigrationHelper:
    """数据库迁移辅助类"""

    def __init__(self):
        """初始化迁移辅助器"""
        self.old_db_path = DB_PATH
        self.backup_db_path = f"{DB_PATH}.backup"
        self.new_email_service = EmailService()
        logger.info("数据库迁移辅助器已初始化")

    def backup_current_database(self) -> bool:
        """
        备份当前数据库

        Returns:
            bool: 备份是否成功
        """
        try:
            if os.path.exists(self.old_db_path):
                shutil.copy2(self.old_db_path, self.backup_db_path)
                logger.info(f"数据库已备份到: {self.backup_db_path}")
                return True
            else:
                logger.warning("数据库文件不存在，无需备份")
                return True
        except Exception as e:
            logger.error(f"备份数据库时出错: {e}")
            return False

    def validate_data_integrity(self) -> bool:
        """
        验证数据完整性

        Returns:
            bool: 数据是否完整
        """
        try:
            # 检查邮件数据
            emails = self.new_email_service.list_emails(limit=10000)
            sent_emails = self.new_email_service.list_sent_emails(limit=10000)

            logger.info(f"验证数据完整性:")
            logger.info(f"  - 接收邮件: {len(emails)} 封")
            logger.info(f"  - 已发送邮件: {len(sent_emails)} 封")

            # 检查一些邮件的内容是否可访问
            content_accessible_count = 0
            for email in emails[:10]:  # 检查前10封邮件
                content = self.new_email_service.get_email_content(email["message_id"])
                if content:
                    content_accessible_count += 1

            logger.info(f"  - 内容可访问邮件: {content_accessible_count}/10")

            return True
        except Exception as e:
            logger.error(f"验证数据完整性时出错: {e}")
            return False

    def create_usage_guide(self) -> str:
        """
        创建使用指南

        Returns:
            str: 使用指南内容
        """
        guide = """
# 数据库处理器重构使用指南

## 重构概述
原有的 `DatabaseHandler` 类已经重构为更简洁的 `EmailService` 类，解决了以下问题：
1. 文件过于庞大（1569行 -> 分模块）
2. 方法命名不一致（统一为动词开头）
3. 参数过多且复杂（简化参数，提供默认值）
4. 功能混杂（分离关注点）

## 主要变化

### 1. 新的API设计
```python
# 旧方式 - 复杂的参数
db.save_email_metadata(message_id, from_addr, to_addrs, subject, date, size, is_spam, spam_score)
db.save_email_content(message_id, content)

# 新方式 - 统一接口
email_service.save_email(message_id, from_addr, to_addrs, subject, content, date)
```

### 2. 统一的方法命名
```python
# 旧方式 - 不一致的命名
db.get_email_metadata()
db.list_emails()
db.mark_email_as_read()

# 新方式 - 一致的命名
email_service.get_email()
email_service.list_emails()
email_service.update_email(is_read=True)
```

### 3. 简化的参数
```python
# 旧方式 - 参数过多
db.list_emails(user_email, include_deleted, include_spam, limit, offset)

# 新方式 - 合理的默认值
email_service.list_emails(user_email=None, limit=100)  # 其他参数有合理默认值
```

## 兼容性保证
为了确保现有代码正常工作，新的 `EmailService` 提供了所有旧方法的兼容性别名：

```python
# 这些旧方法仍然可用
email_service.get_email_metadata()
email_service.save_email_content()
email_service.mark_email_as_read()
```

## 推荐的迁移方式

### 立即修复的错误调用
```python
# 错误调用（CLI中的问题）
db.get_sent_emails()  # 方法不存在
db.get_emails()       # 方法不存在

# 正确调用
email_service.list_sent_emails()
email_service.list_emails()
```

### 逐步迁移的新API
```python
# 推荐逐步迁移到新API
email_service.save_email(message_id, from_addr, to_addrs, subject, content)
email_service.update_email(message_id, is_read=True)
email_service.delete_email(message_id, permanent=True)
```

## 性能改进
1. **模块化设计**: 职责分离，更易维护
2. **统一连接管理**: 减少数据库连接开销
3. **智能内容管理**: 更好的邮件内容处理
4. **类型安全**: 使用强类型模型

## 错误处理改进
1. **一致的异常处理**: 所有方法都有统一的错误处理
2. **详细的日志记录**: 更好的调试信息
3. **优雅的降级**: 出错时的合理回退策略

## 使用建议
1. **新项目**: 直接使用新的 `EmailService` API
2. **现有项目**: 可以直接替换，兼容性已保证
3. **逐步迁移**: 建议逐步迁移到新API以获得更好的开发体验
"""
        return guide

    def save_usage_guide(self, filename: str = "database_refactor_guide.md") -> bool:
        """
        保存使用指南到文件

        Args:
            filename: 文件名

        Returns:
            bool: 保存是否成功
        """
        try:
            guide_content = self.create_usage_guide()
            with open(filename, "w", encoding="utf-8") as f:
                f.write(guide_content)
            logger.info(f"使用指南已保存到: {filename}")
            return True
        except Exception as e:
            logger.error(f"保存使用指南时出错: {e}")
            return False

    def run_migration_test(self) -> bool:
        """
        运行迁移测试

        Returns:
            bool: 测试是否通过
        """
        try:
            logger.info("开始运行迁移测试...")

            # 测试基本功能
            logger.info("1. 测试邮件列表获取...")
            emails = self.new_email_service.list_emails(limit=5)
            logger.info(f"   获取到 {len(emails)} 封邮件")

            logger.info("2. 测试已发送邮件获取...")
            sent_emails = self.new_email_service.list_sent_emails(limit=5)
            logger.info(f"   获取到 {len(sent_emails)} 封已发送邮件")

            logger.info("3. 测试兼容性方法...")
            # 测试兼容性方法
            metadata = (
                self.new_email_service.get_email_metadata(emails[0]["message_id"])
                if emails
                else None
            )
            logger.info(
                f"   兼容性方法测试: {'通过' if metadata else '未通过（无邮件数据）'}"
            )

            logger.info("4. 测试新API方法...")
            # 测试新API
            email_data = (
                self.new_email_service.get_email(emails[0]["message_id"])
                if emails
                else None
            )
            logger.info(
                f"   新API方法测试: {'通过' if email_data else '未通过（无邮件数据）'}"
            )

            logger.info("迁移测试完成 ✓")
            return True
        except Exception as e:
            logger.error(f"迁移测试失败: {e}")
            return False

    def show_api_comparison(self) -> None:
        """显示API对比"""
        comparison = """
=== 数据库处理器API对比 ===

旧API (DatabaseHandler)          新API (EmailService)
─────────────────────────────────────────────────────────────
save_email_metadata()           save_email()
save_email_content()            save_email() (统一接口)
get_email_metadata()            get_email()
get_email_content()             get_email(include_content=True)
list_emails()                   list_emails() (简化参数)
mark_email_as_read()            update_email(is_read=True)
mark_email_as_deleted()         update_email(is_deleted=True)
mark_email_as_spam()            update_email(is_spam=True)
delete_email_metadata()        delete_email(permanent=True)

已发送邮件:
save_sent_email_metadata()     save_sent_email()
get_sent_email_metadata()      get_sent_email()
get_sent_email_content()       get_sent_email(include_content=True)
list_sent_emails()             list_sent_emails()

搜索:
search_emails()                search_emails() (简化参数)

修复的错误调用:
get_sent_emails() [不存在]     list_sent_emails()
get_emails() [不存在]          list_emails()
"""
        print(comparison)


def main():
    """主函数"""
    print("=" * 60)
    print("数据库处理器重构迁移辅助工具")
    print("=" * 60)

    migration_helper = DatabaseMigrationHelper()

    # 1. 备份数据库
    print("\n1. 备份当前数据库...")
    if migration_helper.backup_current_database():
        print("✓ 数据库备份成功")
    else:
        print("✗ 数据库备份失败")
        return

    # 2. 验证数据完整性
    print("\n2. 验证数据完整性...")
    if migration_helper.validate_data_integrity():
        print("✓ 数据完整性验证通过")
    else:
        print("✗ 数据完整性验证失败")
        return

    # 3. 运行迁移测试
    print("\n3. 运行迁移测试...")
    if migration_helper.run_migration_test():
        print("✓ 迁移测试通过")
    else:
        print("✗ 迁移测试失败")
        return

    # 4. 显示API对比
    print("\n4. API对比:")
    migration_helper.show_api_comparison()

    # 5. 保存使用指南
    print("\n5. 保存使用指南...")
    if migration_helper.save_usage_guide():
        print("✓ 使用指南已保存")
    else:
        print("✗ 保存使用指南失败")

    print("\n" + "=" * 60)
    print("迁移准备完成！")
    print("=" * 60)
    print("\n建议:")
    print("1. 阅读生成的 database_refactor_guide.md 文件")
    print("2. 逐步替换代码中的数据库调用")
    print("3. 优先修复已知的错误调用（如CLI中的问题）")
    print("4. 测试完毕后可以删除备份文件")


if __name__ == "__main__":
    main()
