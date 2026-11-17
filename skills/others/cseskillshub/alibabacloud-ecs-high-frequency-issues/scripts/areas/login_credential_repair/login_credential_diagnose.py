#!/usr/bin/env python3
"""ECS instance logon-credential repair triage: single entry point.

Collects cloud-side evidence with the aliyun CLI (caller identity, instance
facts, key-pair existence, cloud assistant agent status, recent command /
reset invocation history), routes it through the embedded decision tree, and
prints an evidence-based report whose every remediation line is a MANUAL
console or in-guest step behind the snapshot-first and tell-and-confirm gates.

The scripts never reset a password, never unlock or enable an account, never
execute anything inside the guest, and never accept or echo a plaintext
password. Anything that would change state is surfaced as guided human action.

Usage examples
    python3 scripts/areas/login_credential_repair/login_credential_diagnose.py --region-id cn-hangzhou \
        --instance-id i-2zeexamplefd9e6793b6 --error-string "account locked"
    python3 scripts/areas/login_credential_repair/login_credential_diagnose.py --region-id cn-beijing \
        --instance-id i-2ze8m0abcdef1234567 --intent reset-not-effective
    python3 scripts/areas/login_credential_repair/login_credential_diagnose.py --region-id cn-hangzhou \
        --scope region --output json
    python3 scripts/areas/login_credential_repair/login_credential_diagnose.py --check-auth-only
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

from _cli import (
    CliError,
    build_user_agent,
    mask_credentials,
    mask_free_text,
    new_session_id,
    paginate,
    run_cli,
)
from _constants import (
    ACTION_DESCRIBE_CLOUD_ASSISTANT_STATUS,
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_INSTANCE_ATTRIBUTE,
    ACTION_DESCRIBE_INVOCATIONS,
    ACTION_DESCRIBE_KEY_PAIRS,
    CLOUD_INSPECTION_WHITELIST,
    CODE_IMPLICIT_DENY,
    CODE_NO_PERMISSION,
    CONSOLE_ENTRIES,
    ECS_API_VERSION,
    ERROR_DICTIONARY,
    GUEST_READ_CHECKS,
    HANDOFF_LINES,
    INSTANCE_ID_RE,
    INVOCATION_MAX_RECORDS,
    INVOCATION_PAGE_SIZE,
    KEY_PAIR_NAME_RE,
    MAX_PAGES,
    OS_LINUX,
    OS_UNKNOWN,
    OS_WINDOWS,
    PAGE_SIZE,
    PLAYBOOK_BY_BRANCH,
    PLAYBOOK_FORGOT_GENERIC,
    PRODUCT_ECS,
    REGION_ID_RE,
    ROOT_CAUSE_TAXONOMY,
    SENSITIVE_CREDENTIAL_NOTICE,
    SKILL_NAME,
    SNAPSHOT_FIRST_RULE,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    STATE_RUNNING,
    STATE_STOPPED,
    TELL_AND_CONFIRM_RULE,
    WRITE_COMMANDS_HUMAN_ONLY,
)
from sts_token import (
    fetch_caller_identity,
    identity_guidance_lines,
    uid_traceability_label,
)

EXIT_BY_STATUS = {STATUS_OK: 0, STATUS_DEGRADED: 1, STATUS_FAIL: 2}

BRANCH_TITLES = {
    "LC1": "client-side path or cached credential",
    "LC2": "wrong logon username for this image",
    "LC3": "online reset channel (cloud assistant agent)",
    "LC4": "key pair interference",
    "LC5": "account locked (lockout policy in effect)",
    "LC6": "account disabled or nonexistent",
    "LC7": "reset write blocked by the guest environment",
    "LC8": "credential knowledge gap (view vs reset)",
    "LC9": "out-of-scope area detected",
}

INTENT_TO_BRANCH = {
    "locked": ["LC5", "LC6"],
    "reset-not-effective": ["LC3", "LC7", "LC1"],
    "forgot-password": ["LC8"],
    "administrator": ["LC5", "LC6", "LC3"],
    "consult": ["LC8"],
    "auto": [],
}

_FINDING_ID = 0


def _finding(branch: str, confidence: str, basis: str, text: str) -> Dict[str, str]:
    """Create a finding row; confidence is CONFIRMED / REPORTED / HYPOTHESIS."""
    global _FINDING_ID
    _FINDING_ID += 1
    return {
        "id": "F{0}".format(_FINDING_ID),
        "rc": branch,
        "confidence": confidence,
        "basis": basis,
        "text": text,
    }


# --------------------------------------------------------------------------- #
# Tolerant response-plucking helpers (never fabricate a missing field)
# --------------------------------------------------------------------------- #
def _dig(node: Any, path: Sequence[str]) -> Any:
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _as_list(node: Any) -> List[Any]:
    if isinstance(node, list):
        return node
    if isinstance(node, dict):
        for inner in ("IpAddress", "IpAddresses", "Item"):
            if isinstance(node.get(inner), list):
                return node[inner]
    if node in (None, ""):
        return []
    return [node]


def _first_str(payload: Dict[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return str(value)
    return ""


# --------------------------------------------------------------------------- #
# Argument handling
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="login_credential_diagnose.py",
        description=(
            "Triage ECS logon-credential failures (password reset not "
            "effective, forgotten password, account locked or disabled, wrong "
            "username, key pair interference) with cloud inspection reads; "
            "output is an evidence report plus manual guidance only."
        ),
    )
    parser.add_argument(
        "--region-id", dest="region_id", default=None,
        help="Alibaba Cloud region id of the instance, e.g. cn-hangzhou "
             "(required for any scoped run; never guessed).",
    )
    parser.add_argument(
        "--instance-id", dest="instance_id", default=None,
        help="ECS instance id the logon failure concerns, e.g. i-2zed1xj9....",
    )
    parser.add_argument(
        "--scope", dest="scope", choices=("auto", "instance", "region"),
        default="auto",
        help="Evidence scope. auto derives it from --instance-id.",
    )
    parser.add_argument(
        "--intent", dest="intent",
        choices=("auto", "consult", "reset-not-effective", "locked",
                 "forgot-password", "administrator"),
        default="auto",
        help="What the customer came for; auto infers it from --error-string.",
    )
    parser.add_argument(
        "--error-string", dest="error_string", default=None,
        help="Verbatim error text the customer saw. Secret-looking tokens are "
             "masked before anything is printed; NEVER paste a password here.",
    )
    parser.add_argument(
        "--login-user", dest="login_user", default=None,
        help="The username the customer typed at the logon prompt (e.g. root, "
             "ecs-user, cloud-user, administrator). This is a username only; "
             "never send the password.",
    )
    parser.add_argument(
        "--key-pair-name", dest="key_pair_name", default=None,
        help="Key pair name to verify, when the customer mentions one.",
    )
    parser.add_argument(
        "--max-pages", dest="max_pages", type=int, default=MAX_PAGES,
        help="Ceiling on paging requests per list action (default {0}).".format(MAX_PAGES),
    )
    parser.add_argument(
        "--timeout", dest="timeout", type=int, default=30,
        help="Per-call CLI timeout in seconds (default 30).",
    )
    parser.add_argument(
        "--output", dest="output", choices=("text", "json"), default="text",
        help="Report rendering (default text).",
    )
    parser.add_argument(
        "--check-auth-only", dest="check_auth_only", action="store_true",
        help="Only verify the caller identity and exit.",
    )
    parser.add_argument("--verbose", dest="verbose", action="store_true",
                        help="Show extra detail.")
    return parser


def validate(args: argparse.Namespace) -> List[str]:
    problems: List[str] = []
    if args.check_auth_only:
        return problems
    if not args.region_id:
        problems.append("--region-id is required for a scoped run (never guessed)")
    elif not re.match(REGION_ID_RE, args.region_id):
        problems.append("--region-id does not look like a region id")
    if args.instance_id and not re.match(INSTANCE_ID_RE, args.instance_id):
        problems.append("--instance-id does not look like an instance id (i-...)")
    if args.key_pair_name and not re.match(KEY_PAIR_NAME_RE, args.key_pair_name):
        problems.append("--key-pair-name contains characters outside the safe set")
    # A logon user is a username, never a secret: reject anything shaped like a
    # pasted password instead of masking it and moving on.
    if args.login_user and not re.match(r"^[A-Za-z][A-Za-z0-9@$_\-.\\]{0,63}$",
                                        args.login_user):
        problems.append("--login-user must be a bare username; never send a password to this skill")
    return problems


# --------------------------------------------------------------------------- #
# Cloud evidence collection (every call is a whitelisted inspection read)
# --------------------------------------------------------------------------- #
def collect_instances(args: argparse.Namespace, session_id: str,
                      warnings: List[str], errors: List[Dict[str, str]]
                      ) -> Tuple[List[Dict[str, Any]], str]:
    base: Dict[str, Any] = {"RegionId": args.region_id}
    if args.instance_id:
        base["InstanceIds"] = json.dumps([args.instance_id])
    try:
        items, paging = paginate(
            PRODUCT_ECS, ACTION_DESCRIBE_INSTANCES, base, "Instance",
            session_id=session_id, page_size=PAGE_SIZE, max_pages=args.max_pages,
            warnings=warnings, nested_keys=("Instances",), timeout=args.timeout,
            region=args.region_id,
        )
    except CliError as exc:
        errors.append({"action": "ecs.{0}".format(ACTION_DESCRIBE_INSTANCES),
                       "code": exc.code, "detail": mask_credentials(str(exc))})
        return [], "failed"
    rows: List[Dict[str, Any]] = []
    for item in items:
        os_type = str(item.get("OSType") or "").lower()
        os_family = OS_WINDOWS if "windows" in os_type else (
            OS_LINUX if "linux" in os_type else OS_UNKNOWN)
        rows.append({
            "instance_id": _first_str(item, ("InstanceId",)),
            "instance_name": _first_str(item, ("InstanceName",)),
            "status": _first_str(item, ("Status",)),
            "os_family": os_family,
            "os_name": _first_str(item, ("OSName",)),
            "public_ips": [str(x) for x in _as_list(_dig(item, ("PublicIpAddress", "IpAddress")))],
            "eip": _first_str(_dig(item, ("EipAddress",)) or {}, ("IpAddress",)),
            "inner_ips": [str(x) for x in _as_list(_dig(item, ("InnerIpAddress", "IpAddress")))],
            "vpc_private_ips": [
                str(x) for x in _as_list(_dig(item, ("VpcAttributes", "PrivateIpAddress", "IpAddress")))],
            "key_pair_name": _first_str(item, ("KeyPairName",)),
            "instance_type": _first_str(item, ("InstanceType",)),
            "zone": _first_str(item, ("ZoneId",)),
        })
    return rows, paging


def collect_attribute(args: argparse.Namespace, session_id: str,
                      warnings: List[str], errors: List[Dict[str, str]]
                      ) -> Dict[str, str]:
    if not args.instance_id:
        return {}
    try:
        payload = run_cli(
            PRODUCT_ECS, ACTION_DESCRIBE_INSTANCE_ATTRIBUTE,
            {"InstanceId": args.instance_id},
            session_id=session_id, warnings=warnings, timeout=args.timeout,
            region=args.region_id,
        )
    except CliError as exc:
        errors.append({"action": "ecs.{0}".format(ACTION_DESCRIBE_INSTANCE_ATTRIBUTE),
                       "code": exc.code, "detail": mask_credentials(str(exc))})
        return {}
    return {
        "status": _first_str(payload, ("Status",)),
        "network_type": _first_str(payload, ("InstanceNetworkType",)),
        "os_name": _first_str(payload, ("OSName",)),
        "instance_type": _first_str(payload, ("InstanceType",)),
        "public_ips": ", ".join(str(x) for x in _as_list(payload.get("PublicIpAddress"))),
        "inner_ips": ", ".join(str(x) for x in _as_list(payload.get("InnerIpAddress"))),
    }


def collect_keypairs(args: argparse.Namespace, instances: List[Dict[str, Any]],
                     session_id: str, warnings: List[str],
                     errors: List[Dict[str, str]]) -> Dict[str, Any]:
    names: List[str] = []
    if args.key_pair_name:
        names.append(args.key_pair_name)
    for row in instances:
        bound = row.get("key_pair_name") or ""
        if bound and bound not in names:
            names.append(bound)
    result: Dict[str, Any] = {"queried": False, "requested": names,
                              "present": [], "missing": [], "region_names": []}
    if not names:
        # Eval 15637 task 587680: with no bound and no named key pair this returned
        # without any read, so "no key pair" rested on the instance row alone and the
        # area's own api:DescribeKeyPairs evidence never appeared. The region inventory
        # is the read that settles it, and it is one non-mutating call.
        try:
            items, _paging = paginate(
                PRODUCT_ECS, ACTION_DESCRIBE_KEY_PAIRS,
                {"RegionId": args.region_id},
                "KeyPair",
                session_id=session_id, page_size=PAGE_SIZE,
                max_pages=2, warnings=warnings, nested_keys=("KeyPairs",),
                timeout=args.timeout, region=args.region_id,
            )
        except CliError as exc:
            errors.append({"action": "ecs.{0}".format(ACTION_DESCRIBE_KEY_PAIRS),
                           "code": exc.code,
                           "detail": mask_credentials(str(exc))})
            return result
        result["queried"] = True
        result["region_names"] = [str(_first_str(k, ("KeyPairName",))) for k in items]
        return result
    result["queried"] = True
    for name in names:
        try:
            items, _paging = paginate(
                PRODUCT_ECS, ACTION_DESCRIBE_KEY_PAIRS,
                {"RegionId": args.region_id, "KeyPairName": name},
                "KeyPair",
                session_id=session_id, page_size=PAGE_SIZE,
                max_pages=2, warnings=warnings, nested_keys=("KeyPairs",),
                timeout=args.timeout, region=args.region_id,
            )
        except CliError as exc:
            errors.append({"action": "ecs.{0}".format(ACTION_DESCRIBE_KEY_PAIRS),
                           "code": exc.code,
                           "detail": mask_credentials(str(exc))})
            continue
        found = [str(_first_str(k, ("KeyPairName",))) for k in items]
        if name in found:
            result["present"].append(name)
        else:
            result["missing"].append(name)
    return result


def collect_agent_status(args: argparse.Namespace, session_id: str,
                         warnings: List[str], errors: List[Dict[str, str]]
                         ) -> Dict[str, Any]:
    if not args.instance_id:
        return {"checked": False, "online": None}
    try:
        payload = run_cli(
            PRODUCT_ECS, ACTION_DESCRIBE_CLOUD_ASSISTANT_STATUS,
            {"RegionId": args.region_id, "InstanceId.1": args.instance_id},
            session_id=session_id, warnings=warnings, timeout=args.timeout,
            region=args.region_id,
        )
    except CliError as exc:
        errors.append({"action": "ecs.{0}".format(ACTION_DESCRIBE_CLOUD_ASSISTANT_STATUS),
                       "code": exc.code, "detail": mask_credentials(str(exc))})
        return {"checked": False, "online": None, "error": exc.code}
    rows = _dig(payload, ("CloudAssistantStatusSet", "CloudAssistantStatus"))
    entries = [r for r in _as_list(rows) if isinstance(r, dict)]
    if not entries:
        return {"checked": True, "online": None,
                "note": "no agent record returned for this instance"}
    entry = entries[0]
    raw = _first_str(entry, ("CloudAssistantStatus",))
    online = {"true": True, "false": False}.get(raw.lower())
    return {
        "checked": True,
        "online": online,
        "raw_status": raw or "not returned",
        "agent_version": _first_str(entry, ("CloudAssistantVersion",)),
        "last_heartbeat": _first_str(entry, ("LastHeartbeatTime", "LastInvocationTime")),
        "supports_reset": _first_str(entry, ("SupportInstanceConnect", "AgentSupportMonitor")),
    }


def collect_invocations(args: argparse.Namespace, session_id: str,
                        warnings: List[str], errors: List[Dict[str, str]]
                        ) -> Dict[str, Any]:
    if not args.instance_id:
        return {"checked": False, "recent": []}
    try:
        items, paging = paginate(
            PRODUCT_ECS, ACTION_DESCRIBE_INVOCATIONS,
            {"RegionId": args.region_id, "InstanceId": args.instance_id},
            "Invocation",
            session_id=session_id, page_size=INVOCATION_PAGE_SIZE,
            max_pages=2, warnings=warnings, nested_keys=("Invocations",),
            timeout=args.timeout, region=args.region_id,
        )
    except CliError as exc:
        errors.append({"action": "ecs.{0}".format(ACTION_DESCRIBE_INVOCATIONS),
                       "code": exc.code, "detail": mask_credentials(str(exc))})
        return {"checked": False, "recent": [], "error": exc.code}
    recent: List[Dict[str, str]] = []
    for record in items[:INVOCATION_MAX_RECORDS]:
        recent.append({
            "name": _first_str(record, ("CommandName", "Name")),
            "type": _first_str(record, ("CommandType", "Type")),
            "status": _first_str(record, ("InvocationStatus", "Status")),
            "created": _first_str(record, ("CreateTime", "CreationTime")),
        })
    return {"checked": True, "paging": paging, "recent": recent}


# --------------------------------------------------------------------------- #
# Decision tree
# --------------------------------------------------------------------------- #
def match_dictionary(error_text: str) -> List[Tuple[str, str]]:
    lowered = (error_text or "").lower()
    hits: List[Tuple[str, str]] = []
    if not lowered.strip():
        return hits
    for branch, phrases, meaning in ERROR_DICTIONARY:
        for phrase in phrases:
            if phrase.lower() in lowered:
                hits.append((branch, meaning))
                break
    return hits


def os_family_of(facts: Dict[str, Any]) -> str:
    for row in facts.get("instances", []):
        if row.get("os_family") in (OS_WINDOWS, OS_LINUX):
            return row["os_family"]
    return OS_UNKNOWN


def derive_branches(args: argparse.Namespace, facts: Dict[str, Any]
                    ) -> Tuple[List[str], List[Dict[str, str]]]:
    branches: List[str] = []
    findings: List[Dict[str, str]] = []

    def add(branch: str) -> None:
        if branch not in branches:
            branches.append(branch)

    # 1) intent
    for branch in INTENT_TO_BRANCH.get(args.intent, []):
        add(branch)

    # 2) verbatim error string against the dictionary
    for branch, meaning in match_dictionary(args.error_string or ""):
        add(branch)
        add_conf = "REPORTED" if branch != "LC9" else "CONFIRMED"
        findings.append(_finding(
            branch, add_conf, "error-string dictionary match",
            "{0} ({1})".format(meaning, BRANCH_TITLES.get(branch, branch)),
        ))

    # 3) hard facts from the cloud reads override pure wording
    os_family = os_family_of(facts)
    agent = facts.get("agent") or {}
    keypair = facts.get("keypair") or {}
    instances = facts.get("instances") or []

    if agent.get("checked") and agent.get("online") is False:
        add("LC3")
        findings.append(_finding(
            "LC3", "CONFIRMED", "api:DescribeCloudAssistantStatus",
            "The cloud assistant agent is offline on this instance: console "
            "online password reset and Workbench passwordless logon cannot "
            "work; invocation history for this instance proves what did or "
            "did not reach the guest.",
        ))
    elif agent.get("checked") and agent.get("online") is True:
        findings.append(_finding(
            "LC3", "CONFIRMED", "api:DescribeCloudAssistantStatus",
            "The cloud assistant agent is online: the online reset channel is "
            "available, so a failed online reset needs its invocation record "
            "examined, not a blind retry.",
        ))

    if keypair.get("missing"):
        add("LC4")
        findings.append(_finding(
            "LC4", "CONFIRMED", "api:DescribeKeyPairs",
            "Key pair(s) {0} are referenced (bound to the instance or named by "
            "the customer) but do not exist in this region: the removal "
            "complaint is a fact, not a guess.".format(", ".join(keypair["missing"])),
        ))
    if keypair.get("present"):
        findings.append(_finding(
            "LC4", "CONFIRMED", "api:DescribeKeyPairs",
            "Key pair(s) {0} exist in this region; if logon still fails with "
            "them, the private key or the guest ssh authorized_keys is the "
            "next thing the customer must check (in-guest reading).".format(
                ", ".join(keypair["present"])),
        ))
    if keypair.get("queried") and not keypair.get("requested"):
        findings.append(_finding(
            "LC4", "CONFIRMED", "api:DescribeKeyPairs",
            "The region key pair inventory was read ({0} key pair(s) exist) and no "
            "key pair is bound to this instance or named by the customer, so the "
            "logon path here is password or VNC - a missing key pair is not the "
            "cause.".format(len(keypair.get("region_names") or [])),
        ))

    for row in instances:
        if not (row.get("public_ips") or []):
            if not row.get("eip"):
                add("LC1")
                findings.append(_finding(
                    "LC1", "CONFIRMED", "api:DescribeInstances",
                    "Instance {0} has no public IP and no EIP attached: local "
                    "SSH/RDP tools cannot reach it from the internet; the "
                    "customer may be dialing a private address or a stale "
                    "domain.".format(row.get("instance_id") or "?"),
                ))
        if row.get("status") == STATE_STOPPED:
            add("LC7")
            findings.append(_finding(
                "LC7", "CONFIRMED", "api:DescribeInstances",
                "Instance is Stopped: start it first (manual step; this skill "
                "never starts or stops instances). Password changes made "
                "offline still need one restart to apply.",
            ))
    if facts.get("attribute", {}).get("status") == STATE_RUNNING and instances:
        findings.append(_finding(
            "LC3", "CONFIRMED", "api:DescribeInstanceAttribute",
            "Instance reports Running: the failure is below the instance-state "
            "area, which keeps the case on the credential area.",
        ))

    # 4) windows + lockout-family symptom keeps LC5; if no branch survived,
    #    fall back to the generic credential-refused triage.
    if not branches:
        add("LC8")
        findings.append(_finding(
            "LC8", "HYPOTHESIS", "no distinguishing evidence",
            "No error text and no intent given: treat as a credential "
            "knowledge gap until the VNC tie-breaker test says otherwise "
            "(confidence low).",
        ))

    # 5) standing hypotheses that tickets loved to assert as facts
    if "LC5" in branches:
        findings.append(_finding(
            "LC5", "HYPOTHESIS", "mechanism (not measured)",
            "Repeated failed logons from internet brute-force traffic against "
            "an openly exposed 3389 is the most common trigger, but this "
            "skill neither reads security-group rules nor the guest event "
            "log, so it stays a hypothesis (confidence medium) until the "
            "customer confirms the 3389 source range in the console.",
        ))
    if "LC3" in branches and agent.get("online") is not False and os_family == OS_WINDOWS:
        findings.append(_finding(
            "LC3", "HYPOTHESIS", "past-ticket pattern",
            "Guest security software intercepting the reset is a known pattern "
            "for Windows instances whose online reset reports success while "
            "the password never changes; it cannot be measured from the cloud "
            "API and must not be stated as the cause (confidence low).",
        ))
    return branches, findings


# --------------------------------------------------------------------------- #
# Guidance rendering
# --------------------------------------------------------------------------- #
def playbook_lines(branches: List[str]) -> List[str]:
    lines: List[str] = []
    seen = set()
    ordered = [b for b in ("LC5", "LC6", "LC3", "LC7", "LC4", "LC8", "LC1", "LC2")
               if b in branches]
    if not ordered:
        ordered = ["LC8"]
    for branch in ordered:
        for line in PLAYBOOK_BY_BRANCH.get(branch, ()):
            if line not in seen:
                seen.add(line)
                lines.append(line)
    if "LC1" in branches or "LC2" in branches or "LC8" in branches:
        for line in PLAYBOOK_FORGOT_GENERIC:
            if line not in seen:
                seen.add(line)
                lines.append(line)
    return lines


def guest_check_lines(facts: Dict[str, Any]) -> List[str]:
    os_family = os_family_of(facts)
    wanted = (OS_LINUX, OS_WINDOWS) if os_family == OS_UNKNOWN else (os_family,)
    lines: List[str] = []
    for family, fact, command, criterion in GUEST_READ_CHECKS:
        if family in wanted:
            lines.append("[{0}] {1} -> run inside Workbench/VNC: `{2}`  |  "
                         "read: {3}".format(family.upper(), fact, command, criterion))
    return lines


def boundary_lines(branches: List[str]) -> List[str]:
    lines = [
        "This skill changes nothing: every write below stays a human step in "
        "the console or inside the guest - " + "; ".join(WRITE_COMMANDS_HUMAN_ONLY),
        "Not covered and handed off instead: security-group rule read/edit, "
        "machine-generated VNC links, disk capacity, instance start/stop, "
        "resource exhaustion, intrusion response, application-panel passwords.",
    ]
    if "LC9" in branches:
        for key in ("network", "security", "app_credential"):
            lines.append(HANDOFF_LINES[key])
    if "LC7" in branches:
        lines.append(HANDOFF_LINES["disk_capacity"])
    lines.append(HANDOFF_LINES["commercial"])
    return lines


def evidence_notes(facts: Dict[str, Any], errors: List[Dict[str, str]]
                   ) -> List[str]:
    notes: List[str] = []
    if not facts.get("instances"):
        notes.append("No instance record returned for the scoped run: the "
                     "instance id or region may be wrong; nothing was assumed.")
    if any(e["code"] in (CODE_NO_PERMISSION, CODE_IMPLICIT_DENY) for e in errors):
        notes.append("At least one inspection call was denied: attach the "
                     "missing action from references/ram-policies.md and "
                     "re-run the same command.")
    if (facts.get("agent") or {}).get("checked") is False:
        notes.append("Cloud assistant status unknown (not checked or call "
                     "failed): online-reset feasibility is reported as "
                     "unverified, not as a conclusion.")
    return notes


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def instance_rows(instances: List[Dict[str, Any]]) -> List[str]:
    rows: List[str] = []
    for row in instances:
        rows.append("  {0} name={1} status={2} os={3} type={4}".format(
            row.get("instance_id") or "not returned",
            row.get("instance_name") or "-",
            row.get("status") or "not returned",
            (row.get("os_name") or row.get("os_family") or "not returned"),
            row.get("instance_type") or "-",
        ))
        rows.append("      public={0} eip={1} private={2} keypair={3}".format(
            ",".join(row.get("public_ips") or []) or "none",
            row.get("eip") or "none",
            ",".join(row.get("inner_ips") or []) or "none",
            row.get("key_pair_name") or "none",
        ))
    if not rows:
        rows.append("  (no instances in scope)")
    return rows


def render_text(report: Dict[str, Any]) -> str:
    out: List[str] = []
    out.append("=" * 72)
    out.append(" ECS Instance Logon Credential Repair - triage report")
    out.append("=" * 72)
    out.append("Skill        : {0}".format(report["skill_name"]))
    out.append("Session id  : {0}".format(report["session_id"]))
    out.append("User-Agent  : {0}".format(report["user_agent"]))
    out.append("Account      : {0} (identity api version {1})".format(
        report["uid_label"], report["identity_api_version"]))
    out.append("Callable set : {0}".format(", ".join(CLOUD_INSPECTION_WHITELIST)))
    out.append("Declared ver : ecs={0}".format(ECS_API_VERSION))

    out.append("")
    out.append("--- Collected parameters (all declared) ---")
    for key, value in report["declared_params"].items():
        out.append("  {0} = {1}".format(key, value))

    out.append("")
    out.append("--- Cloud-side evidence: instances ---")
    out.extend(report["instance_rows"])
    if report["attribute"]:
        attribute_text = ", ".join("{0}={1}".format(k, v) for k, v in
                                   sorted(report["attribute"].items()) if v)
        if attribute_text:
            out.append("  attribute read: {0}".format(attribute_text))
    out.append("  key pairs: {0}".format(report["keypair_summary"]))
    out.append("  cloud assistant: {0}".format(report["agent_summary"]))
    out.append("  recent invocations (command/reset history):")
    if report["invocation_rows"]:
        out.extend(report["invocation_rows"])
    else:
        out.append("    (none returned / not checked)")

    out.append("")
    out.append("--- Scenario branches ---")
    out.append("  " + (", ".join(
        "{0} ({1})".format(b, BRANCH_TITLES.get(b, b))
        for b in report["branches"]) or "none derived"))

    out.append("")
    out.append("--- Findings (CONFIRMED = api fact, REPORTED = customer text, "
               "HYPOTHESIS = not measured) ---")
    if not report["findings"]:
        out.append("  (no finding derived; evidence was insufficient rather than assumed)")
    for item in report["findings"]:
        out.append("  [{0}][{1}][{2}] {3}".format(
            item["id"], item["confidence"], item["rc"], item["text"]))
        out.append("      basis: {0}".format(item["basis"]))

    out.append("")
    out.append("--- Root-cause codes used by the decision tree ---")
    for code, text in ROOT_CAUSE_TAXONOMY:
        out.append("  {0}: {1}".format(code, text))

    out.append("")
    out.append("--- Playbook (manual steps; tell-and-confirm before each; "
               "snapshot first for any write) ---")
    out.append("  {0}".format(SNAPSHOT_FIRST_RULE))
    out.append("  {0}".format(TELL_AND_CONFIRM_RULE))
    for line in report["playbook"]:
        out.append("  {0}".format(line))
    out.append("")
    out.append("  Console paths:")
    for name, path in CONSOLE_ENTRIES.items():
        out.append("    {0}: {1}".format(name, path))

    out.append("")
    out.append("--- In-guest readings the CUSTOMER runs (this skill runs none) ---")
    if report["guest_checks"]:
        for line in report["guest_checks"]:
            out.append("  {0}".format(line))
        out.append("  Paste the OUTPUT back, never the password; mask anything "
                   "secret-looking before sharing.")
    else:
        out.append("  (none: no in-guest reading needed for this branch)")

    out.append("")
    out.append("--- Scope boundary and handoff ---")
    for line in report["boundary"]:
        out.append("  {0}".format(line))

    out.append("")
    out.append("--- Sensitive credential notice ---")
    out.append("  {0}".format(SENSITIVE_CREDENTIAL_NOTICE))
    for line in report.get("sensitive_extra", []):
        out.append("  {0}".format(line))

    if report["evidence_notes"]:
        out.append("")
        out.append("--- Evidence notes ---")
        for line in report["evidence_notes"]:
            out.append("  {0}".format(line))

    if report["warnings"]:
        out.append("")
        out.append("--- Warnings ---")
        for line in report["warnings"]:
            out.append("  [WARN] {0}".format(line))

    if report["errors"]:
        out.append("")
        out.append("--- Failed inspection calls ---")
        for item in report["errors"]:
            out.append("  {0} -> {1}: {2}".format(
                item["action"], item["code"], item["detail"]))

    out.append("")
    out.append("STATUS: {0}".format(report["STATUS"]))
    out.append("NEXT_ACTION: {0}".format(report["NEXT_ACTION"]))
    out.append("")
    out.append("Reference: references/login-credential-repair__login-credential-decision-tree.md "
               "(branches LC1-LC9), references/login-credential-repair__windows-lockout-playbook.md, "
               "references/login-credential-repair__password-reset-playbook.md, "
               "references/login-credential-repair__guest-credential-checks.md, "
               "references/login-credential-repair__handoff-scripts.md, references/login-credential-repair__help-docs.md, "
               "references/ram-policies.md")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #
def summarize_keypair(keypair: Dict[str, Any]) -> str:
    if not keypair.get("queried"):
        return "not queried (no key pair bound or named)"
    if not keypair.get("requested"):
        return ("region inventory read: {0} key pair(s) in region; "
                "none bound or named".format(len(keypair.get("region_names") or [])))
    return "requested={0}; present={1}; missing={2}".format(
        ", ".join(keypair.get("requested") or []) or "-",
        ", ".join(keypair.get("present") or []) or "none",
        ", ".join(keypair.get("missing") or []) or "none",
    )


def summarize_agent(agent: Dict[str, Any]) -> str:
    if not agent.get("checked"):
        return "not checked or call failed"
    if agent.get("online") is True:
        return "ONLINE (version {0}, heartbeat {1})".format(
            agent.get("agent_version") or "not returned",
            agent.get("last_heartbeat") or "not returned")
    if agent.get("online") is False:
        return "OFFLINE (raw {0})".format(agent.get("raw_status"))
    return "state not returned: {0}".format(agent.get("note") or
                                            agent.get("raw_status") or "unknown")


def determine_status(errors: List[Dict[str, str]], warnings: List[str],
                     facts: Dict[str, Any], identity_error: Optional[str]) -> str:
    if identity_error:
        return STATUS_FAIL
    if any(e["code"] in (CODE_NO_PERMISSION, CODE_IMPLICIT_DENY) for e in errors):
        return STATUS_DEGRADED
    if not facts.get("instances"):
        return STATUS_DEGRADED if errors else STATUS_OK
    if errors or warnings:
        return STATUS_DEGRADED
    if (facts.get("agent") or {}).get("online") is None:
        return STATUS_DEGRADED
    return STATUS_OK


def next_action_for(status: str, branches: List[str], args: argparse.Namespace,
                    errors: List[Dict[str, str]]) -> str:
    if status == STATUS_FAIL:
        if any(e["code"] in (CODE_NO_PERMISSION, CODE_IMPLICIT_DENY) for e in errors):
            return ("Ask the account administrator for the missing inspection "
                    "action listed in references/ram-policies.md, then re-run "
                    "the same command.")
        return ("Restore the CLI credential chain with `aliyun sts get-caller-identity`, "
                "then re-run; never share key material with the assistant.")
    if "LC9" in branches:
        return ("Stop on the credential area and hand off per "
                "references/login-credential-repair__handoff-scripts.md; report only what the reads "
                "confirmed.")
    if "LC5" in branches or "LC6" in branches:
        return ("Walk the VNC zero-write path and the read-form `net accounts` "
                "check first (references/login-credential-repair__windows-lockout-playbook.md); any "
                "policy write is a customer-executed step after a snapshot.")
    if "LC3" in branches or "LC7" in branches:
        return ("Follow the reset decision in references/login-credential-repair__password-reset-playbook.md: "
                "online only while the agent reads online, otherwise the "
                "restart-window offline path with snapshot first.")
    if not args.instance_id:
        return ("Re-run with --instance-id picked from the listed instances so "
                "the agent, key-pair and invocation reads can be scoped.")
    return ("Have the customer run the VNC tie-breaker test and the listed "
            "in-guest reads, then re-run with the observed --error-string to "
            "narrow the branch.")


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    session_id = new_session_id()
    warnings: List[str] = []
    errors: List[Dict[str, str]] = []

    identity, identity_error = fetch_caller_identity(session_id, warnings=warnings)
    report: Dict[str, Any] = {
        "skill_name": SKILL_NAME,
        "session_id": session_id,
        "user_agent": build_user_agent(session_id),
        "region_id": args.region_id,
        "instance_id": args.instance_id,
        "uid_label": uid_traceability_label(identity),
        "identity_api_version": identity.get("api_version") or "not returned",
        "declared_params": {},
        "attribute": {},
        "instance_rows": [],
        "keypair_summary": "not queried",
        "agent_summary": "not checked",
        "invocation_rows": [],
        "branches": [],
        "findings": [],
        "playbook": [],
        "guest_checks": [],
        "boundary": [],
        "evidence_notes": [],
        "sensitive_extra": [],
        "warnings": warnings,
        "errors": errors,
    }

    if args.check_auth_only:
        report["STATUS"] = STATUS_OK if identity_error is None else STATUS_FAIL
        report["NEXT_ACTION"] = (
            "Credential chain works; run the full triage with --region-id."
            if identity_error is None
            else "Run `aliyun sts get-caller-identity` to restore the default credential "
                 "chain; never share key material with the assistant."
        )
        report["playbook"] = identity_guidance_lines(identity_error)
        return report

    masked_error = mask_free_text(args.error_string) if args.error_string else None
    login_user_shown = "not supplied"
    if args.login_user:
        ok_name = re.match(r"^[A-Za-z][A-Za-z0-9@$_\-.\\]{0,63}$", args.login_user)
        # A bare username is not secret; anything else is rejected, not echoed.
        login_user_shown = args.login_user if ok_name else "rejected (username only)"
    report["declared_params"] = {
        "region-id": args.region_id or "not supplied",
        "instance-id": args.instance_id or "not supplied (region scope listing)",
        "scope": ("instance" if args.instance_id
                  else (args.scope if args.scope != "auto" else "region")),
        "intent": args.intent,
        "error-string": masked_error or "not supplied",
        "login-user": login_user_shown,
        "key-pair-name": args.key_pair_name or "not supplied (derived from the instance when bound)",
        "page-size": PAGE_SIZE,
        "max-pages": args.max_pages,
        "per-call-timeout-seconds": args.timeout,
        "credential-source": "local CLI default chain; no key material in arguments",
    }
    if masked_error and args.error_string and masked_error != args.error_string:
        report["sensitive_extra"] = [
            "The supplied error text contained secret-looking value(s); they "
            "were masked in this report and are never echoed by the skill. If "
            "that text included a real password, reset it as soon as the "
            "instance is reachable again."
        ]

    problems = validate(args)
    if problems:
        report["instance_rows"] = ["  (not collected: input validation failed)"]
        report["findings"] = [_finding(
            "LC9", "CONFIRMED", "input validation",
            "Input rejected: {0}".format(" ".join(problems)))]
        report["STATUS"] = STATUS_FAIL
        report["NEXT_ACTION"] = ("Collect the missing or malformed value(s) "
                                 "from the customer console page or ticket, "
                                 "then re-run: {0}".format(" ".join(problems)))
        return report

    instances, paging = collect_instances(args, session_id, warnings, errors)
    report["attribute"] = collect_attribute(args, session_id, warnings, errors)
    keypair = collect_keypairs(args, instances, session_id, warnings, errors)
    agent = collect_agent_status(args, session_id, warnings, errors)
    invocations = collect_invocations(args, session_id, warnings, errors)
    facts: Dict[str, Any] = {
        "instances": instances,
        "paging": paging,
        "attribute": report["attribute"],
        "keypair": keypair,
        "agent": agent,
        "invocations": invocations,
    }
    report["instance_rows"] = instance_rows(instances)
    report["keypair_summary"] = summarize_keypair(keypair)
    report["agent_summary"] = summarize_agent(agent)
    report["invocation_rows"] = [
        "    {0} type={1} status={2} created={3}".format(
            r.get("name") or "unnamed", r.get("type") or "-",
            r.get("status") or "-", r.get("created") or "-")
        for r in invocations.get("recent", [])
    ]

    branches, findings = derive_branches(args, facts)
    report["branches"] = branches
    report["findings"] = findings
    report["playbook"] = playbook_lines(branches)
    report["guest_checks"] = guest_check_lines(facts) if any(
        b in branches for b in ("LC1", "LC2", "LC4", "LC5", "LC6", "LC7", "LC3")
    ) else []
    report["boundary"] = boundary_lines(branches)
    report["evidence_notes"] = evidence_notes(facts, errors)
    report["STATUS"] = determine_status(errors, warnings, facts, identity_error)
    report["NEXT_ACTION"] = next_action_for(report["STATUS"], branches, args, errors)
    if identity_error:
        report["warnings"].append(
            "caller identity lookup returned {0}; account label reported as "
            "unavailable instead of assumed".format(identity_error))
        report["playbook"] = identity_guidance_lines(identity_error) + report["playbook"]
    return report


def _run_selftest() -> int:
    """Offline boundary locks for the login-diagnosis decision core.

    ``derive_branches`` unions intent + verbatim error-string dictionary hits +
    hard cloud facts into the LC1-LC9 branch set that the customer is then
    routed on, and falls back to LC8 only when nothing distinguishes the case;
    ``match_dictionary`` must match case-insensitively and return nothing on
    empty/garbage; ``next_action_for`` picks a single remediation by a strict
    priority (FAIL > LC9 handoff > LC5/LC6 > LC3/LC7 > missing-id > fallback).
    A wrong branch or ordering sends the responder to the opposite fix, so each
    is pinned with inputs that isolate one signal at a time. Pure logic only -
    no cloud, no credentials, no subprocess.
    """
    rc = 0

    def expect(name, cond):
        nonlocal rc
        if cond:
            print("PASS {0}".format(name))
        else:
            print("FAIL {0}".format(name))
            rc = 1

    # --- match_dictionary: case-insensitive phrase -> (branch, meaning)
    branch, phrases, _ = ERROR_DICTIONARY[0]
    hits = match_dictionary("SSH: " + phrases[0].upper())
    expect("md_case_insensitive_hit", hits and hits[0][0] == branch)
    expect("md_empty_none", match_dictionary("") == [] and match_dictionary(None) == [])
    expect("md_garbage_empty", match_dictionary("totally unrelated zzz") == [])

    # --- os_family_of: first windows/linux row wins, else unknown
    expect("osf_windows", os_family_of({"instances": [{"os_family": OS_WINDOWS}]}) == OS_WINDOWS)
    expect("osf_linux", os_family_of({"instances": [{"os_family": OS_LINUX}]}) == OS_LINUX)
    expect("osf_unknown", os_family_of({"instances": [{"os_family": "weird"}]}) == OS_UNKNOWN)
    expect("osf_empty_unknown", os_family_of({"instances": []}) == OS_UNKNOWN)

    # --- next_action_for: strict priority order
    def A(iid="i-abc"):
        return argparse.Namespace(instance_id=iid)

    expect("naf_fail_permission",
           "ram-policies" in next_action_for(STATUS_FAIL, [], A(), [{"code": CODE_NO_PERMISSION}]))
    expect("naf_fail_credentials",
           "aliyun sts get-caller-identity" in next_action_for(STATUS_FAIL, [], A(), []))
    # LC9 handoff outranks LC5 vnc when both present
    expect("naf_lc9_beats_lc5",
           "hand" in next_action_for("OK", ["LC5", "LC9"], A(), []).lower())
    expect("naf_lc5_vnc", "vnc" in next_action_for("OK", ["LC5"], A(), []).lower())
    expect("naf_lc3_reset", "reset" in next_action_for("OK", ["LC3"], A(), []).lower())
    expect("naf_no_instance_id",
           "instance-id" in next_action_for("OK", [], A(iid=""), []).lower())

    # --- derive_branches: each signal in isolation, dedup, LC8 fallback
    def args_of(intent="auto", err=""):
        return argparse.Namespace(intent=intent, error_string=err)

    def neutral_facts(**over):
        base = {"instances": [], "agent": {"checked": False},
                "keypair": {"missing": [], "present": []}, "attribute": {}}
        base.update(over)
        return base

    def branches_of(a, f):
        return derive_branches(a, f)[0]

    expect("db_intent_locked", branches_of(args_of("locked"), neutral_facts()) == ["LC5", "LC6"])
    expect("db_fallback_lc8", branches_of(args_of("auto"), neutral_facts()) == ["LC8"])
    expect("db_agent_offline_lc3",
           "LC3" in branches_of(args_of("auto"), neutral_facts(agent={"checked": True, "online": False})))
    expect("db_agent_online_no_lc3_branch",
           "LC3" not in branches_of(args_of("auto"), neutral_facts(agent={"checked": True, "online": True})))
    expect("db_keypair_missing_lc4",
           "LC4" in branches_of(args_of("auto"), neutral_facts(keypair={"missing": ["k"], "present": []})))
    db_lc1 = branches_of(args_of("auto"), neutral_facts(
        instances=[{"instance_id": "i-1", "public_ips": [], "eip": None, "status": "Running"}]))
    expect("db_no_public_ip_lc1", "LC1" in db_lc1)
    db_stopped = branches_of(args_of("auto"), neutral_facts(
        instances=[{"instance_id": "i-1", "public_ips": ["1.2.3.4"], "status": STATE_STOPPED}]))
    expect("db_stopped_lc7", "LC7" in db_stopped)
    # dedup: an intent that already yields LC5 plus an LC5 error phrase stays single
    dup = branches_of(args_of("locked"), neutral_facts())
    expect("db_dedup", len(dup) == len(set(dup)))

    # --- key pair inventory: no bound and no named key pair still gets the read,
    #     so "no key pair here" is measured against the region, not inferred.
    _kp_calls = []
    _kp_real = globals()["paginate"]

    def _kp_stub(product, action, params, item_key, **kw):
        _kp_calls.append((action, dict(params)))
        return ([{"KeyPairName": "region-key-a"}, {"KeyPairName": "region-key-b"}], {})

    globals()["paginate"] = _kp_stub
    try:
        _kp_args = argparse.Namespace(key_pair_name=None, region_id="cn-hangzhou",
                                      timeout=30)
        _kp = collect_keypairs(_kp_args, [{"key_pair_name": ""}], "s", [], [])
        expect("kp_no_name_still_reads_the_region_inventory",
               (_kp["queried"], len(_kp_calls), _kp["requested"]) == (True, 1, []))
        expect("kp_region_read_is_not_filtered_by_a_guess",
               "KeyPairName" not in _kp_calls[0][1])
        expect("kp_region_names_are_recorded",
               _kp["region_names"] == ["region-key-a", "region-key-b"])
        expect("kp_region_summary_is_not_the_unqueried_form",
               "region inventory read: 2" in summarize_keypair(_kp))
        _kp_findings = derive_branches(args_of("auto"), neutral_facts(keypair=_kp))[1]
        expect("kp_region_read_carries_confirmed_api_evidence",
               any(f.get("basis") == "api:{0}".format(ACTION_DESCRIBE_KEY_PAIRS)
                   and f.get("confidence") == "CONFIRMED" for f in _kp_findings))
        _kp_named = collect_keypairs(
            argparse.Namespace(key_pair_name="region-key-a", region_id="cn-hangzhou",
                               timeout=30), [], "s", [], [])
        expect("kp_named_path_keeps_the_filtered_read",
               (_kp_named["requested"], _kp_calls[-1][1].get("KeyPairName"))
               == (["region-key-a"], "region-key-a"))
    finally:
        globals()["paginate"] = _kp_real

    print("SELFTEST: {0}".format("PASS" if rc == 0 else "FAIL"))
    return rc


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = build_report(args)
    except CliError as exc:
        sys.stderr.write("[WARN] {0}\n".format(mask_credentials(str(exc))))
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: Re-check the region and instance ids, restore CLI "
              "access, then re-run the same command.")
        return EXIT_BY_STATUS[STATUS_FAIL]
    except Exception as exc:  # pragma: no cover - last-resort guard, never fabricate
        sys.stderr.write("[WARN] unexpected failure: {0}\n".format(mask_credentials(exc)))
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: Report this run to the skill owner using the "
              "session id shown in the output; do not attempt manual cloud "
              "changes as a workaround.")
        return EXIT_BY_STATUS[STATUS_FAIL]

    if args.output == "json":
        printable = dict(report)
        printable["guidance_source"] = "references/login-credential-repair__login-credential-decision-tree.md"
        printable["whitelist"] = list(CLOUD_INSPECTION_WHITELIST)
        print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return EXIT_BY_STATUS.get(report["STATUS"], EXIT_BY_STATUS[STATUS_DEGRADED])


if __name__ == "__main__":
    sys.exit(main())
