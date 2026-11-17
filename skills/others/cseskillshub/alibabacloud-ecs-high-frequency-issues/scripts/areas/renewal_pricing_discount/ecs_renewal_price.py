#!/usr/bin/env python3
"""
ecs_renewal_price.py -- SINGLE ENTRY for ECS Renewal Pricing & Discount
=======================================================================
Diagnosis (read-only + manual guidance).

SECURITY: This script is strictly READ-ONLY. It only invokes the whitelisted
read APIs below through the shared CLI layer and never mutates any cloud
resource, order, or configuration. Credentials are resolved exclusively by
the aliyun CLI default credential chain; this script never reads, prints,
passes or caches any AccessKey / Secret / STS token.

Authorized read-only actions (complete whitelist; anything else is FORBIDDEN):
  sts GetCallerIdentity                            (2015-04-01)
  ecs DescribeInstances                            (2014-05-26)
  ecs DescribeInstanceAutoRenewAttribute           (2014-05-26)
  bssopenapi QueryAvailableInstances               (2017-12-14)
  bssopenapi DescribePricingModule                 (2017-12-14)
  bssopenapi GetSubscriptionPrice                  (2017-12-14)

Modes (subcommands):
  inventory        Renewal fact baseline of ONE region: identity + instance
                   specs / charge type / expiry / bandwidth billing type +
                   auto-renewal attributes + expiry-risk list.
  expiring         Cross-region renewal inventory (BSS QueryAvailableInstances).
  pricing-modules  Billing-module discovery for the price composition
                   (BSS DescribePricingModule, ProductCode=ecs).
  quote            List-price trial via BSS GetSubscriptionPrice. Order type
                   and module list values must be EXPLICITLY supplied (they
                   are never guessed); supports multi-period comparison to
                   demonstrate duration-bound discount tiers. Every amount
                   is emitted with the mandatory list-price disclaimer.
  explain          Offline price-mismatch attribution: routes the customer's
                   own wording (or a quoted console page string) through the
                   embedded B1-B11 decision tree and outputs the matching
                   attribution + manual guidance + risk notices. No API call.
  handoff          Builds the standard information package for the business
                   / appeal / console / other-skill channels. Never collects
                   customer contact details. No API call.

Every run ends with the machine-readable contract lines:
  STATUS: OK | DEGRADED | FAIL
  NEXT_ACTION: <one instruction for the agent>

Exit codes: 0 = OK or DEGRADED (usable conclusion), 1 = FAIL (no usable
conclusion), 2 = argparse usage error.
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Optional

import _cli
from _constants import (
    BSS_PAGE_SIZE,
    BSS_SUBSCRIPTION_TYPES,
    ECS_PAGE_SIZE,
    ECS_PRODUCT_CODE,
    ECS_SUBSCRIPTION_TYPE,
    EXPIRY_URGENT_DAYS,
    EXPIRY_WARNING_DAYS,
    GLOSSARY,
    HANDOFF_CHANNELS,
    MISMATCH_BRANCHES,
    PAGE_STRINGS,
    PRICE_DISCLAIMER,
    RISK_NOTICES,
)

# ---------------------------------------------------------------------------
# Input validation (strict; anything unexpected is rejected BEFORE the CLI
# layer, so no caller-controlled string is ever interpreted by a shell).
# ---------------------------------------------------------------------------

_REGION_RE = re.compile(r"^[a-z][a-z0-9-]{1,29}$")
_INSTANCE_ID_RE = re.compile(r"^i-[a-zA-Z0-9]{6,40}$")
_ENUM_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,31}$")
_MODULE_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")

_MAX_INSTANCE_IDS = 50


def _validate_region(value: str, label: str) -> str:
    if not value or not _REGION_RE.match(value):
        raise SystemExit(
            f"[ERROR] invalid {label} {value!r}: expected a plain region id "
            "such as cn-hangzhou (never guessed; confirm with the customer)")
    return value


def _validate_instance_ids(value: str) -> str:
    """Accept one or a comma-separated list of ECS instance ids."""
    parts = [p.strip() for p in (value or "").split(",") if p.strip()]
    if not parts or len(parts) > _MAX_INSTANCE_IDS:
        raise SystemExit(
            f"[ERROR] --instance-id expects 1..{_MAX_INSTANCE_IDS} comma-"
            "separated instance ids like i-2zeexamplef13e4e573a")
    for p in parts:
        if not _INSTANCE_ID_RE.match(p):
            raise SystemExit(
                f"[ERROR] invalid instance id {p!r}: expected i-<alnum>")
    return ",".join(parts)


def _validate_enum_word(value: str, label: str) -> str:
    if not value or not _ENUM_WORD_RE.match(value):
        raise SystemExit(
            f"[ERROR] invalid {label} {value!r}: plain alphanumeric token "
            "only; use the exact value documented for the API")
    return value


def _parse_module_spec(spec: str, index: int) -> dict[str, str]:
    """Parse `ModuleCode=<c>;Config=<cfg>[;ModuleStatus=<s>][;Tag=<t>]`.

    Parameter NAMES mirror the public ModuleList.N.* shape of the pricing
    API; VALUES are pass-through (this skill never guesses enum members).
    """
    out: dict[str, str] = {}
    for chunk in spec.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        key, sep, value = chunk.partition("=")
        if not sep or not value.strip():
            raise SystemExit(
                f"[ERROR] --module[{index}] chunk {chunk!r} must be "
                "Key=Value (keys: ModuleCode, Config, ModuleStatus, Tag)")
        key = key.strip()
        if key not in ("ModuleCode", "Config", "ModuleStatus", "Tag"):
            raise SystemExit(
                f"[ERROR] --module[{index}] key {key!r} not allowed; use "
                "ModuleCode / Config / ModuleStatus / Tag exactly")
        if not _MODULE_KEY_RE.match(value.strip()) and key != "Config":
            raise SystemExit(
                f"[ERROR] --module[{index}] value for {key} looks invalid")
        out[key] = value.strip()
    if "ModuleCode" not in out:
        raise SystemExit(
            f"[ERROR] --module[{index}] must carry a ModuleCode= entry")
    return out


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

_TIME_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ")


def _parse_utc(value: Optional[str]) -> Optional[datetime]:
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(value or "", fmt).replace(
                tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _days_until(value: Optional[str]) -> Optional[int]:
    dt = _parse_utc(value)
    if dt is None:
        return None
    return (dt - datetime.now(timezone.utc)).days


# ---------------------------------------------------------------------------
# Report plumbing
# ---------------------------------------------------------------------------

class Report:
    """Accumulates findings, degradation marks and the final contract."""

    def __init__(self, title: str) -> None:
        self.title = title
        self.lines: list[str] = []
        self.errors: list[dict[str, str]] = []
        self.auto_filled: list[str] = []
        self.findings: list[str] = []
        self.suggestions: list[str] = []
        self.data: dict[str, Any] = {}
        self.status = "OK"
        self.next_action = ""

    def note(self, line: str = "") -> None:
        self.lines.append(line)

    def record_error(self, step: str, detail: str) -> None:
        self.errors.append({"step": step, "detail": detail})
        print(f"[WARN] {step}: {detail}", file=sys.stderr)
        self.status = "DEGRADED"

    def render(self, as_json: bool) -> None:
        if as_json:
            print(json.dumps({
                "mode": self.title,
                "status": self.status,
                "next_action": self.next_action,
                "auto_filled": self.auto_filled,
                "data": self.data,
                "key_findings": self.findings,
                "suggestions": self.suggestions,
                "errors": self.errors,
                "disclaimer": PRICE_DISCLAIMER,
            }, indent=2, ensure_ascii=False))
            return
        bar = "=" * 72
        print(bar)
        print(f" {self.title}")
        print(bar)
        for line in self.lines:
            print(line)
        if self.errors:
            print("\n## Graceful Degradation Log")
            for err in self.errors:
                print(f"  [DEGRADED] {err['step']}: {err['detail']}")
        if self.auto_filled:
            print("\n## Auto-filled Parameters")
            for item in self.auto_filled:
                print(f"  - {item}")
        print("\nSummary")
        print("-------")
        for finding in self.findings:
            print(f"  * {finding}")
        for suggestion in self.suggestions:
            print(f"  -> {suggestion}")


def _finish(rep: Report) -> int:
    """Emit the STATUS/NEXT_ACTION contract; return the exit code."""
    if rep.status == "FAIL":
        print("\nSTATUS: FAIL")
        print(f"NEXT_ACTION: {rep.next_action}")
        return 1
    print(f"\nSTATUS: {rep.status}")
    print(f"NEXT_ACTION: {rep.next_action}")
    return 0


# ---------------------------------------------------------------------------
# Mode: inventory (C1 + C2 single region)
# ---------------------------------------------------------------------------

def _fetch_auto_renew(rep: Report, region: str, instance_ids: list[str],
                      profile: Optional[str]) -> dict[str, dict[str, Any]]:
    """Best-effort auto-renewal attributes; failures degrade, never abort."""
    attrs: dict[str, dict[str, Any]] = {}
    if not instance_ids:
        return attrs
    try:
        body = _cli.call(
            "ecs", "DescribeInstanceAutoRenewAttribute",
            {"RegionId": region, "InstanceId": ",".join(instance_ids),
             "PageSize": str(ECS_PAGE_SIZE)},
            region=region, profile=profile)
    except _cli.CliError as e:
        rep.record_error(
            "DescribeInstanceAutoRenewAttribute",
            f"{e} | check RAM action ecs:DescribeInstanceAutoRenewAttribute")
        return attrs
    rows = (((body.get("InstanceSet") or {}).get("InstanceAutoRenewAttribute"))
            or [])
    for row in rows:
        iid = str(row.get("InstanceId") or "")
        if iid:
            attrs[iid] = {
                "auto_renew_enabled": bool(row.get("AutoRenewEnabled")),
                "renewal_status": str(row.get("RenewalStatus") or ""),
                "duration": row.get("Duration"),
                "period_unit": str(row.get("PeriodUnit") or ""),
            }
    return attrs


def mode_inventory(args: argparse.Namespace) -> int:
    rep = Report("ECS renewal fact baseline (single region)")
    region = _validate_region(args.region, "--region")
    rep.data["region"] = region

    _cli.check_cli_available()

    uid = _cli.resolve_account_id(profile=args.profile)
    if uid:
        rep.data["uid"] = uid
        rep.note(f"Account UID (auto-derived via STS GetCallerIdentity): {uid}")
        rep.auto_filled.append(
            "UID auto-derived via sts GetCallerIdentity: " + uid)
    else:
        rep.record_error(
            "sts GetCallerIdentity",
            "identity unavailable; results still valid for the configured "
            "credential but cannot be attributed to a UID. Configure the "
            "CLI credential chain (aliyun sts get-caller-identity); never pass AK/SK.")
        rep.data["uid"] = ""

    params: dict[str, Any] = {"RegionId": region}
    instance_ids: Optional[str] = None
    if args.instance_id:
        instance_ids = _validate_instance_ids(args.instance_id)
        params["InstanceIds"] = f"[{instance_ids}]"

    try:
        instances, page_err = _cli.paginate_pagenum(
            "ecs", "DescribeInstances", params,
            items_path=["Instances", "Instance"],
            total_path=["TotalCount"], region=region, profile=args.profile,
            page_size=ECS_PAGE_SIZE)
    except _cli.CliError as e:  # defensive; paginate already degrades
        instances, page_err = [], str(e)
    if page_err:
        rep.record_error("DescribeInstances", page_err)

    if not instances and not page_err:
        rep.note(f"No ECS instances visible in {region} for this account.")
        rep.findings.append(
            f"Region {region}: zero instances visible to this credential - "
            "confirm the region and the account with the customer before "
            "answering any pricing question.")
        rep.suggestions.append(
            "Ask the customer to confirm the region, or run the expiring "
            "mode for a cross-region renewal inventory.")
        rep.status = "OK"
        rep.next_action = (
            "confirm the region with the customer, then rerun inventory or "
            "use the expiring mode")
        rep.render(args.json)
        return _finish(rep)

    if not instances and page_err:
        # Read failure is NOT evidence of zero instances.
        rep.findings.append(
            f"Region {region}: instance data unavailable because the read "
            "call failed - never interpret this as 'no instances'. Fix the "
            "credential or permission shown in the degradation log "
            "(references/ram-policies.md) and rerun.")
        rep.next_action = (
            "repair the credential/RAM issue named in the degradation log, "
            "then rerun inventory --region " + region)
        rep.render(args.json)
        return _finish(rep)

    subscription_ids = [
        str(i.get("InstanceId") or "")
        for i in instances
        if str(i.get("InstanceChargeType") or "") == "PrePaid"
    ]
    attrs = _fetch_auto_renew(rep, region, subscription_ids, args.profile)

    rep.note(f"\nInstances in {region}: {len(instances)}")
    rep.note("  InstanceId            Status     ChargeType  ExpiredTime"
             "         AutoRenew  Type                Bandwidth billing")
    risky: list[str] = []
    rows: list[dict[str, Any]] = []
    for inst in instances:
        iid = str(inst.get("InstanceId") or "")
        expired = str(inst.get("ExpiredTime") or "")
        charge = str(inst.get("InstanceChargeType") or "")
        attr = attrs.get(iid) or {}
        if charge != "PrePaid":
            auto = "-"
        elif attr:
            auto = "on" if attr.get("auto_renew_enabled") else "off"
        else:
            auto = "unknown"
        days = _days_until(expired if charge == "PrePaid" else None)
        row = {
            "instance_id": iid,
            "status": str(inst.get("Status") or ""),
            "instance_type": str(inst.get("InstanceType") or ""),
            "charge_type": charge,
            "expired_time": expired,
            "days_to_expiry": days,
            "internet_charge_type": str(
                inst.get("InternetChargeType") or ""),
            "auto_renew": attr or None,
        }
        rows.append(row)
        flag = ""
        if charge == "PrePaid" and days is not None:
            if days < 0:
                flag = "ALREADY-EXPIRED"
            elif days <= EXPIRY_URGENT_DAYS:
                flag = f"EXPIRES-IN-{days}D"
            elif days <= EXPIRY_WARNING_DAYS:
                flag = f"expires-in-{days}d"
            if flag:
                risky.append(f"{iid}: {flag} (auto-renew {auto})")
        rep.note(f"  {iid:<22}{row['status']:<11}{charge:<12}"
                 f"{expired:<20}{auto:<11}"
                 f"{row['instance_type']:<20}"
                 f"{row['internet_charge_type']}  {flag}".rstrip())

    rep.data["instances"] = rows
    rep.data["expiry_risk"] = risky

    rep.findings.append(
        f"Region {region}: {len(instances)} instance(s) inventoried; "
        f"{len(subscription_ids)} subscription (PrePaid).")
    if risky:
        rep.findings.append(
            f"{len(risky)} instance(s) in the expiry window (<= "
            f"{EXPIRY_WARNING_DAYS} days or already expired). Renewal "
            "guidance is MANUAL ONLY: order placement and payment are "
            "console actions performed by the customer.")
    else:
        rep.findings.append("No instance is inside the 30-day expiry window.")
    rep.suggestions.append(
        "For renewal/upgrade price questions run the quote mode "
        "(list-price trial; console real-time price prevails) and, for a "
        "price mismatch, the explain mode with the customer's own wording.")
    rep.suggestions.append(
        "Amounts presented to the customer MUST carry the list-price "
        "disclaimer; see the DISCLAIMER line of this output.")

    rep.next_action = (
        "use the facts above; for discount/quote requests route to handoff "
        "--channel business, for price-mismatch questions to explain "
        "--symptom \"<customer wording>\"")
    rep.render(args.json)
    return _finish(rep)


# ---------------------------------------------------------------------------
# Mode: expiring (C2 cross region)
# ---------------------------------------------------------------------------

def mode_expiring(args: argparse.Namespace) -> int:
    rep = Report("Cross-region renewables inventory (BSS)")
    _cli.check_cli_available()

    params: dict[str, Any] = {
        "ProductCode": ECS_PRODUCT_CODE,
        "SubscriptionType": ECS_SUBSCRIPTION_TYPE,
    }
    if args.instance_ids:
        params["InstanceIDs"] = _validate_instance_ids(args.instance_ids)
    if args.renew_status:
        params["RenewStatus"] = _validate_enum_word(
            args.renew_status, "--renew-status")
    if args.end_time_end:
        params["EndTimeEnd"] = args.end_time_end

    items, err = _cli.paginate_pagenum(
        "bssopenapi", "QueryAvailableInstances", params,
        items_path=["Data", "Instances", "Instance"],
        total_path=["Data", "TotalCount"],
        region=None, profile=args.profile, page_size=BSS_PAGE_SIZE,
        page_num_key="PageNum", page_size_key="PageSize")
    if err:
        rep.record_error(
            "QueryAvailableInstances",
            f"{err} | check RAM action bss:DescribeInstances")

    uid = _cli.resolve_account_id(profile=args.profile)
    rep.data["uid"] = uid
    if uid:
        rep.note(f"Account UID (auto-derived via STS GetCallerIdentity): {uid}")

    rep.data["renewables"] = items
    rep.note(f"\nSubscription ECS instances visible to the billing inventory: "
             f"{len(items)}")
    by_region: dict[str, int] = {}
    urgent: list[str] = []
    for row in items:
        region = str(row.get("Region") or "?")
        by_region[region] = by_region.get(region, 0) + 1
        end = str(row.get("EndTime") or "")
        days = _days_until(end)
        iid = str(row.get("InstanceID") or "")
        renew_state = str(row.get("RenewStatus") or "")
        if days is not None and days <= EXPIRY_WARNING_DAYS:
            urgent.append(
                f"{iid} ({region}): ends {end} ({days}d left), "
                f"renewal state {renew_state or 'unknown'}")
        rep.note(f"  {iid:<24}{region:<16}{end:<24}{renew_state}")
    rep.data["by_region"] = by_region
    rep.data["urgent"] = urgent

    if urgent:
        rep.findings.append(
            f"{len(urgent)} instance(s) end within {EXPIRY_WARNING_DAYS} "
            "days or already passed EndTime - state the expiry risk facts, "
            "never a price figure.")
    rep.findings.append(
        "Cross-region totals: "
        + (", ".join(f"{k}={v}" for k, v in sorted(by_region.items()))
           or "none"))
    rep.suggestions.append(
        "Renewal itself is performed by the customer in the console "
        "(renew wizard). For per-instance detail (specs, charge type) run "
        "the inventory mode per region.")
    rep.suggestions.append(
        "Order-level questions (history, voided orders) are beyond the "
        "authorized action set of this skill: point the customer to the "
        "order management page (handoff --channel console).")
    rep.next_action = (
        "for each at-risk instance run inventory --region <its region> to "
        "confirm specs and auto-renew state before answering")
    rep.render(args.json)
    return _finish(rep)


# ---------------------------------------------------------------------------
# Mode: pricing-modules (C3 composition discovery)
# ---------------------------------------------------------------------------

def mode_pricing_modules(args: argparse.Namespace) -> int:
    rep = Report("ECS billing-module discovery (price composition)")
    _cli.check_cli_available()

    subscription_type = _validate_enum_word(
        args.subscription_type, "--subscription-type")
    if subscription_type not in BSS_SUBSCRIPTION_TYPES:
        raise SystemExit(
            "[ERROR] --subscription-type must be Subscription or PayAsYouGo "
            "(public BSS enum)")

    params: dict[str, Any] = {
        "ProductCode": args.product_code,
        "SubscriptionType": subscription_type,
    }
    if args.product_type:
        params["ProductType"] = args.product_type

    try:
        body = _cli.call("bssopenapi", "DescribePricingModule", params,
                         region=None, profile=args.profile)
    except _cli.CliError as e:
        rep.record_error(
            "DescribePricingModule",
            f"{e} | check RAM action bss:DescribePricingModule")
        body = {}

    modules = (((body.get("Data") or {}).get("ModuleList") or {})
               .get("Module")) or []
    attr_names = sorted({
        str(attr.get("Name") or attr.get("Code") or "")
        for mod in modules
        for attr in (((mod.get("ConfigList") or {}).get("ConfigList"))
                     or ((mod.get("AttributeList") or {}).get("Attribute"))
                     or [])
        if str(attr.get("Name") or attr.get("Code") or "")
    })
    rep.data["modules"] = [
        {"module_code": str(m.get("ModuleCode") or ""),
         "name": str(m.get("Name") or "")}
        for m in modules]
    rep.data["config_attributes"] = attr_names

    rep.note("Billing modules for the queried product (use their ModuleCode "
             "values in the quote mode --module entries):")
    for mod in modules:
        rep.note(f"  {str(mod.get('ModuleCode') or '?'):<24}"
                 f"{str(mod.get('Name') or '')}")
    if not modules:
        rep.findings.append(
            "No modules returned - the quote mode degrades to the purchase-"
            "page fallback口径: guide the customer to the console wizard.")

    rep.findings.append(
        f"{len(modules)} billing module(s) discovered; this is how a renewal "
        "quote splits into instance / disk / bandwidth components.")
    rep.suggestions.append(
        "Feed the module codes into the quote mode as --module "
        "\"ModuleCode=<code>;Config=<key:value...>\" lines taken from the "
        "console selection; NEVER invent config values.")
    rep.suggestions.append(
        "If the customer only needs the final payable figure, point to the "
        "purchase page real-time price (handoff --channel console).")
    rep.next_action = (
        "run quote with explicit --order-type and --module values taken "
        "from the customer's console selections")
    rep.render(args.json)
    return _finish(rep)


# ---------------------------------------------------------------------------
# Mode: quote (C3 list-price trial + B1 tier demo)
# ---------------------------------------------------------------------------

def _quote_once(args: argparse.Namespace, period: Optional[int]) -> dict:
    params: dict[str, Any] = {
        "SubscriptionType": args.subscription_type,
        "ProductCode": args.product_code,
        "OrderType": args.order_type,
    }
    for idx, spec in enumerate(args.module, start=1):
        parsed = _parse_module_spec(spec, idx)
        for key, value in parsed.items():
            params[f"ModuleList.{idx}.{key}"] = value
    if period is not None:
        params["ServicePeriodQuantity"] = str(period)
        params["ServicePeriodUnit"] = args.unit
    if args.quantity:
        params["Quantity"] = str(args.quantity)
    if args.region:
        params["Region"] = _validate_region(args.region, "--region")
    if args.instance_id:
        params["InstanceId"] = _validate_instance_ids(args.instance_id)
    try:
        body = _cli.call("bssopenapi", "GetSubscriptionPrice", params,
                         region=None, profile=args.profile)
    except _cli.CliError as e:
        return {"error": str(e),
                "ram_hint": "check RAM action bss:DescribePrice"}
    data = body.get("Data") or {}
    rules = (((data.get("Rules") or {}).get("Rule"))) or []
    return {
        "request": {k: v for k, v in params.items()},
        "original_price": data.get("OriginalPrice"),
        "discount_price": data.get("DiscountPrice"),
        "trade_price": data.get("TradePrice"),
        "currency": data.get("Currency"),
        "rules": [str(r.get("Description") or r.get("RuleId") or "")
                  for r in rules],
        "code": body.get("Code"),
    }


def mode_quote(args: argparse.Namespace) -> int:
    rep = Report("Renewal/change list-price trial (GetSubscriptionPrice)")

    if not args.order_type or not args.module:
        rep.status = "FAIL"
        rep.findings.append(
            "OrderType and at least one ModuleList entry are REQUIRED and "
            "this skill never guesses them: their valid values must come "
            "from the pricing-modules discovery output combined with the "
            "customer's console selections, or from the official API doc.")
        rep.suggestions.append(
            "Fallback consistent with human support practice: state that "
            "the authoritative figure is the purchase-page real-time price "
            "and hand the customer the wizard path (ECS console -> "
            "renew / upgrade, stop before payment to read the quote).")
        rep.next_action = (
            "rerun with --order-type and --module values, or fall back to "
            "the purchase-page guidance")
        rep.render(args.json)
        return _finish(rep)

    _cli.check_cli_available()
    args.order_type = _validate_enum_word(args.order_type, "--order-type")
    args.subscription_type = _validate_enum_word(
        args.subscription_type, "--subscription-type")
    if args.subscription_type not in BSS_SUBSCRIPTION_TYPES:
        raise SystemExit(
            "[ERROR] --subscription-type must be Subscription or PayAsYouGo")

    periods: list[Optional[int]] = [None]
    if args.compare_periods:
        wanted = []
        for chunk in args.compare_periods.split(","):
            chunk = chunk.strip()
            if not chunk.isdigit() or not 1 <= int(chunk) <= 120:
                raise SystemExit(
                    "[ERROR] --compare-periods expects 1..120-sized comma "
                    "list, e.g. 12,24,36")
            wanted.append(int(chunk))
        if not wanted:
            raise SystemExit("[ERROR] --compare-periods is empty")
        periods = wanted
        rep.auto_filled.append(
            f"trial periods auto-expanded for tier comparison: {wanted} "
            f"{args.unit}(s)")

    trials: list[dict[str, Any]] = []
    failures = 0
    for period in periods:
        result = _quote_once(args, period)
        result["period"] = period
        trials.append(result)
        if "error" in result:
            failures += 1
            rep.record_error(
                f"GetSubscriptionPrice(period={period})",
                f"{result['error']} | {result['ram_hint']}")

    rep.data["trials"] = trials
    rep.note("Each amount below is a LIST-PRICE trial. " + PRICE_DISCLAIMER)
    for result in trials:
        label = f"period {result['period']} {args.unit}" \
            if result["period"] else "default period"
        if "error" in result:
            rep.note(f"  {label}: TRIAL FAILED (degraded, see log)")
            continue
        rep.note(
            f"  {label}: original={result['original_price']} "
            f"discount={result['discount_price']} "
            f"trade={result['trade_price']} {result['currency'] or ''}")
        for rule in result["rules"]:
            if rule:
                rep.note(f"      rule: {rule}")

    if failures == len(trials):
        rep.status = "DEGRADED"
        rep.findings.append(
            "Every trial call failed; no figure was produced. Do NOT "
            "guess amounts: fall back to the documented wording plus the "
            "purchase-page real-time price guidance.")
    elif len(periods) > 1:
        prices = [t.get("original_price") for t in trials
                  if "error" not in t]
        rep.findings.append(
            "Multi-period trial completed: compare the rows to SHOW how the "
            "list-price composition changes with the requested period "
            "(duration-bound tier demo, branch B1).")
        if any(p for p in prices):
            rep.findings.append(
                "Differences between period rows are list-price effects "
                "only; account/activity discount tiers are not reflected - "
                "state the tier MECHANISM, never a payable figure.")
    else:
        rep.findings.append("Single trial completed (list-price basis).")

    rep.suggestions.append(
        "Any customer-facing restatement of these numbers MUST include the "
        "disclaimer line above verbatim, and must never be phrased as "
        "'you will pay X'.")
    rep.next_action = (
        "attribute price differences with explain --symptom; route any "
        "discount request via handoff --channel business")
    rep.render(args.json)
    return _finish(rep)


# ---------------------------------------------------------------------------
# Mode: explain (C4 attribution tree, offline)
# ---------------------------------------------------------------------------

_RISK_HEAVY_BRANCHES = {"B5", "B7", "B8", "B10", "B11"}


def route_symptom(text: str) -> list[dict[str, Any]]:
    """Pure function: match customer wording against the B1-B11 table.

    Matching is case-insensitive substring on the branch keyword list.
    Never raises; empty input yields no branches.
    """
    low = (text or "").lower()
    hits: list[dict[str, Any]] = []
    for branch in MISMATCH_BRANCHES:
        for kw in branch["keywords"]:
            if kw.lower() in low:
                hits.append(branch)
                break
    return hits


# Boundary assertions (pure routing function; runs at import).
assert route_symptom("") == []
assert any(b["id"] == "B2" for b in route_symptom(
    "renewal page shows a discount but payment page shows full price"))
assert any(b["id"] == "B7" for b in route_symptom(
    "the downgrade refund shows 0 yuan"))


def mode_explain(args: argparse.Namespace) -> int:
    rep = Report("Price-mismatch attribution (decision tree B1-B11)")
    symptom = args.symptom or ""
    hits = route_symptom(symptom)

    rep.data["symptom"] = symptom
    rep.data["page_string_reference"] = PAGE_STRINGS
    rep.data["glossary"] = GLOSSARY

    if args.expired_in_days is not None:
        rep.data["expired_in_days"] = args.expired_in_days

    if not hits:
        rep.findings.append(
            "No branch matched the supplied wording. Do NOT invent an "
            "attribution: collect the fact baseline first (inventory / "
            "expiring modes), then ask the customer ONE clarifying question "
            "(what exactly was quoted where and when).")
        rep.suggestions.append(
            "Usable next probes: inventory --region <r>; expiring; "
            "handoff --channel console for order-page self-check.")
        rep.next_action = (
            "run inventory/expiring to ground the facts, then rerun explain "
            "with the customer's concrete page wording")
        rep.render(args.json)
        return _finish(rep)

    rep.note(f"Customer wording: \"{symptom}\"\n")
    for branch in hits:
        rep.note(f"[{branch['id']}] {branch['name']}")
        rep.note(f"  attribution : {branch['attribution']}")
        rep.note(f"  guidance    : {branch['guidance']}")
        rep.note(f"  full text   : {branch['reference']}")
        if branch["id"] == "B1" and args.expired_in_days is not None:
            rep.note(
                f"  fact        : instance expires in "
                f"{args.expired_in_days} day(s) - cross-checked against the "
                "duration-bound tier window (whole-year boundaries).")
        if branch["id"] == "B10" and args.expired_in_days is not None:
            rep.note(
                f"  fact        : remaining validity {args.expired_in_days} "
                "day(s); a console figure next to an upgrade/expansion "
                "commonly covers ONLY this remainder.")
        rep.note("")
        rep.findings.append(
            f"Matched {branch['id']} ({branch['name']}); relay its "
            "attribution and manual guidance, with the disclaimer.")

    if any(b["id"] in _RISK_HEAVY_BRANCHES for b in hits):
        rep.note("## Mandatory risk notices (output BEFORE guidance)")
        for notice in RISK_NOTICES:
            rep.note(f"  ! {notice}")
        rep.note("")
        rep.data["risk_notices"] = RISK_NOTICES
        rep.findings.append(
            "Risk-heavy branch: the mandatory notices block is included; "
            "output it ahead of any console steps.")

    rep.data["branches"] = [b["id"] for b in hits]
    rep.suggestions.append(
        "This skill explains rules and shows list-price composition; the "
        "final payable amount and every executed action stay with the "
        "customer's console.")
    rep.next_action = (
        "compose the answer from the matched branches; route discount "
        "demands to handoff --channel business")
    rep.render(args.json)
    return _finish(rep)


# ---------------------------------------------------------------------------
# Mode: handoff (C5 information package, offline)
# ---------------------------------------------------------------------------

def mode_handoff(args: argparse.Namespace) -> int:
    rep = Report("Channel handoff information package")
    key = (args.channel or "").strip().lower().replace("_", "-")
    if key == "otherskill":
        key = "other-skill"
    if key not in HANDOFF_CHANNELS:
        raise SystemExit(
            "[ERROR] --channel must be one of: "
            + ", ".join(sorted(HANDOFF_CHANNELS)))
    spec = HANDOFF_CHANNELS[key]

    facts = {
        "account_uid": args.uid or "<from sts_token.py / inventory output>",
        "instance_id": args.instance_id or
                       "<from inventory / expiring output>",
        "region": args.region or "<confirmed with the customer>",
        "expired_time": args.expired_time or
                        "<from inventory ExpiredTime>",
        "charge_type": args.charge_type or
                       "<from inventory InstanceChargeType>",
        "customer_request": args.request or "<one line, customer's words>",
    }
    rep.data["channel"] = key
    rep.data["facts"] = facts

    rep.note(f"Target channel : {key}")
    rep.note(f"When          : {spec['when']}")
    rep.note(f"Boundary line : {spec['boundary_line']}")
    rep.note("\nInformation package fields:")
    for field in spec["fields"]:
        rep.note(f"  - {field}")
    rep.note("\nFilled facts (leave placeholders until evidenced):")
    for name, value in facts.items():
        rep.note(f"  {name:<15}: {value}")
    if key == "business":
        rep.note("\nPII rule: this skill NEVER collects, stores or forwards "
                 "customer phone numbers or emails. The customer supplies "
                 "contact details to the business channel themselves.")

    rep.findings.append(
        f"{key.capitalize()} handoff package prepared. Relay it verbatim; "
        "do not add promised outcomes (no discount, no approval, no review "
        "result may be predicted).")
    rep.suggestions.append(
        "Attach the inventory/expiring outputs as evidence when available; "
        "an un-evidenced package with placeholders must not be sent.")
    rep.next_action = (
        "present the package; if facts are still placeholders, run "
        "inventory --region <r> first")
    rep.render(args.json)
    return _finish(rep)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecs_renewal_price.py",
        description=(
            "Read-only ECS renewal pricing & discount diagnosis entry. "
            "All amounts are list-price trials; final prices come from the "
            "customer's console in real time."),
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    common.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")

    sub = parser.add_subparsers(dest="mode", required=True)

    p_inv = sub.add_parser(
        "inventory", parents=[common],
        help="single-region renewal fact baseline (read-only)")
    p_inv.add_argument("--region", required=True,
                       help="ECS region id, e.g. cn-hangzhou (never guessed)")
    p_inv.add_argument("--instance-id", default=None,
                       help="optional i-... id(s), comma-separated")
    p_inv.set_defaults(func=mode_inventory)

    p_exp = sub.add_parser(
        "expiring", parents=[common],
        help="cross-region renewables inventory (BSS, read-only)")
    p_exp.add_argument("--instance-ids", default=None,
                       help="optional i-... id(s), comma-separated filter")
    p_exp.add_argument("--renew-status", default=None,
                       help="optional RenewStatus filter, exact value from "
                            "the official API doc (never guessed)")
    p_exp.add_argument("--end-time-end", default=None,
                       help="optional EndTime upper bound, UTC ISO format "
                            "as accepted by the API")
    p_exp.set_defaults(func=mode_expiring)

    p_mod = sub.add_parser(
        "pricing-modules", parents=[common],
        help="billing-module discovery for price composition (read-only)")
    p_mod.add_argument("--product-code", default=ECS_PRODUCT_CODE,
                       help="BSS product code (default: ecs)")
    p_mod.add_argument("--subscription-type", default=ECS_SUBSCRIPTION_TYPE,
                       help="Subscription (default) or PayAsYouGo")
    p_mod.add_argument("--product-type", default=None,
                       help="optional exact ProductType value")
    p_mod.set_defaults(func=mode_pricing_modules)

    p_q = sub.add_parser(
        "quote", parents=[common],
        help="list-price trial via GetSubscriptionPrice (values are "
             "pass-through; never guessed)")
    p_q.add_argument("--order-type", default=None,
                     help="EXACT OrderType value from the official API doc")
    p_q.add_argument("--module", action="append", default=[],
                     help="repeatable: ModuleCode=<code>;Config=<k:v;...>"
                          "[;ModuleStatus=<s>][;Tag=<t>]")
    p_q.add_argument("--product-code", default=ECS_PRODUCT_CODE)
    p_q.add_argument("--subscription-type", default=ECS_SUBSCRIPTION_TYPE)
    p_q.add_argument("--unit", default="Month", choices=["Month", "Year"],
                     help="ServicePeriodUnit")
    p_q.add_argument("--compare-periods", default=None,
                     help="comma list, e.g. 12,24,36 - demo of duration-"
                          "bound tier steps")
    p_q.add_argument("--quantity", default=None,
                     help="optional Quantity integer")
    p_q.add_argument("--region", default=None,
                     help="optional Region parameter (validated region id)")
    p_q.add_argument("--instance-id", default=None,
                     help="optional i-... instance id for the trial")
    p_q.set_defaults(func=mode_quote)

    p_ex = sub.add_parser(
        "explain", parents=[common],
        help="offline attribution of price mismatches (decision tree)")
    p_ex.add_argument("--symptom", default="",
                      help="the customer's OWN wording (translated or raw)")
    p_ex.add_argument("--expired-in-days", type=int, default=None,
                      help="fact from inventory output; strengthens B1/B10")
    p_ex.set_defaults(func=mode_explain)

    p_h = sub.add_parser(
        "handoff", parents=[common],
        help="build the standard channel handoff information package")
    p_h.add_argument("--channel", required=True,
                     help="business | appeal | console | other-skill")
    p_h.add_argument("--uid", default=None)
    p_h.add_argument("--instance-id", default=None)
    p_h.add_argument("--region", default=None)
    p_h.add_argument("--expired-time", default=None)
    p_h.add_argument("--charge-type", default=None)
    p_h.add_argument("--request", default=None,
                     help="one line: what the customer wants (in their words)")
    p_h.set_defaults(func=mode_handoff)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
