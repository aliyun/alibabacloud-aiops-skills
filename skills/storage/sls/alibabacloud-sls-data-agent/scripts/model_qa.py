#!/usr/bin/env python3
"""Read-only Context/Source Model catalogs, shared SLS queries and evidence."""

import argparse
import os
import sys

from _model_qa.contextmodel import ContextModelCatalog, ContextModelClient
from _model_qa.sourcemodel import SourceModelCatalog, SourceModelClient
from _model_qa.slsmodel.output import DEFAULT_MAX_BYTES
from _model_qa.slsmodel.encoding import dumps
from _model_qa.sls_api import SLSClient
from _model_qa.query_time import resolve_time_range
from _model_qa.query_evidence import LogQueryRecord


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


def add_connection(parser):
    parser.add_argument("--endpoint",
                        help="HTTPS SLS service endpoint; overrides --region. Provide --endpoint or --region")
    parser.add_argument("--region",
                        help="Region ID (e.g. cn-beijing); derives <region>.log.aliyuncs.com when --endpoint is omitted")
    parser.add_argument("--timeout", type=positive_int, default=60, help="Read timeout in seconds (default: 60)")


def add_context_model_connection(parser, *, require_model=False):
    add_connection(parser)
    parser.add_argument("--name", dest="context_model_name", required=require_model,
                        help="Context Model name/UUID" if require_model else "Fuzzy filter on the model name only")


def add_context_catalog_connection(parser):
    add_context_model_connection(parser, require_model=True)


def add_regional_connection(parser, *, require_logstore=False):
    add_connection(parser)
    parser.add_argument("--project", required=True, help="Target Project name")
    if require_logstore:
        parser.add_argument("--logstore", required=True, help="Logstore name")


def register_catalog_commands(model_commands, add_connection, *, include_example_queries):
    """Register only the definition reads shared by the two model workflows."""
    catalog = model_commands.add_parser("catalog")
    operations = catalog.add_subparsers(dest="operation", required=True)
    for operation in ("overview", "get"):
        command = operations.add_parser(
            operation,
            description=(
                "Show model sources and the Elements containing their definitions. "
                "--sources filters source entries only; model-level terms and unresolved entries remain. "
                "Unresolved entries are not a basis for data queries. "
                "The output budget may omit Member names or source entries; narrow --sources or increase --max-bytes. "
                "Use catalog get for Member definitions. An item not shown is not necessarily absent, "
                "and untruncated output does not prove upstream completeness."
                if operation == "overview" else
                "Read one Element's Member definitions in their original order, including definitions not yet adopted. "
                "Provide exactly one Element selector. Use --members to select exact Member names. "
                "missingMembers lists requested names that do not exist; omittedMembers lists definitions "
                "omitted by the byte budget. Narrow --members or increase --max-bytes to read omitted definitions."))
        add_connection(command)
        command.add_argument(
            "--max-bytes", type=positive_int, default=DEFAULT_MAX_BYTES,
            help="Target size of the complete response in compact JSON bytes; "
                 "must be positive, not a hard limit (default: %(default)s)")
        if operation == "overview":
            command.add_argument(
                "--sources", dest="source_tags",
                help="Exact source identifiers from overview, comma-separated; omit for no source filtering. "
                     "Selected sources may still be omitted by the output budget")
        if operation == "get":
            selection = command.add_mutually_exclusive_group(required=True)
            for element_type, argument in ELEMENT_SELECTORS.items():
                if element_type == "exampleQuery" and not include_example_queries:
                    continue
                selection.add_argument(
                    "--" + argument.replace("_", "-"), dest=argument,
                    help=f"{element_type} Element name; provide exactly one Element selector")
            command.add_argument(
                "--members", dest="member_names",
                help="Comma-separated exact Member names in this Element; omit for all. "
                     "Names not found appear in missingMembers")
    return operations


def register_context_model_commands(commands):
    model = commands.add_parser("context-model", help="Explore a named Context Model and its storage mappings")
    model_commands = model.add_subparsers(dest="model_command", required=True)
    listing = model_commands.add_parser(
        "list", help="List one page of Context Models",
        description="List one page of Context Models; does not automatically fetch all pages. "
                    "Use --page to read another page. Filters combine with AND.")
    add_context_model_connection(listing)
    listing.add_argument("--page", type=positive_int, default=1, help="Page number (default: %(default)s)")
    listing.add_argument("--size", type=positive_int, default=20, help="Models per page (default: %(default)s)")
    listing.add_argument("--keyword", help="Fuzzy filter on model name, display name or description")
    listing.add_argument("--project-name", help="Exact filter on models whose sources reference this Project")
    operations = register_catalog_commands(model_commands, add_context_catalog_connection, include_example_queries=True)
    resolve = operations.add_parser(
        "resolve", help="Resolve Context Model definitions to physical SLS storage",
        description="Resolve query execution coordinates by Schema Element name or an exact source key. "
                    "Provide exactly one of --schema and --source. Returns the actual schema and datasources, "
                    "including region/project/store and optional search_filter.")
    add_context_catalog_connection(resolve)
    selector = resolve.add_mutually_exclusive_group(required=True)
    selector.add_argument("--schema", dest="schema_name", help="Schema Element name (kind=log_set), not the Context Model name")
    selector.add_argument("--source", dest="source_tag",
                          help="Single exact source key to resolve; mutually exclusive with --schema")


def register_source_model_commands(commands):
    model = commands.add_parser("source-model", help="Explore the selected Project's Source Model")
    model_commands = model.add_subparsers(dest="model_command", required=True)
    status = model_commands.add_parser(
        "status", help="Read Project Source Model generation status",
        description="Return the Source Model's elementCount and taskState. pending means the task is queued; "
                    "an element count of 0 alone does not prove the model is absent.")
    add_regional_connection(status)
    query = model_commands.add_parser(
        "query", help="Read Source Model definitions with SPL",
        description="Execute raw SPL against model content and return query status. "
                    "Provide exactly one of --query and --query-file.")
    add_regional_connection(query)
    input_query = query.add_mutually_exclusive_group(required=True)
    input_query.add_argument("--query", dest="model_query",
                             help="Raw SPL; provide exactly one of --query and --query-file")
    input_query.add_argument("--query-file",
                             help="UTF-8 SPL file; - reads stdin. Provide exactly one of --query and --query-file")
    register_catalog_commands(model_commands, add_regional_connection, include_example_queries=False)


def execute_context_model_command(args):
    client = ContextModelClient(SLSClient(args.endpoint, args.region, args.timeout))
    if args.model_command == "list":
        return client.list_models(args.page, args.size, args.keyword, args.context_model_name, args.project_name)
    catalog = ContextModelCatalog(client, args.context_model_name)
    if args.operation == "resolve":
        return catalog.resolve_storage(args.schema_name, source_tag=args.source_tag)
    return execute_catalog_command(catalog, args)


def execute_source_model_command(args):
    if args.model_command == "query":
        if args.query_file == "-":
            query = sys.stdin.read()
        elif args.query_file is not None:
            with open(args.query_file, encoding="utf-8") as stream:
                query = stream.read()
        else:
            query = args.model_query
        if not query.strip():
            raise CommandError("InvalidParameter", "Source Model query must not be empty")
    client = SourceModelClient(SLSClient(args.endpoint, args.region, args.timeout))
    if args.model_command == "status":
        return client.get_generation_status(args.project)
    if args.model_command == "query":
        return client.query_model_response(args.project, query)
    return execute_catalog_command(SourceModelCatalog(client, args.project), args)


def execute_catalog_command(catalog, args):
    if args.operation == "overview":
        return catalog.overview(parse_name_list(args.source_tags), args.max_bytes)
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
    query = commands.add_parser("query", help="Query logs with a bounded time range",
                                description="Search logs or analyze logs with SQL.")
    add_regional_connection(query, require_logstore=True)
    query.add_argument("--query", dest="log_query", required=True, help="Log search or SQL analysis statement")
    query.add_argument(
        "--time-range",
        help="Query time range, e.g. last_1h, today, yesterday or now-1h~now. "
             "Use alone, or provide both --from and --to; the two forms are mutually exclusive")
    query.add_argument("--from", dest="from_value", help="Start time, e.g. now, now-1h or a Unix timestamp")
    query.add_argument("--to", dest="to_value", help="End time, e.g. now, now-5m or a Unix timestamp")
    query.add_argument("--timezone", help="IANA timezone for today/yesterday; default: system local time")
    query.add_argument("--lines", type=positive_int, default=100,
                       help="Maximum number of log entries returned (default: %(default)s)")
    query.add_argument("--offset", type=nonnegative_int, default=0, help="Pagination offset")
    query.add_argument("--power-sql", action="store_true", help="Use enhanced SQL for this query")
    query.add_argument(
        "--force-accurate", action="store_true",
        help="Request complete SQL results; completeness is determined by the returned status. "
             "Retry once if incomplete")
    query.add_argument("--save-file",
                       help="Save the complete query result and actual request as JSON; "
                            "fail if the target path already exists")
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
    if not args.endpoint and not args.region:
        raise CommandError("InvalidParameter", "Provide --endpoint or --region")
    if args.command == "context-model":
        return execute_context_model_command(args)
    if args.command == "source-model":
        return execute_source_model_command(args)
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
