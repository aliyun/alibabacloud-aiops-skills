#!/usr/bin/env python3
"""AgentLoop Recall SearchContext CLI (Python port of the former search_context.js).

Uses only the Python 3.8+ standard library. Reads auth and endpoint
configuration from recall.env files or process environment variables and
prints a JSON object to stdout for every outcome, never a traceback.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from email.utils import formatdate
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

CONFIG_KEYS = [
    "AGENTLOOP_ENABLE_RECALL",
    "AGENTLOOP_RECALL_ENDPOINT",
    "AGENTLOOP_CONFIRM_OUTBOUND",
]

SECRET_KEYS = [
    "AGENTLOOP_ACCESS_KEY",
    "AGENTLOOP_ACCESS_SECRET",
    "AGENTLOOP_BEARER_API_KEY",
]

ENV_KEYS = [*CONFIG_KEYS, *SECRET_KEYS]

USAGE = "usage: python3 scripts/experience/search_context.py search --query <text> --context-type experience|memory --confirm-outbound [--limit 5] [--threshold 0.6] [--filter-json '{}']"
MAX_QUERY_LENGTH = 2048
MAX_FILTER_JSON_LENGTH = 8192


def request_id() -> str:
    return str(uuid.uuid4())


def write_json(payload) -> None:
    sys.stdout.write(f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n")


def empty_result(rid: str, error=None) -> dict:
    return {"request_id": rid, "error": error, "results": []}


def help_result(rid: str) -> dict:
    return {"request_id": rid, "error": None, "results": [], "usage": USAGE}


def parse_env_file(file_path, keys=ENV_KEYS) -> dict:
    values: dict = {}
    allowed_keys = set(keys)
    if not file_path or not os.path.exists(file_path):
        return values
    with open(file_path, "r", encoding="utf-8") as handle:
        text = handle.read()
    for raw_line in re.split(r"\r?\n", text):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        without_export = line[len("export "):].strip() if line.startswith("export ") else line
        eq = without_export.find("=")
        if eq < 0:
            continue
        key = without_export[:eq].strip()
        if key not in allowed_keys:
            continue
        value = without_export[eq + 1:].strip()
        quote = value[0] if value else ""
        if quote in ("'", '"') and value.endswith(quote):
            value = value[1:-1]
        else:
            comment = re.search(r"\s#", value)
            if comment:
                value = value[: comment.start()].strip()
        values[key] = value
    return values


def find_project_config(start_dir) -> str | None:
    current = Path(start_dir).resolve()
    while True:
        candidate = current / ".agentloop" / "recall.env"
        if candidate.exists():
            return str(candidate)
        if current.parent == current:
            return None
        current = current.parent


def load_config(keys=ENV_KEYS) -> dict:
    home_config = str(Path.home() / ".agentloop" / "recall.env")
    project_config = find_project_config(os.getcwd())
    env_config = {key: os.environ[key] for key in keys if key in os.environ}
    merged = parse_env_file(home_config, keys)
    merged.update(parse_env_file(project_config, keys))
    merged.update(env_config)
    return merged


def to_number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def parse_args(argv: list) -> dict:
    parsed = {
        "command": argv[0] if argv else None,
        "query": None,
        "contextType": None,
        "limit": 5,
        "threshold": 0.6,
        "filterJson": "{}",
        "confirmOutbound": False,
        "help": False,
    }
    if parsed["command"] in ("--help", "-h"):
        parsed["help"] = True
        return parsed
    i = 1
    while i < len(argv):
        arg = argv[i]

        def read_value():
            nonlocal i
            if i + 1 >= len(argv):
                raise ValueError(f"missing value for {arg}")
            i += 1
            return argv[i]

        if arg == "--query":
            parsed["query"] = read_value()
        elif arg == "--context-type":
            parsed["contextType"] = read_value()
        elif arg == "--limit":
            parsed["limit"] = to_number(read_value())
        elif arg == "--threshold":
            parsed["threshold"] = to_number(read_value())
        elif arg == "--filter-json":
            parsed["filterJson"] = read_value()
        elif arg == "--confirm-outbound":
            parsed["confirmOutbound"] = True
        elif arg in ("--help", "-h"):
            parsed["help"] = True
        else:
            raise ValueError(f"unknown argument: {arg}")
        i += 1
    return parsed


def validate_input(args: dict):
    if args["help"]:
        return None
    if args["command"] != "search":
        return "first argument must be: search"
    if not args["query"] or not str(args["query"]).strip():
        return "missing --query"
    if len(str(args["query"])) > MAX_QUERY_LENGTH:
        return f"--query must be {MAX_QUERY_LENGTH} characters or fewer"
    if not args["contextType"] or args["contextType"] not in ("experience", "memory"):
        return "missing or invalid --context-type"
    limit = to_number(args["limit"])
    if not (math.isfinite(limit) and float(limit).is_integer() and limit >= 1):
        return "--limit must be a positive integer"
    args["limit"] = int(limit)
    threshold = to_number(args["threshold"])
    if not math.isfinite(threshold) or threshold < 0 or threshold > 1:
        return "--threshold must be a number between 0 and 1"
    args["threshold"] = threshold
    if len(str(args["filterJson"] or "")) > MAX_FILTER_JSON_LENGTH:
        return f"--filter-json must be {MAX_FILTER_JSON_LENGTH} characters or fewer"
    try:
        parsed = json.loads(args["filterJson"] or "{}")
    except ValueError as err:
        return f"invalid --filter-json: {err}"
    if not isinstance(parsed, dict):
        return "--filter-json must be a JSON object"
    args["filter"] = parsed
    return None


def enabled(value) -> bool:
    return str(value or "").strip().lower() == "true"


def is_local_http_host(hostname) -> bool:
    return hostname in ("localhost", "127.0.0.1", "::1", "[::1]")


def validate_endpoint(endpoint: str):
    try:
        url = urlsplit(endpoint)
        hostname = url.hostname
    except ValueError as err:
        return f"invalid AGENTLOOP_RECALL_ENDPOINT: {err}"
    if url.scheme not in ("https", "http") or not url.netloc:
        if url.scheme in ("https", "http"):
            return f"invalid AGENTLOOP_RECALL_ENDPOINT: {endpoint}"
        return "AGENTLOOP_RECALL_ENDPOINT must use http or https"
    if url.scheme == "http" and not is_local_http_host(hostname):
        return "AGENTLOOP_RECALL_ENDPOINT must use https for non-local endpoints"
    return None


def js_str(value) -> str:
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, list):
        return ",".join(js_str(item) for item in value)
    return str(value)


def normalize_result(item) -> dict:
    if not isinstance(item, dict):
        return {"title": "", "summary": "", "content": js_str(item), "metadata": {}}
    metadata = dict(item["metadata"]) if isinstance(item.get("metadata"), dict) else {}
    if "contextId" in item and "contextId" not in metadata:
        metadata["contextId"] = item["contextId"]
    if "score" in item and "score" not in metadata:
        metadata["score"] = item["score"]
    if "id" in item and "id" not in metadata:
        metadata["id"] = item["id"]
    content = ""
    for key in ("content", "context", "memory", "text", "body", "formatted"):
        if key in item and item[key] is not None:
            content = js_str(item[key])
            break
    return {
        "title": js_str(item.get("title")),
        "summary": js_str(item.get("summary")),
        "content": content,
        "metadata": metadata,
    }


def js_truthy(value) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return value != ""
    if isinstance(value, (int, float)):
        return value != 0 and not (isinstance(value, float) and math.isnan(value))
    return True


def normalize_response(payload, fallback_request_id: str) -> dict:
    data = payload if isinstance(payload, dict) else {}
    rid = data.get("request_id")
    if not js_truthy(rid):
        rid = data.get("requestId")
    if not js_truthy(rid):
        rid = fallback_request_id
    results = payload if isinstance(payload, list) else data.get("results")
    if not isinstance(results, list):
        inner = data.get("data")
        if isinstance(inner, dict):
            results = inner.get("results")
            if not js_truthy(results):
                results = inner.get("items")
    return {
        "request_id": str(rid),
        "error": None,
        "results": [normalize_result(item) for item in results] if isinstance(results, list) else [],
    }


def rfc1123_date() -> str:
    return formatdate(usegmt=True)


def content_md5(data: str) -> str:
    return base64.b64encode(hashlib.md5(data.encode("utf-8")).digest()).decode("ascii")


def canonicalized_acs_headers(headers: dict) -> str:
    entries = sorted(
        (str(name).lower(), str(value).strip())
        for name, value in headers.items()
        if str(name).lower().startswith("x-acs-")
    )
    return "".join(f"{name}:{value}\n" for name, value in entries)


def canonicalized_resource(url) -> str:
    path = url.path or "/"
    search = f"?{url.query}" if url.query else ""
    return f"{path}{search}"


def api_key_search_endpoint(endpoint: str) -> str:
    url = urlsplit(endpoint)
    if "/contextstore/" in url.path and url.path.endswith("/context/search"):
        url = url._replace(path="/v2/memories/search", query="")
    return urlunsplit(url)


def search_request_body(args: dict, auth_mode: str) -> dict:
    if auth_mode == "apiKey":
        return {
            "query": str(args["query"]).strip(),
            "top_k": args["limit"],
            "threshold": args["threshold"],
            "filters": args.get("filter") or {},
        }
    return {
        "query": str(args["query"]).strip(),
        "context_type": args["contextType"],
        "limit": args["limit"],
        "threshold": args["threshold"],
        "filter": args.get("filter") or {},
        "formatted": True,
    }


def sign_roa_request(method: str, url, headers: dict, access_key: str, access_secret: str) -> str:
    accept = headers.get("Accept", "")
    md5 = headers.get("Content-MD5", "")
    content_type = headers.get("Content-Type", "")
    date = headers.get("Date", "")
    string_to_sign = "\n".join([
        method.upper(),
        accept,
        md5,
        content_type,
        date,
        f"{canonicalized_acs_headers(headers)}{canonicalized_resource(url)}",
    ])
    signature = base64.b64encode(
        hmac.new(access_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode("ascii")
    return f"acs {access_key}:{signature}"


def xml_text(text: str, tag_name: str) -> str:
    match = re.search(rf"<{tag_name}>([\s\S]*?)</{tag_name}>", text, re.IGNORECASE)
    if not match:
        return ""
    value = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", match.group(1))
    return (
        value.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
    )


def parse_response_payload(text, content_type):
    trimmed = str(text or "").strip()
    if not trimmed:
        return {}
    lower_content_type = str(content_type or "").lower()
    if "json" in lower_content_type or trimmed.startswith("{") or trimmed.startswith("["):
        return json.loads(trimmed)
    if "xml" in lower_content_type or trimmed.startswith("<?xml") or trimmed.startswith("<Error"):
        return {
            "code": xml_text(trimmed, "Code"),
            "message": xml_text(trimmed, "Message"),
            "requestId": xml_text(trimmed, "RequestId"),
        }
    return {"message": trimmed[:500]}


def post_json(endpoint: str, auth: dict, body: dict) -> dict:
    url = urlsplit(endpoint)
    data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Content-Length": str(len(data)),
    }
    if auth["mode"] == "ak":
        headers["Date"] = rfc1123_date()
        headers["Content-MD5"] = content_md5(data.decode("utf-8"))
        headers["x-acs-signature-method"] = "HMAC-SHA1"
        headers["x-acs-signature-version"] = "1.0"
        headers["x-acs-signature-nonce"] = request_id()
        headers["x-acs-request-id"] = auth["requestId"]
        headers["Authorization"] = sign_roa_request("POST", url, headers, auth["accessKey"], auth["accessSecret"])
    elif auth["mode"] == "apiKey":
        headers["Authorization"] = f"Token {auth['apiKey']}"
    request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status_code = response.status
            response_content_type = response.headers.get("Content-Type", "") or ""
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        status_code = err.code
        response_content_type = err.headers.get("Content-Type", "") if err.headers else ""
        text = err.read().decode("utf-8")
    return {
        "statusCode": status_code or 0,
        "contentType": response_content_type,
        "payload": parse_response_payload(text, response_content_type),
    }


def main() -> None:
    rid = request_id()
    try:
        args = parse_args(sys.argv[1:])
    except ValueError as err:
        write_json(empty_result(rid, str(err)))
        return

    validation_error = validate_input(args)
    if validation_error:
        write_json(empty_result(rid, validation_error))
        return
    if args["help"]:
        write_json(help_result(rid))
        return

    config = load_config(CONFIG_KEYS)
    if not enabled(config.get("AGENTLOOP_ENABLE_RECALL")):
        write_json(empty_result(rid))
        return

    if not args["confirmOutbound"] and not enabled(config.get("AGENTLOOP_CONFIRM_OUTBOUND")):
        write_json(empty_result(rid, "outbound recall requires explicit confirmation: pass --confirm-outbound or set AGENTLOOP_CONFIRM_OUTBOUND=true after user approval"))
        return

    endpoint = str(config.get("AGENTLOOP_RECALL_ENDPOINT") or "").strip()
    if not endpoint:
        write_json(empty_result(rid, "missing AGENTLOOP_RECALL_ENDPOINT"))
        return
    endpoint_error = validate_endpoint(endpoint)
    if endpoint_error:
        write_json(empty_result(rid, endpoint_error))
        return

    secret_config = load_config(SECRET_KEYS)
    access_key = str(secret_config.get("AGENTLOOP_ACCESS_KEY") or "").strip()
    access_secret = str(secret_config.get("AGENTLOOP_ACCESS_SECRET") or "").strip()
    bearer_api_key = str(secret_config.get("AGENTLOOP_BEARER_API_KEY") or "").strip()
    has_ak_pair = bool(access_key and access_secret)
    if not has_ak_pair and not bearer_api_key:
        write_json(empty_result(rid, "missing credentials: set AGENTLOOP_ACCESS_KEY and AGENTLOOP_ACCESS_SECRET, or AGENTLOOP_BEARER_API_KEY"))
        return

    auth = (
        {"mode": "ak", "accessKey": access_key, "accessSecret": access_secret, "requestId": rid}
        if has_ak_pair
        else {"mode": "apiKey", "apiKey": bearer_api_key}
    )
    request_endpoint = api_key_search_endpoint(endpoint) if auth["mode"] == "apiKey" else endpoint
    body = search_request_body(args, auth["mode"])

    try:
        response = post_json(request_endpoint, auth, body)
        if response["statusCode"] < 200 or response["statusCode"] >= 300:
            payload = response["payload"] if isinstance(response["payload"], dict) else {}
            code = payload.get("code") or payload.get("Code")
            message = payload.get("error") or payload.get("message") or payload.get("Message")
            upstream_request_id = payload.get("requestId") or payload.get("RequestId")
            code_and_message = ": ".join(str(part) for part in (code, message) if js_truthy(part))
            details = " ".join(part for part in (
                code_and_message,
                f"requestId={upstream_request_id}" if js_truthy(upstream_request_id) else "",
            ) if part)
            suffix = f" {details}" if details else ""
            write_json(empty_result(rid, f"SearchContext HTTP {response['statusCode']}{suffix}"))
            return
        write_json(normalize_response(response["payload"], rid))
    except Exception as err:  # noqa: BLE001 - always report as JSON, never traceback
        write_json(empty_result(rid, f"SearchContext request failed: {err}"))


if __name__ == "__main__":
    main()
