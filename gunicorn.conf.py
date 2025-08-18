import os

bind = "127.0.0.1:8080"  # 监听的 IP 和端口
workers = 2  # 根据实际情况调整工作进程数
worker_class = "sync"  # 或选择其他 worker 类型，如 "gevent", "eventlet", "tornado"

capture_output = True  # 捕获 stdout/stderr 输出
loglevel = "info"     # 设置日志级别为 debug，能看到所有打印
# 指定日志文件路径
accesslog = "/var/log/gunicorn-app-access.log"
errorlog = "/var/log/gunicorn-app-error.log"

# 其他可能需要的配置项，如 timeout、keepalive、preload_app 等
# ...
