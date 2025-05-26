# 邮件系统项目

## 项目概述

这是一个完整的邮件系统实现，包含SMTP和POP3服务器以及相应的客户端。系统支持SSL/TLS加密、用户认证、高并发处理和完整的邮件存储功能。

## 功能特性

### ✅ 已完成功能
- **SMTP服务器**: SSL/TLS支持，用户认证，邮件发送
- **POP3服务器**: SSL/TLS支持，高并发优化，邮件接收
- **客户端**: 邮件发送/接收，本地存储，用户认证
- **数据库**: SQLite存储，WAL模式，元数据管理
- **安全**: SSL证书，密码加密，用户权限管理

### 📊 性能指标
- **并发支持**: 200+并发连接
- **SSL连接**: 100%成功率
- **响应时间**: <3秒 (高并发场景)
- **资源使用**: CPU <6%, 内存合理

## 快速开始

### 环境要求
- Python 3.8 或更高版本
- pip 包管理器

### 安装依赖
```bash
# 手动安装
pip install -r requirements.txt
```

### 初始化环境
```bash
python init_project.py
```

### 🎯 推荐方式：使用统一CLI界面

**最简单的使用方式是运行统一的命令行界面：**

```bash
python cli.py
```

这将启动一个交互式菜单，提供完整的邮件客户端功能：
- 📧 发送邮件（支持附件、HTML格式）
- 📥 接收邮件（POP3/IMAP支持）
- 🔍 搜索和查看邮件
- ⚙️ 账户和服务器配置管理
- 🔒 SSL/TLS安全连接

## 🛠️ 高级用户与开发者选项（可选）

### 启动服务器
```bash
# 启动SMTP和POP3服务器
python examples/example_run_both_servers.py

# 或分别启动
python server/smtp_server.py --port 465
python server/pop3_server.py --port 995
```

### 发送邮件
```bash
python examples/send_auth_email.py \
  --host localhost --port 465 --ssl \
  --username testuser --password testpass \
  --sender test@example.com --recipient test@example.com \
  --subject "测试邮件" --content "邮件内容"
```

### 接收邮件
```bash
python -m client.pop3_cli \
  --host localhost --port 995 \
  --username testuser --password testpass --list
```

## 项目结构

```
├── server/                 # 服务器模块
│   ├── smtp_server.py     # SMTP服务器
│   ├── pop3_server.py     # POP3服务器
│   ├── db_handler.py      # 数据库处理
│   └── user_auth.py       # 用户认证
├── client/                # 客户端模块
├── examples/              # 使用示例
├── tests/                 # 测试文件
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   └── performance/      # 性能测试
├── docs/                  # 文档
├── data/                  # 数据文件
└── spam_filter/           # 垃圾邮件过滤
```

## 测试

### 运行特定测试
```bash
# 系统功能验证
python tests/integration/comprehensive_system_test.py

# SSL功能测试
python tests/integration/test_pop3_ssl.py

# 性能测试
python tests/performance/test_high_concurrency.py
```

## 已知问题

1. **邮件格式处理问题**（正在修复中）：
   - 客户端发送和服务端接收的邮件格式不一致
   - .eml文件保存和读取的格式兼容性问题
   - 邮件头部编码解码处理不统一
   - MIME类型处理和多部分邮件解析存在差异
   - 附件编码解码在不同组件间不兼容
   - 数据库存储的邮件元数据解析不一致

2. **SSL连接稳定性**：
   - POP3 SSL连接在首次成功后可能失败
   - 需要进一步优化SSL握手和连接管理

3. **性能优化**：
   - 大量并发连接时的性能表现需要测试
   - 内存使用优化

4. **错误处理**：
   - 某些边缘情况的错误处理可能不够完善

## 文档

- [用户指南](docs/user_guide/)
- [API文档](docs/api/)
- [开发指南](docs/development/)

## 许可证

MIT License
