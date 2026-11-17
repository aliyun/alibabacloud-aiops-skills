#!/usr/bin/env python3
"""Gated in-guest evidence collection through Cloud Assistant.

This module owns the ONLY side-effecting call this skill is allowed to make:
the consent-gated Cloud Assistant `run-command` dispatch (Class B - the
underlying API is `RunCommand`; no grant is declared in this skill's policy, it
runs only under the customer's own credentials), which dispatches ONE exact command from the guest inspection
whitelist (see _constants.GUEST_WHITELIST_LINUX / GUEST_WHITELIST_WINDOWS) into
the customer's instance. Dispatching a command is why this skill makes no
observation-only claim about itself; what the dispatched commands do is inspect
state only --
top, ps, free, vmstat, uptime, sar, iostat, atop -r, Get-Process, Get-Counter.
The command text itself is never allowed to touch files, services, power state
or configuration: the exact-template whitelist and the side-effect blocklist
are both enforced here before anything is sent, and a rejected command is
turned into manual guidance, never rewritten and retried.

Confirmation gate (mandatory, enforced in this order):
  1. The caller (the Agent) MUST present to the customer, verbatim: the exact
     command, the target instance id, that the command only inspects state and
     changes nothing inside the instance, and whether it can be reversed
     (dispatching it can be cancelled by not running; the reading itself is
     harmless).
  2. The customer MUST approve THIS run. The entry script then invokes this
     module with --confirmation "<quote of the approval>" -- the module refuses
     an empty, placeholder or self-asserted confirmation.
  3. Approval covers exactly ONE whitelisted command. A second command needs a
     second run with a second quote. No standing or batch authorization.

Results are read back with the DescribeInvocations API call (returns
historical execution results, not a live stream); this is the only way to get
process-level readings, since no cloud query API exposes in-guest process CPU
or memory. Output is credential-masked before it is printed or parsed.

Run its offline self-test:  python3 scripts/areas/resource_bottleneck/guest_evidence.py --self-test
"""

import argparse
import base64
import json
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from _cli import CliError, mask_credentials, new_session_id, run_cli
from _constants import (
    ACTION_DESCRIBE_INVOCATIONS,
    ACTION_RUN_COMMAND,
    CODE_IMPLICIT_DENY,
    CODE_NO_PERMISSION,
    COMMAND_BLOCK_SUBSTRINGS,
    GUEST_WHITELIST_LINUX,
    GUEST_WHITELIST_WINDOWS,
    INVOCATION_POLL_INTERVAL_SECONDS,
    INVOCATION_POLL_MAX,
    PRODUCT_ECS,
    RUNCOMMAND_CONTENT_ENCODING,
    RUNCOMMAND_TIMEOUT_SECONDS,
    RUNSCRIPT_LINUX,
    RUNSCRIPT_WINDOWS,
)

_PLACEHOLDER_CONFIRMATIONS = ("", "yes", "ok", "confirm", "confirmed", "approved",
                              "y", "auto", "true")

_TERMINAL_STATUSES = (
    "finished", "success", "failed", "error", "timeout", "cancelled",
    "stopped", "partialfailed", "invalid", "aborted",
)


def validate_guest_command(command: str, os_type: str) -> Tuple[bool, str, str]:
    """Decide whether ONE command may be dispatched into the guest.

    Returns ``(allowed, reason, purpose)``. Acceptance requires BOTH: the
    command fullmatches one whitelist template (exact template, not prefix or
    substring), and it contains none of the side-effect block substrings.
    """
    stripped = (command or "").strip()
    if not stripped:
        return False, "empty command", ""
    if "\n" in stripped or "\r" in stripped:
        return False, "multi-line input: exactly one command per confirmed run", ""
    if any(token in stripped for token in COMMAND_BLOCK_SUBSTRINGS):
        return False, (
            "command contains a file-, process-, service- or configuration-"
            "mutating token; dispatching it here is prohibited, output manual "
            "guidance instead"
        ), ""
    templates = GUEST_WHITELIST_WINDOWS if (os_type or "").lower() == "windows" \
        else GUEST_WHITELIST_LINUX
    for pattern, purpose in templates:
        if pattern.fullmatch(stripped):
            return True, "matched exact whitelist template", purpose
    family = "Windows" if (os_type or "").lower() == "windows" else "Linux"
    return False, (
        "not an exact {0} whitelist template (see references/resource-bottleneck__guest-commands.md); "
        "fuzzy matches are rejected".format(family)
    ), ""


def is_valid_confirmation(text: Optional[str]) -> bool:
    """Reject empty or placeholder confirmations; the quote must be real."""
    return (text or "").strip().lower() not in _PLACEHOLDER_CONFIRMATIONS


def dispatch_command(
    region_id: str, instance_id: str, command: str, os_type: str,
    session_id: str, timeout: int, warnings: Optional[List[str]] = None,
) -> str:
    """Send one already-whitelisted command via RunCommand; return InvokeId."""
    run_type = RUNSCRIPT_WINDOWS if (os_type or "").lower() == "windows" else RUNSCRIPT_LINUX
    payload = run_cli(
        PRODUCT_ECS, ACTION_RUN_COMMAND,
        params={
            "RegionId": region_id,
            "Type": run_type,
            "CommandContent": base64.b64encode(command.encode("utf-8")).decode("ascii"),
            "ContentEncoding": RUNCOMMAND_CONTENT_ENCODING,
            "InstanceId.1": instance_id,
            "Name": "skill-ecs-resource-bottleneck",
            "Description": "gated single whitelisted inspection command",
            "Timeout": RUNCOMMAND_TIMEOUT_SECONDS,
        },
        session_id=session_id, timeout=timeout, warnings=warnings,
    )
    invoke_id = payload.get("InvokeId")
    if not invoke_id:
        raise CliError("ResponseParseError", "RunCommand returned no InvokeId", retryable=False)
    return str(invoke_id)


def fetch_invocation(
    region_id: str, invoke_id: str, instance_id: str,
    session_id: str, timeout: int, warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Read back one dispatched command's result via DescribeInvocations."""
    payload = run_cli(
        PRODUCT_ECS, ACTION_DESCRIBE_INVOCATIONS,
        params={
            "RegionId": region_id,
            "InvokeId": invoke_id,
            "IncludeOutput": "true",
        },
        session_id=session_id, timeout=timeout, warnings=warnings,
    )
    invocations = (payload.get("Invocations") or {}).get("Invocation") or []
    record: Dict[str, Any] = {}
    for invocation in invocations:
        if isinstance(invocation, dict):
            record = invocation
            break
    if not record:
        return {"terminal": False, "status": "not-returned", "output": "",
                "exit_code": None, "error_info": "no invocation record returned yet"}
    instances = (record.get("InvokeInstances") or {}).get("InvokeInstance") or []
    instance_record: Dict[str, Any] = {}
    for item in instances:
        if isinstance(item, dict) and str(item.get("InstanceId", "")) == instance_id:
            instance_record = item
            break
    if not instance_record and instances and isinstance(instances[0], dict):
        instance_record = instances[0]
    status = str(instance_record.get("InvocationStatus")
                 or record.get("InvokeStatus") or "unknown")
    raw_output = instance_record.get("Output") or ""
    output = _decode_output(raw_output)
    exit_code = instance_record.get("ExitCode")
    error_info = instance_record.get("ErrorInfo") or ""
    return {
        "terminal": status.lower().replace(" ", "") in _TERMINAL_STATUSES,
        "status": status,
        "output": output,
        "exit_code": exit_code,
        "error_info": mask_credentials(error_info),
    }


def _decode_output(raw: str) -> str:
    """Cloud Assistant output is base64; fall back to the raw text."""
    if not raw:
        return ""
    try:
        decoded = base64.b64decode(raw, validate=True).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - any decoding miss falls back to raw
        decoded = raw
    return mask_credentials(decoded)


def collect_guest_evidence(
    region_id: str, instance_id: str, command: str, os_type: str,
    confirmation: Optional[str], session_id: str, timeout: int,
    warnings: List[str],
) -> Dict[str, Any]:
    """The full gated path: confirm -> validate -> dispatch -> poll -> read back."""
    result: Dict[str, Any] = {
        "attempted": True, "command": command, "status": "unknown",
        "output": "", "error": None, "reject_reason": None,
    }
    if not is_valid_confirmation(confirmation):
        result["status"] = "rejected"
        result["reject_reason"] = (
            "no verbatim customer approval supplied for THIS run. The gate is: "
            "present the exact command, target instance, its inspect-only nature "
            "and reversibility to the customer, get their approval, then re-run "
            "with --confirmation quoting it."
        )
        return result
    allowed, reason, purpose = validate_guest_command(command, os_type)
    if not allowed:
        result["status"] = "rejected"
        result["reject_reason"] = reason
        return result
    result["purpose"] = purpose
    try:
        invoke_id = dispatch_command(
            region_id, instance_id, command, os_type, session_id, timeout, warnings)
        result["invoke_id"] = invoke_id
    except CliError as exc:
        result["status"] = "dispatch-failed"
        result["error"] = str(exc)
        if exc.code in (CODE_NO_PERMISSION, CODE_IMPLICIT_DENY):
            result["error"] += (
                " -- Cloud Assistant dispatch needs the RunCommand API under the "
                "customer's own credentials (gated, no declared grant); the reading "
                "itself would also need the guest agent online."
            )
        return result

    poll_timeout = max(timeout, INVOCATION_POLL_INTERVAL_SECONDS + 5)
    record: Dict[str, Any] = {}
    for _ in range(INVOCATION_POLL_MAX):
        try:
            record = fetch_invocation(
                region_id, invoke_id, instance_id, session_id,
                poll_timeout, warnings)
        except CliError as exc:
            result["status"] = "readback-failed"
            result["error"] = str(exc)
            return result
        if record.get("terminal"):
            break
        time.sleep(INVOCATION_POLL_INTERVAL_SECONDS)
    result["status"] = record.get("status", "unknown")
    result["output"] = record.get("output", "")
    result["exit_code"] = record.get("exit_code")
    if record.get("error_info"):
        result["error_info"] = record["error_info"]
    return result


def parse_guest_findings(output: str, cpu_count: Optional[int] = None) -> List[Dict[str, str]]:
    """Extract reportable signals from guest command output. Pure function."""
    findings: List[Dict[str, str]] = []
    if not output:
        return findings
    lowered = output.lower()
    if "kswapd" in lowered:
        findings.append({
            "id": "G-KSWAPD", "level": "high", "rule": "R1",
            "text": "guest output shows kswapd paging activity: memory pressure, "
                    "not CPU demand, is driving the reading (rule R1).",
        })
    if "out of memory" in lowered or "oom" in lowered or "oom-killer" in lowered:
        findings.append({
            "id": "G-OOM", "level": "high", "rule": "R1",
            "text": "guest output contains an out-of-memory / OOM killer trace; "
                    "memory exhaustion reached process-kill level.",
        })
    if "blocked for more than" in lowered:
        findings.append({
            "id": "G-BLOCKED", "level": "high", "rule": "R4",
            "text": "guest log shows a task blocked for more than the hung-task "
                    "limit: the blocked process is the victim of I/O pressure, "
                    "not the cause (rule R4, ticket T-BF2F77A0).",
        })
    if "possible syn flooding" in lowered:
        findings.append({
            "id": "G-SYN", "level": "info", "rule": "R9",
            "text": "kernel 'Possible SYN flooding' notice seen: it reports a "
                    "full half-connection queue, not a defect by itself (rule "
                    "R9, ticket T-F5D78C4B); judge with bandwidth and connection "
                    "counts.",
        })
    load = _extract_load(output)
    if load and cpu_count:
        # _extract_load yields numeric strings (each already float()-validated);
        # coerce before dividing or a plain "load average: x, y, z" line from the
        # gated uptime/top capture raises TypeError and aborts the whole diagnosis.
        ratio = float(load[0]) / max(1, cpu_count)
        findings.append({
            "id": "G-LOAD", "level": "info", "rule": "R2/R3",
            "text": "guest load average {0} on {1} vCPU(s): runnable/queued work "
                    "is {2:.1f}x the core count (caliber: /proc style 1-min "
                    "value).".format("/".join(load), cpu_count, ratio),
        })
    for pid_line in _top_cpu_lines(output):
        findings.append({"id": "G-TOP", "level": "info", "rule": "R2", "text": pid_line})
    return findings


def _extract_load(output: str) -> Optional[List[str]]:
    marker = "load average"
    index = output.lower().find(marker)
    if index == -1:
        return None
    tail = output[index + len(marker): index + len(marker) + 40]
    numbers: List[str] = []
    for token in tail.replace(":", " ").replace(",", " ").split():
        try:
            float(token)
        except ValueError:
            continue
        numbers.append(token)
        if len(numbers) == 3:
            break
    return numbers or None


def _top_cpu_lines(output: str, limit: int = 5) -> List[str]:
    """Pull the busiest process lines out of a `top -bn1`/`ps aux` capture.

    Deliberately conservative: the process NAME is quoted (customers repeatedly
    misremembered which process it was, e.g. php vs beam.smp in ticket
    T-88D2167B) but no interpretation of what the process is happens here.
    """
    lines: List[str] = []
    for raw in output.splitlines():
        if len(lines) >= limit:
            break
        columns = raw.split()
        if len(columns) < 10:
            continue
        cpu_pct = _percent(columns[8]) if _looks_like_top(columns) else _percent(columns[2])
        if cpu_pct is None or cpu_pct < 50.0:
            continue
        command = columns[-1] if _looks_like_top(columns) else " ".join(columns[10:])
        lines.append(
            "guest process line shows {0} at {1:.0f}% of a processor ({2}) "
            "-- confirm with the business whether this process and volume are "
            "expected.".format(command, cpu_pct, raw.strip()[:90]))
    return lines


def _looks_like_top(columns: List[str]) -> bool:
    try:
        int(columns[0])
        return columns[1].isdigit() or columns[1].isalpha()
    except (ValueError, IndexError):
        return False


def _percent(token: str) -> Optional[float]:
    try:
        return float(token.rstrip("%"))
    except (TypeError, ValueError):
        return None


# --- offline self-test of the pure decision functions ------------------------
def _self_test() -> int:
    ok, _reason, _purpose = validate_guest_command("uptime", "linux")
    assert ok
    ok, _reason, _p2 = validate_guest_command("top -bn1", "linux")
    assert ok
    ok, _reason, _p3 = validate_guest_command("ps aux --sort=-%cpu | head -n 10", "linux")
    assert ok
    ok, _reason, _p4 = validate_guest_command("atop -r /var/log/atop/atop_20260826 -b 0810 -e 0930", "linux")
    assert ok
    ok, reason, _p5 = validate_guest_command("Get-Process | Sort-Object CPU -Descending | Select-Object -First 10", "Windows")
    assert ok, reason
    # rejections: mutation, chaining, fuzzy, empty, multi-line
    assert not validate_guest_command("top -bn1 > /tmp/out", "linux")[0]
    assert not validate_guest_command("uptime && free -m", "linux")[0]
    assert not validate_guest_command("kill -9 1234", "linux")[0]
    assert not validate_guest_command("top -bn2", "linux")[0]
    assert not validate_guest_command("top", "linux")[0]
    assert not validate_guest_command("", "linux")[0]
    assert not validate_guest_command("uptime\nfree -m", "linux")[0]
    assert not validate_guest_command("swapon -a", "linux")[0]
    # confirmation gate: placeholders are not confirmations
    assert not is_valid_confirmation(None)
    assert not is_valid_confirmation(" yes ")
    assert not is_valid_confirmation("")
    assert is_valid_confirmation("customer replied: go ahead and run top -bn1 on i-abc")
    # guest findings parsing (normal / empty / garbage)
    assert parse_guest_findings("") == []
    findings = parse_guest_findings(
        "  PID USER ... 12.3 kswapd0\nload average: 8.02, 6.45, 4.21\n"
        " 1122 root  20  0  99  0.5 java -jar app.jar", cpu_count=2)
    ids = [item["id"] for item in findings]
    assert "G-KSWAPD" in ids and "G-LOAD" in ids
    # the load ratio must be numeric arithmetic (8.02 / 2 vCPU = 4.0x), never a
    # str/int TypeError on the real gated uptime/top output shape
    load_text = next(item["text"] for item in findings if item["id"] == "G-LOAD")
    assert "4.0x" in load_text and "8.02/6.45/4.21" in load_text, load_text
    assert parse_guest_findings("garbage", cpu_count=None) == []
    assert _percent("42.0") == 42.0 and _percent("x") is None
    print("guest_evidence self-test passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guest_evidence.py",
        description=(
            "Gated in-guest evidence module: dispatches exactly ONE whitelisted "
            "inspection command through Cloud Assistant, only after the "
            "customer's approval for this run is quoted via --confirmation."
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="run offline checks and exit")
    parser.add_argument("--region-id", dest="region_id")
    parser.add_argument("--instance-id", dest="instance_id")
    parser.add_argument("--os-type", dest="os_type", default="linux")
    parser.add_argument("--command", dest="command")
    parser.add_argument("--confirmation", dest="confirmation")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--json", action="store_true", help="render JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    if not all((args.region_id, args.instance_id, args.command)):
        parser.error("--region-id, --instance-id and --command are required "
                     "(or use --self-test)")
    session_id = new_session_id()
    warnings: List[str] = []
    result = collect_guest_evidence(
        args.region_id, args.instance_id, args.command, args.os_type,
        args.confirmation, session_id, max(1, args.timeout), warnings)
    if args.json:
        print(json.dumps({"session_id": session_id, "warnings": warnings, **result},
                         ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("guest evidence (gated Cloud Assistant dispatch)")
        print("  session  : {0}".format(session_id))
        print("  command  : {0}".format(mask_credentials(args.command)))
        print("  status   : {0}".format(result["status"]))
        if result.get("reject_reason"):
            print("  rejected : {0}".format(result["reject_reason"]))
        if result.get("error"):
            print("  error    : {0}".format(result["error"]))
        if result.get("output"):
            print("--- output (credential-masked) ---")
            print(result["output"])
    return 0 if result["status"] not in ("rejected",) else 1


if __name__ == "__main__":
    sys.exit(main())
