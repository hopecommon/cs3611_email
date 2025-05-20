# 邮件系统测试指南

本文档提供了如何测试邮件系统的详细说明，包括服务器和客户端组件的验证。

## 系统验证工具

我们提供了一个综合性的验证工具 `verify_email_system.py`，它可以自动执行以下测试流程：

1. 启动本地SMTP服务器（使用 `server/authenticated_smtp_server.py`）
2. 启动本地POP3服务器（使用 `server/pop3_server.py`）
3. 使用SMTP客户端（`client/smtp_client.py`）向本地SMTP服务器发送测试邮件
4. 使用POP3客户端（`client/pop3_client.py`）从本地POP3服务器接收这些邮件
5. 验证整个邮件发送和接收流程是否正常工作

这个工具不依赖于测试用户和预设邮件这类临时解决方案，而是通过实际的邮件发送和接收流程来验证系统功能。

## 运行系统验证测试

### 基本用法

```bash
python verify_email_system.py
```

这将自动执行完整的测试流程，并在控制台输出测试结果。

### 高级选项

```bash
# 指定SMTP服务器端口
python verify_email_system.py --smtp-port 8025

# 指定POP3服务器端口
python verify_email_system.py --pop3-port 11000

# 指定服务器主机名
python verify_email_system.py --host 127.0.0.1
```

## 测试流程详解

### 1. 启动服务器

测试工具首先会启动SMTP和POP3服务器：

- SMTP服务器默认在随机可用端口（8025-8100范围内）启动
- POP3服务器默认在随机可用端口（11000-11100范围内）启动
- 两个服务器都会创建一个测试用户（用户名：testuser，密码：testpass）

### 2. 发送测试邮件

测试工具会使用SMTP客户端发送一封测试邮件：

- 发件人：testuser@example.com
- 收件人：testuser@example.com
- 主题：包含唯一标识符的测试主题
- 内容：包含纯文本和HTML格式的测试内容

### 3. 接收测试邮件

测试工具会使用POP3客户端尝试接收刚才发送的测试邮件：

- 连接到POP3服务器
- 获取邮件列表
- 下载所有邮件
- 查找与发送的测试邮件匹配的邮件

### 4. 验证邮件内容

测试工具会验证接收到的邮件内容是否与发送的邮件一致：

- 验证邮件ID
- 验证主题
- 验证发件人
- 验证收件人
- 验证邮件内容

### 5. 清理资源

测试完成后，测试工具会停止SMTP和POP3服务器，释放所有资源。

## 常见问题及解决方法

### 端口冲突

**问题**：如果指定的端口已被占用，测试可能会失败。

**解决方法**：
- 不指定端口，让测试工具自动查找可用端口
- 使用 `--smtp-port` 和 `--pop3-port` 参数指定其他可用端口
- 使用 `netstat -ano | findstr :<端口号>` 命令查看端口占用情况

### 认证失败

**问题**：如果用户认证失败，测试可能会失败。

**解决方法**：
- 检查 `server/user_auth.py` 是否正确实现
- 检查数据库是否正确初始化
- 检查测试用户是否成功创建

### 邮件发送失败

**问题**：如果邮件发送失败，测试可能会失败。

**解决方法**：
- 检查SMTP服务器日志
- 确保SMTP服务器正确启动
- 检查认证信息是否正确

### 邮件接收失败

**问题**：如果邮件接收失败，测试可能会失败。

**解决方法**：
- 检查POP3服务器日志
- 确保POP3服务器正确启动
- 检查数据库中是否存在邮件记录
- 增加等待时间，确保邮件处理完成

### 邮件内容验证失败

**问题**：如果邮件内容验证失败，测试可能会失败。

**解决方法**：
- 检查邮件解析逻辑
- 检查MIME处理是否正确
- 检查编码/解码过程是否正确

## 手动测试步骤

如果自动测试失败，您可以按照以下步骤手动测试系统：

### 1. 启动SMTP服务器

```bash
python -m server.authenticated_smtp_server --host localhost --port 465 --ssl
```

### 2. 启动POP3服务器

```bash
python -m server.pop3_server --host localhost --port 995 --ssl
```

### 3. 发送测试邮件

```bash
python -m client.smtp_cli --host localhost --port 465 --username testuser --password testpass --from testuser@example.com --to testuser@example.com --subject "测试邮件" --text "这是一封测试邮件" --ssl
```

### 4. 接收测试邮件

```bash
python -m client.pop3_cli --host localhost --port 995 --username testuser --password testpass --retrieve-all --ssl
```

## 测试结果解释

### 成功

如果测试成功，您将看到以下输出：

```
INFO - 测试成功: 邮件系统工作正常
```

这表示整个邮件系统工作正常，包括：
- SMTP服务器能够接收邮件
- POP3服务器能够提供邮件
- 数据库能够正确存储和检索邮件
- 客户端能够正确发送和接收邮件

### 失败

如果测试失败，您将看到详细的错误信息，例如：

```
ERROR - 测试失败: 无法发送测试邮件
```

或

```
ERROR - 测试失败: 无法接收测试邮件
```

或

```
ERROR - 测试失败: 邮件内容验证失败
```

请根据错误信息和日志输出定位问题，并参考上面的"常见问题及解决方法"部分。

## 日志文件

测试过程中的详细日志会保存在 `logs/verify_email_system.log` 文件中，您可以查看此文件获取更多调试信息。

## 注意事项

- 测试前请确保已安装所有依赖包（`pip install -r requirements.txt`）
- 测试前请确保已初始化项目（`python init_project.py`）
- 测试过程中可能会创建临时文件和数据库记录，测试完成后会自动清理
- 如果测试过程中意外中断，可能需要手动停止服务器进程
