#!/usr/bin/env python3
"""
backup_strategy_advisor.py -- SINGLE ENTRY POINT for the
alibabacloud-ecs-backup-strategy-design skill (READ-ONLY advisory).

SECURITY: This skill is strictly READ-ONLY. It only calls the whitelisted
read-only APIs (`aliyun sts get-caller-identity`, `aliyun ecs
describe-instances`, `aliyun ecs describe-instance-status`) through the shared
CLI layer with a per-call timeout and the run's User-Agent label. It never
runs commands inside any instance, never submits, changes, deletes or binds
any cloud configuration, and never reads, prints, or passes credential
values explicitly -- the aliyun CLI default credential chain resolves
authentication. Console operations in the produced plan are GUIDANCE FOR THE
CUSTOMER TO PERFORM; the skill does not perform them.

Modes (all read-only; contract: stdout ends with STATUS:/NEXT_ACTION:):
  design              --target whole-instance,files,database,local-copy,off-site
                        [+ --data-size-gb --change-gb --change-period
                         --retention-days --snapshots-per-day --disk-count
                         --cross-region]
  cloud facts         --region-id <r> [--instance-id i-a,i-b | --inventory]
  effectiveness check --check-effectiveness [--customer-report "<console text>"]
  failure/symptom     --error-text "<exact alert wording>" [--symptom "<text>"]
  knowledge topics    --list-topics | --topic <key>

Exit codes: 0 = OK or DEGRADED (usable conclusion produced),
            1 = FAIL (missing/invalid input or every evidence call failed),
            2 = argparse usage error only (a diagnosed condition never exits 2).

Usage examples (run from the skill root):
  python3 scripts/backup_strategy_advisor.py --region-id cn-hangzhou \
      --instance-id i-bp1xxxxxxxx --target whole-instance \
      --data-size-gb 2048 --change-gb 20 --change-period week \
      --retention-days 7 --snapshots-per-day 1 --cross-region
  python3 scripts/backup_strategy_advisor.py \
      --error-text "backup job failed: insufficient disk space"
  python3 scripts/backup_strategy_advisor.py --topic snapshot-capacity-vs-disk-usage
"""

from __future__ import annotations

import argparse
import json
import re
import sys

import _cli
from _constants import (
    CONDITION_RULES,
    CROSS_REGION_COPY_RULES,
    DEFAULT_REGION,
    DOC_URLS,
    DOC_VERIFICATION_NOTE,
    EFFECTIVENESS_NOT_FETCHED,
    EFFECTIVENESS_SELFCHECK_STEPS,
    FILE_BACKUP_BILLING_RULES,
    KNOWLEDGE_TOPICS,
    LOCAL_DISK_FAMILY_NOTE,
    MAX_DATA_GB,
    MAX_DISK_COUNT,
    MAX_RETENTION_DAYS,
    MAX_SNAPSHOTS_PER_DAY,
    MAX_TEXT_LEN,
    MECHANISM_RULES,
    NO_COMMITMENT_STATEMENT,
    RESOURCE_PACKAGE_NOTE,
    SNAPSHOT_CAPACITY_RULES,
    TARGET_SYNONYMS,
    UNKNOWN_CONDITION_VERDICT,
)

# Input-validation patterns (E20: strict validation, no shell metacharacters
# ever reach a subprocess).
REGION_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
INSTANCE_ID_RE = re.compile(r"^i-[A-Za-z0-9._-]{4,64}$")
_LOCAL_DISK_RE = re.compile(r"^ecs\.[id][0-9][a-z0-9.-]*$", re.IGNORECASE)

READ_ONLY_STATEMENT = (
    "This skill is READ-ONLY: it performed read-only queries only, ran no "
    "commands inside any instance, and changed nothing. Every console "
    "operation listed above is guidance for YOU to perform; the skill can "
    "then re-check the design against these rules or the read-only facts."
)

PERIOD_DAYS = {"day": 1.0, "week": 7.0, "month": 30.0}


# ---------------------------------------------------------------------------
# Pure rule functions (unit-testable; no network)
# ---------------------------------------------------------------------------

def normalize_targets(raw: str) -> tuple:
    """Map comma-separated --target values to known mechanism keys.

    Returns (targets, invalid). Invalid tokens keep their original spelling
    so the report can name them.
    """
    targets: list = []
    invalid: list = []
    for token in (raw or "").split(","):
        token = token.strip().lower()
        if not token:
            continue
        mapped = TARGET_SYNONYMS.get(token)
        if mapped and mapped in MECHANISM_RULES:
            if mapped not in targets:
                targets.append(mapped)
        elif token in MECHANISM_RULES:
            if token not in targets:
                targets.append(token)
        else:
            invalid.append(token)
    return targets, invalid


def normalize_daily_change(change_gb: float, period: str) -> float:
    """Normalize a customer-estimated change volume to GB per day."""
    days = PERIOD_DAYS.get((period or "day").lower(), 1.0)
    return round(float(change_gb) / days, 3)


def local_disk_note(instance_type: str) -> dict:
    """Heuristic local-disk detection from the instance type family name.

    Rule knowledge (not an API field): families starting with ecs.i<N>/
    ecs.d<N> carry local disks, which do not support snapshots.
    """
    itype = (instance_type or "").strip()
    if not itype:
        return {"suspected": None, "note": "instance type not provided"}
    if _LOCAL_DISK_RE.match(itype):
        return {"suspected": True,
                "note": LOCAL_DISK_FAMILY_NOTE + " Snapshots are unavailable "
                        "on local disks: plan file-level / database-level "
                        "copies off the local disk instead."}
    return {"suspected": False,
            "note": "cloud disks by family name; snapshots apply"}


def cost_model(data_size_gb, daily_change_gb, retention_days,
               snapshots_per_day, disk_count, cross_region,
               targets_files=False) -> dict:
    """Parameterized billing MODEL and worked example -- never a committed
    amount (official support stance on both sides of the ticket)."""
    model = {
        "formulas": [
            "snapshots alive in the retention window = retention-days x "
            "snapshots-per-day x disks",
            "cross-region copy billings = number of snapshots copied "
            "(create N, copy N) -- one traffic fee + destination-region "
            "storage per copy",
            "steady-state snapshot capacity (GB) ~= used-data base + "
            "daily-change(GB) x retention-days  [lower bound: block-level "
            "change >= file-level change, and deleted files keep occupying "
            "referenced blocks]",
        ],
        "snapshots_in_window": None,
        "copy_events": None,
        "steady_capacity_gb": None,
        "snapshot_rules": list(SNAPSHOT_CAPACITY_RULES),
        "copy_rules": list(CROSS_REGION_COPY_RULES) if cross_region else [],
        "file_backup_rules": list(FILE_BACKUP_BILLING_RULES) if targets_files else [],
        "resource_package_note": RESOURCE_PACKAGE_NOTE,
        "no_commitment": NO_COMMITMENT_STATEMENT,
    }
    if retention_days and snapshots_per_day and disk_count:
        model["snapshots_in_window"] = int(retention_days) * int(
            snapshots_per_day) * int(disk_count)
        if cross_region:
            model["copy_events"] = model["snapshots_in_window"]
    if data_size_gb and daily_change_gb and retention_days:
        model["steady_capacity_gb"] = round(
            float(data_size_gb) + float(daily_change_gb) * int(retention_days), 2)
    return model


def classify_condition(text: str) -> str:
    """Classify customer-visible failure/symptom wording against the embedded
    CONDITION_RULES patterns. Returns the category, "" for empty input, or
    "unknown". First matching rule wins (order = specificity)."""
    low = (text or "").lower().strip()
    if not low:
        return ""
    for rule in CONDITION_RULES:
        for pattern in rule["patterns"]:
            if pattern in low:
                return rule["category"]
    return "unknown"


def condition_result(category: str) -> dict:
    """Full verdict bundle for a classified category."""
    if category in ("", "unknown"):
        return {"category": category or "empty",
                "verdict": UNKNOWN_CONDITION_VERDICT,
                "route": False, "customer_next_steps": [], "docs": []}
    for rule in CONDITION_RULES:
        if rule["category"] == category:
            return {
                "category": category,
                "verdict": rule["verdict"],
                "route": rule["route"],
                "customer_next_steps": list(rule["customer_next_steps"]),
                "docs": list(rule["docs"]),
            }
    return {"category": category, "verdict": UNKNOWN_CONDITION_VERDICT,
            "route": False, "customer_next_steps": [], "docs": []}


def design_plan(targets: list) -> dict:
    """Build the mechanism-design sections for the requested backup objects."""
    unknown = [t for t in targets if t not in MECHANISM_RULES]
    if unknown or not targets:
        return {"status": "FAIL",
                "unknown_targets": unknown,
                "valid_targets": sorted(MECHANISM_RULES),
                "sections": [], "mechanisms": [], "docs": []}
    sections = []
    mechanisms: list = []
    docs: list = []
    for target in targets:
        rule = MECHANISM_RULES[target]
        sections.append({
            "target": target,
            "label": rule["label"],
            "mechanisms": list(rule["mechanisms"]),
            "core_rule": rule["core_rule"],
            "design_note": rule["single_disk_note"],
            "limitations": list(rule["limitations"]),
            "customer_steps": list(rule["customer_steps"]),
            "gap_probes": list(rule["gap_probes"]),
            "docs": list(rule["docs"]),
        })
        for m in rule["mechanisms"]:
            if m not in mechanisms:
                mechanisms.append(m)
        for d in rule["docs"]:
            if d not in docs:
                docs.append(d)
    return {"status": "OK", "unknown_targets": [], "sections": sections,
            "mechanisms": mechanisms, "docs": docs}


def effectiveness_sections(customer_report: str) -> dict:
    """Policy-effectiveness judgment. Snapshot/policy state is NOT fetchable
    through an API in this release (unverified permission surface), so the
    judgment comes from the customer's console report, rule-checked here."""
    judgment = "UNKNOWN -- run self-check steps 1 and 2 first"
    low = (customer_report or "").lower().strip()
    if low:
        neg = re.search(r"\bnot\b|\bno\b|never|didn'?t|nothing|empty|cannot find", low)
        pos = re.search(r"applied|linked|bound|associated|exists|shows", low)
        if neg and not pos:
            judgment = ("NOT_EFFECTIVE (per your console report): an "
                        "automatic snapshot policy only runs once it is "
                        "APPLIED to the disk(s). Apply it to the target "
                        "disk(s) in the console (you perform it), then "
                        "verify a snapshot appears at the next time point.")
        elif pos and not neg:
            judgment = ("EFFECTIVE (per your console report): the policy is "
                        "reported as applied; confirm a real snapshot "
                        "exists after the first scheduled time point -- "
                        "'policy applied' is necessary, 'snapshot visible' "
                        "is the proof.")
        else:
            judgment = ("AMBIGUOUS console report: ask the customer to "
                        "restate whether the policy shows an applied-disk "
                        "binding, then re-run with that wording.")
    return {"judgment": judgment,
            "steps": list(EFFECTIVENESS_SELFCHECK_STEPS),
            "not_fetched_note": EFFECTIVENESS_NOT_FETCHED}


# Inline boundary assertions for the pure functions (normal / boundary /
# invalid inputs), executed on every import.
assert normalize_daily_change(70, "week") == 10.0
assert normalize_daily_change(14, "day") == 14.0
assert normalize_daily_change(300, "month") == 10.0
assert normalize_daily_change(70, "") == 70.0
_cm = cost_model(2048, 5, 7, 2, 1, True)
assert _cm["snapshots_in_window"] == 14
assert _cm["copy_events"] == 14
assert _cm["steady_capacity_gb"] == 2083
_cm2 = cost_model(None, None, None, None, 1, False)
assert _cm2["snapshots_in_window"] is None
assert _cm2["steady_capacity_gb"] is None
assert classify_condition("Backup job failed: insufficient disk space") == \
    "precondition_disk_full"
assert classify_condition("The automatic snapshot policy was created but no "
                          "snapshots appear") == "policy_not_effective"
assert classify_condition("ransom note opened, files are encrypted") == \
    "ransomware_incident"
assert classify_condition("how do I back up before I release the instance") == \
    "pre_release_backup"
assert classify_condition("") == ""
assert classify_condition("totally unrelated wording") == "unknown"
assert local_disk_note("ecs.i2.4xlarge")["suspected"] is True
assert local_disk_note("ecs.d1.4xlarge")["suspected"] is True
assert local_disk_note("ecs.g6.large")["suspected"] is False
assert local_disk_note("")["suspected"] is None
_d = design_plan(["files"])
assert "Cloud Backup" in " ".join(_d["mechanisms"])
assert all("snapshot" not in m for m in _d["mechanisms"])
assert design_plan(["bogus"])["status"] == "FAIL"
assert design_plan([])["status"] == "FAIL"
assert "applied" in design_plan(["whole-instance"])["sections"][0]["core_rule"]
assert effectiveness_sections("The policy is applied to my disk")["judgment"] \
    .startswith("EFFECTIVE")
assert effectiveness_sections("")["judgment"].startswith("UNKNOWN")
assert normalize_targets("server, db, nonsense")[0] == ["whole-instance", "database"]
assert normalize_targets("server, db, nonsense")[1] == ["nonsense"]


# ---------------------------------------------------------------------------
# Read-only cloud facts
# ---------------------------------------------------------------------------

def fetch_facts(region: str, instance_ids: list, inventory: bool,
                profile) -> dict:
    """Gather instance facts via the whitelisted read-only ECS/STS queries.

    Every failure degrades to a recorded error string; nothing here can
    change cloud state."""
    facts = {"attempted": False, "uid": "", "instances": [], "missing": [],
             "errors": [], "statuses": {}}
    if not (instance_ids or inventory):
        return facts
    facts["attempted"] = True
    facts["uid"] = _cli.resolve_account_id(region=region, profile=profile)
    if not facts["uid"]:
        facts["errors"].append(
            "identity: `aliyun sts get-caller-identity` failed "
            "(credential chain not configured or NoPermission on "
            "sts:GetCallerIdentity); UID label NOT FETCHED")
    try:
        items = _cli.list_instances(region, instance_ids or None, profile=profile)
    except _cli.CliError as e:
        facts["errors"].append(
            f"DescribeInstances [{e.code or 'error'}]: {e}")
        items = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        iid = str(item.get("InstanceId") or "")
        seen.add(iid)
        facts["instances"].append({
            "InstanceId": iid,
            "Status": str(item.get("Status") or ""),
            "OSType": str(item.get("OSType") or ""),
            "InstanceType": str(item.get("InstanceType") or ""),
            "InstanceChargeType": str(item.get("InstanceChargeType") or ""),
            "ImageId": str(item.get("ImageId") or ""),
        })
    if instance_ids:
        facts["missing"] = [i for i in instance_ids if i not in seen]
    if facts["instances"]:
        ids = [f["InstanceId"] for f in facts["instances"] if f["InstanceId"]][:50]
        try:
            facts["statuses"] = _cli.get_instance_statuses(region, ids, profile=profile)
        except _cli.CliError as e:
            facts["errors"].append(
                f"DescribeInstanceStatus [{e.code or 'error'}]: {e}")
    return facts


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

BAR = "=" * 72


def _fmt_num(value, unit="") -> str:
    if value is None:
        return "not provided"
    return f"{value}{unit}"


def build_reference_list(doc_keys: list) -> list:
    refs = []
    for key in doc_keys:
        url = DOC_URLS.get(key)
        if url:
            refs.append({"key": key, "url": url})
    return refs


def render_text(r: dict) -> str:
    lines = [BAR,
             " ECS BACKUP STRATEGY DESIGN -- READ-ONLY ADVISORY REPORT",
             BAR,
             f"Region scope   : {r['region']}",
             f"Modes run      : {', '.join(r['modes']) or 'none'}"]
    if r["identity_label"]:
        lines.append(f"Account UID    : {r['identity_label']} "
                     "(auto-derived via aliyun sts get-caller-identity; "
                     "traceability label only)")
    if r["auto_filled"]:
        lines.append("Auto-filled    : " + "; ".join(r["auto_filled"]))

    facts = r["facts"]
    if facts.get("attempted"):
        lines += ["", "## 1. Cloud facts (read-only Describe queries)"]
        for inst in facts["instances"][:20]:
            status = facts["statuses"].get(inst["InstanceId"], inst["Status"] or "n/a")
            lines.append(
                f"- {inst['InstanceId']}: status={status}, os={inst['OSType'] or 'n/a'}, "
                f"type={inst['InstanceType'] or 'n/a'}, charge={inst['InstanceChargeType'] or 'n/a'}")
        if len(facts["instances"]) > 20:
            lines.append(f"- ... and {len(facts['instances']) - 20} more instance(s)")
        for iid in facts["missing"]:
            lines.append(f"- {iid}: NOT FOUND in region {r['region']} under the "
                         "current credential (verify the region and the "
                         "account; empty is a valid result -- no write is "
                         "implied)")
        for inst in facts["instances"][:10]:
            note = local_disk_note(inst["InstanceType"])
            if note["suspected"] is not False:
                lines.append(f"- local-disk heuristic for {inst['InstanceId']} "
                             f"({inst['InstanceType'] or 'type unknown'}): "
                             f"{note['note']}")

    design = r["design"]
    if design.get("sections"):
        lines += ["", "## 2. Recommended backup design (per backup object)"]
        for sec in design["sections"]:
            lines.append(f"### Object: {sec['label']}")
            lines.append("Mechanisms:")
            lines += [f"- {m}" for m in sec["mechanisms"]]
            lines.append(f"Core rule: {sec['core_rule']}")
            if sec["design_note"]:
                lines.append(f"Design note: {sec['design_note']}")
            if sec["limitations"]:
                lines.append("Known limits:")
                lines += [f"- {x}" for x in sec["limitations"]]
            lines.append("Console steps (performed by YOU, the customer):")
            lines += [f"- {x}" for x in sec["customer_steps"]]
            lines.append("Coverage gaps to confirm (customer self-check -- "
                         "not visible to read-only cloud APIs):")
            lines += [f"- {x}" for x in sec["gap_probes"]]
            lines.append("")

    cost = r["cost_model"]
    if cost:
        lines += ["", "## 3. Billing model and cost example (no committed amount)"]
        lines.append("Formulas:")
        lines += [f"- {x}" for x in cost["formulas"]]
        lines.append(f"- snapshots alive in window: {_fmt_num(cost['snapshots_in_window'])}")
        if cost["copy_events"] is not None:
            lines.append(f"- cross-region copy billings in window: "
                         f"{_fmt_num(cost['copy_events'])} (one traffic fee + "
                         "destination-region storage per copy)")
        lines.append(f"- steady-state snapshot capacity estimate (GB, lower bound): "
                     f"{_fmt_num(cost['steady_capacity_gb'])}")
        lines.append("Model rules:")
        lines += [f"- {x}" for x in cost["snapshot_rules"]]
        lines += [f"- {x}" for x in cost["copy_rules"]]
        lines += [f"- {x}" for x in cost["file_backup_rules"]]
        lines.append(f"- {cost['resource_package_note']}")
        lines.append(f"COMMITMENT STATEMENT: {cost['no_commitment']}")

    eff = r.get("effectiveness")
    if eff:
        lines += ["", "## 4. Policy effectiveness re-check"]
        lines.append(f"Judgment: {eff['judgment']}")
        lines.append(f"Not-fetched note: {eff['not_fetched_note']}")
        lines.append("Console self-check steps (you perform them):")
        lines += [f"{i}. {x}" for i, x in enumerate(eff["steps"], 1)]

    conditions = r.get("conditions") or []
    if conditions:
        lines += ["", "## 5. Failure / symptom classification"]
        for cond in conditions:
            lines.append(f"Input: \"{cond['input'][:120]}\"")
            lines.append(f"Category: {cond['result']['category']}")
            lines.append(f"Verdict: {cond['result']['verdict']}")
            if cond["result"]["route"]:
                lines.append("BOUNDARY: this symptom belongs to another "
                             "channel (see references/routing.md); this skill "
                             "only answers the backup-side sub-question.")
            if cond["result"]["customer_next_steps"]:
                lines.append("Next steps (performed by YOU, the customer):")
                lines += [f"- {x}" for x in cond["result"]["customer_next_steps"]]
            lines.append("")

    if r["degradation_log"]:
        lines += ["", "## Graceful Degradation Log"]
        lines += [f"- {x}" for x in r["degradation_log"]]

    lines += ["", "## Data sources"]
    lines.append(f"- API-fetched (read-only): {r['data_sources']['api_fetched'] or 'none'}")
    lines.append(f"- Customer-provided inputs: {r['data_sources']['customer_provided'] or 'none'}")
    lines.append(f"- NOT FETCHED (boundaries of this skill): "
                 f"{'; '.join(r['data_sources']['not_fetched'])}")
    lines += ["", "## Official references (relative rule modules: references/)"]
    for ref in r["references"]:
        lines.append(f"- {ref['key']}: {ref['url']}")
    lines.append(f"Verification note: {r['doc_note']}")
    lines += ["", READ_ONLY_STATEMENT, "",
              f"STATUS: {r['status']}",
              f"NEXT_ACTION: {r['next_action']}"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Argument parsing / main
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="backup_strategy_advisor.py",
        description=("Read-only ECS backup strategy design advisor "
                     "(STATUS/NEXT_ACTION contract)"),
    )
    ap.add_argument("--region-id", default=None,
                    help=f"Region for read-only queries (default: "
                         f"{DEFAULT_REGION}, auto-filled and declared)")
    ap.add_argument("--instance-id", default=None,
                    help="Comma-separated ECS instance id(s) to look up "
                         "(read-only)")
    ap.add_argument("--inventory", action="store_true",
                    help="List the instances visible in the region "
                         "(read-only batch check)")
    ap.add_argument("--target", default=None,
                    help="Backup object(s): whole-instance, files, database, "
                         "local-copy, off-site (comma-separated)")
    ap.add_argument("--data-size-gb", type=float, default=None,
                    help=f"Customer-stated data volume in GB (0..{MAX_DATA_GB})")
    ap.add_argument("--change-gb", type=float, default=None,
                    help="Customer-stated change volume per period in GB")
    ap.add_argument("--change-period", default="day",
                    choices=["day", "week", "month"],
                    help="Period for --change-gb (default: day)")
    ap.add_argument("--retention-days", type=int, default=None,
                    help=f"Snapshot retention in days (1..{MAX_RETENTION_DAYS})")
    ap.add_argument("--snapshots-per-day", type=int, default=None,
                    help=f"Scheduled snapshots per disk per day "
                         f"(1..{MAX_SNAPSHOTS_PER_DAY})")
    ap.add_argument("--disk-count", type=int, default=None,
                    help=f"Disks covered by the policy (1..{MAX_DISK_COUNT}; "
                         "default 1, declared)")
    ap.add_argument("--cross-region", action="store_true",
                    help="Design includes cross-region copy")
    ap.add_argument("--check-effectiveness", action="store_true",
                    help="Add the policy-effectiveness re-check section")
    ap.add_argument("--customer-report", default=None,
                    help="Customer's console report text to rule-check for "
                         "effectiveness")
    ap.add_argument("--error-text", default=None,
                    help="Exact alert/error wording to classify")
    ap.add_argument("--symptom", default=None,
                    help="Customer symptom wording to classify")
    ap.add_argument("--topic", default=None,
                    help="Knowledge topic key (see --list-topics)")
    ap.add_argument("--list-topics", action="store_true",
                    help="List knowledge topic keys and exit")
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    ap.add_argument("--profile", default=None,
                    help="Optional aliyun CLI credential profile name")
    return ap


def main() -> None:
    ap = build_arg_parser()
    args = ap.parse_args()

    # ---- knowledge modes (offline, no cloud calls) ----
    if args.list_topics:
        for key in sorted(KNOWLEDGE_TOPICS):
            print(f"{key}: {KNOWLEDGE_TOPICS[key]['question']}")
        print("\nSTATUS: OK")
        print("NEXT_ACTION: re-run with --topic <key> for the full answer")
        return
    if args.topic:
        key = args.topic.strip().lower()
        topic = KNOWLEDGE_TOPICS.get(key)
        if not topic:
            print(f"[WARN] unknown topic key '{key}'; see --list-topics",
                  file=sys.stderr)
            print("\nSTATUS: FAIL")
            print("NEXT_ACTION: pick a key from --list-topics")
            sys.exit(1)
        print(f"Q: {topic['question']}")
        print(f"A: {topic['answer']}")
        refs = build_reference_list(topic["docs"])
        for ref in refs:
            print(f"- {ref['key']}: {ref['url']}")
        print(f"Verification note: {DOC_VERIFICATION_NOTE}")
        print("\nSTATUS: OK")
        print("NEXT_ACTION: combine this rule answer with the design modes "
              "when account facts are needed")
        return

    auto_filled: list = []
    errors: list = []

    # ---- validate region ----
    region = (args.region_id or DEFAULT_REGION).strip().lower()
    if not args.region_id:
        auto_filled.append(f"region-id defaulted to {DEFAULT_REGION}")
    if not REGION_RE.match(region):
        print(f"[ERROR] invalid region id '{args.region_id}'", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: use a valid region id such as cn-hangzhou; ask "
              "the customer which region the instance lives in.")
        sys.exit(1)

    # ---- validate instance ids ----
    instance_ids = [t.strip() for t in (args.instance_id or "").split(",")
                    if t.strip()]
    for iid in instance_ids:
        if not INSTANCE_ID_RE.match(iid):
            print(f"[ERROR] invalid instance id '{iid}'", file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: ask the customer for the exact i-... "
                  "instance id.")
            sys.exit(1)

    # ---- validate numeric inputs ----
    def _check_range(name, value, lo, hi):
        if value is None:
            return None
        if value < lo or value > hi:
            print(f"[ERROR] --{name} must be within {lo}..{hi}, got {value}",
                  file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: re-run with a sane value provided by the "
                  "customer; never substitute a guess.")
            sys.exit(1)
        return value

    data_size = _check_range("data-size-gb", args.data_size_gb, 0, MAX_DATA_GB)
    change_gb = _check_range("change-gb", args.change_gb, 0, MAX_DATA_GB)
    retention = _check_range("retention-days", args.retention_days, 1, MAX_RETENTION_DAYS)
    spd = _check_range("snapshots-per-day", args.snapshots_per_day, 1, MAX_SNAPSHOTS_PER_DAY)
    if args.disk_count is None:
        disk_count = 1
        if retention and spd:
            auto_filled.append("disk-count defaulted to 1 (declare it)")
    else:
        disk_count = _check_range("disk-count", args.disk_count, 1, MAX_DISK_COUNT)

    # ---- targets ----
    targets, invalid = normalize_targets(args.target or "")
    if invalid:
        print(f"[ERROR] unknown --target value(s): {', '.join(invalid)}",
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: valid targets are "
              + ", ".join(sorted(MECHANISM_RULES))
              + "; ask the customer which object must be backed up.")
        sys.exit(1)
    if args.cross_region and "off-site" in MECHANISM_RULES and "off-site" not in targets:
        targets.append("off-site")
    if not targets and (instance_ids or args.inventory):
        targets = ["whole-instance"]
        auto_filled.append("--target defaulted to whole-instance for the "
                           "given instance facts (declare it)")

    daily_change = normalize_daily_change(change_gb, args.change_period) \
        if change_gb else None

    # ---- actionability gate ----
    error_text = (args.error_text or "")[:MAX_TEXT_LEN]
    symptom = (args.symptom or "")[:MAX_TEXT_LEN]
    conditions = []
    for label, text in (("error-text", error_text), ("symptom", symptom)):
        if text.strip():
            conditions.append({"input": text,
                               "result": condition_result(classify_condition(text))})
    actionable = bool(targets or conditions or args.check_effectiveness
                      or args.inventory or instance_ids)
    if not actionable:
        print("[WARN] nothing to advise on: no --target, no instance ids, "
              "no --error-text/--symptom, no --check-effectiveness.",
              file=sys.stderr)
        report = {
            "modes": [], "region": region, "auto_filled": auto_filled,
            "identity_label": "", "facts": {"attempted": False, "uid": "",
                                            "instances": [], "missing": [],
                                            "errors": [], "statuses": {}},
            "design": {"status": "FAIL", "sections": [], "mechanisms": [], "docs": []},
            "cost_model": None, "effectiveness": None, "conditions": [],
            "degradation_log": ["no actionable input provided"],
            "data_sources": {"api_fetched": "", "customer_provided": "",
                             "not_fetched": ["everything"]},
            "references": [], "doc_note": DOC_VERIFICATION_NOTE,
            "status": "FAIL",
            "next_action": ("Ask the customer: which data must be backed up "
                            "(whole instance / files / database / local copy "
                            "/ off-site), in which region, and paste any "
                            "exact alert text. Then re-run."),
        }
        _emit(report, args, started_facts=False)
        sys.exit(1)

    # ---- read-only cloud facts ----
    facts = fetch_facts(region, instance_ids, args.inventory, args.profile)
    errors.extend(facts["errors"])

    # ---- design + cost ----
    design = design_plan(targets)
    cost = None
    if targets or data_size or daily_change or retention:
        cost = cost_model(data_size, daily_change, retention, spd,
                          disk_count, args.cross_region or ("off-site" in targets),
                          targets_files=("files" in targets))

    # ---- effectiveness ----
    eff = None
    if args.check_effectiveness:
        eff = effectiveness_sections(args.customer_report or "")

    # ---- status ----
    degraded = bool(errors)
    status = "DEGRADED" if degraded else "OK"
    if status == "OK":
        next_action = ("Share the plan; once the customer has performed the "
                       "console steps, re-run with --check-effectiveness "
                       "--customer-report \"<what the console shows>\" (and "
                       "the instance id) to rule-check the design. "
                       "Snapshot/policy facts remain customer-confirmed -- "
                       "this skill never performs console operations.")
    else:
        next_action = ("Some evidence calls failed (see the degradation "
                       "log). Relay the partial plan, state exactly which "
                       "facts are missing, and ask the customer to supply "
                       "them from the console or via a support ticket. Do "
                       "not fabricate the missing facts and do not work "
                       "around the failure with hand-written commands.")

    api_fetched = []
    if facts["uid"]:
        api_fetched.append("caller identity (STS get-caller-identity)")
    if facts["instances"]:
        api_fetched.append(f"{len(facts['instances'])} instance fact(s) via "
                           "ecs DescribeInstances")
    if facts["statuses"]:
        api_fetched.append(f"{len(facts['statuses'])} status record(s) via "
                           "ecs DescribeInstanceStatus")
    customer_provided = []
    for name, value in (("--target", targets), ("--data-size-gb", data_size),
                        ("--change-gb per period", (change_gb, args.change_period) if change_gb else None),
                        ("--retention-days", retention),
                        ("--snapshots-per-day", spd), ("--disk-count", disk_count),
                        ("--cross-region", args.cross_region or None),
                        ("--customer-report", (args.customer_report or "")[:80] or None),
                        ("--error-text/--symptom", (error_text or symptom) or None)):
        if value:
            customer_provided.append(f"{name}={value}")

    used_docs: list = []
    for key in design.get("docs", []):
        if key not in used_docs:
            used_docs.append(key)
    for cond in conditions:
        for key in cond["result"]["docs"]:
            if key not in used_docs:
                used_docs.append(key)
    if cost:
        for key in ("snapshot-billing-a", "snapshot-billing-b"):
            if key not in used_docs:
                used_docs.append(key)
    if eff:
        for key in ("enable-disable-auto-policy", "auto-snapshot-policy"):
            if key not in used_docs:
                used_docs.append(key)

    report = {
        "modes": (["design"] if design["sections"] else [])
                 + (["facts"] if facts["attempted"] else [])
                 + (["effectiveness"] if eff else [])
                 + (["condition"] if conditions else []),
        "region": region,
        "auto_filled": auto_filled,
        "identity_label": facts["uid"],
        "facts": facts,
        "design": design,
        "cost_model": cost,
        "effectiveness": eff,
        "conditions": conditions,
        "degradation_log": errors,
        "data_sources": {
            "api_fetched": "; ".join(api_fetched),
            "customer_provided": "; ".join(customer_provided),
            "not_fetched": [
                "snapshot usage and snapshot list",
                "automatic snapshot policies and their disk bindings",
                "file-backup jobs and covered paths",
                "in-guest disk usage / data volumes (customer self-check only)",
                "final billed amounts (model + example only)",
            ],
        },
        "references": build_reference_list(used_docs),
        "doc_note": DOC_VERIFICATION_NOTE,
        "status": status,
        "next_action": next_action,
    }
    _emit(report, args, started_facts=True)
    sys.exit(0)


def _emit(report: dict, args: argparse.Namespace, started_facts: bool) -> None:
    """Print the report (human or JSON). The STATUS/NEXT_ACTION contract
    lines are always present on stdout."""
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"STATUS: {report['status']}")
        print(f"NEXT_ACTION: {report['next_action']}")
    else:
        print(render_text(report))


if __name__ == "__main__":
    main()
