#!/usr/bin/env python3
"""
Send ChatApp messages (WhatsApp / Viber)

This script wraps `aliyun cams send-chatapp-message` and supports:
  - Template messages: requires template code, language, and variables
  - Custom messages: requires message type and content JSON

Usage:
    # Template message
    python send_chatapp_message.py send-template \
        --from "86138xxxx" --to "86139xxxx" \
        --template-code hello_world --language en \
        --template-params 1=Alice 2=Bob

    # Custom text message
    python send_chatapp_message.py send-message \
        --from "86138xxxx" --to "86139xxxx" \
        --message-type text \
        --content '{"text":"Hello, this is a test message"}'

    # Preview only without sending (--dry-run)
    python send_chatapp_message.py send-template ... --dry-run
"""

import argparse
import json
import subprocess
import sys
import time


def run_cli(cmd_args, dry_run=False):
    """Execute aliyun CLI command"""
    cmd = ["aliyun", "cams", "send-chatapp-message", "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send"]
    cmd.extend(cmd_args)

    if dry_run:
        print("\n[Dry Run] Command to be executed:")
        print(" ".join(cmd))
        print()
        return {"DryRun": True, "Command": " ".join(cmd)}

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


def confirm_send(details):
    """Confirm with user before sending"""
    print("\n========== Pre-send Confirmation ==========")
    for key, value in details.items():
        print(f"  {key}: {value}")
    print("============================================")

    try:
        ans = input("\nConfirm send? Please type yes to proceed: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nSend cancelled.")
        sys.exit(0)

    if ans != "yes":
        print("Send cancelled.")
        sys.exit(0)


def build_template_params(params_list):
    """Convert ['1=value1', '2=value2'] to CLI format"""
    return ["--template-params"] + params_list


def validate_phone(phone):
    """Validate phone number format: must be pure numeric digits, no '+'"""
    if not phone:
        print("Error: Phone number cannot be empty", file=sys.stderr)
        sys.exit(1)
    if phone.startswith("+"):
        print(f"Error: Phone number '{phone}' format incorrect. API requires pure numeric format without '+'", file=sys.stderr)
        print("Correct examples: 8613800000000 (China), 14100000000 (US)", file=sys.stderr)
        sys.exit(1)
    if not phone.isdigit():
        print(f"Error: Phone number '{phone}' contains invalid characters. Only pure digits allowed", file=sys.stderr)
        sys.exit(1)


def validate_json(content):
    """Validate JSON format"""
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error: Content is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)


def run_cli_query(cmd_args):
    """Execute aliyun CLI query command and return parsed JSON"""
    cmd = ["aliyun", "cams", "list-chatapp-message", "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send"]
    cmd.extend(cmd_args)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print("Warning: Duplicate check query timed out, proceeding with send.", file=sys.stderr)
        return None
    if result.returncode != 0:
        print(f"Warning: Duplicate check query failed, proceeding with send.\n{result.stderr}", file=sys.stderr)
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def check_duplicate_message(from_num, to_num, content, message_type, cust_space_id=None, region=None):
    """Check if a duplicate message was recently sent using check-then-act idempotency.

    Queries recent messages (within the last 5 minutes) sent from `from_num` to `to_num`.
    If a message with identical content and type is found, returns its MessageId.
    Returns None if no duplicate is found.
    """
    # Query messages from the last 5 minutes
    now_ms = int(time.time() * 1000)
    five_min_ago_ms = now_ms - 5 * 60 * 1000

    cli_args = [
        "--channel-type", "whatsapp",
        "--from", from_num,
        "--to", to_num,
        "--business-number", from_num,
        "--start-time", str(five_min_ago_ms),
        "--end-time", str(now_ms),
        "--page", "Index=1", "Size=10",
    ]
    if cust_space_id:
        cli_args.extend(["--cust-space-id", cust_space_id])
    if region:
        cli_args.extend(["--region", region])

    data = run_cli_query(cli_args)
    if not data or not data.get("Data"):
        return None

    # Parse content for comparison
    try:
        sent_content = json.loads(content) if isinstance(content, str) else content
    except (json.JSONDecodeError, TypeError):
        sent_content = {"raw": content}

    # Look for matching DOWN message with same content and type
    for msg in data["Data"]:
        if msg.get("EventAction") != "DOWN":
            continue
        if msg.get("MessageType", "").upper() != message_type.upper():
            continue
        msg_data = msg.get("Message", "")
        try:
            msg_content = json.loads(msg_data) if isinstance(msg_data, str) else msg_data
        except (json.JSONDecodeError, TypeError):
            msg_content = {"raw": msg_data}
        if msg_content == sent_content:
            return msg.get("MessageId")

    return None


def cmd_send_template(args):
    """Send a template message"""
    validate_phone(args.from_num)
    validate_phone(args.to_num)

    details = {
        "Message Type": "Template Message",
        "Channel": args.channel_type,
        "From": args.from_num,
        "To": args.to_num,
        "Template Code": args.template_code,
        "Template Language": args.language,
        "Template Variables": args.template_params or "(none)",
    }
    if args.cust_space_id:
        details["Space ID"] = args.cust_space_id

    if not args.yes:
        confirm_send(details)

    cli_args = [
        "--channel-type", args.channel_type,
        "--type", "template",
        "--from", args.from_num,
        "--to", args.to_num,
        "--template-code", args.template_code,
        "--biz-language", args.language,
    ]

    if args.template_params:
        cli_args.extend(build_template_params(args.template_params))
    if args.task_id:
        cli_args.extend(["--task-id", args.task_id])

    if args.cust_space_id:
        cli_args.extend(["--cust-space-id", args.cust_space_id])
    if args.region:
        cli_args.extend(["--region", args.region])

    result = run_cli(cli_args, dry_run=args.dry_run)
    print("\nSend result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_send_message(args):
    """Send a custom message"""
    validate_phone(args.from_num)
    validate_phone(args.to_num)
    validate_json(args.content)

    details = {
        "Message Type": "Custom Message",
        "Channel": args.channel_type,
        "From": args.from_num,
        "To": args.to_num,
        "Content Type": args.message_type,
        "Content": args.content,
    }
    if args.cust_space_id:
        details["Space ID"] = args.cust_space_id

    if not args.yes:
        confirm_send(details)

    # Check-then-act: verify no duplicate message was recently sent
    dup_msg_id = check_duplicate_message(
        args.from_num, args.to_num,
        args.content, args.message_type,
        cust_space_id=args.cust_space_id, region=args.region
    )
    if dup_msg_id:
        print(f"\nDuplicate detected: A message with identical content was already sent (MessageId: {dup_msg_id}).")
        print("Skipping send to prevent duplicate delivery.")
        print(json.dumps({"Code": "OK", "Message": "Duplicate skipped", "ExistingMessageId": dup_msg_id}, indent=2, ensure_ascii=False))
        return

    cli_args = [
        "--channel-type", args.channel_type,
        "--type", "message",
        "--from", args.from_num,
        "--to", args.to_num,
        "--message-type", args.message_type,
        "--content", args.content,
    ]
    if args.task_id:
        cli_args.extend(["--task-id", args.task_id])

    if args.cust_space_id:
        cli_args.extend(["--cust-space-id", args.cust_space_id])
    if args.region:
        cli_args.extend(["--region", args.region])

    result = run_cli(cli_args, dry_run=args.dry_run)
    print("\nSend result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Send ChatApp messages")
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Template message subcommand
    tmpl_parser = subparsers.add_parser("send-template", help="Send a template message")
    tmpl_parser.add_argument("--from", dest="from_num", required=True, help="Sender phone number, numeric digits only (e.g. 8613867404376, no +)")
    tmpl_parser.add_argument("--to", dest="to_num", required=True, help="Recipient phone number, numeric with country code (e.g. 8619521605234, no +)")
    tmpl_parser.add_argument("--channel-type", default="whatsapp", choices=["whatsapp", "viber"], help="Channel type, default whatsapp")
    tmpl_parser.add_argument("--template-code", required=True, help="Template code")
    tmpl_parser.add_argument("--language", required=True, help="Template language, e.g. en, zh_CN")
    tmpl_parser.add_argument("--template-params", nargs="+", help="Template variables, format: 1=value1 2=value2 ...")
    tmpl_parser.add_argument("--cust-space-id", help="Space ID under ISV account")
    tmpl_parser.add_argument("--region", help="Region, e.g. cn-hangzhou, ap-southeast-1")
    tmpl_parser.add_argument("--task-id", help="Custom task ID passed to API as-is (no auto-generation)")
    tmpl_parser.add_argument("--dry-run", action="store_true", help="Preview command only, do not actually send")
    tmpl_parser.add_argument("--yes", action="store_true", help="Skip confirmation and send directly")
    tmpl_parser.set_defaults(func=cmd_send_template)

    # Custom message subcommand
    msg_parser = subparsers.add_parser("send-message", help="Send a custom message")
    msg_parser.add_argument("--from", dest="from_num", required=True, help="Sender phone number, numeric digits only (e.g. 8613867404376, no +)")
    msg_parser.add_argument("--to", dest="to_num", required=True, help="Recipient phone number, numeric with country code (e.g. 8619521605234, no +)")
    msg_parser.add_argument("--channel-type", default="whatsapp", choices=["whatsapp", "viber"], help="Channel type, default whatsapp")
    msg_parser.add_argument("--message-type", required=True,
                            choices=["text", "image", "video", "audio", "document", "interactive",
                                     "contacts", "location", "sticker", "reaction"],
                            help="Message content type")
    msg_parser.add_argument("--content", required=True, help="Message content JSON string")
    msg_parser.add_argument("--cust-space-id", help="Space ID under ISV account")
    msg_parser.add_argument("--region", help="Region, e.g. cn-hangzhou, ap-southeast-1")
    msg_parser.add_argument("--task-id", help="Custom task ID passed to API as-is (no auto-generation)")
    msg_parser.add_argument("--dry-run", action="store_true", help="Preview command only, do not actually send")
    msg_parser.add_argument("--yes", action="store_true", help="Skip confirmation and send directly")
    msg_parser.set_defaults(func=cmd_send_message)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
