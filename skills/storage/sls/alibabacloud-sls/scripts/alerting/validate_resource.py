#!/usr/bin/env python3
"""Validate an SLS notification resource value or ResourceRecord locally.

Usage:
    python3 scripts/alerting/validate_resource.py --input FILE --input-kind value --resource-name NAME
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple
from urllib.parse import urlparse


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common.cli import add_input, add_validation_options, resolve_input
from _common.json_io import ToolError, check_output_path, load as _load_json, loads
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
    if path == "$":
        return document
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
    scopes = r'^value\.templates(?:\.[A-Za-z_][A-Za-z0-9_]*|\["(?:\\.|[^"\\])*"\])'
    for kind in ("errors", "warnings"):
        known = {(item["code"], item["path"]) for item in original[kind]}
        for item in report[kind]:
            if (item["code"], item["path"]) not in known:
                continue
            match = re.match(scopes, item["path"])
            scope = match[0] if match else item["path"]
            if item["code"] == "RECIPIENT_READINESS" or item["path"] == "value.type":
                scope = "value"
            if item["path"] == "resource_name" or item["code"] == "IDENTITY_MISMATCH":
                scope = "$"
            before, after = _value_at(baseline, scope), _value_at(current, scope)
            if (
                before is not _MISSING
                and after is not _MISSING
                and _same(before, after)
                and _same(_value_at(current, "value.type"), _value_at(baseline, "value.type"))
            ):
                item["origin"] = "baseline"


class ResourceSpec:
    def __init__(self, id_field, tag_field, required, optional=_MISSING):
        object.__setattr__(self, "id_field", id_field)
        object.__setattr__(self, "tag_field", tag_field)
        object.__setattr__(self, "required", required)
        object.__setattr__(self, "optional", {} if optional is _MISSING else optional)

    def __setattr__(self, name, value):
        raise AttributeError("ResourceSpec fields are read-only")

    def __delattr__(self, name):
        raise AttributeError("ResourceSpec fields are read-only")


class ValidationReport:
    def __init__(
        self,
        resource_name,
        purpose="custom-write",
        errors=_MISSING,
        warnings=_MISSING,
        id_field=None,
        tag_field=None,
        record_id=None,
        record_tag=None,
    ):
        self.resource_name = resource_name
        self.purpose = purpose
        self.errors = [] if errors is _MISSING else errors
        self.warnings = [] if warnings is _MISSING else warnings
        self.id_field = id_field
        self.tag_field = tag_field
        self.record_id = record_id
        self.record_tag = record_tag

    @property
    def result(self) -> str:
        return _result(self.errors, self.warnings)["result"]

    def to_dict(self):
        return _result(
            self.errors,
            self.warnings,
            resource_name=self.resource_name,
            purpose=self.purpose,
            identity_mapping={
                "id_field": self.id_field,
                "tag_field": self.tag_field,
                "id": self.record_id,
                "tag": self.record_tag,
            },
        )

    def error(self, code: str, path: str, message: str) -> None:
        self.errors.append(_issue(code, path, message))

    def warn(self, code: str, path: str, message: str) -> None:
        self.warnings.append(_issue(code, path, message))


RESOURCE_SPECS: Dict[str, ResourceSpec] = {
    "sls.common.user": ResourceSpec(
        id_field="user_id",
        tag_field="user_name",
        required={
            "user_id": str,
            "user_name": str,
            "email": list,
            "country_code": str,
            "phone": str,
            "enabled": bool,
            "sms_enabled": bool,
            "voice_enabled": bool,
        },
    ),
    "sls.common.user_group": ResourceSpec(
        id_field="user_group_id",
        tag_field="user_group_name",
        required={
            "user_group_id": str,
            "user_group_name": str,
            "enabled": bool,
            "members": list,
        },
    ),
    "sls.alert.action_webhook": ResourceSpec(
        id_field="id",
        tag_field="name",
        required={
            "id": str,
            "name": str,
            "type": str,
            "url": str,
            "method": str,
            "headers": list,
        },
        optional={"secret": str},
    ),
    "sls.alert.action_policy": ResourceSpec(
        id_field="action_policy_id",
        tag_field="action_policy_name",
        required={
            "action_policy_id": str,
            "action_policy_name": str,
            "labels": dict,
            "is_default": bool,
            "primary_policy_script": str,
            "secondary_policy_script": str,
            "escalation_start_enabled": bool,
            "escalation_start_timeout": str,
            "escalation_inprogress_enabled": bool,
            "escalation_inprogress_timeout": str,
            "escalation_enabled": bool,
            "escalation_timeout": str,
        },
    ),
    "sls.alert.alert_policy": ResourceSpec(
        id_field="policy_id",
        tag_field="policy_name",
        required={
            "policy_id": str,
            "policy_name": str,
            "parent_id": str,
            "is_default": bool,
            "group_script": str,
            "inhibit_script": str,
            "silence_script": str,
        },
    ),
    "sls.alert.content_template": ResourceSpec(
        id_field="template_id",
        tag_field="template_name",
        required={
            "template_id": str,
            "template_name": str,
            "is_default": bool,
            "templates": dict,
        },
    ),
}


TEMPLATE_CHANNELS: Dict[str, Tuple[str, ...]] = {
    "sms": ("locale", "content"),
    "voice": ("locale", "content"),
    "email": ("locale", "subject", "content"),
    "dingtalk": ("locale", "title", "content"),
    "wechat": ("locale", "title", "content"),
    "lark": ("locale", "title", "content"),
    "slack": ("locale", "title", "content"),
    "webhook": ("locale", "send_type", "limit", "content"),
    "fc": ("locale", "send_type", "limit", "content"),
    "event_bridge": ("locale", "subject", "content"),
    "message_center": ("locale", "content"),
}

WEBHOOK_TYPES = {"dingtalk", "wechat", "lark", "slack", "custom"}


def _matches_type(value: Any, expected: type) -> bool:
    if expected is bool:
        return type(value) is bool
    if expected is int:
        return type(value) is int
    return isinstance(value, expected)


def _type_name(expected: type) -> str:
    return {
        str: "string",
        bool: "boolean",
        list: "array",
        dict: "object",
        int: "integer",
    }.get(expected, expected.__name__)


def _check_known_fields(
    report: ValidationReport, value: Mapping[str, Any], known: Any, path: str
) -> None:
    for name in sorted(set(value) - set(known)):
        report.warn(
            "UNKNOWN_FIELD",
            _field_path(path, name),
            "{}.{} is an unknown field; it was preserved".format(path, name),
        )


def _check_string_list(
    report: ValidationReport, value: Any, path: str, warn_if_empty: bool = False
) -> None:
    if not isinstance(value, list):
        return
    for index, item in enumerate(value):
        if not isinstance(item, str):
            report.error(
                "TYPE_MISMATCH",
                "{}[{}]".format(path, index),
                "{}[{}] must be a string".format(path, index),
            )
        elif not item.strip():
            report.error(
                "REQUIRED",
                "{}[{}]".format(path, index),
                "{}[{}] must not be empty".format(path, index),
            )
    strings = [item for item in value if isinstance(item, str)]
    if len(strings) != len(set(strings)):
        report.warn("DUPLICATE_VALUE", path, "{} contains duplicate entries".format(path))
    if warn_if_empty and not value:
        report.warn(
            "RECIPIENT_READINESS",
            path,
            "{} is empty; the resource has no resolved recipients".format(path),
        )


def _check_common_value(
    report: ValidationReport, spec: ResourceSpec, value: Mapping[str, Any]
) -> None:
    _check_known_fields(
        report,
        value,
        set(spec.required) | set(spec.optional) | {"createTime", "lastModifyTime"},
        "value",
    )
    for name, expected in spec.required.items():
        if name not in value:
            report.error("REQUIRED", "value.{}".format(name), "value.{} is required".format(name))
        elif not _matches_type(value[name], expected):
            report.error(
                "TYPE_MISMATCH",
                "value." + name,
                "value.{} must be a {}".format(name, _type_name(expected)),
            )

    for name, expected in spec.optional.items():
        if name in value and not _matches_type(value[name], expected):
            report.error(
                "TYPE_MISMATCH",
                "value." + name,
                "value.{} must be a {}".format(name, _type_name(expected)),
            )

    for name in (spec.id_field, spec.tag_field):
        item = value.get(name)
        if isinstance(item, str) and not item.strip():
            report.error(
                "REQUIRED", "value.{}".format(name), "value.{} must not be empty".format(name)
            )

    report.id_field = spec.id_field
    report.tag_field = spec.tag_field
    if isinstance(value.get(spec.id_field), str):
        report.record_id = value[spec.id_field]
    if isinstance(value.get(spec.tag_field), str):
        report.record_tag = value[spec.tag_field]

    for metadata_field in ("createTime", "lastModifyTime"):
        if report.purpose == "custom-write" and metadata_field in value:
            report.warn(
                "RESPONSE_METADATA",
                "value." + metadata_field,
                "value.{} is response metadata and should not be sent as desired state".format(
                    metadata_field
                ),
            )


def _check_user(report: ValidationReport, value: Mapping[str, Any]) -> None:
    emails = value.get("email")
    _check_string_list(report, emails, "value.email")

    phone = value.get("phone")
    has_phone = isinstance(phone, str) and bool(phone.strip())
    has_email = isinstance(emails, list) and any(
        isinstance(item, str) and item.strip() for item in emails
    )
    if not has_email and not has_phone:
        report.warn(
            "RECIPIENT_READINESS", "value", "the user has no nonempty email address or phone number"
        )
    if value.get("sms_enabled") is True and not has_phone:
        report.warn(
            "RECIPIENT_READINESS",
            "value.sms_enabled",
            "sms_enabled is true but value.phone is empty",
        )
    if value.get("voice_enabled") is True:
        if not has_phone:
            report.warn(
                "RECIPIENT_READINESS",
                "value.voice_enabled",
                "voice_enabled is true but value.phone is empty",
            )
        if value.get("country_code") != "86":
            report.warn(
                "RECIPIENT_READINESS",
                "value.country_code",
                "voice delivery currently requires country_code 86; service acceptance is not tested locally",
            )


def _check_user_group(report: ValidationReport, value: Mapping[str, Any]) -> None:
    _check_string_list(report, value.get("members"), "value.members", warn_if_empty=True)


def _check_webhook(report: ValidationReport, value: Mapping[str, Any]) -> None:
    webhook_type = value.get("type")
    if not isinstance(webhook_type, str):
        return  # The common value checks report the missing or invalid type.
    if not webhook_type.strip():
        report.error("REQUIRED", "value.type", "value.type must not be empty")
        return
    if webhook_type not in WEBHOOK_TYPES:
        report.warn(
            "UNKNOWN_VALUE",
            "value.type",
            "unknown Webhook type; type-specific checks were skipped; verify its schema before writing",
        )
        return

    url = value.get("url")
    if isinstance(url, str):
        try:
            parsed = urlparse(url)
            valid_url = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        except ValueError:
            valid_url = False
        if not valid_url:
            report.error(
                "INVALID_VALUE", "value.url", "value.url must be an absolute HTTP or HTTPS URL"
            )

    method = value.get("method")
    headers = value.get("headers")
    if webhook_type in {"dingtalk", "wechat", "lark", "slack"}:
        if method != "POST":
            report.error(
                "INVALID_VALUE",
                "value.method",
                "value.method must be POST for a non-custom Webhook",
            )
        if isinstance(headers, list) and headers:
            report.error(
                "INVALID_VALUE",
                "value.headers",
                "value.headers must be empty for a non-custom Webhook",
            )
    elif isinstance(method, str) and method not in {"GET", "POST", "PUT", "DELETE", "OPTIONS"}:
        report.error(
            "INVALID_VALUE",
            "value.method",
            "value.method must be GET, POST, PUT, DELETE, or OPTIONS",
        )

    if isinstance(headers, list):
        for index, header in enumerate(headers):
            path = "value.headers[{}]".format(index)
            if not isinstance(header, dict):
                report.error("TYPE_MISMATCH", path, "{} must be an object".format(path))
                continue
            _check_known_fields(report, header, ("key", "value"), path)
            for field_name in ("key", "value"):
                item = header.get(field_name)
                if not isinstance(item, str):
                    report.error(
                        "TYPE_MISMATCH",
                        "{}.{}".format(path, field_name),
                        "{}.{} must be a string".format(path, field_name),
                    )
                elif field_name == "key" and not item.strip():
                    report.error(
                        "REQUIRED", "{}.key".format(path), "{}.key must not be empty".format(path)
                    )

    if "secret" in value and webhook_type not in {"dingtalk", "lark"}:
        report.warn(
            "COVERAGE_WARNING",
            "value.secret",
            "value.secret is documented only for DingTalk and Lark",
        )


def _check_custom_marker(report: ValidationReport, value: Mapping[str, Any]) -> None:
    if report.purpose == "custom-write" and value.get("is_default") is True:
        report.error(
            "INVALID_VALUE",
            "value.is_default",
            "value.is_default must be false for a custom resource payload",
        )


def _check_action_policy(report: ValidationReport, value: Mapping[str, Any]) -> None:
    _check_custom_marker(report, value)
    labels = value.get("labels")
    if report.purpose == "custom-write" and isinstance(labels, dict) and labels:
        report.error(
            "INVALID_VALUE", "value.labels", "value.labels is reserved and must be an empty object"
        )

    for name in ("primary_policy_script", "secondary_policy_script"):
        script = value.get(name)
        if isinstance(script, str) and not script.strip():
            report.error(
                "REQUIRED", "value.{}".format(name), "value.{} must not be empty".format(name)
            )

    timeout_pairs = (
        ("escalation_start_enabled", "escalation_start_timeout"),
        ("escalation_inprogress_enabled", "escalation_inprogress_timeout"),
        ("escalation_enabled", "escalation_timeout"),
    )
    for enabled_field, timeout_field in timeout_pairs:
        if value.get(enabled_field) is True:
            timeout = value.get(timeout_field)
            if isinstance(timeout, str) and not timeout.strip():
                report.error(
                    "REQUIRED",
                    "value." + timeout_field,
                    "value.{} must not be empty when value.{} is true".format(
                        timeout_field, enabled_field
                    ),
                )


def _check_alert_policy(report: ValidationReport, value: Mapping[str, Any]) -> None:
    _check_custom_marker(report, value)
    group_script = value.get("group_script")
    if isinstance(group_script, str) and not group_script.strip():
        report.error("REQUIRED", "value.group_script", "value.group_script must not be empty")


def _check_template_channel(report: ValidationReport, channel: str, config: Any) -> None:
    path = _field_path("value.templates", channel)
    if not isinstance(config, dict):
        report.error("TYPE_MISMATCH", path, "{} must be an object".format(path))
        return

    required = TEMPLATE_CHANNELS.get(channel)
    if required is None:
        report.warn(
            "UNKNOWN_VALUE",
            path,
            "{} is not known to this validator; its fields were preserved but not checked".format(
                path
            ),
        )
        return

    _check_known_fields(report, config, required, path)

    # Service-returned templates can omit channel fields supplied by defaults.
    if report.purpose == "custom-write":
        for field_name in required:
            if field_name not in config:
                report.error(
                    "REQUIRED",
                    "{}.{}".format(path, field_name),
                    "{}.{} is required".format(path, field_name),
                )

    for field_name in ("locale", "subject", "title", "content", "send_type"):
        if field_name in config and not isinstance(config[field_name], str):
            report.error(
                "TYPE_MISMATCH",
                "{}.{}".format(path, field_name),
                "{}.{} must be a string".format(path, field_name),
            )
    if "limit" in config and not _matches_type(config["limit"], int):
        report.error(
            "TYPE_MISMATCH", "{}.limit".format(path), "{}.limit must be an integer".format(path)
        )
    elif isinstance(config.get("limit"), int) and config["limit"] < 0:
        report.error(
            "OUT_OF_RANGE",
            "{}.limit".format(path),
            "{}.limit must be greater than or equal to zero".format(path),
        )

    locale = config.get("locale")
    if isinstance(locale, str):
        if not locale.strip():
            report.error(
                "REQUIRED", "{}.locale".format(path), "{}.locale must not be empty".format(path)
            )
        elif locale not in {"zh-CN", "en-US"}:
            report.warn(
                "UNKNOWN_VALUE",
                "{}.locale".format(path),
                "{}.locale is not known to this validator; service support was not checked".format(
                    path
                ),
            )

    send_type = config.get("send_type")
    if isinstance(send_type, str) and send_type not in {"single", "batch"}:
        report.warn(
            "UNKNOWN_VALUE",
            path + ".send_type",
            "{}.send_type is not single or batch; preserve it only when it came from a verified service record".format(
                path
            ),
        )


def _check_content_template(report: ValidationReport, value: Mapping[str, Any]) -> None:
    _check_custom_marker(report, value)
    templates = value.get("templates")
    if not isinstance(templates, dict):
        return
    if not templates:
        report.error(
            "REQUIRED", "value.templates", "value.templates must contain at least one channel"
        )
        return
    for channel, config in templates.items():
        _check_template_channel(report, channel, config)


RESOURCE_CHECKS = {
    "sls.common.user": _check_user,
    "sls.common.user_group": _check_user_group,
    "sls.alert.action_webhook": _check_webhook,
    "sls.alert.action_policy": _check_action_policy,
    "sls.alert.alert_policy": _check_alert_policy,
    "sls.alert.content_template": _check_content_template,
}


def _validate_value(
    resource_name: str, value: Any, purpose: str = "custom-write"
) -> ValidationReport:
    """Validate a decoded ResourceRecord value object."""
    report = ValidationReport(resource_name=resource_name, purpose=purpose)
    if purpose not in {"read", "custom-write"}:
        report.error("INVALID_VALUE", "purpose", "purpose must be read or custom-write")
        return report
    if not isinstance(resource_name, str) or not resource_name.strip():
        report.error("INVALID_VALUE", "resource_name", "resource_name must be a nonempty string")
        return report
    if not isinstance(value, dict):
        report.error("TYPE_MISMATCH", "value", "value must decode to a JSON object")
        return report

    spec = RESOURCE_SPECS.get(resource_name)
    if spec is None:
        report.warn(
            "UNKNOWN_VALUE",
            "resource_name",
            "unknown resource_name; value schema and identity mapping were not checked; verify them before writing",
        )
        return report

    webhook_type = value.get("type")
    if (
        resource_name == "sls.alert.action_webhook"
        and isinstance(webhook_type, str)
        and webhook_type.strip()
        and webhook_type not in WEBHOOK_TYPES
    ):
        spec = ResourceSpec(
            spec.id_field, spec.tag_field, required={"id": str, "name": str, "type": str}
        )
        # The unknown type may define a different value schema. Check only its
        # shared identity; do not guess a field allowlist for that schema.
        identity = {name: value[name] for name in ("id", "name", "type") if name in value}
        _check_common_value(report, spec, identity)
    else:
        _check_common_value(report, spec, value)
    RESOURCE_CHECKS[resource_name](report, value)
    return report


def _unwrap_record(payload):
    if (
        isinstance(payload, dict)
        and "record" in payload
        and not {"id", "tag", "value"}.intersection(payload)
    ):
        payload = payload["record"]
    if not isinstance(payload, dict):
        raise ValueError("record must be a JSON object")
    return payload


class _RecordValueError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _decode_record_value(encoded):
    if not isinstance(encoded, str):
        raise _RecordValueError(
            "TYPE_MISMATCH",
            "record.value must be a JSON string; validate a decoded object with --input-kind value",
        )
    try:
        value = loads(encoded)
    except json.JSONDecodeError as exc:
        raise _RecordValueError(
            "INVALID_JSON",
            "record.value: invalid JSON at line {}, column {}".format(exc.lineno, exc.colno),
        ) from exc
    except ValueError as exc:
        raise _RecordValueError("INVALID_JSON", "record.value: " + str(exc)) from exc
    if isinstance(value, str):
        try:
            nested = loads(value)
        except ValueError:
            nested = None
        if isinstance(nested, dict):
            raise _RecordValueError(
                "DOUBLE_ENCODING", "record.value appears to be double-encoded JSON"
            )
    if not isinstance(value, dict):
        raise _RecordValueError("TYPE_MISMATCH", "record.value must decode to a JSON object")
    return _without_null_fields(value)


def _validate_record(
    resource_name: str, payload: Any, purpose: str = "custom-write"
) -> ValidationReport:
    """Validate a complete ResourceRecord and its encoded value."""
    report = ValidationReport(resource_name=resource_name, purpose=purpose)
    if purpose not in {"read", "custom-write"}:
        report.error("INVALID_VALUE", "purpose", "purpose must be read or custom-write")
        return report
    try:
        record = _unwrap_record(payload)
    except ValueError as exc:
        report.error("TYPE_MISMATCH", "record", str(exc))
        return report

    _check_known_fields(
        report,
        record,
        ("id", "tag", "value", "resource_name", "createTime", "lastModifyTime"),
        "record",
    )

    if "resource_name" in record and record["resource_name"] != resource_name:
        report.error(
            "IDENTITY_MISMATCH",
            "record.resource_name",
            "record.resource_name does not match --resource-name",
        )

    for name in ("id", "tag", "value"):
        if name not in record:
            report.error("REQUIRED", "record.{}".format(name), "record.{} is required".format(name))

    for name in ("id", "tag"):
        item = record.get(name)
        if name in record and not isinstance(item, str):
            report.error(
                "TYPE_MISMATCH", "record.{}".format(name), "record.{} must be a string".format(name)
            )
        elif isinstance(item, str) and not item.strip():
            report.error(
                "REQUIRED", "record.{}".format(name), "record.{} must not be empty".format(name)
            )

    if "value" not in record:
        return report
    try:
        decoded = _decode_record_value(record["value"])
    except _RecordValueError as exc:
        report.error(exc.code, "record.value", str(exc))
        return report

    value_report = _validate_value(resource_name, decoded, purpose=purpose)
    report.errors.extend(value_report.errors)
    report.warnings.extend(value_report.warnings)
    report.id_field = value_report.id_field
    report.tag_field = value_report.tag_field
    report.record_id = value_report.record_id
    report.record_tag = value_report.record_tag

    if (
        isinstance(record.get("id"), str)
        and value_report.record_id is not None
        and record["id"] != value_report.record_id
    ):
        report.error(
            "IDENTITY_MISMATCH",
            "record.id",
            "record.id does not equal value.{}".format(value_report.id_field),
        )
    if (
        isinstance(record.get("tag"), str)
        and value_report.record_tag is not None
        and record["tag"] != value_report.record_tag
    ):
        report.error(
            "IDENTITY_MISMATCH",
            "record.tag",
            "record.tag does not equal value.{}".format(value_report.tag_field),
        )
    return report


def _record_context(payload):
    record = _unwrap_record(payload)
    if not isinstance(record.get("id"), str) or not record["id"].strip():
        raise ValueError("baseline record must have an ID")
    value = _decode_record_value(record["value"])
    # Compare decoded content; wire encoding is checked by record validation.
    return {"record": dict(record, value=value), "value": value}


def _resource_baseline(report, resource_name, payload, purpose, baseline, record):
    if baseline is _NO_BASELINE:
        return report
    validate = _validate_record if record else _validate_value
    try:
        if record:
            previous = _record_context(baseline)
        else:
            if not isinstance(baseline, dict):
                raise ValueError("baseline value must be an object")
            previous = {"value": baseline}
        original = validate(resource_name, baseline, purpose)
        if original.id_field and (
            not isinstance(original.record_id, str) or not original.record_id.strip()
        ):
            raise ValueError("baseline value must have a stable identity")
    except (KeyError, TypeError, ValueError):
        report.error(
            "BASELINE_INVALID",
            "$",
            "Cannot establish an object and identity from the supplied baseline",
        )
        return report
    try:
        current = _record_context(payload) if record else {"value": payload}
    except (KeyError, TypeError, ValueError):
        return report  # Malformed input has already been diagnosed by the validator.
    if record and previous["record"]["id"] != current["record"]["id"]:
        report.error(
            "BASELINE_ID_MISMATCH", "record.id", "Baseline and input must select the same record"
        )
        return report
    if (
        original.record_id is not None
        and report.record_id is not None
        and original.record_id != report.record_id
    ):
        report.error(
            "BASELINE_ID_MISMATCH",
            "value." + original.id_field,
            "Baseline and input must select the same resource value",
        )
        return report
    for context in (current, previous):
        context.update(resource_name=resource_name, purpose=purpose)
    _mark_baseline(
        {"errors": report.errors, "warnings": report.warnings},
        current,
        previous,
        {"errors": original.errors, "warnings": original.warnings},
    )
    return report


def validate_value(resource_name, value, purpose="custom-write", baseline=_NO_BASELINE):
    """Validate a value; an optional baseline only annotates diagnostic origin."""
    value = _without_null_fields(value)
    if baseline is not _NO_BASELINE:
        baseline = _without_null_fields(baseline)
    report = _validate_value(resource_name, value, purpose)
    return _resource_baseline(report, resource_name, value, purpose, baseline, record=False)


def validate_record(resource_name, payload, purpose="custom-write", baseline=_NO_BASELINE):
    """Validate a record; an optional baseline only annotates diagnostic origin."""
    payload = _without_null_fields(payload)
    if baseline is not _NO_BASELINE:
        baseline = _without_null_fields(baseline)
    report = _validate_record(resource_name, payload, purpose)
    return _resource_baseline(report, resource_name, payload, purpose, baseline, record=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    add_input(parser, positional=True)
    add_validation_options(parser)
    parser.add_argument("--input-kind", required=True, choices=("value", "record"))
    parser.add_argument(
        "--purpose",
        choices=("custom-write", "read"),
        default="custom-write",
        help="custom-write checks proposed configuration; read checks service responses",
    )
    parser.add_argument(
        "--resource-name",
        required=True,
        help="SLS resource namespace; unknown types receive only generic checks",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Original JSON in the same input-kind for diagnostic provenance",
    )
    args = parser.parse_args(argv)
    path = resolve_input(parser, args)
    check_output_path(args.output, (path if path != "-" else None, args.baseline))
    try:
        payload = _load_json(path, allow_stdin=True)
        baseline = _load_json(args.baseline, "Baseline") if args.baseline else _NO_BASELINE
    except (ToolError, ValueError) as exc:
        report = ValidationReport(resource_name=args.resource_name, purpose=args.purpose)
        report.error("INPUT_ERROR", "$", str(exc))
    else:
        report = (
            validate_value(args.resource_name, payload, purpose=args.purpose, baseline=baseline)
            if args.input_kind == "value"
            else validate_record(
                args.resource_name, payload, purpose=args.purpose, baseline=baseline
            )
        )
    document = report.to_dict()
    emit(document, args.output)
    return exit_code(document, args.strict)


if __name__ == "__main__":
    raise SystemExit(run(main))
