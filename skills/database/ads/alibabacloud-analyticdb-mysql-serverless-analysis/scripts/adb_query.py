#!/usr/bin/env python3
"""ADB Serverless Query API 的只读命令行客户端。

This script uses only the Python standard library and has no third-party
runtime dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any


SKILL_NAME = "alibabacloud-analyticdb-mysql-serverless-analysis"
TOKEN_ENV = "ADB_ACCESS_TOKEN"
SESSION_ID_ENV = "SKILL_SESSION_ID"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
REGION_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WORKSPACE_RE = re.compile(r"^ws-[A-Za-z0-9]+$")
SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")
READ_ONLY_KEYWORDS = {"SELECT", "SHOW", "DESCRIBE", "DESC"}
FORMAT_SPECIFIC_READER_RE = re.compile(
    r"\b(?:parquet_file|csv_file|json_file)\s*\(", re.IGNORECASE
)
DIRECT_FILE_READER_RE = re.compile(r"\b(?:files|hive_files)\s*\(", re.IGNORECASE)
AGGREGATE_RE = re.compile(
    r"\b(?:count|sum|avg|min|max)\s*\(|\bgroup\s+by\b|\bselect\s+distinct\b",
    re.IGNORECASE,
)
WHERE_RE = re.compile(r"\bwhere\b", re.IGNORECASE)
LIMIT_RE = re.compile(r"\blimit\s+[1-9][0-9]*\b", re.IGNORECASE)


class ValidationError(ValueError):
    """本地输入校验失败。"""


class QueryError(RuntimeError):
    """远端请求或响应失败。"""


def endpoint_from_region(region_code: str) -> str:
    region_code = region_code.strip()
    if not REGION_RE.fullmatch(region_code):
        raise ValidationError(
            "regionCode 格式无效；只能包含小写字母、数字和连字符。"
        )
    return f"https://serverless.{region_code}.ads.aliyuncs.com"


def validate_endpoint(endpoint: str) -> str:
    value = endpoint.strip()
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValidationError("endpoint 必须是有效的 HTTPS 地址。")
    if parsed.username or parsed.password:
        raise ValidationError("endpoint 不能包含用户名或密码。")
    if parsed.query or parsed.fragment:
        raise ValidationError("endpoint 不能包含 query 或 fragment。")
    if parsed.path not in ("", "/"):
        raise ValidationError("endpoint 只能包含服务根地址，不能包含 API 路径。")
    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise ValidationError("endpoint 端口格式无效。") from exc
    port = f":{parsed_port}" if parsed_port is not None else ""
    return f"https://{parsed.hostname}{port}"


def validate_workspace_id(workspace_id: str) -> str:
    value = workspace_id.strip()
    if not WORKSPACE_RE.fullmatch(value):
        raise ValidationError("workspaceId 格式无效；应形如 ws-xxxxxxxx。")
    return value


def _mask_literals_and_comments(sql: str) -> str:
    chars = list(sql)
    masked = list(sql)
    i = 0
    state = "normal"
    while i < len(chars):
        char = chars[i]
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if state == "normal":
            if char == "'":
                masked[i] = " "
                state = "single"
            elif char == '"':
                masked[i] = " "
                state = "double"
            elif char == "-" and nxt == "-":
                masked[i] = masked[i + 1] = " "
                i += 1
                state = "line_comment"
            elif char == "/" and nxt == "*":
                masked[i] = masked[i + 1] = " "
                i += 1
                state = "block_comment"
        elif state == "single":
            masked[i] = " "
            if char == "'" and nxt == "'":
                masked[i + 1] = " "
                i += 1
            elif char == "'":
                state = "normal"
        elif state == "double":
            masked[i] = " "
            if char == '"' and nxt == '"':
                masked[i + 1] = " "
                i += 1
            elif char == '"':
                state = "normal"
        elif state == "line_comment":
            masked[i] = " "
            if char in "\r\n":
                state = "normal"
        elif state == "block_comment":
            masked[i] = " "
            if char == "*" and nxt == "/":
                masked[i + 1] = " "
                i += 1
                state = "normal"
        i += 1
    if state in {"single", "double", "block_comment"}:
        raise ValidationError("SQL 包含未闭合的字符串、标识符或块注释。")
    return "".join(masked)


def validate_sql(sql: str) -> str:
    value = sql.strip()
    if not value:
        raise ValidationError("SQL 不能为空。")
    masked = _mask_literals_and_comments(value).strip()
    if not masked:
        raise ValidationError("SQL 不能为空。")

    if masked.endswith(";"):
        statement = masked[:-1].strip()
    else:
        statement = masked
    if ";" in statement:
        raise ValidationError("只允许执行一条 SQL 语句。")

    match = re.match(r"([A-Za-z]+)", statement)
    keyword = match.group(1).upper() if match else ""
    if keyword not in READ_ONLY_KEYWORDS:
        allowed = "、".join(sorted(READ_ONLY_KEYWORDS))
        raise ValidationError(f"只允许只读 SQL，首个关键字必须是：{allowed}。")

    if FORMAT_SPECIFIC_READER_RE.search(statement):
        raise ValidationError(
            "禁止使用 parquet_file、csv_file 或 json_file；"
            "请优先检查已注册 Hive 表，否则使用自动推断的 files。"
        )

    if keyword == "SELECT" and DIRECT_FILE_READER_RE.search(statement):
        if AGGREGATE_RE.search(statement):
            if not WHERE_RE.search(statement):
                raise ValidationError(
                    "禁止通过 files 或 hive_files 执行无过滤条件的聚合；"
                    "请先检查已注册 Hive 表，或将查询限定到明确分区。"
                )
        elif not LIMIT_RE.search(statement):
            raise ValidationError(
                "通过 files 或 hive_files 直接读取 OSS 时，非聚合 SELECT 必须包含 LIMIT。"
            )
    return value


def build_query_url(endpoint: str, workspace_id: str) -> str:
    base = validate_endpoint(endpoint)
    workspace = validate_workspace_id(workspace_id)
    return f"{base}/workspace/{workspace}/v1/query"


def _redact(text: str, secret: str | None) -> str:
    if secret:
        return text.replace(secret, "***")
    return text


def build_user_agent(environ: Mapping[str, str] | None = None) -> str:
    """Build the Alibaba Cloud observability User-Agent for this session."""
    environment = os.environ if environ is None else environ
    session_id = environment.get(SESSION_ID_ENV, "")
    user_agent = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}"
    if not session_id:
        return user_agent
    if not SESSION_ID_RE.fullmatch(session_id):
        raise ValidationError(
            f"{SESSION_ID_ENV} 必须是 32 位小写十六进制字符串。"
        )
    return f"{user_agent}/{session_id}"


def resolve_access_token(
    explicit_access_token: str | None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """选择本次请求的令牌；用户显式输入优先于进程环境变量。"""
    if explicit_access_token is not None:
        if not explicit_access_token.strip():
            raise ValidationError("用户显式提供的 accessToken 不能为空。")
        return explicit_access_token

    environment = os.environ if environ is None else environ
    token = environment.get(TOKEN_ENV, "")
    if not token:
        raise ValidationError(
            f"未提供 accessToken，且环境变量 {TOKEN_ENV} 未配置；请配置后重试。"
        )
    return token


def _read_limited(response: Any) -> bytes:
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise QueryError("响应超过 10 MiB 限制；请缩小查询结果范围。")
    return body


def build_response_evidence(body: Any) -> dict[str, Any]:
    """Return stable, non-secret facts that scenario assertions can match."""
    evidence: dict[str, Any] = {"querySucceeded": False}
    if not isinstance(body, Mapping):
        return evidence

    service_code = body.get("code")
    evidence["serviceCode"] = service_code
    evidence["querySucceeded"] = service_code == 0

    data = body.get("data")
    if not isinstance(data, Mapping):
        return evidence

    columns = data.get("columns")
    rows = data.get("rows")
    if isinstance(columns, list):
        evidence["columnCount"] = len(columns)
    if isinstance(rows, list):
        evidence["rowCount"] = len(rows)
    if isinstance(data.get("hasMore"), bool):
        evidence["hasMore"] = data["hasMore"]
    return evidence


def execute_query(
    endpoint: str,
    workspace_id: str,
    sql: str,
    token: str,
    timeout: float = 60.0,
) -> dict[str, Any]:
    url = build_query_url(endpoint, workspace_id)
    statement = validate_sql(sql)
    if not token.strip():
        raise ValidationError(f"环境变量 {TOKEN_ENV} 未配置。")
    if timeout <= 0 or timeout > 300:
        raise ValidationError("timeout 必须大于 0 且不超过 300 秒。")

    payload = json.dumps({"sql": statement}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": build_user_agent(),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = _read_limited(response)
            status = getattr(response, "status", 200)
            request_id = response.headers.get("x-acs-request-id")
    except urllib.error.HTTPError as exc:
        raw = _read_limited(exc)
        detail = _redact(raw.decode("utf-8", errors="replace"), token)
        raise QueryError(f"HTTP {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise QueryError(_redact(f"网络请求失败：{exc.reason}", token)) from None

    text = _redact(raw.decode("utf-8", errors="replace"), token)
    try:
        body: Any = json.loads(text)
    except json.JSONDecodeError:
        body = text
    return {
        "httpStatus": status,
        "requestId": request_id,
        "evidence": build_response_evidence(body),
        "body": body,
    }


def _read_sql(sql_file: str | None) -> str:
    if sql_file:
        with open(sql_file, "r", encoding="utf-8") as handle:
            return handle.read()
    if sys.stdin.isatty():
        raise ValidationError("请通过标准输入或 --sql-file 提供 SQL。")
    return sys.stdin.read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="通过 ADB Serverless Query API 执行单条只读 Presto SQL。"
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--region-code", help="用于拼接 Serverless 公网 endpoint")
    target.add_argument("--endpoint", help="用户确认的 Serverless HTTPS endpoint")
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--sql-file", help="SQL 文件；未提供时从标准输入读取")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅校验并打印脱敏请求，不读取 token、不访问网络",
    )
    return parser


def main(
    argv: list[str] | None = None,
    access_token: str | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    selected_token: str | None = None
    try:
        endpoint = (
            endpoint_from_region(args.region_code)
            if args.region_code
            else validate_endpoint(args.endpoint)
        )
        workspace_id = validate_workspace_id(args.workspace_id)
        sql = validate_sql(_read_sql(args.sql_file))
        url = build_query_url(endpoint, workspace_id)

        if args.dry_run:
            print(
                json.dumps(
                    {
                        "dryRun": True,
                        "url": url,
                        "workspaceId": workspace_id,
                        "requestBody": {"sql": sql},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        selected_token = resolve_access_token(access_token)
        result = execute_query(
            endpoint=endpoint,
            workspace_id=workspace_id,
            sql=sql,
            token=selected_token,
            timeout=args.timeout,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValidationError, QueryError, OSError) as exc:
        secret = selected_token or access_token or os.environ.get(TOKEN_ENV)
        print(f"错误：{_redact(str(exc), secret)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
