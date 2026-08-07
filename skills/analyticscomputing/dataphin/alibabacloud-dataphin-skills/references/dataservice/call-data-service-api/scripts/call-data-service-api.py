#!/usr/bin/env python3
"""call-data-service-api.py — Dataphin 数据服务 API 调用（AppKey/AppSecret + HMAC-SHA256）。

【零依赖】仅使用 Python 标准库，无需安装官方 SDK，也无需 pip install requests。
签名串构造与官方 Python SDK（dataphin-sdk-core-python v5.5.0）逐字节一致：

  POST\n{accept}\n{content-md5}\n{content-type}\n{date}\n
  {按字典序的 x-ca-* 头，每行 "k:v\\n"}
  {path 原样，含 query string}

要点：JSON body **不参与**签名（content-md5 为空，仅 octet-stream 才计算）；
path 不做 query 归一化/排序，签名与实际请求行必须完全一致。

凭证与环境（环境变量，均不打印）：
  DATAPHIN_APP_KEY       应用 AppKey（来自 manage-app-and-bindauth）
  DATAPHIN_APP_SECRET    应用 AppSecret
  DATAPHIN_GATEWAY_HOST  数据服务网关地址（控制台 数据服务 > 服务管理 > 网络配置）
  SKILL_SESSION_ID       可观测 session-id（可选，写入 user-agent）

用法：
  # 同步调用（LIST/GET/CREATE/UPDATE/DELETE）
  python3 call-data-service-api.py call --api-id 10083 --method LIST \\
      --params '{"conditions":{},"returnFields":[],"pageStart":0,"pageSize":10,"keepColumnCase":true}'
  # 异步调用（自动轮询 jobId → 合并分页 → 关闭任务）
  python3 call-data-service-api.py async-call --api-id 10083 --method LIST --params-file q.json
  # 流式调用（SSE，逐帧输出 JSON）
  python3 call-data-service-api.py sse --api-id 10083 --method GET --params '{"conditions":{}}'

选项：
  --stage RELEASE|PRE    环境标识（RELEASE=生产，PRE=开发），默认 RELEASE
  --env PROD|PRE         数据环境，默认 PROD
  --scheme HTTP|HTTPS    协议，默认 HTTP（内置网关仅支持 HTTP）
  --port                 端口，默认 HTTP=80 / HTTPS=443
  --ignore-ssl           HTTPS 且证书不受信（私有化部署自签 CA）时跳过校验
  --quiet                仅输出结果 JSON
"""
import argparse
import base64
import hashlib
import hmac
import http.client
import json
import os
import ssl
import sys
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse

SUCCESS_CODE = 'DPN-OLTP-COMMON-000'
# ApiConfig.method → 网关路径动词。methodType 由 API 发布时的操作类型决定，
# 猜错会返回 403 "The request api path /xxx/{apiId} not bind app {appKey}"
METHOD_VERBS = {
    'LIST': 'list', 'GET': 'get',
    'CREATE': 'create', 'UPDATE': 'update', 'DELETE': 'delete',
}
DEFAULT_FETCH_SIZE = 1000
JOB_STATUS = {
    1: 'RUNNING', 2: 'SUCCESS', 3: 'FAILED', 4: 'CANCELLED',
    5: 'EXPIRED', 6: 'CLOSED_BY_SUCCESS', 7: 'CLOSED_BY_FAILED',
}


def _log(msg, quiet):
    if not quiet:
        sys.stderr.write(msg + "\n")


class Gateway:
    """数据服务网关客户端（同步 / 异步 / SSE）。"""

    def __init__(self, host, app_key, app_secret, stage='RELEASE', env='PROD',
                 scheme='HTTP', port=None, ignore_ssl=False, timeout=30, quiet=False):
        self.host, host_port = self._split_host(host)
        self.app_key = str(app_key)
        self.app_secret = app_secret
        self.stage = stage
        self.env = env
        self.scheme = scheme.upper()
        self.port = port or host_port or (443 if self.scheme == 'HTTPS' else 80)
        self.ignore_ssl = ignore_ssl
        self.timeout = timeout
        self.quiet = quiet

    @staticmethod
    def _split_host(host):
        """容忍 host 写成 http://h、h:80 等形式，拆出纯域名与端口。"""
        parsed = urlparse(host if '://' in host else '//' + host)
        return parsed.hostname, parsed.port

    def _headers(self, path, accept='application/json'):
        """构造并签名请求头（算法见模块 docstring）。"""
        # user-agent 承载可观测标记：**不要**用 X-Ca-User-Agent，
        # x-ca-* 前缀会被纳入签名串，易触发 SignatureDoesNotMatch
        ua = 'AlibabaCloud-Agent-Skills/call-data-service-api'
        session_id = os.environ.get('SKILL_SESSION_ID', '')
        headers = {
            'accept': accept,
            'content-type': 'application/json',
            'date': str(datetime.now()),
            'user-agent': f'{ua}/{session_id}' if session_id else ua,
            'x-ca-key': self.app_key,
            'x-ca-nonce': str(uuid.uuid4()),
            'x-ca-signature-method': 'HmacSHA256',
            'x-ca-stage': self.stage,
            'x-ca-timestamp': str(int(time.time() * 1000)),
        }
        ca_keys = sorted(k for k in headers if k.startswith('x-ca-'))
        string_to_sign = (
            'POST\n'
            + headers['accept'] + '\n'
            + '\n'                        # content-md5：JSON body 不参与签名
            + headers['content-type'] + '\n'
            + headers['date'] + '\n'
            + ''.join(f'{k}:{headers[k]}\n' for k in ca_keys)
            + path
        )
        headers['x-ca-signature-headers'] = ','.join(ca_keys)
        headers['x-ca-signature'] = base64.b64encode(hmac.new(
            self.app_secret.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256
        ).digest()).decode('utf-8')
        return headers

    def _connect(self):
        if self.scheme == 'HTTPS':
            context = ssl._create_unverified_context() if self.ignore_ssl else None
            return http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout,
                                               context=context)
        return http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)

    def _post(self, path, body, accept='application/json'):
        conn = self._connect()
        try:
            conn.request('POST', path, body=json.dumps(body).encode('utf-8'),
                         headers=self._headers(path, accept))
            resp = conn.getresponse()
            text = resp.read().decode('utf-8')
            if resp.status != 200:
                raise RuntimeError(f'HTTP {resp.status}: {text}')
            return json.loads(text)
        finally:
            conn.close()

    def api_path(self, api_id, method):
        verb = METHOD_VERBS[method.upper()]
        return f'/{verb}/{api_id}?appKey={self.app_key}&env={self.env}'

    def call(self, api_id, method, params):
        """同步调用。params 为 QueryParam（查询）或 ManipulationParam（DML）。"""
        return self._post(self.api_path(api_id, method), params)

    # --- 异步调用 ---------------------------------------------------------
    def _job_request(self, endpoint, job_id, fetch_size=DEFAULT_FETCH_SIZE):
        path = (f'{endpoint}?appKey={self.app_key}&env={self.env}'
                f'&fetchSize={fetch_size}&jobId={job_id}')
        # SDK 此处发送字面量 null；body 不参与 JSON 签名，传 {} 等效
        return self._post(path, {})

    def async_call(self, api_id, method, params, poll_interval=1.0, timeout=300,
                   max_status_retry=5):
        """异步调用：提交 → 轮询 getJobStatus → 合并 getJobResult 分页 → closeJob。"""
        resp = self.call(api_id, method, params)
        job_id = resp.get('jobId')
        if not job_id:
            return resp  # 数据量小时网关直接返回同步结果
        _log(f'[async] jobId={job_id}', self.quiet)

        deadline = time.time() + timeout
        retry = 0
        result = None
        try:
            while time.time() < deadline:
                time.sleep(poll_interval)
                status_resp = self._job_request('/getJobStatus', job_id)
                if status_resp.get('code') != SUCCESS_CODE:
                    retry += 1
                    if retry > max_status_retry:
                        raise RuntimeError(f'状态查询连续失败: {status_resp.get("message")}')
                    continue
                status = status_resp.get('result', {}).get('status')
                _log(f'[async] status={JOB_STATUS.get(status, status)}', self.quiet)
                if status == 1:
                    continue
                if status == 2:
                    result = self._collect_result(job_id)
                    break
                if status == 3:
                    log = self._job_request('/getJobExecutionLog', job_id)
                    raise RuntimeError(f'异步任务失败: {json.dumps(log, ensure_ascii=False)}')
                break  # CANCELLED / EXPIRED / CLOSED_*
            else:
                raise TimeoutError(f'异步任务超时({timeout}s)，jobId={job_id}')
        finally:
            try:
                self._job_request('/closeJob', job_id)
            except Exception as exc:                       # 关闭失败不掩盖主异常
                _log(f'[async] closeJob 失败（可忽略）: {exc}', self.quiet)
        return result if result is not None else resp

    def _collect_result(self, job_id):
        """循环拉取 getJobResult 直到空批次，合并 results。"""
        merged = None
        while True:
            batch = self._job_request('/getJobResult', job_id)
            if merged is None:
                merged = batch
                if batch.get('code') != SUCCESS_CODE:
                    return batch
                if not batch.get('results'):
                    return merged
                continue
            if batch.get('code') != SUCCESS_CODE or not batch.get('results'):
                return merged
            merged['results'].extend(batch['results'])

    # --- 流式调用 ---------------------------------------------------------
    def sse(self, api_id, method, params):
        """SSE 流式调用，逐帧 yield 解析后的 JSON。"""
        path = self.api_path(api_id, method)
        conn = self._connect()
        try:
            conn.request('POST', path, body=json.dumps(params).encode('utf-8'),
                         headers=self._headers(path, accept='text/event-stream'))
            resp = conn.getresponse()
            if resp.status != 200:
                raise RuntimeError(f'HTTP {resp.status}: {resp.read().decode("utf-8")}')
            if resp.getheader('content-type') != 'text/event-stream':
                yield json.loads(resp.read().decode('utf-8'))
                return
            buf = ''
            while True:
                line = resp.readline().decode('utf-8')
                if not line:                                # 服务端关闭
                    break
                buf += line
                if buf.endswith('\n\n'):
                    for data in [l[5:] for l in buf.splitlines() if l.startswith('data:')]:
                        if data:
                            yield json.loads(data)
                    buf = ''
        finally:
            conn.close()


def _build_gateway(args):
    app_key = os.environ.get('DATAPHIN_APP_KEY')
    app_secret = os.environ.get('DATAPHIN_APP_SECRET')
    host = os.environ.get('DATAPHIN_GATEWAY_HOST')
    if not (app_key and app_secret and host):
        sys.stderr.write(
            '缺少必要环境变量：DATAPHIN_APP_KEY / DATAPHIN_APP_SECRET / DATAPHIN_GATEWAY_HOST\n'
        )
        sys.exit(2)
    return Gateway(host=host, app_key=app_key, app_secret=app_secret, stage=args.stage,
                   env=args.env, scheme=args.scheme, port=args.port,
                   ignore_ssl=args.ignore_ssl, quiet=args.quiet)


def _load_params(args):
    if args.params_file:
        with open(args.params_file, encoding='utf-8') as fp:
            return json.load(fp)
    return json.loads(args.params) if args.params else {}


def run_call(args):
    gw = _build_gateway(args)
    params = _load_params(args)
    _log(f'[call] {args.method} apiId={args.api_id} stage={args.stage} env={args.env}', args.quiet)
    return gw.call(args.api_id, args.method, params)


def run_async_call(args):
    gw = _build_gateway(args)
    params = _load_params(args)
    _log(f'[async-call] {args.method} apiId={args.api_id}', args.quiet)
    return gw.async_call(args.api_id, args.method, params,
                         poll_interval=args.poll_interval, timeout=args.timeout)


def run_sse(args):
    gw = _build_gateway(args)
    params = _load_params(args)
    _log(f'[sse] {args.method} apiId={args.api_id}', args.quiet)
    for item in gw.sse(args.api_id, args.method, params):
        print(json.dumps(item, ensure_ascii=False))
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Dataphin 数据服务 API 调用（AppKey/AppSecret 签名，零第三方依赖）')
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--api-id', required=True, help='API 唯一标识')
    common.add_argument('--method', required=True, choices=sorted(METHOD_VERBS),
                        help='操作类型（大写）；决定网关路径动词')
    common.add_argument('--params', default=None, help='请求参数 JSON 字符串')
    common.add_argument('--params-file', default=None, help='请求参数 JSON 文件（与 --params 二选一）')
    common.add_argument('--stage', default='RELEASE', choices=['RELEASE', 'PRE'],
                        help='环境标识，默认 RELEASE')
    common.add_argument('--env', default='PROD', choices=['PROD', 'PRE'],
                        help='数据环境，默认 PROD')
    common.add_argument('--scheme', default='HTTP', choices=['HTTP', 'HTTPS'],
                        help='协议，默认 HTTP（内置网关仅支持 HTTP）')
    common.add_argument('--port', type=int, default=None, help='端口，默认 HTTP=80 / HTTPS=443')
    common.add_argument('--ignore-ssl', action='store_true', help='跳过 SSL 校验（自签 CA）')
    common.add_argument('--quiet', action='store_true', help='仅输出结果 JSON')
    sub = parser.add_subparsers(dest='command', required=True)

    p_call = sub.add_parser('call', parents=[common], help='同步调用')
    p_call.set_defaults(func=run_call)

    p_async = sub.add_parser('async-call', parents=[common], help='异步调用（自动轮询）')
    p_async.add_argument('--poll-interval', type=float, default=1.0, help='轮询间隔秒，默认 1')
    p_async.add_argument('--timeout', type=int, default=300, help='轮询超时秒，默认 300')
    p_async.set_defaults(func=run_async_call)

    p_sse = sub.add_parser('sse', parents=[common], help='流式调用（SSE）')
    p_sse.set_defaults(func=run_sse)

    args = parser.parse_args()
    try:
        body = args.func(args)
    except Exception as exc:
        sys.stderr.write(f'调用失败: {exc}\n')
        sys.exit(1)
    if body is None:
        return
    print(json.dumps(body, ensure_ascii=False, indent=2))
    if body.get('code') != SUCCESS_CODE:
        sys.exit(1)


if __name__ == '__main__':
    main()
