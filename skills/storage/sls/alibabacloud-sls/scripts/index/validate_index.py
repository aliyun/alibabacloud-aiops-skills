#!/usr/bin/env python3
"""Validate a writable SLS index configuration locally.

Usage:
    python3 scripts/index/validate_index.py --input FILE
"""

import argparse
import sys
from decimal import Decimal
from pathlib import Path


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common.cli import add_input, add_validation_options, resolve_input
from _common.json_io import ToolError, check_output_path, load
from _common.reports import emit, exit_code, input_error, result, run


ROOT_FIELDS = {
    "line": "object",
    "keys": "object",
    "scan_index": "boolean",
    "max_text_len": "integer",
    "log_reduce": "boolean",
    "log_reduce_white_list": "strings",
    "log_reduce_black_list": "strings",
}
LINE_FIELDS = {
    "token": "strings",
    "caseSensitive": "boolean",
    "chn": "boolean",
    "auto_key_detect": "boolean",
    "auto_text_keys": "strings",
    "include_keys": "strings",
    "exclude_keys": "strings",
}
JSON_FIELD_FIELDS = {
    "type": "string",
    "alias": "string",
    "doc_value": "boolean",
    "caseSensitive": "boolean",
    "chn": "boolean",
    "token": "strings",
}
FIELD_FIELDS = {
    **JSON_FIELD_FIELDS,
    "index_all": "boolean",
    "max_depth": "integer",
    "json_keys": "object",
    "embedding": "string",
    "vector_index": "string",
}
RESPONSE_FIELDS = {"ttl", "index_mode", "lastModifyTime", "storage"}


def field_path(parent, key):
    """JSON Pointer paths keep dynamic field names unambiguous."""
    return parent + "/" + key.replace("~", "~0").replace("/", "~1")


def validate_index(config):
    errors = []

    def issue(code, path, message):
        errors.append({"code": code, "path": path, "message": message})

    def check_type(value, kind, path):
        valid = {
            "object": isinstance(value, dict),
            "string": isinstance(value, str),
            "integer": type(value) is int,
            "boolean": type(value) is bool,
            "strings": isinstance(value, list),
        }[kind]
        if not valid:
            issue(
                "TYPE_MISMATCH",
                path,
                "Expected " + ("an array of strings" if kind == "strings" else kind),
            )
            return False
        if kind == "strings":
            for index, item in enumerate(value):
                if not isinstance(item, str):
                    issue("TYPE_MISMATCH", path + "/" + str(index), "Expected string")
        return True

    def check_object(value, fields, required, path):
        if not check_type(value, "object", path):
            return False
        for key in required:
            if key not in value:
                issue("REQUIRED_FIELD", field_path(path, key), "Required field is missing")
        for key in sorted(value):
            location = field_path(path, key)
            if path == "" and key in RESPONSE_FIELDS:
                issue(
                    "RESPONSE_ONLY_FIELD",
                    location,
                    "Keep this response metadata in the backup, not the writable configuration",
                )
            elif key not in fields:
                issue("UNKNOWN_FIELD", location, "Field is not recognized by this validator")
            else:
                check_type(value[key], fields[key], location)
        return True

    def check_field(value, path, leaf=False):
        fields = JSON_FIELD_FIELDS if leaf else FIELD_FIELDS
        if not check_object(value, fields, ("type",), path):
            return
        kind = value.get("type")
        if isinstance(kind, str):
            if not kind.strip():
                issue("EMPTY_VALUE", path + "/type", "Field type must not be empty")
            elif kind not in (
                ("text", "long", "double") if leaf else ("text", "long", "double", "json")
            ):
                issue(
                    "UNSUPPORTED_TYPE",
                    path + "/type",
                    "Field type is outside this validator's known types",
                )
        if not leaf and isinstance(value.get("json_keys"), dict):
            for name in sorted(value["json_keys"]):
                check_field(
                    value["json_keys"][name], field_path(path + "/json_keys", name), leaf=True
                )

    if check_object(config, ROOT_FIELDS, (), ""):
        if not any(key in config for key in ("line", "keys", "scan_index")):
            issue("MISSING_INDEX_SECTION", "", "Provide line, keys or scan_index")
        if "line" in config and isinstance(config["line"], dict):
            check_object(config["line"], LINE_FIELDS, ("token",), "/line")
            include_keys = config["line"].get("include_keys")
            exclude_keys = config["line"].get("exclude_keys")
            if (
                isinstance(include_keys, list)
                and include_keys
                and isinstance(exclude_keys, list)
                and exclude_keys
            ):
                issue(
                    "MUTUALLY_EXCLUSIVE_FIELDS",
                    "/line",
                    "include_keys and exclude_keys must not both be non-empty",
                )
        if isinstance(config.get("keys"), dict):
            for name in sorted(config["keys"]):
                check_field(config["keys"][name], field_path("/keys", name))
    return result(errors)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    add_input(parser, positional=True)
    add_validation_options(parser)
    args = parser.parse_args(argv)
    path = resolve_input(parser, args)
    check_output_path(args.output, (path if path != "-" else None,))
    try:
        config = load(path, allow_stdin=True, parse_float=Decimal)
        report = validate_index(config)
    except (ToolError, ValueError) as exc:
        report = input_error(exc)
    emit(report, args.output)
    return exit_code(report, args.strict)


if __name__ == "__main__":
    raise SystemExit(run(main))
