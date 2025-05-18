# 邮件客户端示例脚本

本目录包含了邮件客户端的示例脚本，用于演示如何使用邮件客户端的各项功能。

## 示例脚本列表

### 发送邮件

1. **send_text_email.py** - 发送纯文本邮件
   ```bash
   python examples/send_text_email.py
   ```
   
   此脚本演示如何发送一封简单的纯文本邮件。运行脚本后，按照提示输入邮箱账号信息和收件人地址。

2. **send_html_email.py** - 发送HTML格式邮件
   ```bash
   python examples/send_html_email.py
   ```
   
   此脚本演示如何发送一封HTML格式的邮件，包含格式化文本、列表、表格和链接等HTML元素。

3. **send_email_with_attachment.py** - 发送带附件的邮件
   ```bash
   python examples/send_email_with_attachment.py
   ```
   
   此脚本演示如何发送一封带附件的邮件。运行脚本后，按照提示输入邮箱账号信息、收件人地址和附件路径。

### 接收邮件

1. **receive_emails.py** - 接收邮件
   ```bash
   python examples/receive_emails.py
   ```
   
   此脚本演示如何从邮箱中接收邮件。运行脚本后，按照提示输入邮箱账号信息和要下载的邮件数量。

### 管理邮件

1. **search_emails.py** - 搜索邮件
   ```bash
   python examples/search_emails.py "搜索关键词"
   ```
   
   此脚本演示如何搜索邮件。可以使用以下选项：
   
   ```bash
   # 只搜索主题和发件人
   python examples/search_emails.py "搜索关键词" --fields subject,sender
   
   # 搜索邮件正文内容
   python examples/search_emails.py "搜索关键词" --content
   
   # 只搜索已发送邮件
   python examples/search_emails.py "搜索关键词" --sent-only
   
   # 只搜索已接收邮件
   python examples/search_emails.py "搜索关键词" --received-only
   
   # 包含已删除邮件
   python examples/search_emails.py "搜索关键词" --include-deleted
   
   # 限制结果数量
   python examples/search_emails.py "搜索关键词" --limit 10
   ```

## 使用说明

### 准备工作

在运行示例脚本之前，请确保：

1. 已安装所有必要的依赖项
2. 已配置邮箱账号信息（或准备好在运行脚本时输入）
3. 对于发送邮件测试，确保你的邮箱服务提供商允许第三方应用访问

### 运行脚本

所有示例脚本都可以直接运行：

```bash
python examples/脚本名称.py [参数]
```

大多数脚本会在运行时提示输入必要的信息，如邮箱账号、密码/授权码和收件人地址等。

### 注意事项

1. **密码安全**：示例脚本中使用明文输入密码，仅用于演示目的。在实际应用中，应该使用更安全的方式存储和获取密码。

2. **QQ邮箱用户**：如果使用QQ邮箱，请使用授权码而不是登录密码。你可以在QQ邮箱设置中获取授权码。

3. **附件处理**：发送大型附件时可能会遇到限制，请注意邮件服务提供商的附件大小限制。

4. **错误处理**：示例脚本包含基本的错误处理，但在实际应用中，应该添加更完善的错误处理机制。

## 自定义示例

你可以基于这些示例脚本创建自己的脚本，以满足特定需求。例如：

- 批量发送邮件
- 定期检查新邮件
- 自动回复邮件
- 邮件归档和备份

只需导入相应的模块，并按照示例中的模式使用即可。
