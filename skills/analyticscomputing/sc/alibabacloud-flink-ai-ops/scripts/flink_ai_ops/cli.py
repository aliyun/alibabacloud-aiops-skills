"""Command-line dispatch with authorization checks before client construction."""

import argparse
import asyncio
import json
from pathlib import Path

from . import chat, patrol
from .client import (
    DEFAULT_CHAT_READ_TIMEOUT,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
)
from .common import OpsError, positive_seconds, redact_sensitive
from .sdk import ApiClient


class Parser(argparse.ArgumentParser):
    """Render argument failures through the same JSON boundary as API errors."""

    def error(self, message):
        raise OpsError("ValidationError", message)


def parser():
    """Register workflow commands with one shared scope and transport parser."""
    root = Parser(description="Alibaba Cloud Flink AI assistant and intelligent patrol")
    shared = Parser(add_help=False)
    shared.add_argument("-w", "--workspace", required=True, help="Confirmed workspace ID.")
    shared.add_argument("-n", "--namespace", required=True, help="Confirmed namespace.")
    shared.add_argument("-r", "--region_id", required=True, help="Alibaba Cloud region ID.")
    shared.add_argument("--connect_timeout", type=positive_seconds, default=DEFAULT_CONNECT_TIMEOUT,
                        help="Connect timeout in seconds, default %(default)s.")
    shared.add_argument("--read_timeout", type=positive_seconds,
                        help=f"Read timeout in seconds; default {DEFAULT_CHAT_READ_TIMEOUT} for the AI assistant, {DEFAULT_READ_TIMEOUT} for patrol.")
    commands = root.add_subparsers(dest="command", required=True)
    chat.register(commands, shared)
    patrol.register(commands, shared)
    return root


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise OpsError("ValidationError", "Duplicate JSON key: " + key)
        result[key] = value
    return result


def _body(args):
    raw = getattr(args, "body_json", None)
    filename = getattr(args, "body_file", None)
    if filename is not None:
        try:
            raw = Path(filename).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise OpsError("ValidationError", "Cannot read body_file: " + str(error)) from error
    if raw is None:
        return None
    try:
        result = json.loads(raw, object_pairs_hook=_pairs)
    except ValueError as error:
        raise OpsError("ValidationError", "Request body must be valid JSON: " + str(error)) from error
    if not isinstance(result, dict):
        raise OpsError("ValidationError", "Request body must be a JSON object.")
    return result


def main(argv=None):
    """Preflight locally, then execute one workflow and emit one redacted result."""
    operation = "cli"
    api = None
    data = None
    error = None
    request_id = ""
    compact = False
    try:
        args = parser().parse_args(argv)
        operation = args.command
        compact = getattr(args, "compact", False)
        request = args.prepare(args, _body(args))
        api = ApiClient(args.region_id, args.workspace, args.namespace, args.connect_timeout,
                        args.read_timeout)
        data = args.execute(api, **request)
        if asyncio.iscoroutine(data):
            data = asyncio.run(data)
    except SystemExit as error:
        return int(error.code or 0)
    except (Exception, KeyboardInterrupt) as failure:
        if not isinstance(failure, OpsError):
            failure = OpsError("Interrupted" if isinstance(failure, KeyboardInterrupt) else type(failure).__name__, str(failure) or "Execution interrupted.")
        data = failure.data
        error = {"code": failure.code, "message": failure.message}
        request_id = failure.request_id
    output = {
        "success": error is None, "operation": operation, "data": data, "error": error,
        "request_id": request_id or (api.last_request_id if api is not None else ""),
    }
    output = redact_sensitive(output)
    if compact:
        output["data"] = chat.compact_chat_output(output["data"])
    print(json.dumps(output, ensure_ascii=False, allow_nan=False))
    return 0 if error is None else 1
