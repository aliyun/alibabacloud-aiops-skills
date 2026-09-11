#!/usr/bin/env python3
"""Validate an SLS notification resource value or ResourceRecord locally.

Usage: python3 scripts/validate_resource.py --input-kind value|record --resource-name NAME [--purpose custom-write|read] [--json] FILE
Use - as FILE to read JSON from stdin.
"""

from __future__ import print_function

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple
from urllib.parse import urlparse


@dataclass(frozen=True)
class ResourceSpec:
    display_name: str
    id_field: str
    tag_field: str
    required: Mapping[str, type]
    optional: Mapping[str, type] = field(default_factory=dict)


@dataclass
class ValidationReport:
    resource_name: str
    purpose: str = "custom-write"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    id_field: Optional[str] = None
    tag_field: Optional[str] = None
    record_id: Optional[str] = None
    record_tag: Optional[str] = None

    @property
    def valid(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


RESOURCE_SPECS: Dict[str, ResourceSpec] = {
    "sls.common.user": ResourceSpec(
        display_name="user",
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
        display_name="user group",
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
        display_name="Webhook integration",
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
        display_name="action policy",
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
        display_name="alert policy",
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
        display_name="content template",
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


def _check_string_list(
    report: ValidationReport, value: Any, path: str, warn_if_empty: bool = False
) -> None:
    if not isinstance(value, list):
        return
    for index, item in enumerate(value):
        if not isinstance(item, str):
            report.error("{}[{}] must be a string".format(path, index))
        elif not item.strip():
            report.error("{}[{}] must not be empty".format(path, index))
    if len(value) != len({item for item in value if isinstance(item, str)}):
        report.warn("{} contains duplicate entries".format(path))
    if warn_if_empty and not value:
        report.warn("{} is empty; the resource has no resolved recipients".format(path))


def _check_common_value(
    report: ValidationReport, spec: ResourceSpec, value: Mapping[str, Any]
) -> None:
    for name, expected in spec.required.items():
        if name not in value:
            report.error("value.{} is required".format(name))
        elif not _matches_type(value[name], expected):
            report.error("value.{} must be a {}".format(name, _type_name(expected)))

    for name, expected in spec.optional.items():
        if name in value and not _matches_type(value[name], expected):
            report.error("value.{} must be a {}".format(name, _type_name(expected)))

    for name in (spec.id_field, spec.tag_field):
        item = value.get(name)
        if isinstance(item, str) and not item.strip():
            report.error("value.{} must not be empty".format(name))

    report.id_field = spec.id_field
    report.tag_field = spec.tag_field
    if isinstance(value.get(spec.id_field), str):
        report.record_id = value[spec.id_field]
    if isinstance(value.get(spec.tag_field), str):
        report.record_tag = value[spec.tag_field]

    for metadata_field in ("createTime", "lastModifyTime"):
        if metadata_field in value:
            report.warn(
                "value.{} is response metadata and should not be sent as desired state".format(
                    metadata_field
                )
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
        report.warn("the user has no nonempty email address or phone number")
    if value.get("sms_enabled") is True and not has_phone:
        report.warn("sms_enabled is true but value.phone is empty")
    if value.get("voice_enabled") is True:
        if not has_phone:
            report.warn("voice_enabled is true but value.phone is empty")
        if value.get("country_code") != "86":
            report.warn(
                "voice delivery currently requires country_code 86; service acceptance is not tested locally"
            )


def _check_user_group(report: ValidationReport, value: Mapping[str, Any]) -> None:
    _check_string_list(
        report, value.get("members"), "value.members", warn_if_empty=True
    )


def _check_webhook(report: ValidationReport, value: Mapping[str, Any]) -> None:
    webhook_type = value.get("type")
    if not isinstance(webhook_type, str):
        return  # The common value checks report the missing or invalid type.
    if not webhook_type.strip():
        report.error("value.type must not be empty")
        return
    if webhook_type not in WEBHOOK_TYPES:
        report.warn("unknown Webhook type; type-specific checks were skipped; verify its schema before writing")
        return

    url = value.get("url")
    if isinstance(url, str):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            report.error("value.url must be an absolute HTTP or HTTPS URL")

    method = value.get("method")
    headers = value.get("headers")
    if webhook_type in {"dingtalk", "wechat", "lark", "slack"}:
        if method != "POST":
            report.error("value.method must be POST for a non-custom Webhook")
        if isinstance(headers, list) and headers:
            report.error("value.headers must be empty for a non-custom Webhook")

    if isinstance(headers, list):
        for index, header in enumerate(headers):
            path = "value.headers[{}]".format(index)
            if not isinstance(header, dict):
                report.error("{} must be an object".format(path))
                continue
            for field_name in ("key", "value"):
                item = header.get(field_name)
                if not isinstance(item, str):
                    report.error("{}.{} must be a string".format(path, field_name))
                elif field_name == "key" and not item.strip():
                    report.error("{}.key must not be empty".format(path))

    if "secret" in value and webhook_type not in {"dingtalk", "lark"}:
        report.warn("value.secret is documented only for DingTalk and Lark")


def _check_custom_marker(report: ValidationReport, value: Mapping[str, Any]) -> None:
    if report.purpose == "custom-write" and value.get("is_default") is True:
        report.error("value.is_default must be false for a custom resource payload")


def _check_action_policy(report: ValidationReport, value: Mapping[str, Any]) -> None:
    _check_custom_marker(report, value)
    labels = value.get("labels")
    if report.purpose == "custom-write" and isinstance(labels, dict) and labels:
        report.error("value.labels is reserved and must be an empty object")

    for name in ("primary_policy_script", "secondary_policy_script"):
        script = value.get(name)
        if isinstance(script, str) and not script.strip():
            report.error("value.{} must not be empty".format(name))

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
                    "value.{} must not be empty when value.{} is true".format(
                        timeout_field, enabled_field
                    )
                )


def _check_alert_policy(report: ValidationReport, value: Mapping[str, Any]) -> None:
    _check_custom_marker(report, value)
    group_script = value.get("group_script")
    if isinstance(group_script, str) and not group_script.strip():
        report.error("value.group_script must not be empty")


def _check_template_channel(
    report: ValidationReport, channel: str, config: Any
) -> None:
    path = "value.templates.{}".format(channel)
    if not isinstance(config, dict):
        report.error("{} must be an object".format(path))
        return

    required = TEMPLATE_CHANNELS.get(channel)
    if required is None:
        report.warn(
            "{} is not known to this validator; its fields were preserved but not checked".format(
                path
            )
        )
        return

    for field_name in required:
        if field_name not in config:
            report.error("{}.{} is required".format(path, field_name))

    for field_name in ("locale", "subject", "title", "content", "send_type"):
        if field_name in config and not isinstance(config[field_name], str):
            report.error("{}.{} must be a string".format(path, field_name))
    if "limit" in config and not _matches_type(config["limit"], int):
        report.error("{}.limit must be an integer".format(path))
    elif isinstance(config.get("limit"), int) and config["limit"] < 0:
        report.error("{}.limit must be greater than or equal to zero".format(path))

    locale = config.get("locale")
    if isinstance(locale, str):
        if not locale.strip():
            report.error("{}.locale must not be empty".format(path))
        elif locale not in {"zh-CN", "en-US"}:
            report.warn("{}.locale is not known to this validator; service support was not checked".format(path))

    send_type = config.get("send_type")
    if isinstance(send_type, str) and send_type not in {"single", "batch"}:
        report.warn(
            "{}.send_type is not single or batch; preserve it only when it came from a verified service record".format(
                path
            )
        )


def _check_content_template(report: ValidationReport, value: Mapping[str, Any]) -> None:
    _check_custom_marker(report, value)
    templates = value.get("templates")
    if not isinstance(templates, dict):
        return
    if not templates:
        report.error("value.templates must contain at least one channel")
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


def validate_value(
    resource_name: str, value: Any, purpose: str = "custom-write"
) -> ValidationReport:
    """Validate a decoded ResourceRecord value object."""
    report = ValidationReport(resource_name=resource_name, purpose=purpose)
    if purpose not in {"read", "custom-write"}:
        report.error("purpose must be read or custom-write")
        return report
    if not isinstance(resource_name, str) or not resource_name.strip():
        report.error("resource_name must be a nonempty string")
        return report
    if not isinstance(value, dict):
        report.error("value must decode to a JSON object")
        return report

    spec = RESOURCE_SPECS.get(resource_name)
    if spec is None:
        report.warn("unknown resource_name; value schema and identity mapping were not checked; verify them before writing")
        return report

    webhook_type = value.get("type")
    if (resource_name == "sls.alert.action_webhook"
            and isinstance(webhook_type, str) and webhook_type.strip()
            and webhook_type not in WEBHOOK_TYPES):
        spec = ResourceSpec(spec.display_name, spec.id_field, spec.tag_field,
                            required={"id": str, "name": str, "type": str})

    _check_common_value(report, spec, value)
    RESOURCE_CHECKS[resource_name](report, value)
    return report


def validate_record(
    resource_name: str, payload: Any, purpose: str = "custom-write"
) -> ValidationReport:
    """Validate a complete ResourceRecord and its encoded value."""
    report = ValidationReport(resource_name=resource_name, purpose=purpose)
    if purpose not in {"read", "custom-write"}:
        report.error("purpose must be read or custom-write")
        return report
    if not isinstance(payload, dict):
        report.error("record input must be a JSON object")
        return report

    record = payload
    if "record" in payload and not {"id", "tag", "value"}.intersection(payload):
        candidate = payload.get("record")
        if not isinstance(candidate, dict):
            report.error("record must be a JSON object")
            return report
        record = candidate

    if "resource_name" in record and record["resource_name"] != resource_name:
        report.error("record.resource_name does not match --resource-name")

    for name in ("id", "tag", "value"):
        if name not in record:
            report.error("record.{} is required".format(name))

    for name in ("id", "tag"):
        item = record.get(name)
        if name in record and not isinstance(item, str):
            report.error("record.{} must be a string".format(name))
        elif isinstance(item, str) and not item.strip():
            report.error("record.{} must not be empty".format(name))

    encoded = record.get("value")
    if "value" not in record:
        return report
    if not isinstance(encoded, str):
        report.error(
            "record.value must be a JSON string; validate a decoded object with --input-kind value"
        )
        return report

    try:
        decoded = json.loads(encoded)
    except json.JSONDecodeError as exc:
        report.error(
            "record.value is not valid JSON: line {}, column {}".format(
                exc.lineno, exc.colno
            )
        )
        return report

    if isinstance(decoded, str):
        try:
            decoded_twice = json.loads(decoded)
        except (json.JSONDecodeError, TypeError):
            decoded_twice = None
        if isinstance(decoded_twice, dict):
            report.error("record.value appears to be double-encoded JSON")
        else:
            report.error("record.value must decode to a JSON object")
        return report

    value_report = validate_value(resource_name, decoded, purpose=purpose)
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
        report.error("record.id does not equal value.{}".format(value_report.id_field))
    if (
        isinstance(record.get("tag"), str)
        and value_report.record_tag is not None
        and record["tag"] != value_report.record_tag
    ):
        report.error(
            "record.tag does not equal value.{}".format(value_report.tag_field)
        )
    return report


def _load_json(path: str) -> Any:
    if path == "-":
        text = sys.stdin.read()
    else:
        text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "input is not valid JSON: line {}, column {}".format(exc.lineno, exc.colno)
        )


def _report_as_json(report: ValidationReport) -> str:
    return json.dumps(
        {
            "valid": report.valid,
            "resource_name": report.resource_name,
            "purpose": report.purpose,
            "identity_mapping": {
                "id_field": report.id_field,
                "tag_field": report.tag_field,
                "id": report.record_id,
                "tag": report.record_tag,
            },
            "errors": report.errors,
            "warnings": report.warnings,
        },
        ensure_ascii=False,
        indent=2,
    )


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="Validate an SLS resource value or record")
    parser.add_argument("--input-kind", required=True, choices=("value", "record"))
    parser.add_argument(
        "--purpose", choices=("custom-write", "read"), default="custom-write",
        help="custom-write checks desired state; read accepts built-in markers",
    )
    parser.add_argument(
        "--resource-name",
        required=True,
        help="SLS resource namespace; unknown types receive only generic checks",
    )
    parser.add_argument("input", help="JSON file, or - to read JSON from stdin")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable report; it includes derived id and tag",
    )
    args = parser.parse_args()
    input_kind = args.input_kind

    try:
        payload = _load_json(args.input)
    except (OSError, ValueError) as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "valid": False,
                        "resource_name": args.resource_name,
                        "identity_mapping": None,
                        "errors": [str(exc)],
                        "warnings": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print("ERROR: {}".format(exc), file=sys.stderr)
        return 1

    report = (
        validate_value(args.resource_name, payload, purpose=args.purpose)
        if input_kind == "value"
        else validate_record(args.resource_name, payload, purpose=args.purpose)
    )
    if args.json:
        print(_report_as_json(report))
    else:
        for warning in report.warnings:
            print("WARNING: {}".format(warning), file=sys.stderr)
        for error in report.errors:
            print("ERROR: {}".format(error), file=sys.stderr)
        if report.valid:
            print(
                "OK: local checks passed for {} {}; review warnings".format(
                    args.resource_name,
                    "value" if input_kind == "value" else "record",
                )
            )
            if report.id_field is not None and report.tag_field is not None:
                print(
                    "Mapping: record.id <- value.{}, record.tag <- value.{}".format(
                        report.id_field, report.tag_field
                    )
                )
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
