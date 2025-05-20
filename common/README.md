# 公共模块 (Common Module)

本目录包含邮件系统的公共模块，提供数据模型、配置和工具函数等基础功能。

## 文件结构

```
common/
├── __init__.py           # 包初始化文件
├── models.py             # 数据模型定义
├── utils.py              # 工具函数
├── config.py             # 配置文件
└── port_config.py        # 端口配置管理
```

## 模块详细说明

### models.py

数据模型模块，定义应用程序的数据结构。

#### 枚举: `EmailStatus`

**描述**: 邮件状态枚举。

**值**:
- `DRAFT`: 草稿
- `SENT`: 已发送
- `RECEIVED`: 已接收
- `DELETED`: 已删除
- `SPAM`: 垃圾邮件

#### 枚举: `EmailPriority`

**描述**: 邮件优先级枚举。

**值**:
- `LOW`: 低优先级
- `NORMAL`: 普通优先级
- `HIGH`: 高优先级

#### 类: `Attachment`

**描述**: 附件数据模型。

**构造函数参数**:
- `filename` (str): 文件名
- `content_type` (str): 内容类型
- `content` (bytes): 二进制内容
- `size` (int): 文件大小，默认为0

**方法**:
- `__post_init__()`: 初始化后处理，如果size为0则计算content的长度
- `to_dict() -> Dict[str, Any]`: 转换为字典（用于序列化）

#### 类: `EmailAddress`

**描述**: 邮件地址数据模型。

**构造函数参数**:
- `name` (str): 显示名称
- `address` (str): 邮件地址

**方法**:
- `__str__() -> str`: 返回格式化的邮件地址字符串
- `to_dict() -> Dict[str, str]`: 转换为字典

#### 类: `Email`

**描述**: 邮件数据模型。

**构造函数参数**:
- `message_id` (str): 邮件ID
- `subject` (str): 邮件主题
- `from_addr` (EmailAddress): 发件人地址
- `to_addrs` (List[EmailAddress]): 收件人地址列表
- `cc_addrs` (List[EmailAddress]): 抄送地址列表，默认为空列表
- `bcc_addrs` (List[EmailAddress]): 密送地址列表，默认为空列表
- `text_content` (str): 纯文本内容，默认为空字符串
- `html_content` (str): HTML内容，默认为空字符串
- `attachments` (List[Attachment]): 附件列表，默认为空列表
- `date` (datetime): 日期时间，默认为当前时间
- `status` (EmailStatus): 邮件状态，默认为DRAFT
- `priority` (EmailPriority): 邮件优先级，默认为NORMAL
- `is_read` (bool): 是否已读，默认为False
- `spam_score` (float): 垃圾邮件评分，默认为0.0
- `server_id` (Optional[str]): 服务器ID，默认为None
- `in_reply_to` (Optional[str]): 回复的邮件ID，默认为None
- `references` (List[str]): 引用的邮件ID列表，默认为空列表
- `headers` (Dict[str, str]): 自定义头部，默认为空字典

**方法**:
- `to_dict() -> Dict[str, Any]`: 转换为字典（用于序列化）
- `from_dict(data: Dict[str, Any]) -> 'Email'`: 从字典创建Email对象（类方法）

#### 类: `User`

**描述**: 用户数据模型。

**构造函数参数**:
- `username` (str): 用户名
- `email` (str): 邮箱
- `password_hash` (str): 密码哈希
- `salt` (str): 盐值
- `full_name` (str): 全名，默认为空字符串
- `is_active` (bool): 是否激活，默认为True
- `created_at` (datetime): 创建时间，默认为当前时间
- `last_login` (Optional[datetime]): 最后登录时间，默认为None

**方法**:
- `to_dict() -> Dict[str, Any]`: 转换为字典
- `from_dict(data: Dict[str, Any]) -> 'User'`: 从字典创建User对象（类方法）

### utils.py

工具函数模块，提供各种通用功能。

**函数**:
- `setup_logging(name: str, level: Optional[str] = None) -> logging.Logger`: 设置并返回一个配置好的日志记录器
- `generate_message_id(domain: str = "localhost") -> str`: 生成唯一的邮件ID
- `generate_timestamp() -> str`: 生成RFC 2822格式的时间戳
- `hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]`: 对密码进行哈希处理
- `verify_password(password: str, hashed_password: str, salt: str) -> bool`: 验证密码是否匹配
- `safe_filename(filename: str) -> str`: 确保文件名安全（移除不安全字符）
- `get_file_extension(filename: str) -> str`: 获取文件扩展名
- `is_valid_email(email: str) -> bool`: 简单验证邮箱地址格式
- `safe_print(text, end="\n")`: 安全地打印文本，处理编码错误

**类**:
- `SafeFormatter(logging.Formatter)`: 自定义格式化器，处理编码错误

### config.py

配置文件模块，管理应用程序的所有配置参数。

**常量**:
- `BASE_DIR` (Path): 项目根目录
- `DATA_DIR` (str): 数据存储目录
- `EMAIL_STORAGE_DIR` (str): 邮件存储目录
- `DB_PATH` (str): 数据库路径
- `SMTP_SERVER` (Dict): SMTP服务器配置
- `POP3_SERVER` (Dict): POP3服务器配置
- `SSL_CERT_FILE` (str): SSL证书文件路径
- `SSL_KEY_FILE` (str): SSL密钥文件路径
- `AUTH_REQUIRED` (bool): 是否要求认证
- `MAX_CONNECTIONS` (int): 最大连接数
- `CONNECTION_TIMEOUT` (int): 连接超时时间（秒）
- `THREAD_POOL_SIZE` (int): 线程池大小
- `SOCKET_BACKLOG` (int): 套接字等待队列大小
- `CONNECTION_IDLE_TIMEOUT` (int): 空闲连接超时（秒）
- `GRACEFUL_SHUTDOWN_TIMEOUT` (int): 优雅关闭超时（秒）
- `MONITOR_INTERVAL` (int): 性能监控间隔（秒）
- `LOG_LEVEL` (str): 日志级别
- `LOG_FILE` (str): 日志文件路径
- `WEB_HOST` (str): Web界面主机名
- `WEB_PORT` (int): Web界面端口
- `SECRET_KEY` (str): 密钥
- `SPAM_FILTER_ENABLED` (bool): 是否启用垃圾邮件过滤
- `SPAM_KEYWORDS` (List[str]): 垃圾邮件关键词列表
- `SPAM_THRESHOLD` (float): 垃圾邮件阈值

### port_config.py

端口配置模块，管理服务器端口配置。

**常量**:
- `CONFIG_DIR` (Path): 配置目录
- `PORT_CONFIG_FILE` (Path): 端口配置文件路径
- `DEFAULT_CONFIG` (Dict): 默认端口配置

**函数**:
- `ensure_config_dir()`: 确保配置目录存在
- `save_port_config(service_name, port)`: 保存服务端口配置
- `get_port_config() -> Dict`: 获取端口配置
- `get_service_port(service_name, default_port=None) -> int`: 获取指定服务的端口

## 依赖关系

- `models.py` 无外部依赖
- `utils.py` 依赖于 `common.config`
- `config.py` 依赖于 `dotenv`
- `port_config.py` 无外部依赖
