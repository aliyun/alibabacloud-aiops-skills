#!/usr/bin/env python3
"""Read-only Context/Source Model catalogs, shared SLS queries and evidence."""

import argparse
import os

from contextmodel import ContextModelCatalog, ContextModelClient
from sourcemodel import SourceModelCatalog, SourceModelClient
from sourcemodel.readiness import check_logstore_readiness
from slsmodel.output import DEFAULT_MAX_BYTES
from slsmodel.encoding import dumps
from sls_api import SLSClient
from query_time import resolve_time_range
from query_evidence import LogQueryRecord


class CommandError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CommandError("InvalidParameter", message)


ELEMENT_SELECTORS = {
    "schema": "schema_element", "overview": "overview_element",
    "metric": "metric_element", "term": "term_element", "exampleQuery": "example_query_element",
}


def positive_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def nonnegative_int(value):
    return 0 if value == "0" else positive_int(value)


def parse_name_list(value):
    if value is None:
        return None
    return list(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))


def add_context_model_connection(parser, *, require_model=False):
    parser.add_argument("--endpoint", default=os.environ.get("SLS_CONTEXT_MODEL_ENDPOINT"), help="HTTPS Context Model endpoint")
    parser.add_argument("--timeout", type=positive_int, default=60, help="Read timeout in seconds (default: 60)")
    parser.add_argument("--name", dest="context_model_name", required=require_model, help="Context Model name/UUID")


def add_context_catalog_connection(parser):
    add_context_model_connection(parser, require_model=True)


def add_regional_connection(parser, *, require_logstore=False):
    parser.add_argument("--endpoint", help="Optional regional SLS endpoint override")
    parser.add_argument("--timeout", type=positive_int, default=60, help="Read timeout in seconds (default: 60)")
    parser.add_argument("--region", required=True)
    parser.add_argument("--project", required=True)
    if require_logstore:
        parser.add_argument("--logstore", required=True)


def register_catalog_commands(model_commands, add_connection, *, include_example_queries):
    """Register only the definition reads shared by the two model workflows."""
    catalog = model_commands.add_parser("catalog")
    operations = catalog.add_subparsers(dest="operation", required=True)
    for operation in ("overview", "get", "search"):
        command = operations.add_parser(operation)
        add_connection(command)
        command.add_argument("--max-bytes", type=positive_int, default=DEFAULT_MAX_BYTES)
        if operation in ("overview", "search"):
            command.add_argument("--sources", dest="source_tags", help="Comma-separated exact metadata.tags.source values")
        if operation == "search":
            command.add_argument("--query", dest="search_text", required=True, help="Question or branch intent; lexical definition retrieval")
            command.add_argument("--limit", type=positive_int, default=20, help="Maximum selected definitions, 1..200")
        if operation == "get":
            selection = command.add_mutually_exclusive_group(required=True)
            for element_type, argument in ELEMENT_SELECTORS.items():
                if element_type == "exampleQuery" and not include_example_queries:
                    continue
                selection.add_argument("--" + argument.replace("_", "-"), dest=argument)
            command.add_argument("--members", dest="member_names", help="Comma-separated exact Member names; omit for all")
    return operations


def register_context_model_commands(commands):
    model = commands.add_parser("context-model", help="Explore a named Context Model and its storage mappings")
    model_commands = model.add_subparsers(dest="model_command", required=True)
    listing = model_commands.add_parser("list", help="List one page of Context Models")
    add_context_model_connection(listing)
    listing.add_argument("--page", type=positive_int, default=1)
    listing.add_argument("--size", type=positive_int, default=20)
    listing.add_argument("--keyword")
    listing.add_argument("--project-name")
    operations = register_catalog_commands(model_commands, add_context_catalog_connection, include_example_queries=True)
    resolve = operations.add_parser("resolve", help="Resolve Context Model definitions to physical SLS storage")
    add_context_catalog_connection(resolve)
    selector = resolve.add_mutually_exclusive_group(required=True)
    selector.add_argument("--schema", dest="schema_name", help="Schema Element name (kind=log_set), not the Context Model name")
    selector.add_argument("--source", dest="source_tag", help="metadata.tags.source value, not a Source Model")


def register_source_model_commands(commands):
    model = commands.add_parser("source-model", help="Explore the selected Project's Source Model")
    model_commands = model.add_subparsers(dest="model_command", required=True)
    status = model_commands.add_parser("status", help="Read Project Source Model generation status")
    add_regional_connection(status)
    ready = model_commands.add_parser("readiness", help="Check the selected Logstore's Source Model readiness")
    add_regional_connection(ready, require_logstore=True)
    ready.add_argument("--legacy-status", action="store_true", help="Accept an explicitly known legacy status response without taskState")
    register_catalog_commands(model_commands, add_regional_connection, include_example_queries=False)


def execute_context_model_command(args):
    if not args.endpoint:
        raise CommandError("InvalidParameter", "Provide --endpoint or SLS_CONTEXT_MODEL_ENDPOINT for Context Model requests")
    client = ContextModelClient(SLSClient(args.endpoint, timeout=args.timeout))
    if args.model_command == "list":
        return client.list_models(args.page, args.size, args.keyword, args.context_model_name, args.project_name)
    catalog = ContextModelCatalog(client, args.context_model_name)
    if args.operation == "resolve":
        return catalog.resolve_storage(args.schema_name, source_tag=args.source_tag)
    return execute_catalog_command(catalog, args)


def execute_source_model_command(args):
    client = SourceModelClient(SLSClient(args.endpoint, args.region, args.timeout))
    if args.model_command == "status":
        return client.get_generation_status(args.project)
    if args.model_command == "readiness":
        return check_logstore_readiness(client, args.project, args.logstore, args.region, legacy_status=args.legacy_status)
    return execute_catalog_command(SourceModelCatalog(client, args.project), args)


def execute_catalog_command(catalog, args):
    if args.operation == "overview":
        return catalog.overview(parse_name_list(args.source_tags), args.max_bytes)
    if args.operation == "search":
        return catalog.search(args.search_text, parse_name_list(args.source_tags), args.limit, args.max_bytes)
    if args.operation == "get":
        element_type, element_name = next((typ, getattr(args, argument)) for typ, argument in ELEMENT_SELECTORS.items()
                                          if getattr(args, argument, None) is not None)
        return catalog.get(element_type, element_name, parse_name_list(args.member_names), args.max_bytes)
    raise CommandError("InvalidParameter", "Unknown catalog operation")


def build_parser():
    root = JSONArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    register_context_model_commands(commands)
    register_source_model_commands(commands)
    query = commands.add_parser("query", help="Query logs with a bounded time range")
    add_regional_connection(query, require_logstore=True)
    query.add_argument("--query", dest="log_query", required=True)
    query.add_argument("--time-range")
    query.add_argument("--from", dest="from_value")
    query.add_argument("--to", dest="to_value")
    query.add_argument("--timezone", help="IANA timezone for today/yesterday; default: system local time")
    query.add_argument("--lines", type=positive_int, default=100)
    query.add_argument("--offset", type=nonnegative_int, default=0)
    query.add_argument("--power-sql", action="store_true")
    query.add_argument("--force-accurate", action="store_true", help="Require SQL accuracy; retry Incomplete once")
    query.add_argument("--save-file", help="Save the actual request and response to a new local JSON file")
    index = commands.add_parser("index", help="Inspect a Logstore's index")
    index_commands = index.add_subparsers(dest="index_command", required=True)
    add_regional_connection(index_commands.add_parser("get"), require_logstore=True)
    return root


def execute_log_query(args):
    # Resolve relative time once, before credentials or network work.
    start, end = resolve_time_range(args.time_range, args.from_value, args.to_value, args.timezone)
    log_query = args.log_query
    if args.force_accurate:
        prefix, separator, sql = log_query.partition("|")
        if not separator:
            raise CommandError("InvalidParameter", "--force-accurate requires a SQL query")
        log_query = prefix + "| set session allow_incomplete=false;" + sql
    with LogQueryRecord(args.save_file) as record:
        client = SLSClient(args.endpoint, args.region, args.timeout)
        for _ in range(2 if args.force_accurate else 1):
            result = client.query_logs(args.project, args.logstore, log_query, start, end, args.lines, args.offset, args.power_sql)
            if result["meta"]["progress"] == "Complete":
                break
        record.commit({"region": args.region, "project": args.project, "logstore": args.logstore,
                       "query": log_query, "from": start, "to": end,
                       "lines": args.lines, "offset": args.offset, "powerSQL": args.power_sql}, result)
        return result


def run_command(args):
    if args.command == "context-model":
        return execute_context_model_command(args)
    if args.command == "source-model":
        return execute_source_model_command(args)
    if args.command == "index":
        return SLSClient(args.endpoint, args.region, args.timeout).get_index(args.project, args.logstore)
    return execute_log_query(args)


def error_payload(error):
    while getattr(error, "inner_exception", None) is not None:
        error = error.inner_exception
    code = getattr(error, "code", None) or type(error).__name__
    message = getattr(error, "message", None)
    if message is None and isinstance(error, OSError):
        message = str(error)
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
        result = run_command(build_parser().parse_args(argv))
        print(dumps(result))
        return 0
    except Exception as error:
        print(dumps(error_payload(error)))
        return 2 if str(getattr(error, "code", "")).startswith("Invalid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
