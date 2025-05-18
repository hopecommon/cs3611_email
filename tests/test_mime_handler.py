"""
MIME处理模块测试 - 测试MIME编码和解码功能
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import base64

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.models import Attachment
from client.mime_handler import MIMEHandler


class TestMIMEHandler(unittest.TestCase):
    """MIME处理模块测试类"""

    def setUp(self):
        """测试前的准备工作"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试文件
        self.text_file_path = os.path.join(self.temp_dir, "test.txt")
        with open(self.text_file_path, "w", encoding="utf-8") as f:
            f.write("这是测试文本内容。")

        self.binary_file_path = os.path.join(self.temp_dir, "test.bin")
        with open(self.binary_file_path, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04")

    def tearDown(self):
        """测试后的清理工作"""
        # 删除临时目录
        shutil.rmtree(self.temp_dir)

    def test_encode_attachment_text(self):
        """测试编码文本附件"""
        # 编码附件
        attachment = MIMEHandler.encode_attachment(self.text_file_path)

        # 验证
        self.assertEqual(attachment.filename, "test.txt")
        self.assertEqual(attachment.content_type, "text/plain")
        self.assertEqual(attachment.content.decode("utf-8"), "这是测试文本内容。")
        self.assertEqual(attachment.size, len("这是测试文本内容。".encode("utf-8")))

    def test_encode_attachment_binary(self):
        """测试编码二进制附件"""
        # 编码附件
        attachment = MIMEHandler.encode_attachment(self.binary_file_path)

        # 验证
        self.assertEqual(attachment.filename, "test.bin")
        self.assertEqual(attachment.content_type, "application/octet-stream")
        self.assertEqual(attachment.content, b"\x00\x01\x02\x03\x04")
        self.assertEqual(attachment.size, 5)

    def test_encode_attachment_not_found(self):
        """测试编码不存在的附件"""
        # 尝试编码不存在的文件
        with self.assertRaises(FileNotFoundError):
            MIMEHandler.encode_attachment(os.path.join(self.temp_dir, "not_exist.txt"))

    def test_decode_attachment(self):
        """测试解码附件"""
        # 创建测试附件
        content = "这是测试内容。".encode("utf-8")
        attachment = Attachment(
            filename="decoded.txt", content_type="text/plain", content=content
        )

        # 解码附件
        output_path = MIMEHandler.decode_attachment(attachment, self.temp_dir)

        # 验证
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, "rb") as f:
            decoded_content = f.read()
        self.assertEqual(decoded_content, content)

    def test_decode_attachment_duplicate_name(self):
        """测试解码同名附件"""
        # 创建测试附件
        content1 = "内容1".encode("utf-8")
        content2 = "内容2".encode("utf-8")

        attachment1 = Attachment(
            filename="same_name.txt", content_type="text/plain", content=content1
        )

        attachment2 = Attachment(
            filename="same_name.txt", content_type="text/plain", content=content2
        )

        # 解码第一个附件
        path1 = MIMEHandler.decode_attachment(attachment1, self.temp_dir)

        # 解码第二个附件
        path2 = MIMEHandler.decode_attachment(attachment2, self.temp_dir)

        # 验证
        self.assertNotEqual(path1, path2)
        self.assertTrue(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))

        with open(path1, "rb") as f:
            content_1 = f.read()
        with open(path2, "rb") as f:
            content_2 = f.read()

        self.assertEqual(content_1, content1)
        self.assertEqual(content_2, content2)

    def test_get_content_type(self):
        """测试获取内容类型"""
        # 测试已知类型
        self.assertEqual(
            MIMEHandler.get_content_type(self.text_file_path), "text/plain"
        )

        # 测试未知类型
        unknown_path = os.path.join(self.temp_dir, "unknown.xyz")
        with open(unknown_path, "w") as f:
            f.write("unknown")
        self.assertEqual(
            MIMEHandler.get_content_type(unknown_path), "application/octet-stream"
        )

        # 测试常见类型
        common_types = {
            ".html": "text/html",
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".zip": "application/x-zip-compressed",
        }

        for ext, mime_type in common_types.items():
            test_path = os.path.join(self.temp_dir, f"test{ext}")
            with open(test_path, "w") as f:
                f.write("test")
            self.assertEqual(MIMEHandler.get_content_type(test_path), mime_type)

    def test_decode_header_value(self):
        """测试解码头部值"""
        # 测试ASCII
        self.assertEqual(
            MIMEHandler.decode_header_value("Simple ASCII"), "Simple ASCII"
        )

        # 测试编码的头部
        encoded_header = "=?utf-8?b?5Lit5paH5qC85byP?="  # "中文格式" in Base64
        self.assertEqual(MIMEHandler.decode_header_value(encoded_header), "中文格式")

        # 测试混合编码
        mixed_header = "Hello, =?utf-8?b?5Lit5paH?= World"  # "Hello, 中文 World"
        self.assertEqual(
            MIMEHandler.decode_header_value(mixed_header), "Hello, 中文 World"
        )

    def test_encode_header_value(self):
        """测试编码头部值"""
        # 测试ASCII
        self.assertEqual(
            MIMEHandler.encode_header_value("Simple ASCII"), "Simple ASCII"
        )

        # 测试中文
        encoded = MIMEHandler.encode_header_value("中文")
        # 解码回来验证
        self.assertEqual(MIMEHandler.decode_header_value(encoded), "中文")


if __name__ == "__main__":
    unittest.main()
