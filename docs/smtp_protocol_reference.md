# SMTP协议参考文档

## 简介

SMTP (Simple Mail Transfer Protocol) 是一种在网络中传输电子邮件的标准协议，最新规范在RFC 5321中定义，该规范于2008年10月发布并取代了之前的RFC 2821。

## 基本概念

SMTP是一个客户端-服务器协议，其中发信方作为客户端，接收方作为服务器。SMTP通信基于文本命令和响应，通常使用TCP端口25（标准）、587（提交）或465（SSL加密）。

## 通信流程

SMTP通信流程主要包括以下步骤：

1. **建立连接**：客户端连接到SMTP服务器
2. **问候**：服务器发送欢迎信息
3. **认证**：客户端进行身份验证
4. **邮件事务**：
   - MAIL FROM：指定发件人
   - RCPT TO：指定收件人
   - DATA：发送邮件内容
5. **结束会话**：QUIT命令关闭连接

### 连接建立示例

```
C: <建立TCP连接到服务器端口25>
S: 220 smtp.example.com ESMTP Postfix
C: HELO client.example.com
S: 250 Hello client.example.com
```

## 主要SMTP命令

| 命令      | 描述                   | 语法                       | 示例                              |
| --------- | ---------------------- | -------------------------- | --------------------------------- |
| HELO      | 标识发送者             | `HELO <domain>`            | `HELO client.example.com`         |
| EHLO      | 扩展HELO，支持扩展功能 | `EHLO <domain>`            | `EHLO client.example.com`         |
| MAIL FROM | 指定邮件发送者         | `MAIL FROM:<reverse-path>` | `MAIL FROM:<sender@example.com>`  |
| RCPT TO   | 指定邮件接收者         | `RCPT TO:<forward-path>`   | `RCPT TO:<recipient@example.com>` |
| DATA      | 开始邮件内容传输       | `DATA`                     | `DATA`                            |
| RSET      | 重置会话状态           | `RSET`                     | `RSET`                            |
| VRFY      | 验证用户存在性         | `VRFY <string>`            | `VRFY user`                       |
| EXPN      | 展开邮件列表           | `EXPN <string>`            | `EXPN users`                      |
| HELP      | 获取帮助信息           | `HELP [<string>]`          | `HELP`                            |
| NOOP      | 无操作                 | `NOOP`                     | `NOOP`                            |
| QUIT      | 结束会话               | `QUIT`                     | `QUIT`                            |

## SMTP响应码

SMTP响应码由三位数字组成，用于表示服务器对命令的处理结果：

| 响应码 | 类别         | 含义                           |
| ------ | ------------ | ------------------------------ |
| 2xx    | 成功完成     | 请求的动作已成功完成           |
| 3xx    | 需进一步操作 | 命令已被接受，但需要进一步信息 |
| 4xx    | 暂时性错误   | 命令未被接受，但错误是暂时性的 |
| 5xx    | 永久性错误   | 命令未被接受，错误是永久性的   |

**常见响应码详解：**

- **211**: 系统状态或帮助回复
- **214**: 帮助信息
- **220**: 服务就绪
- **221**: 服务关闭传输通道
- **250**: 请求的操作完成
- **251**: 用户非本地，将转发
- **354**: 开始邮件输入，以"."结束
- **421**: 服务不可用
- **450**: 请求的操作未执行，邮箱不可用
- **451**: 请求的操作中止，本地错误
- **452**: 请求的操作未执行，系统存储不足
- **500**: 命令语法错误
- **501**: 参数或参数值语法错误
- **502**: 命令未实现
- **503**: 命令序列错误
- **504**: 命令参数未实现
- **550**: 请求的操作未执行，邮箱不可用
- **551**: 用户非本地
- **552**: 请求的操作中止，超出存储分配
- **553**: 请求的操作未执行，邮箱名不允许
- **554**: 事务失败

## 完整SMTP会话示例

以下是一个完整的SMTP会话示例，包括认证、发送邮件和断开连接：

```
C: <建立与服务器的TCP连接>
S: 220 smtp.example.com ESMTP Postfix
C: EHLO client.example.com
S: 250-smtp.example.com
S: 250-PIPELINING
S: 250-SIZE 10240000
S: 250-VRFY
S: 250-ETRN
S: 250-STARTTLS
S: 250-AUTH PLAIN LOGIN
S: 250-ENHANCEDSTATUSCODES
S: 250-8BITMIME
S: 250 DSN

C: AUTH LOGIN
S: 334 VXNlcm5hbWU6
C: dXNlcm5hbWU=             # 用户名的Base64编码
S: 334 UGFzc3dvcmQ6
C: cGFzc3dvcmQ=             # 密码的Base64编码
S: 235 2.7.0 Authentication successful

C: MAIL FROM:<sender@example.com>
S: 250 2.1.0 Ok
C: RCPT TO:<recipient@example.com>
S: 250 2.1.5 Ok
C: DATA
S: 354 End data with <CR><LF>.<CR><LF>

C: From: "Sender Name" <sender@example.com>
C: To: "Recipient Name" <recipient@example.com>
C: Subject: Test Email
C: 
C: This is a test email message.
C: .
S: 250 2.0.0 Ok: queued as 12345

C: QUIT
S: 221 2.0.0 Bye
```

## SMTP扩展 (ESMTP)

ESMTP（扩展SMTP）通过EHLO命令而不是HELO命令启动，服务器会响应支持的扩展列表。

常用ESMTP扩展：

- **8BITMIME**：允许8位MIME编码传输
- **SIZE**：指定最大消息大小
- **STARTTLS**：支持TLS加密
- **AUTH**：支持各种认证机制
- **PIPELINING**：允许命令流水线处理
- **DSN**：支持送达状态通知

## 认证机制

SMTP支持多种认证机制，常用的包括：

### PLAIN认证

基本的明文认证方式，使用Base64编码传输凭据：

```
C: AUTH PLAIN
S: 334
C: AHVzZXJuYW1lAHBhc3N3b3Jk  # Base64(\0username\0password)
S: 235 2.7.0 Authentication successful
```

### LOGIN认证

分两步传输用户名和密码：

```
C: AUTH LOGIN
S: 334 VXNlcm5hbWU6          # Base64("Username:")
C: dXNlcm5hbWU=              # Base64("username")
S: 334 UGFzc3dvcmQ6          # Base64("Password:")
C: cGFzc3dvcmQ=              # Base64("password")
S: 235 2.7.0 Authentication successful
```

## 安全SMTP (SMTPS)

SMTP可通过两种方式实现安全传输：

1. **隐式TLS**：直接在端口465上使用SSL/TLS加密连接
2. **显式TLS (STARTTLS)**：在普通SMTP会话中使用STARTTLS命令升级为加密连接

STARTTLS示例：

```
C: EHLO client.example.com
S: 250-smtp.example.com
S: 250-STARTTLS
S: 250 ...其他扩展...
C: STARTTLS
S: 220 Ready to start TLS
<此时进行TLS握手>
C: EHLO client.example.com
... 继续加密会话 ...
```

## 邮件服务提供商特殊要求

不同邮件服务商可能有特殊要求，以下是几个主要邮件服务的配置：

### Gmail

- SMTP服务器：smtp.gmail.com
- 端口：587（STARTTLS）或465（SSL）
- 必须启用"不太安全的应用访问权限"或使用应用专用密码
- 要求强认证

### QQ邮箱

- SMTP服务器：smtp.qq.com
- 端口：587或465
- 需要使用授权码而非账户密码
- 有发送频率和数量限制

### Outlook/Hotmail

- SMTP服务器：smtp.office365.com
- 端口：587（STARTTLS）
- 强制要求TLS加密
- 对邮件内容有更严格的检查

## 常见问题与解决方案

### 认证失败

- **问题**：535 5.7.8 Authentication credentials invalid
- **解决**：
  - 检查用户名和密码是否正确
  - 对特殊邮箱服务，使用授权码代替密码
  - 查看邮箱服务商是否需要开启"允许不安全应用访问"

### 连接问题

- **问题**：无法连接到SMTP服务器
- **解决**：
  - 检查服务器地址和端口是否正确
  - 检查网络连接和防火墙设置
  - 确认服务器允许远程连接

### 发送限制

- **问题**：450 4.4.2 Mailbox quota exceeded
- **解决**：
  - 检查邮箱是否已满
  - 是否达到发送频率或数量限制
  - 是否存在发送政策限制

## 实现建议

### Python实现示例

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(sender, recipient, subject, body, smtp_server, port, username, password, use_tls=True):
    # 创建多部分消息
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject
    
    # 添加文本内容
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # 连接到SMTP服务器
        server = smtplib.SMTP(smtp_server, port)
        server.ehlo()
        
        # 启用TLS加密（如果需要）
        if use_tls:
            server.starttls()
            server.ehlo()
        
        # 登录
        server.login(username, password)
        
        # 发送邮件
        server.send_message(msg)
        print("邮件发送成功!")
    except Exception as e:
        print(f"发送失败: {e}")
    finally:
        server.quit()

# 使用示例
send_email(
    sender="sender@example.com",
    recipient="recipient@example.com",
    subject="测试邮件",
    body="这是一封测试邮件",
    smtp_server="smtp.example.com",
    port=587,
    username="username",
    password="password",
    use_tls=True
)
```

## 参考资料

- [RFC 5321 - Simple Mail Transfer Protocol](https://tools.ietf.org/html/rfc5321)
- [RFC 5322 - Internet Message Format](https://tools.ietf.org/html/rfc5322)
- [RFC 4954 - SMTP Service Extension for Authentication](https://tools.ietf.org/html/rfc4954)
- [Python smtplib 文档](https://docs.python.org/3/library/smtplib.html) 