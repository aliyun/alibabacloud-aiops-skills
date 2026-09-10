#!/usr/bin/env python3
"""Offline checks for CLI-bound direct SLS log alert documents (Python 3.7+).

Usage: validate_alert.py [--json] FILE (or - for stdin).
Checks structure, identity byte limits, schedule shape, query/join cardinality,
severity and JSON types, and known CLI incompatibility. Does not execute or
parse SQL, expressions, Cron grammar, policy DSL, permissions, or templates.
Unknown fields are retained. Unsupported modes are warnings, not service errors.
Exit 0: local checks passed (inspect warnings); 1: invalid; 2: CLI usage error.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def validate_alert(document):
    errors, warnings = [], []

    def obj(value, path):
        if not isinstance(value, dict):
            errors.append(path + " must be an object")
            return {}
        return value

    def array(value, path):
        if not isinstance(value, list):
            errors.append(path + " must be an array")
            return []
        return value

    def string(value, path, nonempty=True):
        if not isinstance(value, str):
            errors.append(path + " must be a string")
            return False
        if nonempty and not value.strip():
            errors.append(path + " must not be empty")
            return False
        return True

    def integer(value, path, minimum, maximum=None):
        if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
            errors.append(path + " must be an integer in the documented range")

    def booleans(value, fields, path):
        for field in fields:
            if field in value and type(value[field]) is not bool:
                errors.append(path + "." + field + " must be a boolean")

    def severity(value, path):
        if type(value) is not int or value not in (2, 4, 6, 8, 10):
            errors.append(path + " must be one of 2, 4, 6, 8, 10")

    def result():
        return {"valid": not errors, "errors": errors, "warnings": warnings}

    doc = obj(document, "rule")
    name = doc.get("name")
    if string(name, "name") and (
        not 4 <= len(name) <= 64 or not re.fullmatch(r"[0-9a-z][0-9a-z_-]*[0-9a-z]", name)
    ):
        errors.append("name must be 4–64 lowercase ASCII letters/digits, hyphens or underscores, with alphanumeric ends")
    for field, lower, upper in (("displayName", 4, 100), ("description", 0, 256)):
        if field == "description" and field not in doc:
            continue
        value = doc.get(field)
        if string(value, field, nonempty=False) and not lower <= len(value.encode("utf-8")) <= upper:
            errors.append(field + " exceeds its documented UTF-8 byte limits")

    schedule = obj(doc.get("schedule"), "schedule")
    kind = schedule.get("type")
    if string(kind, "schedule.type"):
        if kind == "FixedRate":
            interval = schedule.get("interval")
            if string(interval, "schedule.interval"):
                match = re.fullmatch(r"([0-9]+)([smhd])", interval)
                if not match:
                    errors.append("schedule.interval must be an integer duration with s/m/h/d suffix")
                else:
                    seconds = int(match[1]) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match[2]]
                    if not 60 <= seconds <= 2592000:
                        errors.append("schedule.interval must be between 60 seconds and 30 days")
        elif kind == "Cron":
            cron = schedule.get("cronExpression")
            if string(cron, "schedule.cronExpression") and (len(cron) > 64 or len(cron.split()) != 5):
                errors.append("schedule.cronExpression must have five fields and at most 64 characters")
            zone = schedule.get("timeZone")
            if string(zone, "schedule.timeZone"):
                match = re.fullmatch(r"([+-])([0-9]{2})([0-9]{2})", zone)
                if not match:
                    errors.append("schedule.timeZone must use +HHMM or -HHMM")
                else:
                    minutes = (int(match[2]) * 60 + int(match[3])) * (-1 if match[1] == "-" else 1)
                    if int(match[3]) >= 60 or not -720 <= minutes <= 840:
                        errors.append("schedule.timeZone must be between -1200 and +1400 with valid minutes")
            warnings.append("Cron grammar and service timezone interpretation are not validated locally")
        else:
            warnings.append("schedule type is outside this validator's FixedRate/Cron coverage")
    if "delay" in schedule:
        integer(schedule["delay"], "schedule.delay", 0, 86400)
    booleans(schedule, ("runImmediately",), "schedule")

    config = obj(doc.get("configuration"), "configuration")
    if config.get("version") != "2.0" or config.get("type") != "default":
        warnings.append("configuration is outside direct version 2.0 coverage; obtain its schema before writing")
        return result()
    queries = array(config.get("queryList"), "configuration.queryList")
    if not queries:
        errors.append("configuration.queryList must contain at least one query")
    if len(queries) > 3:
        warnings.append("more than three queries is outside the documented workflow; verify service support")
    for i, value in enumerate(queries):
        path = "configuration.queryList[{}]".format(i)
        query = obj(value, path)
        if query.get("storeType", "log") == "log":
            for field in ("store", "query", "timeSpanType", "start", "end"):
                string(query.get(field), path + "." + field)
        else:
            warnings.append(path + " is not a log query; source-specific validation is required")
        for field in ("region", "project", "roleArn", "powerSqlMode", "storeType"):
            if field in query:
                string(query[field], path + "." + field, nonempty=False)

    joins = array(config.get("joinConfigurations", []), "configuration.joinConfigurations")
    if queries and len(joins) != len(queries) - 1:
        errors.append("joinConfigurations length must equal queryList length minus one")
    for i, value in enumerate(joins):
        path = "configuration.joinConfigurations[{}]".format(i)
        join = obj(value, path)
        string(join.get("type"), path + ".type")
        if "condition" in join:
            string(join["condition"], path + ".condition", nonempty=False)

    branches = array(config.get("severityConfigurations"), "configuration.severityConfigurations")
    if not branches:
        errors.append("configuration.severityConfigurations must not be empty")
    levels = []
    for i, value in enumerate(branches):
        path = "configuration.severityConfigurations[{}]".format(i)
        branch = obj(value, path)
        level = branch.get("severity")
        severity(level, path + ".severity")
        if type(level) is int:
            levels.append(level)
        condition = obj(branch.get("evalCondition"), path + ".evalCondition")
        for field in ("condition", "countCondition"):
            string(condition.get(field), path + ".evalCondition." + field, nonempty=False)
    if levels != sorted(levels, reverse=True):
        warnings.append("severity branches are not descending; an earlier match can mask higher severity")
    if "noDataSeverity" in config:
        severity(config["noDataSeverity"], "configuration.noDataSeverity")
    if "threshold" in config:
        integer(config["threshold"], "configuration.threshold", 1)
    booleans(config, ("autoAnnotation", "sendResolved", "noDataFire"), "configuration")

    if "groupConfiguration" in config:
        group = obj(config["groupConfiguration"], "configuration.groupConfiguration")
        string(group.get("type"), "configuration.groupConfiguration.type")
        if "fields" in group:
            fields = array(group["fields"], "configuration.groupConfiguration.fields")
            for field in fields:
                string(field, "configuration.groupConfiguration.fields[]")
        if group.get("type") == "custom" and not group.get("fields"):
            errors.append("custom groupConfiguration requires fields")

    for field in ("sinkAlerthub", "sinkCms", "sinkEventStore"):
        if field in config:
            sink = obj(config[field], "configuration." + field)
            booleans(sink, ("enabled",), "configuration." + field)
    if "policyConfiguration" in config:
        policy = obj(config["policyConfiguration"], "configuration.policyConfiguration")
        if "useDefault" in policy:
            errors.append("policyConfiguration.useDefault is incompatible with the checked CLI; follow rule assembly compatibility guidance")
        for field in ("alertPolicyId", "actionPolicyId", "repeatInterval"):
            if field in policy:
                string(policy[field], "configuration.policyConfiguration." + field, nonempty=False)
    return result()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON file or - for stdin")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        source = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        report = validate_alert(json.loads(source))
    except (OSError, ValueError) as exc:
        report = {"valid": False, "errors": ["Cannot validate input ({})".format(type(exc).__name__)], "warnings": []}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for field in ("errors", "warnings"):
            for message in report[field]:
                print(field.upper() + ": " + message, file=sys.stderr)
        if report["valid"]:
            print("OK: local rule checks passed; review warnings")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
