#! env python
# -*- coding: utf-8 -*-
 
from flask import Flask, request, session, Response
from urllib.parse import urlparse, unquote
import re
import base64
import requests
 
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.debug = True
 
 
@app.route('/')
def hello_world():
    return '<h1 style="color: green;">你好，flask!</h1>'

@app.route('/proxy.do', methods=['GET', 'POST'])
def proxy_request():
    # 不区分大小写提取参数
    args_lower = {k.lower(): v for k, v in request.args.items()}
    raw_url = None

    # 按优先级顺序提取参数
    if 'base64url' in args_lower:
        try:
            raw_url = base64.urlsafe_b64decode(args_lower['base64url']).decode('utf-8')
        except Exception as e:
            return f"Base64URL解码失败: {str(e)}", 400

    elif 'base64' in args_lower:
        try:
            # 先URL解码再Base64解码
            decoded_str = unquote(args_lower['base64'])
            raw_url = base64.b64decode(decoded_str).decode('utf-8')
        except Exception as e:
            return f"Base64解码失败: {str(e)}", 400

    elif 'url' in args_lower:
        # 直接URL解码
        raw_url = unquote(args_lower['url'])

    else:
        return "缺少必要参数: base64url, base64 或 url", 400

    # 获取新功能参数
    origin = args_lower.get('origin')
    referer = args_lower.get('referer')
    user_ua = args_lower.get('user_ua') == '1'  # 检查是否设置为1
    debug_mode = 'debug' in args_lower  # 检查是否存在debug参数

    # === 安全验证 ===
    # 验证并补全URL协议头
    if not raw_url.startswith(('http://', 'https://')):
        raw_url = 'http://' + raw_url

    # 解析URL检查是否存在自我循环
    parsed_url = urlparse(raw_url)
    server_host = request.host.split(':')[0]  # 获取当前服务器主机名

    # 禁止代理到自身服务（包括localhost、回环地址和当前主机）
    if (
        parsed_url.hostname in ['localhost', '127.0.0.1', '::1', server_host]
    ):
        return "禁止代理到自身服务", 403

    # 禁止访问私有地址段
    if parsed_url.hostname and parsed_url.hostname.startswith(('10.', '172.16.', '192.168.')):
        return "禁止代理到私有网络地址", 403

    try:
        # 根据user_ua参数决定是否使用用户的UA
        if user_ua:
            user_agent = request.headers.get('User-Agent', 'PyProxy/1.0')
        else:
            user_agent = 'PyProxy/1.0'

        # 获取客户端真实 IP（考虑代理情况）
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in client_ip:
            # 处理多个 IP 的情况（如经过多层代理）
            client_ip = client_ip.split(',')[0].strip()

        # 构建请求头
        headers = {
            'User-Agent': user_agent,
            'X-Forwarded-For': client_ip,
            'Via': 'PyProxy/1.0'  # 添加代理标识
        }

        # 添加origin头（如果指定）
        if origin:
            headers['Origin'] = origin

        # 添加referer头（如果指定）
        if referer:
            headers['Referer'] = referer

        # 确定请求方法和数据
        request_method = request.method
        data = None
        json_data = None

        # 根据请求类型设置相应参数
        if request_method == 'POST':
            content_type = request.headers.get('Content-Type', '').lower()

            # JSON类型POST请求
            if 'application/json' in content_type:
                json_data = request.get_json()
            # 表单类型POST请求
            elif 'application/x-www-form-urlencoded' in content_type:
                data = request.form
            # 其他类型POST请求，默认转为GET
            else:
                request_method = 'GET'
        # GET请求无需处理数据

        # 发送请求
        if request_method == 'GET':
            resp = requests.get(
                raw_url,
                allow_redirects=False,  # 禁用自动重定向
                timeout=10,             # 超时设置
                headers=headers
            )
        else:  # POST请求
            resp = requests.post(
                raw_url,
                data=data,
                json=json_data,
                allow_redirects=False,
                timeout=10,
                headers=headers
            )

        # 处理调试模式
        if debug_mode:
            # 构建调试信息
            debug_output = [
                f"代理请求URL: {raw_url}",
                f"请求方法: {request_method}",
                f"响应状态码: {resp.status_code}",
                "\n响应头:"
            ]
            for k, v in resp.headers.items():
                debug_output.append(f"  {k}: {v}")
            debug_output.append("\n响应内容:")
            debug_output.append(resp.text)
            
            # 返回纯文本调试信息
            return Response("\n".join(debug_output), mimetype='text/plain')

        # 非调试模式：处理并返回代理响应
        # 排除代理自身的content-type和CORS相关头
        excluded_headers = ['content-encoding', 'content-length', 'connection', 'server']
        # 定义需要去除的CORS相关头
        cors_headers = [
            'access-control-allow-origin',
            'access-control-allow-methods',
            'access-control-allow-headers',
            'access-control-allow-credentials',
            'access-control-max-age',
            'access-control-expose-headers'
        ]

        # 合并需要排除的头，并转换为小写便于比较
        all_excluded = excluded_headers + cors_headers
        all_excluded_lower = [h.lower() for h in all_excluded]

        # 过滤响应头，排除指定的头
        response_headers = {
            k: v for k, v in resp.headers.items()
            if k.lower() not in all_excluded_lower
        }

        return Response(
            resp.content,
            status=resp.status_code,
            headers=response_headers
        )

    except requests.exceptions.RequestException as e:
        if debug_mode:
            # 调试模式下详细显示错误信息
            error_text = f"代理请求失败: {str(e)}\n"
            error_text += f"请求URL: {raw_url}\n"
            error_text += f"请求方法: {request_method}"
            return Response(error_text, mimetype='text/plain', status=502)
        else:
            return f"代理请求失败: {str(e)}", 502


@app.route('/ipv4.do', methods=['GET'])
def handle_ipv4():
    # 正确获取X-Forwarded-For头
    x_forwarded_for = request.headers.get('X-Forwarded-For')  # 使用标准格式

    # 处理可能包含多个IP的情况
    if x_forwarded_for:
        # 分割并取第一个IP，去除空格
        original_ip = x_forwarded_for.split(',')[0].strip()
    else:
        # 如果头不存在，尝试从远程地址获取
        original_ip = request.remote_addr or None

    # 更健壮的IPv4正则表达式
    ipv4_pattern = re.compile(
        r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )

    # 判断逻辑
    if original_ip and ipv4_pattern.match(original_ip):
        return original_ip, 200
    else:
        # 不存在IPv6的域名解析，肯定是其他情况
        return "No_Valid_IP", 200

@app.route('/ipv6.do', methods=['GET'])
def handle_ipv6():
    # 正确获取X-Forwarded-For头
    x_forwarded_for = request.headers.get('X-Forwarded-For')  # 使用标准格式
    
    # 处理可能包含多个IP的情况
    if x_forwarded_for:
        # 分割并取第一个IP，去除空格
        original_ip = x_forwarded_for.split(',')[0].strip()
    else:
        # 如果头不存在，尝试从远程地址获取
        original_ip = request.remote_addr or None

    # 更健壮的IPv4正则表达式
    ipv4_pattern = re.compile(
        r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )
    
    # 判断逻辑
    if original_ip and ipv4_pattern.match(original_ip):
        return "IPv6_Unavailable:Only_IPv4_"+original_ip, 200
    elif original_ip:
        # 只要不是IPv4就认为是IPv6
        return original_ip, 200
    else:
        return "IPv6_Unavailable:No_Valid_IP", 200

@app.route('/add.do', methods=['GET'])
def add_to_list():
    # 定义白名单和黑名单文件路径
    whitelist_path = '/home/ecs-user/tvbox-random-sites/whitelist.txt'
    blacklist_path = '/home/ecs-user/tvbox-random-sites/blacklist.txt'
    
    # 初始化返回消息
    response_messages = []

    for param, value in request.args.items():
        if not value:
            return '<h1 style="color: red;">缺少必要参数。</h1>', 400

        try:

            # 检查值是否已经存在于相应的文件中
            file_path = None
            message_prefix = ""

            if param in ['w', 'white', 'whitelist']:
                file_path = whitelist_path
                message_prefix = "白名单"
            elif param in ['b', 'black', 'blacklist']:
                file_path = blacklist_path
                message_prefix = "黑名单"
            else:
                return f'<h1 style="color: red;">无效参数: {param}</h1>', 400

            # 检查值是否已经存在
            value_exists = False
            try:
                with open(file_path, 'r') as file:
                    value_exists = any(line.strip() == value for line in file)
            except FileNotFoundError:
                pass  # 文件不存在时，默认值不存在

            if value_exists:
                response_messages.append(f'<h1 style="color: green;">"{value}" 已经存在于 {message_prefix} 中。</h1>')
            else:
                with open(file_path, 'a') as f:
                    f.write(f"{value}\n")
                response_messages.append(f'<h1 style="color: green;">已添加 "{value}" 到 {message_prefix}。</h1>')

        except Exception as e:
            return f'<h1 style="color: red;">处理参数 "{param}" 时发生错误: {e}</h1>', 500

    # 如果没有任何有效的参数被处理，则返回错误信息
    if not response_messages:
        return '<h1 style="color: red;">没有提供有效参数。</h1>', 400

    # 返回所有成功处理的消息
    return "\n".join(response_messages), 200

 
 
@app.route('/user/<username>')
def show_user_profile(username):
    return 'User %s' % username
 
 
@app.route('/test.do', methods=['GET', 'POST'])
def test():
    # 访问路径
    print(request.path)
    # 方法（GET或POST）
    print(request.method)
    # GET参数
    print(request.args)
    # POST参数
    print(request.form)
    # JSON类型参数
    print(request.json)
    # File内容（对应前端表单name属性为"the_file"）
    if 'the_file' in request.files:
        f = request.files['the_file']
        print(f.filename)
    # Cookies
    print(request.cookies)


    # 返回html模板
    # return render_template('hello.html', name=name)
    # 返回时设定header等
    # resp = make_response(render_template('hello.html'), name=name)
    # resp.set_cookie('username', 'the username')
    # resp.headers['X-Something'] = 'A value'
    # return resp


    # 使用session
    session['login'] = 'admin'
    print(session['login'])
    session.pop('login', None)

    # 刷新缓冲区，打印所有日志
    print("\n", flush=True)

    return 'test' 
 
if __name__ == '__main__':
    # app.secret_key = 'your-secret-key-here'
    app.run()
