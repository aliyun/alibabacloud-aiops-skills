#!/usr/bin/env python3
"""FlowSpec Validation Tool

Validates DataWorks node/workflow directories or spec.json files.

Dependency: jsonschema>=4.0,<5.0 (optional, for JSON Schema validation)

Usage:
    python validate.py <path>              # Validate a directory or file
    python validate.py <path> --json       # Output in JSON format
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    jsonschema = None

# Skill root directory (relative to this script's location)
SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = SKILL_ROOT / "assets" / "schemas"


class ValidationResult:
    def __init__(self, path):
        self.path = str(path)
        self.errors = []
        self.warnings = []

    def error(self, field, message, fix=None):
        entry = {"field": field, "message": message}
        if fix:
            entry["fix"] = fix
        self.errors.append(entry)

    def warning(self, field, message):
        self.warnings.append({"field": field, "message": message})

    @property
    def valid(self):
        return len(self.errors) == 0

    def to_dict(self):
        return {
            "valid": self.valid,
            "path": self.path,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def to_text(self):
        lines = [f"Validation: {self.path}", ""]
        for e in self.errors:
            lines.append(f"  ❌ {e['field']}: {e['message']}")
            if "fix" in e:
                lines.append(f"     Fix: {e['fix']}")
        for w in self.warnings:
            lines.append(f"  ⚠️  {w['field']}: {w['message']}")
        lines.append("")
        lines.append(f"Result: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return "\n".join(lines)


def load_json_schema(kind):
    """Load FlowSpec JSON Schema"""
    schema_map = {
        "Node": "Node.schema.json",
        "CycleWorkflow": "CycleWorkflow.schema.json",
        "ManualWorkflow": "ManualWorkflow.schema.json",
    }
    filename = schema_map.get(kind)
    if not filename:
        return None
    schema_path = SCHEMAS_DIR / "flowspec" / filename
    if not schema_path.exists():
        return None
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_properties(props_path):
    """Parse dataworks.properties file"""
    props = {}
    if not props_path.exists():
        return None
    with open(props_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                props[key.strip()] = value.strip()
    return props


def find_spec_file(directory):
    """Find *.spec.json file in the directory"""
    spec_files = list(directory.glob("*.spec.json"))
    if len(spec_files) == 1:
        return spec_files[0]
    if len(spec_files) > 1:
        # Prefer the one matching the directory name
        dir_name = directory.name
        for sf in spec_files:
            if sf.stem.replace(".spec", "") == dir_name:
                return sf
        return spec_files[0]
    return None


def validate_spec_json(spec_path, result):
    """Validate a spec.json file"""
    # 1. Read and parse JSON
    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            spec_data = json.load(f)
    except json.JSONDecodeError as e:
        result.error("spec.json", f"JSON parse failed: {e}", "Check that the JSON format is correct")
        return None

    # 2. JSON Schema validation
    kind = spec_data.get("kind")
    if not kind:
        result.error("kind", "Missing kind field", 'Add "kind": "Node" or "CycleWorkflow" or "ManualWorkflow"')
        return None

    if jsonschema:
        schema = load_json_schema(kind)
        if schema:
            try:
                jsonschema.validate(spec_data, schema)
            except jsonschema.ValidationError as e:
                path_str = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
                result.error(f"schema({path_str})", str(e.message)[:200])

    return spec_data


def validate_node(spec_data, spec_path, directory, result):
    """Validate a Node type spec"""
    if not spec_data or spec_data.get("kind") != "Node":
        return

    nodes = spec_data.get("spec", {}).get("nodes", [])
    if not nodes:
        result.error("spec.nodes", "Node list is empty", "Define at least one node")
        return

    for i, node in enumerate(nodes):
        prefix = f"spec.nodes[{i}]"

        # Timeout default value warning
        timeout = node.get("timeout")
        timeout_unit = node.get("timeoutUnit", "HOURS")
        if timeout == 4 and timeout_unit == "HOURS":
            result.warning(
                f"{prefix}.timeout",
                "Timeout is set to the default value of 4 hours",
            )

        # Trigger format check
        trigger = node.get("trigger")
        if trigger:
            if trigger.get("type") == "Scheduler" and not trigger.get("cron"):
                result.error(
                    f"{prefix}.trigger.cron",
                    "Scheduler type trigger is missing a cron expression",
                    'Add "cron": "00 00 00 * * ?"',
                )


def validate_workflow(spec_data, result):
    """Validate a Workflow type spec"""
    kind = spec_data.get("kind", "")
    if kind not in ("CycleWorkflow", "ManualWorkflow"):
        return

    workflows = spec_data.get("spec", {}).get("workflows", [])
    if not workflows:
        result.error("spec.workflows", "Workflow list is empty", "Define at least one workflow")
        return

    for i, wf in enumerate(workflows):
        prefix = f"spec.workflows[{i}]"
        if not wf.get("name"):
            result.error(f"{prefix}.name", "Workflow name cannot be empty")

        if kind == "CycleWorkflow":
            trigger = wf.get("trigger")
            if trigger and trigger.get("type") == "Scheduler" and not trigger.get("cron"):
                result.error(
                    f"{prefix}.trigger.cron",
                    "Cycle workflow Scheduler trigger is missing a cron expression",
                )


def validate_properties(directory, result):
    """Validate dataworks.properties"""
    props_path = directory / "dataworks.properties"

    # 8. properties exists
    if not props_path.exists():
        result.error(
            "dataworks.properties",
            "dataworks.properties file does not exist",
            f"Create file {props_path}",
        )
        return

    props = parse_properties(props_path)
    if props is None:
        return

    placeholder_pattern = re.compile(r"\$\{[^}]+\}")
    valid_prefixes = ("spec.", "script.", "projectIdentifier")

    for key, value in props.items():
        # 9. No placeholders in value
        if placeholder_pattern.search(value):
            result.error(
                f"dataworks.properties[{key}]",
                f'Value contains placeholder: "{value}"',
                f"Replace the value of {key} with an actual value",
            )

        # 10. Key prefix convention
        if not any(key.startswith(p) for p in valid_prefixes):
            result.error(
                f"dataworks.properties[{key}]",
                f'Key has non-standard prefix: "{key}"',
                'Key must start with "spec." or "script." (except "projectIdentifier")',
            )


def validate_directory(directory, result, recursive=True):
    """Validate a node/workflow directory"""
    directory = Path(directory)

    # Find spec.json
    spec_file = find_spec_file(directory)
    if not spec_file:
        result.error("*.spec.json", "No .spec.json file found in directory", "Create a <name>.spec.json file")
        return

    # Validate spec.json
    spec_data = validate_spec_json(spec_file, result)
    if not spec_data:
        return

    kind = spec_data.get("kind", "")

    if kind == "Node":
        validate_node(spec_data, spec_file, directory, result)
        validate_properties(directory, result)
    elif kind in ("CycleWorkflow", "ManualWorkflow"):
        validate_workflow(spec_data, result)
        validate_properties(directory, result)

        # Recursively validate child node directories
        if recursive:
            for subdir in sorted(directory.iterdir()):
                if subdir.is_dir() and find_spec_file(subdir):
                    sub_result = ValidationResult(subdir)
                    validate_directory(subdir, sub_result, recursive=False)
                    result.errors.extend(sub_result.errors)
                    result.warnings.extend(sub_result.warnings)


def validate_file(file_path, result):
    """Validate a single spec.json file"""
    spec_data = validate_spec_json(file_path, result)
    if not spec_data:
        return

    kind = spec_data.get("kind", "")
    directory = Path(file_path).parent

    if kind == "Node":
        validate_node(spec_data, file_path, directory, result)
    elif kind in ("CycleWorkflow", "ManualWorkflow"):
        validate_workflow(spec_data, result)


def main():
    parser = argparse.ArgumentParser(description="FlowSpec Validation Tool")
    parser.add_argument("path", help="Path to directory or .spec.json file to validate")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    result = ValidationResult(args.path)

    if target.is_dir():
        validate_directory(target, result)
    elif target.is_file():
        validate_file(target, result)
        # Also check properties in the same directory
        if target.suffix == ".json":
            validate_properties(target.parent, result)
    else:
        result.error("path", f"Path does not exist: {args.path}")

    # Output
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.to_text())

    sys.exit(0 if result.valid else 1)


if __name__ == "__main__":
    main()
