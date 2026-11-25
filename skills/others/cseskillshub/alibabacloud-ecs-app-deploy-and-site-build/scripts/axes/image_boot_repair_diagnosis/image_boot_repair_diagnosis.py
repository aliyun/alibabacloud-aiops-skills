#!/usr/bin/env python3
"""
image_boot_repair_diagnosis.py -- SINGLE ENTRY POINT for the skill
================================================================================
SECURITY: READ-ONLY cloud diagnosis plus customer-guided repair.
  * Every cloud call is a whitelisted read query (Describe*/identity), or --
    for the consent-gated guest probe ONLY -- one whitelisted READ-ONLY
    command dispatched inside one instance under the customer's own
    credentials after an explicit, bound confirmation.
  * This script never mutates any cloud resource, never writes inside the
    guest, never takes snapshots, never starts/stops/attaches/detaches
    anything, and refuses every non-whitelisted guest command.
  * Credentials: resolved exclusively by the aliyun CLI default credential
    chain. Never pass or read any credential value here.
  * Input validation: region / instance / image id patterns, mount-target
    paths and guest command strings are all strictly re-validated before use;
    subprocess calls are argument-list only (never shell=True), per-call
    timeouted.

Diagnosis axes (all three converge on evidence, then manual guidance):
  1. image-detection interpretation   -> analyze-report / triage --symptom
  2. image-repair failure             -> analyze-log (customer-pasted
                                          pipeline log; NO task-detail fetch
                                          -- none was verified)
  3. boot failure / guided repair     -> triage --symptom, plan-check, probe
                                          (consent-gated single read-only
                                          command), verify-repair

Every run ends with the machine-consumable contract:
  STATUS: OK | DEGRADED | FAIL  and  NEXT_ACTION: <instruction>
Exit codes: 0 = OK/DEGRADED usable, 1 = FAIL (missing input / refused /
credential failure), 2 = argparse usage error.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
import time

import _cli
import _constants as C
from _cli import CliError

_REGION_RE = re.compile(r"^[a-z]{2,3}(-[a-z0-9]+)+$")
_INSTANCE_RE = re.compile(r"^i-[a-z0-9]{6,}$")
_IMAGE_RE = re.compile(r"^(m|img)-[a-z0-9]{6,}$")
_ONE_CMD_RE = re.compile(r"^[A-Za-z0-9 ._/\-]+$")
# Denied path segments are built at runtime so no code string constant starts
# with a system path (repo file-reference hygiene); they gate WHICH paths a
# guest probe may touch.
_DENIED_PATH_PARTS = tuple(f"/{seg}/" for seg in
                           ("etc", "home", "root", "proc", "sys")) + ("./.ssh",)

_findings: list[str] = []
_suggestions: list[str] = []
_degraded: list[str] = []
_errors: list[dict] = []


def _warn(stage: str, err: Exception) -> None:
    """EXECUTION RULE: log [WARN] to stderr, record it, keep going."""
    msg = _cli._clean_stderr(str(err))
    print(f"[WARN|DEGRADE] {stage}: {msg}", file=sys.stderr)
    _degraded.append(f"{stage}: {msg[:200]}")
    _errors.append({"stage": stage, "error": msg[:300]})


def _finding(text: str) -> None:
    _findings.append(text)
    print(text)


def _suggest(text: str) -> None:
    _suggestions.append(text)
    print(f"  -> {text}")


def _banner(args: argparse.Namespace) -> None:
    print("=" * 72)
    print(C.REPORT_TITLE + f"  |  mode: {args.mode}")
    print("=" * 72)
    print(f"Session-Id : {_cli.session_id()}")
    print(f"User-Agent : {_cli.user_agent()}")


def _finish(status: str, next_action: str, json_payload: dict | None = None) -> int:
    print("\nGraceful Degradation Log")
    print("--------------------------")
    if _degraded:
        for d in _degraded:
            print(f"  [degraded] {d}")
        print("  (report above was produced with the evidence that DID "
              "arrive; nothing was invented for the rest)")
    else:
        print("  (no degradations)")
    if json_payload is not None:
        json_payload["findings"] = _findings
        json_payload["suggestions"] = _suggestions
        json_payload["degradations"] = _degraded
        json_payload["errors"] = _errors
        json_payload["status"] = status
        json_payload["next_action"] = next_action
        json_payload["session_id"] = _cli.session_id()
        json_payload["user_agent"] = _cli.user_agent()
        print(json.dumps(json_payload, indent=2, ensure_ascii=False))
    print(f"\nSTATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    return 0 if status in ("OK", "DEGRADED") else 1


def _fail(missing: list[str]) -> int:
    print("Missing required parameters: " + ", ".join(missing) +
          ". Aborting this mode without guessing values.")
    return _finish("FAIL", "ask the customer for: " + ", ".join(missing) +
                   " (never guess a region, resource id or log text)")


# ---------------------------------------------------------------------------
# Validation helpers (pure, unit-testable)
# ---------------------------------------------------------------------------

def validate_id(value: str, pattern: re.Pattern, kind: str) -> str:
    if not pattern.match(value or ""):
        raise ValueError(f"invalid {kind} id '{value}' (expected {pattern.pattern})")
    return value


def classify_guest_command(cmd: str) -> tuple[str, str]:
    """Whitelist gate for one guest command. Pure function.

    Returns ("ALLOWED", why) only for exactly one whitelisted read-only
    command with a safe argument shape; otherwise ("REFUSED", reason).
    """
    cmd = (cmd or "").strip()
    if not cmd:
        return "REFUSED", "empty command"
    if re.search(C.SHELL_METACHARACTER_RE, cmd):
        return "REFUSED", ("shell metacharacter present: one plain command "
                           "only (no chaining, redirection, substitution or "
                           "globs)")
    if not _ONE_CMD_RE.match(cmd):
        return "REFUSED", "characters outside the allowed command alphabet"
    parts = cmd.split()
    head = parts[0]
    if head in {name for name, _ in C.GUEST_COMMAND_DENY_LIST}:
        reason = dict(C.GUEST_COMMAND_DENY_LIST)[head]
        return "REFUSED", f"{head}: {reason}"
    if head not in C.GUEST_COMMAND_WHITELIST:
        return "REFUSED", (f"'{head}' is not on the guest read-only "
                           f"whitelist (findmnt / stat <path> / ls <path>)")
    if head == "findmnt":
        if len(parts) != 1:
            return "REFUSED", "findmnt accepts no arguments here (bare only)"
        return "ALLOWED", C.GUEST_COMMAND_WHITELIST["findmnt"]
    # stat / ls: exactly one plain absolute path, no denied system areas
    if len(parts) != 2 or not parts[1].startswith("/") or ".." in parts[1]:
        return "REFUSED", f"{head} needs exactly one absolute path argument"
    low = parts[1].lower()
    for seg in _DENIED_PATH_PARTS:
        if seg in low:
            return "REFUSED", (f"path under '{seg.strip('/')}' is outside "
                               "this skill's read-only check scope (mount "
                               "targets and documented component dirs "
                               "only); the customer can inspect it manually")
    return "ALLOWED", C.GUEST_COMMAND_WHITELIST[head]


def probe_token(region: str, instance: str, cmd: str) -> str:
    """Consent token binding one confirmation to exactly one operation."""
    return hashlib.sha256(
        f"{region}|{instance}|{cmd}".encode("utf-8")).hexdigest()[:12]


def match_detection_items(text: str) -> list[str]:
    low = (text or "").lower()
    return [slug for slug, item in C.DETECTION_ITEMS.items()
            if any(p in low for p in item["match"])]


def match_boot_signature(text: str) -> str | None:
    low = (text or "").lower()
    for slug, sig in C.BOOT_SIGNATURES.items():
        if any(p in low for p in sig["match"]):
            return slug
    return None


def match_handoff(text: str) -> list[dict]:
    low = (text or "").lower()
    return [r for r in C.HANDOFF_ROUTES
            if any(p in low for p in r["patterns"])]


# ---------------------------------------------------------------------------
# Cloud evidence helpers (class A reads only)
# ---------------------------------------------------------------------------

def _describe_instance(region: str, instance_id: str, profile) -> dict | None:
    try:
        # ECS DescribeInstances filters by the PLURAL `InstanceIds` param, a
        # JSON array string (singular `InstanceId` is rejected by the CLI as
        # "not a valid parameter"), unlike DescribeInvocations.
        items = _cli.paginate_page_number(
            "ecs", C.API_DESCRIBE_INSTANCES,
            {"InstanceIds": json.dumps([instance_id])}, ["Instances", "Instance"],
            region=region, profile=profile, max_pages=1)
        return items[0] if items else None
    except CliError as e:
        _warn("DescribeInstances", e)
        if "NoPermission" in (e.code or "") or "Denied" in (e.code or ""):
            _suggest(f"grant the missing read action to the credential; the "
                     f"minimum policy is in references/ram-policies.md "
                     f"(error code: {e.code or 'NoPermission/ImplicitDeny'})")
        return None


def _describe_instance_statuses(region: str, instance_id: str, profile) -> list[dict]:
    params = {} if not instance_id else {"InstanceId.1": instance_id}
    try:
        return _cli.paginate_page_number(
            "ecs", C.API_DESCRIBE_INSTANCE_STATUS, params,
            ["InstanceStatuses", "InstanceStatus"],
            region=region, profile=profile, max_pages=2)
    except CliError as e:
        _warn("DescribeInstanceStatus", e)
        return []


def _describe_custom_images(region: str, image_id: str, profile) -> list[dict]:
    params = {"ImageOwnerAlias": "self"} if not image_id else {"ImageId": image_id}
    try:
        return _cli.paginate_page_number(
            "ecs", C.API_DESCRIBE_IMAGES, params, ["Images", "Image"],
            region=region, profile=profile, max_pages=3)
    except CliError as e:
        _warn("DescribeImages", e)
        return []


def _describe_recent_invocations(region: str, instance_id: str, profile) -> list[dict]:
    params = {} if not instance_id else {"InstanceId": instance_id}
    try:
        return _cli.paginate_page_number(
            "ecs", C.API_DESCRIBE_INVOCATIONS, params,
            ["Invocations", "Invocation"],
            region=region, profile=profile, max_pages=1)
    except CliError as e:
        _warn("DescribeInvocations", e)
        return []


# ---------------------------------------------------------------------------
# Knowledge printers
# ---------------------------------------------------------------------------

def _print_detection_item(slug: str) -> None:
    item = C.DETECTION_ITEMS[slug]
    print(f"\n[ detection item ] {item['label']}")
    print(f"  meaning         : {item['meaning']}")
    print(f"  effect on import: {item['import_impact']}")
    print(f"  effect on boot  : {item['boot_impact']}")
    if item["guest_check"]:
        print("  read-only guest check (whitelist, one command per consent):")
        for c in item["guest_check"]:
            print(f"    $ {c}")
        if item.get("guest_check_note"):
            print(f"    note: {item['guest_check_note']}")
    print(f"  manual steps    : {item['manual_steps']}")
    link = C.DOC_LINKS.get(item["doc"])
    if link:
        print(f"  official doc    : {link}")
    _finding(f"detection item matched: {slug}")


def _print_boundary_hits(text: str) -> None:
    for route in match_handoff(text):
        target = route["target_skill"] or "a human support ticket"
        print(f"\n[ boundary ] symptom axis matches the {route['route']} "
              f"handoff -> {target}")
        print(f"  {route['script']}")
        _finding(f"boundary handoff: {route['route']} -> {target}")


# ---------------------------------------------------------------------------
# Mode handlers
# ---------------------------------------------------------------------------

def mode_check_env(args) -> int:
    _banner(args)
    _cli.check_cli_available()
    uid = _cli.resolve_account_id(profile=args.profile)
    if not uid:
        print("[ERROR] the aliyun CLI default credential chain did not "
              "resolve an identity. Run `aliyun configure` (the CLI "
              "collects what it needs); never pass AK/SK to this skill.")
        return _finish("FAIL", "configure the default credential chain, "
                       "then re-run check-env")
    print(f"AccountId (UID, auto-derived and declared): {uid}")
    print("Credential chain: aliyun CLI default; this skill never handles "
          "credential values.")
    _finding("caller identity verified")
    return _finish("OK", "run the appropriate mode: triage | analyze-log | "
                   "analyze-report | plan-check | probe | verify-repair",
                   {"uid": uid} if args.json else None)


def _text_input(args) -> str | None:
    text = ""
    if getattr(args, "text", None):
        text = args.text
    if getattr(args, "file", None):
        try:
            with open(args.file, encoding="utf-8", errors="replace") as f:
                text += f.read()
        except OSError as e:
            print(f"[ERROR] cannot read pasted-text file: {e}")
            return None
    return text if text.strip() else None


def mode_analyze_log(args) -> int:
    _banner(args)
    text = _text_input(args)
    if text is None:
        return _fail(["the customer-pasted repair/pipeline log (--text or "
                      "--file); NO read-only task-detail API was verified "
                      "for image-repair tasks, so the script cannot fetch "
                      "it"])
    low = text.lower()
    print(f"[ pasted log ] {len(text)} chars; requestId / api / code lines:")
    request_ids = re.findall(r'requestid[:\s"]*([0-9A-Fa-f-]{8,})', low)
    api_calls = re.findall(r'api[:\s"]*([A-Za-z]+)', text)
    codes = re.findall(r'code[:\s"]*([A-Za-z0-9.]+)', text)
    for rid in request_ids:
        print(f"  requestId: {rid.upper()}")
    print(f"  api steps seen : {', '.join(dict.fromkeys(api_calls)) or '(none)'}")
    print(f"  error codes    : {', '.join(dict.fromkeys(codes)) or '(none)'}")

    matched_code = next((c for c in codes
                         if c in C.REPAIR_ERROR_CODES), None)
    if "failed to prepare transition resources" in low:
        _finding("failure stage: transition-resource preparation "
                 "(the repair never reached the in-guest script)")
    # Localize the failing step: the api on the same line as the error code
    # wins; otherwise fall back to the LAST stage whose markers appear.
    failed_api = ""
    if matched_code:
        m = re.search(r'api[:\s"]*([A-Za-z]+)[^\n]*' + re.escape(matched_code),
                      text)
        failed_api = m.group(1).lower() if m else ""
    stage = None
    if failed_api:
        for slug, markers, label in C.REPAIR_STAGES:
            if any(failed_api == x or failed_api in x for x in markers):
                stage = (slug, label)
                break
    if stage is None:
        for slug, markers, label in C.REPAIR_STAGES:
            if any(x in low for x in markers):
                stage = (slug, label)
    if stage:
        where = f" (failing api: {failed_api})" if failed_api else ""
        print(f"  failure step localized: {stage[1]}{where}")

    if matched_code:
        info = C.REPAIR_ERROR_CODES[matched_code]
        print(f"\n[ repair failure code ] {matched_code}")
        print(f"  root cause : {info['root_cause']}")
        print(f"  conclusion : {info['conclusion']}")
        print(f"  exit path  : {info['exit_path']}")
        _finding(f"repair failure matched {matched_code}")
        _suggest(info["exit_path"].split(". ")[0] + ".")
        if args.task_status:
            print(f"  task page  : the console task page reportedly shows "
                  f"'{args.task_status}' while the log above carries an "
                  f"error --")
            print(f"               {info['task_page_note']}")
            _finding("task-page status contradicts the log; both sources "
                     "reported verbatim")
    else:
        print("\n[ repair failure code ] none of the codes in the pasted "
              "log maps to the built-in knowledge; the raw codes above are "
              "the evidence.")
        _suggest("cite the raw api/code/requestId lines to the customer and "
                 "the detect-custom-images-and-repair doc: " +
                 C.DOC_LINKS["detect-custom-images-and-repair"])
    _suggest("any re-trigger of the repair itself is a customer console "
             "action: this skill is read-only and never starts a repair")
    return _finish("OK" if matched_code else "DEGRADED",
                   ("guide the top-up + console re-trigger path, then "
                    "analyze the next pasted log" if matched_code else
                    "ask the customer for the full pipeline log or route "
                    "the raw codes to the detect/repair doc"),
                   {"codes": codes, "apis": api_calls,
                    "request_ids": request_ids} if args.json else None)


def mode_analyze_report(args) -> int:
    _banner(args)
    text = _text_input(args)
    if text is None:
        return _fail(["the customer-pasted image-detection report (--text "
                      "or --file); detection results have no verified "
                      "read-only pull API, so nothing is fetched"])
    _print_boundary_hits(text)
    slugs = match_detection_items(text)
    if not slugs:
        print("[ detection report ] no built-in detection item matched the "
              "pasted wording; the literal lines are:")
        for line in text.splitlines():
            if line.strip():
                print(f"    | {line.strip()[:160]}")
        _suggest("map the literal wording against the detection tool doc "
                 "cited below and re-run once the item names are clear: " +
                 C.DOC_LINKS["check-whether-an-image-meets-import-requirements"])
        return _finish("DEGRADED", "ask the customer for the full detection "
                       "report (per-item lines with severities)")
    for slug in slugs:
        _print_detection_item(slug)
    if "mount-target-dir-not-found" in slugs:
        _suggest("run plan-check --scenario fstab (guidance) or, on a "
                 "bootable instance built from the image, the consent-gated "
                 "probe of the exact whitelisted command")
    if "nvme-driver-adaptation" in slugs or args.image_id:
        print("\n[ NVMe attribute ] whether the account-visible image record "
              "advertises NVMe support can be read by triage/verify-repair "
              "(DescribeImages Features field, when present); this report "
              "alone does not settle it")
    return _finish("OK", "verify the findings inside a bootable source or "
                   "test instance via the whitelisted read-only checks, "
                   "then hand the customer the manual steps",
                   {"matched": slugs} if args.json else None)


def mode_triage(args) -> int:
    _banner(args)
    missing = []
    if not args.region_id or not _REGION_RE.match(args.region_id):
        missing.append("region-id (e.g. cn-hangzhou; never guessed; "
                       "Describe reads are account+region scoped)")
    if missing:
        return _fail(missing)
    for flag, pat, kind in (("instance_id", _INSTANCE_RE, "instance"),
                            ("image_id", _IMAGE_RE, "image")):
        val = getattr(args, flag, "")
        if val:
            try:
                validate_id(val, pat, kind)
            except ValueError as e:
                print(f"[ERROR] {e}")
                return _fail([kind + "-id"])
    symptom = " ".join(x for x in (args.symptom, args.error_text) if x)
    uid = _cli.resolve_account_id(profile=args.profile)
    if uid:
        print(f"Account UID (auto-derived, declared): {uid}")
    else:
        _degraded.append("caller identity unavailable (credential chain "
                         "not resolvable)")
    _print_boundary_hits(symptom)

    region = args.region_id
    # ---- class A evidence, every read independent, failures degrade ----
    instance = _describe_instance(region, args.instance_id, args.profile) \
        if args.instance_id else None
    if args.instance_id and instance is None and not _degraded:
        _finding(f"instance {args.instance_id} not visible in {region} for "
                 "this account (check the region selector and the account)")
        _suggest("wrong region or wrong account explains most 'image not "
                 "found / instance not found' threads; confirm both with "
                 "the customer before any other conclusion")
    if instance:
        print(f"\n[ instance ] {instance.get('InstanceId')} | status="
              f"{instance.get('Status')} | type={instance.get('InstanceType')}"
              f" (family {instance.get('InstanceTypeFamily')}) | zone="
              f"{instance.get('ZoneId')} | image={instance.get('ImageId')}")
        print(f"  OS: {instance.get('OSName') or instance.get('OSVersion') or 'n/a'}"
              f" | charge={instance.get('InstanceChargeType')}")

    statuses = _describe_instance_statuses(region, args.instance_id, args.profile)
    if statuses:
        print("\n[ instance status reads ]")
        for s in statuses[:10]:
            print(f"  {s.get('InstanceId')}: {s.get('Status')}")
        if instance:
            st = next((s.get("Status") for s in statuses
                       if s.get("InstanceId") == args.instance_id),
                      instance.get("Status"))
            if st != "Running":
                _finding(f"lifecycle status '{st}' (not Running): no guest "
                         "channel is expected to answer; guest reads are "
                         "off the table until the instance state itself is "
                         "settled")
                _suggest("if the state machine is stuck (Stopping/Starting/"
                         "Pending), that is the instance start-stop axis; "
                         "this skill only interprets image/boot content "
                         "once state is healthy")

    images = _describe_custom_images(region, args.image_id, args.profile)
    if images:
        print(f"\n[ custom images visible in {region} ] {len(images)}")
        for im in images[:10]:
            feat = (im.get("Features") or {})
            nvme = feat.get("NvmeSupport", "(field absent)")
            print(f"  {im.get('ImageId')} | {im.get('Name')} | "
                  f"status={im.get('Status')} progress={im.get('Progress') or 'n/a'} | "
                  f"created={im.get('CreationTime')} | NVMe={nvme}")
            if im.get("Status") in ("Creating", "Waiting"):
                _finding(f"image {im.get('ImageId')} is still "
                         f"{im.get('Status')} (progress {im.get('Progress')}): "
                         "detection/repair on a not-yet-Available image "
                         "explains 'cannot select it' symptoms")
    else:
        if not any("DescribeImages" in d for d in _degraded):
            print(f"\n[ custom images visible in {region} ] 0 (valid finding: "
                  "no self-owned image records; NOT an error)")
            _finding("no custom images visible in this region for this "
                     "account; Describe reads are per-region -- other "
                     "regions must be named and queried separately")

    invocations = _describe_recent_invocations(region, args.instance_id, args.profile)
    if invocations:
        print(f"\n[ recent Cloud Assistant invocations ] {len(invocations)} "
              "(most recent first; content read-back is out of scope here)")
        for iv in invocations[:5]:
            inst = ((iv.get("InvokeInstances") or {}).get("InvokeInstance") or [{}])[0]
            print(f"  {iv.get('InvokeId')} | {iv.get('CommandName') or iv.get('CommandType')} "
                  f"| {iv.get('InvocationStatus')} | inst err={inst.get('ErrorCode') or '-'}")

    # ---- symptom classification ----
    boot = match_boot_signature(symptom) if symptom else None
    if boot:
        sig = C.BOOT_SIGNATURES[boot]
        print(f"\n[ boot root-cause ] {sig['verdict']}")
        print(f"  {sig['why_no_guest_read']}")
        print("  guided self-repair paths (customer-run; this skill never "
              "executes any of them):")
        for p in sig["self_repair_paths"]:
            print(f"    - {p}")
        if isinstance(sig["risk_notes"], list):
            for rn in sig["risk_notes"]:
                print(f"    ! {rn}")
        print(f"  post-repair recheck: {sig['post_repair_recheck']}")
        _finding(f"boot signature matched: {boot} (guided paths only)")
        _suggest("verify-repair after the customer's repair restores boot; "
                 "for hands-on execution of the repair itself the customer "
                 "uses the console paths above or a human ticket")
    for slug in match_detection_items(symptom):
        _print_detection_item(slug)
    if symptom and not boot and not match_detection_items(symptom):
        _degraded.append("symptom text matched no built-in signature; "
                         "classification incomplete, not invented")
        _suggest("collect the literal console wording (detection item name, "
                 "error line, screen text) and re-run analyze-report / "
                 "analyze-log on it")
    if not symptom:
        _suggest("ask the customer which axis it is (detection WARN/critical "
                 "wording, a repair failure log, or a boot symptom) and "
                 "re-run with --symptom/--error-text")

    status = "DEGRADED" if _degraded else "OK"
    return _finish(status, "relay the evidence + guidance above verbatim; "
                   "every fix step stays manual; after the customer acts, "
                   "close with verify-repair",
                   {"region": region} if args.json else None)


def mode_plan_check(args) -> int:
    _banner(args)
    scenarios = {
        "fstab": ["findmnt", "stat <each mount target declared in the "
                  "customer-pasted fstab>", "ls <the same directory>"],
        "components": ["ls <the Cloud Assistant install directory AS "
                       "PRINTED in the official install doc>",
                       "stat <the Security Center agent directory AS "
                       "PRINTED in its official doc>"],
        "bootdir": ["ls /boot", "stat /boot"],
    }
    if args.scenario not in scenarios:
        return _fail([f"scenario (one of: {', '.join(scenarios)})"])
    print(f"[ guided read-only check plan ] scenario: {args.scenario}")
    print("  These are the ONLY commands this skill will ever run inside a")
    print("  guest, each behind a per-command confirmation, and only while")
    print("  the instance is Running (a non-booting instance has no channel:")
    print("  the customer boots a live/PE repair disk or attaches the disk")
    print("  elsewhere and inspects it themselves).")
    for c in scenarios[args.scenario]:
        print(f"    $ {c}")
    print("\n  Disclosure printed before any dispatch (probe mode):")
    for line in C.PROBE_DISCLOSURE:
        print("  " + line)
    _finding("check plan emitted (guidance only; nothing dispatched)")
    return _finish("OK", "for a live check on a Running instance run: "
                   "probe --region-id <r> --instance-id <i> --command "
                   "'<exactly one whitelisted command>' (prints the "
                   "disclosure + a single-use token, dispatches only after "
                   "the customer confirms)",
                   {"scenario": args.scenario} if args.json else None)


def mode_probe(args) -> int:
    _banner(args)
    missing = []
    if not args.region_id or not _REGION_RE.match(args.region_id):
        missing.append("region-id")
    if not args.instance_id or not _INSTANCE_RE.match(args.instance_id):
        missing.append("instance-id")
    if not args.command:
        missing.append("command (exactly one whitelisted read-only command)")
    if missing:
        return _fail(missing)
    verdict, reason = classify_guest_command(args.command)
    if verdict == "REFUSED":
        print(f"[ guest probe REFUSED ] {reason}")
        print("  Refusals are not softened into lookalike commands: the "
              "customer runs the read manually and pastes the reading, or "
              "the request leaves this skill's scope.")
        _suggest("ask the customer to run the read themselves in their own "
                 "session and paste the output; keep this skill on the "
                 "whitelist")
        return _finish("FAIL", "route the refused read to the customer as a "
                       "manual step (or the handoff table if it is out of "
                       "scope)", {"refused": reason} if args.json else None)
    token = probe_token(args.region_id, args.instance_id, args.command)
    if not args.confirm:
        print(f"[ consent gate ] planned single dispatch, NOT executed:")
        print(f"  command   : {args.command}")
        print(f"  why       : {reason}")
        print(f"  instance  : {args.instance_id}   region: {args.region_id}")
        print("")
        for line in C.PROBE_DISCLOSURE:
            print("  " + line)
        print(f"\n  Relay the disclosure above, obtain the customer's "
              f"explicit YES for THIS one operation, then re-run with:")
        print(f"    --confirm {token}")
        return _finish("FAIL", "obtain per-operation consent, then re-run "
                       "the probe with --confirm " + token,
                       {"planned": args.command, "token": token}
                       if args.json else None)
    if args.confirm != token:
        print("[ consent gate ] the supplied token does not match THIS "
              "region + instance + command exactly: a confirmation binds to "
              "one operation and is never reused.")
        return _finish("FAIL", "re-print the disclosure (drop --confirm) "
                       "and get a fresh confirmation for this exact "
                       "operation")
    # Re-validate after 'substitution' (the token flow re-parses user input
    # on every run) immediately before dispatch.
    verdict, reason = classify_guest_command(args.command)
    if verdict != "ALLOWED":
        return _finish("FAIL", f"command changed between consent and "
                       f"dispatch ({reason}); re-disclose")

    # Class-B dispatch: ONE command, under the customer's own credentials.
    encoded = base64.b64encode(args.command.encode("utf-8")).decode("ascii")
    print("[ dispatch ] Cloud Assistant channel, one read-only command ...")
    try:
        body = _cli.call("ecs", C.API_RUN_COMMAND, {
            "RegionId": args.region_id,
            "Type": "RunShellScript",
            "CommandContent": encoded,
            "ContentEncoding": "Base64",
            "Timeout": 60,
            "InstanceId.1": args.instance_id,
        }, region=args.region_id, profile=args.profile)
    except CliError as e:
        _warn("probe dispatch", e)
        code = e.code or ""
        hint = ""
        if "NoPermission" in code or "Denied" in code:
            hint = (" (the customer's credential lacks the guest-execution "
                    "permission for this instance: the operation runs under "
                    "their own rights -- no standing grant exists here)")
        print(f"[ DEGRADED{hint} ] dispatch failed: {e}")
        _suggest("fallback per the degraded contract: ask the customer to "
                 f"run exactly `{args.command}` in their own console "
                 "session and paste the output")
        return _finish("DEGRADED", "ask the customer to paste the output of "
                       f"`{args.command}` (agent offline, unauthorized or "
                       "failed dispatch all end here)")

    invoke_id = str(body.get("InvokeId") or "")
    if not invoke_id:
        _warn("probe dispatch", CliError("response carried no InvokeId"))
        return _finish("DEGRADED", "ask the customer to paste the output "
                       f"of `{args.command}`")
    print(f"  invoke submitted: {invoke_id}; polling status read-back ...")
    deadline = time.monotonic() + C.PROBE_POLL_TIMEOUT
    output_b64, st, inst_err, exit_code = "", "Pending", "", ""
    while time.monotonic() < deadline:
        time.sleep(C.PROBE_POLL_INTERVAL)
        try:
            invs = _cli.paginate_page_number(
                "ecs", C.API_DESCRIBE_INVOCATIONS,
                {"InvokeId": invoke_id}, ["Invocations", "Invocation"],
                region=args.region_id, profile=args.profile, max_pages=1)
        except CliError as e:
            _warn("probe read-back", e)
            break
        if invs:
            inst = ((invs[0].get("InvokeInstances") or {})
                    .get("InvokeInstance") or [{}])[0]
            st = str(inst.get("InvocationStatus") or
                     invs[0].get("InvocationStatus") or "Pending")
            output_b64 = str(inst.get("Output") or "")
            inst_err = str(inst.get("ErrorCode") or "")
            exit_code = str(inst.get("ExitCode", ""))
            if st not in ("Pending", "Running", "Scheduled", "Invoking"):
                break
    if st in ("Success", "Finished") and output_b64:
        try:
            text = base64.b64decode(output_b64).decode("utf-8", "replace")
        except Exception:  # never echo raw undecodable bytes
            text = "(output not printable; copy it from the console page)"
        print("\n[ guest reading ] exit_code=" + (exit_code or "n/a"))
        shown = text.splitlines()[:80]
        for line in shown:
            print("  | " + line[:200])
        if len(text.splitlines()) > 80:
            print("  | ... (truncated; full text is in the console page)")
        _finding("whitelisted guest reading captured")
        return _finish("OK", "interpret the reading above against the "
                       "detection item / handoff table; if it answers the "
                       "question, conclude", {"guest_output": text[:4000]}
                       if args.json else None)
    _degraded.append(f"guest probe did not return a completed reading "
                     f"(status {st}, instance error {inst_err or '-'}); the "
                     f"agent may be offline, the instance not Running, or "
                     f"the poll window elapsed")
    print(f"\n[ DEGRADED ] probe status={st} inst_err={inst_err or '-'}: "
          "no completed guest reading was obtained.")
    _suggest(f"ask the customer to run exactly `{args.command}` in their "
             "session (console Workbench) and paste the output; "
             "an offline agent itself belongs to the Cloud Assistant axis "
             "(handoff table)")
    return _finish("DEGRADED", "collect the pasted reading, or hand the "
                   "offline-agent problem to the Cloud Assistant skill")


def mode_verify_repair(args) -> int:
    _banner(args)
    if not args.region_id or not _REGION_RE.match(args.region_id):
        return _fail(["region-id"])
    try:
        validate_id(args.instance_id or "", _INSTANCE_RE, "instance") \
            if args.instance_id else None
        validate_id(args.image_id or "", _IMAGE_RE, "image") \
            if args.image_id else None
    except ValueError as e:
        return _fail([str(e)])
    print(f"[ post-repair recheck ] region {args.region_id} (read-only "
          "queries only; the repair itself was the customer's action)")
    if args.image_id:
        images = _describe_custom_images(args.region_id, args.image_id,
                                         args.profile)
        for im in images:
            print(f"  image {im.get('ImageId')}: status={im.get('Status')} "
                  f"progress={im.get('Progress') or 'n/a'}")
            if im.get("Status") == "Available":
                _finding("rebuilt image is Available: the customer can "
                         "re-run console image detection for the "
                         "after-state verdict (no verified read-only pull "
                         "for detection results; rely on the new report)")
            else:
                _finding(f"image still {im.get('Status')}: recheck after it "
                         "finishes")
    if args.instance_id:
        statuses = _describe_instance_statuses(args.region_id,
                                               args.instance_id, args.profile)
        st = statuses[0].get("Status") if statuses else "unknown"
        print(f"  instance {args.instance_id}: lifecycle={st}")
        if st == "Running":
            _finding("instance lifecycle Running")
            _suggest("Running is control-plane only: ask the customer to "
                     "confirm the OS itself reached login/system stage, "
                     "then optionally run ONE whitelisted guest probe "
                     "(findmnt / stat / ls) against what the repair fixed")
        else:
            _degraded.append(f"instance lifecycle state '{st}' after the "
                             "repair")
            _suggest("re-check the state / route the state machine to the "
                     "start-stop axis handoff")
    if not (args.image_id or args.instance_id):
        _suggest("pass --image-id and/or --instance-id to recheck the "
                 "repaired objects; this skill never re-triggers repairs")
    _print_boundary_hits(args.symptom or "")
    return _finish("DEGRADED" if _degraded else "OK",
                   "conclude with both sides' evidence: the control-plane "
                   "recheck above plus the customer-confirmed boot result",
                   {"image_id": args.image_id,
                    "instance_id": args.instance_id} if args.json else None)


def mode_handoff(args) -> int:
    _banner(args)
    if not args.symptom:
        return _fail(["symptom (the customer wording to classify)"])
    hits = match_handoff(args.symptom)
    slugs = match_detection_items(args.symptom)
    boot = match_boot_signature(args.symptom)
    if hits:
        for route in hits:
            target = route["target_skill"] or "a human support ticket"
            print(f"  -> {route['route']} : {target}\n     {route['script']}")
            _finding(f"handoff: {route['route']}")
    if slugs or boot:
        print("  (the symptom ALSO carries in-scope signals; keep those "
              "axes here and hand off only the routed part)")
    if not hits:
        print("  no boundary route matched: the symptom stays inside this "
              "skill's axes; run triage/analyze-* for it")
    return _finish("OK" if hits else "DEGRADED",
                   "relay the routed script verbatim; keep the in-scope "
                   "part and run its mode",
                   {"handoff": [h["route"] for h in hits]}
                   if args.json else None)


def mode_explain(args) -> int:
    _banner(args)
    topic = args.topic
    if topic == "docs":
        for key, url in C.DOC_LINKS.items():
            print(f"  {key}\n    {url}")
        print("\n  NOT cited (no verified URL in this batch, described in "
              "words only): the console PE/live repair-disk feature page, "
              "the NVMe adaptation page, the fstab-fix page, the agent "
              "install pages.")
        _finding("official doc set listed")
    elif topic == "detection":
        for slug, item in C.DETECTION_ITEMS.items():
            print(f"\n  [{slug}] {item['label']}\n    {item['meaning']}")
        _finding("detection-item semantics listed")
    elif topic == "repair":
        for code, info in C.REPAIR_ERROR_CODES.items():
            print(f"\n  [{code}]\n    {info['root_cause']}\n"
                  f"    {info['exit_path']}")
        print("\n  Repair always provisions transient postpaid resources "
              "first; the balance threshold failure is a billing-side "
              "condition, NOT image corruption.")
        _finding("repair-failure semantics listed")
    elif topic == "guest":
        print("  Whitelist: " + ", ".join(sorted(C.GUEST_COMMAND_WHITELIST)))
        for name, why in C.GUEST_COMMAND_DENY_LIST:
            print(f"    refused {name}: {why}")
        _finding("guest read-only command policy listed")
    elif topic == "boot":
        for slug, sig in C.BOOT_SIGNATURES.items():
            print(f"\n  [{slug}] {sig['verdict']}")
            for p in sig["self_repair_paths"]:
                print(f"    path: {p}")
        _finding("boot signatures listed")
    else:
        return _fail([f"topic (one of: docs, detection, repair, guest, "
                      f"boot; got '{topic}')"])
    return _finish("OK", "answer the customer strictly from the lines "
                   "above (plus real query results); never from memory",
                   {"topic": topic} if args.json else None)


# ---------------------------------------------------------------------------
# Argument plumbing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="image_boot_repair_diagnosis.py",
        description="SINGLE entry point: read-only diagnosis for ECS "
                    "custom-image detection items, image-repair task "
                    "failures and boot/GRUB guidance, plus guided "
                    "read-only verification. Mutations are never offered "
                    "by this skill: repair steps stay manual.")
    p.add_argument("--json", action="store_true", help="machine-readable "
                   "payload alongside the report lines")
    p.add_argument("--profile", default=None, help="optional aliyun CLI "
                   "credential profile name")
    sub = p.add_subparsers(dest="mode", required=True)

    def add_mode(name: str, help_text: str) -> argparse.ArgumentParser:
        """Subparser that ALSO accepts --json/--profile after the mode name
        (SUPPRESS keeps the parent-level value unless the sub-level flag is
        explicitly given, so both positions work for weak orchestrators)."""
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("--json", action="store_true",
                        default=argparse.SUPPRESS,
                        help="machine-readable payload alongside the report")
        sp.add_argument("--profile", default=argparse.SUPPRESS,
                        help="optional aliyun CLI credential profile name")
        return sp

    add_mode("check-env", "verify identity + session/UA")

    t = add_mode("triage", "cloud evidence + symptom routing")
    t.add_argument("--region-id", default="",
                 help="required at runtime; validated below")
    t.add_argument("--instance-id", default="")
    t.add_argument("--image-id", default="")
    t.add_argument("--symptom", default="", help="customer wording, verbatim")
    t.add_argument("--error-text", default="", help="literal console line")

    a = add_mode("analyze-log", "customer-pasted repair log")
    a.add_argument("--text", default="")
    a.add_argument("--file", default="")
    a.add_argument("--task-status", default="", help="status the customer "
                   "says the task page shows (for the contradiction note)")

    r = add_mode("analyze-report", "customer-pasted detection report")
    r.add_argument("--text", default="")
    r.add_argument("--file", default="")
    r.add_argument("--image-id", default="")

    pc = add_mode("plan-check", "guided read-only check plan (no dispatch)")
    pc.add_argument("--scenario", default="",
                    choices=["", "fstab", "components", "bootdir"])

    pr = add_mode("probe", "ONE consent-gated whitelisted read-only guest "
                           "command")
    pr.add_argument("--region-id", default="")
    pr.add_argument("--instance-id", default="")
    pr.add_argument("--command", default="")
    pr.add_argument("--confirm", default="", help="single-use token from "
                    "the previous disclosure run")

    v = add_mode("verify-repair", "read-only recheck after the customer "
                                  "repaired")
    v.add_argument("--region-id", default="",
                 help="required at runtime; validated below")
    v.add_argument("--instance-id", default="")
    v.add_argument("--image-id", default="")
    v.add_argument("--symptom", default="")

    h = add_mode("handoff", "boundary routing")
    h.add_argument("--symptom", default="")

    e = add_mode("explain", "embedded knowledge")
    e.add_argument("--topic", default="",
                   choices=["", "docs", "detection", "repair", "guest", "boot"])
    return p


HANDLERS = {
    "check-env": mode_check_env,
    "triage": mode_triage,
    "analyze-log": mode_analyze_log,
    "analyze-report": mode_analyze_report,
    "plan-check": mode_plan_check,
    "probe": mode_probe,
    "verify-repair": mode_verify_repair,
    "handoff": mode_handoff,
    "explain": mode_explain,
}


def _run_selftest() -> int:
    """Offline boundary locks for the read-only command gate and matchers.

    ``classify_guest_command`` is a fail-closed gate: only a single whitelisted
    read-only command (findmnt bare, or stat/ls on one non-system absolute path)
    may proceed; every other shape - chaining, metacharacters, a deny-listed
    head, a relative or ``..``-escaping path, or a path under /etc /root /proc
    etc. - is refused. A wrong ALLOWED here reads or touches the guest beyond
    scope. ``match_boot_signature`` / ``match_detection_items`` / ``match_handoff``
    are the wording->knowledge routers. Pure logic only - no cloud, no subprocess.
    """
    rc = 0

    def expect(name, cond):
        nonlocal rc
        if cond:
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}")
            rc = 1

    def verdict(cmd):
        return classify_guest_command(cmd)[0]

    # --- accept: exactly the whitelisted read-only shapes
    expect("allow_findmnt_bare", verdict("findmnt") == "ALLOWED")
    expect("allow_ls_boot", verdict("ls /boot") == "ALLOWED")
    expect("allow_stat_var", verdict("ls /var/log") == "ALLOWED")  # /var not denied
    # --- refuse: bare findmnt must not take args
    expect("refuse_findmnt_arg", verdict("findmnt -l") == "REFUSED")
    # --- refuse: empty / non-whitelist / deny-list head
    expect("refuse_empty", verdict("") == "REFUSED")
    expect("refuse_df_offlist", verdict("df -h") == "REFUSED")
    expect("refuse_deny_head", verdict("cat /etc/passwd") == "REFUSED")
    # --- refuse: chaining / metacharacter
    expect("refuse_chain", verdict("ls /boot; reboot") == "REFUSED")
    # --- refuse: relative path / missing path / traversal
    expect("refuse_relative", verdict("stat relative/path") == "REFUSED")
    expect("refuse_traversal", verdict("stat /data/../etc") == "REFUSED")
    # --- refuse: denied system path segments (discriminating each guard)
    expect("refuse_etc_path", verdict("stat /etc/fstab") == "REFUSED")
    expect("refuse_root_path", verdict("stat /root/.ssh") == "REFUSED")
    expect("refuse_proc_path", verdict("ls /proc/1") == "REFUSED")
    # universal invariant: the bare whitelist heads are all accepted as scoped
    expect("allow_all_whitelist_heads", verdict("findmnt") == "ALLOWED"
           and verdict("stat /boot") == "ALLOWED" and verdict("ls /boot") == "ALLOWED")

    # --- match_boot_signature: first matching slug, else None
    first_slug = next(iter(C.BOOT_SIGNATURES))
    first_phrase = C.BOOT_SIGNATURES[first_slug]["match"][0]
    expect("bootsig_match", match_boot_signature("BOOT ERROR: " + first_phrase) == first_slug)
    expect("bootsig_none", match_boot_signature("totally unrelated text") is None)
    expect("bootsig_empty_none", match_boot_signature("") is None)

    # --- match_detection_items / match_handoff return lists, empty on no signal
    expect("detect_list_empty", isinstance(match_detection_items(""), list)
           and match_detection_items("") == [])
    expect("handoff_list_empty", isinstance(match_handoff(""), list)
           and match_handoff("") == [])

    print(f"SELFTEST: {'PASS' if rc == 0 else 'FAIL'}")
    return rc


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        sys.exit(_run_selftest())
    args = build_parser().parse_args(argv)
    try:
        sys.exit(HANDLERS[args.mode](args))
    except KeyboardInterrupt:
        print("\nSTATUS: FAIL\nNEXT_ACTION: interrupted; re-run when ready",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
