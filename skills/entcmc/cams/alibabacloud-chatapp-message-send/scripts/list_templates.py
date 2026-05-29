#!/usr/bin/env python3
"""
List ChatApp message templates

Usage:
    python list_templates.py [--audit-status pass|fail|auditing|unaudit] [--template-type WHATSAPP|VIBER] [--language en|zh_CN|...]

Examples:
    python list_templates.py --audit-status pass --template-type WHATSAPP
    python list_templates.py --template-type WHATSAPP --language zh_CN
"""

import argparse
import json
import subprocess
import sys


def run_cli(args):
    """Execute aliyun CLI command and return parsed JSON"""
    cmd = ["aliyun", "cams", "list-chatapp-template", "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send"]
    cmd.extend(args)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print("Error: CLI command timed out after 60 seconds. Please check your network or try again later.", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        print(f"Error: CLI call failed\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Error: Unable to parse CLI output: {e}\nOutput:\n{result.stdout}", file=sys.stderr)
        sys.exit(1)


def format_template(t):
    """Format a single template entry"""
    code = t.get("TemplateCode", "N/A")
    name = t.get("Name", "N/A")
    lang = t.get("Language", "N/A")
    status = t.get("AuditStatus", "N/A")
    category = t.get("Category", "N/A")
    template_type = t.get("TemplateType", "N/A")

    status_icon = {
        "pass": "[PASS]",
        "fail": "[FAIL]",
        "auditing": "[AUDITING]",
        "unaudit": "[UNAUDIT]",
    }.get(status, status)

    return f"  - {code} | {name} | Language: {lang} | Status: {status_icon} | Category: {category} | {template_type}"


def main():
    parser = argparse.ArgumentParser(description="List ChatApp message templates")
    parser.add_argument("--audit-status", choices=["pass", "fail", "auditing", "unaudit"],
                        help="Filter by audit status: pass, fail, auditing, unaudit")
    parser.add_argument("--template-type", choices=["WHATSAPP", "VIBER"],
                        help="Filter by template type: WHATSAPP or VIBER")
    parser.add_argument("--language", help="Filter by language, e.g. en, zh_CN")
    parser.add_argument("--cust-space-id", help="Space ID under ISV account")
    parser.add_argument("--region", help="Region, e.g. ap-southeast-1")
    parser.add_argument("--page-index", type=int, default=1, help="Page index, default 1")
    parser.add_argument("--page-size", type=int, default=50, help="Page size, default 50")
    args = parser.parse_args()

    cli_args = []
    if args.audit_status:
        cli_args.extend(["--audit-status", args.audit_status])
    if args.template_type:
        cli_args.extend(["--template-type", args.template_type])
    if args.language:
        cli_args.extend(["--biz-language", args.language])
    if args.cust_space_id:
        cli_args.extend(["--cust-space-id", args.cust_space_id])
    if args.region:
        cli_args.extend(["--region", args.region])
    cli_args.extend(["--page", f"Index={args.page_index}", f"Size={args.page_size}"])

    data = run_cli(cli_args)

    templates = data.get("Data", {}).get("List", [])
    total = data.get("Data", {}).get("Total", 0)

    if not templates:
        print("No templates found matching the criteria.")
        return

    print(f"\nFound {total} templates (showing {len(templates)} on this page):\n")
    for t in templates:
        print(format_template(t))
    print()

    # Output concise list for copy-paste
    print("Template code summary (for copy-paste):")
    for t in templates:
        code = t.get("TemplateCode", "N/A")
        name = t.get("Name", "N/A")
        lang = t.get("Language", "N/A")
        print(f"  {code}  ({name}, {lang})")
    print()


if __name__ == "__main__":
    main()
