#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ram_policy_diagnosis.py -- single entry point for
area:ram-policy-diagnosis (RAM sub-account & permission-policy
diagnosis for ECS)
=====================================================================
SECURITY / OPERATING MODEL:
  * Cloud evidence calls made by this script are non-mutating queries
    (sts GetCallerIdentity, ecs DescribeInstances, ecs DescribeInvocations)
    executed through the shared CLI layer (scripts/areas/ram_policy_diagnosis/_cli.py) with per-call
    timeouts, retry-with-backoff and credential masking.
  * ecs:run-command (OpenAPI operation RunCommand) is the ONE write-attribute
    action this script can reach, and ONLY in --guest-check mode, ONLY with a
    command taken verbatim from
    the embedded observation-only whitelist (_constants.GUEST_COMMAND_
    WHITELIST), and ONLY after the caller passes --confirm, which is valid
    for that single invocation. The agent MUST first show the customer the
    command, its scope and its observation-only nature and obtain agreement
    (SKILL.md "User Confirmation"). Any request to run a command outside
    the whitelist is refused: the script prints the manual-guidance refusal
    and never dispatches it.
  * The script NEVER touches RAM APIs, never grants or revokes anything,
    never disables or removes keys, roles or identities. RAM-side changes
    are manual main-account console operations; this tool only decodes,
    verifies what cloud queries allow, and generates paste-ready policy
    text plus the exact manual steps.
  * No credential handling: authentication is the aliyun CLI default
    credential chain; never pass or print key material.

Modes (mutually exclusive):
  default            triage: decode the customer error text, classify the
                     root cause, verify instance visibility, emit the
                     four-part answer (verdict / paste-able policy /
                     manual grant steps / boundary + handoff).
  --list-templates   list embedded policy template ids.
  --template ID      print one policy template (JSON + evidence labels).
  --lookup-action X  resolve an action name to its owning product +
                     evidence label (no API call).
  --list-guest-commands   show the observation-only guest whitelist.
  --guest-check      dispatch ONE whitelisted guest command (requires
                     --command, --instance-id, --region-id, --confirm).

Output contract (anti-hallucination L1):
  Human mode: sections + a final "Summary"; every run ends with
      STATUS: OK|DEGRADED|FAIL
      NEXT_ACTION: <single imperative instruction>
  --json mode adds machine fields status / next_action / summary /
  key_findings / suggestions / errors / auto_filled. Empty or failed
  evidence still emits these fields; nothing is invented.

Usage examples:
  python3 ram_policy_diagnosis.py --region-id cn-hangzhou \
      --instance-id i-bp1example0b79486034 \
      --error-text "403 no permission ... RAM ... AliyunECSFullAccess granted"
  python3 ram_policy_diagnosis.py \
      --error-text "User has no permission to do the action: (ListExecutionRiskyTasks)" \
      --skip-api --json
  python3 ram_policy_diagnosis.py --lookup-action ecs-workbench:ChatMessages
  python3 ram_policy_diagnosis.py --guest-check --region-id cn-hangzhou \
      --instance-id i-bp1example0b79486034 --command whoami --confirm
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import binascii
import json
import re
import sys
import time

import _cli
from _constants import (
    ACTION_EXTRACT_PATTERNS,
    ACTION_OWNERS,
    AK_LEAK_STEPS,
    BARE_ACTION_HINTS,
    BRANCH_TITLES,
    CAPABILITY_CHAINS,
    DEFAULT_TIMEOUT,
    DENIAL_SIGNAL_PATTERNS,
    DOC_FOR_BRANCH,
    ECS_API_VERSION,
    ECS_RUN_TYPE_SHELL,
    EXCLUSION_SIGNAL_PATTERNS,
    GUEST_COMMAND_REJECT_NOTE,
    GUEST_COMMAND_WHITELIST,
    GUEST_CONFIRMATION_BRIEF,
    GRANT_STEPS,
    HANDOFF_TARGETS,
    HELP_DOCS,
    MAX_ERROR_TEXT_CHARS,
    OS_USER_NOTE,
    POLL_INTERVAL_SECONDS,
    POLL_MAX_ATTEMPTS,
    POLICY_TEMPLATES,
    ROLE_FLOW_STEPS,
    SCOPE_MODEL,
    SITE_ACCOUNT_NOTE,
    SKILL_NAME,
    SLR_NOTE,
    SYNTAX_RULES,
    TEMPLATE_GUIDANCE_IDS,
    VERIFICATION_CHECKLIST,
)

# ---------------------------------------------------------------------------
# Input validation (argument-list subprocess; strict regex guards, no shell)
# ---------------------------------------------------------------------------

_REGION_RE = re.compile(r"^[a-z][a-z0-9-]{2,30}$")
_INSTANCE_RE = re.compile(r"^i-[a-z0-9]{4,40}$")
_RG_RE = re.compile(r"^rg-[a-z0-9]{4,40}$")
_IDENT_RE = re.compile(r"^[A-Za-z0-9@._-]{1,128}$")
_ACTION_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}:[A-Z][A-Za-z0-9]{2,60}$")
_BARE_ACTION_RE = re.compile(r"^[A-Z][A-Za-z0-9]{2,60}$")


def _region_type(value: str) -> str:
    v = value.strip().lower()
    if not _REGION_RE.match(v):
        raise argparse.ArgumentTypeError(
            f"invalid --region-id '{value}': expected e.g. cn-hangzhou")
    return v


def _instance_type(value: str) -> str:
    v = value.strip()
    if not _INSTANCE_RE.match(v):
        raise argparse.ArgumentTypeError(
            f"invalid --instance-id '{value}': expected i-<alnum>")
    return v


def _rg_type(value: str) -> str:
    v = value.strip()
    if not _RG_RE.match(v):
        raise argparse.ArgumentTypeError(
            f"invalid --resource-group-id '{value}': expected rg-<alnum>")
    return v


# Boundary assertions for the validators (batch rule: pure functions carry
# inline normal/boundary/invalid checks): valid shapes pass, hostile shapes
# are rejected before any subprocess is built.
assert _REGION_RE.match("cn-hangzhou") and not _REGION_RE.match("cn; rm -")
assert _INSTANCE_RE.match("i-bp1example0b79486034")
assert not _INSTANCE_RE.match("i-123; rm -rf /")
assert _RG_RE.match("rg-aek67smrdjuqmqa") and not _RG_RE.match("rg-..")
assert _IDENT_RE.match("someone@1234567890.onaliyun.com")
assert not _IDENT_RE.match("bad name with spaces")


# ---------------------------------------------------------------------------
# Pure decoding functions (K1 / K3)
# ---------------------------------------------------------------------------

def truncate_error_text(text: str) -> tuple[str, bool]:
    """Cap the pasted error text; returns (text, truncated)."""
    if text and len(text) > MAX_ERROR_TEXT_CHARS:
        return text[:MAX_ERROR_TEXT_CHARS], True
    return text or "", bool(text and len(text) > MAX_ERROR_TEXT_CHARS)


def find_denial_signals(text: str) -> list[dict]:
    """Match RAM-denial signal patterns against customer error text."""
    out = []
    for key, pattern, meaning in DENIAL_SIGNAL_PATTERNS:
        if re.search(pattern, text):
            out.append({"signal": key, "meaning": meaning})
    return out


def find_exclusion_signals(text: str) -> list[dict]:
    """Match non-permission (handoff) signal patterns."""
    out = []
    for key, pattern, meaning, area in EXCLUSION_SIGNAL_PATTERNS:
        if re.search(pattern, text):
            out.append({"signal": key, "meaning": meaning, "area": area})
    return out


def resolve_action_owner(token: str) -> dict:
    """Resolve an action token to product + evidence label. Pure function."""
    entry = {"action": token, "prefix": "", "product": "unknown product",
             "caveat": "",
             "evidence": "no catalog entry -- outside this skill's call "
                         "surface; never guessed"}
    prefix = ""
    bare = token
    if ":" in token:
        prefix, _, bare = token.partition(":")
        prefix = prefix.lower()
        entry["prefix"] = prefix
        owner = ACTION_OWNERS.get(prefix)
        if owner:
            entry["product"], entry["caveat"] = owner[0], owner[1]
        else:
            entry["product"] = (f"prefix '{prefix}' is not in the embedded "
                                f"catalog -- do NOT guess the product")
    else:
        hinted = BARE_ACTION_HINTS.get(bare.lower())
        if hinted:
            entry["prefix"] = hinted
            owner = ACTION_OWNERS.get(hinted)
            if owner:
                entry["product"], entry["caveat"] = owner[0], owner[1]
    if token in ("ecs:DescribeInstances",
                 "ecs:DescribeInvocations", "sts:GetCallerIdentity") or \
            bare in ("DescribeInstances", "RunCommand",
                     "DescribeInvocations", "GetCallerIdentity"):
        entry["evidence"] = ("verified for THIS build (this skill's own call "
                             "surface)")
    elif entry["prefix"] in ("ecs-workbench", "oos", "bss") or \
            bare.lower() in BARE_ACTION_HINTS or \
            (entry["prefix"] == "ecs" and bare.lower() in
             ("describeinvocationresults", "describecloudassistantstatus",
              "listtagresources", "runinstances")):
        entry["evidence"] = ("ticket-cited (quoted in a real support ticket, "
                             "NOT verified against the OpenAPI contract; never "
                             "invoked by "
                             "this skill, usable only in labelled templates)")
    return entry


def extract_actions(text: str, api_hint: str = "") -> list[dict]:
    """Pull action names out of the customer error text + api hint."""
    found: list[str] = []
    for pattern in ACTION_EXTRACT_PATTERNS:
        for m in re.finditer(pattern, text):
            tok = m.group(1)
            if tok not in found:
                found.append(tok)
    if api_hint:
        hint = api_hint.strip()
        if hint not in found and (_BARE_ACTION_RE.match(hint)
                                  or _ACTION_RE.match(hint)):
            found.append(hint)
    return [resolve_action_owner(t) for t in found]


def match_chains(text: str) -> list[dict]:
    """Map the error/question text onto capability chains (K3 routing)."""
    out = []
    for key, pattern, template_ids, explanation in CAPABILITY_CHAINS:
        if re.search(pattern, text):
            out.append({"chain": key, "templates": template_ids,
                        "explanation": explanation})
    return out


def classify_branch(denials: list[dict], exclusions: list[dict],
                    chains: list[dict], actions: list[dict],
                    scope_clues: list[str]) -> str:
    """Deterministic root-cause branch selection (K2). Pure function.

    Priority: consultative chains survive without a denial; strong
    exclusions without a denial route to the handoff branch; with a denial
    the order is feature-chain action gap -> invalid syntax wording ->
    scope/deny mismatch -> role -> incident -> planning -> unknown denial.
    """
    strong = {d["signal"] for d in denials}
    has_denial = bool(strong & {"http-403", "no-permission", "not-authorized",
                                "deny-rule-hit", "ram-tagged-denial",
                                "ram-suffixed-code"})
    consult_map = {"ak-leak-incident": "security-incident",
                   "os-user-vs-ram-user": "os-user-confusion",
                   "least-privilege-planning": "identity-planning",
                   "oos-role-flow": "role-flow",
                   "role-generic": "role-flow"}
    prefer = set(consult_map)
    if not has_denial:
        for ch in chains:
            if ch["chain"] in prefer:
                return consult_map[ch["chain"]]
        if exclusions:
            return "not-permission"
        if denials or actions:
            return "unknown-denial"
        return "ambiguous"
    if any(a["prefix"] in ("ecs-workbench", "oos") for a in actions) or \
            any(c["chain"] in ("workbench-chat", "oos-package-install",
                               "instance-create-chain") for c in chains):
        return "missing-action-chain"
    joined = " ".join(scope_clues).lower()
    if ("does not support ram" in joined or "not support ram" in joined
            or "specified resource" in joined):
        return "syntax-invalid"
    if "deny-rule-hit" in strong or scope_clues:
        return "grant-context-mismatch"
    if any(c["chain"] in ("oos-role-flow", "role-generic") for c in chains):
        return "role-flow"
    if any(c["chain"] == "ak-leak-incident" for c in chains):
        return "security-incident"
    if any(c["chain"] == "least-privilege-planning" for c in chains):
        return "identity-planning"
    return "unknown-denial"


SCOPE_CLUE_PATTERN = re.compile(
    r"(?i)resource ?group|rg-[a-z0-9]{6,}|aliyunecsfull|full ?access"
    r"|granted|already (?:been )?(?:authorized|granted)|attached"
    r"|still.{0,20}(?:denied|no permission|cannot|invisible)|invisible"
    r"|cannot see|can'?t see|mobile|phone|app")

# Self-check block for the pure functions (batch rule: normal / boundary /
# invalid inputs asserted at import time).
_d = find_denial_signals(
    "User has no permission to do the action: (ListExecutionRiskyTasks)")
assert [x["signal"] for x in _d] == ["no-permission"], _d
# A bare RAM-suffixed code carries no status and no prose, so it needs its own
# signal; without it such input used to classify as "ambiguous".
_d2 = find_denial_signals("the console returned a code: AccessProblem.RAM")
assert [x["signal"] for x in _d2] == ["ram-suffixed-code"], _d2
assert classify_branch(_d2, [], [], [], []) == "unknown-denial"
_e = find_exclusion_signals("the website says blocked by cors policy")
assert [x["area"] for x in _e] == ["application-layer"], _e
assert find_exclusion_signals("403 no permission ram on ecs") == []
_a = extract_actions("", api_hint="RunInstances")
assert _a and _a[0]["prefix"] == "ecs", _a
assert _a[0]["evidence"].startswith("ticket-cited"), _a[0]["evidence"]
assert _a[0]["evidence"] == resolve_action_owner(
    "oos:StartExecution")["evidence"]
_a2 = extract_actions("action: (ChatMessages) please")
assert _a2 and _a2[0]["prefix"] == "ecs-workbench", _a2
assert resolve_action_owner("ecs:DescribeInstances")["evidence"].startswith(
    "verified")
assert resolve_action_owner("bogus:DoSomething")["product"].startswith("prefix")
assert classify_branch(_d, [], match_chains(
    "install web vs code via workbench failed"), _a2, []) == \
    "missing-action-chain"
assert classify_branch([], _e, [], [], []) == "not-permission"
assert classify_branch(
    [{"signal": "ram-tagged-denial", "meaning": ""}], [], [], [],
    ["only resource group rg-aek67smrdjuqmqa granted"]) == \
    "grant-context-mismatch"
assert classify_branch(
    find_denial_signals("still no permission although granted"), [],
    match_chains("I granted AliyunECSFullAccess already"), [],
    ["aliyunecsfullaccess attached"]) == "grant-context-mismatch"
assert classify_branch(
    find_denial_signals("denied by an explicit deny rule"), [], [], [],
    []) == "grant-context-mismatch"
assert classify_branch([], [], match_chains(
    "my accesskey leaked and someone created a malicious sub user"), [],
    []) == "security-incident"
assert classify_branch([], [], [], [], []) == "ambiguous"


def collect_scope_clues(text: str, resource_group_id: str,
                        ram_user: str) -> list[str]:
    clues = [m.group(0) for m in SCOPE_CLUE_PATTERN.finditer(text or "")]
    if resource_group_id:
        clues.append(f"resource group id supplied: {resource_group_id}")
    if ram_user:
        clues.append(f"RAM user identity supplied: {ram_user}")
    return clues


# ---------------------------------------------------------------------------
# Cloud evidence (K5) -- all non-mutating; degraded on failure, never invented
# ---------------------------------------------------------------------------

def _record_evidence_error(report: dict, what: str, e: _cli.CliError,
                           impact: str) -> None:
    code = e.code or "Unknown"
    if _cli.is_permission_error(e):
        hint = ("the credential running THIS diagnosis lacks the action -- "
                "grant it per references/ram-policies.md (NoPermission "
                "family)")
    else:
        hint = impact
    report["errors"].append({"step": what, "code": code,
                             "message": str(e)[:300], "impact": hint})
    print(f"[WARN] {what}: {code}: {str(e)[:200]}", file=sys.stderr)


def gather_identity(report: dict, profile: str | None) -> None:
    try:
        report["evidence"]["identity"] = _cli.resolve_caller_identity(
            profile=profile)
    except _cli.CliError as e:
        _record_evidence_error(
            report, "sts GetCallerIdentity", e,
            "identity not verified; every finding below carries that caveat")


def gather_instance_visibility(report: dict, region: str, instance_id: str,
                               profile: str | None) -> None:
    """DescribeInstances for the single instance; record real fields only."""
    params = {"RegionId": region, "InstanceIds": json.dumps([instance_id]),
              "PageSize": "50"}
    try:
        body = _cli.call("ecs", "DescribeInstances", params, region=region,
                         profile=profile, timeout=DEFAULT_TIMEOUT)
    except _cli.CliError as e:
        _record_evidence_error(
            report, f"ecs DescribeInstances (region {region})", e,
            "instance visibility unverified: cannot tell 'not authorized' "
            "from 'not in this account/region'")
        return
    instances = (body.get("Instances") or {}).get("Instance") or []
    ev = report["evidence"]
    ev["queried_region"] = region
    if not instances:
        ev["instance_visibility"] = {
            "instance_id": instance_id,
            "visible_in_queried_region": False,
            "note": ("not visible to THIS credential in this region: either "
                     "the id is wrong, the instance lives in another region/"
                     "account, or the diagnostic credential itself lacks "
                     "visibility -- distinguish 'invisible to you' from "
                     "'does not exist' before blaming RAM"),
        }
        return
    inst = instances[0]
    tags = (inst.get("Tags") or {}).get("Tag") or []
    ev["instance_visibility"] = {
        "instance_id": inst.get("InstanceId"),
        "visible_in_queried_region": True,
        "status": inst.get("Status"),
        "resource_group_id": inst.get("ResourceGroupId") or "(none)",
        "zone_id": inst.get("ZoneId"),
        "instance_name": inst.get("InstanceName"),
        "tag_count": len(tags),
    }


def compare_scope_context(report: dict, resource_group_id: str) -> None:
    vis = report["evidence"].get("instance_visibility")
    if not vis or not vis.get("visible_in_queried_region"):
        return
    actual = vis.get("resource_group_id") or "(none)"
    if resource_group_id:
        match = (actual == resource_group_id)
        report["evidence"]["resource_group_match"] = {
            "supplied": resource_group_id, "actual": actual, "match": match,
            "note": ("grant and console context must use the SAME resource "
                     "group; mismatch explains 'policy attached yet denied' "
                     "(ticket T-EE03C367 pattern)"
                     if not match else
                     "resource group binding matches the supplied scope"),
        }
    if actual == "(none)":
        report["evidence"].setdefault("findings", []).append(
            "instance carries NO resource-group binding: a resource-group-"
            "scoped grant can never match it; the grant must be account-"
            "level (or the instance moved into the group -- a manual step)")


def gather_tag_scope(report: dict, region: str, instance_id: str,
                     tag_key: str, tag_value: str | None,
                     profile: str | None) -> None:
    params = {"RegionId": region, "InstanceIds": json.dumps([instance_id]),
              "PageSize": "50", "Tag.1.Key": tag_key}
    if tag_value:
        params["Tag.1.Value"] = tag_value
    try:
        body = _cli.call("ecs", "DescribeInstances", params, region=region,
                         profile=profile, timeout=DEFAULT_TIMEOUT)
    except _cli.CliError as e:
        _record_evidence_error(report, "ecs DescribeInstances (tag scope)", e,
                               "tag-scoped visibility unverified")
        return
    found = ((body.get("Instances") or {}).get("Instance") or [])
    report["evidence"]["tag_scope"] = {
        "tag": tag_key + ("=" + tag_value if tag_value else ""),
        "instance_visible_under_tag": bool(found),
    }


# ---------------------------------------------------------------------------
# Guest evidence (K6) -- confirmation-gated, whitelist-exact, one command
# ---------------------------------------------------------------------------

def run_guest_check(args: argparse.Namespace) -> tuple[int, dict]:
    summary: dict = {"mode": "guest-check", "command_key": args.command,
                     "instance_id": args.instance_id,
                     "region": args.region_id, "status": "OK",
                     "errors": [], "auto_filled": {}}
    command = GUEST_COMMAND_WHITELIST.get(args.command or "")
    if not command:
        print("[ERROR] --command must be one of the embedded whitelist keys:",
              file=sys.stderr)
        for k, v in GUEST_COMMAND_WHITELIST.items():
            print(f"  {k}: {v}", file=sys.stderr)
        print(f"[ERROR] {GUEST_COMMAND_REJECT_NOTE}", file=sys.stderr)
        summary["status"] = "FAIL"
        _emit_status("FAIL", "refuse: choose a whitelisted --command key "
                             "(--list-guest-commands) or ask the instance "
                             "owner to run the check manually")
        return 1, summary

    if not args.confirm:
        print("=" * 70)
        print("CONFIRMATION REQUIRED (command NOT dispatched yet)")
        print("=" * 70)
        print(GUEST_CONFIRMATION_BRIEF.format(
            instance_id=args.instance_id, region_id=args.region_id,
            command=command))
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: show this brief to the customer and, after they "
              "agree, re-run the same command with --confirm (confirmation "
              "is valid for this single invocation only)")
        summary["status"] = "FAIL"
        summary["gated"] = True
        return 1, summary

    _cli.check_cli_available()
    params = {
        "RegionId": args.region_id,
        "Type": ECS_RUN_TYPE_SHELL,
        "CommandContent": command,
        "Name": f"{SKILL_NAME}-diag",
        "Description": "observation-only diagnostic dispatched by the ECS "
                       "RAM policy diagnosis skill (whitelisted)",
        "Timeout": "30",
        "InstanceId.1": args.instance_id,
    }
    try:
        body = _cli.call("ecs", "RunCommand", params, region=args.region_id,
                         profile=args.profile, timeout=DEFAULT_TIMEOUT)
    except _cli.CliError as e:
        code = e.code or "Unknown"
        if _cli.is_permission_error(e):
            extra = ("the operating identity lacks ecs:run-command -- grant "
                     "it per references/ram-policies.md (NoPermission family)")
        else:
            extra = ("check the Cloud Assistant agent on the instance; this "
                     "skill never retries the same check through another "
                     "execution channel")
        print(f"[WARN] RunCommand failed: {code}", file=sys.stderr)
        print(f"[WARN] {extra}", file=sys.stderr)
        summary["errors"].append({"step": "ecs RunCommand", "code": code,
                                  "message": str(e)[:300]})
        summary["status"] = "DEGRADED"
        _emit_status("DEGRADED", "guest evidence unavailable; fall back to "
                                 "asking the customer to run the whitelisted "
                                 "command inside the instance and paste the "
                                 "output back")
        return 0, summary

    invoke_id = str(body.get("InvokeId") or "")
    summary["invoke_id"] = invoke_id
    result = poll_invocation(args, invoke_id, summary)
    if result is None:
        summary["status"] = "DEGRADED"
        _emit_status("DEGRADED", "the command was accepted but no result "
                                 "arrived in the polling window; ask the "
                                 "customer for the in-guest output directly")
        return 0, summary
    summary["invocation"] = result
    print("=" * 70)
    print(f"Guest diagnostic result (invoke id {invoke_id})")
    print("=" * 70)
    print(f"  command            : {command}")
    print(f"  invocation status  : {result['invocation_status']}")
    print(f"  exit code          : {result['exit_code']}")
    if result.get("error_info"):
        print(f"  error info         : {result['error_info']}")
    print("  output:")
    for line in (result["output"] or "(empty)").splitlines():
        print(f"    {line}")
    if result["invocation_status"] != "Success":
        summary["status"] = "DEGRADED"
        _emit_status("DEGRADED", "relay the status and error info verbatim; "
                                 "do not retry with other commands")
        return 0, summary
    _emit_status("OK", "use the guest output together with the triage "
                       "report to settle the OS-user-vs-RAM-user or "
                       "command-channel-health question")
    return 0, summary


def poll_invocation(args: argparse.Namespace, invoke_id: str,
                    summary: dict) -> dict | None:
    if not invoke_id:
        return None
    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        try:
            body = _cli.call(
                "ecs", "DescribeInvocations",
                {"RegionId": args.region_id, "InvokeId": invoke_id,
                 "IncludeOutput": "true"},
                region=args.region_id, profile=args.profile,
                timeout=DEFAULT_TIMEOUT)
        except _cli.CliError as e:
            _record_evidence_error(summary, "ecs DescribeInvocations", e,
                                   "invocation result unreadable")
            return None
        invs = (body.get("Invocations") or {}).get("Invocation") or []
        if invs:
            insts = ((invs[0].get("InvokeInstances") or {})
                     .get("InvokeInstance") or [])
            if insts:
                one = insts[0]
                raw = str(one.get("Output") or "")
                output = ""
                if raw:
                    try:
                        output = base64.b64decode(raw).decode(
                            "utf-8", "replace")
                    except (binascii.Error, ValueError):
                        output = "(output not base64; raw truncated) " + raw[:120]
                return {
                    "invocation_status": str(
                        one.get("InvocationStatus") or ""),
                    "exit_code": one.get("ExitCode"),
                    "output": _cli._clean_stderr(output),
                    "error_info": str(one.get("ErrorInfo") or ""),
                }
        if attempt < POLL_MAX_ATTEMPTS:
            time.sleep(POLL_INTERVAL_SECONDS)
    return None


# ---------------------------------------------------------------------------
# Report assembly (the four-part answer, K1-K8)
# ---------------------------------------------------------------------------

def template_guidance(tid: str) -> dict | None:
    """Guidance pseudo-templates carried as constant blocks."""
    if tid == "role_flow_steps":
        return {"title": "RAM role flow steps (manual, main account)",
                "steps": ROLE_FLOW_STEPS}
    if tid == "slr_note":
        return {"title": "Service-linked roles", "note": SLR_NOTE}
    if tid == "ak_leak_steps":
        return {"title": "AccessKey containment steps (manual-only)",
                "steps": AK_LEAK_STEPS}
    if tid == "os_user_note":
        return {"title": "OS user vs RAM user", "note": OS_USER_NOTE}
    if tid == "scope_model_note":
        return {"title": "Scope model", "scopes": SCOPE_MODEL}
    if tid == "t_syntax_note":
        return {"title": "Policy syntax rules",
                "rules": [r[0] for r in SYNTAX_RULES]}
    return None


def build_policy_document(template_ids: list[str]) -> dict | None:
    statements = []
    for tid in template_ids:
        tpl = POLICY_TEMPLATES.get(tid)
        if tpl:
            statements.append(dict(tpl["statement"]))
    if not statements:
        return None
    return {"Version": "1", "Statement": statements}


def branch_template_ids(branch: str, chains: list[dict]) -> list[str]:
    ids: list[str] = []
    for ch in chains:
        for t in ch["templates"]:
            if t not in ids:
                ids.append(t)
    if branch == "grant-context-mismatch":
        for t in ("t1_describe_instances", "t_syntax_note"):
            if t not in ids:
                ids.append(t)
    elif branch == "role-flow" and "role_flow_steps" not in ids:
        ids.append("role_flow_steps")
    elif branch == "identity-planning":
        for t in ("t6_least_privilege_read", "scope_model_note"):
            if t not in ids:
                ids.append(t)
    if not ids and branch in ("unknown-denial", "syntax-invalid"):
        ids.append("t_syntax_note")
    return ids


_NOTPERM_TICKETS = {
    "resource-lifecycle": "T-337347EB", "application-layer": "T-913B2393",
    "security-group": "T-D5229C33", "guest-resource": "T-87674B21",
    "account-system": "T-D0578489", "platform-policy": "T-7621C755",
    "billing-image": "T-920B4F23", "instance-state": "T-28ED5673",
    "backup-restore": "T-50DCE95E", "account-verification": "T-8FA544FE",
    "connection-method": "T-2B09C359",
}


def _area_ticket(area: str) -> str:
    return _NOTPERM_TICKETS.get(area, "")


def _visibility_findings(vis: dict, branch: str) -> list[str]:
    if branch == "not-permission":
        return []
    return [f"instance {vis.get('instance_id')} exists in the queried "
            f"region (state {vis.get('status')}), bound to resource group "
            f"{vis.get('resource_group_id')}"]


def assemble_triage(args: argparse.Namespace) -> dict:
    raw_text = args.error_text or ""
    text, truncated = truncate_error_text(raw_text)
    if args.api:
        text = (text + " " + args.api).strip()
    report: dict = {
        "skill": SKILL_NAME,
        "ecs_api_version": ECS_API_VERSION,
        "inputs": {"region_id": args.region_id,
                   "instance_id": args.instance_id,
                   "resource_group_id": args.resource_group_id,
                   "ram_user": args.ram_user, "api": args.api,
                   "error_text_chars": len(raw_text),
                   "error_text_truncated": truncated},
        "decode": {}, "classification": {}, "evidence": {},
        "recommendation": {}, "boundary": {}, "errors": [], "auto_filled": {},
    }
    if truncated:
        report["auto_filled"]["error_text"] = (
            f"truncated to {MAX_ERROR_TEXT_CHARS} chars for pattern matching")

    denials = find_denial_signals(text)
    exclusions = find_exclusion_signals(text)
    actions = extract_actions(text, api_hint=args.api or "")
    chains = match_chains(text)
    scope_clues = collect_scope_clues(args.error_text or "",
                                      args.resource_group_id, args.ram_user)
    branch = classify_branch(denials, exclusions, chains, actions, scope_clues)

    report["decode"] = {
        "denial_signals": denials,
        "exclusion_signals": exclusions,
        "extracted_actions": actions,
        "capability_chains": [{"chain": c["chain"],
                               "explanation": c["explanation"]}
                              for c in chains],
        "scope_clues": scope_clues,
    }
    report["classification"] = {
        "branch": branch,
        "title": BRANCH_TITLES.get(branch, "Ambiguous input"),
        "checklist": [f"{t}: {d}" for t, d in VERIFICATION_CHECKLIST],
    }

    template_ids = branch_template_ids(branch, chains)
    recommendation: dict = {
        "manual_grant_steps": GRANT_STEPS if branch not in (
            "not-permission", "ambiguous", "security-incident") else [],
        "template_ids": template_ids,
        "policy_document": build_policy_document(template_ids),
        "policy_document_evidence": (
            "action names inside carry per-template evidence labels; "
            "ticket-cited names are NOT verified -- see "
            "references/ram-policy-diagnosis__policy-templates.md"),
        "docs": [{"id": d, "url": HELP_DOCS[d]}
                 for d in DOC_FOR_BRANCH.get(branch, []) if d in HELP_DOCS],
    }
    if branch == "not-permission":
        recommendation["handoff_note"] = (
            "no RAM action is required here; deliver the handoff line below "
            "instead of a policy grant")
    if branch == "security-incident":
        recommendation["manual_grant_steps"] = []
    report["recommendation"] = recommendation

    handoffs = []
    for ex in exclusions:
        target, why = HANDOFF_TARGETS.get(
            ex["area"], ("human support", "adjacent area; this skill carries "
                                          "no matching diagnosis"))
        handoffs.append({"area": ex["area"], "signal": ex["signal"],
                         "target": target, "why": why,
                         "evidence_ticket": _area_ticket(ex["area"])})
    if branch == "not-permission" and not handoffs:
        handoffs.append({"area": "unknown", "signal": "none",
                         "target": "human support",
                         "why": "no recognizable RAM denial",
                         "evidence_ticket": ""})
    report["boundary"] = {
        "handoffs": handoffs,
        "site_account_note": (SITE_ACCOUNT_NOTE if any(
            h["area"] == "account-system" for h in handoffs) else ""),
        "never_done": [
            "any RAM console or RAM API change (grants, policy edits, role "
            "or identity removal) -- main-account manual steps only, exactly "
            "as ticket staff never operated customer accounts",
            "any in-guest command outside the observation-only whitelist",
            "any cloud resource change: nothing is created, modified, "
            "released or restarted anywhere",
        ],
    }

    if not args.skip_api and branch != "ambiguous":
        gather_identity(report, args.profile)
        if args.region_id and args.instance_id:
            gather_instance_visibility(report, args.region_id,
                                       args.instance_id, args.profile)
            compare_scope_context(report, args.resource_group_id or "")
            if args.tag_key:
                gather_tag_scope(report, args.region_id, args.instance_id,
                                 args.tag_key, args.tag_value, args.profile)
            vis = report["evidence"].get("instance_visibility") or {}
            if vis.get("visible_in_queried_region"):
                report["evidence"].setdefault(
                    "findings", []).extend(_visibility_findings(vis, branch))
        else:
            report["auto_filled"]["evidence_calls"] = (
                "visibility check skipped: --region-id and --instance-id "
                "were not both provided; identity check still ran")
    elif args.skip_api:
        report["auto_filled"]["evidence_calls"] = (
            "skipped on request (--skip-api); report is decode + embedded "
            "knowledge only")

    if branch == "ambiguous" and not args.error_text and not args.api:
        report["status"] = "FAIL"
    elif report["errors"]:
        report["status"] = "DEGRADED"
    else:
        report["status"] = "OK"
    return report


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _emit_status(status: str, next_action: str) -> None:
    print(f"\nSTATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")


def next_action_for(report: dict) -> tuple[str, str]:
    status = report["status"]
    branch = report["classification"]["branch"]
    if status == "FAIL":
        return ("FAIL", "collect the missing inputs (the customer error "
                        "text, or region+instance for the visibility check) "
                        "and run this entry script again")
    if branch == "not-permission":
        return (status, "deliver the handoff line with its evidence link; "
                        "do not open a RAM grant flow")
    nxt = ("relay the verdict, the labelled policy document and the "
           "main-account grant steps verbatim; have the customer re-test "
           "after the grant")
    if any("RunCommand" in str(e.get("step", "")) or
           "guest" in str(e.get("step", "")) for e in report["errors"]):
        nxt += "; if in-guest evidence is still needed, run --guest-check " \
               "behind the confirmation gate"
    if report["errors"]:
        nxt += "; disclose the degraded evidence lines"
    return (status, nxt)


def render_human(report: dict) -> None:
    line = "=" * 72
    print(line)
    print(f" {SKILL_NAME}")
    print(f" branch: {report['classification']['branch']} -- "
          f"{report['classification']['title']}")
    print(line)
    inp = report["inputs"]
    print("\n[Inputs]")
    for k, v in inp.items():
        if v not in (None, "", False, 0):
            print(f"  {k}: {v}")
    for k, v in report["auto_filled"].items():
        print(f"  auto-filled {k}: {v}")

    dec = report["decode"]
    print("\n[Error decode]")
    if dec["denial_signals"]:
        for d in dec["denial_signals"]:
            print(f"  DENIAL signal  : {d['signal']} -- {d['meaning']}")
    else:
        print("  no explicit RAM-denial signal matched")
    for x in dec["exclusion_signals"]:
        print(f"  EXCLUSION      : {x['signal']} -- {x['meaning']}"
              f" [area {x['area']}]")
    for a in dec["extracted_actions"]:
        print(f"  action token   : {a['action']} -> {a['product']}"
              + (f" | {a['caveat']}" if a["caveat"] else "")
              + f" | evidence: {a['evidence']}")
    for c in dec["capability_chains"]:
        print(f"  chain          : {c['chain']} -- {c['explanation']}")

    print("\n[Evidence]")
    ev = report["evidence"]
    ident = ev.get("identity")
    if ident:
        print(f"  caller identity: account {ident['account_id'] or 'n/a'}, "
              f"type {ident['identity_type']} (ARN {ident['arn'] or 'n/a'})")
    vis = ev.get("instance_visibility")
    if vis:
        if vis.get("visible_in_queried_region"):
            print(f"  instance       : {vis['instance_id']} visible in "
                  f"region {inp.get('region_id')}; state "
                  f"{vis.get('status')}; resource group "
                  f"{vis.get('resource_group_id')}")
        else:
            print(f"  instance       : {vis['instance_id']} NOT visible in "
                  f"the queried region -- {vis['note']}")
    rgm = ev.get("resource_group_match")
    if rgm:
        print(f"  scope match    : supplied {rgm['supplied']} vs actual "
              f"{rgm['actual']} -> {'MATCH' if rgm['match'] else 'MISMATCH'}"
              f" -- {rgm['note']}")
    tg = ev.get("tag_scope")
    if tg:
        print(f"  tag scope      : visible under tag {tg['tag']} -> "
              f"{tg['instance_visible_under_tag']}")
    for f in ev.get("findings", []):
        print(f"  finding        : {f}")
    for err in report["errors"]:
        print(f"  degraded step  : {err['step']} [{err['code']}] -> "
              f"{err['impact']}")
    if not any((ident, vis, rgm, tg, ev.get("findings"), report["errors"])):
        print("  none collected this run (offline or not applicable)")

    print("\n[Root-cause checklist applied]")
    for item in report["classification"]["checklist"]:
        print(f"  - {item}")

    rec = report["recommendation"]
    if rec.get("manual_grant_steps"):
        print("\n[Manual grant steps -- the MAIN ACCOUNT performs these; "
              "this skill never changes RAM]")
        for s in rec["manual_grant_steps"]:
            print(f"  {s}")
    if rec.get("template_ids"):
        print("\n[Policy / guidance templates to relay]")
        for tid in rec["template_ids"]:
            tpl = POLICY_TEMPLATES.get(tid)
            if tpl:
                print(f"  - {tid}: {tpl['title']} "
                      f"[evidence: {tpl['evidence']}]")
            else:
                g = template_guidance(tid)
                if g:
                    print(f"  - {tid}: {g['title']}")
                else:
                    print(f"  - {tid}: (unknown id -- report this)")
        if rec.get("policy_document"):
            print("\n  Paste-able policy document (Action names carry the "
                  "evidence labels above; verify ticket-cited names in the "
                  "console before relying on them):")
            for l in json.dumps(rec["policy_document"],
                                indent=2).splitlines():
                print("  " + l)
        for tid in rec["template_ids"]:
            tpl = POLICY_TEMPLATES.get(tid)
            if tpl:
                for n in tpl["notes"]:
                    print(f"  note ({tid}): {n}")
    if rec.get("handoff_note"):
        print(f"\n[Note] {rec['handoff_note']}")
    if rec.get("docs"):
        print("\n[Official docs]")
        for d in rec["docs"]:
            print(f"  - {d['url']}")

    bnd = report["boundary"]
    print("\n[Boundary & handoff]")
    for h in bnd["handoffs"]:
        print(f"  area {h['area']}: -> {h['target']} ({h['why']})"
              + (f" [evidence ticket {h['evidence_ticket']}]"
                 if h["evidence_ticket"] else ""))
    if bnd.get("site_account_note"):
        print(f"  note: {bnd['site_account_note']}")
    for n in bnd["never_done"]:
        print(f"  never: {n}")

    print("\nSummary")
    print("-------")
    for s in _build_summary(report):
        print(s)


def _build_summary(report: dict) -> list[str]:
    branch = report["classification"]["branch"]
    n_sig = len(report["decode"]["denial_signals"])
    n_ex = len(report["decode"]["exclusion_signals"])
    n_act = len(report["decode"]["extracted_actions"])
    out = [f"Checked the pasted error text for RAM-denial and "
           f"non-permission signals: {n_sig} denial signal(s), {n_ex} "
           f"exclusion signal(s), {n_act} action token(s) resolved."]
    out.append(f"Classification: {branch} -- "
               f"{report['classification']['title']}.")
    ev = report["evidence"]
    if ev.get("identity"):
        out.append(f"Evidence collected under account "
                   f"{ev['identity']['account_id'] or 'n/a'} "
                   f"({ev['identity']['identity_type']}); results reflect "
                   f"that account only.")
    if ev.get("instance_visibility"):
        out.append("Instance visibility "
                   + ("confirmed" if ev["instance_visibility"].get(
                       "visible_in_queried_region") else "NEGATIVE")
                   + " in the queried region.")
    if report["errors"]:
        out.append(f"{len(report['errors'])} evidence step(s) degraded; see "
                   f"the degraded lines -- nothing was invented for them.")
    if branch not in ("not-permission", "ambiguous"):
        out.append("Next: the main account follows the manual grant steps; "
                   "the sub-account re-tests after signing in again. This "
                   "skill does not operate RAM or any cloud change itself.")
    return out


def render_json(report: dict, status: str, nxt: str) -> None:
    kf = _build_summary(report)
    report["summary"] = kf
    report["key_findings"] = kf
    report["next_action"] = nxt
    report["suggestions"] = [
        "Relay verdict / policy document / grant steps / boundary as four "
        "parts, verbatim from this JSON.",
        "Cite only the URLs listed under references/ram-policy-diagnosis__help-docs.md; declare "
        "every auto-filled or degraded item.",
    ]
    print(json.dumps(report, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Local-only modes
# ---------------------------------------------------------------------------

def mode_list_templates() -> int:
    print("Embedded policy templates:")
    for tid, tpl in POLICY_TEMPLATES.items():
        print(f"  {tid}: {tpl['title']} [evidence: {tpl['evidence']}]")
    print("Guidance blocks:")
    for tid in TEMPLATE_GUIDANCE_IDS:
        g = template_guidance(tid)
        print(f"  {tid}: {g['title'] if g else '(missing block!)'}")
    _emit_status("OK", "print one with --template <id>, or run the default "
                       "triage mode with the customer error text")
    return 0


def mode_template(tid: str) -> int:
    tpl = POLICY_TEMPLATES.get(tid)
    if tpl:
        print(f"# {tpl['title']}")
        print(f"# evidence: {tpl['evidence']}")
        doc = {"Version": "1", "Statement": [dict(tpl["statement"])]}
        print(json.dumps(doc, indent=2))
        for n in tpl["notes"]:
            print(f"# note: {n}")
        _emit_status("OK", "have the MAIN ACCOUNT attach this policy text as "
                           "a custom policy in the RAM console; this skill "
                           "never applies grants")
        return 0
    g = template_guidance(tid)
    if g:
        print(f"# {g['title']}")
        for s in g.get("steps", []):
            print(f"  {s}")
        if g.get("note"):
            print(g["note"])
        for k, v in (g.get("scopes") or {}).items():
            print(f"  {k}: {v}")
        for r in g.get("rules", []):
            print(f"  rule: {r}")
        _emit_status("OK", "relay these manual steps alongside the customer's "
                           "denial text")
        return 0
    print(f"[ERROR] unknown template id '{tid}'; run --list-templates",
          file=sys.stderr)
    _emit_status("FAIL", "list the ids with --list-templates")
    return 1


def mode_lookup_action(name: str) -> int:
    name = name.strip()
    if not (_ACTION_RE.match(name) or _BARE_ACTION_RE.match(name)):
        print(f"[ERROR] '{name}' is not an action-name shape", file=sys.stderr)
        _emit_status("FAIL", "pass the exact token from the customer error "
                             "text, e.g. --lookup-action ChatMessages")
        return 1
    entry = resolve_action_owner(name)
    print(json.dumps(entry, indent=2))
    chain_hits = [c["chain"] for c in match_chains(name)]
    if chain_hits:
        print(f"related chains: {', '.join(chain_hits)}")
    _emit_status("OK", "run the full triage with --error-text to get the "
                       "verdict + templates for this denial")
    return 0


def mode_list_guest_commands() -> int:
    print("Observation-only guest command whitelist (exact strings):")
    for k, v in GUEST_COMMAND_WHITELIST.items():
        print(f"  {k:10s} -> {v}")
    print(GUEST_COMMAND_REJECT_NOTE)
    _emit_status("OK", "for a whitelisted key use --guest-check behind the "
                       "confirmation gate")
    return 0


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ram_policy_diagnosis.py",
        description="ECS RAM sub-account & permission-policy triage: decode "
                    "denials, verify visibility, emit labelled policy "
                    "templates and manual grant steps.",
        epilog="Evidence queries are non-mutating; the single "
               "write-attribute action ecs:run-command is limited to the "
               "whitelisted observation-only guest commands behind --confirm.",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--list-templates", action="store_true",
                      help="list embedded policy/guidance template ids")
    mode.add_argument("--template", metavar="ID",
                      help="print one template with evidence labels")
    mode.add_argument("--lookup-action", metavar="NAME",
                      help="resolve an action name to product + evidence")
    mode.add_argument("--list-guest-commands", action="store_true",
                      help="show the observation-only guest whitelist")
    mode.add_argument("--selftest", action="store_true",
                      help="run offline pure-function regression checks")
    mode.add_argument("--guest-check", action="store_true",
                      help="dispatch ONE whitelisted guest command (gated)")

    p.add_argument("--error-text", default="",
                   help="customer error message exactly as received")
    p.add_argument("--api", default="",
                   help="API name of the failing operation, e.g. RunInstances")
    p.add_argument("--region-id", type=_region_type, default=None,
                   help="ECS region id for the visibility check")
    p.add_argument("--instance-id", type=_instance_type, default=None,
                   help="ECS instance id (i-...) to verify visibility")
    p.add_argument("--resource-group-id", type=_rg_type, default=None,
                   help="rg-... the customer believes applies")
    p.add_argument("--ram-user", default=None,
                   help="RAM user login name under diagnosis")
    p.add_argument("--tag-key", default=None,
                   help="tag key for tag-scope visibility verification")
    p.add_argument("--tag-value", default=None, help="tag value")
    p.add_argument("--command", default=None,
                   help="guest-check: whitelist key "
                        "(see --list-guest-commands)")
    p.add_argument("--confirm", action="store_true",
                   help="guest-check: the customer saw the brief and agreed "
                        "(valid for this invocation only)")
    p.add_argument("--skip-api", action="store_true",
                   help="decode + knowledge only, no cloud calls")
    p.add_argument("--profile", default=None,
                   help="optional aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    return p


def _run_selftest() -> int:
    """Offline regression lock for the K1/K2/K3 decision core. The module-load
    asserts above cover the common paths; this gate additionally pins the
    previously-unasserted branches (syntax-invalid, with-denial role-flow /
    identity-planning, workbench missing-action-chain) and the template /
    truncation / validator helpers, so an edit that flips a branch or loosens a
    guard fails here before the code ever reads a real ticket. Pure functions
    only: no CLI, no credentials, no network."""
    fails: list[str] = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            fails.append(name)

    denial = find_denial_signals("got 403 Forbidden, you have no permission")
    check("deny probe yields strong signals",
          {"http-403", "no-permission"} <= {d["signal"] for d in denial})

    check("syntax-invalid via 'does not support ram'",
          classify_branch(denial, [], [], [],
                          ["this action does not support ram"]) == "syntax-invalid")
    check("syntax-invalid via 'specified resource'",
          classify_branch(denial, [], [], [],
                          ["the specified resource does not exist"]) == "syntax-invalid")

    check("role-flow with denial",
          classify_branch(denial, [], [{"chain": "oos-role-flow",
                                        "templates": [], "explanation": ""}],
                          [], []) == "role-flow")
    check("identity-planning with denial",
          classify_branch(denial, [], [{"chain": "least-privilege-planning",
                                        "templates": [], "explanation": ""}],
                          [], []) == "identity-planning")
    wb = extract_actions("", api_hint="ChatMessages")
    check("workbench action gap wins over role/scope ordering",
          wb and wb[0]["prefix"] == "ecs-workbench"
          and classify_branch(denial, [], [], wb, []) == "missing-action-chain")
    check("bare ram-suffixed code is an unknown denial, never ambiguous",
          classify_branch(find_denial_signals("code: AccessProblem.RAM"),
                          [], [], [], []) == "unknown-denial")
    check("no signal at all is ambiguous",
          classify_branch([], [], [], [], []) == "ambiguous")

    check("truncate under cap unchanged",
          truncate_error_text("short") == ("short", False))
    long_in = "x" * (MAX_ERROR_TEXT_CHARS + 500)
    t_out, t_flag = truncate_error_text(long_in)
    check("truncate over cap cuts and flags",
          t_flag is True and len(t_out) == MAX_ERROR_TEXT_CHARS)
    check("truncate empty string", truncate_error_text("") == ("", False))

    check("syntax-invalid falls back to the syntax note",
          branch_template_ids("syntax-invalid", []) == ["t_syntax_note"])
    check("role-flow appends the role steps once",
          branch_template_ids("role-flow", [{"templates": ["role_flow_steps"]}])
          == ["role_flow_steps"])
    gt = branch_template_ids("grant-context-mismatch", [])
    check("grant-context-mismatch seeds describe+syntax",
          gt == ["t1_describe_instances", "t_syntax_note"])
    check("chain templates merge ahead of branch extras, deduped",
          branch_template_ids("role-flow",
                              [{"templates": ["x", "y"]}]) == ["x", "y", "role_flow_steps"])

    doc = build_policy_document(["t1_describe_instances"])
    check("build_policy_document emits a statement",
          bool(doc and doc.get("Statement")))
    check("build_policy_document returns None when nothing resolves",
          build_policy_document(["does-not-exist"]) is None)

    clues = collect_scope_clues("only resource group rg-aek67smrdjuqmqa granted",
                                "rg-aek67smrdjuqmqa", "someone@123.onaliyun.com")
    check("collect_scope_clues finds the rg clue",
          any("resource group" in c.lower() for c in clues))
    check("collect_scope_clues appends supplied ids",
          any("resource group id supplied" in c for c in clues)
          and any("RAM user identity supplied" in c for c in clues))

    check("own-surface action is 'verified'",
          resolve_action_owner("ecs:DescribeInstances")["evidence"].startswith("verified"))
    check("unknown prefix is never guessed",
          resolve_action_owner("nosuchprod:Thing")["product"].startswith("prefix"))
    check("bare hint resolves to a known product prefix",
          resolve_action_owner("RunInstances")["prefix"] == "ecs")

    for fn, good, bad in (
        (_region_type, "cn-hangzhou", "cn-hangzhou; rm -rf /"),
        (_instance_type, "i-bp1example0b79486034", "i-bp1$(whoami)"),
        (_rg_type, "rg-aek67smrdjuqmqa", "rg-`id`"),
    ):
        check("%s accepts a valid value" % fn.__name__, fn(good) == good.strip())
        try:
            fn(bad)
            check("%s must reject injection" % fn.__name__, False)
        except argparse.ArgumentTypeError:
            check("%s rejects injection" % fn.__name__, True)

    print("=" * 72)
    print(" OFFLINE SELF-TEST (extended) -- ram_policy_diagnosis")
    print("=" * 72)
    if fails:
        for name in fails:
            print("  FAILED: %s" % name)
        print("\nSTATUS: FAIL")
        return 1
    print("  no failures across the extended decision-core checks.")
    print("\nSTATUS: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.selftest:
        return _run_selftest()
    if args.list_templates:
        return mode_list_templates()
    if args.template:
        return mode_template(args.template)
    if args.lookup_action:
        return mode_lookup_action(args.lookup_action)
    if args.list_guest_commands:
        return mode_list_guest_commands()
    if args.guest_check:
        if not (args.region_id and args.instance_id and args.command):
            print("[ERROR] --guest-check needs --region-id, --instance-id "
                  "and a whitelisted --command", file=sys.stderr)
            _emit_status("FAIL", "collect region, instance id and whitelist "
                                 "key, then re-run")
            return 1
        rc, _summary = run_guest_check(args)
        return rc

    # default triage mode
    if not args.error_text and not args.api and not args.instance_id:
        print("[ERROR] triage needs at least --error-text (preferred), "
              "--api, or --instance-id with --region-id to verify "
              "visibility", file=sys.stderr)
        print("[ERROR] Nothing is invented: the customer's error text "
              "exactly as received is the primary evidence.", file=sys.stderr)
        _emit_status("FAIL", "ask the customer for the error message as "
                             "displayed (copied text), the region, and the "
                             "instance/resource id")
        return 1

    if not args.skip_api:
        _cli.check_cli_available()
    report = assemble_triage(args)
    status, nxt = next_action_for(report)
    report["status"] = status
    if args.json:
        # Machine-readable mode MUST emit ONLY the JSON object on stdout. The
        # status and the next-action hint already live INSIDE the report
        # (report["status"] set above; report["next_action"] set in render_json).
        # The human STATUS:/NEXT_ACTION: trailer belongs to the report path only;
        # appending it after the object breaks json.loads for the aggregate harness
        # adapter (Extra data at the closing brace).
        render_json(report, status, nxt)
    else:
        render_human(report)
        print(f"\nSTATUS: {status}")
        print(f"NEXT_ACTION: {nxt}")
    return 0 if status in ("OK", "DEGRADED") else 1


if __name__ == "__main__":
    sys.exit(main())
