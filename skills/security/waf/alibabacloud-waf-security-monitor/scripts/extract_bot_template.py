#!/usr/bin/env python3
"""Extract bot_manager template ID from describe-defense-templates response.

Dependencies: Python 3 standard library only (json, sys).

Usage:
    echo "$DESCRIBE_DEFENSE_TEMPLATES_OUTPUT" | python3 scripts/extract_bot_template.py

Input:  JSON from 'aliyun waf-openapi describe-defense-templates' on stdin.
Output: The TemplateId of the first bot_manager template (stdout), or nothing if not found.
Exit 0 on success or no match; exit 1 on invalid input.
"""
import sys
import json

raw = sys.stdin.read().strip()
if not raw:
    print("[ERROR] extract_bot_template: empty input on stdin. Expected JSON from describe-defense-templates.", file=sys.stderr)
    print("  Fix: Ensure describe-defense-templates output is piped to this script, e.g.: echo \"$RESULT\" | python3 scripts/extract_bot_template.py", file=sys.stderr)
    sys.exit(1)

try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    print(f"[ERROR] extract_bot_template: invalid JSON input: {e}", file=sys.stderr)
    print("  Fix: Check that the CLI command succeeded and returned valid JSON. Run: aliyun waf-openapi describe-defense-templates --help", file=sys.stderr)
    sys.exit(1)

templates = data.get('Templates', [])
if not isinstance(templates, list):
    print(f"[ERROR] extract_bot_template: 'Templates' field is not a list, got {type(templates).__name__}", file=sys.stderr)
    print("  Fix: Verify the API response structure. The response should contain a 'Templates' array.", file=sys.stderr)
    sys.exit(1)

for template in templates:
    if template.get('DefenseScene') == 'bot_manager':
        tid = template.get('TemplateId')
        if tid is not None:
            print(tid)
        else:
            print("[ERROR] extract_bot_template: bot_manager template found but missing TemplateId field", file=sys.stderr)
            print("  Fix: Check the template object structure. Expected field 'TemplateId' in the bot_manager template entry.", file=sys.stderr)
        break
