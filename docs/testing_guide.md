# 邮件客户端测试指南

本文档提供了如何测试邮件客户端各项功能的详细说明。

## 测试准备

在运行测试之前，请确保：

1. 已安装所有必要的依赖项
2. 已配置测试账号信息（在 `tests/test_config.py` 中）
3. 对于发送邮件测试，确保你的邮箱服务提供商允许第三方应用访问

### 配置测试账号

编辑 `tests/test_config.py` 文件，填入你的测试账号信息：

```python
TEST_ACCOUNT = {
    "smtp_host": "smtp.qq.com",
    "smtp_port": 25,
    "smtp_ssl": True,
    "pop3_host": "pop.qq.com",
    "pop3_port": 110,
    "pop3_ssl": True,
    "username": "your_email@qq.com",  # 替换为你的QQ邮箱
    "password": "your_password",      # 替换为你的授权码
    "recipient": "recipient@example.com"  # 替换为接收测试邮件的邮箱
}
```

**注意**：对于QQ邮箱，`password` 应该是授权码而不是登录密码。你可以在QQ邮箱设置中获取授权码。

## 运行测试

### 运行所有测试

使用以下命令运行所有测试：

```bash
python run_all_tests.py --modules all --verbose
```

### 运行特定测试

运行特定测试模块：

```bash
# 运行认证测试
python run_all_tests.py --modules auth --verbose

# 运行SMTP发送测试
python run_all_tests.py --modules smtp --verbose

# 运行POP3接收测试
python run_all_tests.py --modules pop3 --verbose

# 运行存储测试
python run_all_tests.py --modules storage --verbose

# 运行多个测试模块
python run_all_tests.py --modules auth smtp --verbose
```

### 直接运行单个测试文件

你也可以直接运行单个测试文件：

```bash
# 运行基本认证测试
python tests/test_auth_basic.py

# 运行全面认证测试
python tests/test_auth_comprehensive.py

# 运行SMTP发送测试
python tests/test_smtp_send.py

# 运行POP3接收测试
python tests/test_pop3_receive.py

# 运行存储测试
python tests/test_storage.py
```

## 测试内容说明

### 1. 认证功能测试

- `test_auth_basic.py`：测试基本的认证功能
- `test_auth_comprehensive.py`：全面测试各种认证方法和错误处理

测试内容包括：
- 明文密码认证
- SSL加密登录
- LOGIN认证命令
- AUTH PLAIN认证命令
- 认证失败的错误处理

### 2. 邮件发送功能测试

- `test_smtp_send.py`：测试发送纯文本邮件、HTML邮件、带附件邮件和多收件人邮件

测试内容包括：
- 发送纯文本邮件
- 发送HTML格式邮件
- 发送带有各类附件的邮件
- 发送到多个收件人（包括抄送和密送）

### 3. 邮件接收功能测试

- `test_pop3_receive.py`：测试连接邮箱、获取邮件列表、下载邮件内容和附件

测试内容包括：
- 通过POP3协议连接邮箱
- 获取邮箱邮件列表
- 下载邮件内容（包括纯文本和HTML格式）
- 下载带附件的邮件

### 4. 本地存储功能测试

- `test_storage.py`：测试将邮件保存为.eml文件、保存邮件元数据到数据库、从数据库检索邮件

测试内容包括：
- 将接收的邮件保存为.eml格式
- 保存的邮件文件是否完整包含所有信息（包括附件）
- 邮件元数据是否正确存储在数据库中

## 测试结果解读

测试成功时，你将看到类似以下输出：

```
Ran X tests in Y.ZZZs

OK
```

如果测试失败，你将看到详细的错误信息，包括：

- 失败的测试用例名称
- 失败的原因
- 相关的堆栈跟踪

## 常见问题解决

### 认证失败

- 检查你的账号信息是否正确
- 对于QQ邮箱，确保使用的是授权码而不是登录密码
- 确保你的邮箱服务提供商允许第三方应用访问

### 连接超时

- 检查网络连接
- 确认服务器地址和端口是否正确
- 检查防火墙设置

### 发送邮件失败

- 检查发件人地址是否与认证账号一致
- 确认邮件格式是否正确
- 查看是否达到发送频率限制

### 接收邮件失败

- 确认邮箱中有邮件
- 检查POP3服务是否已启用
- 验证认证信息是否正确

### 存储测试失败

- 检查数据库文件是否存在且可写
- 确认文件系统权限
- 验证邮件格式是否正确

## 手动测试

除了自动化测试外，你还可以进行手动测试：

### 发送测试邮件

```python
from client.smtp_client import SMTPClient
from common.models import Email, EmailAddress, Attachment, EmailStatus

# 创建SMTP客户端
smtp_client = SMTPClient(
    host="smtp.qq.com",
    port=25,
    use_ssl=True,
    username="your_email@qq.com",  # 替换为你的QQ邮箱
    password="your_password",      # 替换为你的授权码
    auth_method="AUTO"
)

# 创建测试邮件
email = Email(
    message_id=f"<test.manual.{id(smtp_client)}@example.com>",
    subject="测试邮件",
    from_addr=EmailAddress(name="发件人", address="your_email@qq.com"),
    to_addrs=[EmailAddress(name="收件人", address="recipient@example.com")],
    text_content="这是一封测试邮件。",
    html_content="<html><body><h1>测试邮件</h1><p>这是一封<b>HTML格式</b>的测试邮件。</p></body></html>",
    date=None,  # 自动设置为当前时间
    status=EmailStatus.DRAFT
)

# 发送邮件
smtp_client.connect()
result = smtp_client.send_email(email)
smtp_client.disconnect()

print(f"邮件发送{'成功' if result else '失败'}")
```

### 接收测试邮件

```python
from client.pop3_client import POP3Client

# 创建POP3客户端
pop3_client = POP3Client(
    host="pop.qq.com",
    port=110,
    use_ssl=True,
    username="your_email@qq.com",  # 替换为你的QQ邮箱
    password="your_password",      # 替换为你的授权码
    auth_method="AUTO"
)

# 连接到邮箱
pop3_client.connect()

# 获取邮件列表
email_list = pop3_client.list_emails()
print(f"邮箱中有{len(email_list)}封邮件")

# 获取最新的邮件
if email_list:
    msg_num = email_list[-1][0]
    email = pop3_client.retrieve_email(msg_num, delete=False)
    
    print(f"主题: {email.subject}")
    print(f"发件人: {email.from_addr.name} <{email.from_addr.address}>")
    print(f"日期: {email.date}")
    print(f"附件数量: {len(email.attachments)}")

# 断开连接
pop3_client.disconnect()
```

## 性能测试

对于大量邮件的处理，可以进行性能测试：

```python
import time
from client.pop3_client import POP3Client

# 创建POP3客户端
pop3_client = POP3Client(
    host="pop.qq.com",
    port=110,
    use_ssl=True,
    username="your_email@qq.com",  # 替换为你的QQ邮箱
    password="your_password",      # 替换为你的授权码
    auth_method="AUTO"
)

# 连接到邮箱
pop3_client.connect()

# 测量获取所有邮件的时间
start_time = time.time()
emails = pop3_client.retrieve_all_emails(delete=False)
end_time = time.time()

print(f"获取了{len(emails)}封邮件，耗时{end_time - start_time:.2f}秒")

# 断开连接
pop3_client.disconnect()
```

## 测试报告

完成测试后，建议生成测试报告，记录以下信息：

1. 测试环境（操作系统、Python版本等）
2. 测试账号信息（可以隐藏密码）
3. 测试用例执行情况
4. 发现的问题和解决方案
5. 性能测试结果
6. 建议的改进事项

这将有助于跟踪项目的质量状况，并为后续开发提供参考。
