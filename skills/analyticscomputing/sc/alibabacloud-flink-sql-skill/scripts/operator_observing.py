#!/usr/bin/env python3
"""Start and query operator observing through the VVP console REST API."""

import re
from urllib.parse import quote

from client import SkillIdentityError, build_user_agent, error_response, output, require_args, require_confirmation, success_response
from metric_history import ConsoleClient, MetricError, add_console_args, read_cookie, redact


def cmd_operator_observing(args):
    required = ("workspace", "namespace", "deployment_id", "job_id")
    err = require_args(args, *required, *(() if args.console_url else ("region_id",)))
    if err:
        return output(err, args.output)
    starting = args.subcommand == "start_operator_observing"
    if starting:
        err = require_confirmation(args.subcommand,
                                   "Operator observing samples live records and writes TaskManager logs.", args.confirm)
        if err:
            return output(err, args.output)
    cookie = ""
    client = None
    try:
        build_user_agent()
        if starting:
            if (args.timeout_seconds <= 0 or not re.fullmatch(r"[1-9][0-9]*(?:kb|mb)", args.max_file_size)
                    or any(not re.fullmatch(r"[0-9a-f]{32}", value) for value in args.operator_ids)):
                raise MetricError("Use positive timeout_seconds, max_file_size such as 2mb, and actual 32-character operator IDs.", "ValidationError")
        cookie = read_cookie(args)
        client = ConsoleClient(args, cookie)
        job = client.job(args.deployment_id, args.job_id)
        path = "/jobs/" + quote(args.job_id, safe="") + "/job-data-observing"
        if args.subcommand == "get_operator_observing":
            observing, request_id = client.request(path)
            if not isinstance(observing, dict) or observing.get("jobId") != args.job_id:
                raise MetricError("The observing response does not match the target Job.")
            data = {"job": job, "observing": observing}
        else:
            operators, request_id = client.request(path + ":observableOperator")
            if not isinstance(operators, list) or any(not isinstance(value, str) for value in operators):
                raise MetricError("VVP returned an invalid observable operator list.")
            data = {"job": job, "operator_ids": operators}
            if starting:
                if not set(args.operator_ids).issubset(operators):
                    raise MetricError("A selected operator is not observable in the target Job.", "ValidationError")
                body = {"operators": args.operator_ids, "timeout": f"{args.timeout_seconds}s",
                        "maxFileSize": args.max_file_size}
                accepted, request_id = client.request(path + ":start", body)
                if accepted is not True:
                    raise MetricError("VVP did not confirm acceptance of the observing request.", request_id=request_id)
                data = {"job": job, "accepted": True, "parameters": body}
        result = success_response(args.subcommand, data, request_id)
    except SkillIdentityError as exc:
        result = error_response(args.subcommand, "SkillIdentityError", str(exc))
    except MetricError as exc:
        code = {"MetricQueryError": "OperatorObservingError", "MetricAuthError": "ConsoleAuthError"}.get(exc.code, exc.code)
        result = error_response(args.subcommand, code, str(exc), exc.request_id)
    except Exception:
        result = error_response(args.subcommand, "OperatorObservingError", "The VVP request failed because of a response or connection error.")
    finally:
        if client:
            client.headers.clear()
    output(redact(result, cookie) if cookie else result, args.output)


def register(subparsers):
    for name, help_text in (
        ("get_observable_operators", "List observable operator IDs for a Job"),
        ("get_operator_observing", "Get operator observing status and parameters"),
        ("start_operator_observing", "Start operator observing with a user-provided VVP Cookie"),
    ):
        parser = subparsers.add_parser(name, help=help_text)
        add_console_args(parser)
        parser.add_argument("--deployment_id", required=True, help="Deployment ID")
        parser.add_argument("--job_id", required=True, help="Job UUID, not the Deployment ID")
        if name == "start_operator_observing":
            parser.add_argument("--operator_ids", nargs="+", required=True, help="Actual observable operator IDs, not SQL plan node numbers")
            parser.add_argument("--timeout_seconds", type=int, default=60, help="Maximum observing duration in seconds (default: 60)")
            parser.add_argument("--max_file_size", default="2mb", help="Log size limit with kb or mb unit (default: 2mb)")
            parser.add_argument("--confirm", action="store_true", help="Confirm sampling live records")
        parser.set_defaults(func=cmd_operator_observing, subcommand=name)
