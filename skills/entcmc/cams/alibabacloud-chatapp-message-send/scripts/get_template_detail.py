#!/usr/bin/env python3
"""
Query ChatApp message template detail and variable structure

Usage:
    python get_template_detail.py --template-code <CODE> --language <LANG> [--cust-space-id <ID>]

Examples:
    python get_template_detail.py --template-code hello_world --language en
    python get_template_detail.py --template-code otp_template --language zh_CN --cust-space-id xxx
"""

import argparse
import json
import re
import subprocess
import sys


def run_cli(args):
    """Execute aliyun CLI command and return parsed JSON"""
    cmd = ["aliyun", "cams", "get-chatapp-template-detail", "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send"]
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


def extract_variables(components):
    """Extract variable names from template components"""
    variables = []
    if not isinstance(components, list):
        return variables

    for comp in components:
        comp_type = comp.get("Type", "").lower()
        text = comp.get("Text", "")
        # WhatsApp template variable format: {{1}}, {{2}}, etc.
        found = re.findall(r"\{\{(\d+)\}\}", text)
        for v in found:
            variables.append({
                "index": v,
                "type": comp_type,
                "example": comp.get("Example", ""),
                "text_preview": text[:80] + "..." if len(text) > 80 else text
            })
    return variables


def main():
    parser = argparse.ArgumentParser(description="Query ChatApp message template detail")
    parser.add_argument("--template-code", required=True, help="Template code")
    parser.add_argument("--language", required=True, help="Template language, e.g. en, zh_CN")
    parser.add_argument("--cust-space-id", help="Space ID under ISV account (required for some scenarios)")
    parser.add_argument("--template-type", default="WHATSAPP", choices=["WHATSAPP", "VIBER"],
                        help="Template type, default WHATSAPP")
    args = parser.parse_args()

    cli_args = [
        "--template-code", args.template_code,
        "--biz-language", args.language,
        "--template-type", args.template_type,
    ]
    if args.cust_space_id:
        cli_args.extend(["--cust-space-id", args.cust_space_id])

    data = run_cli(cli_args)

    template = data.get("Data", {})
    if not template:
        print("No template details retrieved.")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    print("\n========== Template Detail ==========\n")
    print(f"Template Code:    {template.get('TemplateCode', 'N/A')}")
    print(f"Template Name:    {template.get('Name', 'N/A')}")
    print(f"Language:         {template.get('Language', 'N/A')}")
    print(f"Audit Status:     {template.get('AuditStatus', 'N/A')}")
    print(f"Category:         {template.get('Category', 'N/A')}")
    print(f"Type:             {template.get('TemplateType', 'N/A')}")

    components = template.get("Components", [])
    print(f"\nComponent Count:  {len(components)}")

    variables = extract_variables(components)
    if variables:
        print("\n---------- Template Variables ----------")
        print("This template contains the following variables. Provide values when sending:\n")
        for v in variables:
            print(f"  Variable {{ {v['index']} }}")
            print(f"    Component:  {v['type']}")
            if v['example']:
                print(f"    Example:    {v['example']}")
            print(f"    Text preview: {v['text_preview']}")
            print()
        print("When sending, use --template-params to specify variable values, e.g.:")
        params = " ".join([f"{v['index']}=value{v['index']}" for v in variables])
        print(f"  --template-params {params}")
    else:
        print("\nThis template has no variables.")

    print("\n---------- Full Component Structure ----------")
    print(json.dumps(components, indent=2, ensure_ascii=False))
    print()


if __name__ == "__main__":
    main()
