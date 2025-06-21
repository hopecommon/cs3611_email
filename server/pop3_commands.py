"""
POP3命令处理模块 - 处理POP3命令的执行逻辑
"""

import logging
import datetime
import json
from typing import Dict, List, Optional, Set, Tuple, Any, Callable

from common.utils import setup_logging
from server.new_db_handler import EmailService  # 使用新的数据库服务
from server.pop3_auth import POP3Authenticator

# 设置日志
logger = setup_logging("pop3_commands")


class POP3CommandHandler:
    """POP3命令处理器，处理各种POP3命令的执行逻辑"""

    def __init__(
        self,
        email_service: EmailService,  # 改用EmailService
        authenticator: POP3Authenticator,
        send_response_callback: Callable[[str], None],
    ):
        """
        初始化POP3命令处理器

        Args:
            email_service: 邮件服务
            authenticator: POP3认证器
            send_response_callback: 发送响应的回调函数
        """
        self.email_service = email_service  # 使用邮件服务
        self.authenticator = authenticator
        self.send_response = send_response_callback

        # 会话状态
        self.state = "AUTHORIZATION"  # AUTHORIZATION, TRANSACTION, UPDATE
        self.authenticated = False
        self.authenticated_user = None
        self.user_email = None  # 用户邮箱地址，用于查询邮件
        self.marked_for_deletion = set()  # 标记为删除的邮件ID
        self.cached_emails = []  # 缓存的邮件列表，避免重复查询

        logger.info("POP3命令处理器已初始化")

    def handle_command(self, command: str) -> bool:
        """
        处理POP3命令

        Args:
            command: 命令字符串

        Returns:
            是否继续处理
        """
        # 解析命令
        parts = command.split(" ", 1)
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ""

        # 记录命令（不记录密码）
        if cmd == "PASS":
            logger.debug(f"处理命令: {cmd} [密码已隐藏]")
        else:
            logger.debug(f"处理命令: {cmd} {arg}")

        # 处理各种命令
        if cmd == "USER":
            return self.process_user(arg)
        elif cmd == "PASS":
            return self.process_pass(arg)
        elif cmd == "QUIT":
            return self.process_quit()
        elif cmd == "STAT":
            return self.process_stat()
        elif cmd == "LIST":
            return self.process_list(arg)
        elif cmd == "RETR":
            return self.process_retr(arg)
        elif cmd == "DELE":
            return self.process_dele(arg)
        elif cmd == "NOOP":
            return self.process_noop()
        elif cmd == "RSET":
            return self.process_rset()
        elif cmd == "TOP":
            return self.process_top(arg)
        elif cmd == "UIDL":
            return self.process_uidl(arg)
        elif cmd == "CAPA":
            # 返回服务器能力
            capabilities = [
                "+OK Capability list follows",
                "USER",
                "TOP",
                "UIDL",
                "RESP-CODES",
                "PIPELINING",
                "AUTH-RESP-CODE",
                ".",
            ]
            self.send_response("\r\n".join(capabilities))
            return True
        else:
            # 未知命令
            logger.warning(f"未知命令: {cmd}")
            self.send_response(f"-ERR Unrecognized command: {cmd}")
            return True

    def process_user(self, username: str) -> bool:
        """
        处理USER命令

        Args:
            username: 用户名

        Returns:
            是否继续处理
        """
        if self.state != "AUTHORIZATION":
            self.send_response("-ERR Command not valid in this state")
            return True

        if not username:
            self.send_response("-ERR Username required")
            return True

        # 保存用户名，等待密码
        self.authenticated_user = username
        self.send_response("+OK User name accepted, password please")
        return True

    def process_pass(self, password: str) -> bool:
        """
        处理PASS命令

        Args:
            password: 密码

        Returns:
            是否继续处理
        """
        if self.state != "AUTHORIZATION":
            self.send_response("-ERR Command not valid in this state")
            return True

        if not self.authenticated_user:
            self.send_response("-ERR USER first")
            return True

        if not password:
            self.send_response("-ERR Password required")
            return True

        # 验证密码
        authenticated, user_email = self.authenticator.authenticate(
            self.authenticated_user, password
        )

        if authenticated:
            self.authenticated = True
            self.state = "TRANSACTION"
            self.user_email = user_email
            logger.info(
                f"用户 {self.authenticated_user} 认证成功，状态切换到 TRANSACTION"
            )

            # 预加载邮件列表
            try:
                # 加载邮件列表 - 使用用户的邮箱地址而不是用户名
                self.cached_emails = self.email_service.list_emails(
                    user_email=self.user_email,
                    include_deleted=False,
                    include_spam=False,
                )
                logger.info(
                    f"已为用户 {self.authenticated_user} (邮箱: {self.user_email}) 预加载 {len(self.cached_emails)} 封邮件"
                )

                # 如果没有找到邮件，尝试使用更宽松的查询进行调试
                if not self.cached_emails:
                    self._debug_email_loading()
            except Exception as e:
                logger.error(f"预加载邮件列表时出错: {e}")
                import traceback

                logger.error(f"异常详情: {traceback.format_exc()}")
                # 正确处理数据库错误
                self.send_response("-ERR Database error, please try again later")
                self.authenticated = False
                self.authenticated_user = None
                self.state = "AUTHORIZATION"
                return True

            self.send_response(
                f"+OK {self.authenticated_user} logged in, {len(self.cached_emails)} messages waiting"
            )
        else:
            logger.warning(f"用户 {self.authenticated_user} 认证失败")
            self.authenticated_user = None
            self.send_response("-ERR Authentication failed")

        return True

    def _debug_email_loading(self) -> None:
        """调试邮件加载问题"""
        logger.warning(f"未找到邮件，尝试使用更宽松的查询进行调试")
        # 尝试直接从数据库查询所有邮件，用于调试
        all_emails = self.email_service.list_emails()
        logger.info(f"数据库中共有 {len(all_emails)} 封邮件")
        if all_emails:
            # 记录一些邮件的收件人信息，用于调试
            for i, email in enumerate(all_emails[:5]):
                to_addrs = email.get("to_addrs", [])
                # 处理不同类型的to_addrs
                if isinstance(to_addrs, list):
                    # 如果是列表，检查元素类型
                    addr_list = []
                    for addr in to_addrs:
                        if isinstance(addr, dict) and "address" in addr:
                            addr_list.append(addr["address"])
                        elif isinstance(addr, str):
                            addr_list.append(addr)
                        else:
                            addr_list.append(str(addr))
                    to_addrs_str = ", ".join(addr_list)
                else:
                    # 如果不是列表，直接转为字符串
                    to_addrs_str = str(to_addrs)
                logger.info(
                    f"邮件 {i+1}: to_addrs={to_addrs_str}, from_addr={email.get('from_addr')}"
                )

                # 检查是否有匹配的收件人
                user_email = self.user_email

                # 检查不同格式的收件人
                match_found = False

                # 检查to_addrs是列表的情况
                if isinstance(to_addrs, list):
                    for addr in to_addrs:
                        if isinstance(addr, dict) and addr.get("address") == user_email:
                            match_found = True
                            break
                        elif isinstance(addr, str) and addr == user_email:
                            match_found = True
                            break
                        elif isinstance(addr, str) and f"<{user_email}>" in addr:
                            match_found = True
                            break
                # 检查to_addrs是字符串的情况
                elif isinstance(to_addrs, str):
                    if user_email in to_addrs or f"<{user_email}>" in to_addrs:
                        match_found = True

                # 如果找到匹配，添加到缓存
                if match_found:
                    logger.info(f"找到匹配的收件人地址: {user_email}")
                    # 将此邮件添加到缓存
                    if email not in self.cached_emails:
                        self.cached_emails.append(email)

    def process_quit(self) -> bool:
        """
        处理QUIT命令

        Returns:
            是否继续处理
        """
        logger.debug(f"处理QUIT命令，当前状态: {self.state}")

        if self.state == "TRANSACTION":
            # 进入UPDATE状态
            self.state = "UPDATE"
            logger.debug(f"状态从TRANSACTION切换到UPDATE")

            # 执行删除操作
            self.perform_deletions()

            self.send_response("+OK POP3 server signing off")
        else:
            logger.debug(f"当前状态不是TRANSACTION，直接退出")
            self.send_response("+OK POP3 server signing off")

        logger.debug(f"QUIT命令处理完成，返回False以结束会话")
        return False

    def process_stat(self) -> bool:
        """
        处理STAT命令

        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True

        # 使用缓存的邮件列表
        if not self.cached_emails:
            try:
                # 如果缓存为空，重新获取邮件列表 - 使用用户的邮箱地址而不是用户名
                self.cached_emails = self.email_service.list_emails(
                    user_email=self.user_email,
                    include_deleted=False,
                    include_spam=False,
                )
                logger.debug(
                    f"已为用户 {self.authenticated_user} 加载 {len(self.cached_emails)} 封邮件"
                )
            except Exception as e:
                logger.error(f"获取邮件列表时出错: {e}")
                self.send_response("-ERR Database error")
                return True

        # 计算总大小
        count = len(self.cached_emails)
        size = sum(email.get("size", 0) for email in self.cached_emails)

        self.send_response(f"+OK {count} {size}")
        return True

    def process_list(self, arg: str) -> bool:
        """
        处理LIST命令

        Args:
            arg: 可选的邮件编号

        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True

        # 使用缓存的邮件列表
        if not self.cached_emails:
            try:
                # 如果缓存为空，重新获取邮件列表 - 使用用户的邮箱地址而不是用户名
                self.cached_emails = self.email_service.list_emails(
                    user_email=self.user_email,
                    include_deleted=False,
                    include_spam=False,
                    include_recalled=False,
                )
                logger.debug(
                    f"已为用户 {self.authenticated_user} 加载 {len(self.cached_emails)} 封邮件"
                )
            except Exception as e:
                logger.error(f"获取邮件列表时出错: {e}")
                self.send_response("-ERR Database error")
                return True

        # 如果指定了邮件编号
        if arg:
            try:
                msg_num = int(arg)
                if 1 <= msg_num <= len(self.cached_emails):
                    email = self.cached_emails[msg_num - 1]
                    self.send_response(f"+OK {msg_num} {email.get('size', 0)}")
                else:
                    self.send_response(
                        f"-ERR No such message, index {msg_num} out of range 1-{len(self.cached_emails)}"
                    )
            except ValueError:
                self.send_response(f"-ERR Invalid message number: {arg}")
        else:
            # 返回所有邮件
            self.send_response(f"+OK {len(self.cached_emails)} messages")
            for i, email in enumerate(self.cached_emails, 1):
                self.send_response(f"{i} {email.get('size', 0)}")
            self.send_response(".")

        return True

    def process_retr(self, arg: str) -> bool:
        """
        处理RETR命令

        Args:
            arg: 邮件编号

        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True

        if not arg:
            self.send_response("-ERR Message number required")
            return True

        try:
            msg_num = int(arg)

            # 使用缓存的邮件列表
            if not self.cached_emails:
                try:
                    # 如果缓存为空，重新获取邮件列表 - 使用用户的邮箱地址而不是用户名
                    self.cached_emails = self.email_service.list_emails(
                        user_email=self.user_email,
                        include_deleted=False,
                        include_spam=False,
                        include_recalled=False,
                    )
                    logger.debug(
                        f"已为用户 {self.authenticated_user} 加载 {len(self.cached_emails)} 封邮件"
                    )
                except Exception as e:
                    logger.error(f"获取邮件列表时出错: {e}")
                    import traceback

                    logger.error(f"异常详情: {traceback.format_exc()}")
                    self.send_response("-ERR Database error")
                    return True

            # 检查邮件编号是否有效
            if not self.cached_emails:
                logger.warning(f"用户 {self.authenticated_user} 没有邮件")
                self.send_response("-ERR No messages available")
                return True

            if 1 <= msg_num <= len(self.cached_emails):
                email = self.cached_emails[msg_num - 1]
                message_id = email["message_id"]

                logger.debug(f"正在获取邮件内容: {message_id}")

                try:
                    # 获取邮件内容
                    content = self.email_service.get_email_content(message_id)

                    if content:
                        # 标记为已读
                        try:
                            self.email_service.mark_email_as_read(message_id)
                            logger.debug(f"邮件已标记为已读: {message_id}")
                        except Exception as e:
                            logger.warning(f"标记邮件为已读时出错: {e}")
                            import traceback

                            logger.warning(f"异常详情: {traceback.format_exc()}")

                        # 计算内容大小
                        content_size = len(content.encode("utf-8"))
                        logger.debug(f"邮件大小: {content_size} 字节")

                        # 确保内容格式正确，处理不同的换行符情况
                        # 首先统一换行符为CRLF
                        content = (
                            content.replace("\r\n", "\n")
                            .replace("\r", "\n")
                            .replace("\n", "\r\n")
                        )

                        # 确保内容以CRLF结尾
                        if not content.endswith("\r\n"):
                            content += "\r\n"

                        # 发送邮件内容
                        self.send_response(f"+OK {content_size} octets")

                        # 发送邮件内容（按行）
                        for line in content.split("\r\n"):
                            # 处理行开头的点（透明性规则）
                            if line.startswith("."):
                                line = "." + line
                            self.send_response(line)

                        # 添加调试日志
                        lines_count = content.count("\r\n") + 1
                        logger.debug(f"已发送邮件内容，共 {lines_count} 行")

                        # 结束标记
                        self.send_response(".")
                        logger.info(
                            f"已发送邮件内容: {message_id}, 大小: {content_size} 字节"
                        )
                    else:
                        # 正确处理邮件内容不存在的情况
                        logger.warning(f"未找到邮件内容: {message_id}")

                        # 尝试从元数据构建基本邮件内容
                        try:
                            # 获取元数据，构建简单邮件头信息
                            metadata = self.email_service.get_email_metadata(message_id)
                            if metadata:
                                # 从元数据中提取关键信息
                                subject = metadata.get("subject", "(无主题)")
                                from_addr = metadata.get("from_addr", "(未知发件人)")

                                # 提取收件人列表
                                to_addrs_json = metadata.get("to_addrs", "[]")
                                try:
                                    to_addrs = json.loads(to_addrs_json)
                                    to_addr_str = ", ".join(to_addrs)
                                except:
                                    to_addr_str = "(未知收件人)"

                                # 获取日期
                                date_str = metadata.get("date", "")
                                if date_str:
                                    try:
                                        date = datetime.datetime.fromisoformat(date_str)
                                        date_formatted = date.strftime(
                                            "%a, %d %b %Y %H:%M:%S %z"
                                        )
                                    except:
                                        date_formatted = date_str
                                else:
                                    date_formatted = datetime.datetime.now().strftime(
                                        "%a, %d %b %Y %H:%M:%S %z"
                                    )

                                # 构建基本邮件内容
                                placeholder_content = f"""From: {from_addr}
To: {to_addr_str}
Subject: {subject}
Message-ID: {message_id}
Date: {date_formatted}
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"

[此邮件的原始内容不可用]
"""
                                # 计算内容大小
                                content_size = len(placeholder_content.encode("utf-8"))
                                logger.debug(f"生成的占位内容大小: {content_size} 字节")

                                # 确保内容格式正确
                                placeholder_content = (
                                    placeholder_content.replace("\r\n", "\n")
                                    .replace("\r", "\n")
                                    .replace("\n", "\r\n")
                                )

                                # 确保内容以CRLF结尾
                                if not placeholder_content.endswith("\r\n"):
                                    placeholder_content += "\r\n"

                                # 发送邮件内容
                                self.send_response(f"+OK {content_size} octets")

                                # 发送邮件内容（按行）
                                for line in placeholder_content.split("\r\n"):
                                    # 处理行开头的点（透明性规则）
                                    if line.startswith("."):
                                        line = "." + line
                                    self.send_response(line)

                                # 结束标记
                                self.send_response(".")
                                logger.info(f"已发送邮件占位内容: {message_id}")
                                return True
                        except Exception as e:
                            logger.error(f"构建占位邮件内容时出错: {e}")

                        # 如果无法构建占位内容，返回错误
                        self.send_response("-ERR Message content not found")
                except Exception as e:
                    logger.error(f"获取邮件内容时出错: {e}")
                    import traceback

                    logger.error(f"异常详情: {traceback.format_exc()}")
                    # 正确处理错误
                    self.send_response("-ERR Failed to retrieve message content")
            else:
                logger.warning(
                    f"无效的邮件编号: {msg_num}, 范围: 1-{len(self.cached_emails)}"
                )
                self.send_response(
                    f"-ERR No such message, index {msg_num} out of range 1-{len(self.cached_emails)}"
                )
        except ValueError:
            logger.warning(f"无效的邮件编号格式: {arg}")
            self.send_response(f"-ERR Invalid message number: {arg}")
        except Exception as e:
            logger.error(f"处理RETR命令时出错: {e}")
            import traceback

            logger.error(f"异常详情: {traceback.format_exc()}")
            self.send_response("-ERR Internal server error")

        return True

    def process_dele(self, arg: str) -> bool:
        """
        处理DELE命令

        Args:
            arg: 邮件编号

        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True

        if not arg:
            self.send_response("-ERR Message number required")
            return True

        try:
            msg_num = int(arg)

            # 使用缓存的邮件列表
            if not self.cached_emails:
                try:
                    # 如果缓存为空，重新获取邮件列表 - 使用用户的邮箱地址而不是用户名
                    self.cached_emails = self.email_service.list_emails(
                        user_email=self.user_email,
                        include_deleted=False,
                        include_spam=False,
                        include_recalled=False,
                    )
                    logger.debug(
                        f"已为用户 {self.authenticated_user} 加载 {len(self.cached_emails)} 封邮件"
                    )
                except Exception as e:
                    logger.error(f"获取邮件列表时出错: {e}")
                    self.send_response("-ERR Database error")
                    return True

            if 1 <= msg_num <= len(self.cached_emails):
                email = self.cached_emails[msg_num - 1]
                message_id = email["message_id"]

                # 检查邮件是否已经标记为删除
                if message_id in self.marked_for_deletion:
                    logger.warning(f"邮件已经标记为删除: {message_id}")
                    self.send_response(f"+OK Message {msg_num} already deleted")
                    return True

                # 标记为删除
                self.marked_for_deletion.add(message_id)
                logger.info(f"邮件已标记为删除: {message_id}")

                self.send_response(f"+OK Message {msg_num} deleted")
            else:
                logger.warning(
                    f"无效的邮件编号: {msg_num}, 范围: 1-{len(self.cached_emails)}"
                )
                self.send_response(
                    f"-ERR No such message, index {msg_num} out of range 1-{len(self.cached_emails)}"
                )
        except ValueError:
            logger.warning(f"无效的邮件编号格式: {arg}")
            self.send_response(f"-ERR Invalid message number: {arg}")
        except Exception as e:
            logger.error(f"处理DELE命令时出错: {e}")
            self.send_response("-ERR Internal server error")

        return True

    def process_noop(self) -> bool:
        """
        处理NOOP命令

        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True

        self.send_response("+OK")
        return True

    def process_rset(self) -> bool:
        """
        处理RSET命令

        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True

        # 清除删除标记
        self.marked_for_deletion.clear()

        self.send_response("+OK")
        return True

    def process_top(self, arg: str) -> bool:
        """
        处理TOP命令

        Args:
            arg: "msg_num n"，其中n是要返回的行数

        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True

        parts = arg.split()
        if len(parts) != 2:
            self.send_response("-ERR Usage: TOP msg_num n")
            return True

        try:
            msg_num = int(parts[0])
            n_lines = int(parts[1])

            # 获取邮件列表 - 使用用户的邮箱地址而不是用户名
            emails = self.email_service.list_emails(
                user_email=self.user_email,
                include_deleted=False,
                include_spam=False,
                include_recalled=False,
            )

            if 1 <= msg_num <= len(emails):
                email = emails[msg_num - 1]

                # 获取邮件内容
                content = self.email_service.get_email_content(email["message_id"])

                if content:
                    # 确保内容格式正确，处理不同的换行符情况
                    content = (
                        content.replace("\r\n", "\n")
                        .replace("\r", "\n")
                        .replace("\n", "\r\n")
                    )

                    # 分割头部和正文
                    parts = content.split("\r\n\r\n", 1)
                    header = parts[0]
                    body = parts[1] if len(parts) > 1 else ""

                    # 发送头部
                    self.send_response(f"+OK")

                    # 发送头部（按行）
                    for line in header.split("\r\n"):
                        # 处理行开头的点（透明性规则）
                        if line.startswith("."):
                            line = "." + line
                        self.send_response(line)

                    # 发送空行
                    self.send_response("")

                    # 发送正文的前n行
                    body_lines = body.split("\r\n")
                    sent_lines = 0
                    for i, line in enumerate(body_lines):
                        if i >= n_lines:
                            break

                        # 处理行开头的点（透明性规则）
                        if line.startswith("."):
                            line = "." + line
                        self.send_response(line)
                        sent_lines += 1

                    # 添加调试日志
                    header_lines = header.count("\r\n") + 1
                    logger.debug(
                        f"TOP命令: 发送了 {header_lines} 行头部和 {sent_lines} 行正文"
                    )

                    # 结束标记
                    self.send_response(".")
                else:
                    self.send_response("-ERR Message content not found")
            else:
                self.send_response(f"-ERR No such message")
        except ValueError:
            self.send_response(f"-ERR Invalid parameters")

        return True

    def process_uidl(self, arg: str) -> bool:
        """
        处理UIDL命令

        Args:
            arg: 可选的邮件编号

        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True

        # 使用缓存的邮件列表
        if not self.cached_emails:
            try:
                # 如果缓存为空，重新获取邮件列表 - 使用用户的邮箱地址而不是用户名
                self.cached_emails = self.email_service.list_emails(
                    user_email=self.user_email,
                    include_deleted=False,
                    include_spam=False,
                    include_recalled=False,
                )
                logger.debug(
                    f"已为用户 {self.authenticated_user} 加载 {len(self.cached_emails)} 封邮件"
                )
            except Exception as e:
                logger.error(f"获取邮件列表时出错: {e}")
                self.send_response("-ERR Database error")
                return True

        # 如果指定了邮件编号
        if arg:
            try:
                msg_num = int(arg)
                if 1 <= msg_num <= len(self.cached_emails):
                    email = self.cached_emails[msg_num - 1]
                    # 使用Message-ID作为唯一标识符
                    message_id = email["message_id"]
                    # 移除尖括号，确保符合POP3协议
                    safe_id = message_id.strip("<>")
                    self.send_response(f"+OK {msg_num} {safe_id}")
                else:
                    self.send_response(
                        f"-ERR No such message, index {msg_num} out of range 1-{len(self.cached_emails)}"
                    )
            except ValueError:
                self.send_response(f"-ERR Invalid message number: {arg}")
        else:
            # 返回所有邮件
            self.send_response(f"+OK")
            for i, email in enumerate(self.cached_emails, 1):
                # 使用Message-ID作为唯一标识符
                message_id = email["message_id"]
                # 移除尖括号，确保符合POP3协议
                safe_id = message_id.strip("<>")
                self.send_response(f"{i} {safe_id}")
            self.send_response(".")

        return True

    def perform_deletions(self) -> None:
        """执行删除操作"""
        for message_id in self.marked_for_deletion:
            self.email_service.mark_email_as_deleted(message_id)

        logger.info(f"已删除{len(self.marked_for_deletion)}封邮件")
        self.marked_for_deletion.clear()
