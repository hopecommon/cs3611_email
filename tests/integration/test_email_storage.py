#!/usr/bin/env python3
"""
测试邮件存储功能和并发性能的脚本
"""

import os
import sys
import time
import subprocess
import sqlite3
import threading
import concurrent.futures
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.utils import setup_logging

# 设置日志
logger = setup_logging("test_email_storage")


def check_database_before():
    """检查测试前的数据库状态"""
    print("=== 测试前数据库状态 ===")
    db_path = "data/email_db.sqlite"

    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return 0

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM emails")
        email_count = cursor.fetchone()[0]
        print(f"emails表中的邮件数量: {email_count}")

        conn.close()
        return email_count

    except Exception as e:
        print(f"检查数据库时出错: {e}")
        return 0


def start_smtp_server(optimized=True):
    """启动SMTP服务器"""
    print("\n=== 启动SMTP服务器 ===")

    if optimized:
        cmd = [
            "python",
            "examples/run_optimized_smtp_server.py",
            "--host",
            "localhost",
            "--port",
            "8025",
            "--max-connections",
            "200",  # 增加最大连接数
            "--no-ssl",  # 使用非SSL模式简化测试
        ]
        print("使用优化SMTP服务器")
    else:
        cmd = [
            "python",
            "examples/run_auth_smtp_server.py",
            "--host",
            "localhost",
            "--port",
            "8025",
            "--no-ssl",  # 使用非SSL模式简化测试
        ]
        print("使用标准SMTP服务器")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # 等待服务器启动
        print("等待SMTP服务器启动...")
        time.sleep(3)

        # 检查进程是否还在运行
        if process.poll() is None:
            print("SMTP服务器启动成功")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"SMTP服务器启动失败:")
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")
            return None

    except Exception as e:
        print(f"启动SMTP服务器时出错: {e}")
        return None


def send_test_email():
    """发送测试邮件"""
    print("\n=== 发送测试邮件 ===")

    cmd = [
        "python",
        "examples/send_auth_email.py",
        "--host",
        "localhost",
        "--port",
        "8025",
        "--username",
        "testuser",
        "--password",
        "testpass",
        "--sender",
        "testuser@example.com",
        "--recipient",
        "testuser@example.com",
        "--subject",
        "存储测试邮件",
        "--content",
        "这是一封用于测试邮件存储功能的邮件。",
        "--no-ssl",  # 使用非SSL模式
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print("测试邮件发送成功")
            print(f"输出: {result.stdout}")
            return True
        else:
            print("测试邮件发送失败")
            print(f"错误: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("发送邮件超时")
        return False
    except Exception as e:
        print(f"发送邮件时出错: {e}")
        return False


def check_database_after():
    """检查测试后的数据库状态"""
    print("\n=== 测试后数据库状态 ===")
    db_path = "data/email_db.sqlite"

    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM emails")
        email_count = cursor.fetchone()[0]
        print(f"emails表中的邮件数量: {email_count}")

        # 查找最新的邮件
        cursor.execute(
            """
            SELECT message_id, from_addr, to_addrs, subject, date, size, content_path
            FROM emails
            ORDER BY date DESC
            LIMIT 1
        """
        )
        latest_email = cursor.fetchone()

        if latest_email:
            print(f"\n最新邮件信息:")
            print(f"  ID: {latest_email[0]}")
            print(f"  发件人: {latest_email[1]}")
            print(f"  收件人: {latest_email[2]}")
            print(f"  主题: {latest_email[3]}")
            print(f"  日期: {latest_email[4]}")
            print(f"  大小: {latest_email[5]}")
            print(f"  内容路径: {latest_email[6]}")

            # 检查邮件文件是否存在
            if latest_email[6] and os.path.exists(latest_email[6]):
                print(f"  内容文件: 存在")
                # 读取文件内容的前几行
                try:
                    with open(latest_email[6], "r", encoding="utf-8") as f:
                        content = f.read()
                        lines = content.split("\n")[:10]  # 前10行
                        print(f"  文件内容预览:")
                        for i, line in enumerate(lines, 1):
                            print(f"    {i}: {line}")
                except Exception as e:
                    print(f"  读取文件内容时出错: {e}")
            else:
                print(f"  内容文件: 不存在")

        conn.close()
        return True

    except Exception as e:
        print(f"检查数据库时出错: {e}")
        return False


def cleanup(smtp_process):
    """清理资源"""
    print("\n=== 清理资源 ===")

    if smtp_process:
        try:
            smtp_process.terminate()
            smtp_process.wait(timeout=5)
            print("SMTP服务器已停止")
        except Exception as e:
            print(f"停止SMTP服务器时出错: {e}")


def send_concurrent_emails(num_emails=10, num_threads=5):
    """发送并发邮件测试"""
    print(f"\n=== 并发邮件发送测试 ({num_emails}封邮件, {num_threads}个线程) ===")

    def send_single_email(email_id):
        """发送单封邮件"""
        cmd = [
            "python",
            "examples/send_auth_email.py",
            "--host",
            "localhost",
            "--port",
            "8025",
            "--username",
            "testuser",
            "--password",
            "testpass",
            "--sender",
            f"testuser{email_id}@example.com",
            "--recipient",
            "testuser@example.com",
            "--subject",
            f"并发测试邮件 #{email_id}",
            "--content",
            f"这是第{email_id}封并发测试邮件。",
            "--no-ssl",
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print(f"邮件 #{email_id} 发送成功")
                return True
            else:
                print(f"邮件 #{email_id} 发送失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"邮件 #{email_id} 发送异常: {e}")
            return False

    # 使用线程池并发发送邮件
    start_time = time.time()
    success_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # 提交所有任务
        futures = [
            executor.submit(send_single_email, i) for i in range(1, num_emails + 1)
        ]

        # 等待所有任务完成
        for future in concurrent.futures.as_completed(futures):
            try:
                if future.result():
                    success_count += 1
            except Exception as e:
                print(f"任务执行异常: {e}")

    end_time = time.time()
    duration = end_time - start_time

    print(f"\n并发测试结果:")
    print(f"  总邮件数: {num_emails}")
    print(f"  成功发送: {success_count}")
    print(f"  失败数量: {num_emails - success_count}")
    print(f"  总耗时: {duration:.2f}秒")
    print(f"  平均速度: {num_emails/duration:.2f}封/秒")

    return success_count == num_emails


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="邮件存储功能测试")
    parser.add_argument("--concurrent", action="store_true", help="运行并发测试")
    parser.add_argument("--num-emails", type=int, default=10, help="并发测试邮件数量")
    parser.add_argument("--num-threads", type=int, default=5, help="并发测试线程数")
    parser.add_argument(
        "--optimized", action="store_true", default=True, help="使用优化SMTP服务器"
    )
    parser.add_argument(
        "--standard", dest="optimized", action="store_false", help="使用标准SMTP服务器"
    )
    args = parser.parse_args()

    print("=== 邮件存储功能测试 ===")

    smtp_process = None

    try:
        # 检查测试前的数据库状态
        initial_count = check_database_before()

        # 启动SMTP服务器
        smtp_process = start_smtp_server(args.optimized)
        if not smtp_process:
            print("测试失败：无法启动SMTP服务器")
            return 1

        if args.concurrent:
            # 运行并发测试
            if not send_concurrent_emails(args.num_emails, args.num_threads):
                print("并发测试失败")
                return 1

            # 等待邮件处理
            print("\n等待邮件处理...")
            time.sleep(5)
        else:
            # 发送单封测试邮件
            if not send_test_email():
                print("测试失败：无法发送邮件")
                return 1

            # 等待邮件处理
            print("\n等待邮件处理...")
            time.sleep(3)

        # 检查测试后的数据库状态
        if not check_database_after():
            print("测试失败：无法检查数据库")
            return 1

        print("\n=== 测试完成 ===")
        if args.concurrent:
            print("并发邮件存储功能测试成功！")
        else:
            print("邮件存储功能测试成功！")
        return 0

    except KeyboardInterrupt:
        print("测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        print(f"测试失败：{e}")
        return 1
    finally:
        # 清理资源
        cleanup(smtp_process)


if __name__ == "__main__":
    sys.exit(main())
