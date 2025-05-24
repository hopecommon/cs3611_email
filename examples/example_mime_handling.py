# -*- coding: utf-8 -*-
"""
MIME处理示例脚本

本脚本演示如何使用MIME处理模块：
- 附件编码和解码
- .eml文件的解析和生成
- 邮件头部编码/解码
- MIME类型检测
- 复杂邮件结构处理

使用前请确保有测试文件和.eml文件。
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client.mime_handler import MIMEHandler
from common.models import Email, EmailAddress, Attachment, EmailPriority
from common.utils import setup_logging, generate_message_id

# 设置日志
logger = setup_logging("mime_example", verbose=True)

# ==================== 配置部分 ====================

# 测试文件目录
TEST_DIR = Path("examples/test_files")
OUTPUT_DIR = Path("examples/output")


def setup_test_environment():
    """
    设置测试环境，创建必要的目录和测试文件
    """
    print("=== 设置测试环境 ===")

    # 创建目录
    TEST_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 创建测试文件
    test_files = {
        "sample.txt": "这是一个示例文本文件。\n包含中文内容测试。\n创建时间: "
        + str(datetime.now()),
        "data.json": '{\n  "name": "测试数据",\n  "value": 123,\n  "timestamp": "'
        + str(datetime.now())
        + '"\n}',
        "readme.md": "# 测试文档\n\n这是一个**Markdown**文件。\n\n- 项目1\n- 项目2\n- 项目3\n",
    }

    for filename, content in test_files.items():
        file_path = TEST_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"创建测试文件: {file_path}")

    print("测试环境设置完成\n")


def demonstrate_attachment_encoding():
    """
    演示附件编码功能
    """
    print("=== 附件编码演示 ===")

    try:
        # 获取测试文件列表
        test_files = list(TEST_DIR.glob("*"))

        if not test_files:
            print("没有找到测试文件，请先运行setup_test_environment()")
            return

        attachments = []

        for file_path in test_files:
            if file_path.is_file():
                print(f"\n处理文件: {file_path.name}")

                # 编码为附件
                attachment = MIMEHandler.encode_attachment(str(file_path))
                attachments.append(attachment)

                print(f"  文件名: {attachment.filename}")
                print(f"  MIME类型: {attachment.content_type}")
                print(f"  大小: {attachment.size} 字节")

                # 验证内容
                if attachment.content_type.startswith("text/"):
                    try:
                        content_preview = attachment.content[:100].decode(
                            "utf-8", errors="replace"
                        )
                        if len(attachment.content) > 100:
                            content_preview += "..."
                        print(f"  内容预览: {content_preview}")
                    except:
                        print(f"  内容: 二进制数据")

        print(f"\n总共编码了 {len(attachments)} 个附件")
        return attachments

    except Exception as e:
        logger.error(f"附件编码演示失败: {e}")
        print(f"编码失败: {e}")
        return []


def demonstrate_attachment_decoding(attachments):
    """
    演示附件解码功能

    Args:
        attachments: 附件列表
    """
    print("\n=== 附件解码演示 ===")

    try:
        if not attachments:
            print("没有附件可解码")
            return

        # 创建解码输出目录
        decode_dir = OUTPUT_DIR / "decoded_attachments"
        decode_dir.mkdir(exist_ok=True)

        for i, attachment in enumerate(attachments, 1):
            print(f"\n解码附件 {i}: {attachment.filename}")

            # 解码附件
            saved_path = MIMEHandler.decode_attachment(attachment, str(decode_dir))
            print(f"  已保存到: {saved_path}")

            # 验证解码结果
            if os.path.exists(saved_path):
                file_size = os.path.getsize(saved_path)
                print(f"  文件大小: {file_size} 字节")

                # 如果是文本文件，显示内容
                if attachment.content_type.startswith("text/"):
                    try:
                        with open(saved_path, "r", encoding="utf-8") as f:
                            content = f.read(200)
                            if len(content) == 200:
                                content += "..."
                            print(f"  内容预览: {content}")
                    except Exception as e:
                        print(f"  读取内容失败: {e}")

        print(f"\n所有附件已解码到: {decode_dir}")

    except Exception as e:
        logger.error(f"附件解码演示失败: {e}")
        print(f"解码失败: {e}")


def demonstrate_eml_creation():
    """
    演示.eml文件创建功能
    """
    print("\n=== .eml文件创建演示 ===")

    try:
        # 创建一个复杂的邮件对象
        email = Email(
            message_id=generate_message_id(),
            subject="MIME处理测试邮件",
            from_addr=EmailAddress(name="发件人测试", address="sender@example.com"),
            to_addrs=[
                EmailAddress(name="收件人1", address="recipient1@example.com"),
                EmailAddress(name="收件人2", address="recipient2@example.com"),
            ],
            cc_addrs=[EmailAddress(name="抄送人", address="cc@example.com")],
            text_content="这是一封测试邮件的纯文本内容。\n\n包含中文字符测试。",
            html_content="""
            <html>
            <head><meta charset="utf-8"><title>测试邮件</title></head>
            <body>
                <h1>MIME处理测试</h1>
                <p>这是一封<strong>HTML格式</strong>的测试邮件。</p>
                <p>包含<em>中文字符</em>测试。</p>
                <ul>
                    <li>功能1: 附件处理</li>
                    <li>功能2: 编码解码</li>
                    <li>功能3: .eml文件生成</li>
                </ul>
            </body>
            </html>
            """,
            date=datetime.now(),
            priority=EmailPriority.HIGH,
        )

        # 添加附件
        test_files = list(TEST_DIR.glob("*.txt"))
        if test_files:
            attachment = MIMEHandler.encode_attachment(str(test_files[0]))
            email.attachments = [attachment]
            print(f"添加附件: {attachment.filename}")

        # 保存为.eml文件
        eml_path = OUTPUT_DIR / "test_email.eml"
        MIMEHandler.save_as_eml(email, str(eml_path))

        print(f"已创建.eml文件: {eml_path}")

        # 显示文件信息
        if eml_path.exists():
            file_size = eml_path.stat().st_size
            print(f"文件大小: {file_size} 字节")

            # 显示文件头部内容
            with open(eml_path, "r", encoding="utf-8") as f:
                header_lines = []
                for line in f:
                    if line.strip() == "":
                        break
                    header_lines.append(line.strip())
                    if len(header_lines) >= 10:  # 只显示前10行头部
                        break

                print("\n.eml文件头部内容:")
                for line in header_lines:
                    print(f"  {line}")
                if len(header_lines) >= 10:
                    print("  ...")

        return str(eml_path)

    except Exception as e:
        logger.error(f".eml文件创建失败: {e}")
        print(f"创建失败: {e}")
        return None


def demonstrate_eml_parsing(eml_path):
    """
    演示.eml文件解析功能

    Args:
        eml_path: .eml文件路径
    """
    print("\n=== .eml文件解析演示 ===")

    try:
        if not eml_path or not os.path.exists(eml_path):
            print("没有.eml文件可解析")
            return

        print(f"解析文件: {eml_path}")

        # 解析.eml文件
        email = MIMEHandler.parse_eml_file(eml_path)

        print(f"\n解析结果:")
        print(f"  主题: {email.subject or '(无主题)'}")

        # 安全地处理发件人信息
        if email.from_addr:
            from_name = email.from_addr.name or ""
            from_address = email.from_addr.address or "unknown@localhost"
            print(f"  发件人: {from_name} <{from_address}>")
        else:
            print("  发件人: (未知发件人)")

        print(f"  收件人数量: {len(email.to_addrs) if email.to_addrs else 0}")
        if email.to_addrs:
            for i, addr in enumerate(email.to_addrs, 1):
                if addr:
                    addr_name = addr.name or ""
                    addr_address = addr.address or ""
                    print(f"    {i}. {addr_name} <{addr_address}>")

        if email.cc_addrs:
            print(f"  抄送数量: {len(email.cc_addrs)}")
            for i, addr in enumerate(email.cc_addrs, 1):
                if addr:
                    addr_name = addr.name or ""
                    addr_address = addr.address or ""
                    print(f"    {i}. {addr_name} <{addr_address}>")

        print(f"  日期: {email.date}")
        print(f"  Message-ID: {email.message_id}")

        # 内容信息
        if email.text_content:
            print(f"  纯文本内容: {len(email.text_content)} 字符")
            preview = email.text_content[:100].replace("\n", " ")
            if len(email.text_content) > 100:
                preview += "..."
            print(f"    预览: {preview}")

        if email.html_content:
            print(f"  HTML内容: {len(email.html_content)} 字符")

        # 附件信息
        if email.attachments:
            print(f"  附件数量: {len(email.attachments)}")
            for i, attachment in enumerate(email.attachments, 1):
                print(
                    f"    {i}. {attachment.filename} ({attachment.content_type}, {attachment.size} 字节)"
                )

    except Exception as e:
        logger.error(f".eml文件解析失败: {e}")
        print(f"解析失败: {e}")


def demonstrate_header_encoding():
    """
    演示邮件头部编码/解码功能
    """
    print("\n=== 邮件头部编码/解码演示 ===")

    try:
        # 测试各种需要编码的头部值
        test_headers = [
            "简单的英文主题",
            "包含中文的主题测试",
            "Mixed English and 中文 subject",
            "特殊字符: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "很长的主题" * 10,  # 测试长主题
        ]

        print("头部编码测试:")
        encoded_headers = []

        for i, header in enumerate(test_headers, 1):
            print(f"\n{i}. 原始: {header}")

            # 编码
            encoded = MIMEHandler.encode_header_value(header)
            encoded_headers.append(encoded)
            print(f"   编码: {encoded}")

            # 解码验证
            decoded = MIMEHandler.decode_header_value(encoded)
            print(f"   解码: {decoded}")

            # 验证往返编码是否正确
            if decoded == header:
                print(f"   状态: 编码/解码成功")
            else:
                print(f"   状态: 编码/解码不匹配!")

        # 测试已编码的头部解码
        print(f"\n预编码头部解码测试:")
        pre_encoded_headers = [
            "=?UTF-8?B?5Lit5paH5Li76aKY?=",  # "中文主题"的Base64编码
            "=?UTF-8?Q?Test_=E4=B8=AD=E6=96=87?=",  # "Test 中文"的Quoted-Printable编码
        ]

        for i, encoded_header in enumerate(pre_encoded_headers, 1):
            print(f"{i}. 编码: {encoded_header}")
            decoded = MIMEHandler.decode_header_value(encoded_header)
            print(f"   解码: {decoded}")

    except Exception as e:
        logger.error(f"头部编码/解码演示失败: {e}")
        print(f"编码/解码失败: {e}")


def demonstrate_mime_type_detection():
    """
    演示MIME类型检测功能
    """
    print("\n=== MIME类型检测演示 ===")

    try:
        # 测试文件扩展名
        test_extensions = [
            "document.txt",
            "image.jpg",
            "archive.zip",
            "video.mp4",
            "audio.mp3",
            "webpage.html",
            "data.json",
            "script.py",
            "document.pdf",
            "spreadsheet.xlsx",
            "unknown.xyz",
        ]

        print("文件类型检测:")
        for filename in test_extensions:
            mime_type = MIMEHandler.get_content_type(filename)
            print(f"  {filename:<20} -> {mime_type}")

        # 测试实际文件
        print(f"\n实际文件类型检测:")
        test_files = list(TEST_DIR.glob("*"))
        for file_path in test_files:
            if file_path.is_file():
                mime_type = MIMEHandler.get_content_type(str(file_path))
                print(f"  {file_path.name:<20} -> {mime_type}")

    except Exception as e:
        logger.error(f"MIME类型检测演示失败: {e}")
        print(f"类型检测失败: {e}")


def cleanup_test_environment():
    """
    清理测试环境
    """
    print("\n=== 清理测试环境 ===")

    try:
        import shutil

        # 删除测试目录
        if TEST_DIR.exists():
            shutil.rmtree(TEST_DIR)
            print(f"已删除测试目录: {TEST_DIR}")

        # 保留输出目录，用户可能需要查看结果
        print(f"输出目录保留: {OUTPUT_DIR}")
        print("如需清理输出目录，请手动删除")

    except Exception as e:
        logger.error(f"清理测试环境失败: {e}")
        print(f"清理失败: {e}")


def main():
    """
    主函数 - 演示各种MIME处理功能
    """
    print("MIME处理示例")
    print("============")
    print()

    try:
        # 1. 设置测试环境
        setup_test_environment()

        # 2. 附件编码演示
        attachments = demonstrate_attachment_encoding()

        # 3. 附件解码演示
        demonstrate_attachment_decoding(attachments)

        # 4. .eml文件创建演示
        eml_path = demonstrate_eml_creation()

        # 5. .eml文件解析演示
        demonstrate_eml_parsing(eml_path)

        # 6. 邮件头部编码/解码演示
        demonstrate_header_encoding()

        # 7. MIME类型检测演示
        demonstrate_mime_type_detection()

        print("\n所有示例执行完成！")
        print(f"输出目录: {OUTPUT_DIR}")

        # 询问是否清理测试环境
        try:
            response = input("\n是否清理测试文件? (y/N): ").strip().lower()
            if response in ["y", "yes"]:
                cleanup_test_environment()
        except:
            pass  # 忽略输入错误

    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print(f"执行失败: {e}")


if __name__ == "__main__":
    main()
