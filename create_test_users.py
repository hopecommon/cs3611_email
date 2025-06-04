#!/usr/bin/env python3
"""
创建PGP邮件测试用户

为邮件系统创建必要的测试用户账户
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from server.user_auth import UserAuth

def create_test_users():
    """创建测试用户"""
    print("🔧 创建PGP邮件测试用户...")
    
    try:
        auth = UserAuth()
        
        # 创建测试用户
        test_users = [
            ("test@example.com", "test123", "测试用户"),
            ("alice@test.local", "alice123", "Alice Chen"),
            ("bob@test.local", "bob123", "Bob Wang"),
            ("admin@test.local", "admin123", "系统管理员")
        ]
        
        for username, password, display_name in test_users:
            try:
                result = auth.create_user(username, password)
                if result:
                    print(f"   ✅ 创建用户: {username} ({display_name})")
                else:
                    print(f"   ⚠️ 用户已存在: {username}")
            except Exception as e:
                print(f"   ❌ 创建用户失败 {username}: {e}")
        
        # 显示用户列表
        print(f"\n📋 当前用户列表:")
        users = auth.list_users()
        for i, user in enumerate(users, 1):
            print(f"   {i}. {user}")
        
        print(f"\n✅ 测试用户准备完成，共 {len(users)} 个用户")
        return True
        
    except Exception as e:
        print(f"❌ 创建用户失败: {e}")
        return False

if __name__ == "__main__":
    success = create_test_users()
    if success:
        print("\n🎯 现在可以使用这些用户进行PGP邮件测试")
    else:
        print("\n❌ 用户创建失败")
        sys.exit(1)