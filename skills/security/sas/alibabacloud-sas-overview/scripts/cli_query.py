#!/usr/bin/env python3
"""Run an allowlisted read query with at most two retries for transient failures."""
import argparse
import errno
import json
import re
import subprocess
import sys
import time

try:
    from .query_permissions import SCOPES
except ImportError:
    from query_permissions import SCOPES

PRODUCTS = {"yundun-sas": "sas", "yundun-waf": "waf-openapi", "bss": "bssopenapi"}
READ_COMMANDS = {(PRODUCTS[action.split(":")[0]],
                  re.sub(r"(?<!^)(?=[A-Z])", "-", action.split(":")[1]).lower())
                 for actions in SCOPES.values() for action in actions}


class QueryError(ValueError):
    def __init__(self, category, attempts, code=None, request_id=None):
        self.category, self.attempts = category, attempts
        self.code, self.request_id = code, request_id
        super().__init__(f"{category}; attempts={attempts}; code={code}; RequestId={request_id}")


def failure_details(output):
    """Extract diagnostic identifiers; never echo arbitrary CLI output/credentials."""
    fields = {}
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            fields = {"Code": data.get("Code"), "RequestId": data.get("RequestId")}
    except ValueError:
        pass
    for field in ("Code", "RequestId"):
        value = fields.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
            match = re.search(r"\b" + field + r"\s*[:=]\s*([A-Za-z0-9_.:-]{1,128})", output)
            fields[field] = match.group(1) if match else None
    lower = output.lower()
    permanent = ("forbidden", "nopermission", "accessdenied", "invalid", "missingparameter",
                 "signature", "unsupported", "notfound", "notactivated", "unauthorized")
    transient = ("bad file descriptor", "connection reset", "connection timed out", "i/o timeout",
                 "requesttimeout", "serviceunavailable", "internalerror", "throttling", "too many requests")
    # Permanent API error codes take priority over incidental words in messages.
    code = (fields.get("Code") or "").lower()
    retry = not any(x in code or x in lower for x in permanent) and any(x in lower for x in transient)
    return retry, fields.get("Code"), fields.get("RequestId")


def run_query(command, run=None, sleep=None, progress=None):
    if len(command) < 3 or command[0] != "aliyun" or tuple(command[1:3]) not in READ_COMMANDS:
        raise ValueError("Only documented overview read queries may be retried")
    run = subprocess.run if run is None else run
    sleep = time.sleep if sleep is None else sleep
    for attempt in range(1, 4):
        if progress:
            progress(f"{command[1]} {command[2]}: attempt {attempt}/3")
        code, request_id = None, None
        try:
            result = run(command, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if not isinstance(data, dict):
                        raise ValueError("Expected response object")
                    return data
                except (ValueError, TypeError):
                    raise QueryError("invalid-response", attempt) from None
            retry, code, request_id = failure_details(result.stdout + "\n" + result.stderr)
            # Prefer structured output if the CLI provides it separately.
            if result.stdout.strip().startswith("{"):
                retry, code, request_id = failure_details(result.stdout)
        except subprocess.TimeoutExpired:
            retry = True
        except OSError as exc:
            retry = exc.errno in (errno.EBADF, errno.ECONNRESET, errno.ETIMEDOUT)
        if not retry or attempt == 3:
            raise QueryError("transient-exhausted" if retry else "non-retryable", attempt, code, request_id)
        if progress:
            progress(f"Transient query failure; retrying after {attempt}s")
        sleep(attempt)  # waits 1s then 2s; 3 total attempts, never an unbounded loop


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    command = parser.parse_args().command
    if command[:1] == ["--"]:
        command = command[1:]
    try:
        print(json.dumps(run_query(command, progress=lambda message: print(message, file=sys.stderr, flush=True)), ensure_ascii=False))
        return 0
    except ValueError as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
