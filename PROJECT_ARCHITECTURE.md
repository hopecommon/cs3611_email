# 邮件系统项目架构文档

## 项目概述

这是一个完整的邮件系统实现，包含SMTP和POP3服务器以及相应的客户端。系统支持SSL/TLS加密、用户认证、高并发处理、PGP加密、Web界面和完整的邮件存储功能。

## 技术栈

### 核心技术
- **Python 3.8+**: 主要开发语言
- **SQLite**: 数据库存储（WAL模式）
- **SSL/TLS**: 传输层安全加密
- **Flask**: Web界面框架
- **aiosmtpd**: 异步SMTP服务器框架

### 主要依赖
- **cryptography**: 加密功能和SSL/TLS支持
- **pyOpenSSL**: SSL/TLS连接实现
- **SQLAlchemy**: ORM框架
- **Flask-Login**: Web用户认证
- **dnspython**: DNS查询功能
- **pytest**: 测试框架

## 项目结构

```
cs3611_email/
├── client/                 # 客户端模块
│   ├── smtp_client.py      # SMTP客户端实现 (578行)
│   ├── pop3_client.py      # POP3客户端实现 (916行)
│   ├── mime_handler.py     # MIME编码/解码处理 (272行)
│   ├── security.py         # 安全功能模块 (310行)
│   ├── socket_utils.py     # 套接字工具函数 (87行)
│   ├── smtp_cli.py         # SMTP命令行接口 (302行)
│   └── pop3_cli.py         # POP3命令行接口 (329行)
├── server/                 # 服务器模块
│   ├── smtp_server.py      # SMTP服务器实现
│   ├── pop3_server.py      # POP3服务器实现
│   ├── new_db_handler.py   # 统一数据库处理
│   ├── user_auth.py        # 用户认证系统
│   └── email_repository.py # 邮件存储库
├── common/                 # 公共模块
│   ├── models.py           # 数据模型定义
│   ├── config.py           # 配置管理
│   ├── utils.py            # 工具函数
│   ├── email_format_handler.py # 邮件格式处理
│   ├── email_content_processor.py # 邮件内容处理
│   └── port_config.py      # 端口配置管理
├── cli/                    # CLI界面模块
│   ├── main_cli.py         # 主CLI控制器
│   ├── send_menu.py        # 发送邮件菜单
│   ├── receive_menu.py     # 接收邮件菜单
│   ├── view_menu.py        # 查看邮件菜单
│   ├── search_menu.py      # 搜索邮件菜单
│   └── modern_settings_menu.py # 现代化设置菜单
├── web/                    # Web界面模块
│   ├── __init__.py         # Flask应用初始化
│   ├── routes/             # 路由模块
│   │   ├── auth.py         # 认证路由
│   │   ├── email.py        # 邮件操作路由
│   │   ├── main.py         # 主页路由
│   │   └── cli_api.py      # CLI集成API
│   ├── templates/          # HTML模板
│   ├── static/             # 静态资源
│   └── models.py           # Web数据模型
├── config/                 # 配置文件
│   ├── email_providers.json # 邮件服务商配置
│   ├── port_config.json    # 端口配置
│   └── spam_keywords.json  # 垃圾邮件关键词
├── tests/                  # 测试模块
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试
│   └── performance/        # 性能测试
├── data/                   # 数据目录
│   ├── emails/             # 邮件存储(.eml文件)
│   └── email_db.sqlite     # SQLite数据库
├── certs/                  # SSL证书
│   ├── server.crt          # 服务器证书
│   └── server.key          # 服务器私钥
├── spam_filter/            # 垃圾邮件过滤
├── examples/               # 使用示例
├── docs/                   # 文档
└── tools/                  # 工具脚本
```

## 核心模块架构

### 1. 客户端模块 (client/)

#### SMTP客户端 (smtp_client.py)
- **功能**: 邮件发送和SMTP协议处理
- **特性**:
  - 多种认证方式(LOGIN/PLAIN/AUTO)
  - SSL/TLS加密支持
  - 自动重试机制(最大3次)
  - 已发送邮件本地保存(.eml格式)
- **关键方法**:
  - `connect()`: 连接SMTP服务器并认证
  - `send_email(email)`: 发送邮件
  - `disconnect()`: 安全断开连接

#### POP3客户端 (pop3_client.py)
- **功能**: 邮件接收和POP3协议处理
- **特性**:
  - BASIC/APOP认证支持
  - 连接超时和重试机制
  - 邮件过滤(按日期、发件人、主题)
  - 复杂邮件头部解码
- **关键方法**:
  - `connect()`: 连接POP3服务器并认证
  - `retrieve_all_emails()`: 获取所有邮件
  - `save_email_as_eml()`: 保存邮件为.eml文件

#### MIME处理器 (mime_handler.py)
- **功能**: MIME编码/解码处理
- **特性**:
  - 附件编码和解码
  - .eml文件解析和生成
  - 邮件头部编码处理(RFC 2047)
  - MIME类型自动检测
- **关键方法**:
  - `encode_attachment(file_path)`: 文件转附件
  - `parse_eml_file(file_path)`: 解析.eml文件
  - `save_as_eml(email, file_path)`: 保存为.eml文件

#### 安全管理器 (security.py)
- **功能**: SSL/TLS和加密功能
- **特性**:
  - SSL/TLS上下文创建和管理
  - SMTP认证字符串生成/验证
  - AES数据加密/解密
  - 密码哈希和验证
- **关键方法**:
  - `create_ssl_context()`: 创建SSL上下文
  - `generate_auth_string()`: 生成认证字符串
  - `encrypt_data()/decrypt_data()`: 数据加密/解密

### 2. 服务器模块 (server/)

#### SMTP服务器 (smtp_server.py)
- **功能**: 接收客户端发送的邮件
- **特性**:
  - SSL/TLS支持
  - 用户认证
  - 高并发处理(200+连接)
  - 邮件存储和转发
- **性能指标**:
  - 并发连接: 200+
  - SSL连接成功率: 100%
  - 响应时间: <3秒

#### POP3服务器 (pop3_server.py)
- **功能**: 向客户端提供邮件接收服务
- **特性**:
  - SSL/TLS支持
  - 高并发优化
  - 邮件检索和管理
  - 连接稳定性优化
- **性能指标**:
  - 并发连接: 100+
  - 连接成功率: 95%+
  - 响应时间: <1秒

#### 数据库处理器 (new_db_handler.py)
- **功能**: 统一的邮件数据库操作
- **特性**:
  - SQLite WAL模式
  - 邮件元数据管理
  - 用户数据管理
  - 事务处理
- **关键方法**:
  - `save_email()`: 保存邮件
  - `get_emails()`: 获取邮件列表
  - `search_emails()`: 搜索邮件

#### 用户认证 (user_auth.py)
- **功能**: 用户认证和权限管理
- **特性**:
  - 密码哈希存储
  - 会话管理
  - 权限验证
  - 安全登录

### 3. 公共模块 (common/)

#### 数据模型 (models.py)
- **Email**: 邮件数据模型
- **EmailAddress**: 邮件地址模型
- **Attachment**: 附件模型
- **User**: 用户模型
- **EmailStatus**: 邮件状态枚举
- **EmailPriority**: 邮件优先级枚举

#### 配置管理 (config.py)
- **功能**: 全局配置管理
- **特性**:
  - 环境变量支持
  - 配置文件加载
  - 默认值设置
  - 路径配置

#### 邮件格式处理 (email_format_handler.py)
- **功能**: 统一的邮件格式处理
- **特性**:
  - RFC 2047编码支持
  - 多种字符集处理
  - MIME类型处理
  - 格式兼容性

### 4. CLI界面模块 (cli/)

#### 主CLI控制器 (main_cli.py)
- **功能**: 基于菜单的邮件客户端操作界面
- **特性**:
  - 交互式菜单系统
  - 账户状态显示
  - 功能模块集成
  - 用户友好界面

#### 功能菜单模块
- **send_menu.py**: 发送邮件功能
- **receive_menu.py**: 接收邮件功能
- **view_menu.py**: 查看邮件功能
- **search_menu.py**: 搜索邮件功能
- **modern_settings_menu.py**: 设置管理功能

### 5. Web界面模块 (web/)

#### Flask应用 (__init__.py)
- **功能**: Web应用初始化和配置
- **特性**:
  - Flask应用工厂模式
  - 蓝图注册
  - 中间件配置
  - 安全设置

#### 路由模块 (routes/)
- **auth.py**: 用户认证路由
- **email.py**: 邮件操作路由
- **main.py**: 主页和仪表板路由
- **cli_api.py**: CLI功能集成API

#### 模板和静态资源
- **templates/**: HTML模板文件
- **static/**: CSS、JavaScript、图片等静态资源

## 数据库设计

### 邮件表 (emails)
```sql
CREATE TABLE emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    subject TEXT,
    from_addr TEXT,
    to_addrs TEXT,
    cc_addrs TEXT,
    bcc_addrs TEXT,
    date TIMESTAMP,
    status TEXT,
    is_read BOOLEAN DEFAULT 0,
    spam_score REAL DEFAULT 0.0,
    file_path TEXT,
    headers TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 用户表 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    full_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### 附件表 (attachments)
```sql
CREATE TABLE attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER,
    filename TEXT NOT NULL,
    content_type TEXT,
    size INTEGER,
    file_path TEXT,
    FOREIGN KEY (email_id) REFERENCES emails (id)
);
```

## 安全架构

### SSL/TLS实现
- **证书管理**: 自签名证书自动生成
- **加密套件**: ECDHE+AESGCM, ECDHE+CHACHA20等
- **协议版本**: TLS 1.2+
- **证书验证**: 支持自定义CA证书

### 用户认证
- **密码存储**: bcrypt哈希 + 随机盐
- **会话管理**: Flask-Login集成
- **权限控制**: 基于角色的访问控制
- **认证方式**: LOGIN, PLAIN, APOP

### 数据加密
- **传输加密**: SSL/TLS
- **存储加密**: AES-256
- **PGP支持**: 端到端加密(开发中)
- **密钥管理**: 安全密钥存储

## 性能优化

### 并发处理
- **SMTP服务器**: 200+并发连接
- **POP3服务器**: 100+并发连接
- **连接池**: 数据库连接池
- **异步处理**: aiosmtpd异步框架

### 内存优化
- **流式处理**: 大文件流式读取
- **缓存机制**: 邮件头部缓存
- **垃圾回收**: 及时释放资源
- **连接管理**: 自动连接清理

### 数据库优化
- **WAL模式**: SQLite WAL模式
- **索引优化**: 关键字段索引
- **查询优化**: SQL查询优化
- **事务管理**: 批量事务处理

## 测试架构

### 测试分类
- **单元测试**: 模块功能测试
- **集成测试**: 系统集成测试
- **性能测试**: 并发和压力测试
- **安全测试**: SSL和认证测试

### 测试工具
- **pytest**: 主要测试框架
- **unittest**: Python标准测试库
- **mock**: 模拟外部依赖
- **coverage**: 测试覆盖率

### 测试指标
- **代码覆盖率**: >80%
- **测试通过率**: 100%
- **性能基准**: 响应时间<3秒
- **并发测试**: 200+连接

## 部署架构

### 环境要求
- **Python**: 3.8+
- **操作系统**: Windows/Linux/macOS
- **内存**: 最小512MB
- **存储**: 最小1GB

### 部署方式
- **单机部署**: 所有组件在一台机器
- **分布式部署**: 客户端/服务器分离
- **容器部署**: Docker支持(规划中)
- **云部署**: 云服务器支持

### 配置管理
- **环境变量**: .env文件配置
- **配置文件**: JSON格式配置
- **命令行参数**: 运行时参数覆盖
- **默认配置**: 内置默认值

## 扩展性设计

### 模块化架构
- **插件系统**: 支持功能插件
- **接口标准**: 统一的接口规范
- **依赖注入**: 松耦合设计
- **事件系统**: 事件驱动架构

### 协议扩展
- **IMAP支持**: 规划中
- **Exchange支持**: 规划中
- **自定义协议**: 可扩展协议栈
- **API接口**: RESTful API

### 功能扩展
- **邮件规则**: 自动处理规则
- **联系人管理**: 通讯录功能
- **日历集成**: 日程管理
- **文件同步**: 云存储集成

## 监控和日志

### 日志系统
- **分级日志**: DEBUG/INFO/WARNING/ERROR
- **文件日志**: 日志文件轮转
- **控制台日志**: 实时日志输出
- **结构化日志**: JSON格式日志

### 性能监控
- **连接监控**: 连接数和状态
- **响应时间**: 请求响应时间
- **资源使用**: CPU和内存使用
- **错误率**: 错误统计和分析

### 健康检查
- **服务状态**: 服务可用性检查
- **数据库状态**: 数据库连接检查
- **SSL证书**: 证书有效期检查
- **磁盘空间**: 存储空间监控

## 开发工作流

### 代码规范
- **PEP 8**: Python代码规范
- **类型提示**: 类型注解
- **文档字符串**: 函数和类文档
- **代码审查**: Pull Request审查

### 版本控制
- **Git**: 版本控制系统
- **分支策略**: Git Flow
- **提交规范**: 规范化提交信息
- **标签管理**: 版本标签

### 持续集成
- **自动测试**: 提交时自动测试
- **代码质量**: 代码质量检查
- **安全扫描**: 安全漏洞扫描
- **部署自动化**: 自动部署流程

## 技术实现细节

### SSL/TLS安全实现

#### 证书管理
```python
# 自动生成自签名证书
def _create_self_signed_cert(self):
    """创建自签名SSL证书"""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    # 生成私钥
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 创建证书
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CS3611 Email System"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
```

#### SSL上下文配置
```python
# SSL上下文创建
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.set_ciphers(
    "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
)
```

### 邮件格式处理 (RFC 2047)

#### 中文编码处理
```python
def encode_header_value(value: str) -> str:
    """RFC 2047邮件头编码"""
    if not value:
        return value

    # 检查是否包含非ASCII字符
    try:
        value.encode('ascii')
        return value
    except UnicodeEncodeError:
        # 使用Base64编码
        encoded = base64.b64encode(value.encode('utf-8')).decode('ascii')
        return f"=?utf-8?B?{encoded}?="

def decode_header_value(value: str) -> str:
    """RFC 2047邮件头解码"""
    if not value or '=?' not in value:
        return value

    decoded_parts = []
    for part, encoding in decode_header(value):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or 'utf-8'))
        else:
            decoded_parts.append(part)

    return ''.join(decoded_parts)
```

### 并发处理架构

#### SMTP服务器并发
```python
class LimitedConnectionController:
    """限制连接数的SMTP控制器"""

    def __init__(self, max_connections=200):
        self.max_connections = max_connections
        self.current_connections = 0
        self.connection_lock = threading.Lock()

    def handle_connection(self, session):
        with self.connection_lock:
            if self.current_connections >= self.max_connections:
                raise ConnectionRefusedError("Too many connections")
            self.current_connections += 1

        try:
            # 处理连接
            self.process_session(session)
        finally:
            with self.connection_lock:
                self.current_connections -= 1
```

#### POP3服务器并发
```python
class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    """多线程TCP服务器"""

    def __init__(self, server_address, RequestHandlerClass,
                 email_service, user_auth, use_ssl, ssl_context, max_connections):
        self.max_connections = max_connections
        self.current_connections = 0
        self.connection_lock = threading.Lock()

        super().__init__(server_address, RequestHandlerClass)
```

### 数据库优化

#### WAL模式配置
```python
def _configure_database(self):
    """配置数据库为WAL模式"""
    self.cursor.execute("PRAGMA journal_mode=WAL")
    self.cursor.execute("PRAGMA synchronous=NORMAL")
    self.cursor.execute("PRAGMA cache_size=10000")
    self.cursor.execute("PRAGMA temp_store=memory")
```

#### 索引优化
```sql
-- 邮件表索引
CREATE INDEX idx_emails_message_id ON emails(message_id);
CREATE INDEX idx_emails_date ON emails(date);
CREATE INDEX idx_emails_status ON emails(status);
CREATE INDEX idx_emails_from_addr ON emails(from_addr);

-- 用户表索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

### 垃圾邮件过滤

#### 关键词过滤
```python
class SpamFilter:
    """垃圾邮件过滤器"""

    def __init__(self):
        self.spam_keywords = self._load_spam_keywords()
        self.spam_threshold = 0.7

    def calculate_spam_score(self, email_content: str) -> float:
        """计算垃圾邮件分数"""
        content_lower = email_content.lower()
        spam_count = 0
        total_words = len(content_lower.split())

        for keyword in self.spam_keywords:
            if keyword.lower() in content_lower:
                spam_count += 1

        return min(spam_count / max(total_words, 1), 1.0)
```

### PGP加密实现

#### 密钥管理
```python
class PGPManager:
    """PGP加密管理器"""

    def __init__(self, gpg_home: str = None):
        self.gpg_home = gpg_home or os.path.expanduser("~/.gnupg")
        self.gpg = gnupg.GPG(gnupghome=self.gpg_home)

    def encrypt_message(self, message: str, recipient_key: str) -> str:
        """加密消息"""
        encrypted_data = self.gpg.encrypt(message, recipient_key)
        if not encrypted_data.ok:
            raise Exception(f"加密失败: {encrypted_data.status}")
        return str(encrypted_data)

    def decrypt_message(self, encrypted_message: str, passphrase: str) -> str:
        """解密消息"""
        decrypted_data = self.gpg.decrypt(encrypted_message, passphrase=passphrase)
        if not decrypted_data.ok:
            raise Exception(f"解密失败: {decrypted_data.status}")
        return str(decrypted_data)
```

## 配置文件详解

### 邮件服务商配置 (config/email_providers.json)
```json
{
  "providers": {
    "qq": {
      "name": "QQ邮箱",
      "domains": ["qq.com"],
      "smtp": {
        "host": "smtp.qq.com",
        "port": 587,
        "ssl_port": 465,
        "use_ssl": true,
        "auth_method": "LOGIN"
      },
      "pop3": {
        "host": "pop.qq.com",
        "port": 110,
        "ssl_port": 995,
        "use_ssl": true,
        "auth_method": "AUTO"
      }
    }
  }
}
```

### 端口配置 (config/port_config.json)
```json
{
  "smtp_server": 8025,
  "pop3_server": 8110,
  "smtp_ssl_server": 8465,
  "pop3_ssl_server": 8995,
  "web_server": 5000
}
```

### 垃圾邮件关键词 (config/spam_keywords.json)
```json
{
  "keywords": [
    "免费", "中奖", "优惠", "促销", "限时",
    "viagra", "casino", "lottery", "winner"
  ],
  "threshold": 0.7
}
```

## 入口点和使用示例

### 主要入口点

#### CLI界面 (推荐)
```bash
python cli.py
```

#### Web界面
```bash
python run_web.py
```

#### 服务器启动
```bash
# 启动SMTP和POP3服务器
python examples/example_run_both_servers.py

# 单独启动SMTP服务器
python server/smtp_server.py --port 465 --ssl

# 单独启动POP3服务器
python server/pop3_server.py --port 995 --ssl
```

### 代码示例

#### 发送邮件
```python
from client.smtp_client import SMTPClient
from common.models import Email, EmailAddress

# 创建邮件
email = Email(
    message_id="test@localhost",
    subject="测试邮件",
    from_addr=EmailAddress("发送者", "sender@example.com"),
    to_addrs=[EmailAddress("接收者", "recipient@example.com")],
    text_content="这是一封测试邮件"
)

# 发送邮件
client = SMTPClient(host="smtp.qq.com", port=465, use_ssl=True)
client.connect(username="your@qq.com", password="your_password")
client.send_email(email)
client.disconnect()
```

#### 接收邮件
```python
from client.pop3_client import POP3Client

# 接收邮件
client = POP3Client(host="pop.qq.com", port=995, use_ssl=True)
client.connect(username="your@qq.com", password="your_password")
emails = client.retrieve_all_emails()
client.disconnect()

for email in emails:
    print(f"主题: {email.subject}")
    print(f"发件人: {email.from_addr}")
    print(f"内容: {email.text_content}")
```

## 测试运行方法

### 单元测试
```bash
# 运行所有单元测试
python -m unittest discover tests/unit

# 运行特定测试
python tests/test_smtp_client.py
python tests/test_pop3_client.py
python tests/test_mime_handler.py
```

### 集成测试
```bash
# 系统功能验证
python tests/integration/comprehensive_system_test.py

# SSL功能测试
python tests/integration/test_pop3_ssl.py

# 邮件存储测试
python tests/integration/test_email_storage.py
```

### 性能测试
```bash
# 高并发测试
python tests/performance/test_enhanced_concurrency.py

# POP3性能测试
python tests/performance/test_pop3_performance.py

# 生成性能报告
python tests/performance/generate_visual_report.py
```

## 部署说明

### 环境准备
```bash
# 1. 安装Python 3.8+
python --version

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化项目
python init_project.py

# 4. 配置环境变量
cp .env.example .env
# 编辑.env文件设置配置
```

### 生产部署
```bash
# 1. 生成SSL证书
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt -days 365 -nodes

# 2. 配置数据库
python -c "from server.new_db_handler import EmailService; EmailService().init_database()"

# 3. 启动服务
python examples/example_run_both_servers.py

# 4. 启动Web界面
python run_web.py
```

### Docker部署 (规划中)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000 8025 8110 8465 8995

CMD ["python", "examples/example_run_both_servers.py"]
```

## 故障排除

### 常见问题

#### SSL连接失败
```bash
# 检查证书文件
ls -la certs/
# 重新生成证书
python -c "from server.smtp_server import StableSMTPServer; StableSMTPServer()._create_self_signed_cert()"
```

#### 端口占用
```bash
# 检查端口占用
python tools/check_ports.py
# 修改端口配置
# 编辑 config/port_config.json
```

#### 数据库锁定
```bash
# 检查数据库状态
python tests/data/check_db.py
# 重置数据库
rm data/email_db.sqlite
python init_project.py
```

#### 邮件格式问题
```bash
# 运行格式兼容性检查
python tools/code_consistency_audit.py
# 查看详细日志
tail -f logs/email_app.log
```

---

*本文档版本: 1.0*
*最后更新: 2025-01-30*
*维护者: CS3611 Project Team*
