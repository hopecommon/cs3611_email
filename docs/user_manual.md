# 邮件客户端用户手册

本手册提供了邮件客户端的详细使用说明，帮助用户快速上手并充分利用所有功能。

## 目录

1. [安装与配置](#安装与配置)
2. [基本使用](#基本使用)
3. [发送邮件](#发送邮件)
4. [接收邮件](#接收邮件)
5. [管理邮件](#管理邮件)
6. [高级功能](#高级功能)
7. [故障排除](#故障排除)
8. [常见问题](#常见问题)

## 安装与配置

### 系统要求

- Python 3.8 或更高版本
- 操作系统：Windows、macOS 或 Linux
- 网络连接

### 安装步骤

1. 克隆或下载项目代码：
   ```bash
   git clone https://github.com/yourusername/cs3611_email.git
   cd cs3611_email
   ```

2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

3. 初始化项目：
   ```bash
   python init_project.py
   ```

### 配置邮箱账户

编辑 `common/config.py` 文件，配置你的邮箱账户信息：

```python
# SMTP服务器配置
SMTP_SERVER = {
    "host": "smtp.example.com",  # SMTP服务器地址
    "port": 25,                  # SMTP服务器端口
    "use_ssl": True,             # 是否使用SSL/TLS
    "username": "your_email@example.com",  # 邮箱账户
    "password": "your_password",           # 邮箱密码或授权码
    "auth_method": "AUTO"        # 认证方法：AUTO, LOGIN, PLAIN
}

# POP3服务器配置
POP3_SERVER = {
    "host": "pop.example.com",   # POP3服务器地址
    "port": 110,                 # POP3服务器端口
    "use_ssl": True,             # 是否使用SSL/TLS
    "username": "your_email@example.com",  # 邮箱账户
    "password": "your_password",           # 邮箱密码或授权码
    "auth_method": "AUTO"        # 认证方法：AUTO, BASIC, APOP
}
```

**注意**：对于QQ邮箱，`password` 应该是授权码而不是登录密码。你可以在QQ邮箱设置中获取授权码。

## 基本使用

### 交互式命令行界面

邮件客户端提供了一个交互式命令行界面，可以通过菜单选择不同的操作。启动交互式界面：

```bash
python cli.py
```

交互式界面提供以下功能：
- 发送邮件（纯文本、HTML、带附件）
- 接收邮件（全部、最新、未读）
- 查看邮件列表（收件箱、已发送）
- 搜索邮件（按发件人、主题、内容、日期）
- 账户设置（SMTP、POP3服务器配置）

### 命令行参数

也可以通过命令行参数直接执行特定操作：

```bash
python cli.py [选项]
```

常用选项：
- `--interactive`, `-i`：启动交互式界面
- `--send`, `-s`：发送指定的.eml文件
- `--receive`, `-r`：接收邮件
- `--list`, `-l`：列出邮件
- `--view`, `-v`：查看指定ID的邮件
- `--username`, `-u`：指定用户名
- `--password`, `-p`：指定密码

### 示例脚本

为了方便使用，我们提供了一系列示例脚本，位于 `examples` 目录下：

发送纯文本邮件：
```bash
python examples/send_text_email.py
```

发送HTML邮件：
```bash
python examples/send_html_email.py
```

发送带附件的邮件：
```bash
python examples/send_email_with_attachment.py
```

接收邮件：
```bash
python examples/receive_emails.py
```

搜索邮件：
```bash
python examples/search_emails.py "搜索关键词"
```

更多示例和详细说明请参见 [examples/README.md](../examples/README.md)。

## 发送邮件

### 创建新邮件

你可以通过以下方式创建新邮件：

1. 使用文本编辑器创建 `.eml` 文件
2. 使用提供的邮件模板
3. 使用 Python 代码创建邮件对象

#### 使用模板创建邮件（不推荐）

按照以下格式编辑：

```
From: 发件人 <sender@example.com>
To: 收件人 <recipient@example.com>
Subject: 邮件主题
Date: Wed, 18 May 2025 10:00:00 +0800
Content-Type: text/plain; charset="utf-8"

这是邮件正文内容。
```

#### 使用代码创建邮件（推荐）

以下代码摘自 `examples/send_text_email.py`：

```python
import datetime
from common.models import Email, EmailAddress, EmailStatus
from client.smtp_client import SMTPClient

# 创建SMTP客户端
smtp_client = SMTPClient(
    host="smtp.qq.com",  # 使用QQ邮箱，可以根据需要修改
    port=465,            # QQ邮箱SSL端口
    use_ssl=True,        # 使用SSL加密
    username="your_email@qq.com",  # 修改为你的邮箱地址
    password="your_password",      # 修改为你的授权码
    auth_method="AUTO"   # 自动选择认证方法
)

# 创建邮件对象
email = Email(
    message_id=f"<example.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{id(smtp_client)}@example.com>",
    subject="测试纯文本邮件",
    from_addr=EmailAddress(name="发件人", address="your_email@qq.com"),  # 必须与username一致
    to_addrs=[EmailAddress(name="收件人", address="recipient@example.com")],  # 修改为实际收件人地址
    text_content="这是一封测试纯文本邮件。\n\n这是第二段落。\n\n祝好，\n发件人",
    date=None,  # 自动设置为当前时间
    status=EmailStatus.DRAFT
)

# 发送邮件
try:
    smtp_client.connect()
    result = smtp_client.send_email(email)
    if result:
        print("邮件发送成功！")
    else:
        print("邮件发送失败！")
finally:
    smtp_client.disconnect()  # 确保连接被关闭
```

完整代码请参见 [examples/send_text_email.py](../examples/send_text_email.py)。

### 添加附件

以下代码摘自 `examples/send_email_with_attachment.py`：

```python
import os
import mimetypes
from common.models import Attachment

# 获取附件信息
attachment_path = input("请输入附件路径: ")

# 检查附件是否存在
if not os.path.exists(attachment_path):
    print(f"错误: 附件文件不存在: {attachment_path}")
    return

# 读取附件内容
try:
    with open(attachment_path, "rb") as f:
        attachment_content = f.read()
except Exception as e:
    print(f"读取附件时出错: {e}")
    return

# 获取附件文件名和类型
attachment_filename = os.path.basename(attachment_path)

# 猜测内容类型
content_type, _ = mimetypes.guess_type(attachment_filename)
if not content_type:
    content_type = "application/octet-stream"

# 创建附件对象
attachment = Attachment(
    filename=attachment_filename,
    content_type=content_type,
    content=attachment_content
)

# 添加到邮件
email.attachments.append(attachment)
```

完整代码请参见 [examples/send_email_with_attachment.py](../examples/send_email_with_attachment.py)。

### 发送HTML邮件

以下代码摘自 `examples/send_html_email.py`：

```python
# HTML内容
html_content = """
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .header { color: #0066cc; font-size: 24px; }
        .content { margin: 20px 0; }
        .footer { color: #666666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">HTML邮件测试</div>
    <div class="content">
        <p>这是一封<strong>HTML格式</strong>的测试邮件。</p>
        <p>HTML邮件支持：</p>
        <ul>
            <li>文本<span style="color: red;">格式化</span></li>
            <li>列表</li>
            <li>表格</li>
            <li>链接: <a href="https://www.example.com">示例链接</a></li>
        </ul>
    </div>
    <div class="footer">
        此邮件由邮件客户端示例脚本发送。
    </div>
</body>
</html>
"""

# 创建邮件对象
email = Email(
    message_id=f"<example.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{id(smtp_client)}@example.com>",
    subject="测试HTML邮件",
    from_addr=EmailAddress(name="发件人", address=username),
    to_addrs=[EmailAddress(name="收件人", address=recipient)],
    text_content="这是一封HTML格式的测试邮件。如果您的邮件客户端不支持HTML，将显示此纯文本内容。",
    html_content=html_content,
    date=None,  # 自动设置为当前时间
    status=EmailStatus.DRAFT
)
```

完整代码请参见 [examples/send_html_email.py](../examples/send_html_email.py)。

## 接收邮件

### 获取邮件列表

以下代码摘自 `examples/receive_emails.py`：

```python
from client.pop3_client import POP3Client

# 创建POP3客户端
pop3_client = POP3Client(
    host="pop.qq.com",  # 使用QQ邮箱，可以根据需要修改
    port=995,           # QQ邮箱SSL端口
    use_ssl=True,       # 使用SSL加密
    username=username,  # 用户输入的邮箱地址
    password=password,  # 用户输入的授权码
    auth_method="AUTO"  # 自动选择认证方法
)

# 接收邮件
try:
    print("正在连接到POP3服务器...")
    pop3_client.connect()

    # 获取邮箱状态
    status = pop3_client.get_mailbox_status()
    print(f"邮箱状态: {status[0]}封邮件, {status[1]}字节")

    # 获取邮件列表
    email_list = pop3_client.list_emails()
    print(f"邮箱中有{len(email_list)}封邮件")

    # 打印前5封邮件的信息
    for i, (msg_num, msg_size) in enumerate(email_list[:5]):
        print(f"邮件 {msg_num}: {msg_size} 字节")
        if i >= 4:
            break
finally:
    # 确保断开连接
    pop3_client.disconnect()
    print("已断开与POP3服务器的连接")
```

完整代码请参见 [examples/receive_emails.py](../examples/receive_emails.py)。

### 下载邮件

以下代码摘自 `examples/receive_emails.py`：

```python
# 获取最新的N封邮件
latest_emails = email_list[-num_emails:]

print(f"正在下载{len(latest_emails)}封邮件...")
for i, (msg_num, msg_size) in enumerate(latest_emails):
    print(f"正在下载第{i+1}封邮件 (编号: {msg_num}, 大小: {msg_size}字节)...")
    email = pop3_client.retrieve_email(msg_num, delete=False)

    if email:
        print(f"  主题: {email.subject}")
        print(f"  发件人: {email.from_addr.name} <{email.from_addr.address}>")
        print(f"  日期: {email.date}")
        print(f"  附件数量: {len(email.attachments)}")

        # 保存邮件
        filepath = pop3_client.save_email_as_eml(email, EMAIL_STORAGE_DIR)
        print(f"  已保存到: {filepath}")

        # 如果有附件，询问是否保存
        if email.attachments:
            save_attachments = input("  是否保存附件? (y/n): ").lower() == 'y'
            if save_attachments:
                # 创建附件保存目录
                attachments_dir = os.path.join(EMAIL_STORAGE_DIR, "attachments")
                os.makedirs(attachments_dir, exist_ok=True)

                # 保存附件
                for j, attachment in enumerate(email.attachments):
                    attachment_path = os.path.join(attachments_dir, attachment.filename)

                    # 检查文件是否已存在
                    if os.path.exists(attachment_path):
                        base, ext = os.path.splitext(attachment.filename)
                        attachment_path = os.path.join(attachments_dir, f"{base}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}")

                    # 保存附件
                    with open(attachment_path, "wb") as f:
                        f.write(attachment.content)

                    print(f"    附件{j+1}: {attachment.filename} 已保存到 {attachment_path}")
```

完整代码请参见 [examples/receive_emails.py](../examples/receive_emails.py)。

### 批量下载邮件

以下代码摘自 `examples/receive_emails.py` 的修改版本，用于批量下载所有邮件：

```python
# 下载所有邮件
try:
    print("正在连接到POP3服务器...")
    pop3_client.connect()

    # 获取邮箱状态
    status = pop3_client.get_mailbox_status()
    print(f"邮箱状态: {status[0]}封邮件, {status[1]}字节")

    # 获取所有邮件
    print("正在获取所有邮件...")
    emails = pop3_client.retrieve_all_emails(delete=False)

    # 保存邮件
    print(f"成功获取了{len(emails)}封邮件，正在保存...")
    for email in emails:
        filepath = pop3_client.save_email_as_eml(email, EMAIL_STORAGE_DIR)
        print(f"已保存邮件: {os.path.basename(filepath)}")

    print(f"所有邮件已保存到: {EMAIL_STORAGE_DIR}")
finally:
    # 断开连接
    pop3_client.disconnect()
    print("已断开与POP3服务器的连接")
```

完整代码请参见 [examples/receive_emails.py](../examples/receive_emails.py)。

## 管理邮件

### 查看已保存的邮件

```bash
python examples/list_emails.py
```

### 搜索邮件

以下代码摘自 `examples/search_emails.py`：

```python
import argparse
from server.db_handler import DatabaseHandler

# 解析命令行参数
parser = argparse.ArgumentParser(description="搜索邮件")
parser.add_argument("query", help="搜索关键词")
parser.add_argument("--fields", help="搜索字段，逗号分隔 (subject,sender,recipients)", default="subject,sender,recipients")
parser.add_argument("--content", action="store_true", help="搜索邮件内容")
parser.add_argument("--sent-only", action="store_true", help="只搜索已发送邮件")
parser.add_argument("--received-only", action="store_true", help="只搜索已接收邮件")
parser.add_argument("--include-deleted", action="store_true", help="包含已删除邮件")
parser.add_argument("--limit", type=int, default=100, help="最大结果数量")

args = parser.parse_args()

# 创建数据库处理器
db_handler = DatabaseHandler()

# 解析搜索字段
search_in = args.fields.split(",") if args.fields else None

# 设置搜索参数
include_sent = not args.received_only
include_received = not args.sent_only

# 搜索邮件
print(f"正在搜索: {args.query}")
emails = db_handler.search_emails(
    query=args.query,
    search_in=search_in,
    include_sent=include_sent,
    include_received=include_received,
    include_deleted=args.include_deleted,
    search_content=args.content,
    limit=args.limit
)
```

使用示例：

```bash
# 基本搜索
python examples/search_emails.py "搜索关键词"

# 只搜索主题和发件人
python examples/search_emails.py "搜索关键词" --fields subject,sender

# 搜索邮件正文内容
python examples/search_emails.py "搜索关键词" --content

# 只搜索已发送邮件
python examples/search_emails.py "搜索关键词" --sent-only

# 只搜索已接收邮件
python examples/search_emails.py "搜索关键词" --received-only

# 包含已删除邮件
python examples/search_emails.py "搜索关键词" --include-deleted

# 限制结果数量
python examples/search_emails.py "搜索关键词" --limit 10
```

完整代码请参见 [examples/search_emails.py](../examples/search_emails.py)。

### 查看特定邮件

```bash
python tools/view_email_by_id.py message_id
```

查看选项：
```bash
# 只查看邮件头
python tools/view_email_by_id.py message_id --headers

# 只查看纯文本内容
python tools/view_email_by_id.py message_id --text

# 只查看HTML内容
python tools/view_email_by_id.py message_id --html

# 只查看附件信息
python tools/view_email_by_id.py message_id --attachments

# 提取附件到指定目录
python tools/view_email_by_id.py message_id --extract path/to/output/dir
```

## 高级功能

### 邮件过滤

使用过滤条件接收邮件：

```bash
# 只接收特定日期之后的邮件
python main.py --client --receive --username your_email@example.com --password your_password --since 2023-01-01

# 只接收来自特定发件人的邮件
python main.py --client --receive --username your_email@example.com --password your_password --from someone@example.com

# 只接收主题包含特定字符串的邮件
python main.py --client --receive --username your_email@example.com --password your_password --subject "重要"
```

### 邮件导入

将外部.eml文件导入到系统中：

```bash
python tools/import_emails.py --dir path/to/emails
```

## 故障排除

### 连接问题

如果无法连接到邮件服务器，请检查：

1. 服务器地址和端口是否正确
2. 网络连接是否正常
3. 防火墙设置是否允许连接
4. 服务器是否要求SSL/TLS连接

### 认证问题

如果认证失败，请检查：

1. 用户名和密码是否正确
2. 对于QQ邮箱，是否使用了授权码而不是登录密码
3. 邮箱服务是否允许第三方应用访问
4. 认证方法是否正确

### 邮件发送问题

如果无法发送邮件，请检查：

1. 发件人地址是否与认证账号一致
2. 邮件格式是否正确
3. 是否达到发送频率限制
4. 邮件大小是否超过限制

## 常见问题

### Q: 如何获取QQ邮箱的授权码？

A: 登录QQ邮箱网页版 -> 设置 -> 账户 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务 -> 开启POP3/SMTP服务 -> 生成授权码

### Q: 为什么我的HTML邮件显示不正确？

A: 确保HTML内容格式正确，包含完整的HTML标签。某些邮件客户端可能对HTML格式有特殊要求。

### Q: 如何处理大型附件？

A: 对于大型附件，建议：
1. 分割成多个小文件
2. 使用云存储服务，在邮件中只发送下载链接
3. 压缩文件以减小大小

### Q: 如何备份邮件数据库？

A: 数据库文件位于 `data/email_db.sqlite`，可以直接复制此文件进行备份。邮件内容文件位于 `data/emails` 目录，也应一并备份。
