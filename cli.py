#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件客户端命令行界面 - 主入口文件
提供基于菜单的邮件客户端操作界面

这是重构后的简洁版本，所有功能模块都在cli/目录下
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import EmailCLI
from common.utils import setup_logging

# 设置日志
logger = setup_logging("cli_main")


def main():
    """主函数"""
    try:
        print("🚀 启动邮件客户端...")
        
        # 创建并启动CLI
        email_cli = EmailCLI()
        email_cli.main_menu()
        
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序运行时出错: {e}")
        print(f"❌ 程序运行时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
