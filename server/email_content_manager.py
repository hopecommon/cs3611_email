"""
邮件内容管理 - 专门负责邮件内容的存储和读取
"""

import os
import re
import datetime
import json
import base64
from typing import Optional, Dict, Any

from common.utils import setup_logging
from common.config import EMAIL_STORAGE_DIR
from common.email_format_handler import EmailFormatHandler

# 设置日志
logger = setup_logging("email_content_manager")


class EmailContentManager:
    """邮件内容管理器"""

    def __init__(self):
        """初始化邮件内容管理器"""
        # 确保邮件存储目录存在
        os.makedirs(EMAIL_STORAGE_DIR, exist_ok=True)
        logger.info("邮件内容管理器已初始化")

    def save_content(
        self, message_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        保存邮件内容，使用统一的EmailFormatHandler

        Args:
            message_id: 邮件ID
            content: 邮件内容
            metadata: 邮件元数据（用于补充头部信息）

        Returns:
            保存的文件路径，失败返回None
        """
        try:
            # 确保存储目录存在
            os.makedirs(EMAIL_STORAGE_DIR, exist_ok=True)

            # 1. 使用EmailFormatHandler统一处理邮件格式
            from common.email_format_handler import EmailFormatHandler

            # 如果有元数据，用它来完善邮件内容
            if metadata:
                # 先尝试解析现有内容
                try:
                    email_obj = EmailFormatHandler.parse_email_content(content)
                    # 用元数据补充缺失的字段
                    if metadata.get("from_addr") and (
                        not email_obj.from_addr
                        or email_obj.from_addr.address in ["unknown@localhost", ""]
                    ):
                        from common.models import EmailAddress

                        email_obj.from_addr = EmailAddress("", metadata["from_addr"])
                    if metadata.get("subject") and not email_obj.subject:
                        email_obj.subject = metadata["subject"]
                    if metadata.get("message_id") and not email_obj.message_id:
                        email_obj.message_id = metadata["message_id"]

                    # 重新格式化内容
                    content = EmailFormatHandler.format_email_for_storage(email_obj)
                except Exception as e:
                    logger.warning(f"解析邮件失败，使用原始内容: {e}")
                    # 如果解析失败，确保格式正确
                    content = EmailFormatHandler.ensure_proper_format(content, metadata)
            else:
                # 没有元数据，直接确保格式正确
                content = EmailFormatHandler.ensure_proper_format(content)

            # 2. 生成安全的文件名
            safe_filename = self._generate_safe_filename(message_id)
            filepath = os.path.join(EMAIL_STORAGE_DIR, f"{safe_filename}.eml")

            # 3. 如果文件已存在，可能需要覆盖或跳过
            if os.path.exists(filepath):
                logger.debug(f"邮件文件已存在，将覆盖: {filepath}")

            # 4. 保存内容
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"已保存邮件内容: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"保存邮件内容时出错: {e}")
            return None

    def get_content(
        self, message_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        获取邮件内容

        Args:
            message_id: 邮件ID
            metadata: 邮件元数据（可选，用于生成占位内容）

        Returns:
            邮件内容，失败返回None
        """
        try:
            # 1. 尝试直接加载内容
            content = self._try_load_content(message_id, metadata)
            if not content:
                logger.warning(f"无法找到邮件内容: {message_id}")
                return None

            # 2. 使用统一的格式验证和修复
            if EmailFormatHandler.validate_email_format(content):
                return content

            # 3. 如果格式有问题，尝试修复
            logger.debug(f"邮件格式需要修复: {message_id}")
            if metadata:
                fixed_content = self._build_complete_email_content(metadata, content)
                return EmailFormatHandler.ensure_proper_format(fixed_content)
            else:
                return EmailFormatHandler.ensure_proper_format(content)

        except Exception as e:
            logger.error(f"获取邮件内容时出错: {e}")
            return None

    def _extract_message_id(self, content: str) -> Optional[str]:
        """从邮件内容中提取Message-ID，使用统一的EmailFormatHandler"""
        try:
            # 使用统一的邮件格式处理器解析
            email_obj = EmailFormatHandler.parse_email_content(content)
            return email_obj.message_id
        except Exception:
            return None

    def _generate_safe_filename(self, message_id: str) -> str:
        """生成安全的文件名"""
        # 标准化处理：移除两端空格，去掉<>，@替换为_at_
        safe_id = message_id.strip().strip("<>").replace("@", "_at_")
        # 移除Windows文件系统不允许的字符
        safe_id = re.sub(r'[\\/*?:"<>|]', "_", safe_id)
        # 确保没有前导或尾随空格
        return safe_id.strip()

    def _ensure_proper_email_format_with_metadata(
        self, content: str, message_id: str, metadata: Dict[str, Any]
    ) -> str:
        """
        使用元数据确保邮件格式正确，补充缺失的头部

        Args:
            content: 原始邮件内容
            message_id: 邮件ID
            metadata: 邮件元数据

        Returns:
            格式化后的邮件内容
        """
        try:
            import email
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # 尝试解析现有邮件
            try:
                msg = email.message_from_string(content)
            except:
                # 如果解析失败，创建新的邮件对象
                msg = MIMEText("", "plain", "utf-8")
                # 将原始内容作为邮件正文
                if content.strip():
                    msg.set_payload(content)

            # 检查并补充必需的头部字段
            needs_update = False

            # Message-ID
            if not msg.get("Message-ID"):
                msg["Message-ID"] = message_id
                needs_update = True

            # From字段
            if not msg.get("From") and metadata.get("from_addr"):
                msg["From"] = metadata["from_addr"]
                needs_update = True

            # To字段
            if not msg.get("To") and metadata.get("to_addrs"):
                to_addrs = metadata["to_addrs"]
                if isinstance(to_addrs, list):
                    msg["To"] = ", ".join(to_addrs)
                else:
                    msg["To"] = str(to_addrs)
                needs_update = True

            # CC字段
            if not msg.get("Cc") and metadata.get("cc_addrs"):
                cc_addrs = metadata["cc_addrs"]
                if isinstance(cc_addrs, list) and cc_addrs:
                    msg["Cc"] = ", ".join(cc_addrs)
                needs_update = True

            # Subject字段
            if not msg.get("Subject") and metadata.get("subject"):
                msg["Subject"] = metadata["subject"]
                needs_update = True

            # Date字段
            if not msg.get("Date") and metadata.get("date"):
                try:
                    import datetime

                    if isinstance(metadata["date"], str):
                        date_obj = datetime.datetime.fromisoformat(metadata["date"])
                    else:
                        date_obj = metadata["date"]
                    msg["Date"] = date_obj.strftime("%a, %d %b %Y %H:%M:%S %z")
                except:
                    msg["Date"] = datetime.datetime.now().strftime(
                        "%a, %d %b %Y %H:%M:%S %z"
                    )
                needs_update = True

            # MIME版本
            if not msg.get("MIME-Version"):
                msg["MIME-Version"] = "1.0"
                needs_update = True

            # Content-Type（如果没有的话）
            if not msg.get("Content-Type"):
                msg["Content-Type"] = "text/plain; charset=utf-8"
                needs_update = True

            if needs_update:
                logger.debug(f"补充邮件头部: {message_id}")
                return str(msg)
            else:
                return content

        except Exception as e:
            logger.warning(f"邮件格式化失败，使用原始内容: {message_id} - {e}")
            return content

    def _try_load_content(
        self, message_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """尝试加载邮件内容"""
        # 1. 尝试使用metadata中的content_path
        if metadata and metadata.get("content_path"):
            content = self._load_from_path(metadata["content_path"])
            if content:
                return content

        # 2. 尝试使用标准化的ID查找文件
        safe_filename = self._generate_safe_filename(message_id)
        filepath = os.path.join(EMAIL_STORAGE_DIR, f"{safe_filename}.eml")
        content = self._load_from_path(filepath)
        if content:
            return content

        # 3. 尝试搜索包含类似ID的文件
        return self._search_similar_files(message_id)

    def _load_from_path(self, filepath: str) -> Optional[str]:
        """从指定路径加载内容"""
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            logger.error(f"读取文件时出错: {filepath}, {e}")
        return None

    def _search_similar_files(self, message_id: str) -> Optional[str]:
        """搜索包含类似ID的文件"""
        try:
            # 提取ID的关键部分进行模糊匹配
            clean_id = message_id.strip("<>").split("@")[0]

            for filename in os.listdir(EMAIL_STORAGE_DIR):
                if filename.endswith(".eml") and clean_id in filename:
                    filepath = os.path.join(EMAIL_STORAGE_DIR, filename)
                    content = self._load_from_path(filepath)
                    if content:
                        logger.debug(f"通过模糊匹配找到邮件文件: {filepath}")
                        return content
        except Exception as e:
            logger.error(f"搜索类似文件时出错: {e}")
        return None

    def _has_proper_email_headers(self, content: str) -> bool:
        """
        检查邮件内容是否有正确的头部格式

        检查两个条件：
        1. 是否包含基本的邮件头部字段
        2. 头部格式是否符合RFC标准（头部字段之间不应有额外空行）

        Args:
            content: 邮件内容

        Returns:
            bool: 如果有正确的头部格式返回True，否则返回False
        """
        if not content:
            return False

        lines = content.split("\n")
        has_headers = False
        header_format_correct = True
        header_count = 0

        for i, line in enumerate(lines[:20]):  # 检查前20行，足够涵盖大部分头部
            line_stripped = line.strip()

            # 检查是否是头部字段
            if line_stripped and ":" in line_stripped:
                # 基本头部字段检查
                if line_stripped.startswith(
                    (
                        "Subject:",
                        "From:",
                        "To:",
                        "Date:",
                        "Message-ID:",
                        "Content-Type:",
                        "MIME-Version:",
                        "Content-Transfer-Encoding:",
                    )
                ):
                    has_headers = True
                    header_count += 1

                    # 检查RFC格式：头部字段后面是否有不必要的空行
                    if i + 1 < len(lines) and lines[i + 1].strip() == "":
                        # 检查下一个非空行是否也是头部字段
                        for j in range(i + 2, min(i + 5, len(lines))):
                            if j < len(lines):
                                next_line = lines[j].strip()
                                if next_line:
                                    # 如果下一个非空行也是头部字段，说明有不必要的空行
                                    if ":" in next_line and next_line.startswith(
                                        (
                                            "Subject:",
                                            "From:",
                                            "To:",
                                            "Date:",
                                            "Message-ID:",
                                            "Content-Type:",
                                            "MIME-Version:",
                                            "Content-Transfer-Encoding:",
                                        )
                                    ):
                                        logger.debug(
                                            f"检测到头部字段间有额外空行：第{i+1}行和第{j+1}行之间"
                                        )
                                        header_format_correct = False
                                        break
                                    else:
                                        break
            elif line_stripped == "" and header_count > 0:
                # 遇到空行且已有头部字段，说明头部结束
                break

        # 只有当既有头部字段，又格式正确时才返回True
        result = has_headers and header_format_correct

        if has_headers and not header_format_correct:
            logger.debug(f"邮件有头部字段但格式不正确，需要修复")
        elif not has_headers:
            logger.debug(f"邮件缺少头部字段")

        return result

    def _build_complete_email_content(
        self, metadata: Dict[str, Any], original_content: str
    ) -> str:
        """根据元数据构建完整的邮件内容"""
        headers = []

        # 添加基本头部 - 注意：不在头部字段之间添加空行
        headers.append(f"Message-ID: {metadata.get('message_id', '')}")
        headers.append(f"Subject: {metadata.get('subject', '')}")
        headers.append(f"From: {metadata.get('from_addr', '')}")

        # 处理收件人
        to_addrs = self._parse_address_list(metadata.get("to_addrs", []))
        if to_addrs:
            headers.append(f"To: {', '.join(to_addrs)}")

        # 添加日期
        date_formatted = self._format_date(metadata.get("date"))
        headers.append(f"Date: {date_formatted}")

        # 添加MIME头部
        headers.append("MIME-Version: 1.0")

        # 检查原始内容是否包含base64编码
        if self._looks_like_base64(original_content):
            headers.append("Content-Type: text/plain; charset=utf-8")
            headers.append("Content-Transfer-Encoding: base64")
            # 只在头部结束后添加一个空行（RFC标准）
            headers.append("")  # 空行分隔头部和正文

            # 提取并处理base64内容
            base64_content = self._extract_base64_content(original_content)
            if base64_content:
                headers.append(base64_content)
            else:
                # 将原内容编码为base64
                encoded_content = base64.b64encode(
                    original_content.encode("utf-8")
                ).decode("ascii")
                formatted_content = "\n".join(
                    [
                        encoded_content[i : i + 76]
                        for i in range(0, len(encoded_content), 76)
                    ]
                )
                headers.append(formatted_content)
        else:
            headers.append("Content-Type: text/plain; charset=utf-8")
            headers.append("Content-Transfer-Encoding: 8bit")
            # 只在头部结束后添加一个空行（RFC标准）
            headers.append("")  # 空行分隔头部和正文
            headers.append(original_content)

        # 使用'\n'连接，确保符合RFC标准：头部字段连续，只在头部结束后有一个空行
        return "\n".join(headers)

    def _parse_address_list(self, to_addrs) -> list:
        """解析地址列表"""
        if isinstance(to_addrs, str):
            try:
                to_addrs = json.loads(to_addrs)
            except json.JSONDecodeError:
                return [to_addrs]

        if isinstance(to_addrs, list):
            if to_addrs and isinstance(to_addrs[0], dict) and "address" in to_addrs[0]:
                return [addr["address"] for addr in to_addrs if addr.get("address")]
            else:
                return [str(addr) for addr in to_addrs]

        return []

    def _format_date(self, date_str: str) -> str:
        """格式化日期"""
        if date_str:
            try:
                date = datetime.datetime.fromisoformat(date_str)
                return date.strftime("%a, %d %b %Y %H:%M:%S %z")
            except ValueError:
                return date_str
        return datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

    def _looks_like_base64(self, content: str) -> bool:
        """检查内容是否看起来像base64编码"""
        lines = content.strip().split("\n")
        base64_lines = 0

        for line in lines:
            line = line.strip()
            if len(line) > 20:
                try:
                    base64.b64decode(line)
                    base64_lines += 1
                except:
                    pass

        return base64_lines > len(lines) / 2

    def _extract_base64_content(self, content: str) -> str:
        """从内容中提取base64编码的部分"""
        lines = content.split("\n")
        base64_lines = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith(
                ("Content-", "MIME-", "Subject:", "From:", "To:", "Date:")
            ):
                try:
                    base64.b64decode(line)
                    base64_lines.append(line)
                except:
                    continue

        return "\n".join(base64_lines)

    def _generate_placeholder_content(
        self, message_id: str, metadata: Dict[str, Any]
    ) -> str:
        """生成占位邮件内容"""
        try:
            subject = metadata.get("subject", "(无主题)")
            from_addr = metadata.get("from_addr", "(未知发件人)")

            # 处理收件人列表
            to_addrs = self._parse_address_list(metadata.get("to_addrs", []))
            to_addr_str = ", ".join(to_addrs) if to_addrs else "(未知收件人)"

            # 格式化日期
            date_formatted = self._format_date(metadata.get("date", ""))

            # 构建符合RFC标准的邮件内容
            placeholder_content = f"""From: {from_addr}
To: {to_addr_str}
Subject: {subject}
Message-ID: {message_id}
Date: {date_formatted}
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"

[此邮件的原始内容不可用，这是根据元数据生成的占位内容]
"""
            logger.warning(f"生成占位邮件内容: {message_id}")
            return placeholder_content
        except Exception as e:
            logger.error(f"生成占位邮件内容时出错: {e}")
            return None
