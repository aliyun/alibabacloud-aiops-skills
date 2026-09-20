#!/usr/bin/env python3
"""Read-only Context Model catalog, SLS queries and index inspection."""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from contextmodel import ContextModelCatalog, ContextModelClient
from contextmodel.adaptive_output import DEFAULT_MAX_BYTES
from slsmodel.element import ELEMENTS
from slsmodel.encoding import dumps


# Command and request errors.

class CommandError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class RequestError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# SDK transport and SLS read APIs.

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "references" / "manifest.json"
SESSION_ID = os.environ.get("SKILL_SESSION_ID") or uuid4().hex


def skill_user_agent():
    version = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["version"]
    return f"AlibabaCloud-Agent-Skills/alibabacloud-sls-data-agent-qa/{SESSION_ID} skill-version/{version}"


def endpoint_host(value):
    if not value:
        raise RequestError("InvalidParameter", "Provide --endpoint or SLS_CONTEXT_MODEL_ENDPOINT for model requests")
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        raise RequestError("InvalidParameter", "Endpoint must not contain whitespace or control characters")
    parsed = urlsplit(value if "://" in value else "https://" + value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or not re.fullmatch(r"[A-Za-z0-9.-]+(?::\d+)?", parsed.netloc)):
        raise RequestError("InvalidParameter", "Endpoint must be an HTTPS service host, without credentials or a path")
    return parsed.netloc.lower()


class SLSClient:
    def __init__(self, endpoint=None, region=None, timeout=60):
        if region is not None and not re.fullmatch(r"[a-z0-9-]+", region):
            raise RequestError("InvalidParameter", "Invalid SLS region")
        host = endpoint_host(endpoint or (f"{region}.log.aliyuncs.com" if region else None))
        user_agent = skill_user_agent()
        try:
            from alibabacloud_credentials.client import Client as CredentialClient
            from alibabacloud_sls20201230.client import Client
            from alibabacloud_tea_openapi.utils_models import Config
        except ImportError:
            raise RequestError("MissingDependency", "Install dependencies with python3 -m pip install -r scripts/requirements.txt from the skill directory") from None
        self.client = Client(Config(endpoint=host, region_id=region, protocol="https",
                                    credential=CredentialClient(), connect_timeout=10000,
                                    read_timeout=timeout * 1000, user_agent=user_agent))
        self.timeout = timeout

    def request(self, action, method, path, query=None, body=None, project=None):
        from alibabacloud_tea_openapi.utils_models import OpenApiRequest, Params
        from darabonba.runtime import RuntimeOptions

        if project is not None and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", project):
            raise RequestError("InvalidParameter", "Invalid SLS project name")
        params = Params(action=action, version="2020-12-30", protocol="HTTPS", pathname=path,
                        method=method, auth_type="AK", style="ROA", req_body_type="json", body_type="json")
        # execute is the same public path used by generated SLS SDK methods.
        response = self.client.execute(
            params, OpenApiRequest(query=query, body=body, host_map={"project": project} if project else {}),
            RuntimeOptions(autoretry=False, connect_timeout=10000, read_timeout=self.timeout * 1000))
        if not isinstance(response, dict) or not isinstance(response.get("statusCode"), int):
            raise RequestError("InvalidResponse", "SLS response has no HTTP status")
        if not 200 <= response["statusCode"] < 300:
            raise RequestError("HTTP_" + str(response["statusCode"]), "SLS returned an unsuccessful HTTP status")
        if not isinstance(response.get("body"), dict):
            raise RequestError("InvalidResponse", "SLS response has no JSON object body")
        return response["body"]

    def get_index(self, project, logstore):
        return self.request("GetIndex", "GET", "/logstores/" + quote(logstore, safe="") + "/index", project=project)

    def query_logs(self, project, logstore, query, start, end, lines=100, offset=0, power_sql=False):
        body = self.request("GetLogsV2", "POST", "/logstores/" + quote(logstore, safe="") + "/logs", project=project,
                            body={"from": start, "to": end, "query": query, "line": lines,
                                  "offset": offset, "powerSql": power_sql})
        # REST calls this collection data; the existing CLI exposes it as logs.
        if not isinstance(body.get("meta"), dict) or not isinstance(body.get("data"), list):
            raise RequestError("InvalidResponse", "Log query response requires meta and data")
        if not isinstance(body["meta"].get("progress"), str):
            raise RequestError("InvalidResponse", "Log query response has no progress status")
        return {"meta": body["meta"], "logs": body["data"], "timeRange": {"from": start, "to": end}}


# Time range parsing.

UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "M": 2592000, "y": 31536000}


def point(value, now):
    value = value.strip()
    if value == "now":
        return int(now.timestamp())
    match = re.fullmatch(r"now([+-])(\d+)([smhdwMy])", value)
    if match:
        seconds = int(match[2]) * UNITS[match[3]]
        return int(now.timestamp()) + (seconds if match[1] == "+" else -seconds)
    if re.fullmatch(r"\d{10,19}", value):
        return int(value) // {13: 1000, 16: 1000000, 19: 1000000000}.get(len(value), 1)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("missing timezone")
        return int(parsed.timestamp())
    except (ValueError, OverflowError):
        raise CommandError("InvalidTimeRange", "Use Unix timestamps, now±N[s/m/h/d/w/M/y], or RFC3339 with a timezone") from None


def resolve_time(time_range=None, from_value=None, to_value=None, timezone=None, now=None):
    try:
        now = now or datetime.now(ZoneInfo(timezone) if timezone else None)
    except (ZoneInfoNotFoundError, ValueError):
        raise CommandError("InvalidTimeRange", "Unknown timezone: " + str(timezone)) from None
    if time_range:
        expression = time_range.strip()
        match = re.fullmatch(r"last_(\d+)([smhdwMy])", expression)
        if match:
            end = int(now.timestamp())
            start = end - int(match[1]) * UNITS[match[2]]
        elif expression in ("today", "yesterday"):
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start, end = int(midnight.timestamp()), int(now.timestamp())
            if expression == "yesterday":
                start, end = start - 86400, start
        elif expression.count("~") == 1:
            first, last = expression.split("~")
            start, end = point(first, now), point(last, now)
        else:
            raise CommandError("InvalidTimeRange", "Use last_15m, today, yesterday, or start~end")
    elif from_value is not None and to_value is not None:
        start, end = point(from_value, now), point(to_value, now)
    else:
        raise CommandError("InvalidTimeRange", "Provide --time-range or both --from and --to")
    if start >= end:
        raise CommandError("InvalidTimeRange", "Start must be before end")
    return start, end


# Context Model command arguments and dispatch.

def positive(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def csv_names(value):
    if value is None:
        return None
    return list(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))


def model_connection(parser):
    parser.add_argument("--endpoint", default=os.environ.get("SLS_CONTEXT_MODEL_ENDPOINT"), help="HTTPS model endpoint")
    parser.add_argument("--timeout", type=positive, default=60, help="Read timeout in seconds (default: 60)")


def register_context_model(commands):
    model = commands.add_parser("context-model", help="Explore a Context Model")
    model_commands = model.add_subparsers(dest="model_command", required=True)
    listing = model_commands.add_parser("list", help="List one page of models")
    model_connection(listing)
    listing.add_argument("--page", type=positive, default=1)
    listing.add_argument("--size", type=positive, default=20)
    for flag in ("keyword", "name", "project-name"):
        listing.add_argument("--" + flag)
    catalog = model_commands.add_parser("catalog")
    operations = catalog.add_subparsers(dest="operation", required=True)
    for operation in ("overview", "get", "resolve"):
        command = operations.add_parser(operation)
        model_connection(command)
        command.add_argument("--name", required=True)
        if operation == "resolve":
            command.add_argument("--schema", required=True)
        else:
            command.add_argument("--max-bytes", type=positive, default=DEFAULT_MAX_BYTES)
        if operation == "overview":
            command.add_argument("--sources", help="Comma-separated exact source names")
        if operation == "get":
            selection = command.add_mutually_exclusive_group(required=True)
            for typ in ELEMENTS:
                selection.add_argument("--" + ("example-query" if typ == "exampleQuery" else typ) + "-element", dest=typ)
            command.add_argument("--members", help="Comma-separated exact member names; omit for all")


def execute_context_model(args):
    client = ContextModelClient(SLSClient(args.endpoint, timeout=args.timeout))
    if args.model_command == "list":
        return client.list_models(args.page, args.size, args.keyword, args.name, args.project_name)
    catalog = ContextModelCatalog(client, args.name)
    if args.operation == "overview":
        return catalog.overview(csv_names(args.sources), args.max_bytes)
    if args.operation == "resolve":
        return catalog.resolve(args.schema)
    typ, element = next((typ, getattr(args, typ)) for typ in ELEMENTS if getattr(args, typ) is not None)
    return catalog.get(typ, element, csv_names(args.members), args.max_bytes)


# Top-level CLI, JSON output and exit codes.

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CommandError("InvalidParameter", message)


def nonnegative(value):
    if value == "0":
        return 0
    return positive(value)


def connection(parser):
    parser.add_argument("--endpoint", help="Optional regional SLS endpoint override")
    parser.add_argument("--timeout", type=positive, default=60, help="Read timeout in seconds (default: 60)")
    parser.add_argument("--region", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--logstore", required=True)


def parser():
    root = Parser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    register_context_model(commands)
    query = commands.add_parser("query", help="Query logs with a bounded time range")
    connection(query)
    query.add_argument("--query", required=True)
    query.add_argument("--time-range")
    query.add_argument("--from", dest="from_value")
    query.add_argument("--to", dest="to_value")
    query.add_argument("--timezone", help="IANA timezone for today/yesterday; default: system local time")
    query.add_argument("--lines", type=positive, default=100)
    query.add_argument("--offset", type=nonnegative, default=0)
    query.add_argument("--power-sql", action="store_true")
    query.add_argument("--force-accurate", action="store_true", help="Require SQL accuracy; retry Incomplete once")
    index = commands.add_parser("index", help="Inspect a logstore's index")
    index_commands = index.add_subparsers(dest="index_command", required=True)
    connection(index_commands.add_parser("get"))
    return root


def run(args):
    if args.command == "context-model":
        return execute_context_model(args)
    # Validate time before credentials/network work. Resolve a relative window only once.
    if args.command == "query":
        start, end = resolve_time(args.time_range, args.from_value, args.to_value, args.timezone)
        query = args.query
        if args.force_accurate:
            prefix, separator, sql = query.partition("|")
            if not separator:
                raise CommandError("InvalidParameter", "--force-accurate requires a SQL query")
            query = prefix + "| set session allow_incomplete=false;" + sql
    client = SLSClient(args.endpoint, getattr(args, "region", None), args.timeout)
    if args.command == "index":
        return client.get_index(args.project, args.logstore)
    if args.command == "query":
        for _ in range(2 if args.force_accurate else 1):
            result = client.query_logs(args.project, args.logstore, query, start, end, args.lines, args.offset, args.power_sql)
            if result["meta"]["progress"] == "Complete":
                break
        return result


def error_payload(error):
    while getattr(error, "inner_exception", None) is not None:
        error = error.inner_exception
    code = getattr(error, "code", None) or type(error).__name__
    message = getattr(error, "message", None)
    message = str(message or "Request failed; check credentials, endpoint and network access")
    # Do not print SDK objects/tracebacks, which may contain signed requests.
    for key, value in os.environ.items():
        if value and any(word in key.upper() for word in ("SECRET", "TOKEN", "ACCESS_KEY")):
            message = message.replace(value, "[REDACTED]")
    result = {"code": str(code), "message": message}
    data = getattr(error, "data", None)
    if isinstance(data, dict) and data.get("requestId"):
        result["requestId"] = data["requestId"]
    return {"error": result}


def main(argv=None):
    try:
        result = run(parser().parse_args(argv))
        print(dumps(result))
        return 0
    except Exception as error:
        print(dumps(error_payload(error)))
        return 2 if str(getattr(error, "code", "")).startswith("Invalid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
