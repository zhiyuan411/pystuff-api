# pystuff-api

Python实现的实用API集合，包含代理服务、IP检测、名单管理等实用功能。

## 项目概述

这是一个基于Flask框架开发的API服务集合，主要功能包括：
- 代理服务（支持GET/POST请求）
- IPv4/IPv6地址检测
- 白名单/黑名单管理
- 基础API测试端点

项目已包含完整的Gunicorn配置和Supervisor管理脚本，适合直接部署到生产环境。

## 文件结构说明

```
.
├── gunicorn.conf.py       # Gunicorn主配置文件（绑定127.0.0.1:8080）
├── gunicorn.ini           # Supervisor配置文件（请根据实际情况配置）
├── restart_gunicorn.sh    # Supervisor服务重启脚本
├── start_gunicorn_local_test.sh  # 本地测试启动脚本
└── test.py                # Flask主应用，包含所有API实现
```

## 核心功能API

### 1. 代理服务 - `/proxy.do`
支持GET/POST请求代理，支持多种参数格式：
- 参数格式：`base64url`, `base64`, `url`
- 可选参数：
  - `origin`: 设置Origin头
  - `referer`: 设置Referer头
  - `user_ua=1`: 使用客户端UA
  - `debug`: 启用调试模式

### 2. IP检测服务
- IPv4检测：`/ipv4.do` - 返回客户端IPv4地址
- IPv6检测：`/ipv6.do` - 返回客户端IPv6地址或状态信息

### 3. 名单管理 - `/add.do`
管理白名单和黑名单：
- 添加白名单：参数 `w`, `white` 或 `whitelist`
- 添加黑名单：参数 `b`, `black` 或 `blacklist`

**注意**：默认文件路径为 `/home/ecs-user/tvbox-random-sites/`，部署时需修改为实际路径

## 安装与部署

### 前置要求
- Python 3.7+
- Flask (`pip install flask`)
- Gunicorn (`pip install gunicorn`)
- Requests (`pip install requests`)
- Supervisor (系统服务管理)

### 配置步骤

1. **修改配置文件**
   ```python
   # gunicorn.conf.py
   bind = "127.0.0.1:8080"  # 部署时改为实际IP和端口
   workers = 4              # 根据CPU核心数调整
   accesslog = "/var/log/gunicorn-app-access.log"
   errorlog = "/var/log/gunicorn-app-error.log"
   ```

2. **配置Supervisor**
   ```ini
   ; gunicorn.ini (示例)
   [program:gunicorn]
   command=/path/to/gunicorn -c gunicorn.conf.py test:app
   directory=/path/to/project
   user=youruser
   autostart=true
   autorestart=true
   ```

3. **设置名单存储路径**
   ```python
   # test.py 中修改以下路径
   whitelist_path = '/your/actual/path/whitelist.txt'
   blacklist_path = '/your/actual/path/blacklist.txt'
   ```

### 启动服务

```bash
# 首次启动
chmod +x restart_gunicorn.sh
./restart_gunicorn.sh

# 重启服务
./restart_gunicorn.sh

# 本地测试
chmod +x start_gunicorn_local_test.sh
./start_gunicorn_local_test.sh
```

## 使用示例

### 代理请求
```bash
# 基本代理
curl "http://yourserver/proxy.do?url=https://example.com"

# 带Origin头的代理
curl "http://yourserver/proxy.do?url=https://api.example.com&origin=https://yourdomain.com"

# Base64编码的URL
curl "http://yourserver/proxy.do?base64=$(echo -n "https://example.com" | base64)"
```

### IP检测
```bash
# IPv4检测
curl http://yourserver/ipv4.do

# IPv6检测
curl http://yourserver/ipv6.do
```

### 名单管理
```bash
# 添加白名单
curl "http://yourserver/add.do?white=https://example.com"

# 添加黑名单
curl "http://yourserver/add.do?black=https://malicious.com"
```

## 安全说明

1. **代理安全限制**：
   - 禁止代理到本地服务 (localhost/127.0.0.1)
   - 禁止代理到私有网络地址 (10.x, 172.16.x, 192.168.x)
   - 添加X-Forwarded-For和Via头部标识

2. **密钥配置**：
   ```python
   # test.py中修改为强密钥
   app.config['SECRET_KEY'] = 'your-strong-secret-key-here'
   ```

3. **日志监控**：
   - 定期检查 `/var/log/gunicorn-app-*.log`
   - 监控异常请求模式

## 贡献指南

欢迎提交Pull Request或提出Issue。请确保：
1. 代码符合PEP8规范
2. 包含必要的测试
3. 更新相关文档
4. 安全相关修改需提供详细说明

## 许可证

本项目采用MIT许可证 - 详情请查看LICENSE文件。
