#!/usr/bin/env python3
"""Validate an SLS alert rule locally.

Usage:
    python3 scripts/alerting/validate_alert.py --input FILE
"""

import argparse
import json
import re
import sys
from pathlib import Path


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common.cli import add_input, add_validation_options, resolve_input
from _common.json_io import ToolError, check_output_path, load as _load_json
from _common.reports import emit, exit_code, result as _result, run
from alerting.validation_common import (
    MISSING as _MISSING,
    field_path as _field_path,
    issue as _issue,
    same as _same,
    without_null_fields as _without_null_fields,
)


_NO_BASELINE = object()


def _value_at(document, path):
    if path in ("$", "rule"):
        return document
    if path.startswith("rule."):
        path = path[5:]
    elif path.startswith("rule["):
        path = path[4:]
    pattern = r'(?:^|\.)([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]|\[("(?:\\.|[^"\\])*")\]'
    position, value = 0, document
    for match in re.finditer(pattern, path):
        if match.start() != position:
            return _MISSING
        position = match.end()
        key = match[1] or (int(match[2]) if match[2] else json.loads(match[3]))
        try:
            value = value[key]
        except (KeyError, IndexError, TypeError):
            return _MISSING
    return value if position == len(path) and position else _MISSING


def _mark_baseline(report, current, baseline, original):
    # Attribution preserves severity and is conservative about coupled inputs.
    scopes = (
        r"^(schedule|configuration\.(?:queryList|severityConfigurations|joinConfigurations)\[\d+\]|"
        r"configuration\.(?:groupConfiguration|policyConfiguration|templateConfiguration|"
        r"sinkAlerthub|sinkCms|sinkEventStore))(?=\.|\[|$)"
    )
    for kind in ("errors", "warnings"):
        known = {(item["code"], item["path"]) for item in original[kind]}
        for item in report[kind]:
            if (item["code"], item["path"]) not in known:
                continue
            match = re.match(scopes, item["path"])
            scope = match[1] if match else item["path"]
            before, after = _value_at(baseline, scope), _value_at(current, scope)
            selectors = ("configuration.version", "configuration.type")
            if (
                before is not _MISSING
                and after is not _MISSING
                and _same(before, after)
                and all(
                    _same(_value_at(current, key), _value_at(baseline, key)) for key in selectors
                )
            ):
                item["origin"] = "baseline"


class _Validator:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def type_error(self, value, path, expected):
        code = "REQUIRED" if value is None else "TYPE_MISMATCH"
        message = path + (" is required" if value is None else " must be " + expected)
        self.errors.append(_issue(code, path, message))

    def obj(self, value, path, fields):
        if not isinstance(value, dict):
            self.type_error(value, path, "an object")
            return None
        for field in sorted(set(value) - set(fields.split())):
            self.warnings.append(
                _issue(
                    "UNKNOWN_FIELD",
                    _field_path(path, field),
                    path + "." + field + " is an unknown field; it was preserved",
                )
            )
        return value

    def array(self, value, path):
        if not isinstance(value, list):
            self.type_error(value, path, "an array")
            return []
        return value

    def string(self, value, path, nonempty=True):
        if not isinstance(value, str):
            self.type_error(value, path, "a string")
            return False
        if nonempty and not value.strip():
            self.errors.append(_issue("REQUIRED", path, path + " must not be empty"))
            return False
        return True

    def integer(self, value, path, minimum=None, maximum=None):
        if type(value) is not int:
            self.errors.append(_issue("TYPE_MISMATCH", path, path + " must be an integer"))
        elif (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
            self.errors.append(
                _issue("OUT_OF_RANGE", path, path + " must be in the documented range")
            )

    def booleans(self, value, fields, path):
        for field in fields.split():
            if field in value and type(value[field]) is not bool:
                self.errors.append(
                    _issue(
                        "TYPE_MISMATCH",
                        path + "." + field,
                        path + "." + field + " must be a boolean",
                    )
                )

    def enum(self, value, path, choices, nonempty=True):
        if self.string(value, path, nonempty=nonempty) and value not in choices:
            self.warnings.append(
                _issue("UNKNOWN_VALUE", path, path + " has an unknown value; verify its schema")
            )

    def severity(self, value, path):
        if type(value) is not int:
            self.type_error(value, path, "an integer")
        elif value not in (2, 4, 6, 8, 10):
            self.warnings.append(
                _issue(
                    "UNKNOWN_VALUE",
                    path,
                    path + " is outside the known severity values 2, 4, 6, 8, 10",
                )
            )

    def schedule(self, value):
        schedule = self.obj(
            value, "schedule", "type interval cronExpression timeZone delay runImmediately"
        )
        if schedule is None:
            return
        kind = schedule.get("type")
        self.enum(kind, "schedule.type", ("FixedRate", "Cron"))
        # Check known fields even when the schedule type is not recognized.
        required = (
            ("interval",) if kind == "FixedRate" else ("cronExpression",) if kind == "Cron" else ()
        )
        strings = {
            field: self.string(schedule.get(field), "schedule." + field, nonempty=field in required)
            for field in ("interval", "cronExpression", "timeZone")
            if field in schedule or field in required
        }
        if kind == "FixedRate":
            interval = schedule.get("interval")
            if strings.get("interval"):
                match = re.fullmatch(r"([0-9]+)([smhd])", interval)
                if not match:
                    self.errors.append(
                        _issue(
                            "INVALID_FORMAT",
                            "schedule.interval",
                            "schedule.interval must be an integer duration with s/m/h/d suffix",
                        )
                    )
                else:
                    seconds = int(match[1]) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match[2]]
                    if not 60 <= seconds <= 2592000:
                        self.errors.append(
                            _issue(
                                "OUT_OF_RANGE",
                                "schedule.interval",
                                "schedule.interval must be between 60 seconds and 30 days",
                            )
                        )
        elif kind == "Cron":
            cron = schedule.get("cronExpression")
            if strings.get("cronExpression") and (len(cron) > 64 or len(cron.split()) != 5):
                self.errors.append(
                    _issue(
                        "INVALID_FORMAT",
                        "schedule.cronExpression",
                        "schedule.cronExpression must have five fields and at most 64 characters",
                    )
                )
            zone = schedule.get("timeZone")
            if strings.get("timeZone") and zone:
                match = re.fullmatch(r"([+-])([0-9]{2})([0-9]{2})", zone)
                if not match:
                    self.errors.append(
                        _issue(
                            "INVALID_FORMAT",
                            "schedule.timeZone",
                            "schedule.timeZone must use +HHMM or -HHMM",
                        )
                    )
                else:
                    minutes = (int(match[2]) * 60 + int(match[3])) * (-1 if match[1] == "-" else 1)
                    if int(match[3]) >= 60 or not -720 <= minutes <= 840:
                        self.errors.append(
                            _issue(
                                "OUT_OF_RANGE",
                                "schedule.timeZone",
                                "schedule.timeZone must be between -1200 and +1400 with valid minutes",
                            )
                        )
        if "delay" in schedule:
            self.integer(schedule["delay"], "schedule.delay", 0, 86400)
        self.booleans(schedule, "runImmediately", "schedule")

    def query(self, value, path, require_fields=True):
        query = self.obj(
            value,
            path,
            "chartTitle query timeSpanType start end storeType project store region roleArn dashboardId powerSqlMode ui logStore maxRows",
        )
        if query is None:
            return
        store_type = query.get("storeType", "log")
        self.enum(store_type, path + ".storeType", ("log", "metric", "meta", ""), nonempty=False)
        if store_type == "":
            store_type = "log"
        legacy_target = "logStore" in query and "store" not in query
        if legacy_target:
            self.warnings.append(
                _issue(
                    "LEGACY_FIELD",
                    path + ".logStore",
                    "Legacy query format; version 2.0 required-field checks were skipped",
                )
            )
        if not require_fields or legacy_target:
            required = ()
        elif store_type in ("log", "metric"):
            required = ("store", "query", "timeSpanType", "start", "end")
        else:
            required = ("store",) if store_type == "meta" else ()
        for field in ("store", "query", "timeSpanType", "start", "end"):
            if field in required or field in query:
                allow_empty_end = (
                    field == "end"
                    and query.get("timeSpanType") == "Relative"
                    and query.get(field) == ""
                )
                self.string(
                    query.get(field),
                    path + "." + field,
                    nonempty=field in required and not allow_empty_end,
                )
        for field in ("chartTitle", "region", "project", "roleArn", "dashboardId", "ui"):
            if field in query:
                self.string(query[field], path + "." + field, nonempty=False)
        if "timeSpanType" in query and store_type != "meta":
            self.enum(
                query["timeSpanType"],
                path + ".timeSpanType",
                (
                    "Relative",
                    "Truncated",
                    "Today",
                    "Custom",
                    "Yesterday",
                    "TheDayBeforeYesterday",
                    "ThisWeek",
                    "LastWeek",
                    "ThisMonth",
                    "ThisQuarter",
                    "Range",
                    "RangeTruncated",
                ),
            )
        if "powerSqlMode" in query:
            self.enum(query["powerSqlMode"], path + ".powerSqlMode", ("auto", "enable", "disable"))
        if "maxRows" in query:
            self.integer(query["maxRows"], path + ".maxRows")
        if "logStore" in query and self.string(
            query["logStore"], path + ".logStore", nonempty=legacy_target
        ):
            if query["logStore"] and query.get("store") and query["logStore"] != query["store"]:
                self.warnings.append(
                    _issue(
                        "LEGACY_FIELD",
                        path + ".logStore",
                        "logStore differs from store; new rules use store as the query target",
                    )
                )

    def condition(self, value, path):
        condition = self.obj(value, path, "condition countCondition")
        if condition is None:
            return
        for field in ("condition", "countCondition"):
            if field in condition:
                self.string(condition.get(field), path + "." + field, nonempty=False)

    def configuration(self, value):
        config = self.obj(
            value,
            "configuration",
            "muteUntil version type templateConfiguration dashboard threshold noDataFire noDataSeverity sendResolved queryList annotations labels conditionConfiguration severityConfigurations joinConfigurations groupConfiguration policyConfiguration autoAnnotation sinkEventStore sinkCms sinkAlerthub tags condition notifyThreshold throttling notificationList sendRecoveryMessage",
        )
        if config is None:
            return
        if "version" in config:
            self.enum(config["version"], "configuration.version", ("2.0",))
        else:
            self.warnings.append(
                _issue(
                    "COVERAGE_WARNING",
                    "configuration",
                    "Configuration has no version; schema coverage is limited",
                )
            )
        self.enum(config.get("type", "default"), "configuration.type", ("default",))
        is_v2 = config.get("version") == "2.0"
        direct = is_v2 and config.get("type", "default") == "default"

        queries = None
        if direct or "queryList" in config:
            queries = self.array(config.get("queryList"), "configuration.queryList")
            if is_v2 and queries == [] and isinstance(config.get("queryList"), list):
                self.errors.append(
                    _issue(
                        "REQUIRED",
                        "configuration.queryList",
                        "configuration.queryList must contain at least one query",
                    )
                )
            if len(queries) > 3:
                self.warnings.append(
                    _issue(
                        "COVERAGE_WARNING",
                        "configuration.queryList",
                        "configuration.queryList exceeds the known limit of three queries",
                    )
                )
            for i, query in enumerate(queries):
                self.query(query, "configuration.queryList[{}]".format(i), require_fields=is_v2)

        joins = self.array(config.get("joinConfigurations", []), "configuration.joinConfigurations")
        if (
            is_v2
            and queries
            and isinstance(config.get("joinConfigurations", []), list)
            and len(joins) != len(queries) - 1
        ):
            self.errors.append(
                _issue(
                    "JOIN_COUNT_MISMATCH",
                    "configuration.joinConfigurations",
                    "configuration.joinConfigurations length must equal queryList length minus one",
                )
            )
        conditional_joins = (
            "inner_join",
            "left_join",
            "right_join",
            "full_join",
            "left_exclude",
            "right_exclude",
        )
        for i, value in enumerate(joins):
            path = "configuration.joinConfigurations[{}]".format(i)
            join = self.obj(value, path, "type condition")
            if join is None:
                continue
            self.enum(
                join.get("type"),
                path + ".type",
                ("no_join", "cross_join", "concat") + conditional_joins,
            )
            if join.get("type") in conditional_joins or "condition" in join:
                self.string(
                    join.get("condition"),
                    path + ".condition",
                    nonempty=join.get("type") in conditional_joins,
                )

        if direct or "severityConfigurations" in config:
            branches = self.array(
                config.get("severityConfigurations"), "configuration.severityConfigurations"
            )
            if is_v2 and branches == [] and isinstance(config.get("severityConfigurations"), list):
                self.errors.append(
                    _issue(
                        "REQUIRED",
                        "configuration.severityConfigurations",
                        "configuration.severityConfigurations must not be empty",
                    )
                )
            levels = []
            for i, value in enumerate(branches):
                path = "configuration.severityConfigurations[{}]".format(i)
                branch = self.obj(value, path, "severity evalCondition")
                if branch is None:
                    continue
                level = branch.get("severity")
                self.severity(level, path + ".severity")
                if type(level) is int:
                    levels.append(level)
                if "evalCondition" in branch:
                    self.condition(branch["evalCondition"], path + ".evalCondition")
            if levels != sorted(levels, reverse=True):
                self.warnings.append(
                    _issue(
                        "SEVERITY_ORDER",
                        "configuration.severityConfigurations",
                        "configuration.severityConfigurations is not descending; an earlier match can mask higher severity",
                    )
                )

        if "noDataSeverity" in config:
            self.severity(config["noDataSeverity"], "configuration.noDataSeverity")
        for field, minimum in (("threshold", 1), ("muteUntil", 0)):
            if field in config:
                self.integer(config[field], "configuration." + field, minimum)
        self.booleans(
            config, "autoAnnotation sendResolved noDataFire sendRecoveryMessage", "configuration"
        )
        if "dashboard" in config:
            self.string(config["dashboard"], "configuration.dashboard", nonempty=False)

        if "groupConfiguration" in config:
            group = self.obj(
                config["groupConfiguration"], "configuration.groupConfiguration", "type fields"
            )
            if group is not None:
                self.enum(
                    group.get("type"),
                    "configuration.groupConfiguration.type",
                    ("no_group", "custom", "labels_auto"),
                )
                if "fields" in group:
                    for i, field in enumerate(
                        self.array(group["fields"], "configuration.groupConfiguration.fields")
                    ):
                        self.string(field, "configuration.groupConfiguration.fields[{}]".format(i))
                if group.get("type") == "custom" and group.get("fields") in (None, []):
                    self.errors.append(
                        _issue(
                            "REQUIRED",
                            "configuration.groupConfiguration",
                            "configuration.groupConfiguration requires fields for custom grouping",
                        )
                    )

        for field in ("sinkAlerthub", "sinkCms", "sinkEventStore"):
            if field in config:
                path = "configuration." + field
                fields = (
                    "enabled endpoint project eventStore roleArn"
                    if field == "sinkEventStore"
                    else "enabled"
                )
                sink = self.obj(config[field], path, fields)
                if sink is None:
                    continue
                self.booleans(sink, "enabled", path)
                for key in fields.split()[1:]:
                    if key in sink:
                        self.string(sink[key], path + "." + key, nonempty=False)
        if "policyConfiguration" in config:
            path = "configuration.policyConfiguration"
            policy = self.obj(
                config["policyConfiguration"],
                path,
                "alertPolicyId actionPolicyId repeatInterval useDefault",
            )
            if policy is not None:
                self.booleans(policy, "useDefault", path)
                for field in ("alertPolicyId", "actionPolicyId", "repeatInterval"):
                    if field in policy:
                        self.string(policy[field], path + "." + field, nonempty=False)

        for field in ("labels", "annotations"):
            if field in config:
                path = "configuration." + field
                for i, value in enumerate(self.array(config[field], path)):
                    item_path = path + "[{}]".format(i)
                    item = self.obj(value, item_path, "key value")
                    if item is None:
                        continue
                    self.string(item.get("key"), item_path + ".key")
                    self.string(item.get("value"), item_path + ".value", nonempty=False)
        if "tags" in config:
            for i, tag in enumerate(self.array(config["tags"], "configuration.tags")):
                self.string(tag, "configuration.tags[{}]".format(i))
        if "conditionConfiguration" in config:
            self.condition(config["conditionConfiguration"], "configuration.conditionConfiguration")
        if "templateConfiguration" in config:
            self.template(config["templateConfiguration"])
        for field in ("condition", "throttling"):
            if field in config:
                self.string(config[field], "configuration." + field, nonempty=False)
        if "notifyThreshold" in config:
            self.integer(config["notifyThreshold"], "configuration.notifyThreshold", 0)
        if "notificationList" in config:
            path = "configuration.notificationList"
            notifications = self.array(config["notificationList"], path)
            for i, notification in enumerate(notifications):
                if not isinstance(notification, dict):
                    self.type_error(notification, path + "[{}]".format(i), "an object")
            if notifications:
                self.warnings.append(
                    _issue(
                        "LEGACY_NOTIFICATION",
                        path,
                        "Legacy recipients do not establish the new rule's notification path; verify its policies and sinks",
                    )
                )
        if config.get("sendRecoveryMessage") is True:
            self.warnings.append(
                _issue(
                    "LEGACY_FIELD",
                    "configuration.sendRecoveryMessage",
                    "Use sendResolved for recovery notifications; this legacy flag is not mapped automatically",
                )
            )

    def template(self, value):
        path = "configuration.templateConfiguration"
        template = self.obj(value, path, "id type version lang tokens annotations aonotations")
        if template is None:
            return
        for field in ("id", "type", "version", "lang"):
            if field in template:
                self.string(template[field], path + "." + field, nonempty=False)
        # Token/annotation names are open keys, not schema field names. Keep the
        # historical API spelling aonotations as well as annotations.
        for field in ("tokens", "annotations", "aonotations"):
            if field not in template:
                continue
            mapping = template[field]
            if not isinstance(mapping, dict):
                self.errors.append(
                    _issue(
                        "TYPE_MISMATCH",
                        path + "." + field,
                        path + "." + field + " must be an object",
                    )
                )
            elif field == "tokens":
                for key, item in mapping.items():
                    self.string(item, _field_path(path + ".tokens", key), nonempty=False)


def _validate_alert(document):
    validator = _Validator()
    doc = validator.obj(
        document,
        "rule",
        "name displayName description schedule configuration createTime lastModifiedTime status apiType type state recyclable scheduleId",
    )
    if doc is None:
        return _result(validator.errors, validator.warnings)
    name = doc.get("name")
    if validator.string(name, "name") and (
        not 4 <= len(name) <= 64 or not re.fullmatch(r"[0-9a-z][0-9a-z_-]*[0-9a-z]", name)
    ):
        validator.errors.append(
            _issue(
                "INVALID_FORMAT",
                "name",
                "name must be 4–64 lowercase ASCII letters/digits, hyphens or underscores, with alphanumeric ends",
            )
        )
    for field, lower, upper in (("displayName", 4, 100), ("description", 0, 256)):
        if field == "description" and field not in doc:
            continue
        value = doc.get(field)
        if (
            validator.string(value, field, nonempty=False)
            and not lower <= len(value.encode("utf-8")) <= upper
        ):
            validator.errors.append(
                _issue("OUT_OF_RANGE", field, field + " exceeds its documented UTF-8 byte limits")
            )
    if "status" in doc:
        validator.enum(doc["status"], "status", ("ENABLED", "DISABLED"))
    if "state" in doc:
        validator.enum(doc["state"], "state", ("Enabled", "Disabled"))
    validator.booleans(doc, "recyclable", "rule")
    if "scheduleId" in doc:
        validator.string(doc["scheduleId"], "scheduleId", nonempty=False)
    for field in ("type", "apiType"):
        if field in doc and validator.string(doc[field], field) and doc[field] != "Alert":
            validator.errors.append(
                _issue("IDENTITY_MISMATCH", field, field + " must identify an Alert task")
            )
    for field in ("createTime", "lastModifiedTime"):
        if field in doc:
            validator.integer(doc[field], field, 0)
    validator.schedule(doc.get("schedule"))
    validator.configuration(doc.get("configuration"))
    return _result(validator.errors, validator.warnings)


def validate_alert(document, baseline=_NO_BASELINE):
    document = _without_null_fields(document)
    report = _validate_alert(document)
    if baseline is _NO_BASELINE:
        return report
    baseline = _without_null_fields(baseline)
    if (
        not isinstance(baseline, dict)
        or not isinstance(baseline.get("name"), str)
        or not baseline["name"].strip()
    ):
        report["errors"].append(
            _issue("BASELINE_INVALID", "$", "Baseline must be a rule object with a stable name")
        )
    elif not isinstance(document, dict) or document.get("name") != baseline["name"]:
        report["errors"].append(
            _issue("BASELINE_ID_MISMATCH", "name", "Baseline and input must select the same rule")
        )
    else:
        _mark_baseline(report, document, baseline, _validate_alert(baseline))
    return _result(report["errors"], report["warnings"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    add_input(parser, positional=True)
    add_validation_options(parser)
    parser.add_argument(
        "--baseline", type=Path, help="Original rule JSON for diagnostic provenance"
    )
    args = parser.parse_args(argv)
    path = resolve_input(parser, args)
    check_output_path(args.output, (path if path != "-" else None, args.baseline))
    try:
        payload = _load_json(path, allow_stdin=True)
        baseline = _load_json(args.baseline, "Baseline") if args.baseline else _NO_BASELINE
    except (ToolError, ValueError) as exc:
        report = _result([_issue("INPUT_ERROR", "$", str(exc))], [])
    else:
        report = validate_alert(payload, baseline)
    emit(report, args.output)
    return exit_code(report, args.strict)


if __name__ == "__main__":
    raise SystemExit(run(main))
