"""
邮件导入工具 - 扫描邮件目录，将.eml文件导入到数据库
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from email import policy
from email.parser import BytesParser
import datetime
import re

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging, safe_print
from common.config import EMAIL_STORAGE_DIR
from server.db_handler import DatabaseHandler
from client.pop3_client import POP3Client
from client.mime_handler import MIMEHandler

# 设置日志
logger = setup_logging("import_emails")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="邮件导入工具")
    parser.add_argument(
        "--dir",
        type=str,
        default=EMAIL_STORAGE_DIR,
        help="邮件目录路径，默认为配置中的EMAIL_STORAGE_DIR",
    )
    parser.add_argument(
        "--sent-dir", type=str, help="已发送邮件目录路径，默认为EMAIL_STORAGE_DIR/sent"
    )
    parser.add_argument(
        "--force", action="store_true", help="强制重新导入所有邮件，即使数据库中已存在"
    )
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")
    return parser.parse_args()


def import_received_emails(directory, db_handler, force=False, verbose=False):
    """导入接收的邮件"""
    if not os.path.exists(directory):
        print(f"目录不存在: {directory}")
        return 0

    # 获取所有.eml文件
    eml_files = [
        f
        for f in os.listdir(directory)
        if f.endswith(".eml") and os.path.isfile(os.path.join(directory, f))
    ]

    if not eml_files:
        print(f"目录中没有.eml文件: {directory}")
        return 0

    print(f"找到{len(eml_files)}个.eml文件")

    # 创建POP3客户端实例（仅用于解析邮件）
    pop3_client = POP3Client()

    # 导入计数
    imported_count = 0

    for eml_file in eml_files:
        file_path = os.path.join(directory, eml_file)

        try:
            # 解析.eml文件
            with open(file_path, "rb") as f:
                parser = BytesParser(policy=policy.default)
                msg = parser.parse(f)

            # 提取消息ID
            message_id = msg.get("Message-ID", "")
            if not message_id:
                # 如果没有Message-ID，尝试从文件名生成一个
                message_id = f"<{os.path.splitext(eml_file)[0]}@imported>"

            # 检查数据库中是否已存在
            if not force and db_handler.get_email_metadata(message_id):
                if verbose:
                    print(f"跳过已存在的邮件: {message_id}")
                continue

            # 转换为Email对象
            email_obj = pop3_client._convert_to_email(msg)

            # 计算正确的content_path
            # 确保邮件ID不包含非法字符
            safe_id = email_obj.message_id.strip().strip("<>").replace("@", "_at_")
            # 移除Windows文件系统不允许的字符
            safe_id = re.sub(r'[\\/*?:"<>|]', "_", safe_id)
            # 确保没有前导或尾随空格
            safe_id = safe_id.strip()

            correct_path = os.path.join(
                EMAIL_STORAGE_DIR,
                f"{safe_id}.eml",
            )

            # 复制文件到正确的位置（如果源文件和目标文件不同）
            os.makedirs(os.path.dirname(correct_path), exist_ok=True)

            # 规范化路径以进行比较
            norm_file_path = os.path.normpath(os.path.abspath(file_path))
            norm_correct_path = os.path.normpath(os.path.abspath(correct_path))

            # 只有当源文件和目标文件不同时才进行复制
            if norm_file_path != norm_correct_path:
                shutil.copy2(file_path, correct_path)
            else:
                # 源文件和目标文件相同，不需要复制
                logger.info(f"源文件和目标文件相同，跳过复制: {file_path}")
                if verbose:
                    print(f"源文件和目标文件相同，跳过复制: {file_path}")

            # 保存元数据到数据库
            try:
                # 如果是强制模式，先尝试删除已存在的记录
                if force:
                    db_handler.delete_email_metadata(email_obj.message_id)

                db_handler.save_email_metadata(
                    message_id=email_obj.message_id,
                    from_addr=email_obj.from_addr.address,
                    to_addrs=[addr.address for addr in email_obj.to_addrs],
                    subject=email_obj.subject,
                    date=email_obj.date,
                    size=os.path.getsize(correct_path),
                    is_spam=False,
                    spam_score=0.0,
                )
            except Exception as e:
                logger.error(f"保存邮件元数据时出错: {e}")
                if verbose:
                    print(f"保存邮件元数据时出错: {e}")
                # 即使保存元数据失败，也继续处理下一封邮件
                continue

            imported_count += 1
            if verbose:
                safe_print(f"已导入邮件: {email_obj.subject}")
        except Exception as e:
            logger.error(f"导入邮件失败: {file_path}, 错误: {e}")
            if verbose:
                print(f"导入邮件失败: {file_path}, 错误: {e}")

    return imported_count


def import_sent_emails(directory, db_handler, force=False, verbose=False):
    """导入已发送的邮件"""
    if not os.path.exists(directory):
        print(f"目录不存在: {directory}")
        return 0

    # 获取所有.eml文件
    eml_files = [
        f
        for f in os.listdir(directory)
        if f.endswith(".eml") and os.path.isfile(os.path.join(directory, f))
    ]

    if not eml_files:
        print(f"目录中没有.eml文件: {directory}")
        return 0

    print(f"找到{len(eml_files)}个已发送的.eml文件")

    # 导入计数
    imported_count = 0

    for eml_file in eml_files:
        file_path = os.path.join(directory, eml_file)

        try:
            # 解析.eml文件
            email_obj = MIMEHandler.parse_eml_file(file_path)

            # 检查数据库中是否已存在
            if not force and db_handler.get_sent_email_metadata(email_obj.message_id):
                if verbose:
                    print(f"跳过已存在的已发送邮件: {email_obj.message_id}")
                continue

            # 保存元数据到数据库
            try:
                # 如果是强制模式，先尝试删除已存在的记录
                if force:
                    db_handler.delete_sent_email_metadata(email_obj.message_id)

                db_handler.save_sent_email_metadata(email_obj, file_path)
            except Exception as e:
                logger.error(f"保存已发送邮件元数据时出错: {e}")
                if verbose:
                    print(f"保存已发送邮件元数据时出错: {e}")
                # 即使保存元数据失败，也继续处理下一封邮件
                continue

            imported_count += 1
            if verbose:
                safe_print(f"已导入已发送邮件: {email_obj.subject}")
        except Exception as e:
            logger.error(f"导入已发送邮件失败: {file_path}, 错误: {e}")
            if verbose:
                print(f"导入已发送邮件失败: {file_path}, 错误: {e}")

    return imported_count


def main():
    """主函数"""
    args = parse_args()

    # 创建数据库处理器
    db_handler = DatabaseHandler()

    # 导入接收的邮件
    received_count = import_received_emails(
        args.dir, db_handler, force=args.force, verbose=args.verbose
    )

    # 导入已发送的邮件
    sent_dir = args.sent_dir or os.path.join(args.dir, "sent")
    sent_count = import_sent_emails(
        sent_dir, db_handler, force=args.force, verbose=args.verbose
    )

    print(f"导入完成: {received_count}封接收邮件, {sent_count}封已发送邮件")


if __name__ == "__main__":
    main()
