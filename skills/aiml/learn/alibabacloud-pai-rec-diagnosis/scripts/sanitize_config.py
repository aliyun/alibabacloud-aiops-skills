#!/usr/bin/env python3
"""
Sanitize PAI-Rec engine configuration by masking sensitive fields.

This script removes credentials (passwords, access keys, tokens, DSN secrets)
from engine configuration JSON before it is displayed or sent to an LLM.

Usage:
    # Sanitize raw CLI JSON output (list-engine-configs / get-engine-config)
    python sanitize_config.py /tmp/raw_config.json

    # Read from stdin
    aliyun pairecservice get-engine-config ... | python sanitize_config.py --stdin

    # Inline JSON string
    python sanitize_config.py '{"ConfigValue": "..."}'

Output:
    Prints sanitized JSON to stdout. Original file is never modified.

Exit codes:
    0: Success
    2: Input error
"""

import json
import re
import sys
import os

# Field name patterns that indicate sensitive values (case-insensitive match)
SENSITIVE_FIELD_PATTERNS = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"accesskey", re.IGNORECASE),
    re.compile(r"accesssecret", re.IGNORECASE),
    re.compile(r"accessid", re.IGNORECASE),
    re.compile(r"secretkey", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
]

# Regex to detect ${...} variable references (these are safe to keep)
ENV_VAR_REF = re.compile(r"^\$\{.+\}$")

# Regex to mask credentials in DSN/connection strings
# Matches: protocol://user:password@host... (greedy to handle @ in passwords)
DSN_CREDENTIAL_PATTERN = re.compile(
    r"((?:postgres|mysql|redis|http|https)://).+(@)"
)

REDACTED = "***REDACTED***"


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field name matches any sensitive pattern."""
    for pattern in SENSITIVE_FIELD_PATTERNS:
        if pattern.search(field_name):
            return True
    return False


def is_env_var_reference(value: str) -> bool:
    """Check if the value is a ${...} environment variable reference."""
    if not isinstance(value, str):
        return False
    return bool(ENV_VAR_REF.match(value.strip()))


def sanitize_dsn(value: str) -> str:
    """Mask credentials in DSN/connection strings."""
    return DSN_CREDENTIAL_PATTERN.sub(rf"\g<1>{REDACTED}:{REDACTED}\2", value)


def sanitize_value(key: str, value):
    """Sanitize a single value based on its field name."""
    if not isinstance(value, str):
        return value

    # Keep ${...} variable references as-is
    if is_env_var_reference(value):
        return value

    # If field name is sensitive, redact the value
    if is_sensitive_field(key):
        return REDACTED

    # Check if the value looks like a DSN with embedded credentials
    if DSN_CREDENTIAL_PATTERN.search(value):
        return sanitize_dsn(value)

    return value


def sanitize_dict(obj: dict) -> dict:
    """Recursively sanitize all sensitive fields in a dictionary."""
    result = {}
    for key, value in obj.items():
        if isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = sanitize_list(key, value)
        elif isinstance(value, str):
            result[key] = sanitize_value(key, value)
        else:
            result[key] = value
    return result


def sanitize_list(parent_key: str, lst: list) -> list:
    """Recursively sanitize items in a list."""
    result = []
    for item in lst:
        if isinstance(item, dict):
            result.append(sanitize_dict(item))
        elif isinstance(item, list):
            result.append(sanitize_list(parent_key, item))
        elif isinstance(item, str):
            result.append(sanitize_value(parent_key, item))
        else:
            result.append(item)
    return result


def sanitize_config_value(config_value_str: str) -> str:
    """Parse and sanitize a ConfigValue JSON string."""
    try:
        config = json.loads(config_value_str)
        if isinstance(config, dict):
            config = sanitize_dict(config)
        return json.dumps(config, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return config_value_str


def sanitize_cli_output(data: dict) -> dict:
    """Sanitize CLI output from list-engine-configs or get-engine-config.

    Handles both:
    - list-engine-configs: {"EngineConfigs": [{"ConfigValue": "...", ...}]}
    - get-engine-config: {"ConfigValue": "...", ...}
    """
    result = dict(data)

    # Handle list-engine-configs response
    if "EngineConfigs" in result and isinstance(result["EngineConfigs"], list):
        sanitized_configs = []
        for ec in result["EngineConfigs"]:
            ec_copy = dict(ec)
            if "ConfigValue" in ec_copy and isinstance(ec_copy["ConfigValue"], str):
                ec_copy["ConfigValue"] = sanitize_config_value(ec_copy["ConfigValue"])
            sanitized_configs.append(ec_copy)
        result["EngineConfigs"] = sanitized_configs
        return result

    # Handle get-engine-config response
    if "ConfigValue" in result and isinstance(result["ConfigValue"], str):
        result["ConfigValue"] = sanitize_config_value(result["ConfigValue"])
        return result

    # Fallback: treat the entire input as a config object
    return sanitize_dict(result)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python sanitize_config.py <json_file>")
        print("       python sanitize_config.py --stdin")
        print("       python sanitize_config.py '{...}' (inline JSON)")
        sys.exit(2)

    arg = sys.argv[1]

    try:
        if arg == "--stdin":
            data = json.load(sys.stdin)
        elif os.path.exists(arg):
            with open(arg, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            try:
                data = json.loads(arg)
            except json.JSONDecodeError:
                print("Error: argument is neither a valid file path nor valid JSON")
                sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"Error: JSON decode failed - {e}")
        sys.exit(2)

    sanitized = sanitize_cli_output(data)
    print(json.dumps(sanitized, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
