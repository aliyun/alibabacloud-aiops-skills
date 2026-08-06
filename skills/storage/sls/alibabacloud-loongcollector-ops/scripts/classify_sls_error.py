#!/usr/bin/env python3
"""classify_sls_error.py — map an SLS CLI/API error payload to Skill recovery tags.

Deterministic classifier for non-2xx `aliyun sls` responses. Reads JSON (or mixed
CLI text containing a JSON object) and emits the exact `[Error: …]` tag required
by SKILL.md §6, plus requestID / missing RAM Action when present.

Protocol: stdout = single JSON object; stderr = diagnostics; exit code:
  0 = classified a known recovery class
  1 = non-2xx / error present but unmapped (still emits structured fields)
  2 = usage / parse failure

Usage:
  python3 scripts/classify_sls_error.py --file err.json
  aliyun sls get-project ... 2>&1 | python3 scripts/classify_sls_error.py
  python3 scripts/classify_sls_error.py --http-code 403 --body '{"errorCode":"Unauthorized","requestID":"..."}'
"""
import argparse
import json
import os
import re
import sys

JSON_OBJECT_RE = re.compile(r"\{.*\}", re.S)
ACTION_RE = re.compile(
    r"(?:no permission for action|not authorized to perform|action)\s+"
    r"([a-zA-Z]+:[A-Za-z0-9]+)",
    re.I,
)

# (error_tag, recovered_tag, matchers on errorCode / message / http)
CLASS_RULES = (
    (
        "parameter",
        "parameter_fixed",
        {"codes": {"ParameterInvalid", "InvalidParameter", "InvalidArgument"}, "http": {400}},
    ),
    (
        "throttling",
        "throttling_retry",
        {"codes": {"WriteQuotaExceed", "QuotaExceed", "Throttling", "Throttling.User"}, "http": {429}},
    ),
    (
        "internal",
        "internal_retry",
        {"codes": {"InternalServerError", "ServiceUnavailable", "ServerError"}, "http": {500, 502, 503}},
    ),
    (
        "permission",
        "permission_granted",
        {
            "codes": {"Unauthorized", "AccessDenied", "NoPermission", "Forbidden"},
            "http": {401, 403},
        },
    ),
)


def _first_json_object(text: str):
    text = (text or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = JSON_OBJECT_RE.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def classify(payload: dict, http_code=None):
    error_code = (
        payload.get("errorCode")
        or payload.get("code")
        or payload.get("Code")
        or ""
    )
    if isinstance(error_code, str):
        error_code = error_code.strip()
    else:
        error_code = str(error_code)

    message = (
        payload.get("errorMessage")
        or payload.get("message")
        or payload.get("Message")
        or ""
    )
    if not isinstance(message, str):
        message = str(message)

    request_id = (
        payload.get("requestID")
        or payload.get("requestId")
        or payload.get("RequestId")
        or payload.get("request_id")
        or ""
    )
    if not isinstance(request_id, str):
        request_id = str(request_id)

    http = _as_int(http_code)
    if http is None:
        http = _as_int(payload.get("httpCode") or payload.get("httpStatus") or payload.get("status"))

    missing_action = ""
    action_match = ACTION_RE.search(message)
    if action_match:
        missing_action = action_match.group(1)

    for error_tag, recovered_tag, rule in CLASS_RULES:
        codes = {c.casefold() for c in rule["codes"]}
        if error_code and error_code.casefold() in codes:
            return {
                "class": error_tag,
                "error_tag": "[Error: %s]" % error_tag,
                "recovered_tag": "[RECOVERED: %s]" % recovered_tag,
                "error_code": error_code,
                "http_code": http,
                "request_id": request_id,
                "missing_action": missing_action,
                "message": message,
            }
        if http is not None and http in rule["http"]:
            return {
                "class": error_tag,
                "error_tag": "[Error: %s]" % error_tag,
                "recovered_tag": "[RECOVERED: %s]" % recovered_tag,
                "error_code": error_code,
                "http_code": http,
                "request_id": request_id,
                "missing_action": missing_action,
                "message": message,
            }

    return {
        "class": "other",
        "error_tag": "",
        "recovered_tag": "",
        "error_code": error_code,
        "http_code": http,
        "request_id": request_id,
        "missing_action": missing_action,
        "message": message,
    }


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--file", help="error payload file; omit to read stdin")
    ap.add_argument("--body", help="raw error JSON/text body")
    ap.add_argument("--http-code", type=int, help="optional HTTP status override")
    args = ap.parse_args()

    if args.body is not None:
        raw = args.body
    elif args.file:
        if not os.path.isfile(args.file):
            sys.stderr.write("[classify_sls_error] file not found: %s\n" % args.file)
            return 2
        with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    else:
        raw = sys.stdin.read()

    payload = _first_json_object(raw)
    if payload is None:
        sys.stderr.write("[classify_sls_error] no JSON object found in input\n")
        return 2

    result = classify(payload, http_code=args.http_code)
    out = {
        "tool": "classify_sls_error",
        "session_id": os.environ.get("SKILL_SESSION_ID", ""),
        "status": "classified" if result["class"] != "other" else "unmapped",
        **result,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0 if result["class"] != "other" else 1


if __name__ == "__main__":
    sys.exit(main())
