# 基于SMTP/POP3协议的电子邮件客户端

这是一个基于SMTP/POP3协议的电子邮件客户端和服务器系统，实现了邮件的发送、接收、存储和安全机制。

## 项目状态

当前项目已完成核心功能的实现和全面测试，包括SMTP客户端、POP3客户端、用户认证、MIME处理、本地存储和基本工具函数。所有核心功能已通过系统测试，确保稳定可靠。尚未实现的功能包括图形用户界面、IMAP客户端和部分服务器端功能。

详细的项目状态和进展请参见[项目总结报告](docs/project_summary.md)。

## 功能特点

### 已实现的客户端功能

- **邮件发送**：通过SMTP协议发送纯文本/HTML邮件，支持添加附件和多收件人（包括抄送和密送）
- **邮件接收**：通过POP3协议获取邮箱邮件列表并下载内容，支持批量下载和过滤
- **用户认证**：支持多种认证方法（基本认证、LOGIN、PLAIN）和SSL/TLS加密连接，具有重试和降级机制
- **本地存储**：将接收和发送的邮件保存为`.eml`格式文件并记录在SQLite数据库中，支持元数据管理
- **邮件搜索**：支持按发件人、主题、内容等条件搜索邮件，包括全文搜索
- **邮件过滤**：支持按日期、发件人、主题等条件过滤邮件，提高处理效率
- **邮件查看**：提供多种方式查看邮件内容，包括通过ID查看、仅查看邮件头/正文/附件等
- **附件处理**：支持提取和保存各类附件，包括文本、图片、文档等
- **错误处理**：健壮的错误处理机制，提供详细的错误信息和日志记录

### 部分实现的服务端功能

- **数据库存储**：使用SQLite数据库保存邮件元数据
- **基础框架**：SMTP和POP3服务器的基本框架已实现

### 计划实现的功能

- **图形用户界面**：使用PyQt5实现邮件客户端的图形界面
- **IMAP客户端**：支持更现代的邮件协议，包括文件夹管理和邮件标记
- **垃圾邮件过滤**：基于关键词匹配或贝叶斯分类器标记垃圾邮件
- **完整的服务器端**：完成SMTP和POP3服务器的实现
- **Web邮件界面**：使用Flask/Django开发浏览器端邮件管理系统

## 项目结构

```
cs3611_email/
├── client/                # 客户端代码
│   ├── smtp_client.py     # SMTP客户端实现
│   ├── pop3_client.py     # POP3客户端实现
│   ├── mime_handler.py    # MIME编码/解码处理
│   ├── security.py        # 安全相关功能（SSL/TLS）
│   └── gui/               # 图形界面（可选）
├── server/                # 服务端代码
│   ├── smtp_server.py     # SMTP服务器实现
│   ├── pop3_server.py     # POP3服务器实现
│   ├── db_handler.py      # 数据库操作
│   └── user_auth.py       # 用户认证
├── common/                # 公共模块
│   ├── config.py          # 配置文件
│   ├── utils.py           # 工具函数
│   └── models.py          # 数据模型
├── extensions/            # 扩展功能
│   ├── spam_filter.py     # 垃圾邮件过滤
│   ├── pgp_encryption.py  # PGP加密
│   ├── mail_recall.py     # 邮件撤回功能
│   └── web_interface/     # Web界面（Flask/Django）
├── tests/                 # 测试代码
├── docs/                  # 文档
├── requirements.txt       # 依赖包
├── main.py                # 主入口
└── init_project.py        # 项目初始化脚本
```

## 安装与使用

### 环境要求

- Python 3.8+
- 依赖包（见`requirements.txt`）

### 安装步骤

1. 克隆仓库：
   ```
   git clone https://github.com/yourusername/cs3611_email.git
   cd cs3611_email
   ```

2. 创建虚拟环境（可选）：
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

4. 初始化项目：
   ```
   python init_project.py
   ```

### 使用方法

#### 启动服务器

启动SMTP服务器：
```
python main.py --server --smtp
```

启动POP3服务器：
```
python main.py --server --pop3
```

#### 使用客户端

发送邮件：
```
python main.py --client --send email.eml --username your_email@example.com --password your_password
```

接收邮件：
```
python main.py --client --receive --username your_email@example.com --password your_password
```

查看已发送邮件：
```
python examples/list_sent_emails.py
```

查看特定已发送邮件的详细内容：
```
python examples/list_sent_emails.py --view message_id --verbose
```

搜索邮件：
```
python examples/search_emails.py "搜索关键词"
```

搜索邮件（高级选项）：
```
# 只搜索主题和发件人
python examples/search_emails.py "搜索关键词" --fields subject,from_addr

# 搜索邮件正文内容（会降低搜索速度）
python examples/search_emails.py "搜索关键词" --content

# 只搜索已发送邮件
python examples/search_emails.py "搜索关键词" --sent-only

# 只搜索已接收邮件
python examples/search_emails.py "搜索关键词" --received-only

# 包含已删除和垃圾邮件
python examples/search_emails.py "搜索关键词" --include-deleted --include-spam

# 查看搜索结果中的特定邮件
python examples/search_emails.py "搜索关键词" --view message_id --verbose

# 使用ID的一部分查看邮件（更方便）
python examples/search_emails.py "搜索关键词" --id message_id_part
```

查看邮件（通过ID）：
```
# 查看特定ID的邮件
python tools/view_email_by_id.py message_id

# 查看ID的一部分匹配的邮件
python tools/view_email_by_id.py message_id_part --list

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

接收邮件（高级选项）：
```
# 限制接收数量
python main.py --client --receive --username your_email@example.com --password your_password --limit 10

# 只接收特定日期之后的邮件
python main.py --client --receive --username your_email@example.com --password your_password --since 2023-01-01

# 只接收来自特定发件人的邮件
python main.py --client --receive --username your_email@example.com --password your_password --from someone@example.com

# 只接收主题包含特定字符串的邮件
python main.py --client --receive --username your_email@example.com --password your_password --subject "重要"
```

启动图形界面（如果实现）：
```
python main.py --client --gui
```

#### 启动Web界面（如果实现）

```
python main.py --web
```

## 实用工具

### 邮件导入工具

将.eml文件导入到数据库中，以便搜索和管理：

```
python tools/import_emails.py
```

高级选项：
```
# 强制重新导入所有邮件
python tools/import_emails.py --force

# 指定邮件目录
python tools/import_emails.py --dir path/to/emails

# 显示详细信息
python tools/import_emails.py --verbose
```

### 邮件查看工具

以友好的格式查看.eml文件内容：

```
python tools/view_email.py path/to/email.eml
```

高级选项：
```
# 显示原始内容
python tools/view_email.py path/to/email.eml --raw

# 只显示邮件头
python tools/view_email.py path/to/email.eml --headers

# 只显示纯文本内容
python tools/view_email.py path/to/email.eml --text

# 只显示HTML内容
python tools/view_email.py path/to/email.eml --html

# 只显示附件信息
python tools/view_email.py path/to/email.eml --attachments

# 提取附件到指定目录
python tools/view_email.py path/to/email.eml --extract path/to/output/dir
```

## 已知问题和限制

- **文件名处理**：在Windows系统上，邮件文件名中的特殊字符可能导致问题，已实现安全文件名处理但可能仍有边缘情况
- **POP3协议限制**：不支持邮件标记和文件夹管理（POP3协议本身的限制），需要实现IMAP支持来解决
- **大型附件**：发送和接收大型附件时可能遇到内存限制，建议分割大型附件或使用云存储链接
- **HTML邮件**：某些复杂的HTML邮件可能解析不正确，特别是包含嵌入式内容和非标准格式的邮件
- **数据库性能**：大量邮件时的数据库性能尚未优化，可能需要添加索引和查询优化
- **安全性**：密码在配置文件中以明文存储，缺乏完整的安全审计机制，建议实现加密存储
- **Unicode支持**：在处理包含特殊字符和表情符号的邮件时可能存在编码问题，已添加错误处理但可能不完善
- **资源管理**：在某些错误情况下可能存在资源泄漏，如未关闭的网络连接，已实现安全关闭机制但可能不完善
- **跨平台兼容性**：在不同操作系统上可能存在路径处理和文件系统兼容性问题

更多已知问题和限制请参见[项目总结报告](docs/project_summary.md)。

## 测试账户

初始化脚本会创建以下测试账户：

- 用户名: admin, 密码: admin123, 邮箱: admin@example.com
- 用户名: user1, 密码: user123, 邮箱: user1@example.com
- 用户名: user2, 密码: user123, 邮箱: user2@example.com

## 开发文档

详细的开发文档请参见[开发者指南](docs/developer_guide.md)。
完整的项目状态和进展请参见[项目总结报告](docs/project_summary.md)。
测试相关信息请参见[测试指南](docs/testing_guide.md)。
用户使用说明请参见[用户手册](docs/user_manual.md)。

## 下一步开发计划

### 短期计划（1-2个月）

1. **优化存储机制**
   - 改进数据库结构，提高查询效率
   - 添加索引和缓存机制
   - 实现邮件压缩存储，减少磁盘占用

2. **增强安全性**
   - 实现密码加密存储
   - 添加证书验证功能
   - 实现更安全的认证机制

3. **完善错误处理**
   - 提供更友好的错误消息
   - 增强日志记录和诊断功能
   - 实现自动恢复机制

### 中期计划（3-6个月）

1. **实现基本图形界面**
   - 使用PyQt5开发简单的图形用户界面
   - 实现邮件列表和预览功能
   - 添加基本的设置界面

2. **添加垃圾邮件过滤功能**
   - 实现基于规则的邮件过滤
   - 添加发件人黑名单/白名单功能
   - 实现简单的垃圾邮件检测算法

3. **实现基本的IMAP支持**
   - 支持文件夹管理和邮件标记
   - 实现邮件状态同步
   - 支持服务器端搜索

### 长期计划（6个月以上）

1. **完整的图形界面**
   - 实现功能完善的图形用户界面
   - 添加主题和自定义选项
   - 实现拖放和快捷键支持

2. **完整的IMAP支持**
   - 支持所有IMAP功能
   - 实现离线操作和同步
   - 支持多账户管理

3. **Web邮件界面**
   - 开发基于Flask/Django的Web邮件系统
   - 实现响应式设计，支持移动设备
   - 添加在线编辑和预览功能

更详细的开发计划请参见[项目总结报告](docs/project_summary.md)。

## 许可证

本项目采用MIT许可证。详情请参见`LICENSE`文件。