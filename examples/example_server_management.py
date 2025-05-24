# -*- coding: utf-8 -*-
"""
服务器管理和监控示例脚本

本脚本演示如何管理和监控邮件服务器：
- 服务器状态监控
- 用户管理操作
- 邮件数据统计
- 性能监控
- 数据库维护
- 日志分析

使用前请确保服务器已正确配置和启动。
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.new_db_handler import EmailService as DatabaseHandler
from server.user_auth import UserAuth
from common.utils import setup_logging
from common.config import EMAIL_STORAGE_DIR

# 设置日志
logger = setup_logging("server_management", verbose=True)

# ==================== 配置部分 ====================

# 数据库配置
DATABASE_CONFIG = {
    "db_path": "data/email_server.db",
    "backup_dir": "backups/",
    "log_retention_days": 30
}

# 监控配置
MONITORING_CONFIG = {
    "check_interval": 60,       # 检查间隔（秒）
    "alert_thresholds": {
        "disk_usage": 80,       # 磁盘使用率阈值（%）
        "memory_usage": 85,     # 内存使用率阈值（%）
        "error_rate": 5         # 错误率阈值（%）
    }
}

class ServerManager:
    """
    服务器管理器类
    """
    
    def __init__(self, db_path=None):
        """
        初始化服务器管理器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path or DATABASE_CONFIG["db_path"]
        self.db_handler = None
        self.user_auth = None
        
        try:
            self.db_handler = DatabaseHandler(self.db_path)
            self.user_auth = UserAuth(self.db_path)
            print(f"✅ 服务器管理器初始化成功")
        except Exception as e:
            print(f"❌ 服务器管理器初始化失败: {e}")
            raise
    
    def get_server_status(self):
        """
        获取服务器状态信息
        
        Returns:
            dict: 服务器状态信息
        """
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "database": self._get_database_status(),
                "users": self._get_user_statistics(),
                "emails": self._get_email_statistics(),
                "storage": self._get_storage_status(),
                "system": self._get_system_status()
            }
            return status
        except Exception as e:
            logger.error(f"获取服务器状态失败: {e}")
            return {"error": str(e)}
    
    def _get_database_status(self):
        """
        获取数据库状态
        """
        try:
            # 检查数据库连接
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取数据库大小
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            # 获取表信息
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 获取各表记录数
            table_counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "status": "connected",
                "size_bytes": db_size,
                "size_mb": round(db_size / 1024 / 1024, 2),
                "tables": table_counts
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _get_user_statistics(self):
        """
        获取用户统计信息
        """
        try:
            users = self.user_auth.list_users()
            
            active_users = sum(1 for user in users if user.is_active)
            inactive_users = len(users) - active_users
            
            # 获取最近登录统计
            recent_logins = 0
            for user in users:
                if user.last_login:
                    last_login = datetime.fromisoformat(user.last_login)
                    if last_login > datetime.now() - timedelta(days=7):
                        recent_logins += 1
            
            return {
                "total_users": len(users),
                "active_users": active_users,
                "inactive_users": inactive_users,
                "recent_logins": recent_logins
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_email_statistics(self):
        """
        获取邮件统计信息
        """
        try:
            # 获取邮件总数
            total_emails = len(self.db_handler.list_emails())
            
            # 获取最近24小时的邮件
            yesterday = datetime.now() - timedelta(days=1)
            recent_emails = len(self.db_handler.list_emails(since_date=yesterday))
            
            # 获取已读/未读邮件统计
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM emails WHERE is_read = 1")
            read_emails = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM emails WHERE is_read = 0")
            unread_emails = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM emails WHERE is_deleted = 1")
            deleted_emails = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM emails WHERE is_spam = 1")
            spam_emails = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_emails": total_emails,
                "recent_emails": recent_emails,
                "read_emails": read_emails,
                "unread_emails": unread_emails,
                "deleted_emails": deleted_emails,
                "spam_emails": spam_emails
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_storage_status(self):
        """
        获取存储状态
        """
        try:
            # 计算邮件存储目录大小
            total_size = 0
            file_count = 0
            
            if os.path.exists(EMAIL_STORAGE_DIR):
                for root, dirs, files in os.walk(EMAIL_STORAGE_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path):
                            total_size += os.path.getsize(file_path)
                            file_count += 1
            
            # 获取磁盘使用情况
            import shutil
            disk_usage = shutil.disk_usage(os.path.dirname(self.db_path))
            
            return {
                "email_storage_mb": round(total_size / 1024 / 1024, 2),
                "email_file_count": file_count,
                "disk_total_gb": round(disk_usage.total / 1024 / 1024 / 1024, 2),
                "disk_used_gb": round(disk_usage.used / 1024 / 1024 / 1024, 2),
                "disk_free_gb": round(disk_usage.free / 1024 / 1024 / 1024, 2),
                "disk_usage_percent": round(disk_usage.used / disk_usage.total * 100, 2)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_system_status(self):
        """
        获取系统状态
        """
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            
            # 进程信息
            process = psutil.Process()
            process_info = {
                "pid": process.pid,
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
            }
            
            return {
                "cpu_percent": cpu_percent,
                "memory_total_gb": round(memory.total / 1024 / 1024 / 1024, 2),
                "memory_used_gb": round(memory.used / 1024 / 1024 / 1024, 2),
                "memory_percent": memory.percent,
                "process": process_info
            }
        except ImportError:
            return {"error": "psutil not installed"}
        except Exception as e:
            return {"error": str(e)}

def display_server_status():
    """
    显示服务器状态
    """
    print("=== 服务器状态监控 ===")
    
    try:
        manager = ServerManager()
        status = manager.get_server_status()
        
        print(f"\n📊 服务器状态报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 数据库状态
        if "database" in status:
            db_status = status["database"]
            print(f"\n💾 数据库状态:")
            print(f"  状态: {db_status.get('status', 'unknown')}")
            print(f"  大小: {db_status.get('size_mb', 0)} MB")
            if "tables" in db_status:
                print(f"  表信息:")
                for table, count in db_status["tables"].items():
                    print(f"    {table}: {count} 条记录")
        
        # 用户统计
        if "users" in status:
            user_stats = status["users"]
            print(f"\n👤 用户统计:")
            print(f"  总用户数: {user_stats.get('total_users', 0)}")
            print(f"  活跃用户: {user_stats.get('active_users', 0)}")
            print(f"  停用用户: {user_stats.get('inactive_users', 0)}")
            print(f"  最近登录: {user_stats.get('recent_logins', 0)} (7天内)")
        
        # 邮件统计
        if "emails" in status:
            email_stats = status["emails"]
            print(f"\n📧 邮件统计:")
            print(f"  总邮件数: {email_stats.get('total_emails', 0)}")
            print(f"  最近邮件: {email_stats.get('recent_emails', 0)} (24小时内)")
            print(f"  已读邮件: {email_stats.get('read_emails', 0)}")
            print(f"  未读邮件: {email_stats.get('unread_emails', 0)}")
            print(f"  已删除: {email_stats.get('deleted_emails', 0)}")
            print(f"  垃圾邮件: {email_stats.get('spam_emails', 0)}")
        
        # 存储状态
        if "storage" in status:
            storage_stats = status["storage"]
            print(f"\n💿 存储状态:")
            print(f"  邮件存储: {storage_stats.get('email_storage_mb', 0)} MB")
            print(f"  邮件文件: {storage_stats.get('email_file_count', 0)} 个")
            print(f"  磁盘总量: {storage_stats.get('disk_total_gb', 0)} GB")
            print(f"  磁盘已用: {storage_stats.get('disk_used_gb', 0)} GB")
            print(f"  磁盘可用: {storage_stats.get('disk_free_gb', 0)} GB")
            print(f"  使用率: {storage_stats.get('disk_usage_percent', 0)}%")
        
        # 系统状态
        if "system" in status:
            system_stats = status["system"]
            print(f"\n🖥️  系统状态:")
            print(f"  CPU使用率: {system_stats.get('cpu_percent', 0)}%")
            print(f"  内存总量: {system_stats.get('memory_total_gb', 0)} GB")
            print(f"  内存已用: {system_stats.get('memory_used_gb', 0)} GB")
            print(f"  内存使用率: {system_stats.get('memory_percent', 0)}%")
            if "process" in system_stats:
                process_info = system_stats["process"]
                print(f"  进程ID: {process_info.get('pid', 'unknown')}")
                print(f"  进程内存: {process_info.get('memory_mb', 0)} MB")
        
    except Exception as e:
        print(f"❌ 获取服务器状态失败: {e}")

def manage_users():
    """
    用户管理操作
    """
    print("\n=== 用户管理 ===")
    
    try:
        user_auth = UserAuth()
        
        while True:
            print("\n用户管理选项:")
            print("1. 列出所有用户")
            print("2. 创建新用户")
            print("3. 激活/停用用户")
            print("4. 修改用户密码")
            print("5. 删除用户")
            print("0. 返回主菜单")
            
            choice = input("\n请选择操作 (0-5): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                # 列出所有用户
                users = user_auth.list_users()
                print(f"\n用户列表 (共 {len(users)} 个用户):")
                print("-" * 80)
                print(f"{'用户名':<15} {'邮箱':<25} {'姓名':<15} {'状态':<8} {'最后登录'}")
                print("-" * 80)
                for user in users:
                    status = "激活" if user.is_active else "停用"
                    last_login = user.last_login or "从未登录"
                    print(f"{user.username:<15} {user.email:<25} {user.full_name:<15} {status:<8} {last_login}")
                
            elif choice == "2":
                # 创建新用户
                print("\n创建新用户:")
                username = input("用户名: ").strip()
                email = input("邮箱: ").strip()
                password = input("密码: ").strip()
                full_name = input("姓名: ").strip()
                
                if username and email and password:
                    try:
                        user = user_auth.create_user(username, email, password, full_name)
                        if user:
                            print(f"✅ 用户创建成功: {username}")
                        else:
                            print(f"❌ 用户创建失败")
                    except Exception as e:
                        print(f"❌ 用户创建失败: {e}")
                else:
                    print("❌ 请填写完整信息")
            
            elif choice == "3":
                # 激活/停用用户
                username = input("\n请输入用户名: ").strip()
                if username:
                    users = user_auth.list_users()
                    user = next((u for u in users if u.username == username), None)
                    if user:
                        if user.is_active:
                            user_auth.deactivate_user(username)
                            print(f"✅ 用户 {username} 已停用")
                        else:
                            user_auth.activate_user(username)
                            print(f"✅ 用户 {username} 已激活")
                    else:
                        print(f"❌ 用户 {username} 不存在")
            
            elif choice == "4":
                # 修改用户密码
                username = input("\n请输入用户名: ").strip()
                new_password = input("新密码: ").strip()
                if username and new_password:
                    try:
                        success = user_auth.change_password(username, new_password)
                        if success:
                            print(f"✅ 用户 {username} 密码修改成功")
                        else:
                            print(f"❌ 密码修改失败")
                    except Exception as e:
                        print(f"❌ 密码修改失败: {e}")
            
            elif choice == "5":
                # 删除用户
                username = input("\n请输入要删除的用户名: ").strip()
                confirm = input(f"确认删除用户 {username}? (y/N): ").strip().lower()
                if confirm == 'y':
                    try:
                        # 注意：这里需要实现删除用户的方法
                        print(f"⚠️  删除用户功能需要在UserAuth类中实现")
                    except Exception as e:
                        print(f"❌ 删除用户失败: {e}")
                else:
                    print("取消删除操作")
            
            else:
                print("❌ 无效选择")
    
    except Exception as e:
        print(f"❌ 用户管理失败: {e}")

def database_maintenance():
    """
    数据库维护操作
    """
    print("\n=== 数据库维护 ===")
    
    try:
        db_handler = EmailService()
        
        print("\n数据库维护选项:")
        print("1. 数据库备份")
        print("2. 清理已删除邮件")
        print("3. 数据库压缩")
        print("4. 数据库统计")
        print("5. 检查数据完整性")
        
        choice = input("\n请选择操作 (1-5): ").strip()
        
        if choice == "1":
            # 数据库备份
            backup_dir = DATABASE_CONFIG["backup_dir"]
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"email_db_backup_{timestamp}.db")
            
            try:
                import shutil
                shutil.copy2(db_handler.db_path, backup_file)
                print(f"✅ 数据库备份成功: {backup_file}")
            except Exception as e:
                print(f"❌ 数据库备份失败: {e}")
        
        elif choice == "2":
            # 清理已删除邮件
            days = input("清理多少天前的已删除邮件 (默认30天): ").strip()
            days = int(days) if days.isdigit() else 30
            
            try:
                # 这里需要实现清理已删除邮件的方法
                print(f"⚠️  清理已删除邮件功能需要在DatabaseHandler类中实现")
                print(f"将清理 {days} 天前的已删除邮件")
            except Exception as e:
                print(f"❌ 清理失败: {e}")
        
        elif choice == "3":
            # 数据库压缩
            try:
                conn = sqlite3.connect(db_handler.db_path)
                conn.execute("VACUUM")
                conn.close()
                print("✅ 数据库压缩完成")
            except Exception as e:
                print(f"❌ 数据库压缩失败: {e}")
        
        elif choice == "4":
            # 数据库统计
            try:
                conn = sqlite3.connect(db_handler.db_path)
                cursor = conn.cursor()
                
                print("\n数据库统计信息:")
                
                # 获取表信息
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"  {table}: {count} 条记录")
                
                # 获取数据库大小
                db_size = os.path.getsize(db_handler.db_path)
                print(f"  数据库大小: {db_size / 1024 / 1024:.2f} MB")
                
                conn.close()
                
            except Exception as e:
                print(f"❌ 获取统计信息失败: {e}")
        
        elif choice == "5":
            # 检查数据完整性
            try:
                conn = sqlite3.connect(db_handler.db_path)
                cursor = conn.cursor()
                
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                
                if result == "ok":
                    print("✅ 数据库完整性检查通过")
                else:
                    print(f"⚠️  数据库完整性检查发现问题: {result}")
                
                conn.close()
                
            except Exception as e:
                print(f"❌ 完整性检查失败: {e}")
        
        else:
            print("❌ 无效选择")
    
    except Exception as e:
        print(f"❌ 数据库维护失败: {e}")

def main():
    """
    主函数 - 服务器管理示例
    """
    print("邮件服务器管理工具")
    print("=" * 50)
    print("本工具提供服务器监控、用户管理和数据库维护功能")
    print()
    
    while True:
        print("\n主菜单:")
        print("1. 显示服务器状态")
        print("2. 用户管理")
        print("3. 数据库维护")
        print("4. 导出状态报告")
        print("0. 退出")
        
        choice = input("\n请选择操作 (0-4): ").strip()
        
        if choice == "0":
            print("退出服务器管理工具")
            break
        elif choice == "1":
            display_server_status()
        elif choice == "2":
            manage_users()
        elif choice == "3":
            database_maintenance()
        elif choice == "4":
            # 导出状态报告
            try:
                manager = ServerManager()
                status = manager.get_server_status()
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = f"server_status_report_{timestamp}.json"
                
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(status, f, indent=2, ensure_ascii=False)
                
                print(f"✅ 状态报告已导出: {report_file}")
            except Exception as e:
                print(f"❌ 导出报告失败: {e}")
        else:
            print("❌ 无效选择")

if __name__ == "__main__":
    main()
