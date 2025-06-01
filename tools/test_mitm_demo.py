# -*- coding: utf-8 -*-
"""
简化的MITM演示测试脚本
"""

import sys
import os
import socket
import threading
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.realistic_mitm_demo import (
    真实邮件服务器管理器,
    真实MITM代理,
    真实邮件客户端模拟器,
)


def test_mitm_demo():
    """测试MITM演示功能"""
    print("开始测试MITM演示功能...")

    # 创建管理器
    服务器管理器 = 真实邮件服务器管理器()
    客户端模拟器 = 真实邮件客户端模拟器()

    try:
        # 启动服务器
        print("启动邮件服务器...")
        服务器管理器.启动服务器()

        # 启动代理
        print("启动MITM代理...")
        明文代理 = 真实MITM代理(8026, "localhost", 8025, is_ssl=False)
        代理线程 = threading.Thread(target=明文代理.启动)
        代理线程.daemon = True
        代理线程.start()

        time.sleep(2)

        # 测试发送邮件
        print("测试发送邮件...")
        成功 = 客户端模拟器.通过mitm发送邮件(
            use_ssl=False, subject="测试邮件", content="这是一封测试邮件"
        )

        print(f"邮件发送结果: {'成功' if 成功 else '失败'}")

        # 获取分析报告
        报告 = 明文代理.获取分析报告()
        print(f"拦截数据包: {报告['总数据包']}")
        print(f"明文数据包: {报告['明文数据包']}")
        print(f"敏感信息类型: {报告['敏感信息类型']}")

        time.sleep(2)

    except Exception as e:
        print(f"测试出错: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 清理
        print("清理资源...")
        if "明文代理" in locals():
            明文代理.停止()
        服务器管理器.停止服务器()
        time.sleep(1)
        print("测试完成")


if __name__ == "__main__":
    test_mitm_demo()
