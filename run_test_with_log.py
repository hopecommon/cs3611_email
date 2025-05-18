"""
运行测试并将输出重定向到日志文件
"""

import sys
import os
import subprocess
import datetime


def run_test(test_path, log_dir="test_logs"):
    """
    运行测试并将输出重定向到日志文件

    Args:
        test_path: 测试文件路径
        log_dir: 日志目录
    """
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 生成日志文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    test_basename = os.path.basename(test_path)
    # 移除文件扩展名（如果有）
    if test_basename.endswith(".py"):
        test_basename = test_basename[:-3]
    log_file = os.path.join(log_dir, f"{test_basename}_{timestamp}.log")

    # 运行命令并直接将输出重定向到文件
    print(f"运行测试: {test_path}")
    print(f"日志文件: {log_file}")

    with open(log_file, "w", encoding="utf-8") as f:
        # 使用subprocess.Popen捕获输出并写入文件
        process = subprocess.Popen(
            ["python", "-m", "unittest", "-v", test_path],
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return_code = process.wait()

    # 打印日志文件内容
    print("\n日志文件内容:")
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            print(f.read())
    except Exception as e:
        print(f"读取日志文件时出错: {e}")

    return return_code


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python run_test_with_log.py <test_path>")
        sys.exit(1)

    test_path = sys.argv[1]
    sys.exit(run_test(test_path))
