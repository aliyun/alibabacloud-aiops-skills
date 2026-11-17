#!/usr/bin/env python3
"""Collect guest-side readings for the disk visibility chain, one command at a time.

This is the only entry point in the skill that can deliver a command into a customer
instance. Two hard gates are enforced in code, not in prose:

  1. --confirmed is mandatory. Without it the script exits before any API call, and
     prints exactly what has to be disclosed to the customer first.
  2. --command must match the approved list in _constants.py byte for byte (modulo
     whitespace). Anything else is refused with a reason. The approved list holds no
     command that writes, partitions, formats, mounts, unmounts, brings a volume
     online or restarts anything.

Usage:
    python3 scripts/areas/disk_attach_os_visibility/guest_probe.py --list-commands
    python3 scripts/areas/disk_attach_os_visibility/guest_probe.py --region-id cn-hangzhou --instance-id i-xxx \
        --os linux --command "lsblk -f" --confirmed
    python3 scripts/areas/disk_attach_os_visibility/guest_probe.py --region-id cn-hangzhou --instance-id i-xxx \
        --os linux --default-sequence --confirmed
    python3 scripts/areas/disk_attach_os_visibility/guest_probe.py ... --os linux --command "lsblk -f" --print-only
"""

import argparse
import base64
import binascii
import json
import re
import sys
from typing import Any, Dict, List, Optional

from _cli import CliError, call, call_poll, first_value, mask_secrets, new_session_id
from _constants import (
    CLI_TIMEOUT_SECONDS,
    COMMAND_TYPE_BY_OS,
    ECS_PRODUCT,
    GUEST_COMMAND_WHITELIST_LINUX,
    GUEST_COMMAND_WHITELIST_WINDOWS,
    GUEST_DEFAULT_SEQUENCE_LINUX,
    GUEST_DEFAULT_SEQUENCE_WINDOWS,
    OS_LINUX,
    OS_WINDOWS,
    PROBE_TIMEOUT_SECONDS,
)

DISCLOSURE = (
    "Before this runs, tell the customer, in one message: which single command is about "
    "to be delivered, that it only prints information and changes no data, no partition, "
    "no filesystem and no mount, that it runs inside their instance through Cloud "
    "Assistant, that it is read by the agent once and discarded, and that they may run it "
    "themselves instead and paste the output. Then get an explicit yes for that one "
    "command. Re-confirm for the next command."
)

_WHITESPACE = re.compile(r"\s+")


def normalise(command: str) -> str:
    return _WHITESPACE.sub(" ", command.strip())


def whitelist_for(os_family: str) -> tuple:
    if os_family == OS_LINUX:
        return GUEST_COMMAND_WHITELIST_LINUX
    if os_family == OS_WINDOWS:
        return GUEST_COMMAND_WHITELIST_WINDOWS
    return ()


def is_approved(command: str, os_family: str) -> bool:
    """Only an exact member of the approved list for that OS family is accepted."""
    return normalise(command) in whitelist_for(os_family)


def _params(command: str, instance_id: str, os_family: str) -> Dict[str, Any]:
    cmd_type = COMMAND_TYPE_BY_OS.get(os_family)
    if not cmd_type:
        raise CliError("UnsupportedOs", "no Cloud Assistant command type is mapped for os=%s" % os_family)
    return {
        "Type": cmd_type,
        "Name": "ecs-disk-attach-visibility-probe",
        "Description": "Inspect-only disk visibility probe; changes nothing on the instance.",
        "CommandContent": command,
        "InstanceId.1": instance_id,
        "Timeout": PROBE_TIMEOUT_SECONDS,
        "ContentEncoding": "PlainText",
    }


def _decode_output(value: Any) -> str:
    """Cloud Assistant may hand back the command output base64 wrapped; accept both."""
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        decoded = base64.b64decode(text, validate=True).decode("utf-8", "replace")
    except (binascii.Error, ValueError, UnicodeError):
        return mask_secrets(text)
    return mask_secrets(decoded)


def run_one(command: str, *, region_id: str, instance_id: str, os_family: str, session_id: str,
            timeout: int, poll_timeout: int, dry_run: bool) -> Dict[str, Any]:
    """Deliver one approved command and read its output back."""
    params = _params(command, instance_id, os_family)
    if dry_run:
        preview = call(ECS_PRODUCT, "RunCommand", params, session_id=session_id,
                       region_id=region_id, timeout=timeout, dry_run=True)
        return {"command": command, "dry_run": True, "request": preview}

    invocation = call(ECS_PRODUCT, "RunCommand", params, session_id=session_id,
                      region_id=region_id, timeout=timeout)
    invoke_id = str(first_value(invocation, "InvokeId", default="") or "")

    result: Dict[str, Any] = {
        "command": command,
        "invoke_id": invoke_id,
        "output": "",
        "state": "unknown",
        "errors": [],
    }
    read_params: Dict[str, Any] = {
        "InstanceId": instance_id,
        "IncludeOutput": "true",
        "ContentEncoding": "PlainText",
    }
    if invoke_id:
        read_params["InvokeId"] = invoke_id

    try:
        payload = call_poll("DescribeInvocations", read_params, session_id=session_id,
                            region_id=region_id, deadline_seconds=poll_timeout)
    except CliError as error:
        result["errors"].append("%s: %s" % (error.code, mask_secrets(error.message)))
        result["state"] = "unavailable"
        return result

    outputs: List[str] = []
    states: List[str] = []
    _collect_nested(payload, outputs, states)
    result["output"] = "\n".join(outputs)
    result["state"] = states[-1].lower() if states else "unknown"
    if not outputs:
        result["errors"].append(
            "DescribeInvocations returned no output for this invocation; the Cloud Assistant "
            "agent may be absent, outdated or the command may still be running.")
        result["state"] = "no-output"
    return result


def _collect_nested(node: Any, outputs: List[str], states: List[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).lower()
            if lowered in ("output", "invocationoutput") and isinstance(value, str) and value:
                outputs.append(_decode_output(value))
            elif lowered in ("invocationstatus", "invokestatus") and isinstance(value, str) and value:
                states.append(value)
            else:
                _collect_nested(value, outputs, states)
    elif isinstance(node, list):
        for item in node:
            _collect_nested(item, outputs, states)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deliver one approved inspect-only command into an ECS instance and read it back.")
    parser.add_argument("--region-id", help="Region id of the instance, for example cn-hangzhou.")
    parser.add_argument("--instance-id", help="Instance id, for example i-c00000000000000000.")
    parser.add_argument("--os", choices=(OS_LINUX, OS_WINDOWS),
                        help="Guest family; selects the approved list and the command type. Required "
                             "before anything is delivered, because a wrong guess changes the parsing.")
    parser.add_argument("--command", help="One exact command from the approved list.")
    parser.add_argument("--default-sequence", action="store_true",
                        help="Run the three default visibility commands for this OS family, "
                             "each as its own delivery.")
    parser.add_argument("--confirmed", action="store_true",
                        help="Asserts the customer was told what will run and agreed to this command.")
    parser.add_argument("--print-only", action="store_true",
                        help="Show the request that would be sent; nothing is delivered.")
    parser.add_argument("--list-commands", action="store_true", help="Print the approved list and exit.")
    parser.add_argument("--timeout", type=int, default=CLI_TIMEOUT_SECONDS, help="Seconds per API call.")
    parser.add_argument("--poll-timeout", type=int, default=90,
                        help="Seconds to wait for the command output to come back.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_commands:
        json.dump({
            "linux": list(GUEST_COMMAND_WHITELIST_LINUX),
            "windows": list(GUEST_COMMAND_WHITELIST_WINDOWS),
            "default_sequence_linux": list(GUEST_DEFAULT_SEQUENCE_LINUX),
            "default_sequence_windows": list(GUEST_DEFAULT_SEQUENCE_WINDOWS),
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    def fail(reason: str, hint: str = "", status: str = "REFUSED") -> int:
        json.dump({
            "status": status,
            "reason": reason,
            "disclosure_required": DISCLOSURE,
            "approved_commands": list(whitelist_for(args.os or "")),
            "next_action": hint or DISCLOSURE,
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 3

    if not args.command and not args.default_sequence:
        return fail("Neither --command nor --default-sequence was given.",
                    "Choose one approved command from --list-commands.")
    if not args.region_id or not args.instance_id:
        return fail("Region id and instance id are both required before anything is delivered.",
                    "Ask the customer for the region, then the instance id.")
    if args.os not in (OS_LINUX, OS_WINDOWS):
        return fail("The guest family has not been stated.",
                    "Confirm whether the instance runs Linux or Windows, then pass --os explicitly.")
    if not args.print_only and not args.confirmed:
        return fail("The customer has not been recorded as agreeing to this command.",
                    DISCLOSURE, status="AWAITING_CONFIRMATION")

    if args.default_sequence:
        commands = list(GUEST_DEFAULT_SEQUENCE_LINUX if args.os == OS_LINUX
                        else GUEST_DEFAULT_SEQUENCE_WINDOWS)
    else:
        commands = [args.command or ""]
        if not is_approved(commands[0], args.os):
            return fail(
                "The command is not on the approved list for %s guests." % args.os,
                "Offer the customer these approved commands instead: %s. A command outside "
                "this list is never delivered; the customer may run it by hand and paste the "
                "output." % ", ".join(whitelist_for(args.os)))

    session_id = new_session_id()
    results: List[Dict[str, Any]] = []
    exit_code = 0
    for command in commands:
        try:
            results.append(run_one(command, region_id=args.region_id, instance_id=args.instance_id,
                                   os_family=args.os, session_id=session_id, timeout=args.timeout,
                                   poll_timeout=args.poll_timeout, dry_run=args.print_only))
        except CliError as error:
            exit_code = 4
            results.append({
                "command": command,
                "output": "",
                "state": "error",
                "errors": ["%s: %s" % (error.code, mask_secrets(error.message))],
                "permission_failure": error.is_permission_failure,
            })
            break

    # A read that has not reached a terminal state is not a collected read. Live
    # measurement produced `state=running` with 322 bytes of partial output and the
    # probe still claimed `collected`, which would let the funnel assert a guest
    # finding it never finished reading.
    unsettled = {"running", "pending", "scheduled", "invoking", "stopping",
                 "unknown", "unavailable", "no-output", ""}
    ok = all(not item.get("errors")
             and str(item.get("state", "")).lower() not in unsettled
             for item in results)
    json.dump({
        "status": "OK" if ok and exit_code == 0 else "DEGRADED",
        "result": "collected" if ok and exit_code == 0 else "partially_collected",
        "os_family": args.os,
        "region_id": args.region_id,
        "instance_id": args.instance_id,
        "session_id": session_id,
        "confirmed": bool(args.confirmed),
        "results": results,
        "next_action": ("Feed this output to scripts/areas/disk_attach_os_visibility/ecs_disk_attach_visibility.py --guest-findings "
                        "to finish the chain." if ok else
                        "Report the gap: fall back to asking the customer to run an approved command "
                        "and paste the output."),
    }, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
