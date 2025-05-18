# 邮件客户端开发者指南

本文档为开发者提供了邮件客户端项目的详细技术说明，包括架构设计、模块说明、API文档和扩展指南。

## 目录

1. [项目架构](#项目架构)
2. [核心模块](#核心模块)
3. [数据模型](#数据模型)
4. [API文档](#API文档)
5. [开发环境设置](#开发环境设置)
6. [测试指南](#测试指南)
7. [扩展指南](#扩展指南)
8. [代码规范](#代码规范)

## 项目架构

邮件客户端采用模块化设计，主要分为以下几个部分：

1. **客户端模块**：实现与邮件服务器的通信，包括SMTP客户端和POP3客户端
2. **服务器模块**：实现邮件服务器功能，包括数据库处理和用户认证
3. **公共模块**：提供通用功能，包括配置、工具函数和数据模型
4. **扩展模块**：提供额外功能，如垃圾邮件过滤、加密等

### 架构图

```
+----------------+      +----------------+      +----------------+
|   客户端模块    |<---->|   公共模块     |<---->|   服务器模块    |
+----------------+      +----------------+      +----------------+
        ^                      ^                       ^
        |                      |                       |
        v                      v                       v
+----------------+      +----------------+      +----------------+
|   用户界面      |<---->|   扩展模块     |<---->|   数据存储     |
+----------------+      +----------------+      +----------------+
```

### 数据流

1. **发送邮件流程**：
   用户界面 -> 邮件对象 -> SMTP客户端 -> 邮件服务器 -> 本地存储

2. **接收邮件流程**：
   邮件服务器 -> POP3客户端 -> 邮件对象 -> 本地存储 -> 用户界面

## 核心模块

### client/smtp_client.py

SMTP客户端模块，负责与SMTP服务器通信，发送邮件。

主要类和方法：
- `SMTPClient`：SMTP客户端类
  - `connect()`：连接到SMTP服务器
  - `disconnect()`：断开与SMTP服务器的连接
  - `send_email(email)`：发送邮件
  - `_authenticate()`：进行认证
  - `_create_mime_message(email)`：创建MIME消息

### client/pop3_client.py

POP3客户端模块，负责与POP3服务器通信，接收邮件。

主要类和方法：
- `POP3Client`：POP3客户端类
  - `connect()`：连接到POP3服务器
  - `disconnect()`：断开与POP3服务器的连接
  - `get_mailbox_status()`：获取邮箱状态
  - `list_emails()`：获取邮件列表
  - `retrieve_email(msg_num, delete=False)`：获取特定邮件
  - `retrieve_all_emails(delete=False, limit=None)`：获取所有邮件
  - `save_email_as_eml(email, directory)`：将邮件保存为.eml文件

### client/mime_handler.py

MIME处理模块，负责邮件的编码和解码。

主要类和方法：
- `MIMEHandler`：MIME处理类
  - `create_mime_message(email)`：创建MIME消息
  - `parse_mime_message(mime_message)`：解析MIME消息
  - `extract_attachments(mime_message)`：提取附件
  - `save_as_eml(email, filepath)`：将邮件保存为.eml文件
  - `load_from_eml(filepath)`：从.eml文件加载邮件

### server/db_handler.py

数据库处理模块，负责邮件元数据的存储和检索。

主要类和方法：
- `DatabaseHandler`：数据库处理类
  - `init_db()`：初始化数据库
  - `save_email_metadata(message_id, from_addr, to_addrs, subject, date, size, is_spam=False, spam_score=0.0)`：保存邮件元数据
  - `save_email_content(message_id, content)`：保存邮件内容
  - `get_email_metadata(message_id)`：获取邮件元数据
  - `get_email_content(message_id)`：获取邮件内容
  - `list_emails(user_email=None, include_deleted=False, include_spam=False, limit=100, offset=0)`：列出邮件
  - `search_emails(query, search_in=None, include_sent=True, include_received=True, include_deleted=False, include_spam=False, search_content=False, limit=100)`：搜索邮件

### common/models.py

数据模型模块，定义了邮件相关的数据结构。

主要类：
- `Email`：邮件类，表示一封完整的邮件
- `EmailAddress`：邮件地址类，表示发件人或收件人
- `Attachment`：附件类，表示邮件附件
- `EmailStatus`：邮件状态枚举，表示邮件的状态（草稿、已发送等）

### common/utils.py

工具函数模块，提供各种辅助功能。

主要函数：
- `setup_logging(name)`：设置日志记录
- `generate_message_id(domain=None)`：生成邮件ID
- `is_valid_email(email)`：验证邮件地址是否有效
- `safe_filename(filename)`：生成安全的文件名
- `format_date(date=None)`：格式化日期

### common/config.py

配置模块，存储全局配置信息。

主要配置项：
- `SMTP_SERVER`：SMTP服务器配置
- `POP3_SERVER`：POP3服务器配置
- `EMAIL_STORAGE_DIR`：邮件存储目录
- `DB_PATH`：数据库路径
- `LOG_LEVEL`：日志级别

## 数据模型

### Email 类

表示一封完整的邮件。

属性：
- `message_id`：邮件ID，格式为 `<random_string@domain>`
- `subject`：邮件主题
- `from_addr`：发件人，EmailAddress 对象
- `to_addrs`：收件人列表，EmailAddress 对象列表
- `cc_addrs`：抄送列表，EmailAddress 对象列表
- `bcc_addrs`：密送列表，EmailAddress 对象列表
- `text_content`：纯文本内容
- `html_content`：HTML内容
- `attachments`：附件列表，Attachment 对象列表
- `date`：日期时间，datetime 对象
- `status`：邮件状态，EmailStatus 枚举值
- `is_read`：是否已读
- `is_spam`：是否为垃圾邮件
- `spam_score`：垃圾邮件评分

### EmailAddress 类

表示邮件地址。

属性：
- `name`：显示名称
- `address`：邮件地址

方法：
- `to_string()`：转换为字符串，格式为 `"name" <address>`
- `to_dict()`：转换为字典，包含 `name` 和 `address` 字段

### Attachment 类

表示邮件附件。

属性：
- `filename`：文件名
- `content_type`：内容类型，如 `text/plain`、`image/jpeg` 等
- `content`：二进制内容
- `content_id`：内容ID，用于内嵌图片等

### EmailStatus 枚举

表示邮件状态。

值：
- `DRAFT`：草稿
- `SENDING`：发送中
- `SENT`：已发送
- `FAILED`：发送失败
- `RECEIVED`：已接收
- `DELETED`：已删除

## API文档

### SMTPClient 类

```python
class SMTPClient:
    def __init__(self, host=None, port=None, use_ssl=None, username=None, password=None, 
                 auth_method="AUTO", timeout=30, max_retries=3, save_sent_emails=True, 
                 sent_emails_dir=None):
        """
        初始化SMTP客户端
        
        Args:
            host: SMTP服务器地址
            port: SMTP服务器端口
            use_ssl: 是否使用SSL/TLS
            username: 用户名
            password: 密码
            auth_method: 认证方法，可选值：AUTO, LOGIN, PLAIN
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            save_sent_emails: 是否保存已发送邮件
            sent_emails_dir: 已发送邮件保存目录
        """
        
    def connect(self):
        """
        连接到SMTP服务器
        
        Raises:
            smtplib.SMTPException: 连接失败时抛出
        """
        
    def disconnect(self):
        """
        断开与SMTP服务器的连接
        """
        
    def send_email(self, email):
        """
        发送邮件
        
        Args:
            email: Email对象
            
        Returns:
            bool: 是否发送成功
        """
```

### POP3Client 类

```python
class POP3Client:
    def __init__(self, host=None, port=None, use_ssl=None, username=None, password=None, 
                 auth_method="AUTO", timeout=30, max_retries=3):
        """
        初始化POP3客户端
        
        Args:
            host: POP3服务器地址
            port: POP3服务器端口
            use_ssl: 是否使用SSL/TLS
            username: 用户名
            password: 密码
            auth_method: 认证方法，可选值：AUTO, BASIC, APOP
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        """
        
    def connect(self):
        """
        连接到POP3服务器
        
        Raises:
            poplib.error_proto: 连接失败时抛出
        """
        
    def disconnect(self):
        """
        断开与POP3服务器的连接
        """
        
    def get_mailbox_status(self):
        """
        获取邮箱状态
        
        Returns:
            tuple: (邮件数量, 邮箱大小)
        """
        
    def list_emails(self):
        """
        获取邮件列表
        
        Returns:
            list: [(邮件编号, 邮件大小), ...]
        """
        
    def retrieve_email(self, msg_num, delete=False):
        """
        获取特定邮件
        
        Args:
            msg_num: 邮件编号
            delete: 是否在获取后删除
            
        Returns:
            Email: 邮件对象
        """
        
    def retrieve_all_emails(self, delete=False, limit=None):
        """
        获取所有邮件
        
        Args:
            delete: 是否在获取后删除
            limit: 最大获取数量
            
        Returns:
            list: [Email, ...]
        """
```

## 开发环境设置

### 环境要求

- Python 3.8+
- 开发工具：任意文本编辑器或IDE（推荐VS Code或PyCharm）
- 版本控制：Git

### 设置步骤

1. 克隆仓库：
   ```bash
   git clone https://github.com/yourusername/cs3611_email.git
   cd cs3611_email
   ```

2. 创建虚拟环境：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

4. 安装开发依赖：
   ```bash
   pip install -r requirements-dev.txt
   ```

5. 设置预提交钩子：
   ```bash
   pre-commit install
   ```

## 测试指南

详细的测试指南请参见 [测试指南](testing_guide.md)。

### 运行单元测试

```bash
python -m unittest discover tests
```

### 运行特定测试

```bash
python -m unittest tests.test_smtp_client
```

### 生成测试覆盖率报告

```bash
coverage run -m unittest discover tests
coverage report
coverage html  # 生成HTML报告
```

## 扩展指南

### 添加新功能

1. 在适当的模块中添加新的类或函数
2. 更新相关的文档
3. 添加单元测试
4. 提交代码并创建合并请求

### 添加新的认证方法

1. 在 `client/smtp_client.py` 或 `client/pop3_client.py` 中的 `_authenticate` 方法中添加新的认证方法
2. 更新 `common/config.py` 中的认证方法选项
3. 添加单元测试验证新的认证方法

### 添加新的邮件格式

1. 在 `client/mime_handler.py` 中添加新的邮件格式处理方法
2. 更新 `Email` 类以支持新的格式
3. 添加单元测试验证新的格式处理

## 代码规范

### Python 风格指南

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 风格指南
- 使用 4 个空格缩进
- 行长度限制为 100 个字符
- 使用 Google 风格的文档字符串

### 命名约定

- 类名：使用 CamelCase（驼峰命名法）
- 函数和变量名：使用 snake_case（蛇形命名法）
- 常量：使用 UPPER_CASE（全大写）
- 私有方法和变量：使用前导下划线（如 `_private_method`）

### 注释和文档

- 所有公共类和方法都应该有文档字符串
- 复杂的代码段应该有注释说明
- 使用 TODO 注释标记待完成的工作

### 提交消息

- 使用现在时态（"Add feature"而不是"Added feature"）
- 第一行是简短的摘要（50个字符以内）
- 如果需要，可以添加详细说明
- 引用相关的问题编号（如"Fixes #123"）
