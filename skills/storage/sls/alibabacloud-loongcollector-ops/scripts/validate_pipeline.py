#!/usr/bin/env python3
"""validate_pipeline.py — static validation of a Logtail pipeline config.

Checks the rendered config against the hard rules in references/pipeline-config.md,
references/plugin-version-gates.yaml and references/index-coupling.md WITHOUT calling
any cloud API. Meant to run before `aliyun sls create/update-logtail-pipeline-config`.

Rules enforced:
  P0  inputs/processors/flushers are arrays of plugin objects with Type
  P1  exactly 1 input
  P2  exactly 1 flusher, Type == flusher_sls, with Logstore
  P3  native and extended processors not mixed in one config
  P4  SPL (processor_spl) cannot coexist with native/extended
  P5  version gate: <2.0 forbids native+extended mix & non-parse first processor;
      =2.0 requires extended only after all native; major<2 forbids *_native/spl
  P6  IC-002 self-collection risk: strict processor (NoMatchError/NoKeyError true)
      without KeepingSourceWhenParseFail -> warn
  P7  index coupling: processors add/rename fields but no index_update provided -> warn
  P8  processor_rename uses equal non-empty SourceKeys/DestKeys string arrays
  P9  processor_json has SourceKey and emits unprefixed fields for index coupling

Protocol: stdout = single JSON object {tool,status,errors,warnings};
          stderr = diagnostics; exit 0 valid (may warn), 1 invalid (errors), 2 usage.

Usage:
  python3 scripts/validate_pipeline.py --file rendered.json [--collector-version 3.4.0]
                                        [--index-provided]
  cat rendered.json | python3 scripts/validate_pipeline.py
"""
import argparse
import json
import os
import sys

NATIVE_SUFFIX = "_native"
EXTENDED_PREFIX = "processor_"          # extended processors are processor_* but NOT *_native/spl
SPL_TYPE = "processor_spl"
PARSE_FIRST_NATIVE = {
    "processor_parse_regex_native", "processor_parse_delimiter_native",
    "processor_parse_json_native", "processor_parse_apsara_native",
}
FIELD_MUTATING = ("processor_parse_", "processor_json", "processor_regex",
                  "processor_rename", "processor_grok")
ALLOWED_INPUT_TYPES = {"input_file", "input_container_stdio"}
ALLOWED_PROCESSOR_TYPES = {
    "processor_parse_json_native",
    "processor_parse_regex_native",
    "processor_parse_delimiter_native",
    "processor_parse_timestamp_native",
    "processor_parse_apsara_native",
    "processor_filter_regex_native",
    "processor_desensitize_native",
    "processor_json",
    "processor_regex",
    "processor_filter_regex",
    "processor_grok",
    "processor_rename",
    "processor_spl",
}
ALLOWED_FLUSHER_TYPES = {"flusher_sls"}


def die(msg, code=2):
    sys.stderr.write("[validate_pipeline] %s\n" % msg)
    sys.exit(code)


def classify(ptype):
    if ptype == SPL_TYPE:
        return "spl"
    if ptype.endswith(NATIVE_SUFFIX):
        return "native"
    if ptype.startswith(EXTENDED_PREFIX):
        return "extended"
    return "unknown"


def major_version(ver):
    if not ver:
        return None
    try:
        return int(str(ver).split(".")[0])
    except ValueError:
        return None


def parse_version_tuple(ver):
    try:
        return tuple(int(x) for x in str(ver).split(".")[:3])
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--file", help="rendered config JSON; omit to read stdin")
    ap.add_argument("--collector-version", default=os.environ.get("COLLECTOR_VERSION", ""))
    ap.add_argument("--index-provided", action="store_true",
                    help="set when an index update diff is included in the same batch")
    args = ap.parse_args()

    raw = ""
    if args.file:
        if not os.path.isfile(args.file):
            die("file not found: %s" % args.file)
        with open(args.file, "r", encoding="utf-8") as fh:
            raw = fh.read()
    else:
        raw = sys.stdin.read()
    if not raw.strip():
        die("empty input")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        die("input is not valid JSON: %s" % e)

    # accept either a bare config or render_pipeline output {config:{...}}
    config = doc.get("config") if isinstance(doc, dict) and "config" in doc else doc
    if not isinstance(config, dict):
        die("could not locate a config object")

    errors, warnings = [], []
    inputs = config.get("inputs") or []
    flushers = config.get("flushers") or []
    processors = config.get("processors") or []
    for field_name, plugins in (
        ("inputs", inputs),
        ("processors", processors),
        ("flushers", flushers),
    ):
        if not isinstance(plugins, list):
            errors.append({"id": "P0", "msg": "%s must be an array" % field_name})
    inputs = inputs if isinstance(inputs, list) else []
    processors = processors if isinstance(processors, list) else []
    flushers = flushers if isinstance(flushers, list) else []
    for field_name, plugins, prefix, allowed_types in (
        ("inputs", inputs, "input_", ALLOWED_INPUT_TYPES),
        ("processors", processors, "processor_", ALLOWED_PROCESSOR_TYPES),
        ("flushers", flushers, "flusher_", ALLOWED_FLUSHER_TYPES),
    ):
        for position, plugin in enumerate(plugins):
            if not isinstance(plugin, dict):
                errors.append({
                    "id": "P0",
                    "msg": "%s[%d] must be an object" % (field_name, position),
                })
                continue
            plugin_type = plugin.get("Type")
            if not isinstance(plugin_type, str) or not plugin_type.startswith(prefix):
                errors.append({
                    "id": "P0",
                    "msg": "%s[%d].Type must start with %s"
                    % (field_name, position, prefix),
                })
            elif plugin_type not in allowed_types:
                errors.append({
                    "id": "P0",
                    "msg": "%s[%d].Type is unsupported in this skill: %s"
                    % (field_name, position, plugin_type),
                })
    inputs = [plugin for plugin in inputs if isinstance(plugin, dict)]
    processors = [plugin for plugin in processors if isinstance(plugin, dict)]
    flushers = [plugin for plugin in flushers if isinstance(plugin, dict)]

    # P1
    if len(inputs) != 1:
        errors.append({"id": "P1", "msg": "exactly 1 input required, got %d" % len(inputs)})
    # P2
    if len(flushers) != 1:
        errors.append({"id": "P2", "msg": "exactly 1 flusher required, got %d" % len(flushers)})
    else:
        fl = flushers[0]
        if fl.get("Type") != "flusher_sls":
            errors.append({"id": "P2", "msg": "flusher Type must be flusher_sls, got %r" % fl.get("Type")})
        elif not fl.get("Logstore"):
            errors.append({"id": "P2", "msg": "flusher_sls missing Logstore"})

    kinds = [classify(p.get("Type", "")) for p in processors]
    has_native = "native" in kinds
    has_extended = "extended" in kinds
    has_spl = "spl" in kinds

    # P3
    if has_native and has_extended:
        errors.append({"id": "P3", "msg": "native and extended processors cannot be mixed in one config"})
    # P4
    if has_spl and (has_native or has_extended):
        errors.append({"id": "P4", "msg": "processor_spl cannot coexist with native/extended processors"})

    # P5 version gates
    vt = parse_version_tuple(args.collector_version)
    mj = major_version(args.collector_version)
    if vt is None:
        warnings.append({"id": "P5", "msg": "collector version unknown; resolve via list-machines .binary before applying version-gated plugins"})
    else:
        if vt < (2, 0):
            if has_native and has_extended:
                errors.append({"id": "P5", "msg": "<2.0 forbids mixing native + extended plugins"})
            if processors and classify(processors[0].get("Type", "")) == "native" \
               and processors[0].get("Type") not in PARSE_FIRST_NATIVE:
                warnings.append({"id": "P5", "msg": "<2.0 first processor must be a parse plugin (regex/delimiter/json/nginx/apache/iis)"})
        if mj is not None and mj < 2:
            for p in processors:
                t = p.get("Type", "")
                if t.endswith(NATIVE_SUFFIX) or t == SPL_TYPE:
                    errors.append({"id": "P5", "msg": "collector major <2 does not support %s; use 1.x extended chain" % t})
        if vt >= (2, 0) and mj == 2 and has_native and has_extended:
            # order rule: extended only after all native
            first_ext = next((i for i, k in enumerate(kinds) if k == "extended"), None)
            last_nat = max((i for i, k in enumerate(kinds) if k == "native"), default=-1)
            if first_ext is not None and first_ext < last_nat:
                errors.append({"id": "P5", "msg": "=2.0 requires extended processors to appear after all native processors"})

    # P6 self-collection risk
    for p in processors:
        strict = p.get("NoMatchError") is True or p.get("NoKeyError") is True
        keeps_parse_fail = (
            p.get("KeepingSourceWhenParseFail") is True
            or p.get("KeepSourceIfParseError") is True
        )
        if strict and not keeps_parse_fail:
            warnings.append({"id": "P6", "msg": "%s strict-mode without KeepingSourceWhenParseFail risks REGEX_UNMATCHED storm / self-collection (IC-002)" % p.get("Type")})

    # P7 index coupling
    mutates = any(str(p.get("Type", "")).startswith(FIELD_MUTATING) for p in processors)
    if mutates and not args.index_provided:
        warnings.append({"id": "P7", "msg": "processors add/rename fields; emit index update diff in the SAME batch (index-coupling.md), or pass --index-provided"})

    # P8/P9 processor-specific contracts
    for p in processors:
        ptype = p.get("Type", "")
        if ptype == "processor_rename_native":
            errors.append({"id": "P8", "msg": "processor_rename_native does not exist; use extended processor_rename"})
        if ptype == "processor_rename":
            if "SourceKey" in p or "DestKey" in p:
                errors.append({"id": "P8", "msg": "processor_rename requires plural SourceKeys and DestKeys arrays"})
            source_keys = p.get("SourceKeys")
            dest_keys = p.get("DestKeys")
            source_valid = (
                isinstance(source_keys, list)
                and bool(source_keys)
                and all(isinstance(item, str) and item for item in source_keys)
            )
            dest_valid = (
                isinstance(dest_keys, list)
                and bool(dest_keys)
                and all(isinstance(item, str) and item for item in dest_keys)
            )
            if not source_valid or not dest_valid:
                errors.append({"id": "P8", "msg": "processor_rename SourceKeys/DestKeys must be non-empty string arrays"})
            elif len(source_keys) != len(dest_keys):
                errors.append({"id": "P8", "msg": "processor_rename SourceKeys and DestKeys must have equal lengths"})
        if ptype == "processor_json":
            if not isinstance(p.get("SourceKey"), str) or not p.get("SourceKey"):
                errors.append({"id": "P9", "msg": "processor_json requires a non-empty SourceKey"})
            if p.get("Prefix") != "" or p.get("UseSourceKeyAsPrefix") is not False:
                warnings.append({"id": "P9", "msg": "processor_json should use Prefix=\"\" and UseSourceKeyAsPrefix=false so index field names match parsed fields"})

    # P9 canonical JSON parse contract when its output feeds processor_rename
    for rename_position, processor in enumerate(processors):
        if processor.get("Type") != "processor_rename":
            continue
        json_processors = [
            item
            for item in processors[:rename_position]
            if item.get("Type") == "processor_json"
        ]
        if not json_processors:
            continue
        json_processor = json_processors[-1]
        required_values = {
            "Prefix": "",
            "NoKeyError": False,
            "KeepSource": False,
            "KeepSourceIfParseError": True,
            "UseSourceKeyAsPrefix": False,
        }
        for field, expected in required_values.items():
            if json_processor.get(field) != expected:
                errors.append({
                    "id": "P9",
                    "msg": "processor_json before processor_rename requires %s=%r"
                    % (field, expected),
                })

    status = "invalid" if errors else "valid"
    out = {
        "tool": "validate_pipeline",
        "session_id": os.environ.get("SKILL_SESSION_ID", ""),
        "status": status,
        "collector_version": args.collector_version or None,
        "processor_kinds": kinds,
        "errors": errors,
        "warnings": warnings,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
