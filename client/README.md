# 客户端模块 (Client Module)

本目录包含邮件客户端的实现，负责与邮件服务器通信，发送和接收邮件。

## 文件结构

```
client/
├── __init__.py           # 包初始化文件
├── smtp_client.py        # SMTP客户端实现
├── pop3_client.py        # POP3客户端实现
├── mime_handler.py       # MIME编码/解码处理
├── security.py           # 安全相关功能（SSL/TLS）
├── socket_utils.py       # 套接字工具函数
├── smtp_cli.py           # SMTP命令行接口
└── pop3_cli.py           # POP3命令行接口
```

## 模块详细说明

### smtp_client.py

SMTP客户端模块，负责与SMTP服务器通信，发送邮件。

#### 类: `SMTPClient`

**描述**: SMTP客户端类，处理邮件发送功能。

**构造函数参数**:
- `host` (str): SMTP服务器主机名，默认使用配置中的值
- `port` (int): SMTP服务器端口，默认使用配置中的值
- `use_ssl` (bool): 是否使用SSL/TLS，默认使用配置中的值
- `ssl_port` (int): SSL/TLS端口，默认使用配置中的值
- `username` (Optional[str]): 认证用户名，默认为None
- `password` (Optional[str]): 认证密码，默认为None
- `auth_method` (Optional[Literal["LOGIN", "PLAIN", "AUTO"]]): 认证方法，默认为"AUTO"
- `timeout` (int): 连接超时时间（秒），默认为30
- `save_sent_emails` (bool): 是否保存已发送邮件，默认为True
- `sent_emails_dir` (str): 已发送邮件保存目录，默认使用配置中的值
- `max_retries` (int): 最大重试次数，默认为3

**属性**:
- `host` (str): SMTP服务器主机名
- `port` (int): SMTP服务器端口
- `use_ssl` (bool): 是否使用SSL/TLS
- `username` (Optional[str]): 认证用户名
- `password` (Optional[str]): 认证密码
- `auth_method` (str): 认证方法
- `timeout` (int): 连接超时时间（秒）
- `connection` (Optional[smtplib.SMTP]): SMTP连接对象
- `save_sent_emails` (bool): 是否保存已发送邮件
- `sent_emails_dir` (str): 已发送邮件保存目录
- `max_retries` (int): 最大重试次数
- `db_handler` (DatabaseHandler): 数据库处理器

**方法**:
- `connect() -> None`: 连接到SMTP服务器
- `disconnect() -> None`: 断开与SMTP服务器的连接
- `send_email(email: Email) -> bool`: 发送邮件
- `_save_sent_email(email: Email) -> None`: 保存已发送邮件
- `_create_mime_message(email: Email) -> EmailMessage`: 从Email对象创建MIME消息
- `_create_attachment_part(attachment: Attachment) -> MIMEBase`: 创建附件部分

### pop3_client.py

POP3客户端模块，负责与POP3服务器通信，接收邮件。

#### 类: `POP3Client`

**描述**: POP3客户端类，处理邮件接收功能。

**构造函数参数**:
- `host` (str): POP3服务器主机名，默认使用配置中的值
- `port` (int): POP3服务器端口，默认使用配置中的值
- `use_ssl` (bool): 是否使用SSL/TLS，默认使用配置中的值
- `ssl_port` (int): SSL/TLS端口，默认使用配置中的值
- `username` (Optional[str]): 认证用户名，默认为None
- `password` (Optional[str]): 认证密码，默认为None
- `auth_method` (Optional[Literal["BASIC", "APOP", "AUTO"]]): 认证方法，默认为"AUTO"
- `timeout` (int): 连接超时时间（秒），默认为30
- `max_retries` (int): 最大重试次数，默认为3

**属性**:
- `host` (str): POP3服务器主机名
- `port` (int): POP3服务器端口
- `use_ssl` (bool): 是否使用SSL/TLS
- `username` (Optional[str]): 认证用户名
- `password` (Optional[str]): 认证密码
- `auth_method` (str): 认证方法
- `timeout` (int): 连接超时时间（秒）
- `max_retries` (int): 最大重试次数
- `connection` (Optional[poplib.POP3]): POP3连接对象

**方法**:
- `connect() -> None`: 连接到POP3服务器
- `disconnect() -> None`: 断开与POP3服务器的连接
- `get_mailbox_status() -> Tuple[int, int]`: 获取邮箱状态（邮件数量和总大小）
- `list_emails() -> List[Tuple[int, int]]`: 列出所有邮件（邮件索引和大小）
- `retrieve_email(msg_num: int, delete: bool = False) -> Optional[Email]`: 获取指定邮件
- `retrieve_all_emails(delete: bool = False, limit: int = None, since_date: datetime = None, only_unread: bool = False, from_addr: str = None, subject_contains: str = None) -> List[Email]`: 获取所有邮件，支持多种过滤选项
- `save_email_as_eml(email: Email, directory: str = EMAIL_STORAGE_DIR) -> str`: 将邮件保存为.eml文件
- `_convert_to_email(msg: EmailMessage) -> Email`: 将EmailMessage对象转换为Email对象
- `_process_message_parts(msg: EmailMessage, text_content: str, html_content: str, attachments: List[Attachment]) -> Tuple[str, str]`: 处理邮件各部分内容

### mime_handler.py

MIME处理模块，处理邮件的MIME编码和解码。

#### 类: `MIMEHandler`

**描述**: MIME处理类，提供静态方法处理MIME编码和解码。

**静态方法**:
- `decode_header_value(header_value: str) -> str`: 解码邮件头部值
- `encode_header_value(value: str, charset: str = 'utf-8') -> str`: 编码邮件头部值
- `get_content_type(file_path: str) -> str`: 获取文件的MIME类型
- `encode_attachment(file_path: str) -> Attachment`: 将文件编码为附件
- `parse_eml_file(file_path: str) -> Email`: 解析.eml文件为Email对象
- `save_as_eml(email_obj: Email, file_path: str) -> None`: 将Email对象保存为.eml文件

### security.py

安全模块，处理SSL/TLS和其他安全相关功能。

#### 类: `SecurityManager`

**描述**: 安全管理类，处理加密和认证。

**静态方法**:
- `create_client_ssl_context() -> ssl.SSLContext`: 创建客户端SSL上下文
- `create_server_ssl_context(cert_file: str = SSL_CERT_FILE, key_file: str = SSL_KEY_FILE) -> ssl.SSLContext`: 创建服务器SSL上下文
- `wrap_socket(sock: socket.socket, context: ssl.SSLContext, server_side: bool = False, server_hostname: Optional[str] = None) -> ssl.SSLSocket`: 包装套接字为SSL套接字
- `verify_auth_string(auth_string: str, users: Dict[str, str]) -> Optional[str]`: 验证SMTP AUTH PLAIN认证字符串
- `hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]`: 哈希密码
- `verify_password(password: str, hashed_password: bytes, salt: bytes) -> bool`: 验证密码

### socket_utils.py

套接字工具模块，提供套接字相关的工具函数和类。

**函数**:
- `safe_socket(sock=None)`: 安全地管理套接字，确保在异常情况下也能正确关闭（上下文管理器）
- `close_socket_safely(sock) -> bool`: 安全地关闭套接字
- `close_ssl_connection_safely(connection) -> bool`: 安全地关闭SSL连接

### smtp_cli.py

SMTP命令行接口，提供命令行发送邮件的功能。

**函数**:
- `parse_args() -> argparse.Namespace`: 解析命令行参数
- `load_config(config_path: str) -> Dict[str, Any]`: 加载配置文件
- `create_email_from_args(args: argparse.Namespace) -> Email`: 从命令行参数创建邮件
- `main()`: 主函数

### pop3_cli.py

POP3命令行接口，提供命令行接收邮件的功能。

**函数**:
- `parse_args() -> argparse.Namespace`: 解析命令行参数
- `print_email_list(emails: List[Tuple[int, int]])`: 打印邮件列表
- `print_email(email: Email, verbose: bool = False)`: 打印邮件内容
- `main()`: 主函数

## 依赖关系

- `smtp_client.py` 依赖于 `common.utils`, `common.models`, `common.config`, `client.mime_handler`, `server.db_handler`, `client.socket_utils`
- `pop3_client.py` 依赖于 `common.utils`, `common.models`, `common.config`, `client.socket_utils`
- `mime_handler.py` 依赖于 `common.utils`, `common.models`
- `security.py` 依赖于 `common.utils`, `common.config`
- `socket_utils.py` 无外部依赖
- `smtp_cli.py` 依赖于 `common.utils`, `common.models`, `common.config`, `client.smtp_client`, `client.mime_handler`
- `pop3_cli.py` 依赖于 `common.utils`, `common.config`, `client.pop3_client`, `server.db_handler`
