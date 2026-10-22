#!/usr/bin/env python3
"""Validate saved SAS JSON responses without making cloud requests."""
import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone


def security_score(data):
    value = data.get("Score")
    result = {"status": "error", "score": None, "request_id": data.get("RequestId")}
    if value is None or value == "":
        return {**result, "reason": "Score missing or null; verify CalType and API response"}
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return {**result, "reason": "Score has an invalid type"}
    try:
        score = float(value)
    except (ValueError, OverflowError):
        return {**result, "reason": "Score is not numeric"}
    if not math.isfinite(score) or not 0 <= score <= 100:
        return {**result, "reason": "Score is outside the finite 0..100 range"}
    return {"status": "ok", "score": score, "request_id": data.get("RequestId")}


def billing_config(data):
    """Report independent billing evidence; do not infer modes from IsPaidUser."""
    warnings = []
    postpay = data.get("IsPostpay")
    if type(postpay) is not bool:
        postpay = None
        warnings.append("IsPostpay missing/invalid; pay-as-you-go status is unknown")
    modules = None
    raw = data.get("PostPayModuleSwitch")
    if raw is not None:
        try:
            if not isinstance(raw, str):
                raise ValueError("expected a JSON string")
            modules = json.loads(raw)
            if not isinstance(modules, dict) or any(type(v) is not int or v not in (0, 1) for v in modules.values()):
                raise ValueError("expected an object of 0/1 switches")
        except (ValueError, TypeError):
            modules = None
            warnings.append("PostPayModuleSwitch malformed; module status is unknown")
    elif postpay is True:
        warnings.append("PostPayModuleSwitch missing; module status is unknown")
    if postpay is False and modules and any(modules.values()):
        warnings.append("IsPostpay conflicts with enabled module switches; verify configuration")
    trial = data.get("IsTrialVersion")
    trial = bool(trial) if type(trial) is int and trial in (0, 1) else None
    return {"status": "partial" if warnings else "ok", "request_id": data.get("RequestId"),
            "postpay_enabled": postpay, "module_switches": modules,
            "postpay_instance_status": data.get("PostPayStatus"),
            "subscription_evidence": {k: data[k] for k in ("InstanceId", "ReleaseTime", "Version") if k in data},
            "is_trial": trial, "warnings": warnings}


def service_times(data, now_ms=None):
    """Keep service opening, postpay opening and instance expiry independent."""
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    result = {"status": "ok", "request_id": data.get("RequestId")}
    for field, name in (("OpenTime", "service"), ("PostPayOpenTime", "postpay"),
                        ("ReleaseTime", "instance_expiry")):
        value = data.get(field)
        item = {"timestamp_ms": None, "utc": None}
        try:
            if type(value) is not int or value <= 0:
                raise ValueError("missing or invalid millisecond timestamp")
            if name != "instance_expiry" and value > now_ms:
                raise ValueError("opening time is in the future")
            stamp = datetime.fromtimestamp(value / 1000, timezone.utc)
            item.update(timestamp_ms=value, utc=stamp.isoformat())
            if name != "instance_expiry":
                item["elapsed_days"] = (now_ms - value) // 86400000
        except (ValueError, OverflowError, OSError) as exc:
            item["reason"] = str(exc)
            result["status"] = "partial"
        result[name] = item
    return result


def reject_constant(value):
    raise ValueError("Non-finite JSON number is invalid")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["score", "billing", "times"])
    args = parser.parse_args()
    try:
        data = json.load(sys.stdin, parse_constant=reject_constant)
        if not isinstance(data, dict):
            raise ValueError("Expected an API response object")
        result = {"score": security_score, "billing": billing_config, "times": service_times}[args.kind](data)
    except (ValueError, TypeError) as exc:
        result = {"status": "error", "reason": str(exc)}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
