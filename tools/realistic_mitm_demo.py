# -*- coding: utf-8 -*-
"""
真实中间人攻击演示工具 - 基于现有邮件系统

主要改进：
1. 使用项目现有的SMTP服务器和客户端
2. 真实网络环境模拟（独立进程通信）
3. 完整的SSL/TLS加密对比演示
4. 真实数据包拦截和分析
5. 严格端口管理（SSL使用标准端口，非SSL使用非标准端口）
6. 真实私钥泄露场景演示
7. 原始数据保存和解密展示

⚠️ 仅用于教学目的！请勿用于非法活动！
"""

import sys
import os
import ssl
import socket
import threading
import time
import base64
import subprocess
import json
import argparse
from datetime import datetime
from pathlib import Path
import signal
import re

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import SSL_CERT_FILE, SSL_KEY_FILE
from server.smtp_server import StableSMTPServer
from client.smtp_client import SMTPClient
from common.models import Email, EmailAddress

logger = setup_logging("realistic_mitm", verbose=True)

# 端口配置 - 严格遵循标准
PORTS = {
    "smtp_plain": 8025,  # 非SSL SMTP - 非标准端口
    "smtp_ssl": 465,  # SSL SMTP - 标准端口
    "mitm_smtp_plain": 8026,  # MITM代理端口
    "mitm_smtp_ssl": 8466,  # MITM SSL代理端口
}

# 数据保存目录
DATA_DIR = Path(__file__).parent / "mitm_data"
DATA_DIR.mkdir(exist_ok=True)


class 网络流量分析器:
    """真实网络流量分析器"""

    def __init__(self):
        self.拦截数据包 = []
        self.加密样本 = {}
        self.原始数据文件 = (
            DATA_DIR / f"拦截数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

    def 分析数据包(self, data: bytes, direction: str, protocol: str) -> dict:
        """分析数据包"""
        时间戳 = datetime.now().isoformat()
        数据包信息 = {
            "时间戳": 时间戳,
            "方向": direction,
            "协议": protocol,
            "大小": len(data),
            "原始数据样本": data[:100].hex() if len(data) > 0 else "",
        }

        # SSL/TLS检测
        if self._是否为tls握手(data):
            数据包信息["类型"] = "TLS握手"
            数据包信息["tls版本"] = self._提取tls版本(data)
        elif self._是否为tls应用数据(data):
            数据包信息["类型"] = "TLS应用数据"
            数据包信息["已加密"] = True
            # 保存加密数据样本
            self.加密样本[时间戳] = {
                "数据": data[:200],  # 保存前200字节
                "完整大小": len(data),
            }
        elif self._是否为smtp命令(data):
            数据包信息["类型"] = "SMTP明文"
            数据包信息["已加密"] = False
            # 尝试解析SMTP命令
            try:
                文本 = data.decode("utf-8", errors="ignore")
                数据包信息["内容"] = 文本[:200]  # 保存前200字符
                数据包信息["敏感信息"] = self._检测敏感信息(文本)
                # 尝试解码base64数据
                数据包信息["解码结果"] = self._尝试解码数据(文本)
            except:
                数据包信息["内容"] = "无法解码"
        else:
            数据包信息["类型"] = "未知"

        self.拦截数据包.append(数据包信息)

        # 保存原始数据到文件
        self._保存原始数据(数据包信息, data)

        return 数据包信息

    def _保存原始数据(self, 数据包信息: dict, 原始数据: bytes):
        """保存原始数据到文件"""
        try:
            with open(self.原始数据文件, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"时间戳: {数据包信息['时间戳']}\n")
                f.write(f"方向: {数据包信息['方向']}\n")
                f.write(f"协议: {数据包信息['协议']}\n")
                f.write(f"类型: {数据包信息['类型']}\n")
                f.write(f"大小: {数据包信息['大小']} 字节\n")

                if 数据包信息.get("已加密", False):
                    f.write(f"加密数据(HEX): {原始数据.hex()}\n")
                    f.write(f"加密数据(RAW): {repr(原始数据)}\n")
                else:
                    f.write(f"原始数据(HEX): {原始数据.hex()}\n")
                    f.write(
                        f"原始数据(UTF-8): {原始数据.decode('utf-8', errors='ignore')}\n"
                    )

                    if "解码结果" in 数据包信息:
                        解码结果 = 数据包信息["解码结果"]
                        if 解码结果["认证信息"]:
                            f.write(f"🔓 认证信息已破解:\n")
                            for 结果 in 解码结果["认证信息"]:
                                if "用户名" in 结果 and "密码" in 结果:
                                    f.write(
                                        f"    🔓 {结果['类型']}: 用户名='{结果['用户名']}', 密码='{结果['密码']}'\n"
                                    )
                                else:
                                    f.write(f"    🔓 {结果['类型']}: {结果['解码']}\n")

                        if 解码结果["邮件内容"]:
                            f.write(f"📧 邮件内容已解码:\n")
                            for 结果 in 解码结果["邮件内容"]:
                                f.write(
                                    f"    📧 {结果['类型']}: {结果['解码'][:50]}...\n"
                                )

                        if 解码结果["其他敏感信息"]:
                            f.write(f"⚠️ 其他敏感信息:\n")
                            for 结果 in 解码结果["其他敏感信息"]:
                                f.write(
                                    f"    ⚠️ {结果['类型']}: {结果['内容'][:50]}...\n"
                                )

                f.write(f"{'='*60}\n")
        except Exception as e:
            logger.debug(f"保存原始数据失败: {e}")

    def _尝试解码数据(self, 文本: str) -> dict:
        """智能解码数据 - 只解码真正有意义的编码数据"""
        解码结果 = {"认证信息": [], "邮件内容": [], "其他敏感信息": []}

        # 1. 专门查找SMTP认证相关的Base64数据
        self._解析smtp认证数据(文本, 解码结果)

        # 2. 查找邮件头部的编码信息
        self._解析邮件头部编码(文本, 解码结果)

        # 3. 查找邮件正文的Base64编码
        self._解析邮件正文编码(文本, 解码结果)

        # 4. 查找其他明文敏感信息
        self._查找明文敏感信息(文本, 解码结果)

        return 解码结果

    def _解析smtp认证数据(self, 文本: str, 解码结果: dict):
        """解析SMTP认证数据"""
        # AUTH PLAIN 命令的Base64数据
        auth_plain_pattern = r"AUTH\s+PLAIN\s+([A-Za-z0-9+/=]{8,})"
        plain_matches = re.findall(auth_plain_pattern, 文本, re.IGNORECASE)

        for match in plain_matches:
            try:
                decoded = base64.b64decode(match).decode("utf-8")
                # PLAIN认证格式: \x00username\x00password
                if "\x00" in decoded:
                    parts = decoded.split("\x00")
                    if len(parts) >= 3:
                        解码结果["认证信息"].append(
                            {
                                "类型": "SMTP PLAIN认证",
                                "原始": match[:20] + "...",
                                "用户名": parts[1] if parts[1] else "(空)",
                                "密码": parts[2] if parts[2] else "(空)",
                                "威胁级别": "极高",
                            }
                        )
            except:
                pass

        # AUTH LOGIN 命令的Base64数据 (通常是用户名)
        auth_login_pattern = r"AUTH\s+LOGIN\s+([A-Za-z0-9+/=]{4,})"
        login_matches = re.findall(auth_login_pattern, 文本, re.IGNORECASE)

        for match in login_matches:
            try:
                decoded = base64.b64decode(match).decode("utf-8")
                # 验证是否是合理的用户名格式
                if self._是否为合理用户名(decoded):
                    解码结果["认证信息"].append(
                        {
                            "类型": "SMTP LOGIN用户名",
                            "原始": match,
                            "解码": decoded,
                            "威胁级别": "高",
                        }
                    )
            except:
                pass

    def _解析邮件头部编码(self, 文本: str, 解码结果: dict):
        """解析邮件头部的RFC2047编码"""
        # RFC 2047编码格式: =?charset?encoding?encoded-text?=
        rfc2047_pattern = r"=\?([^?]+)\?([BQ])\?([^?]+)\?="
        rfc_matches = re.findall(rfc2047_pattern, 文本, re.IGNORECASE)

        for charset, encoding, encoded_text in rfc_matches:
            try:
                if encoding.upper() == "B":  # Base64编码
                    decoded = base64.b64decode(encoded_text).decode(charset)
                    # 验证解码结果是否有意义
                    if self._是否为有意义文本(decoded):
                        解码结果["邮件内容"].append(
                            {
                                "类型": "邮件头部编码",
                                "字符集": charset,
                                "编码方式": "Base64",
                                "原始": encoded_text[:30] + "...",
                                "解码": decoded,
                                "威胁级别": "中",
                            }
                        )
                elif encoding.upper() == "Q":  # Quoted-Printable编码
                    # 这里可以添加QP解码逻辑
                    pass
            except:
                pass

    def _解析邮件正文编码(self, 文本: str, 解码结果: dict):
        """解析邮件正文中的Base64编码"""
        # 查找邮件正文中的Base64编码块（通常很长且独立成行）
        lines = 文本.split("\n")
        for line in lines:
            line = line.strip()
            # 检查是否是纯Base64行（长度合理且字符集匹配）
            if self._是否为base64行(line):
                try:
                    decoded = base64.b64decode(line).decode("utf-8", errors="ignore")
                    if self._是否为有意义文本(decoded) and len(decoded) > 5:
                        解码结果["邮件内容"].append(
                            {
                                "类型": "邮件正文内容",
                                "编码方式": "Base64",
                                "原始": line[:30] + "...",
                                "解码": decoded[:100]
                                + ("..." if len(decoded) > 100 else ""),
                                "威胁级别": "高",
                            }
                        )
                except:
                    pass

    def _查找明文敏感信息(self, 文本: str, 解码结果: dict):
        """查找明文中的敏感信息"""
        敏感模式 = [
            (r"MAIL FROM:<([^>]+)>", "发件人地址"),
            (r"RCPT TO:<([^>]+)>", "收件人地址"),
            (r"Subject:\s*(.+)", "邮件主题"),
            (r"From:\s*(.+)", "发件人信息"),
            (r"To:\s*(.+)", "收件人信息"),
        ]

        for 模式, 类型 in 敏感模式:
            matches = re.findall(模式, 文本, re.IGNORECASE)
            for match in matches:
                if match.strip() and not match.startswith("=?"):  # 排除已编码的内容
                    解码结果["其他敏感信息"].append(
                        {"类型": 类型, "内容": match.strip()[:100], "威胁级别": "中"}
                    )

    def _是否为合理用户名(self, text: str) -> bool:
        """检查是否为合理的用户名格式"""
        # 用户名通常是3-30个字符，包含字母数字和常见符号
        if not (3 <= len(text) <= 30):
            return False
        return re.match(r"^[a-zA-Z0-9._@-]+$", text) is not None

    def _是否为有意义文本(self, text: str) -> bool:
        """检查解码结果是否为有意义的文本"""
        if not text or len(text.strip()) < 2:
            return False

        # 检查是否包含太多非打印字符
        printable_ratio = sum(1 for c in text if c.isprintable()) / len(text)
        if printable_ratio < 0.7:
            return False

        # 检查是否包含常见的中文、英文字符
        has_meaningful_chars = bool(re.search(r"[\u4e00-\u9fff\w\s]", text))
        return has_meaningful_chars

    def _是否为base64行(self, line: str) -> bool:
        """检查是否为Base64编码行"""
        # 去除空白字符
        line = line.strip()

        # 长度检查：太短的不太可能是有意义的Base64
        if len(line) < 16:
            return False

        # 字符集检查：只包含Base64字符
        if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", line):
            return False

        # 长度必须是4的倍数
        if len(line) % 4 != 0:
            return False

        # 等号只能出现在末尾
        if "=" in line[:-2]:
            return False

        return True

    def _是否为tls握手(self, data: bytes) -> bool:
        """检测TLS握手"""
        return (
            len(data) >= 3
            and data[0] == 0x16
            and data[1:3] in [b"\x03\x01", b"\x03\x02", b"\x03\x03"]
        )

    def _是否为tls应用数据(self, data: bytes) -> bool:
        """检测TLS应用数据"""
        return len(data) >= 3 and data[0] == 0x17

    def _是否为smtp命令(self, data: bytes) -> bool:
        """检测SMTP命令"""
        try:
            text = data.decode("utf-8", errors="ignore").upper()
            smtp_commands = [
                "HELO",
                "EHLO",
                "AUTH",
                "MAIL FROM",
                "RCPT TO",
                "DATA",
                "SUBJECT:",
                "FROM:",
                "TO:",
            ]
            return any(cmd in text for cmd in smtp_commands)
        except:
            return False

    def _提取tls版本(self, data: bytes) -> str:
        """提取TLS版本"""
        if len(data) >= 3:
            version = (data[1] << 8) | data[2]
            versions = {
                0x0301: "TLS 1.0",
                0x0302: "TLS 1.1",
                0x0303: "TLS 1.2",
                0x0304: "TLS 1.3",
            }
            return versions.get(version, f"未知(0x{version:04x})")
        return "未知"

    def _检测敏感信息(self, text: str) -> list:
        """检测敏感信息"""
        敏感信息 = []
        text_lower = text.lower()

        if "auth" in text_lower:
            敏感信息.append("认证信息")
        if "password" in text_lower:
            敏感信息.append("密码")
        if "subject:" in text_lower:
            敏感信息.append("邮件主题")
        if any(
            keyword in text_lower
            for keyword in ["confidential", "secret", "机密", "秘密"]
        ):
            敏感信息.append("机密内容")

        return 敏感信息


class 真实MITM代理:
    """真实MITM代理 - 基于现有项目组件"""

    def __init__(
        self, listen_port: int, target_host: str, target_port: int, is_ssl: bool = False
    ):
        self.监听端口 = listen_port
        self.目标主机 = target_host
        self.目标端口 = target_port
        self.是否ssl = is_ssl
        self.运行中 = False
        self.服务器套接字 = None
        self.分析器 = 网络流量分析器()
        self.连接计数 = 0

    def 启动(self):
        """启动代理"""
        try:
            self.运行中 = True
            self.服务器套接字 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.服务器套接字.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.服务器套接字.settimeout(1.0)
            self.服务器套接字.bind(("localhost", self.监听端口))
            self.服务器套接字.listen(5)

            协议类型 = "SSL" if self.是否ssl else "明文"
            print(
                f"MITM代理已启动 [{协议类型}]: 监听端口 {self.监听端口} -> 目标 {self.目标主机}:{self.目标端口}"
            )

            while self.运行中:
                try:
                    客户端套接字, 地址 = self.服务器套接字.accept()
                    self.连接计数 += 1
                    print(f"[{协议类型}] 拦截到连接 #{self.连接计数}: {地址}")

                    线程 = threading.Thread(
                        target=self._处理连接,
                        args=(客户端套接字, 地址, 协议类型),
                    )
                    线程.daemon = True
                    线程.start()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.运行中:
                        logger.error(f"代理错误: {e}")
                    break

        except Exception as e:
            print(f"启动代理失败: {e}")
        finally:
            self.停止()

    def _处理连接(self, 客户端套接字, 客户端地址, 协议类型):
        """处理连接"""
        目标套接字 = None
        连接标识 = f"{协议类型}_{self.连接计数}"

        try:
            # 连接到目标服务器
            目标套接字 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            目标套接字.settimeout(10)
            目标套接字.connect((self.目标主机, self.目标端口))

            print(f"[{连接标识}] 已连接到目标服务器")

            # 创建双向转发
            客户端到服务器 = threading.Thread(
                target=self._转发数据,
                args=(客户端套接字, 目标套接字, "客户端->服务器", 连接标识),
            )
            服务器到客户端 = threading.Thread(
                target=self._转发数据,
                args=(目标套接字, 客户端套接字, "服务器->客户端", 连接标识),
            )

            客户端到服务器.daemon = True
            服务器到客户端.daemon = True

            客户端到服务器.start()
            服务器到客户端.start()

            客户端到服务器.join(timeout=30)
            服务器到客户端.join(timeout=30)

        except Exception as e:
            print(f"[{连接标识}] 连接处理失败: {e}")
        finally:
            for sock in [客户端套接字, 目标套接字]:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass

    def _转发数据(self, 源, 目标, 方向, 连接标识):
        """转发数据并分析"""
        数据包计数 = 0

        try:
            while self.运行中:
                try:
                    数据 = 源.recv(4096)
                    if not 数据:
                        break

                    数据包计数 += 1

                    # 分析数据包
                    数据包信息 = self.分析器.分析数据包(
                        数据, 方向, "SSL" if self.是否ssl else "明文"
                    )

                    print(
                        f"[{连接标识}] 数据包#{数据包计数} ({方向}): {数据包信息['类型']} - {len(数据)}字节"
                    )

                    # 如果是明文数据，显示内容
                    if not 数据包信息.get("已加密", False) and "内容" in 数据包信息:
                        内容预览 = (
                            数据包信息["内容"][:50]
                            .replace("\r", "\\r")
                            .replace("\n", "\\n")
                        )
                        print(f"  内容预览: {内容预览}...")

                        if 数据包信息.get("敏感信息"):
                            print(
                                f"  发现敏感信息: {', '.join(数据包信息['敏感信息'])}"
                            )

                        # 显示解码结果
                        if "解码结果" in 数据包信息:
                            解码结果 = 数据包信息["解码结果"]
                            if 解码结果["认证信息"]:
                                print(f"🔓 认证信息已破解:")
                                for 结果 in 解码结果["认证信息"]:
                                    if "用户名" in 结果 and "密码" in 结果:
                                        print(
                                            f"    🔓 {结果['类型']}: 用户名='{结果['用户名']}', 密码='{结果['密码']}'"
                                        )
                                    else:
                                        print(f"    🔓 {结果['类型']}: {结果['解码']}")

                            if 解码结果["邮件内容"]:
                                print(f"📧 邮件内容已解码:")
                                for 结果 in 解码结果["邮件内容"]:
                                    print(
                                        f"    📧 {结果['类型']}: {结果['解码'][:50]}..."
                                    )

                            if 解码结果["其他敏感信息"]:
                                print(f"⚠️ 其他敏感信息:")
                                for 结果 in 解码结果["其他敏感信息"]:
                                    print(
                                        f"    ⚠️ {结果['类型']}: {结果['内容'][:50]}..."
                                    )

                    # 转发数据
                    目标.send(数据)

                except socket.timeout:
                    break
                except Exception as e:
                    logger.debug(f"转发异常: {e}")
                    break

        except Exception as e:
            logger.debug(f"转发线程异常: {e}")

    def 停止(self):
        """停止代理"""
        self.运行中 = False
        if self.服务器套接字:
            try:
                self.服务器套接字.close()
            except:
                pass

    def 获取分析报告(self) -> dict:
        """获取分析报告"""
        总数据包 = len(self.分析器.拦截数据包)
        加密数据包 = sum(1 for p in self.分析器.拦截数据包 if p.get("已加密", False))
        明文数据包 = 总数据包 - 加密数据包

        发现的敏感信息 = []
        for packet in self.分析器.拦截数据包:
            if packet.get("敏感信息"):
                发现的敏感信息.extend(packet["敏感信息"])

        return {
            "总数据包": 总数据包,
            "加密数据包": 加密数据包,
            "明文数据包": 明文数据包,
            "敏感信息类型": list(set(发现的敏感信息)),
            "加密样本": len(self.分析器.加密样本),
            "原始数据包": self.分析器.拦截数据包[-10:],  # 最后10个数据包
            "原始数据文件": str(self.分析器.原始数据文件),
        }


class 真实邮件服务器管理器:
    """真实邮件服务器管理器"""

    def __init__(self):
        self.smtp明文服务器 = None
        self.smtp_ssl服务器 = None
        self.服务器线程 = []

    def 启动服务器(self):
        """启动邮件服务器"""
        try:
            print("启动真实邮件服务器...")

            # 启动SMTP服务器（非SSL）
            self.smtp明文服务器 = StableSMTPServer(
                host="localhost",
                port=PORTS["smtp_plain"],
                use_ssl=False,
                require_auth=True,
            )
            smtp明文线程 = threading.Thread(target=self.smtp明文服务器.start)
            smtp明文线程.daemon = True
            smtp明文线程.start()
            self.服务器线程.append(smtp明文线程)
            print(f"SMTP服务器（非SSL）已启动: 端口 {PORTS['smtp_plain']}")

            # 启动SMTP服务器（SSL）
            self.smtp_ssl服务器 = StableSMTPServer(
                host="localhost",
                port=PORTS["smtp_ssl"],
                use_ssl=True,
                require_auth=True,
            )
            smtp_ssl线程 = threading.Thread(target=self.smtp_ssl服务器.start)
            smtp_ssl线程.daemon = True
            smtp_ssl线程.start()
            self.服务器线程.append(smtp_ssl线程)
            print(f"SMTP服务器（SSL）已启动: 端口 {PORTS['smtp_ssl']}")

            # 等待服务器启动
            time.sleep(3)

            # 验证服务器
            self._验证服务器()

        except Exception as e:
            print(f"启动服务器失败: {e}")
            raise

    def _验证服务器(self):
        """验证服务器启动状态"""
        for 端口名称, 端口 in PORTS.items():
            if 端口名称.startswith("smtp_") and not 端口名称.startswith("mitm_"):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(("localhost", 端口))
                    sock.close()

                    if result == 0:
                        print(f"  {端口名称}({端口}) 服务器运行正常")
                    else:
                        print(f"  警告: {端口名称}({端口}) 服务器可能未启动")
                except Exception as e:
                    print(f"  警告: 检查 {端口名称}({端口}) 失败: {e}")

    def 停止服务器(self):
        """停止所有服务器"""
        print("停止邮件服务器...")

        for server in [self.smtp明文服务器, self.smtp_ssl服务器]:
            if server:
                try:
                    server.stop()
                except Exception as e:
                    logger.debug(f"停止服务器错误: {e}")


class 真实邮件客户端模拟器:
    """真实邮件客户端模拟器"""

    def __init__(self):
        self.测试用户名 = "testuser"
        self.测试密码 = "testpass"

    def 通过mitm发送邮件(self, use_ssl: bool, subject: str, content: str) -> bool:
        """通过MITM代理发送邮件"""
        try:
            协议类型 = "SSL" if use_ssl else "明文"
            mitm端口 = PORTS["mitm_smtp_ssl"] if use_ssl else PORTS["mitm_smtp_plain"]

            print(f"\n正在通过MITM代理发送{协议类型}邮件 (端口: {mitm端口})...")

            # 创建邮件对象，使用有效的邮件格式
            邮件 = Email(
                message_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
                subject=subject,
                from_addr=EmailAddress("测试发送者", f"{self.测试用户名}@example.com"),
                to_addrs=[EmailAddress("测试接收者", "recipient@example.com")],
                text_content=content,
            )

            # 创建SMTP客户端，连接到MITM代理
            客户端 = SMTPClient(
                host="localhost",
                port=mitm端口,
                use_ssl=use_ssl,
                username=self.测试用户名,
                password=self.测试密码,
                timeout=10,
            )

            # 发送邮件
            客户端.connect()
            结果 = 客户端.send_email(邮件)
            客户端.disconnect()

            if 结果:
                print(f"{协议类型}邮件发送成功")
                return True
            else:
                print(f"{协议类型}邮件发送失败")
                return False

        except Exception as e:
            print(f"{协议类型}邮件发送异常: {e}")
            return False


def 演示私钥解密(ssl代理: 真实MITM代理):
    """演示私钥泄露场景下的解密过程"""
    print("\n" + "=" * 70)
    print("场景演示：私钥泄露 - 攻击者获得了服务器私钥")
    print("=" * 70)

    if not os.path.exists(SSL_KEY_FILE):
        print("警告: SSL私钥文件不存在，跳过私钥解密演示")
        return

    # 获取分析报告
    报告 = ssl代理.获取分析报告()

    print(f"SSL流量分析结果:")
    print(f"   总数据包: {报告['总数据包']}")
    print(f"   加密数据包: {报告['加密数据包']}")
    print(f"   明文数据包: {报告['明文数据包']}")
    print(f"   加密样本: {报告['加密样本']}")

    if 报告["加密样本"] > 0:
        print(f"\n模拟私钥解密过程:")
        print(f"   1. 攻击者获得SSL私钥文件: {SSL_KEY_FILE}")
        print(f"   2. 从拦截的TLS握手中提取会话密钥")
        print(f"   3. 使用会话密钥解密应用数据")

        print(f"\n模拟解密结果（假设成功）:")
        print(f"   解密出的邮件内容包括:")
        print(f"       • 邮件主题: 包含敏感信息的测试邮件")
        print(f"       • 认证信息: 用户名和密码")
        print(f"       • 邮件正文: 完整的邮件内容")
        print(f"       • 发件人/收件人信息: 完整的通信关系")

        print(f"\n关键安全威胁:")
        print(f"   • 历史通信记录完全暴露")
        print(f"   • 未来通信持续被监听")
        print(f"   • 用户认证信息泄露")
        print(f"   • 商业机密和隐私完全失去保护")

        # 尝试显示一些加密数据的十六进制表示
        print(f"\n加密数据样本（十六进制表示）:")
        for 时间戳, 样本 in list(ssl代理.分析器.加密样本.items())[:3]:  # 显示前3个样本
            加密数据 = 样本["数据"]
            print(f"   时间: {时间戳}")
            print(f"   加密数据: {加密数据.hex()[:100]}...")
            print(f"   大小: {样本['完整大小']} 字节")
    else:
        print(f"警告: 没有捕获到足够的SSL加密数据")


def 生成解密演示报告(明文代理: 真实MITM代理, ssl代理: 真实MITM代理):
    """生成详细的解密演示报告"""
    print("\n" + "=" * 80)
    print("详细解密演示报告")
    print("=" * 80)

    明文报告 = 明文代理.获取分析报告()
    ssl报告 = ssl代理.获取分析报告()

    # 保存解密报告到文件
    报告文件 = DATA_DIR / f"解密演示报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(报告文件, "w", encoding="utf-8") as f:
        f.write("中间人攻击解密演示报告\n")
        f.write("=" * 50 + "\n\n")

        f.write("1. 明文通信分析\n")
        f.write("-" * 30 + "\n")
        f.write(f"总数据包: {明文报告['总数据包']}\n")
        f.write(f"明文数据包: {明文报告['明文数据包']}\n")
        f.write(f"发现的敏感信息类型: {', '.join(明文报告['敏感信息类型'])}\n")
        f.write(f"原始数据文件: {明文报告['原始数据文件']}\n\n")

        f.write("明文数据包详情:\n")
        for i, 数据包 in enumerate(明文报告["原始数据包"]):
            if not 数据包.get("已加密", False):
                f.write(f"  数据包 {i+1}:\n")
                f.write(f"    时间: {数据包['时间戳']}\n")
                f.write(f"    类型: {数据包['类型']}\n")
                f.write(f"    大小: {数据包['大小']} 字节\n")
                if "内容" in 数据包:
                    f.write(f"    内容: {数据包['内容'][:100]}...\n")
                if "解码结果" in 数据包:
                    for 结果 in 数据包["解码结果"]["认证信息"]:
                        f.write(f"    认证信息: {结果['类型']} -> {结果['原始']}\n")
                    for 结果 in 数据包["解码结果"]["邮件内容"]:
                        f.write(f"    邮件内容: {结果['类型']} -> {结果['原始']}\n")
                    for 结果 in 数据包["解码结果"]["其他敏感信息"]:
                        f.write(f"    其他敏感信息: {结果['类型']} -> {结果['内容']}\n")
                f.write("\n")

        f.write("\n2. SSL加密通信分析\n")
        f.write("-" * 30 + "\n")
        f.write(f"总数据包: {ssl报告['总数据包']}\n")
        f.write(f"加密数据包: {ssl报告['加密数据包']}\n")
        f.write(f"明文数据包: {ssl报告['明文数据包']}\n")
        f.write(f"加密样本数量: {ssl报告['加密样本']}\n")
        f.write(f"原始数据文件: {ssl报告['原始数据文件']}\n\n")

        f.write("加密数据包详情:\n")
        for i, 数据包 in enumerate(ssl报告["原始数据包"]):
            if 数据包.get("已加密", False):
                f.write(f"  加密数据包 {i+1}:\n")
                f.write(f"    时间: {数据包['时间戳']}\n")
                f.write(f"    类型: {数据包['类型']}\n")
                f.write(f"    大小: {数据包['大小']} 字节\n")
                f.write(f"    加密数据样本: {数据包['原始数据样本']}\n\n")

        f.write("\n3. 安全结论\n")
        f.write("-" * 30 + "\n")
        f.write("明文通信风险:\n")
        f.write("• 所有通信内容完全暴露\n")
        f.write("• 认证信息可被直接窃取\n")
        f.write("• 通信关系完全透明\n\n")

        f.write("SSL加密保护:\n")
        f.write("• 通信内容完全加密\n")
        f.write("• 认证过程受到保护\n")
        f.write("• 需要私钥才能解密\n\n")

        f.write("私钥泄露威胁:\n")
        f.write("• 历史通信可被解密\n")
        f.write("• 未来通信持续暴露\n")
        f.write("• 整个加密体系失效\n")

    print(f"详细报告已保存到: {报告文件}")
    print(f"明文数据文件: {明文报告['原始数据文件']}")
    print(f"SSL数据文件: {ssl报告['原始数据文件']}")


def main():
    """主演示函数"""
    print("=" * 80)
    print("真实中间人攻击演示 - 基于真实邮件系统")
    print("=" * 80)
    print("演示目标:")
    print("   1. 对比SSL和非SSL通信的安全差异")
    print("   2. 展示MITM攻击的真实威胁")
    print("   3. 证明SSL加密的重要性")
    print("   4. 警示私钥泄露的严重后果")
    print("   5. 保存和解密拦截的原始数据")
    print("=" * 80)
    print("警告: 本演示仅用于教学目的！")
    print("=" * 80)

    # 用户输入邮件内容
    print("\n请输入测试邮件内容:")
    try:
        主题 = (
            input("邮件主题: ").strip()
            or f"机密文件_{datetime.now().strftime('%H%M%S')}"
        )
        内容 = input("邮件正文: ").strip() or "此邮件包含重要商业机密信息，请妥善保管。"
    except EOFError:
        # 非交互模式，使用默认值
        print("检测到非交互模式，使用默认测试内容...")
        主题 = f"机密文件_{datetime.now().strftime('%H%M%S')}"
        内容 = "此邮件包含重要商业机密信息，请妥善保管。"

    # 添加时间戳
    时间戳 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    主题带时间 = f"{主题} [{时间戳}]"
    内容带时间 = f"{内容}\n\n发送时间: {时间戳}\n包含敏感信息: 是"

    print(f"\n将要发送的邮件:")
    print(f"主题: {主题带时间}")
    print(f"内容: {内容带时间}")

    try:
        input("\n按回车键开始真实攻击演示...")
    except EOFError:
        # 非交互模式，直接继续
        print("自动开始演示...")
        time.sleep(1)

    # 创建服务器管理器
    服务器管理器 = 真实邮件服务器管理器()
    客户端模拟器 = 真实邮件客户端模拟器()
    明文代理 = None
    ssl代理 = None

    try:
        # 启动真实邮件服务器
        服务器管理器.启动服务器()

        # 启动MITM代理
        print(f"\n启动MITM攻击代理...")

        # 非SSL代理
        明文代理 = 真实MITM代理(
            PORTS["mitm_smtp_plain"], "localhost", PORTS["smtp_plain"], is_ssl=False
        )
        明文线程 = threading.Thread(target=明文代理.启动)
        明文线程.daemon = True
        明文线程.start()

        # SSL代理
        ssl代理 = 真实MITM代理(
            PORTS["mitm_smtp_ssl"], "localhost", PORTS["smtp_ssl"], is_ssl=True
        )
        ssl线程 = threading.Thread(target=ssl代理.启动)
        ssl线程.daemon = True
        ssl线程.start()

        time.sleep(2)

        # 演示1: 非SSL通信
        print("\n" + "=" * 60)
        print("演示1: 非SSL通信 - 完全暴露")
        print("=" * 60)

        成功1 = 客户端模拟器.通过mitm发送邮件(
            use_ssl=False, subject=主题带时间, content=内容带时间
        )

        time.sleep(3)

        if 成功1:
            明文报告 = 明文代理.获取分析报告()
            print(f"\n非SSL通信分析结果:")
            print(f"   拦截数据包: {明文报告['总数据包']}")
            print(f"   明文数据包: {明文报告['明文数据包']}")
            print(
                f"   发现敏感信息类型: {', '.join(明文报告['敏感信息类型']) if 明文报告['敏感信息类型'] else '无'}"
            )
            print(f"   原始数据已保存到: {明文报告['原始数据文件']}")

            print(f"\n安全威胁:")
            print(f"   • 邮件内容完全可读")
            print(f"   • 认证信息明文传输")
            print(f"   • 通信关系完全暴露")

        # 演示2: SSL通信
        print("\n" + "=" * 60)
        print("演示2: SSL通信 - 加密保护")
        print("=" * 60)

        成功2 = 客户端模拟器.通过mitm发送邮件(
            use_ssl=True, subject=主题带时间, content=内容带时间
        )

        time.sleep(3)

        if 成功2:
            ssl报告 = ssl代理.获取分析报告()
            print(f"\nSSL通信分析结果:")
            print(f"   拦截数据包: {ssl报告['总数据包']}")
            print(f"   加密数据包: {ssl报告['加密数据包']}")
            print(f"   明文数据包: {ssl报告['明文数据包']}")
            print(f"   原始数据已保存到: {ssl报告['原始数据文件']}")

            print(f"\n加密保护效果:")
            print(f"   • 邮件内容完全加密，无法直接读取")
            print(f"   • 认证过程受SSL保护")
            print(f"   • 通信内容对攻击者呈现为乱码")

        # 演示3: 私钥泄露场景
        if 成功2 and ssl代理:
            演示私钥解密(ssl代理)

        # 生成详细报告
        if 成功1 and 成功2:
            生成解密演示报告(明文代理, ssl代理)

        # 最终对比总结
        print("\n" + "=" * 70)
        print("安全对比总结")
        print("=" * 70)

        print(f"\n非SSL vs SSL 数据包对比:")
        if 成功1 and 成功2:
            明文报告 = 明文代理.获取分析报告()
            ssl报告 = ssl代理.获取分析报告()

            print(f"   非SSL通信:")
            print(f"     • 明文数据包: {明文报告['明文数据包']}")
            print(f"     • 敏感信息暴露: {'是' if 明文报告['敏感信息类型'] else '否'}")
            print(f"     • 安全等级: 极低 ❌")

            print(f"   SSL通信:")
            print(f"     • 加密数据包: {ssl报告['加密数据包']}")
            print(f"     • 内容保护: 完全加密")
            print(f"     • 安全等级: 高 ✅")

        print(f"\n关键洞察:")
        print(f"   1. SSL/TLS加密是网络通信的基本要求")
        print(f"   2. 私钥安全是整个系统安全的核心")
        print(f"   3. 即使有了加密，也要防范MITM攻击")
        print(f"   4. 定期更新证书和加密算法")

        print(f"\n您的测试内容 '{主题}' 在不同模式下的安全性已得到清晰展示！")
        print(f"\n所有拦截的原始数据已保存到 {DATA_DIR} 目录中")

    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"\n演示错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 清理资源
        print(f"\n正在清理演示环境...")

        if 明文代理:
            明文代理.停止()
        if ssl代理:
            ssl代理.停止()

        服务器管理器.停止服务器()

        time.sleep(2)
        print("清理完成")

        print(f"\n真实MITM攻击演示结束")
        print(f"演示数据已保存，可用于进一步的安全分析")


if __name__ == "__main__":
    main()
