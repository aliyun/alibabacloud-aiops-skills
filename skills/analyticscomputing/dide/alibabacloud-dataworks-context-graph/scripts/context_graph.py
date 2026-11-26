#!/usr/bin/env python3
"""Read-only DataWorks Context Graph OpenAPI commands."""

import argparse
import getpass
import json
import os
import sys
import time
import unicodedata
import warnings

from context_graph_client import ContextGraphClient
from context_graph_auth import read_credentials_file
from context_graph_cli_transport import validate_backend
from context_graph_contract import (SkillError, endpoint_allowlist, parse_json, resolve_endpoint,
                                    safe_output, validate_request)


CREDENTIAL_ENV = {
    "AccessKeyId": "ALIBABA_CLOUD_ACCESS_KEY_ID",
    "AccessKeySecret": "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    "SecurityToken": "ALIBABA_CLOUD_SECURITY_TOKEN",
}
MAX_CREDENTIAL_BYTES = 64 * 1024


def read_credentials(stream):
    """Read the complete invocation STS triple without echo, persistence, or identity mixing."""
    message = "Provide valid JSON through standard input with exactly AccessKeyId, AccessKeySecret, and SecurityToken, at most 64 KiB."
    try:
        if stream.isatty():
            # Support terminal-only hosts; stop if echo cannot be disabled rather than exposing input.
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                raw = getpass.getpass("STS triple JSON (hidden input): ")
        else:
            raw = stream.read(MAX_CREDENTIAL_BYTES + 1)
        if len(raw.encode("utf-8")) > MAX_CREDENTIAL_BYTES:
            raise SkillError("CredentialsInvalid", message)
        values = parse_json(raw)
        if not isinstance(values, dict) or set(values) != set(CREDENTIAL_ENV):
            raise SkillError("CredentialsInvalid", message)
        for value in values.values():
            if not isinstance(value, str) or not value or any(
                    char.isspace() or unicodedata.category(char).startswith("C") for char in value):
                raise SkillError("CredentialsInvalid", message)
        return {target: values[source] for source, target in CREDENTIAL_ENV.items()}
    except (SkillError, OSError, UnicodeError, EOFError, getpass.GetPassWarning):
        # JSON/read exceptions may include raw input; replace them with a fixed safe message.
        raise SkillError("CredentialsInvalid", message) from None


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # Raw argparse errors echo arguments; use a fixed message to avoid exposing sensitive input.
        raise SkillError("InvalidParameter", "Invalid command or parameters; use --help for current command usage.")


def parser():
    root = Parser(description="Retrieve and read DataWorks Context Graph; request one page per command.", allow_abbrev=False)
    root.add_argument("--region", required=True, help="Knowledge base region, for example cn-beijing")
    root.add_argument("--backend", choices=("sdk", "aliyun"), default="sdk", help="Use the SDK default or delegate to the installed aliyun CLI")
    credentials = root.add_mutually_exclusive_group()
    credentials.add_argument("--credentials-stdin", action="store_true", help="Read the complete invocation STS triple JSON from standard input")
    credentials.add_argument("--credentials-file", help="Read invocation AK/STS credentials only from a user-specified regular file")
    credentials.add_argument("--profile", help="Delegate an existing profile to aliyun; mutually exclusive with explicit credential inputs")
    root.add_argument("--diagnostics", action="store_true", help="Add safe local stage timings, excluding process startup and not pure server time")
    root.add_argument("--include-source-urls", action="store_true", help="Explicitly request temporary download URLs in Sources")
    groups = root.add_subparsers(dest="group", required=True, parser_class=Parser)
    retrieve = groups.add_parser("retrieve", allow_abbrev=False, help="Retrieve knowledge points for the original question")
    retrieve.set_defaults(action="RetrieveKnowledgePoints")
    retrieve.add_argument("--query", required=True)
    retrieve.add_argument("--knowledge-base-ids", type=parse_json, default=argparse.SUPPRESS)
    retrieve.add_argument("--focus-objects", type=parse_json, default=argparse.SUPPRESS)
    retrieve.add_argument("--max-results", type=int, default=argparse.SUPPRESS)
    for group_name in ("point", "base"):
        group = groups.add_parser(group_name, allow_abbrev=False)
        actions = group.add_subparsers(dest="operation", required=True, parser_class=Parser)
        for operation in ("get", "list"):
            cmd = actions.add_parser(operation, allow_abbrev=False)
            prefix = "KnowledgePoint" if group_name == "point" else "KnowledgeBase"
            cmd.set_defaults(action=("Get" if operation == "get" else "List") + prefix + ("s" if operation == "list" else ""))
            if group_name == "point" or operation == "get":
                cmd.add_argument("--knowledge-base-id", required=True)
            if group_name == "point":
                cmd.add_argument("--type", required=operation == "get", default=argparse.SUPPRESS)
            if group_name == "point" and operation == "get":
                cmd.add_argument("--id", required=True)
            if operation == "list" or group_name == "point":
                cmd.add_argument("--max-results", type=int, default=argparse.SUPPRESS)
                cmd.add_argument("--next-token", default=argparse.SUPPRESS)
    return root


PARAMETERS = {
    "query": "Query", "knowledge_base_ids": "KnowledgeBaseIds", "focus_objects": "FocusObjects",
    "max_results": "MaxResults", "knowledge_base_id": "KnowledgeBaseId", "type": "Type",
    "id": "Id", "next_token": "NextToken",
}


def main(argv=None):
    started = time.perf_counter()
    diagnostics = False
    timings = {"CredentialPreparationMs": None, "ClientCallMs": None}
    def emit(payload):
        if diagnostics:
            payload = dict(payload)
            payload["Diagnostics"] = {
                "TimingScope": "Local CLI stages exclude process startup; ClientCall includes SDK initialization, network, and internal retries, not pure server time.",
                **timings, "TotalExecutionMs": round((time.perf_counter() - started) * 1000, 3),
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    action = None
    environ = dict(os.environ)
    secrets = tuple(environ.get(name, "") for name in CREDENTIAL_ENV.values())
    try:
        args = parser().parse_args(argv)
        diagnostics = args.diagnostics
        action = args.action
        validate_backend(args.backend, args.profile)
        params = {target: getattr(args, source) for source, target in PARAMETERS.items()
                  if hasattr(args, source)}
        params = validate_request(action, params)
        resolve_endpoint(args.region, environ.get("DATAWORKS_ENDPOINT"), allowed_hosts=endpoint_allowlist(environ))
        stage_started = time.perf_counter()
        try:
            if args.credentials_stdin:
                credentials = read_credentials(sys.stdin)
                secrets += tuple(credentials.values())
                environ.update(credentials)
            elif args.credentials_file is not None:
                credentials = read_credentials_file(args.credentials_file)
                secrets += tuple(credentials.values())
                environ.update(credentials)
        finally:
            timings["CredentialPreparationMs"] = round((time.perf_counter() - stage_started) * 1000, 3)
        stage_started = time.perf_counter()
        try:
            options = {"backend": args.backend, "profile": args.profile} if args.backend != "sdk" else {}
            result = ContextGraphClient(args.region, environ=environ, **options).invoke(
                action, params, include_source_urls=args.include_source_urls)
        finally:
            timings["ClientCallMs"] = round((time.perf_counter() - stage_started) * 1000, 3)
        emit(safe_output(result, secrets, include_source_urls=args.include_source_urls))
        return 0
    except SkillError as error:
        emit(safe_output(error.envelope(action), secrets))
        return 1
    except KeyboardInterrupt:
        emit({"Success": False, "Error": {"Code": "Interrupted", "Message": "The request was interrupted.", "Retryable": False}})
        return 130
    except Exception:
        emit({"Success": False, "Error": {"Code": "InternalError", "Message": "Local execution failed; check dependencies and input.", "Retryable": False}})
        return 1


if __name__ == "__main__":
    sys.exit(main())
