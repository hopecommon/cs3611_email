#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的邮件服务 - 直接使用SMTP/POP3客户端
"""

import sys
import os
import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.models import Email, EmailAddress, Attachment
from client.smtp_client import SMTPClient
from client.pop3_client_refactored import POP3ClientRefactored
from server.new_db_handler import EmailService

# 设置日志
logger = setup_logging("simple_email_service")


class SimpleEmailService:
    """简化的邮件服务类"""

    def __init__(self, user):
        """
        初始化邮件服务

        Args:
            user: 用户对象（包含邮箱配置）
        """
        self.user = user
        self.db_service = EmailService()

    def send_email(
        self,
        to_addresses,
        subject,
        content,
        cc_addresses=None,
        bcc_addresses=None,
        attachments=None,
        content_type="text",
    ):
        """
        发送邮件

        Args:
            to_addresses: 收件人列表
            subject: 邮件主题
            content: 邮件内容
            cc_addresses: 抄送列表
            bcc_addresses: 密送列表
            attachments: 附件列表
            content_type: 内容类型 ('text' 或 'html')

        Returns:
            dict: 发送结果
        """
        try:
            logger.info(f"开始发送邮件: {subject} -> {to_addresses}")

            # 获取SMTP配置
            smtp_config = self.user.get_smtp_config()
            if not smtp_config:
                return {"success": False, "error": "无法获取SMTP配置"}

            # 创建邮件对象
            email = Email(
                message_id="",  # 让SMTP客户端自动生成
                from_addr=EmailAddress(name=self.user.email, address=self.user.email),
                to_addrs=[
                    EmailAddress(name=addr.strip(), address=addr.strip())
                    for addr in to_addresses
                ],
                subject=subject,
                text_content=content if content_type == "text" else None,
                html_content=content if content_type == "html" else None,
                date=datetime.datetime.now(),
            )

            # 处理抄送和密送
            if cc_addresses:
                email.cc_addrs = [
                    EmailAddress(name=addr.strip(), address=addr.strip())
                    for addr in cc_addresses
                ]
            if bcc_addresses:
                email.bcc_addrs = [
                    EmailAddress(name=addr.strip(), address=addr.strip())
                    for addr in bcc_addresses
                ]

            # 处理附件
            if attachments:
                email.attachments = []
                for attachment in attachments:
                    if hasattr(attachment, "read"):  # 文件对象
                        email.attachments.append(
                            Attachment(
                                filename=getattr(attachment, "filename", "attachment"),
                                content=attachment.read(),
                                content_type="application/octet-stream",
                            )
                        )

            # 创建SMTP客户端并发送
            # 为QQ邮箱使用特殊配置
            is_qq_email = "qq.com" in smtp_config["host"].lower()
            auth_method = (
                "LOGIN" if is_qq_email else smtp_config.get("auth_method", "AUTO")
            )

            logger.info(
                f"为{'QQ邮箱' if is_qq_email else '其他邮箱'}创建SMTP客户端，认证方法: {auth_method}"
            )

            smtp_client = SMTPClient(
                host=smtp_config["host"],
                port=smtp_config["port"],
                use_ssl=smtp_config["use_ssl"],
                username=smtp_config["username"],
                password=smtp_config["password"],
                auth_method=auth_method,
                timeout=30,
                save_sent_emails=False,  # 禁用保存邮件到文件
                max_retries=1,  # 减少重试次数，让我们的逻辑处理重连
            )

            # 发送邮件
            success = self._direct_send_email(smtp_client, email)

            if success:
                logger.info(f"邮件发送成功: {subject}")
                return {"success": True, "message": "邮件发送成功"}
            else:
                logger.error(f"邮件发送失败: {subject}")
                return {"success": False, "error": "邮件发送失败"}

        except Exception as e:
            logger.error(f"发送邮件异常: {e}")
            return {"success": False, "error": f"发送邮件时出错: {str(e)}"}

    def _direct_send_email(self, smtp_client, email):
        """
        直接发送邮件，完全绕过SMTP客户端的重连逻辑
        """
        try:
            # 确保SMTP客户端已连接
            if not smtp_client.connection:
                logger.info("SMTP客户端未连接，正在建立连接...")
                smtp_client.connect()
                logger.info("SMTP连接建立成功")

            # 特殊处理QQ邮箱：确保EHLO状态正确
            is_qq_email = "qq.com" in smtp_client.host.lower()
            if is_qq_email:
                logger.info("检测到QQ邮箱，执行特殊处理...")
                try:
                    # 强制重新执行EHLO命令
                    code, response = smtp_client.connection.ehlo()
                    logger.info(f"QQ邮箱EHLO响应: {code} {response}")
                    if code != 250:
                        logger.warning(f"QQ邮箱EHLO失败: {code} {response}")
                        # 重新连接
                        smtp_client.disconnect()
                        smtp_client.connect()
                except Exception as ehlo_e:
                    logger.warning(f"QQ邮箱EHLO失败，重新连接: {ehlo_e}")
                    smtp_client.disconnect()
                    smtp_client.connect()
            else:
                # 验证连接状态
                try:
                    # 发送NOOP命令测试连接
                    code, response = smtp_client.connection.noop()
                    if code != 250:
                        logger.warning(f"SMTP连接状态异常: {code} {response}")
                        # 重新连接
                        smtp_client.disconnect()
                        smtp_client.connect()
                except Exception as noop_e:
                    logger.warning(f"SMTP连接测试失败，重新连接: {noop_e}")
                    smtp_client.disconnect()
                    smtp_client.connect()

            # 导入EmailFormatHandler
            from common.email_format_handler import EmailFormatHandler

            # 创建MIME消息
            logger.info("正在创建MIME消息...")
            mime_msg = EmailFormatHandler.create_mime_message(email)

            # 准备收件人列表
            all_recipients = []
            all_recipients.extend([addr.address for addr in email.to_addrs])
            all_recipients.extend([addr.address for addr in email.cc_addrs])
            all_recipients.extend([addr.address for addr in email.bcc_addrs])

            # 发件人地址
            from_addr = email.from_addr.address

            logger.info(f"准备发送邮件: {from_addr} -> {all_recipients}")
            logger.info(f"邮件主题: {email.subject}")

            # 对于QQ邮箱，在发送前再次验证连接状态
            if is_qq_email:
                try:
                    # 验证连接是否仍然有效
                    code, response = smtp_client.connection.noop()
                    logger.info(f"QQ邮箱发送前NOOP检查: {code} {response}")
                except Exception as noop_e:
                    logger.warning(f"QQ邮箱发送前状态检查失败: {noop_e}")
                    # 重新连接但不重新认证（保持现有连接）
                    raise Exception("连接状态无效，需要重新连接")

            # 直接使用SMTP连接发送邮件，不经过send_email方法
            logger.info("正在发送邮件...")
            smtp_client.connection.send_message(mime_msg, from_addr, all_recipients)

            logger.info(f"邮件发送成功: {email.subject}")
            return True

        except Exception as e:
            logger.error(f"直接发送邮件失败: {e}")

            # 如果发送失败，可能是连接问题，尝试重新连接一次
            try:
                logger.info("发送失败，尝试重新连接SMTP服务器...")
                smtp_client.disconnect()
                smtp_client.connect()

                # 对于QQ邮箱，在重连后再次执行EHLO
                if "qq.com" in smtp_client.host.lower():
                    logger.info("QQ邮箱重连后执行EHLO...")
                    code, response = smtp_client.connection.ehlo()
                    logger.info(f"QQ邮箱重连后EHLO: {code} {response}")

                # 重新创建MIME消息（防止状态问题）
                mime_msg = EmailFormatHandler.create_mime_message(email)

                # 重新发送
                logger.info("重新连接成功，再次尝试发送邮件...")
                smtp_client.connection.send_message(mime_msg, from_addr, all_recipients)

                logger.info(f"重连后邮件发送成功: {email.subject}")
                return True

            except Exception as retry_e:
                logger.error(f"重连后仍然发送失败: {retry_e}")
                return False

    def receive_emails(self, limit=10, only_new=True):
        """
        接收邮件

        Args:
            limit: 最多接收邮件数量
            only_new: 是否只接收新邮件

        Returns:
            dict: 接收结果
        """
        try:
            logger.info(f"开始接收邮件，限制: {limit}, 仅新邮件: {only_new}")

            # 获取POP3配置
            pop3_config = self.user.get_pop3_config()
            if not pop3_config:
                return {"success": False, "error": "无法获取POP3配置"}

            # 创建POP3客户端
            pop3_client = POP3ClientRefactored(
                host=pop3_config["host"],
                port=pop3_config["port"],
                use_ssl=pop3_config["use_ssl"],
                username=pop3_config["username"],
                password=pop3_config["password"],
                auth_method=pop3_config.get("auth_method", "AUTO"),
            )

            # 接收邮件
            with pop3_client as client:
                if only_new:
                    # 只获取最新邮件
                    emails = client.retrieve_all_emails(limit=limit)
                else:
                    # 获取所有邮件
                    emails = client.retrieve_all_emails(limit=limit)

                # 保存到数据库
                new_count = 0
                for email in emails:
                    try:
                        # 检查邮件是否已存在
                        existing_email = self.db_service.get_email(email.message_id)
                        if not existing_email:
                            self.db_service.save_email(
                                message_id=email.message_id,
                                from_addr=email.from_addr.address,
                                to_addrs=[addr.address for addr in email.to_addrs],
                                subject=email.subject,
                                content=email.text_content or email.html_content or "",
                                date=email.date,
                            )
                            new_count += 1
                    except Exception as save_e:
                        logger.warning(f"保存邮件失败: {save_e}")

                logger.info(f"接收邮件完成，新邮件: {new_count}")
                return {
                    "success": True,
                    "total": len(emails),
                    "new_emails": new_count,
                    "message": f"成功接收 {len(emails)} 封邮件，其中 {new_count} 封为新邮件",
                }

        except Exception as e:
            logger.error(f"接收邮件异常: {e}")
            return {"success": False, "error": f"接收邮件时出错: {str(e)}"}

    def get_inbox_emails(self, page=1, per_page=20):
        """
        获取收件箱邮件列表

        Args:
            page: 页码
            per_page: 每页数量

        Returns:
            dict: 邮件列表
        """
        try:
            offset = (page - 1) * per_page
            emails = self.db_service.list_emails(
                user_email=self.user.email, limit=per_page, offset=offset
            )

            total = self.db_service.get_email_count(user_email=self.user.email)

            return {
                "success": True,
                "emails": emails,
                "total": total,
                "page": page,
                "per_page": per_page,
            }

        except Exception as e:
            logger.error(f"获取收件箱邮件异常: {e}")
            return {"success": False, "error": f"获取邮件列表时出错: {str(e)}"}

    def get_sent_emails(self, page=1, per_page=20):
        """
        获取发件箱邮件列表

        Args:
            page: 页码
            per_page: 每页数量

        Returns:
            dict: 邮件列表
        """
        try:
            offset = (page - 1) * per_page
            emails = self.db_service.list_sent_emails(
                from_addr=self.user.email, limit=per_page, offset=offset
            )

            # 计算总数（简化实现）
            all_sent = self.db_service.list_sent_emails(from_addr=self.user.email)
            total = len(all_sent)

            return {
                "success": True,
                "emails": emails,
                "total": total,
                "page": page,
                "per_page": per_page,
            }

        except Exception as e:
            logger.error(f"获取发件箱邮件异常: {e}")
            return {"success": False, "error": f"获取发件箱邮件时出错: {str(e)}"}

    def get_email_by_id(self, message_id):
        """
        根据消息ID获取邮件

        Args:
            message_id: 邮件消息ID

        Returns:
            dict: 邮件详情
        """
        try:
            email = self.db_service.get_email_by_id(message_id)
            if email:
                return {"success": True, "email": email}
            else:
                return {"success": False, "error": "邮件不存在"}

        except Exception as e:
            logger.error(f"获取邮件详情异常: {e}")
            return {"success": False, "error": f"获取邮件详情时出错: {str(e)}"}

    def delete_email(self, message_id):
        """
        删除邮件

        Args:
            message_id: 邮件消息ID

        Returns:
            dict: 删除结果
        """
        try:
            success = self.db_service.delete_email(message_id)
            if success:
                return {"success": True, "message": "邮件删除成功"}
            else:
                return {"success": False, "error": "邮件删除失败"}

        except Exception as e:
            logger.error(f"删除邮件异常: {e}")
            return {"success": False, "error": f"删除邮件时出错: {str(e)}"}

    def test_connection(self):
        """
        测试邮箱连接

        Returns:
            dict: 测试结果
        """
        try:
            results = {"smtp": False, "pop3": False}

            # 测试SMTP连接
            try:
                smtp_config = self.user.get_smtp_config()
                if smtp_config:
                    smtp_client = SMTPClient(
                        host=smtp_config["host"],
                        port=smtp_config["port"],
                        use_ssl=smtp_config["use_ssl"],
                        username=smtp_config["username"],
                        password=smtp_config["password"],
                        timeout=10,
                    )
                    smtp_client.connect()
                    smtp_client.disconnect()
                    results["smtp"] = True
            except Exception as smtp_e:
                logger.debug(f"SMTP连接测试失败: {smtp_e}")

            # 测试POP3连接
            try:
                pop3_config = self.user.get_pop3_config()
                if pop3_config:
                    pop3_client = POP3ClientRefactored(
                        host=pop3_config["host"],
                        port=pop3_config["port"],
                        use_ssl=pop3_config["use_ssl"],
                        username=pop3_config["username"],
                        password=pop3_config["password"],
                        timeout=10,
                    )
                    pop3_client.connect()
                    pop3_client.disconnect()
                    results["pop3"] = True
            except Exception as pop3_e:
                logger.debug(f"POP3连接测试失败: {pop3_e}")

            return {"success": True, "results": results}

        except Exception as e:
            logger.error(f"连接测试异常: {e}")
            return {"success": False, "error": f"连接测试时出错: {str(e)}"}


def get_email_service(user):
    """
    获取邮件服务实例

    Args:
        user: 用户对象

    Returns:
        SimpleEmailService: 邮件服务实例
    """
    return SimpleEmailService(user)
