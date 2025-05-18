# 邮件客户端测试指南

本文档提供了如何测试邮件客户端各项功能的详细说明。

## 测试准备

在运行测试之前，请确保：

1. 已安装所有必要的依赖项
2. 已配置测试账号信息（在 `tests/test_config.py` 中）
3. 对于发送邮件测试，确保你的邮箱服务提供商允许第三方应用访问

### 配置测试账号

编辑 `tests/test_config.py` 文件，填入你的测试账号信息：

```python
TEST_ACCOUNT = {
    "smtp_host": "smtp.qq.com",
    "smtp_port": 25,
    "smtp_ssl": True,
    "pop3_host": "pop.qq.com",
    "pop3_port": 110,
    "pop3_ssl": True,
    "username": "your_email@qq.com",  # 替换为你的QQ邮箱
    "password": "your_password",      # 替换为你的授权码
    "recipient": "recipient@example.com"  # 替换为接收测试邮件的邮箱
}
```

**注意**：对于QQ邮箱，`password` 应该是授权码而不是登录密码。你可以在QQ邮箱设置中获取授权码。

## 运行测试

### 运行所有测试

使用以下命令运行所有测试：

```bash
python run_all_tests.py --modules all --verbose
```

### 运行特定测试

运行特定测试模块：

```bash
# 运行认证测试
python run_all_tests.py --modules auth --verbose

# 运行SMTP发送测试
python run_all_tests.py --modules smtp --verbose

# 运行POP3接收测试
python run_all_tests.py --modules pop3 --verbose

# 运行存储测试
python run_all_tests.py --modules storage --verbose

# 运行多个测试模块
python run_all_tests.py --modules auth smtp --verbose
```

### 直接运行单个测试文件

你也可以直接运行单个测试文件：

```bash
# 运行基本认证测试
python tests/test_auth_basic.py

# 运行全面认证测试
python tests/test_auth_comprehensive.py

# 运行SMTP发送测试
python tests/test_smtp_send.py

# 运行POP3接收测试
python tests/test_pop3_receive.py

# 运行存储测试
python tests/test_storage.py
```

## 测试内容说明

### 1. 认证功能测试

- `test_auth_basic.py`：测试基本的认证功能
- `test_auth_comprehensive.py`：全面测试各种认证方法和错误处理

### 2. 邮件发送功能测试

- `test_smtp_send.py`：测试发送纯文本邮件、HTML邮件、带附件邮件和多收件人邮件

### 3. 邮件接收功能测试

- `test_pop3_receive.py`：测试连接邮箱、获取邮件列表、下载邮件内容和附件

### 4. 本地存储功能测试

- `test_storage.py`：测试将邮件保存为.eml文件、保存邮件元数据到数据库、从数据库检索邮件

## 测试结果解读

测试成功时，你将看到类似以下输出：

```
Ran X tests in Y.ZZZs

OK
```

如果测试失败，你将看到详细的错误信息，包括：

- 失败的测试用例名称
- 失败的原因
- 相关的堆栈跟踪

## 常见问题解决

### 认证失败

- 检查你的账号信息是否正确
- 对于QQ邮箱，确保使用的是授权码而不是登录密码
- 确保你的邮箱服务提供商允许第三方应用访问

### 连接超时

- 检查网络连接
- 确认服务器地址和端口是否正确
- 检查防火墙设置

### 发送邮件失败

- 检查发件人地址是否与认证账号一致
- 确认邮件格式是否正确
- 查看是否达到发送频率限制

### 接收邮件失败

- 确认邮箱中有邮件
- 检查POP3服务是否已启用
- 验证认证信息是否正确
