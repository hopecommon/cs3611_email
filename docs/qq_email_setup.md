# QQ邮箱SMTP配置指南

本文档提供了如何配置和使用QQ邮箱SMTP服务发送测试邮件的详细说明。

## 1. 获取QQ邮箱授权码

在使用QQ邮箱的SMTP服务之前，您需要获取授权码：

1. 登录您的QQ邮箱 (https://mail.qq.com)
2. 点击"设置" -> "账户"
3. 在"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"部分，开启"POP3/SMTP服务"
4. 点击"生成授权码"按钮，并按照提示操作
5. 记下生成的授权码，这将用作SMTP密码

## 2. 配置方法

您可以通过以下两种方式之一配置QQ邮箱SMTP服务：

### 2.1 使用JSON配置文件

1. 复制`config/qq_config.json`文件并填写您的信息：

```json
{
    "smtp": {
        "host": "smtp.qq.com",
        "port": 587,
        "use_ssl": true,  // QQ邮箱强制要求SSL连接
        "ssl_port": 465,
        "username": "your_qq_number@qq.com",  // 替换为您的QQ邮箱
        "password": "your_authorization_code"  // 替换为您的授权码
    },
    "email": {
        "from_name": "您的名字",  // 替换为您的名字
        "from_address": "your_qq_number@qq.com",  // 替换为您的QQ邮箱，必须与username一致
        "default_to": "recipient@example.com"  // 替换为默认收件人
    }
}
```

2. 保存文件后，您可以使用以下命令发送测试邮件：

```bash
python examples/send_qq_email.py --config config/qq_config.json
```

### 2.2 使用环境变量

1. 复制`config/.env.template`文件为`.env`（放在项目根目录或`config`目录下）：

```
# SMTP服务器设置
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USE_SSL=True
SMTP_SSL_PORT=465

# 认证信息 - 请删除注释并替换为您的实际值
SMTP_USERNAME=your_qq_number@qq.com
SMTP_PASSWORD=your_authorization_code

# 邮件默认设置 - 请删除注释并替换为您的实际值
EMAIL_FROM_NAME=您的名字
EMAIL_FROM_ADDRESS=your_qq_number@qq.com
EMAIL_DEFAULT_TO=recipient@example.com
```

注意：
- 环境变量中不要包含注释，上面的注释仅用于说明
- `EMAIL_FROM_ADDRESS`必须与`SMTP_USERNAME`一致
- `SMTP_USE_SSL`必须设置为`True`，QQ邮箱强制要求SSL连接

2. 保存文件后，您可以使用以下命令发送测试邮件：

```bash
python examples/send_qq_email.py
```

## 3. 发送测试邮件

### 3.1 基本用法

```bash
python examples/send_qq_email.py
```

这将使用默认配置发送一封测试邮件。

### 3.2 指定收件人

```bash
python examples/send_qq_email.py --to recipient@example.com
```

### 3.3 自定义主题和正文

```bash
python examples/send_qq_email.py --subject "自定义主题" --body "这是自定义正文内容。"
```

### 3.4 发送HTML格式邮件

```bash
python examples/send_qq_email.py --html --body "<h1>HTML邮件</h1><p>这是一封<strong>HTML格式</strong>的邮件。</p>"
```

### 3.5 添加附件

```bash
python examples/send_qq_email.py --attachment path/to/file.txt
```

## 4. 故障排除

### 4.1 连接问题

如果遇到"目标计算机积极拒绝"错误，请检查：

- SMTP服务器地址和端口是否正确
- 您的网络是否允许连接到SMTP服务器
- 防火墙是否阻止了连接

### 4.2 认证问题

如果遇到认证失败错误，请检查：

- 用户名（QQ邮箱地址）是否正确
- 授权码是否正确（不是QQ密码）
- 是否已开启POP3/SMTP服务
- 发件人地址是否与SMTP用户名一致（QQ邮箱强制要求一致）

### 4.3 SSL/TLS问题

如果遇到SSL/TLS相关错误：

- QQ邮箱强制要求使用SSL连接，确保`use_ssl`设置为`true`
- 必须使用465端口进行SSL连接
- 不支持使用587端口的STARTTLS方式

### 4.4 "Connection unexpectedly closed"错误

如果遇到"Connection unexpectedly closed"错误：

- 确认使用了SSL连接（`use_ssl=True`）
- 确认使用了正确的SSL端口（465）
- 检查授权码是否正确且未过期
- 确认发件人地址与SMTP用户名完全一致

## 5. 安全注意事项

- 不要将包含授权码的配置文件提交到版本控制系统
- 不要在公共场合或共享代码中暴露您的授权码
- 定期更新您的授权码以提高安全性
