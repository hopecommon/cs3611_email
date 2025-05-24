# 邮件客户端模块 (Email Client Module)

本模块提供完整的邮件客户端功能，支持SMTP邮件发送和POP3邮件接收，包含SSL/TLS加密、多种认证方式、命令行工具等特性。

## 核心特性

- **SMTP客户端**: 支持邮件发送、多种认证方式(LOGIN/PLAIN/AUTO)、SSL/TLS加密
- **POP3客户端**: 支持邮件接收、APOP/BASIC认证、邮件过滤和本地存储
- **MIME处理**: 完整的邮件编码/解码、附件处理、.eml文件支持
- **安全功能**: SSL/TLS支持、密码加密、安全连接管理
- **命令行工具**: 功能完整的SMTP/POP3命令行接口
- **国际化**: 全面的UTF-8支持，特别优化中文等非ASCII字符处理

## 文件结构

```
client/
├── __init__.py           # 包初始化文件
├── smtp_client.py        # SMTP客户端核心实现 (578行)
├── pop3_client.py        # POP3客户端核心实现 (916行)
├── mime_handler.py       # MIME编码/解码处理 (272行)
├── security.py           # 安全功能模块 (310行)
├── socket_utils.py       # 套接字工具函数 (87行)
├── smtp_cli.py           # SMTP命令行接口 (302行)
└── pop3_cli.py           # POP3命令行接口 (329行)
```

## 快速开始

### SMTP邮件发送

```python
from client.smtp_client import SMTPClient
from common.models import Email, EmailAddress

# 创建SMTP客户端
smtp_client = SMTPClient(
    host="smtp.example.com",
    port=587,
    use_ssl=True,
    username="user@example.com",
    password="password"
)

# 创建邮件
email = Email(
    subject="测试邮件",
    from_addr=EmailAddress(name="发件人", address="sender@example.com"),
    to_addrs=[EmailAddress(name="收件人", address="recipient@example.com")],
    text_content="这是一封测试邮件"
)

# 发送邮件
smtp_client.connect()
smtp_client.send_email(email)
smtp_client.disconnect()
```

### POP3邮件接收

```python
from client.pop3_client_refactored import POP3Client

# 创建POP3客户端
pop3_client = POP3Client(
    host="pop3.example.com",
    port=995,
    use_ssl=True,
    username="user@example.com",
    password="password"
)

# 接收邮件
pop3_client.connect()
emails = pop3_client.retrieve_all_emails(limit=10)
pop3_client.disconnect()

# 处理邮件
for email in emails:
    print(f"主题: {email.subject}")
    print(f"发件人: {email.from_addr.address}")
```

### 命令行使用

```bash
# 发送邮件
python client/smtp_cli.py --host smtp.qq.com --ssl --username your@qq.com --ask-password --from your@qq.com --to recipient@example.com --subject "测试邮件" --body "邮件内容"

# 接收邮件
python client/pop3_cli.py --host pop3.qq.com --ssl --username your@qq.com --ask-password --retrieve-all --verbose
```

## 核心模块说明

### SMTPClient (smtp_client.py)

**主要功能**:
- 邮件发送和SMTP协议处理
- 多种认证方式: LOGIN、PLAIN、AUTO(自动选择)
- SSL/TLS加密支持
- 自动重试机制(最大3次)
- 已发送邮件本地保存(.eml格式)
- QQ邮箱等特殊服务器优化

**关键方法**:
- `connect()`: 连接SMTP服务器并认证
- `send_email(email)`: 发送邮件
- `disconnect()`: 安全断开连接

### POP3Client (pop3_client.py)

**主要功能**:
- 邮件接收和POP3协议处理
- BASIC/APOP认证支持
- 连接超时和重试机制
- 邮件过滤(按日期、发件人、主题)
- 复杂邮件头部解码
- 多部分邮件和附件处理

**关键方法**:
- `connect()`: 连接POP3服务器并认证
- `retrieve_all_emails()`: 获取所有邮件(支持过滤)
- `retrieve_email(msg_num)`: 获取指定邮件
- `save_email_as_eml()`: 保存邮件为.eml文件

### MIMEHandler (mime_handler.py)

**主要功能**:
- MIME编码/解码处理
- 附件编码和解码
- .eml文件解析和生成
- 邮件头部编码处理
- MIME类型自动检测

**关键方法**:
- `encode_attachment(file_path)`: 文件转附件
- `parse_eml_file(file_path)`: 解析.eml文件
- `save_as_eml(email, file_path)`: 保存为.eml文件

### SecurityManager (security.py)

**主要功能**:
- SSL/TLS上下文创建和管理
- SMTP认证字符串生成/验证
- AES数据加密/解密
- 密码哈希和验证
- 安全套接字包装

**关键方法**:
- `create_ssl_context()`: 创建SSL上下文
- `generate_auth_string()`: 生成认证字符串
- `encrypt_data()/decrypt_data()`: 数据加密/解密

## 依赖关系

### 外部依赖
- `common.utils`: 通用工具函数(日志、验证等)
- `common.models`: 数据模型(Email、EmailAddress、Attachment)
- `common.config`: 配置管理(服务器设置、目录配置)
- `common.port_config`: 端口配置和自动检测
- `server.db_handler`: 数据库处理(邮件元数据存储)

### 内部依赖
- 所有客户端模块依赖`socket_utils`进行安全连接管理
- 命令行工具依赖对应的客户端类
- `mime_handler`与客户端类相互调用进行邮件处理

## 错误处理和重试机制

### 连接管理
- 自动重试机制(默认3次)
- 连接超时处理(默认30秒)
- 安全的连接关闭和资源清理
- SSL连接错误的特殊处理

### 编码处理
- UTF-8编码优先，fallback到其他编码
- 中文等非ASCII字符的特殊处理
- Windows控制台编码兼容性

### 服务器兼容性
- QQ邮箱授权码错误的特殊提示
- 不同邮件服务器的认证方式适配
- MIME类型的跨平台兼容性

## 配置说明

客户端支持多种配置方式:

1. **代码配置**: 直接在代码中指定参数
2. **配置文件**: 支持JSON格式配置文件
3. **命令行参数**: 命令行工具支持完整参数配置
4. **环境变量**: 通过common.config模块支持

### 示例配置文件

```json
{
  "smtp": {
    "host": "smtp.qq.com",
    "port": 587,
    "ssl_port": 465,
    "use_ssl": true,
    "username": "your@qq.com",
    "password": "your_auth_code"
  },
  "pop3": {
    "host": "pop3.qq.com",
    "port": 110,
    "ssl_port": 995,
    "use_ssl": true,
    "username": "your@qq.com",
    "password": "your_auth_code"
  }
}
```

## 性能特性

- **连接复用**: SMTP客户端支持连接复用发送多封邮件
- **批量处理**: POP3客户端支持批量邮件获取和处理
- **内存优化**: 大附件的流式处理，避免内存溢出
- **并发安全**: 线程安全的连接管理和资源清理

## 测试和调试

### 日志系统
所有模块都集成了详细的日志记录:
```python
# 启用详细日志
from common.utils import setup_logging
logger = setup_logging("client_test", verbose=True)
```

### 命令行调试
```bash
# 启用详细输出
python client/smtp_cli.py --verbose [其他参数]
python client/pop3_cli.py --verbose [其他参数]
```

### 常见问题排查
1. **连接失败**: 检查服务器地址、端口、SSL设置
2. **认证失败**: 确认用户名密码，QQ邮箱需使用授权码
3. **编码问题**: 确保所有文本使用UTF-8编码
4. **附件问题**: 检查文件路径和MIME类型检测
