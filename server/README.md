# 服务端模块 (Server Module)

本目录包含邮件服务器的实现，负责接收、存储和提供邮件服务。

## 文件结构

```
server/
├── __init__.py                   # 包初始化文件
├── basic_smtp_server.py          # 基础SMTP服务器实现
├── authenticated_smtp_server.py  # 带认证的SMTP服务器实现
├── pop3_server.py                # POP3服务器实现
├── db_handler.py                 # 数据库处理器
├── email_db.py                   # 邮件数据库接口
└── user_auth.py                  # 用户认证
```

## 模块详细说明

### basic_smtp_server.py

基础SMTP服务器模块，使用aiosmtpd实现基本的SMTP服务。

#### 类: `BasicSMTPHandler`

**描述**: 基础SMTP处理程序，处理SMTP命令和邮件接收。

**构造函数参数**:
- `db_handler` (DatabaseHandler): 数据库处理器，如果为None则创建一个新的
- `server`: SMTP服务器实例，用于访问服务器配置

**属性**:
- `db_handler` (DatabaseHandler): 数据库处理器
- `user_auth` (UserAuth): 用户认证
- `_server`: 服务器实例引用
- `authenticated_sessions` (set): 已认证的会话集合

**方法**:
- `handle_EHLO(server, session, envelope, hostname, responses) -> List`: 处理EHLO命令
- `handle_MAIL(server, session, envelope, address, mail_options) -> str`: 处理MAIL FROM命令
- `handle_RCPT(server, session, envelope, address, rcpt_options) -> str`: 处理RCPT TO命令
- `handle_DATA(server, session, envelope) -> str`: 处理DATA命令

#### 类: `BasicSMTPServer`

**描述**: 基础SMTP服务器类，使用aiosmtpd实现。

**构造函数参数**:
- `host` (str): 服务器主机名或IP地址，默认为"localhost"
- `port` (int): 服务器端口，默认为8025
- `db_handler` (DatabaseHandler): 数据库处理器，如果为None则创建一个新的
- `require_auth` (bool): 是否要求认证，默认使用配置中的值

**属性**:
- `host` (str): 服务器主机名或IP地址
- `port` (int): 服务器端口
- `db_handler` (DatabaseHandler): 数据库处理器
- `require_auth` (bool): 是否要求认证
- `handler` (BasicSMTPHandler): SMTP处理程序
- `controller` (Controller): aiosmtpd控制器

**方法**:
- `start() -> None`: 启动SMTP服务器
- `stop() -> None`: 停止SMTP服务器
- `auth_callback(server, session, envelope, mechanism, auth_data) -> AuthResult`: 认证回调函数

### authenticated_smtp_server.py

认证SMTP服务器模块，使用aiosmtpd实现带完整认证功能的SMTP服务。

#### 类: `AuthenticatedSMTPHandler`

**描述**: 认证SMTP处理程序，处理SMTP命令和邮件接收，支持完整的认证功能。

**构造函数参数**:
- `db_handler` (DatabaseHandler): 数据库处理器，如果为None则创建一个新的
- `server`: SMTP服务器实例，用于访问服务器配置

**属性**:
- `db_handler` (DatabaseHandler): 数据库处理器
- `user_auth` (UserAuth): 用户认证
- `_server`: 服务器实例引用
- `authenticated_sessions` (Set[Session]): 已认证的会话集合

**方法**:
- `handle_EHLO(server, session, envelope, hostname, responses) -> List`: 处理EHLO命令
- `handle_MAIL(server, session, envelope, address, mail_options) -> str`: 处理MAIL FROM命令
- `handle_RCPT(server, session, envelope, address, rcpt_options) -> str`: 处理RCPT TO命令
- `handle_DATA(server, session, envelope) -> str`: 处理DATA命令

#### 类: `AuthenticatedSMTPServer`

**描述**: 认证SMTP服务器类，使用aiosmtpd实现，支持完整的认证功能。

**构造函数参数**:
- `host` (str): 服务器主机名或IP地址，默认为"localhost"
- `port` (int): 服务器端口，默认为8025
- `db_handler` (DatabaseHandler): 数据库处理器，如果为None则创建一个新的
- `require_auth` (bool): 是否要求认证，默认为True
- `use_ssl` (bool): 是否使用SSL/TLS，默认为True
- `ssl_cert_file` (str): SSL证书文件路径，默认使用配置中的值
- `ssl_key_file` (str): SSL密钥文件路径，默认使用配置中的值

**属性**:
- `host` (str): 服务器主机名或IP地址
- `port` (int): 服务器端口
- `db_handler` (DatabaseHandler): 数据库处理器
- `require_auth` (bool): 是否要求认证
- `use_ssl` (bool): 是否使用SSL/TLS
- `ssl_cert_file` (str): SSL证书文件路径
- `ssl_key_file` (str): SSL密钥文件路径
- `handler` (AuthenticatedSMTPHandler): SMTP处理程序
- `controller` (Controller): aiosmtpd控制器
- `ssl_context` (ssl.SSLContext): SSL上下文

**方法**:
- `start() -> None`: 启动SMTP服务器
- `stop() -> None`: 停止SMTP服务器
- `auth_callback(server, session, envelope, mechanism, auth_data) -> AuthResult`: 认证回调函数

### pop3_server.py

POP3服务器模块，实现基本的POP3服务，支持SSL/TLS和用户认证。

#### 类: `POP3Server`

**描述**: POP3服务器类，实现基本的POP3服务。

**构造函数参数**:
- `host` (str): 服务器主机名或IP地址，默认为"localhost"
- `port` (int): 服务器端口，默认为110
- `use_ssl` (bool): 是否使用SSL/TLS，默认为False
- `ssl_port` (int): SSL/TLS端口，默认为995
- `max_connections` (int): 最大连接数，默认使用配置中的值
- `ssl_cert_file` (str): SSL证书文件路径，默认使用配置中的值
- `ssl_key_file` (str): SSL密钥文件路径，默认使用配置中的值

**属性**:
- `host` (str): 服务器主机名或IP地址
- `port` (int): 服务器端口
- `use_ssl` (bool): 是否使用SSL/TLS
- `ssl_cert_file` (str): SSL证书文件路径
- `ssl_key_file` (str): SSL密钥文件路径
- `max_connections` (int): 最大连接数
- `running` (bool): 服务器是否正在运行
- `server_socket` (socket.socket): 服务器套接字
- `db_handler` (DatabaseHandler): 数据库处理器
- `user_auth` (UserAuth): 用户认证
- `connections` (List): 连接列表
- `thread_pool` (ThreadPoolExecutor): 线程池
- `ssl_context` (ssl.SSLContext): SSL上下文

**方法**:
- `start() -> None`: 启动POP3服务器
- `stop() -> None`: 停止POP3服务器
- `_handle_connections() -> None`: 处理连接

#### 类: `POP3Session`

**描述**: POP3会话类，处理单个客户端连接。

**构造函数参数**:
- `client_socket` (socket.socket): 客户端套接字
- `client_address` (Tuple[str, int]): 客户端地址
- `db_handler` (DatabaseHandler): 数据库处理器
- `auth_required` (bool): 是否要求认证
- `users` (Dict[str, str]): 用户名到密码的映射
- `user_auth` (UserAuth): 用户认证

**属性**:
- `socket` (socket.socket): 客户端套接字
- `address` (Tuple[str, int]): 客户端地址
- `db_handler` (DatabaseHandler): 数据库处理器
- `auth_required` (bool): 是否要求认证
- `users` (Dict[str, str]): 用户名到密码的映射
- `user_auth` (UserAuth): 用户认证
- `state` (str): 会话状态
- `authenticated` (bool): 是否已认证
- `authenticated_user` (str): 已认证的用户名
- `user_email` (str): 用户邮箱地址
- `marked_for_deletion` (set): 标记为删除的邮件ID集合
- `cached_emails` (List): 缓存的邮件列表
- `last_command_time` (float): 上次命令时间
- `command_count` (int): 命令计数
- `bytes_received` (int): 接收的字节数
- `bytes_sent` (int): 发送的字节数
- `start_time` (float): 开始时间

**方法**:
- `handle() -> None`: 处理POP3会话
- `receive_command() -> str`: 接收命令
- `send_response(response: str) -> None`: 发送响应
- `process_command(command: str) -> bool`: 处理命令
- `process_user(arg: str) -> bool`: 处理USER命令
- `process_pass(arg: str) -> bool`: 处理PASS命令
- `process_quit() -> bool`: 处理QUIT命令
- `process_stat() -> bool`: 处理STAT命令
- `process_list(arg: str) -> bool`: 处理LIST命令
- `process_retr(arg: str) -> bool`: 处理RETR命令
- `process_dele(arg: str) -> bool`: 处理DELE命令
- `process_noop() -> bool`: 处理NOOP命令
- `process_rset() -> bool`: 处理RSET命令
- `process_top(arg: str) -> bool`: 处理TOP命令
- `process_uidl(arg: str) -> bool`: 处理UIDL命令
- `process_capa() -> bool`: 处理CAPA命令

### db_handler.py

数据库处理模块，管理邮件元数据和用户信息。

#### 类: `DatabaseHandler`

**描述**: 数据库处理类，管理SQLite数据库。

**构造函数参数**:
- `db_path` (str): 数据库文件路径，默认使用配置中的值

**属性**:
- `db_path` (str): 数据库文件路径

**方法**:
- `_get_connection(timeout: float = 30.0) -> sqlite3.Connection`: 获取数据库连接，带有超时和重试机制
- `init_db() -> None`: 初始化数据库表
- `save_received_email_metadata(email_obj: Any, content_path: str) -> bool`: 保存接收的邮件元数据
- `save_email_metadata(message_id: str, from_addr: str, to_addrs: List[str], subject: str, date: datetime.datetime, size: int, is_spam: bool = False, spam_score: float = 0.0) -> None`: 保存邮件元数据
- `save_email_content(message_id: str, content: str) -> None`: 保存邮件内容
- `get_email_metadata(message_id: str) -> Optional[Dict[str, Any]]`: 获取邮件元数据
- `get_email_content(message_id: str) -> Optional[str]`: 获取邮件内容
- `mark_email_as_read(message_id: str) -> bool`: 标记邮件为已读
- `mark_email_as_unread(message_id: str) -> bool`: 标记邮件为未读
- `mark_email_as_deleted(message_id: str) -> bool`: 标记邮件为已删除
- `mark_email_as_spam(message_id: str, spam_score: float = 1.0) -> bool`: 标记邮件为垃圾邮件
- `get_emails(folder: str = "inbox", limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]`: 获取邮件列表
- `search_emails(query: str, search_in: Optional[List[str]] = None, include_sent: bool = True, include_received: bool = True, include_deleted: bool = False, include_spam: bool = False, search_content: bool = False, limit: int = 100) -> List[Dict[str, Any]]`: 搜索邮件
- `save_sent_email_metadata(email_obj: Any, content_path: str) -> bool`: 保存已发送邮件元数据
- `get_sent_email_metadata(message_id: str) -> Optional[Dict[str, Any]]`: 获取已发送邮件元数据
- `list_emails(user_email: Optional[str] = None, include_deleted: bool = False, include_spam: bool = False, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]`: 列出邮件

### email_db.py

邮件数据库接口，提供简化的数据库操作接口。

#### 类: `EmailDB`

**描述**: 邮件数据库简化接口，提供统一、简洁的API来操作邮件数据库。

**构造函数参数**:
- `db_path` (str): 数据库文件路径，默认使用配置中的值

**属性**:
- `db` (DatabaseHandler): 数据库处理器

**方法**:
- `mark_as_read(message_id: str) -> bool`: 标记邮件为已读
- `mark_as_unread(message_id: str) -> bool`: 标记邮件为未读
- `mark_as_deleted(message_id: str) -> bool`: 标记邮件为已删除
- `mark_as_spam(message_id: str, spam_score: float = 1.0) -> bool`: 标记邮件为垃圾邮件
- `get_email(message_id: str) -> Optional[Dict[str, Any]]`: 获取邮件元数据和内容
- `list_emails(folder: str = "inbox", limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]`: 列出邮件
- `search(query: str, search_in: Optional[List[str]] = None, include_content: bool = False) -> List[Dict[str, Any]]`: 搜索邮件
- `search_by_date(date_str: str) -> List[Dict[str, Any]]`: 按日期搜索邮件
- `save_received_email(email_obj: Any, content_path: str) -> bool`: 保存接收的邮件
- `save_sent_email(email_obj: Any, content_path: str) -> bool`: 保存已发送的邮件

### user_auth.py

用户认证模块，处理用户认证和权限。

#### 类: `UserAuth`

**描述**: 用户认证类，处理用户管理和认证。

**构造函数参数**:
- `db_path` (str): 数据库文件路径，默认使用配置中的值

**属性**:
- `db_path` (str): 数据库文件路径

**方法**:
- `create_user(username: str, email: str, password: str, full_name: str = "") -> Optional[User]`: 创建新用户
- `authenticate(username: str, password: str) -> Optional[User]`: 验证用户凭据
- `get_user_by_username(username: str) -> Optional[User]`: 通过用户名获取用户
- `get_user_by_email(email: str) -> Optional[User]`: 通过邮箱获取用户
- `update_user(username: str, **kwargs) -> bool`: 更新用户信息
- `update_last_login(username: str) -> bool`: 更新最后登录时间
- `deactivate_user(username: str) -> bool`: 停用用户
- `activate_user(username: str) -> bool`: 激活用户
- `change_password(username: str, new_password: str) -> bool`: 修改密码
- `list_users() -> List[User]`: 列出所有用户

## 依赖关系

- `basic_smtp_server.py` 依赖于 `common.utils`, `common.config`, `server.db_handler`, `server.user_auth`
- `authenticated_smtp_server.py` 依赖于 `common.utils`, `common.config`, `server.db_handler`, `server.user_auth`
- `pop3_server.py` 依赖于 `common.utils`, `common.config`, `server.db_handler`, `server.user_auth`, `common.port_config`
- `db_handler.py` 依赖于 `common.utils`, `common.config`
- `email_db.py` 依赖于 `common.utils`, `common.config`, `server.db_handler`
- `user_auth.py` 依赖于 `common.utils`, `common.config`, `common.models`
