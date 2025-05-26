#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码一致性审查工具
检测和评估代码分离、重复定义、接口不一致等问题
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging

logger = setup_logging("code_consistency_audit")


class CodeConsistencyAuditor:
    """代码一致性审查器"""

    def __init__(self, project_root: str = None):
        self.project_root = project_root or str(Path(__file__).resolve().parent.parent)
        self.method_definitions = defaultdict(list)
        self.class_definitions = defaultdict(list)
        self.function_signatures = defaultdict(list)
        self.issues = []

    def audit_project(self) -> Dict[str, Any]:
        """审查整个项目的代码一致性"""
        print("🔍 开始代码一致性审查...")

        # 扫描所有Python文件
        python_files = self._find_python_files()
        print(f"📁 找到 {len(python_files)} 个Python文件")

        # 分析每个文件
        for file_path in python_files:
            self._analyze_file(file_path)

        # 检测问题
        self._detect_issues()

        # 生成报告
        report = self._generate_report()

        return report

    def _find_python_files(self) -> List[str]:
        """查找所有Python文件"""
        python_files = []
        exclude_dirs = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "venv",
            "env",
            "node_modules",
        }

        for root, dirs, files in os.walk(self.project_root):
            # 排除特定目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        return python_files

    def _analyze_file(self, file_path: str):
        """分析单个Python文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析AST
            tree = ast.parse(content)

            # 分析类和方法定义
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._analyze_class(node, file_path)
                elif isinstance(node, ast.FunctionDef):
                    self._analyze_function(node, file_path, None)

        except Exception as e:
            logger.warning(f"分析文件 {file_path} 时出错: {e}")

    def _analyze_class(self, class_node: ast.ClassDef, file_path: str):
        """分析类定义"""
        class_name = class_node.name
        self.class_definitions[class_name].append(
            {"file": file_path, "line": class_node.lineno, "methods": []}
        )

        # 分析类中的方法
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                self._analyze_function(node, file_path, class_name)

    def _analyze_function(
        self, func_node: ast.FunctionDef, file_path: str, class_name: str = None
    ):
        """分析函数/方法定义"""
        func_name = func_node.name

        # 提取函数签名
        signature = self._extract_signature(func_node)

        # 记录方法定义
        if class_name:
            method_key = f"{class_name}.{func_name}"
            self.method_definitions[method_key].append(
                {
                    "file": file_path,
                    "line": func_node.lineno,
                    "class": class_name,
                    "signature": signature,
                }
            )

        # 记录函数签名
        self.function_signatures[func_name].append(
            {
                "file": file_path,
                "line": func_node.lineno,
                "class": class_name,
                "signature": signature,
                "full_name": method_key if class_name else func_name,
            }
        )

    def _extract_signature(self, func_node: ast.FunctionDef) -> str:
        """提取函数签名"""
        args = []

        # 处理普通参数
        for arg in func_node.args.args:
            args.append(arg.arg)

        # 处理默认参数
        defaults_start = len(func_node.args.args) - len(func_node.args.defaults)
        for i, default in enumerate(func_node.args.defaults):
            arg_index = defaults_start + i
            if arg_index < len(func_node.args.args):
                arg_name = func_node.args.args[arg_index].arg
                # 简化默认值表示
                args[arg_index] = f"{arg_name}=..."

        # 处理*args
        if func_node.args.vararg:
            args.append(f"*{func_node.args.vararg.arg}")

        # 处理**kwargs
        if func_node.args.kwarg:
            args.append(f"**{func_node.args.kwarg.arg}")

        return f"({', '.join(args)})"

    def _detect_issues(self):
        """检测代码一致性问题"""
        print("🔍 检测代码一致性问题...")

        # 检测重复的方法定义
        self._detect_duplicate_methods()

        # 检测签名不一致的方法
        self._detect_inconsistent_signatures()

        # 检测特定的已知问题模式
        self._detect_known_patterns()

    def _detect_duplicate_methods(self):
        """检测重复的方法定义"""
        for method_name, definitions in self.method_definitions.items():
            if len(definitions) > 1:
                # 检查是否是真正的重复（不同文件中的相同方法）
                files = set(d["file"] for d in definitions)
                if len(files) > 1:
                    self.issues.append(
                        {
                            "type": "duplicate_method",
                            "severity": "high",
                            "method": method_name,
                            "message": f"方法 {method_name} 在多个文件中定义",
                            "locations": [(d["file"], d["line"]) for d in definitions],
                        }
                    )

    def _detect_inconsistent_signatures(self):
        """检测签名不一致的方法"""
        for func_name, signatures in self.function_signatures.items():
            if len(signatures) > 1:
                # 按签名分组
                signature_groups = defaultdict(list)
                for sig_info in signatures:
                    signature_groups[sig_info["signature"]].append(sig_info)

                # 如果有多个不同的签名
                if len(signature_groups) > 1:
                    self.issues.append(
                        {
                            "type": "inconsistent_signature",
                            "severity": "medium",
                            "function": func_name,
                            "message": f"函数/方法 {func_name} 有不一致的签名",
                            "signatures": list(signature_groups.keys()),
                            "locations": [
                                (s["file"], s["line"], s["signature"])
                                for s in signatures
                            ],
                        }
                    )

    def _detect_known_patterns(self):
        """检测已知的问题模式"""
        # 检测 list_sent_emails 类型的问题
        self._detect_layered_method_inconsistency()

    def _detect_layered_method_inconsistency(self):
        """检测分层架构中的方法不一致问题"""
        # 定义需要检查的方法模式
        patterns_to_check = [
            "list_sent_emails",
            "list_emails",
            "get_emails",
            "search_emails",
            "update_email",
            "delete_email",
        ]

        for pattern in patterns_to_check:
            # 查找所有匹配的方法
            matching_methods = []
            for method_name, definitions in self.method_definitions.items():
                if pattern in method_name.lower():
                    matching_methods.extend(definitions)

            # 按类分组
            class_groups = defaultdict(list)
            for method in matching_methods:
                class_name = method.get("class", "global")
                class_groups[class_name].append(method)

            # 检查是否存在分层不一致
            if len(class_groups) > 1:
                signatures = set()
                for methods in class_groups.values():
                    for method in methods:
                        signatures.add(method["signature"])

                if len(signatures) > 1:
                    self.issues.append(
                        {
                            "type": "layered_inconsistency",
                            "severity": "high",
                            "pattern": pattern,
                            "message": f"分层架构中 {pattern} 方法签名不一致",
                            "classes": list(class_groups.keys()),
                            "signatures": list(signatures),
                            "details": class_groups,
                        }
                    )

    def _generate_report(self) -> Dict[str, Any]:
        """生成审查报告"""
        print("📊 生成审查报告...")

        # 按严重程度分类问题
        issues_by_severity = defaultdict(list)
        for issue in self.issues:
            issues_by_severity[issue["severity"]].append(issue)

        # 统计信息
        stats = {
            "total_files": len(self._find_python_files()),
            "total_classes": len(self.class_definitions),
            "total_methods": sum(
                len(defs) for defs in self.method_definitions.values()
            ),
            "total_issues": len(self.issues),
            "issues_by_severity": {
                "high": len(issues_by_severity["high"]),
                "medium": len(issues_by_severity["medium"]),
                "low": len(issues_by_severity["low"]),
            },
        }

        return {
            "stats": stats,
            "issues": self.issues,
            "issues_by_severity": dict(issues_by_severity),
            "method_definitions": dict(self.method_definitions),
            "class_definitions": dict(self.class_definitions),
        }

    def print_report(self, report: Dict[str, Any]):
        """打印审查报告"""
        print("\n" + "=" * 80)
        print("📋 代码一致性审查报告")
        print("=" * 80)

        # 统计信息
        stats = report["stats"]
        print(f"\n📊 统计信息:")
        print(f"   文件数量: {stats['total_files']}")
        print(f"   类数量: {stats['total_classes']}")
        print(f"   方法数量: {stats['total_methods']}")
        print(f"   问题总数: {stats['total_issues']}")

        # 按严重程度显示问题
        severity_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        for severity in ["high", "medium", "low"]:
            count = stats["issues_by_severity"].get(severity, 0)
            if count > 0:
                print(f"   {severity_colors[severity]} {severity.upper()}: {count}")

        # 详细问题列表
        if report["issues"]:
            print(f"\n🔍 详细问题:")
            for i, issue in enumerate(report["issues"], 1):
                severity_icon = severity_colors.get(issue["severity"], "⚪")
                print(
                    f"\n{i}. {severity_icon} [{issue['type'].upper()}] {issue['message']}"
                )

                if issue["type"] == "duplicate_method":
                    print(f"   方法: {issue['method']}")
                    for file_path, line in issue["locations"]:
                        rel_path = os.path.relpath(file_path, self.project_root)
                        print(f"   📁 {rel_path}:{line}")

                elif issue["type"] == "inconsistent_signature":
                    print(f"   函数: {issue['function']}")
                    print(f"   签名变体: {len(issue['signatures'])}")
                    for file_path, line, signature in issue["locations"]:
                        rel_path = os.path.relpath(file_path, self.project_root)
                        print(f"   📁 {rel_path}:{line} -> {signature}")

                elif issue["type"] == "layered_inconsistency":
                    print(f"   模式: {issue['pattern']}")
                    print(f"   涉及类: {', '.join(issue['classes'])}")
                    print(f"   签名变体: {len(issue['signatures'])}")
                    for class_name, methods in issue["details"].items():
                        print(f"   📦 {class_name}:")
                        for method in methods:
                            rel_path = os.path.relpath(
                                method["file"], self.project_root
                            )
                            print(
                                f"      📁 {rel_path}:{method['line']} -> {method['signature']}"
                            )

        # 建议
        print(f"\n💡 修复建议:")
        if stats["issues_by_severity"]["high"] > 0:
            print("   1. 优先修复高严重程度问题（分层架构不一致、重复定义）")
        if stats["issues_by_severity"]["medium"] > 0:
            print("   2. 统一函数/方法签名，确保接口一致性")
        if stats["total_issues"] > 0:
            print("   3. 建立代码审查流程，防止类似问题再次出现")
            print("   4. 考虑使用接口/抽象基类来强制签名一致性")
        else:
            print("   🎉 代码一致性良好，未发现重大问题！")


def create_evaluation_method():
    """创建评估方法文档"""
    evaluation_doc = """
# 代码一致性评估方法

## 问题根源分析

### 为什么会出现代码分离？

1. **分层架构设计**
   - Repository层：数据访问层，直接操作数据库
   - Service层：业务逻辑层，调用Repository层
   - CLI层：用户界面层，调用Service层

2. **历史遗留问题**
   - 多个开发者在不同时期修改代码
   - 缺乏统一的接口规范
   - 重构过程中遗漏某些层级

3. **缺乏自动化检查**
   - 没有接口一致性检查工具
   - 缺乏代码审查流程
   - 测试覆盖不全面

## 评估方法

### 1. 自动化代码审查
```bash
# 运行代码一致性审查工具
python tools/code_consistency_audit.py
```

### 2. 手动检查清单
- [ ] 检查所有同名方法的签名是否一致
- [ ] 验证分层架构中的接口传递是否正确
- [ ] 确认CLI层是否正确调用Service层方法
- [ ] 检查是否有遗漏的参数传递

### 3. 测试验证
- [ ] 单元测试覆盖所有层级
- [ ] 集成测试验证端到端功能
- [ ] 回归测试确保修复不引入新问题

### 4. 代码质量指标
- 接口一致性：同名方法签名匹配率
- 分层完整性：参数传递链完整性
- 测试覆盖率：关键功能测试覆盖率

## 预防措施

### 1. 开发规范
- 定义统一的接口规范
- 使用抽象基类强制接口一致性
- 建立代码审查流程

### 2. 自动化工具
- 集成代码一致性检查到CI/CD
- 使用类型提示增强接口约束
- 定期运行代码质量检查

### 3. 文档管理
- 维护API文档
- 记录接口变更历史
- 提供开发指南

## 修复优先级

1. **高优先级**：分层架构不一致、重复定义
2. **中优先级**：签名不一致、参数遗漏
3. **低优先级**：代码风格、命名规范
"""

    with open("docs/code_consistency_evaluation.md", "w", encoding="utf-8") as f:
        f.write(evaluation_doc)

    print("📝 已创建评估方法文档: docs/code_consistency_evaluation.md")


def main():
    """主函数"""
    print("🔍 代码一致性审查工具")
    print("=" * 50)

    # 创建审查器
    auditor = CodeConsistencyAuditor()

    # 执行审查
    report = auditor.audit_project()

    # 打印报告
    auditor.print_report(report)

    # 创建评估方法文档
    create_evaluation_method()

    # 保存详细报告
    import json

    with open("logs/code_consistency_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📄 详细报告已保存到: logs/code_consistency_report.json")

    return len(report["issues"]) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
