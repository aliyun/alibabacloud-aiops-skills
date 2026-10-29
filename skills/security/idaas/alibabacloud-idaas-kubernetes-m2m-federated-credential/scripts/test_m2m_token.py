#!/usr/bin/env python3
"""用 K8s ServiceAccount OIDC Token 请求 IDaaS Token 端点，验证能否换出 M2M Token。

用法: test_m2m_token.py <instance_endpoint> <client_id> <cred_name> <scope> <token_file>
  instance_endpoint: 实例 DefaultEndpoint（如 rz8w3xcn.aliyunidaas.com），不带 https://
  client_id:         M2M Client 应用 ID (app_xxx)
  cred_name:         应用联邦凭证名称（application_federated_credential_name）
  scope:             <ResourceServer标识>|<ScopeValue>
                     PAM 闭环固定: urn:cloud:idaas:pam|cloud_account_role:obtain_access_credential
                     ⚠️ 自定义 RS 标识斜杠数量以实际注册为准，勿"规范化"；.all 为通配
  token_file:        SA JWT Token 文件（原文直传，仅去除首尾空白；与 PKCS#7 不同，无需 PEM/归一化）

输出: HTTP 响应（含 access_token 时自动脱敏：token 值仅保留前 12 字符+长度；
     错误响应不含敏感物，原样输出便于排障）；成功时附 ---TOKEN_SUMMARY---（JWT 解码摘要）
     末行 TOKEN_OK=yes|no 供 Agent 解析

⚠️ 脱敏必须在脚本 stdout 层完成：stdout 会原样进入 Agent 会话上下文/transcript/遥测，
   完整 Bearer Token 一旦打印即视为泄露（TTL 内可直接调 PAM 换 STS）。
"""
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

ASSERTION_TYPE = "urn:cloud:idaas:params:oauth:client-assertion-type:id-token-bearer"
TOKEN_PREFIX_LEN = 12
SENSITIVE_FIELDS = ("access_token", "refresh_token", "id_token")


def redact_body(body: str) -> str:
    """成功响应脱敏后输出；错误响应（无 token 字段）原样输出保留排障信息"""
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return body.strip()
    if not isinstance(d, dict):
        return body.strip()
    hit = False
    for k in SENSITIVE_FIELDS:
        v = d.get(k)
        if isinstance(v, str) and v:
            d[k] = f"{v[:TOKEN_PREFIX_LEN]}...(redacted,共{len(v)}字符)"
            hit = True
    if not hit:
        return body.strip()
    return json.dumps(d, ensure_ascii=False, indent=2)


def load_assertion(path: str) -> str:
    p = Path(path)
    if not p.is_file():
        sys.exit(f"ERROR: Token 文件不存在: {path}")
    tok = p.read_text().strip()
    if not tok:
        sys.exit("ERROR: Token 文件内容为空")
    if tok.count(".") != 2:
        print("WARN: 内容不像 JWT（应为 header.payload.signature 三段），仍将原样提交",
              file=sys.stderr)
    return tok


def post_token(endpoint: str, form: dict, assertion: str, insecure: bool):
    args = [
        "curl", "-sS", "--request", "POST",
        "--url", f"https://{endpoint}/api/v2/iauths_system/oauth2/token",
        "--header", "Content-Type: application/x-www-form-urlencoded",
        "--data-urlencode", "grant_type=client_credentials",
        "--data-urlencode", f"client_id={form['client_id']}",
        "--data-urlencode", f"client_assertion_type={ASSERTION_TYPE}",
        "--data-urlencode", f"client_assertion={assertion}",
        "--data-urlencode", f"scope={form['scope']}",
        "--data-urlencode",
        f"application_federated_credential_name={form['cred_name']}",
        "-w", "\nHTTP_STATUS=%{http_code}",
    ]
    if insecure:
        args.insert(1, "-k")
    p = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return (p.stdout or "") + (p.stderr or "")


def summarize(body: str) -> None:
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return
    if "access_token" not in d:
        return
    parts = d["access_token"].split(".")
    if len(parts) < 2:
        return
    pad = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    try:
        pl = json.loads(pad(parts[1]))
    except Exception:
        return
    fmt = lambda ts: time.strftime("%F %T", time.localtime(ts))
    tok = d["access_token"]
    print("---TOKEN_SUMMARY---")
    print("access_token:", f"{tok[:TOKEN_PREFIX_LEN]}...(redacted,共{len(tok)}字符)")
    print("sub:", pl.get("sub"), "| aud:", pl.get("aud"))
    print("scope:", pl.get("scope"))
    print("有效期:", fmt(pl.get("iat", 0)), "→", fmt(pl.get("exp", 0)))


def main() -> None:
    if len(sys.argv) < 6:
        sys.exit("用法: test_m2m_token.py <endpoint> <client_id> <cred_name> "
                 "<scope> <token_file>")
    endpoint, client_id, cred_name, scope, tok_file = sys.argv[1:6]
    assertion = load_assertion(tok_file)
    form = {"client_id": client_id, "cred_name": cred_name, "scope": scope}

    resp = post_token(endpoint, form, assertion, insecure=False)
    if "HTTP_STATUS=000" in resp:
        # 连接层失败（多为代理环境 SSL 校验失败）→ 降级 -k 重试一次
        first_err = resp.strip().splitlines()[0] if resp.strip() else "无错误文本"
        print(f"WARN: 连接/SSL 失败（代理环境常见），降级 -k 重试。首次错误: {first_err}",
              file=sys.stderr)
        resp = post_token(endpoint, form, assertion, insecure=True)

    body = resp.rsplit("HTTP_STATUS=", 1)[0]
    status = resp.rsplit("HTTP_STATUS=", 1)[1].strip() if "HTTP_STATUS=" in resp else "?"
    print(redact_body(body))
    print(f"HTTP_STATUS={status}")
    summarize(body)
    print(f"TOKEN_OK={'yes' if status == '200' else 'no'}")


if __name__ == "__main__":
    main()
