"""
运行所有测试 - 全面测试邮件客户端功能
"""

import sys
import os
import unittest
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

def run_tests(test_modules=None, verbose=False):
    """
    运行指定的测试模块
    
    Args:
        test_modules: 要运行的测试模块列表，如果为None则运行所有测试
        verbose: 是否显示详细输出
    """
    # 所有可用的测试模块
    all_test_modules = {
        "auth": "tests.test_auth_basic",
        "auth_comprehensive": "tests.test_auth_comprehensive",
        "smtp": "tests.test_smtp_send",
        "pop3": "tests.test_pop3_receive",
        "storage": "tests.test_storage"
    }
    
    # 如果没有指定测试模块，则运行所有测试
    if not test_modules:
        test_modules = list(all_test_modules.keys())
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加指定的测试模块
    for module_name in test_modules:
        if module_name in all_test_modules:
            try:
                # 导入测试模块
                module = __import__(all_test_modules[module_name], fromlist=["*"])
                # 添加模块中的所有测试
                suite.addTest(loader.loadTestsFromModule(module))
                print(f"已添加测试模块: {module_name}")
            except ImportError as e:
                print(f"无法导入测试模块 {module_name}: {e}")
        else:
            print(f"未知的测试模块: {module_name}")
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行邮件客户端功能测试")
    parser.add_argument("--modules", nargs="+", choices=["auth", "auth_comprehensive", "smtp", "pop3", "storage", "all"],
                        help="要运行的测试模块，可选值: auth, auth_comprehensive, smtp, pop3, storage, all")
    parser.add_argument("--verbose", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    # 处理测试模块参数
    test_modules = args.modules
    if test_modules and "all" in test_modules:
        test_modules = None  # 运行所有测试
    
    # 运行测试
    success = run_tests(test_modules, args.verbose)
    
    # 设置退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
