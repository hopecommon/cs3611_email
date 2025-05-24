# -*- coding: utf-8 -*-
"""
命令行工具使用示例脚本

本脚本演示如何使用邮件客户端的命令行工具：
- SMTP命令行工具使用方法
- POP3命令行工具使用方法
- 配置文件的使用
- 常见使用场景和最佳实践

注意：本脚本主要用于演示命令行工具的使用方法，不会实际执行命令。
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging

# 设置日志
logger = setup_logging("cli_example", verbose=True)

# ==================== 配置部分 ====================

# 示例配置文件内容
EXAMPLE_CONFIG = {
    "smtp": {
        "host": "smtp.qq.com",
        "port": 587,
        "ssl_port": 465,
        "use_ssl": True,
        "username": "your@qq.com",
        "password": "your_auth_code"
    },
    "pop3": {
        "host": "pop3.qq.com",
        "port": 110,
        "ssl_port": 995,
        "use_ssl": True,
        "username": "your@qq.com",
        "password": "your_auth_code"
    },
    "save_dir": "examples/emails"
}

def create_example_config():
    """
    创建示例配置文件
    """
    print("=== 创建示例配置文件 ===")
    
    try:
        config_dir = Path("examples/config")
        config_dir.mkdir(exist_ok=True)
        
        config_file = config_dir / "email_config.json"
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(EXAMPLE_CONFIG, f, indent=2, ensure_ascii=False)
        
        print(f"已创建配置文件: {config_file}")
        print("配置文件内容:")
        print(json.dumps(EXAMPLE_CONFIG, indent=2, ensure_ascii=False))
        
        return str(config_file)
        
    except Exception as e:
        logger.error(f"创建配置文件失败: {e}")
        print(f"创建配置文件失败: {e}")
        return None

def demonstrate_smtp_cli_usage():
    """
    演示SMTP命令行工具使用方法
    """
    print("\n=== SMTP命令行工具使用演示 ===")
    
    # 基本命令示例
    basic_commands = [
        {
            "name": "发送简单文本邮件",
            "command": [
                "python", "client/smtp_cli.py",
                "--host", "smtp.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--ask-password",
                "--from", "your@qq.com",
                "--to", "recipient@example.com",
                "--subject", "测试邮件",
                "--body", "这是一封测试邮件"
            ]
        },
        {
            "name": "发送HTML邮件",
            "command": [
                "python", "client/smtp_cli.py",
                "--host", "smtp.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--password", "your_auth_code",
                "--from", "your@qq.com",
                "--from-name", "发件人姓名",
                "--to", "recipient@example.com",
                "--subject", "HTML测试邮件",
                "--body", "<h1>HTML邮件</h1><p>这是<strong>HTML格式</strong>的邮件。</p>",
                "--html"
            ]
        },
        {
            "name": "发送带附件的邮件",
            "command": [
                "python", "client/smtp_cli.py",
                "--host", "smtp.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--ask-password",
                "--from", "your@qq.com",
                "--to", "recipient@example.com",
                "--subject", "带附件的邮件",
                "--body", "请查看附件",
                "--attachment", "examples/test_files/document.pdf",
                "--attachment", "examples/test_files/image.jpg"
            ]
        },
        {
            "name": "使用配置文件发送邮件",
            "command": [
                "python", "client/smtp_cli.py",
                "--config", "examples/config/email_config.json",
                "--from", "your@qq.com",
                "--to", "recipient@example.com",
                "--subject", "配置文件测试",
                "--body", "使用配置文件发送的邮件"
            ]
        },
        {
            "name": "发送高优先级邮件",
            "command": [
                "python", "client/smtp_cli.py",
                "--host", "smtp.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--ask-password",
                "--from", "your@qq.com",
                "--to", "recipient@example.com",
                "--cc", "cc@example.com",
                "--bcc", "bcc@example.com",
                "--subject", "紧急邮件",
                "--body", "这是一封紧急邮件",
                "--priority", "high",
                "--verbose"
            ]
        }
    ]
    
    print("SMTP命令行工具使用示例:")
    for i, example in enumerate(basic_commands, 1):
        print(f"\n{i}. {example['name']}:")
        command_str = " ".join(example["command"])
        print(f"   {command_str}")
        
        # 解释关键参数
        if "--ssl" in example["command"]:
            print("   说明: 使用SSL加密连接")
        if "--ask-password" in example["command"]:
            print("   说明: 运行时提示输入密码")
        if "--html" in example["command"]:
            print("   说明: 邮件内容为HTML格式")
        if "--attachment" in example["command"]:
            print("   说明: 包含附件文件")
        if "--config" in example["command"]:
            print("   说明: 使用配置文件")
        if "--verbose" in example["command"]:
            print("   说明: 显示详细输出信息")

def demonstrate_pop3_cli_usage():
    """
    演示POP3命令行工具使用方法
    """
    print("\n=== POP3命令行工具使用演示 ===")
    
    # 基本命令示例
    basic_commands = [
        {
            "name": "获取邮箱状态",
            "command": [
                "python", "client/pop3_cli.py",
                "--host", "pop3.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--ask-password",
                "--status"
            ]
        },
        {
            "name": "列出所有邮件",
            "command": [
                "python", "client/pop3_cli.py",
                "--host", "pop3.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--password", "your_auth_code",
                "--list"
            ]
        },
        {
            "name": "获取指定邮件",
            "command": [
                "python", "client/pop3_cli.py",
                "--host", "pop3.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--ask-password",
                "--retrieve", "1",
                "--verbose"
            ]
        },
        {
            "name": "获取所有邮件",
            "command": [
                "python", "client/pop3_cli.py",
                "--host", "pop3.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--ask-password",
                "--retrieve-all",
                "--save-dir", "examples/emails/inbox"
            ]
        },
        {
            "name": "使用配置文件获取邮件",
            "command": [
                "python", "client/pop3_cli.py",
                "--config", "examples/config/email_config.json",
                "--retrieve-all",
                "--verbose"
            ]
        },
        {
            "name": "删除指定邮件",
            "command": [
                "python", "client/pop3_cli.py",
                "--host", "pop3.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--ask-password",
                "--delete", "1"
            ]
        },
        {
            "name": "设置超时和重试参数",
            "command": [
                "python", "client/pop3_cli.py",
                "--host", "pop3.qq.com",
                "--ssl",
                "--username", "your@qq.com",
                "--ask-password",
                "--retrieve-all",
                "--timeout", "180",
                "--max-retries", "5",
                "--verbose"
            ]
        }
    ]
    
    print("POP3命令行工具使用示例:")
    for i, example in enumerate(basic_commands, 1):
        print(f"\n{i}. {example['name']}:")
        command_str = " ".join(example["command"])
        print(f"   {command_str}")
        
        # 解释关键参数
        if "--status" in example["command"]:
            print("   说明: 显示邮箱状态（邮件数量和大小）")
        if "--list" in example["command"]:
            print("   说明: 列出所有邮件的编号和大小")
        if "--retrieve" in example["command"]:
            print("   说明: 获取指定编号的邮件")
        if "--retrieve-all" in example["command"]:
            print("   说明: 获取所有邮件")
        if "--delete" in example["command"]:
            print("   说明: 删除指定编号的邮件")
        if "--save-dir" in example["command"]:
            print("   说明: 指定邮件保存目录")
        if "--timeout" in example["command"]:
            print("   说明: 设置连接超时时间")

def demonstrate_advanced_usage():
    """
    演示高级使用场景
    """
    print("\n=== 高级使用场景演示 ===")
    
    advanced_scenarios = [
        {
            "name": "批量发送邮件脚本",
            "description": "使用shell脚本批量发送邮件",
            "script": """
#!/bin/bash
# 批量发送邮件脚本

RECIPIENTS=("user1@example.com" "user2@example.com" "user3@example.com")
SUBJECT="批量通知邮件"
BODY="这是一封批量发送的通知邮件。"

for recipient in "${RECIPIENTS[@]}"; do
    echo "发送邮件给: $recipient"
    python client/smtp_cli.py \\
        --config examples/config/email_config.json \\
        --from your@qq.com \\
        --to "$recipient" \\
        --subject "$SUBJECT" \\
        --body "$BODY"
    
    if [ $? -eq 0 ]; then
        echo "发送成功: $recipient"
    else
        echo "发送失败: $recipient"
    fi
    
    # 避免发送过快
    sleep 2
done
            """
        },
        {
            "name": "邮件备份脚本",
            "description": "定期备份邮件的脚本",
            "script": """
#!/bin/bash
# 邮件备份脚本

BACKUP_DIR="backups/emails/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

echo "开始备份邮件到: $BACKUP_DIR"

python client/pop3_cli.py \\
    --config examples/config/email_config.json \\
    --retrieve-all \\
    --save-dir "$BACKUP_DIR" \\
    --verbose

if [ $? -eq 0 ]; then
    echo "邮件备份完成"
    # 压缩备份文件
    tar -czf "$BACKUP_DIR.tar.gz" -C "backups/emails" "$(basename $BACKUP_DIR)"
    echo "备份文件已压缩: $BACKUP_DIR.tar.gz"
else
    echo "邮件备份失败"
fi
            """
        },
        {
            "name": "邮件监控脚本",
            "description": "监控新邮件并发送通知",
            "script": """
#!/bin/bash
# 邮件监控脚本

LAST_COUNT_FILE="/tmp/email_count.txt"
CURRENT_COUNT=$(python client/pop3_cli.py \\
    --config examples/config/email_config.json \\
    --status | grep "邮件数量" | awk '{print $2}')

if [ -f "$LAST_COUNT_FILE" ]; then
    LAST_COUNT=$(cat "$LAST_COUNT_FILE")
else
    LAST_COUNT=0
fi

echo "$CURRENT_COUNT" > "$LAST_COUNT_FILE"

if [ "$CURRENT_COUNT" -gt "$LAST_COUNT" ]; then
    NEW_EMAILS=$((CURRENT_COUNT - LAST_COUNT))
    echo "发现 $NEW_EMAILS 封新邮件"
    
    # 发送通知邮件
    python client/smtp_cli.py \\
        --config examples/config/email_config.json \\
        --from your@qq.com \\
        --to admin@example.com \\
        --subject "新邮件通知" \\
        --body "您有 $NEW_EMAILS 封新邮件"
fi
            """
        }
    ]
    
    for i, scenario in enumerate(advanced_scenarios, 1):
        print(f"\n{i}. {scenario['name']}:")
        print(f"   描述: {scenario['description']}")
        print(f"   脚本内容:")
        for line in scenario["script"].strip().split("\n"):
            print(f"   {line}")

def demonstrate_configuration_examples():
    """
    演示不同邮件服务商的配置示例
    """
    print("\n=== 不同邮件服务商配置示例 ===")
    
    provider_configs = {
        "QQ邮箱": {
            "smtp": {"host": "smtp.qq.com", "ssl_port": 465, "use_ssl": True},
            "pop3": {"host": "pop3.qq.com", "ssl_port": 995, "use_ssl": True},
            "note": "需要在QQ邮箱设置中开启SMTP/POP3服务并获取授权码"
        },
        "163邮箱": {
            "smtp": {"host": "smtp.163.com", "ssl_port": 465, "use_ssl": True},
            "pop3": {"host": "pop3.163.com", "ssl_port": 995, "use_ssl": True},
            "note": "需要在163邮箱设置中开启SMTP/POP3服务并设置授权码"
        },
        "Gmail": {
            "smtp": {"host": "smtp.gmail.com", "ssl_port": 465, "use_ssl": True},
            "pop3": {"host": "pop3.gmail.com", "ssl_port": 995, "use_ssl": True},
            "note": "需要开启两步验证并生成应用专用密码"
        },
        "Outlook": {
            "smtp": {"host": "smtp-mail.outlook.com", "ssl_port": 587, "use_ssl": True},
            "pop3": {"host": "outlook.office365.com", "ssl_port": 995, "use_ssl": True},
            "note": "可能需要在账户安全设置中允许不太安全的应用"
        }
    }
    
    for provider, config in provider_configs.items():
        print(f"\n{provider} 配置:")
        print(f"  SMTP: {config['smtp']['host']}:{config['smtp']['ssl_port']} (SSL)")
        print(f"  POP3: {config['pop3']['host']}:{config['pop3']['ssl_port']} (SSL)")
        print(f"  注意: {config['note']}")
        
        # 生成对应的命令行示例
        smtp_cmd = f"""python client/smtp_cli.py \\
    --host {config['smtp']['host']} --ssl \\
    --username your@{provider.lower().replace('邮箱', '.com')} --ask-password \\
    --from your@{provider.lower().replace('邮箱', '.com')} \\
    --to recipient@example.com \\
    --subject "测试邮件" --body "测试内容" """
        
        print(f"  SMTP命令示例:")
        for line in smtp_cmd.strip().split("\\\n"):
            print(f"    {line.strip()}")

def demonstrate_troubleshooting():
    """
    演示常见问题排查方法
    """
    print("\n=== 常见问题排查演示 ===")
    
    troubleshooting_tips = [
        {
            "problem": "连接被拒绝 (Connection refused)",
            "solutions": [
                "检查服务器地址和端口是否正确",
                "确认是否需要使用SSL连接",
                "检查网络连接和防火墙设置",
                "使用 --verbose 参数查看详细错误信息"
            ],
            "command": "python client/smtp_cli.py --host smtp.qq.com --ssl --verbose ..."
        },
        {
            "problem": "认证失败 (Authentication failed)",
            "solutions": [
                "确认用户名和密码是否正确",
                "QQ邮箱需要使用授权码而不是QQ密码",
                "检查是否已开启SMTP/POP3服务",
                "尝试不同的认证方法"
            ],
            "command": "python client/smtp_cli.py --username your@qq.com --ask-password ..."
        },
        {
            "problem": "SSL证书验证失败",
            "solutions": [
                "检查系统时间是否正确",
                "更新CA证书",
                "检查服务器证书是否有效",
                "如果是测试环境，可以暂时跳过证书验证"
            ],
            "command": "python client/smtp_cli.py --ssl --verbose ..."
        },
        {
            "problem": "邮件发送成功但收不到",
            "solutions": [
                "检查收件人地址是否正确",
                "查看垃圾邮件文件夹",
                "确认发件人地址是否被列入黑名单",
                "检查邮件服务商的发送限制"
            ],
            "command": "python client/smtp_cli.py --verbose --from verified@domain.com ..."
        },
        {
            "problem": "中文字符显示乱码",
            "solutions": [
                "确保终端支持UTF-8编码",
                "Windows用户可能需要设置代码页",
                "使用 --verbose 参数查看编码信息",
                "检查邮件内容的字符编码"
            ],
            "command": "chcp 65001 && python client/pop3_cli.py --verbose ..."
        }
    ]
    
    for i, tip in enumerate(troubleshooting_tips, 1):
        print(f"\n{i}. 问题: {tip['problem']}")
        print("   解决方案:")
        for j, solution in enumerate(tip['solutions'], 1):
            print(f"     {j}) {solution}")
        print(f"   调试命令: {tip['command']}")

def main():
    """
    主函数 - 演示命令行工具使用方法
    """
    print("命令行工具使用示例")
    print("==================")
    print("本示例演示SMTP和POP3命令行工具的使用方法")
    print()
    
    try:
        # 1. 创建示例配置文件
        config_file = create_example_config()
        
        # 2. SMTP命令行工具演示
        demonstrate_smtp_cli_usage()
        
        # 3. POP3命令行工具演示
        demonstrate_pop3_cli_usage()
        
        # 4. 高级使用场景演示
        demonstrate_advanced_usage()
        
        # 5. 不同邮件服务商配置示例
        demonstrate_configuration_examples()
        
        # 6. 常见问题排查
        demonstrate_troubleshooting()
        
        print("\n命令行工具使用示例演示完成！")
        print("\n使用提示:")
        print("1. 修改配置文件中的邮箱信息")
        print("2. 使用 --help 参数查看完整的命令行选项")
        print("3. 使用 --verbose 参数获取详细的调试信息")
        print("4. 使用 --ask-password 参数安全地输入密码")
        
        if config_file:
            print(f"5. 示例配置文件: {config_file}")
        
    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print(f"执行失败: {e}")

if __name__ == "__main__":
    main()
