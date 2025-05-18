"""
邮件查看工具 - 以友好的格式查看.eml文件内容
"""
import os
import sys
import argparse
from pathlib import Path
from email import policy
from email.parser import BytesParser
import datetime
import re
import html
from email.header import decode_header

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging, safe_print
from client.mime_handler import MIMEHandler

# 设置日志
logger = setup_logging('view_email')

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='邮件查看工具')
    parser.add_argument('file_path', type=str, help='.eml文件路径')
    parser.add_argument('--raw', action='store_true', help='显示原始内容')
    parser.add_argument('--html', action='store_true', help='显示HTML内容')
    parser.add_argument('--text', action='store_true', help='显示纯文本内容')
    parser.add_argument('--headers', action='store_true', help='只显示邮件头')
    parser.add_argument('--attachments', action='store_true', help='只显示附件信息')
    parser.add_argument('--extract', type=str, help='提取附件到指定目录')
    return parser.parse_args()

def decode_str(s):
    """解码字符串，处理各种编码"""
    if s is None:
        return ""
    
    # 如果是bytes，尝试解码
    if isinstance(s, bytes):
        try:
            return s.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return s.decode('gbk')
            except UnicodeDecodeError:
                return s.decode('latin1')
    
    # 如果是字符串，直接返回
    return s

def decode_header_str(header_str):
    """解码邮件头部字符串"""
    if not header_str:
        return ""
    
    decoded_parts = []
    for part, encoding in decode_header(header_str):
        if isinstance(part, bytes):
            if encoding:
                try:
                    decoded_parts.append(part.decode(encoding))
                except (UnicodeDecodeError, LookupError):
                    try:
                        decoded_parts.append(part.decode('utf-8'))
                    except UnicodeDecodeError:
                        decoded_parts.append(part.decode('latin1', errors='replace'))
            else:
                try:
                    decoded_parts.append(part.decode('utf-8'))
                except UnicodeDecodeError:
                    decoded_parts.append(part.decode('latin1', errors='replace'))
        else:
            decoded_parts.append(part)
    
    return ''.join(decoded_parts)

def print_headers(msg):
    """打印邮件头部信息"""
    print("=" * 80)
    print("邮件头部信息:")
    print("-" * 80)
    
    # 常见头部字段
    important_headers = [
        'From', 'To', 'Cc', 'Bcc', 'Subject', 'Date', 
        'Message-ID', 'In-Reply-To', 'References'
    ]
    
    # 先打印重要的头部
    for header in important_headers:
        if header in msg:
            value = decode_header_str(msg[header])
            safe_print(f"{header}: {value}")
    
    # 再打印其他头部
    print("-" * 80)
    print("其他头部字段:")
    for header, value in msg.items():
        if header not in important_headers:
            value = decode_header_str(value)
            safe_print(f"{header}: {value}")
    
    print("=" * 80)

def print_text_content(msg):
    """打印纯文本内容"""
    print("=" * 80)
    print("纯文本内容:")
    print("-" * 80)
    
    # 查找纯文本部分
    text_content = ""
    
    # 如果是简单邮件
    if msg.get_content_type() == 'text/plain':
        text_content = decode_str(msg.get_content())
    else:
        # 遍历所有部分
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                text_content += decode_str(part.get_content())
    
    if text_content:
        safe_print(text_content)
    else:
        print("没有找到纯文本内容")
    
    print("=" * 80)

def print_html_content(msg):
    """打印HTML内容"""
    print("=" * 80)
    print("HTML内容:")
    print("-" * 80)
    
    # 查找HTML部分
    html_content = ""
    
    # 如果是简单邮件
    if msg.get_content_type() == 'text/html':
        html_content = decode_str(msg.get_content())
    else:
        # 遍历所有部分
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                html_content += decode_str(part.get_content())
    
    if html_content:
        # 简单处理HTML，移除标签
        html_text = re.sub(r'<[^>]+>', ' ', html_content)
        html_text = re.sub(r'\s+', ' ', html_text)
        html_text = html.unescape(html_text)
        safe_print(html_text)
    else:
        print("没有找到HTML内容")
    
    print("=" * 80)

def print_attachments(msg):
    """打印附件信息"""
    print("=" * 80)
    print("附件信息:")
    print("-" * 80)
    
    attachment_count = 0
    
    # 遍历所有部分
    for part in msg.walk():
        # 检查是否是附件
        if part.get_content_disposition() == 'attachment':
            attachment_count += 1
            filename = decode_header_str(part.get_filename())
            content_type = part.get_content_type()
            size = len(part.get_payload(decode=True))
            
            safe_print(f"附件 {attachment_count}:")
            safe_print(f"  文件名: {filename}")
            safe_print(f"  类型: {content_type}")
            safe_print(f"  大小: {size} 字节")
            print()
    
    if attachment_count == 0:
        print("没有找到附件")
    
    print("=" * 80)

def extract_attachments(msg, output_dir):
    """提取附件到指定目录"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    attachment_count = 0
    
    # 遍历所有部分
    for part in msg.walk():
        # 检查是否是附件
        if part.get_content_disposition() == 'attachment':
            attachment_count += 1
            filename = decode_header_str(part.get_filename())
            
            # 确保文件名安全
            filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
            
            # 保存附件
            file_path = os.path.join(output_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(part.get_payload(decode=True))
            
            safe_print(f"已提取附件: {filename} -> {file_path}")
    
    if attachment_count == 0:
        print("没有找到附件")
    else:
        print(f"共提取了 {attachment_count} 个附件到 {output_dir}")

def print_email_summary(msg):
    """打印邮件摘要"""
    print("=" * 80)
    print("邮件摘要:")
    print("-" * 80)
    
    # 发件人
    from_addr = decode_header_str(msg.get('From', ''))
    safe_print(f"发件人: {from_addr}")
    
    # 收件人
    to_addr = decode_header_str(msg.get('To', ''))
    safe_print(f"收件人: {to_addr}")
    
    # 抄送
    cc_addr = decode_header_str(msg.get('Cc', ''))
    if cc_addr:
        safe_print(f"抄送: {cc_addr}")
    
    # 主题
    subject = decode_header_str(msg.get('Subject', ''))
    safe_print(f"主题: {subject}")
    
    # 日期
    date = decode_header_str(msg.get('Date', ''))
    safe_print(f"日期: {date}")
    
    # 附件数量
    attachment_count = 0
    for part in msg.walk():
        if part.get_content_disposition() == 'attachment':
            attachment_count += 1
    
    if attachment_count > 0:
        print(f"附件数量: {attachment_count}")
    
    print("=" * 80)

def main():
    """主函数"""
    args = parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.file_path):
        print(f"文件不存在: {args.file_path}")
        return
    
    try:
        # 解析.eml文件
        with open(args.file_path, 'rb') as f:
            parser = BytesParser(policy=policy.default)
            msg = parser.parse(f)
        
        # 根据参数显示不同内容
        if args.raw:
            # 显示原始内容
            with open(args.file_path, 'r', encoding='utf-8', errors='replace') as f:
                print(f.read())
        elif args.headers:
            # 只显示邮件头
            print_headers(msg)
        elif args.text:
            # 只显示纯文本内容
            print_text_content(msg)
        elif args.html:
            # 只显示HTML内容
            print_html_content(msg)
        elif args.attachments:
            # 只显示附件信息
            print_attachments(msg)
        elif args.extract:
            # 提取附件
            extract_attachments(msg, args.extract)
        else:
            # 显示摘要和内容
            print_email_summary(msg)
            print_text_content(msg)
            print_attachments(msg)
    
    except Exception as e:
        logger.error(f"查看邮件失败: {e}")
        print(f"查看邮件失败: {e}")

if __name__ == "__main__":
    main()
