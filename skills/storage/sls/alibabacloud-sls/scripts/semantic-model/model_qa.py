#!/usr/bin/env python3
"""Local model-definition search and Source Model readiness checks."""

import argparse
import os

from readiness import check_logstore_readiness
from slsmodel.catalog_search import search
from slsmodel.output import DEFAULT_MAX_BYTES, search_output
from slsmodel.encoding import dumps
from sls_cli import SLSModelCLI


class CommandError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CommandError("InvalidParameter", message)


def positive_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def parse_name_list(value):
    if value is None:
        return None
    return list(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))


def required_subparsers(parser, dest):
    """Avoid the required keyword added to add_subparsers in Python 3.7."""
    commands = parser.add_subparsers(dest=dest)
    commands.required = True
    return commands


def add_context_model_connection(parser):
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("SLS_CONTEXT_MODEL_ENDPOINT"),
        help="HTTPS Context Model endpoint",
    )
    parser.add_argument(
        "--timeout",
        type=positive_int,
        default=60,
        help="CLI subprocess deadline in seconds (default: 60)",
    )
    parser.add_argument("--profile", help="Aliyun CLI profile; otherwise use CLI profile selection")
    parser.add_argument("--region", help="Optional region override for the Context Model endpoint")
    parser.add_argument(
        "--name", dest="context_model_name", required=True, help="Context Model name/UUID"
    )


def add_regional_connection(parser, *, require_logstore=False):
    parser.add_argument("--endpoint", help="Optional regional SLS endpoint override")
    parser.add_argument(
        "--timeout",
        type=positive_int,
        default=60,
        help="CLI subprocess deadline in seconds (default: 60)",
    )
    parser.add_argument("--profile", help="Aliyun CLI profile; otherwise use CLI profile selection")
    parser.add_argument("--region", required=True)
    parser.add_argument("--project", required=True)
    if require_logstore:
        parser.add_argument("--logstore", required=True)


def register_catalog_search(model_commands, add_connection):
    """Keep lexical retrieval local; overview/get/resolve use aliyun sls."""
    catalog = model_commands.add_parser("catalog")
    operations = required_subparsers(catalog, "operation")
    command = operations.add_parser("search")
    add_connection(command)
    command.add_argument("--max-bytes", type=positive_int, default=DEFAULT_MAX_BYTES)
    command.add_argument(
        "--sources", dest="source_tags", help="Comma-separated exact metadata.tags.source values"
    )
    command.add_argument(
        "--query",
        dest="search_text",
        required=True,
        help="Question or branch intent; lexical definition retrieval",
    )
    command.add_argument(
        "--limit", type=positive_int, default=20, help="Maximum selected definitions, 1..200"
    )


def register_context_model_commands(commands):
    model = commands.add_parser("context-model", help="Search a named Context Model's definitions")
    model_commands = required_subparsers(model, "model_command")
    register_catalog_search(model_commands, add_context_model_connection)


def register_source_model_commands(commands):
    model = commands.add_parser("source-model", help="Explore the selected Project's Source Model")
    model_commands = required_subparsers(model, "model_command")
    ready = model_commands.add_parser(
        "readiness", help="Check the selected Logstore's Source Model readiness"
    )
    add_regional_connection(ready, require_logstore=True)
    ready.add_argument(
        "--legacy-status",
        action="store_true",
        help="Accept an explicitly known legacy status response without taskState",
    )
    register_catalog_search(model_commands, add_regional_connection)


def build_parser():
    root = JSONArgumentParser(
        description=__doc__,
        epilog="Use aliyun sls for model list/status, catalog overview/get/resolve, query and index get.",
    )
    commands = required_subparsers(root, "command")
    register_context_model_commands(commands)
    register_source_model_commands(commands)
    return root


def run_command(args):
    client = SLSModelCLI(args.endpoint, args.region, args.timeout, args.profile)
    if args.command == "source-model":
        if args.model_command == "readiness":
            return check_logstore_readiness(
                client, args.project, args.logstore, args.region, legacy_status=args.legacy_status
            )
        query_model = lambda spl: client.query_source_model(args.project, spl)
        identity = {"project": args.project}
    elif args.command == "context-model":
        query_model = lambda spl: client.query_context_model(args.context_model_name, spl)
        identity = {"model": args.context_model_name}
    else:
        raise CommandError("InvalidParameter", "Unknown model command")
    result = search(
        query_model,
        args.search_text,
        parse_name_list(args.source_tags),
        args.limit,
        include_example_queries=args.command == "context-model",
    )
    return search_output(identity, result, args.max_bytes)


def error_payload(error):
    code = getattr(error, "code", None) or type(error).__name__
    message = getattr(error, "message", None)
    if message is None and isinstance(error, OSError):
        message = str(error)
    message = str(message or "Request failed; check credentials, endpoint and network access")
    # Do not print subprocess objects or tracebacks containing command arguments.
    result = {"code": str(code), "message": message}
    data = getattr(error, "data", None)
    if isinstance(data, dict) and data.get("requestId"):
        result["requestId"] = data["requestId"]
    if isinstance(data, dict):
        for key in ("httpStatus", "cliExitCode", "stderr"):
            if key in data:
                result[key] = data[key]
    # CLI diagnostics may also contain secret values in stderr or request IDs.
    secret_names = (
        "SECRET",
        "TOKEN",
        "PASSWORD",
        "API_KEY",
        "ACCESS_KEY",
        "ACCESS_KEY_ID",
        "ACCESS_KEY_SECRET",
    )
    secret_values = [
        value
        for key, value in os.environ.items()
        if value
        and any(key.upper() == name or key.upper().endswith("_" + name) for name in secret_names)
    ]

    def redact(value):
        if isinstance(value, dict):
            return {key: redact(item) for key, item in value.items()}
        if isinstance(value, str):
            for secret in secret_values:
                value = value.replace(secret, "[REDACTED]")
        return value

    result = redact(result)
    return {"error": result}


def main(argv=None):
    try:
        result = run_command(build_parser().parse_args(argv))
        print(dumps(result))
        return 0
    except Exception as error:
        print(dumps(error_payload(error)))
        return 2 if str(getattr(error, "code", "")).startswith("Invalid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
