#!/bin/bash
APP_MODULE="test:app"  # 模块名:实例名
WORKERS=4  # 根据实际情况调整工作进程数
BIND="127.0.0.1:8080"  # Gunicorn监听的IP和端口

gunicorn ${APP_MODULE} --workers=${WORKERS} --bind=${BIND}

