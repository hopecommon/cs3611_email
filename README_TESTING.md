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

## 手动测试步骤

如果自动测试失败，您可以按照以下步骤手动测试系统：

同时启动：
```bash
python examples/example_run_both_servers.py
```

### 1. 启动SMTP服务器

```bash
python -m server.smtp_server --host localhost --port 465
```

### 2. 启动POP3服务器

```bash
python -m server.pop3_server --host localhost --port 995
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
