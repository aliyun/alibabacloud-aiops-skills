#!/usr/bin/env python3
"""
AK Leak Incident Response Investigation Script (Dual-Backend Version)
====================================================================
Implements the 6-step chain-following SOP using Alibaba Cloud OpenAPIs, routed
through the dual-backend layer in `_cli.py` (aliyun CLI preferred, direct
V3-signed HTTPS fallback):
  1. Notification verification (Security Center DescribeAccesskeyLeakList)
  2. Leaked AK operation audit (ActionTrail LookupEvents, EventAccessKeyId filter)
  3. Cross-product operation grouping (by eventSource)
  4. Sub-user chain tracing (User filter for each CreateUser target)
  5. New AK chain tracing (recursive EventAccessKeyId for each CreateAccessKey)
  6. Operational timeline report with 6-section English conclusion

Usage:
    python ak_leak_investigation.py --ak <AK> --account <UID> [options]

Authentication:
    Handled by the active backend (see _cli.py). The CLI backend uses the
    aliyun CLI profile (~/.aliyun/config.json); the HTTP fallback resolves
    credentials from ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
    (+ optional ALIBABA_CLOUD_SECURITY_TOKEN) or ~/.aliyun/config.json.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cli
import _constants

DANGEROUS_SERVICES = _constants.DANGEROUS_SERVICES
HIGH_RISK_EVENTS = _constants.HIGH_RISK_EVENTS
SERVICE_SOURCE_PREFIXES = _constants.SERVICE_SOURCE_PREFIXES

# Region / CLI profile are set by main() and consumed by the query helpers.
_REGION = "cn-shanghai"
_PROFILE = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AK Leak Incident Response -- 6-step chain-following investigation (Public API)"
    )
    parser.add_argument("--ak", required=True, help="Leaked AccessKey ID")
    parser.add_argument("--account", default=None,
                        help="Alibaba Cloud MAIN account UID (optional; auto-derived from the "
                             "credential's STS AccountId if omitted). Provide the MAIN account UID, "
                             "NOT a RAM sub-user's numeric ID -- STS AccountId is the main UID for "
                             "root, RAM sub-users, and assumed-roles alike.")
    parser.add_argument("--days", type=int, default=30,
                        help="ActionTrail lookback in days (max 90, default 30)")
    _default_output = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "output", "ak_leak_report.md",
    )
    parser.add_argument("--output", default=_default_output, help="Output file path")
    parser.add_argument("--services", default=",".join(DANGEROUS_SERVICES),
                        help="Comma-separated service list")
    parser.add_argument("--profile", default=None,
                        help="aliyun CLI profile name (optional; uses CLI default profile)")
    parser.add_argument("--region", default="cn-shanghai",
                        help="Alibaba Cloud region (default: cn-shanghai)")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown",
                        help="Report output format")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Step 1: Notification Verification (Security Center)
# ---------------------------------------------------------------------------

def query_ak_leak_detection(ak: str = "", days: int = 30) -> dict[str, Any]:
    """Query Security Center for AK leak detection alerts via the dual-backend layer."""
    result = {
        "source": "security_center",
        "alert_detected": False,
        "total_records": 0,
        "records": [],
        "aks_found_in_alert": [],
    }
    try:
        params = {"CurrentPage": 1, "PageSize": 100}
        if ak:
            params["Query"] = f"ak:{ak}"
        body = _cli.call("sas", "DescribeAccesskeyLeakList", params,
                         region=_REGION, profile=_PROFILE)
        records = body.get("AccessKeyLeakList") or []
        total = body.get("TotalCount", 0) or 0
        result["total_records"] = total
        result["records"] = [
            {"ak": r.get("AccesskeyId") or r.get("AccessKeyId", ""), "type": r.get("Type", ""),
             "status": r.get("Status", ""), "deal_time": r.get("DealTime", ""),
             "url": r.get("Url", "")}
            for r in records
        ]
        result["alert_detected"] = total > 0
        aks = {r.get("AccesskeyId") or r.get("AccessKeyId") for r in records}
        result["aks_found_in_alert"] = sorted(a for a in aks if a)
    except _cli.CliError as e:
        print(f"[WARN] DescribeAccesskeyLeakList failed: {e} — continuing with degradation (Step 1 skipped)", file=sys.stderr)
        code = e.code or ""
        if "NoPermission" in code or "Forbidden" in code:
            result["error"] = f"Security Center access denied (credential lacks yundun-aegis:DescribeAccesskeyLeakList): {e}"
        else:
            result["error"] = str(e)
    return result


def infer_ban_from_actiontrail(ak: str, start_time: str, end_time: str) -> dict[str, Any]:
    """Infer AK ban status from ActionTrail error codes via the dual-backend layer."""
    result = {"ak_ban_inferred": False, "ban_error_codes": [], "total_events": 0, "failed_events": 0}
    if not ak:
        return result
    ban_error_set = {
        "InvalidAccessKeyId.Inactive", "Forbidden.AccessKeyDisabled",
        "Forbidden.AccessKey", "InvalidAccessKeyId.NotFound",
    }
    try:
        events = _cli.paginate_next_token(
            "actiontrail", "LookupEvents",
            {"StartTime": start_time, "EndTime": end_time, "MaxResults": 50,
             "LookupAttribute.1.Key": "EventAccessKeyId", "LookupAttribute.1.Value": ak},
            region=_REGION, profile=_PROFILE,
        )
        ban_codes = set()
        total = len(events)
        failed = 0
        for evt in events:
            ec = (evt.get("errorCode") if isinstance(evt, dict) else "") or ""
            if ec in ban_error_set:
                failed += 1
                ban_codes.add(ec)
        result["total_events"] = total
        result["failed_events"] = failed
        result["ban_error_codes"] = sorted(ban_codes)
        if total > 0 and failed == total and ban_codes:
            result["ak_ban_inferred"] = True
    except _cli.CliError as e:
        print(f"[WARN] ActionTrail LookupEvents (ban inference) failed: {e} — continuing with degradation", file=sys.stderr)
        result["error"] = str(e)
    return result


# ---------------------------------------------------------------------------
# Step 2: AK Info Query (RAM)
# ---------------------------------------------------------------------------

def _resolve_ak_owner(ak: str, start_time: str = "", end_time: str = "") -> str:
    """Best-effort: find the RAM user name that owns `ak` from ActionTrail.

    Reads `userIdentity.userName` from a recent event for this AccessKey. Used
    to satisfy GetAccessKeyLastUsed's UserName requirement when the caller is
    not the AK owner (e.g. an assumed-role or root credential). Returns "" when
    the owner cannot be determined.
    """
    if not (start_time and end_time):
        return ""
    try:
        body = _cli.call("actiontrail", "LookupEvents", {
            "StartTime": start_time, "EndTime": end_time, "MaxResults": 10,
            "LookupAttribute.1.Key": "EventAccessKeyId",
            "LookupAttribute.1.Value": ak,
        }, region=_REGION, profile=_PROFILE)
        for evt in (body.get("Events") or []):
            name = (evt.get("userIdentity") or {}).get("userName") or ""
            if name:
                return name
    except _cli.CliError:
        print("[WARN] ActionTrail LookupEvents (AK owner reverse-lookup) failed — continuing with degradation", file=sys.stderr)
    return ""


def query_ak_info(ak: str, start_time: str = "", end_time: str = "") -> dict[str, Any]:
    """Query AK usage info via RAM GetAccessKeyLastUsed (dual-backend layer).

    Note: the public RAM API has no way to fetch an arbitrary AK's owner /
    create time / status. The closest public signal is GetAccessKeyLastUsed,
    which returns the last-used time.
    Owner/createTime/status are cross-referenced from ActionTrail instead.
    """
    result = {"accessKeyId": ak, "status": "N/A", "createTime": "N/A",
              "owner": "N/A", "type": "N/A"}
    try:
        body = _cli.call("ram", "GetAccessKeyLastUsed",
                         {"UserAccessKeyId": ak}, region=_REGION, profile=_PROFILE)
        last_used = body.get("AccessKeyLastUsed") or {}
        if last_used:
            result["lastUsedTime"] = last_used.get("LastUsedDate", "N/A")
            result["lastUsedService"] = last_used.get("ServiceName", "N/A")
    except _cli.CliError as e:
        # RAM-user / assumed-role / root callers must pass UserName for
        # GetAccessKeyLastUsed (the API returns "MissingParameter: Parameter
        # UserName is required" otherwise). Discover the AK's owner and retry:
        # prefer the caller's own name, else derive the owner from ActionTrail.
        # A successful retry also confirms ownership, so we fill in the owner
        # (otherwise not resolvable via read-only public API).
        if "UserName" in str(e) or "MissingParameter" in str(e):
            print(f"[WARN] GetAccessKeyLastUsed failed: {e} — retrying with resolved UserName (degradation)", file=sys.stderr)
            owner_name = (_cli.resolve_caller_username(region=_REGION, profile=_PROFILE)
                          or _resolve_ak_owner(ak, start_time, end_time))
            if owner_name:
                try:
                    body = _cli.call("ram", "GetAccessKeyLastUsed",
                                     {"UserAccessKeyId": ak, "UserName": owner_name},
                                     region=_REGION, profile=_PROFILE)
                    last_used = body.get("AccessKeyLastUsed") or {}
                    if last_used:
                        result["lastUsedTime"] = last_used.get("LastUsedDate", "N/A")
                        result["lastUsedService"] = last_used.get("ServiceName", "N/A")
                    if result.get("owner") in (None, "N/A"):
                        result["owner"] = owner_name
                except _cli.CliError as e2:
                    print(f"[WARN] GetAccessKeyLastUsed retry failed: {e2} — continuing with degradation", file=sys.stderr)
                    result["basic_error"] = str(e2)
            else:
                result["basic_error"] = str(e)
        else:
            print(f"[WARN] GetAccessKeyLastUsed failed: {e} — continuing with degradation", file=sys.stderr)
            result["basic_error"] = str(e)
    # Best-effort: if the AK belongs to the *calling* user, ListAccessKeys can
    # resolve its real Status/CreateDate. Foreign AKs (other users/accounts) are
    # not resolvable via read-only public API, so they honestly stay "N/A".
    try:
        body = _cli.call("ram", "ListAccessKeys", {}, region=_REGION, profile=_PROFILE)
        aks = (body.get("AccessKeys") or {}).get("AccessKey") or []
        if isinstance(aks, dict):
            aks = [aks]
        for entry in aks:
            if isinstance(entry, dict) and entry.get("AccessKeyId") == ak:
                result["status"] = entry.get("Status", result["status"])
                result["createTime"] = entry.get("CreateDate", result["createTime"])
                break
    except _cli.CliError:
        pass
    return result


# ---------------------------------------------------------------------------
# Step 3: ActionTrail Audit
# ---------------------------------------------------------------------------

def lookup_events(start_time: str, end_time: str,
                  service: str = "", source_ip: str = "", ak: str = "", user: str = "") -> list[dict]:
    """Query ActionTrail LookupEvents via the dual-backend layer with NextToken pagination."""
    params: dict[str, Any] = {"StartTime": start_time, "EndTime": end_time, "MaxResults": 50}
    if source_ip:
        params["LookupAttribute.1.Key"] = "SourceIpAddress"
        params["LookupAttribute.1.Value"] = source_ip
    elif ak:
        params["LookupAttribute.1.Key"] = "EventAccessKeyId"
        params["LookupAttribute.1.Value"] = ak
    elif user:
        params["LookupAttribute.1.Key"] = "User"
        params["LookupAttribute.1.Value"] = user
    elif service:
        params["LookupAttribute.1.Key"] = "ServiceName"
        params["LookupAttribute.1.Value"] = service
    raw = _cli.paginate_next_token(
        "actiontrail", "LookupEvents", params,
        region=_REGION, profile=_PROFILE, items_key="Events",
    )
    return [_event_to_dict(evt) for evt in raw]


def _event_to_dict(evt: Any) -> dict:
    """Normalize an ActionTrail event to a flat dict.
    Events from public LookupEvents are dicts, not SDK objects."""
    if isinstance(evt, dict):
        user_identity = evt.get("userIdentity") or {}
        if not isinstance(user_identity, dict):
            user_identity = {}
        return {
            "eventId": evt.get("eventId", "N/A"),
            "eventName": evt.get("eventName", "Unknown"),
            "eventTime": evt.get("eventTime", "N/A"),
            "eventSource": evt.get("eventSource", ""),
            "sourceIpAddress": evt.get("sourceIpAddress", "N/A"),
            "userAgent": evt.get("userAgent", "N/A"),
            "userIdentity": user_identity,
            "userName": user_identity.get("userName") or "N/A",
            "accessKeyId": evt.get("accessKeyId") or user_identity.get("accessKeyId", "N/A"),
            "requestParameters": evt.get("requestParameters") or {},
            "responseElements": evt.get("responseElements") or {},
            "errorCode": evt.get("errorCode") or "",
            "errorMessage": evt.get("errorMessage") or "",
            "serviceName": evt.get("serviceName", ""),
            "eventRW": evt.get("eventRW", ""),
        }
    # SDK object fallback
    uid = getattr(evt, "user_identity", None) or {}
    if hasattr(uid, "to_map"):
        uid = uid.to_map()
    elif not isinstance(uid, dict):
        uid = {}
    return {
        "eventId": getattr(evt, "event_id", None) or "N/A",
        "eventName": getattr(evt, "event_name", None) or "Unknown",
        "eventTime": getattr(evt, "event_time", None) or "N/A",
        "eventSource": getattr(evt, "event_source", None) or "",
        "sourceIpAddress": getattr(evt, "source_ip_address", None) or "N/A",
        "userAgent": getattr(evt, "user_agent", None) or "N/A",
        "userIdentity": uid,
        "userName": uid.get("userName") or "N/A",
        "accessKeyId": getattr(evt, "access_key_id", None) or "N/A",
        "requestParameters": getattr(evt, "request_parameters", None) or {},
        "responseElements": getattr(evt, "response_elements", None) or {},
        "errorCode": getattr(evt, "error_code", None) or "",
        "errorMessage": getattr(evt, "error_message", None) or "",
    }


def classify_event_risk(event_name: str, service: str) -> str:
    high_risk = HIGH_RISK_EVENTS.get(service, [])
    if any(pattern in event_name for pattern in high_risk):
        return "HIGH"
    if any(kw in event_name for kw in ("Modify", "Update", "Delete", "Remove", "Stop", "Release")):
        return "MEDIUM"
    return "LOW"


def process_events(raw_events: list[dict], service: str) -> list[dict]:
    processed = []
    for evt in raw_events:
        event_name = evt.get("eventName", "Unknown")
        risk = classify_event_risk(event_name, service)
        error_code = evt.get("errorCode", "")
        success = not bool(error_code)
        processed.append({
            "eventId": evt.get("eventId", "N/A"),
            "eventName": event_name,
            "eventTime": evt.get("eventTime", "N/A"),
            "eventSource": evt.get("eventSource", ""),
            "sourceIPAddress": evt.get("sourceIpAddress", "N/A"),
            "userAgent": evt.get("userAgent", "N/A"),
            "userName": evt.get("userName", "N/A"),
            "accessKeyId": evt.get("accessKeyId", "N/A"),
            "requestParameters": evt.get("requestParameters", {}),
            "responseElements": evt.get("responseElements", {}),
            "riskLevel": risk,
            "service": service,
            "success": success,
            "errorCode": error_code,
            "errorMessage": evt.get("errorMessage", ""),
        })
    return processed


def identify_sub_accounts(events: list[dict]) -> list[str]:
    """Identify sub-account names from successful CreateUser events."""
    sub_accounts = set()
    for e in events:
        if e["eventName"] == "CreateUser" and e.get("success", True):
            params = e.get("requestParameters", {})
            user_name = params.get("UserName") or params.get("userName")
            if user_name:
                sub_accounts.add(user_name)
    return sorted(sub_accounts)


def identify_new_aks(events: list[dict]) -> list[dict]:
    """Identify new AccessKeys from successful CreateAccessKey events."""
    new_aks = []
    for e in events:
        if e["eventName"] == "CreateAccessKey" and e.get("success", True):
            resp = e.get("responseElements", {})
            ak_obj = resp.get("AccessKey", resp)
            ak_id = ak_obj.get("AccessKeyId", "")
            params = e.get("requestParameters", {})
            target_user = params.get("UserName") or params.get("userName") or "(root)"
            if ak_id:
                new_aks.append({"ak_id": ak_id, "target_user": target_user,
                               "event_time": e.get("eventTime", "N/A")})
    return new_aks


def trace_ak_chain(account: str, start_time: str, end_time: str,
                   leaked_ak: str, max_depth: int = 5) -> dict[str, Any]:
    """Recursive chain-following: trace leaked AK -> sub-users -> new AKs.

    Implements Steps 2-5 of the 6-step SOP.
    """
    visited_aks: set[str] = set()
    visited_users: set[str] = set()
    seen_event_ids: set[str] = set()
    all_chain_events: list[dict] = []
    chain_log: list[str] = []
    ak_first_seen: dict[str, str] = {}

    def _trace_ak(ak_id: str, depth: int, label: str) -> None:
        if ak_id in visited_aks or depth > max_depth:
            return
        visited_aks.add(ak_id)
        chain_log.append(f"{'  ' * depth}[AK] Tracing {label}: {_cli.mask_sensitive(ak_id)}")
        print(f"[CHAIN] {'  ' * depth}Tracing AK {label}: {_cli.mask_sensitive(ak_id)}", file=sys.stderr)
        try:
            events_raw = lookup_events(start_time, end_time, ak=ak_id)
        except Exception as e:
            chain_log.append(f"{'  ' * depth}  Error: {e}")
            return
        events = process_events(events_raw, f"AK:{_cli.mask_sensitive(ak_id)}")
        for evt in events:
            eid = evt.get("eventId", "")
            if eid and eid not in seen_event_ids:
                seen_event_ids.add(eid)
                all_chain_events.append(evt)
            et = evt.get("eventTime", "")
            if et and et != "N/A":
                if ak_id not in ak_first_seen or et < ak_first_seen[ak_id]:
                    ak_first_seen[ak_id] = et
        chain_log.append(f"{'  ' * depth}  Found {len(events)} events")
        for sub_user in identify_sub_accounts(events):
            _trace_user(sub_user, depth + 1)
        for new_ak in identify_new_aks(events):
            ak_first_seen[new_ak["ak_id"]] = new_ak["event_time"]
            _trace_ak(new_ak["ak_id"], depth + 1, f"created-for-{new_ak['target_user']}")

    def _trace_user(user_name: str, depth: int) -> None:
        if user_name in visited_users or depth > max_depth:
            return
        visited_users.add(user_name)
        chain_log.append(f"{'  ' * depth}[USER] Tracing sub-user: {user_name}")
        print(f"[CHAIN] {'  ' * depth}Tracing User: {user_name}", file=sys.stderr)
        try:
            events_raw = lookup_events(start_time, end_time, user=user_name)
        except Exception as e:
            chain_log.append(f"{'  ' * depth}  Error: {e}")
            return
        events = process_events(events_raw, f"User:{user_name}")
        for evt in events:
            eid = evt.get("eventId", "")
            if eid and eid not in seen_event_ids:
                seen_event_ids.add(eid)
                all_chain_events.append(evt)
        chain_log.append(f"{'  ' * depth}  Found {len(events)} events")
        for new_ak in identify_new_aks(events):
            ak_first_seen[new_ak["ak_id"]] = new_ak["event_time"]
            _trace_ak(new_ak["ak_id"], depth + 1, f"sub-user-{user_name}-created")

    _trace_ak(leaked_ak, 0, "leaked-AK")
    return {
        "chain_events": all_chain_events,
        "visited_aks": sorted(visited_aks),
        "visited_users": sorted(visited_users),
        "chain_log": chain_log,
        "ak_first_seen": ak_first_seen,
    }


# ---------------------------------------------------------------------------
# Step 6: Report Generation
# ---------------------------------------------------------------------------

def generate_recommendations(high_risk_count: int, events_by_service: dict[str, list[dict]]) -> list[dict]:
    recs = []
    if high_risk_count > 0:
        recs.append({"priority": "CRITICAL",
                     "action": "Immediately disable the leaked AK and rotate all credentials.",
                     "owner": "Security Team"})
    if any(events_by_service.get("Ram", [])):
        recs.append({"priority": "HIGH",
                     "action": "Audit all RAM users, roles, and policies created during the incident window.",
                     "owner": "IAM Admin"})
    if any(events_by_service.get("ECS", [])):
        recs.append({"priority": "HIGH",
                     "action": "Inspect all ECS instances created/started. Terminate unauthorized instances.",
                     "owner": "Cloud Ops"})
    if any(events_by_service.get("Alidns", [])):
        recs.append({"priority": "HIGH",
                     "action": "Review DNS record modifications for potential hijacking.",
                     "owner": "Network Team"})
    recs.append({"priority": "MEDIUM",
                 "action": "Enable CloudMonitor alerts and ActionTrail log analysis for continuous monitoring.",
                 "owner": "Security Team"})
    return recs


def build_timeline(events_by_service: dict[str, list[dict]]) -> list[dict]:
    all_events = []
    for evts in events_by_service.values():
        all_events.extend(evts)
    def _sort_key(e):
        ts = e.get("eventTime", "")
        if ts and ts != "N/A":
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.min.replace(tzinfo=timezone.utc)
    return sorted(all_events, key=_sort_key)


def _build_action_details(events_by_service: dict[str, list[dict]]) -> dict[str, list[str]]:
    """Categorize high-risk events by service for description."""
    details: dict[str, list[str]] = {}
    for svc, evts in events_by_service.items():
        svc_details = []
        for e in evts:
            if e["riskLevel"] != "HIGH":
                continue
            time_str = e.get("eventTime", "unknown time")
            ip = e.get("sourceIPAddress", "unknown IP")
            user = e.get("userName", "unknown user")
            en = e["eventName"]
            result_tag = ""
            if not e.get("success", True):
                result_tag = f" **[Failed: {e.get('errorCode', 'FAIL')}]**"
            if en == "CreateUser":
                params = e.get("requestParameters", {})
                uname = params.get("UserName") or params.get("userName") or "unknown"
                svc_details.append(f"Created sub-account {uname} ({time_str}, source IP: {ip}){result_tag}")
            elif en in ("RunInstances", "CreateInstance"):
                svc_details.append(f"Called {en} to create ECS instance ({time_str}, source IP: {ip}){result_tag}")
            elif en == "AttachPolicyToUser":
                svc_details.append(f"Attached permission policy to sub-account ({time_str}, source IP: {ip}){result_tag}")
            elif en == "AddDomainRecord":
                svc_details.append(f"Added DNS record ({time_str}, source IP: {ip}){result_tag}")
            elif en == "SendSms":
                svc_details.append(f"Sent SMS ({time_str}, source IP: {ip}){result_tag}")
            else:
                svc_details.append(f"Called {en} ({time_str}, source IP: {ip}, user: {user}){result_tag}")
        if svc_details:
            details[svc] = svc_details
    return details


def build_conclusion(ak, account_info, timeline, sub_accounts, events_by_service,
                     notification, ban_info, ak_designations) -> dict[str, Any]:
    """Build the English conclusion section following the standard template."""
    abnormal_ips = set()
    for e in timeline:
        ip = e.get("sourceIPAddress", "")
        if ip and ip not in ("N/A", "127.0.0.1", "", "-"):
            abnormal_ips.add(ip)

    # Section I: Event Overview
    owner = account_info.get("owner", "Unknown")
    ak_status = account_info.get("status", "Unknown")
    create_time = account_info.get("createTime", "Unknown")
    ak_type = account_info.get("type", "Unknown")
    ak_label = ak_designations.get(ak, ak)
    alert_detected = "Yes" if notification.get("alert_detected") else "No"
    has_ban = "Yes" if ban_info.get("ak_ban_inferred") else "No"

    total_in_timeline = len(timeline)
    failed_in_timeline = sum(1 for e in timeline if not e.get("success", True))
    all_failed = total_in_timeline > 0 and failed_in_timeline == total_in_timeline
    high_risk_ct = sum(1 for e in timeline if e["riskLevel"] == "HIGH")
    medium_ct = sum(1 for e in timeline if e["riskLevel"] == "MEDIUM")
    # Only STRONG signals justify a "corroborated compromise" verdict + P0 disable.
    # Medium-risk (Modify/Update-type) ops alone are surfaced for review, not as
    # proof of abuse -- otherwise benign Modify/Update calls (or leak-handling
    # operations like ModifyAccessKeyLeakDeal) would be misread as an intrusion.
    strong_findings = bool(
        notification.get("alert_detected")
        or ban_info.get("ak_ban_inferred")
        or high_risk_ct > 0
        or sub_accounts
    )
    has_findings = strong_findings
    observed_codes = sorted({e.get("errorCode") for e in timeline
                             if not e.get("success", True) and e.get("errorCode")})

    exec_status_desc = ""
    if all_failed:
        codes_note = f" (observed error codes: {', '.join(observed_codes)})" if observed_codes else ""
        exec_status_desc = (
            f"\n\n**Important Finding**: All {total_in_timeline} operations in the audit window "
            f"**failed**{codes_note}, indicating the AK was already in a disabled/inactive state "
            f"(disabled either manually by the account owner or automatically by Alibaba Cloud risk "
            f"control -- the audit logs do not attribute which) before these operations. "
            f"**No actual security impact**."
        )
    elif failed_in_timeline > 0:
        success_count = total_in_timeline - failed_in_timeline
        exec_status_desc = (
            f"\n\n**Execution Results**: {success_count} operations succeeded, "
            f"{failed_in_timeline} failed (blocked)."
        )

    if strong_findings:
        lead = (f"AccessKey `{ak_label}` (original ID: `{_cli.mask_sensitive(ak)}`) was reported as "
                f"suspected-leaked; this read-only investigation corroborated it (see findings below).")
    elif medium_ct > 0:
        lead = (f"AccessKey `{ak_label}` (original ID: `{_cli.mask_sensitive(ak)}`) was reported as "
                f"suspected-leaked. This read-only investigation found **no leak alert, no ban "
                f"indication, and no high-risk operations**, but **{medium_ct} medium-risk "
                f"(Modify/Update-type) operation(s)** that warrant review (see findings below).")
    else:
        lead = (f"AccessKey `{ak_label}` (original ID: `{_cli.mask_sensitive(ak)}`) was reported as "
                f"suspected-leaked, but this read-only investigation found **no leak alert, no ban "
                f"indication, and no high/medium-risk operations** in the audit window.")
    owner_str = (f"owner `{owner}`" if owner not in ("Unknown", "N/A")
                 else "an owner that is not retrievable via read-only API")
    status_str = (ak_status if ak_status not in ("Unknown", "N/A")
                  else "unknown (read-only API cannot resolve it for this AK)")
    create_str = create_time if create_time not in ("Unknown", "N/A") else "unknown"
    overview = (
        f"{lead}\n"
        f"This AK belongs to {owner_str}, current status: {status_str}, type: {ak_type}, "
        f"created at {create_str}.\n"
        f"Security Center AK leak alert: {alert_detected}; "
        f"AK ban enforcement (inferred from ActionTrail): {has_ban}."
        f"{exec_status_desc}"
    )

    # Section II: Intrusion Path
    ip_list = sorted(abnormal_ips)
    if ip_list:
        ip_section = (f"Calls originated from {len(ip_list)} distinct source IP address(es); "
                      f"confirm whether these are expected business addresses:\n")
        for ip in ip_list:
            ip_section += f"- `{ip}`\n"
    else:
        ip_section = "No definitive source IP extracted from call logs.\n"

    sorted_events = sorted(
        [e for e in timeline if e["riskLevel"] in ("HIGH", "MEDIUM")],
        key=lambda x: x.get("eventTime", "")
    )
    timeline_lines = []
    for i, e in enumerate(sorted_events[:5], 1):
        ts = e.get("eventTime", "unknown time")
        svc = e["service"]
        en = e["eventName"]
        ip = e.get("sourceIPAddress", "unknown IP")
        timeline_lines.append(f"{i}. {ts}: Called `{svc}:{en}`, source IP `{ip}`")
    if timeline_lines:
        timeline_section = "Key timeline:\n" + "\n".join(timeline_lines)
    else:
        timeline_section = "No high/medium-risk operation events detected."

    # Data-driven only: never assert fabricated "attack characteristics" when the
    # audit shows nothing. A clean AK must read as clean.
    if not ip_list and not sorted_events:
        intrusion_path = ("No anomalous call pattern or high/medium-risk operations were "
                          "identified in the audit window.")
    else:
        intrusion_path = ip_section + "\n" + timeline_section

    # Section III: Harmful Actions
    action_details = _build_action_details(events_by_service)
    high_risk_count = sum(1 for e in timeline if e["riskLevel"] == "HIGH")
    svc_with_events = [s for s, ev in events_by_service.items() if ev]
    harm_section = (
        f"ActionTrail audit shows {len(timeline)} event records for this AK, "
        f"including {high_risk_count} high-risk operations across {len(svc_with_events)} services.\n\n"
    )
    for svc, details in action_details.items():
        harm_section += f"[{svc}]\n"
        for d in details:
            harm_section += f"- {d}\n"
        harm_section += "\n"
    if not action_details:
        harm_section += "No definitive high-risk operation records found.\n"

    # Section IV: Impact Scope
    ecs_count = sum(1 for e in timeline if e["service"] == "ECS" and e["eventName"] in ("RunInstances", "CreateInstance"))
    sg_count = sum(1 for e in timeline if e["service"] == "ECS" and e["eventName"] == "CreateSecurityGroup")
    ram_policy_changes = sum(1 for e in timeline if e["service"] == "Ram" and e["eventName"] in ("AttachPolicyToUser", "AttachPolicyToRole"))
    has_alidns = any(e["service"] == "Alidns" for e in timeline)
    has_dms = any(e["service"] == "Dms" for e in timeline)
    has_sms = any(e["service"] == "SMS" for e in timeline)

    impact = (
        f"| Impact Dimension | Details |\n"
        f"|-----------------|--------|\n"
        f"| Account Security | {len(sub_accounts)} sub-accounts created, {ram_policy_changes} policy changes |\n"
        f"| Resource Security | {ecs_count} ECS instances, {sg_count} security groups created |\n"
        f"| Cost Security | {'Unauthorized instances may incur ongoing cloud costs' if ecs_count > 0 else 'No unauthorized instance creation detected'} |\n"
        f"| Data Security | {'DMS data access detected' if has_dms else 'No data access detected'} |\n"
        f"| DNS Security | {'DNS record changes detected' if has_alidns else 'No DNS record changes detected'} |\n"
        f"| SMS Security | {'SMS sending detected' if has_sms else 'No SMS sending detected'} |\n"
    )

    # Section V: Risk Analysis
    risk_analysis = []
    if any(e["service"] == "Ram" and e["riskLevel"] == "HIGH" for e in timeline):
        risk_analysis.append("1. **Account level**: Leaked AK can create sub-accounts and grant permissions, enabling persistent access;")
    if any(e["service"] == "ECS" and e["riskLevel"] == "HIGH" for e in timeline):
        risk_analysis.append("2. **Resource level**: Anomalous ECS instances created, potentially used for mining, C2, or DDoS;")
        risk_analysis.append("3. **Cost level**: Unauthorized resources incur uncontrolled cloud costs;")
    if has_dms:
        risk_analysis.append("4. **Data level**: DMS/RDS operations detected; data exfiltration risk if sub-accounts have broad permissions;")
    if has_alidns:
        risk_analysis.append("5. **DNS level**: DNS record modifications may cause traffic hijacking or phishing;")
    risk_analysis.append("6. **Compliance level**: AK leak incidents must be reported and handled per internal security incident procedures.")

    if len(risk_analysis) <= 1:
        risk_analysis = [
            "1. **Account level**: Leaked AK can be used to call Alibaba Cloud APIs, posing privilege abuse risk;",
            "2. **Resource level**: Attacker may create or modify cloud resources using this AK;",
            "3. **Compliance level**: AK leak incidents must follow internal security incident procedures.",
        ]

    # Section VI: Remediation Recommendations (P0-P3)
    advice: list[str] = []
    if has_findings:
        p0 = [f"[P0 -- Immediate (within 30 minutes)] Disable and delete leaked AK `{ak_label}` (original ID: `{_cli.mask_sensitive(ak)}`);"]
        if sub_accounts:
            p0.append(f"[P0] Delete attacker-created sub-accounts ({', '.join(sub_accounts)}) and all their AKs and policies;")
        if ecs_count > 0:
            p0.append(f"[P0] Terminate {ecs_count} attacker-created ECS instances and associated EIPs/security groups;")
        advice.extend(p0)
    else:
        advice.append(
            "[Precaution] No confirmed compromise (no leak alert, ban, high-risk operation, or "
            "attacker-created sub-account) was found in this account's audit window. If you have "
            "external evidence of exposure (e.g., the AK appeared in a public repo), rotate it as a "
            "precaution; otherwise continue routine monitoring."
        )
        if medium_ct:
            advice.append(
                f"[Review] {medium_ct} medium-risk (Modify/Update-type) operation(s) were observed -- "
                f"confirm they are expected/authorized business activity before closing."
            )

    p1 = ["[P1 -- Urgent (within 2 hours)] Rotate all existing AccessKeys on this account;"]
    if has_alidns:
        p1.append("[P1] Restore deleted/modified DNS records and verify against known baseline;")
    p1.append("[P1] Enforce least-privilege principle for RAM permissions, remove unnecessary AdministratorAccess;")
    advice.extend(p1)

    p2 = [
        "[P2 -- Important (within 24 hours)] Investigate AK leak source (code repos, CI/CD configs, third-party platforms);",
        "[P2] Enable MFA enforcement for all RAM users;",
        "[P2] If leaked AK belongs to root account, migrate to RAM user AK and delete root AK;",
        "[P2] Separate human users from program users: console users vs API users;",
        "[P2] Strengthen password policy (12+ chars, 3+ char types, 90-day expiration);",
    ]
    advice.extend(p2)

    p3 = [
        "[P3 -- Long-term (within 1 week)] Migrate to credential-free architecture (ECS Instance Role / RRSA / KMS Secrets Manager);",
        "[P3] Clean up idle AKs (unused 90 days -> disable -> observe -> delete) and idle RAM users;",
        "[P3] Ensure each RAM user has only 1 active AK;",
        "[P3] Enable ActionTrail real-time delivery to SLS + CloudMonitor alerts (Ram/DNS/CloudSSO operations);",
        "[P3] Enable RAM Cloud Governance with all 14+ detection items;",
        "[P3] Implement enterprise SSO integration to eliminate password-based login.",
    ]
    advice.extend(p3)

    return {
        "overview": overview,
        "intrusion_path": intrusion_path,
        "harm_details": harm_section,
        "impact": impact,
        "risk_analysis": risk_analysis,
        "advice": advice,
        "abnormal_ips": ip_list,
        "sub_accounts_created": sub_accounts,
    }


def build_readonly_header() -> list:
    """Always-on banner placed at the very top of every report (leak confirmed or
    not). It states plainly that this skill performed NO write operations and that
    every remediation step must be executed manually by the operator -- so the
    output is never misread as "the skill already disabled / handled the AK".
    """
    return [
        "> # 🔒 READ-ONLY SKILL — NO CHANGES WERE MADE",
        "> ",
        "> This investigation performed **only read-only** Alibaba Cloud API calls "
        "(`Describe*` / `Lookup*` / `Get*` / `List*`). It did **NOT** disable, rotate, "
        "modify, delete, or mark-as-handled any AccessKey, RAM user, or other resource, "
        "and it did **NOT** flag any Security Center leak record as processed.",
        "> ",
        "> **Any remediation described below must be performed manually by you** via the "
        "RAM Console / CLI. This skill will not do it for you.",
        "",
    ]


def build_urgent_banner(neutralized: bool = False) -> list:
    """Prominent remediation warning placed at the very top of the report when the
    target AccessKey is confirmed/likely leaked.

    This skill is READ-ONLY: it never disables, modifies, or deletes any
    credential. The banner instructs the operator to act manually, and always
    spells out the full four-step workflow (disable → create replacement →
    migrate & verify → delete) -- never partial guidance.

    When ``neutralized`` is True (AK already disabled and every audited operation
    failed), a calmer variant is used -- there is no ongoing abuse to stop.
    """
    if neutralized:
        return [
            "> # ℹ️ LEAKED ACCESSKEY — ALREADY DISABLED, NO SUCCESSFUL ABUSE OBSERVED",
            "> ",
            "> The target AccessKey was leaked but appears **already disabled** -- every audited "
            "operation failed and **no successful abuse was observed**. There is no ongoing abuse to "
            "stop, but the credential is still compromised. Complete the full remediation workflow:",
            "> ",
            "> 1. **DISABLE** — already disabled; confirm its status is **Inactive** in the RAM Console.",
            "> 2. **CREATE a replacement AccessKey** for the owning RAM user.",
            "> 3. **MIGRATE & VERIFY** — roll the new AccessKey out to every app / service / pipeline that "
            "used the leaked one, then verify there is no service disruption.",
            "> 4. **DELETE the old (disabled) AccessKey** once you have verified nothing depends on it.",
            "> ",
            "> Also **INVESTIGATE the leak source** (code repos, CI/CD configs, third-party platforms) to prevent recurrence.",
            "> ",
            "> ⚠️ This skill is **read-only** — it will not modify or delete any credential for you.",
            "",
        ]
    return [
        "> # 🚨 URGENT — LEAKED ACCESSKEY DETECTED, IMMEDIATE ACTION REQUIRED",
        "> ",
        "> The target AccessKey is compromised. Perform the **full four-step remediation "
        "workflow NOW, in this exact order**, to stop ongoing abuse (do NOT stop after disabling):",
        "> ",
        "> 1. **DISABLE the leaked AccessKey immediately.** RAM Console → AccessKey Management → set it to "
        "**Inactive** (or run `aliyun ram update-access-key --user-access-key-id <AK> --status Inactive` yourself). "
        "This blocks all further API calls made with it.",
        "> 2. **CREATE a replacement AccessKey** for the owning RAM user.",
        "> 3. **MIGRATE & VERIFY** — roll the new AccessKey out to every application / service / pipeline that "
        "used the leaked one, then verify there is no service disruption.",
        "> 4. **DELETE the old AccessKey** once replacement is verified. **Never delete before replacing.**",
        "> ",
        "> ⚠️ This skill is **read-only** — it will not disable, modify, or delete any credential for you. You must perform the steps above via the RAM Console / CLI.",
        "",
    ]


def build_cross_account_banner(warning: dict) -> list:
    """Prominent banner shown when --account differs from the credential's own
    account UID. The investigation is scoped to the credential's account, so a
    mismatch means empty results cannot be trusted as "no leak"."""
    prov = _cli.mask_sensitive(warning.get("provided_account", ""))
    cred = _cli.mask_sensitive(warning.get("credential_account", ""))
    return [
        "> # \u26a0\ufe0f ACCOUNT MISMATCH \u2014 CROSS-ACCOUNT INVESTIGATION NOT SUPPORTED",
        "> ",
        f"> You asked about account `{prov}`, but the active credential belongs to `{cred}`.",
        "> ",
        "> Security Center leak records, ActionTrail events, and RAM AccessKey info are all "
        "**account-scoped**; the AccessKey ID does not carry its owner account, and there is no "
        "AssumeRole-by-AK mechanism.",
        "> ",
        f"> **The findings below reflect ONLY account `{cred}`. Empty / clean results do NOT prove "
        "the target AccessKey is safe** -- they may simply mean the AK lives in a different account.",
        "> ",
        f"> To investigate an AccessKey in account `{prov}`, re-run this skill authenticated as that "
        "account (`--profile <that-account>` or its env AK/SK).",
        "",
    ]


def generate_report(ak, account, notification, ban_info, account_info,
                    events_by_service, sub_accounts, start_time, end_time,
                    fmt, ak_designations, cross_account_warning=None) -> str:
    timeline = build_timeline(events_by_service)
    conclusion = build_conclusion(ak, account_info, timeline, sub_accounts,
                                  events_by_service, notification, ban_info, ak_designations)
    high_risk_count = sum(1 for e in timeline if e["riskLevel"] == "HIGH")
    medium_risk_count = sum(1 for e in timeline if e["riskLevel"] == "MEDIUM")
    failed_count = sum(1 for e in timeline if not e.get("success", True))
    total_events = len(timeline)
    recommendations = generate_recommendations(high_risk_count, events_by_service)
    leak_confirmed = bool(
        notification.get("alert_detected")
        or ban_info.get("ak_ban_inferred")
        or high_risk_count > 0
    )
    successful_events = total_events - failed_count
    # "Already disabled, every audited op failed" means there is no ongoing abuse
    # to stop -- this must take precedence over a mere leak alert (which only
    # confirms the leak, not active exploitation).
    neutralized = bool(
        ban_info.get("ak_ban_inferred") and total_events > 0 and failed_count == total_events
    )
    active_abuse = bool(
        (high_risk_count > 0 and successful_events > 0)
        or (notification.get("alert_detected") and not neutralized)
    )

    report = {
        "metadata": {
            "investigationTime": datetime.now(timezone.utc).isoformat(),
            "ak": ak, "account": account,
            "timeWindow": {"start": start_time, "end": end_time},
            "servicesScanned": list(events_by_service.keys()),
            "urgentRemediationRequired": leak_confirmed,
            "readOnly": True,
            "readOnlyNotice": (
                "This skill is READ-ONLY. It performed no write operations: it did not "
                "disable, rotate, modify, delete, or mark-as-handled any AccessKey / RAM "
                "user / resource, and did not flag any Security Center leak record as "
                "processed. All remediation (disable -> create replacement -> migrate & "
                "verify -> delete) must be performed manually by the operator."
            ),
            "crossAccountWarning": cross_account_warning,
        },
        "step1_notification": notification,
        "step1_ban_inference": ban_info,
        "step2_ak_info": account_info,
        "step3_actiontrail": {"subAccountsIdentified": sub_accounts, "eventsByService": events_by_service},
        "step4_timeline": {
            "timeline": timeline, "conclusion": conclusion,
            "summary": {
                "totalEvents": total_events, "highRiskEvents": high_risk_count,
                "mediumRiskEvents": medium_risk_count, "failedEvents": failed_count,
                "servicesWithEvents": [s for s, ev in events_by_service.items() if ev],
            },
            "recommendations": recommendations,
        },
    }

    if fmt == "json":
        return _cli.mask_text(
            json.dumps(_cli.mask_obj(report), indent=2, ensure_ascii=False),
            extra=[account],
        )

    ak_label = ak_designations.get(ak, ak)
    md = [
        "# AK Leak Incident Response Report",
        "",
        f"**Investigation Time:** {report['metadata']['investigationTime']}",
        f"**Target AK:** `{ak_label}` (original ID: `{_cli.mask_sensitive(ak)}`)",
        f"**Target Account:** `{_cli.mask_sensitive(account)}`",
        f"**Time Window:** {start_time} ~ {end_time}",
        "",
    ]
    if cross_account_warning:
        md += build_cross_account_banner(cross_account_warning)
    # Always-on read-only banner (leak confirmed or not) so the output is never
    # misread as "the skill already disabled / handled the AK".
    md += build_readonly_header()
    if neutralized:
        md += build_urgent_banner(neutralized=True)
    elif active_abuse:
        md += build_urgent_banner()
    elif high_risk_count > 0:
        md += build_urgent_banner()
    md += [
        "---",
        "",
        "## Step 1: Notification Verification",
        "",
    ]

    # Notification
    if notification.get("alert_detected"):
        md.append("- [x] AK leak alert **DETECTED** via Security Center.")
        if notification.get("aks_found_in_alert"):
            md.append(f"- AKs in alert: `{', '.join(_cli.mask_sensitive(a) for a in notification['aks_found_in_alert'])}`")
    else:
        md.append("- [ ] No AK leak alert found via Security Center.")
    md.append("")
    if ban_info.get("ak_ban_inferred"):
        md.append("- [x] AK ban **INFERRED** from ActionTrail error codes.")
        md.append(f"- Ban error codes: `{', '.join(ban_info.get('ban_error_codes', []))}`")
    else:
        md.append("- [ ] No AK ban inferred from ActionTrail.")
    md.append("")

    # AK Info
    md.extend(["## Step 2: AK Information Query", "", "| Field | Value |", "|-------|-------|"])
    for k, v in [("accessKeyId", _cli.mask_sensitive(account_info.get("accessKeyId", "N/A"))),
                 ("status", account_info.get("status", "N/A")),
                 ("createTime", account_info.get("createTime", "N/A")),
                 ("owner", account_info.get("owner", "N/A")),
                 ("type", account_info.get("type", "N/A"))]:
        md.append(f"| {k} | {v} |")
    md.append("")

    # ActionTrail
    md.extend(["## Step 3: ActionTrail Dangerous Operation Audit", ""])
    if sub_accounts:
        md.append(f"**Sub-accounts created by leaked AK:** `{', '.join(sub_accounts)}`")
    else:
        md.append("**No sub-accounts created by leaked AK detected.**")
    md.extend(["", "### Event Summary", "", "| Metric | Value |", "|--------|-------|",
               f"| Total Events | {total_events} |",
               f"| High Risk Events | {high_risk_count} |",
               f"| Medium Risk Events | {medium_risk_count} |",
               f"| Failed Events | {failed_count} |",
               f"| Successful Events | {total_events - failed_count} |", ""])

    # Per-service
    md.extend(["### Dangerous Operations by Service", ""])
    for svc, evts in events_by_service.items():
        if not evts:
            continue
        md.extend([f"#### {svc}", "",
                   "| EventTime | EventName | Risk | SourceIP | User | Result |",
                   "|-----------|-----------|------|----------|------|--------|"])
        for e in evts:
            user = e.get("userName", "N/A")
            result = "OK" if e.get("success", True) else f"FAIL: {e.get('errorCode', 'FAIL')}"
            md.append(f"| {e['eventTime']} | {e['eventName']} | {e['riskLevel']} | {e['sourceIPAddress']} | {user} | {result} |")
        md.append("")

    # Timeline
    md.extend(["## Step 4: Operational Timeline", "",
               "| EventTime (UTC) | Service | EventName | Risk | SourceIP | User | Result |",
               "|-----------------|---------|-----------|------|----------|------|--------|"])
    for e in timeline:
        user = e.get("userName", "N/A")
        result = "OK" if e.get("success", True) else f"FAIL: {e.get('errorCode', 'FAIL')}"
        md.append(f"| {e['eventTime']} | {e['service']} | {e['eventName']} | {e['riskLevel']} | {e['sourceIPAddress']} | {user} | {result} |")
    md.append("")

    # Conclusion (English, 6 sections)
    md.extend(["### Conclusion", "",
               "#### I. Event Overview", "", conclusion["overview"], "",
               "#### II. Intrusion Path and Anomaly Characteristics", "", conclusion["intrusion_path"], "",
               "#### III. Harmful Action Details", "", conclusion["harm_details"], "",
               "#### IV. Impact Scope", "", conclusion["impact"], "",
               "#### V. Risk Analysis", ""])
    for r in conclusion["risk_analysis"]:
        md.append(f"- {r}")
    md.extend(["", "#### VI. Remediation Recommendations (by Priority)", ""])
    for a in conclusion["advice"]:
        md.append(f"- {a}")
    md.extend(["", "### Recommendations", "", "| Priority | Action | Owner |", "|----------|--------|-------|"])
    for rec in recommendations:
        md.append(f"| {rec['priority']} | {rec['action']} | {rec.get('owner', 'TBD')} |")
    md.extend(["", "---", "", "## Reference Documents", "",
               "- [AccessKey Restrictive Protection](https://www.alibabacloud.com/help/en/ram/user-guide/accesskey-restrictive-protection-description)",
               "- [AccessKey Leakage Solution](https://www.alibabacloud.com/help/en/ram/user-guide/solution-to-accesskey-leakage)",
               ""])
    return _cli.mask_text("\n".join(md), extra=[account])


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    _cli.check_cli_available()
    # Emit the observability session-id once at startup (stderr, so JSON stdout
    # stays clean). Every CLI/HTTP call in this run carries the matching
    # User-Agent: AlibabaCloud-Agent-Skills/<skill>/<session-id>.
    print(f"[INFO] Session ID: {_cli.session_id()} | User-Agent: {_cli.user_agent()}",
          file=sys.stderr)
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Region / profile drive all CLI calls (set module globals)
    global _REGION, _PROFILE
    _REGION = args.region
    _PROFILE = args.profile

    # Always derive the credential's own account UID (read-only STS) so we can
    # auto-fill --account AND detect cross-account misuse (a foreign --ak/--account
    # would silently return empty results and be misread as "no leak").
    credential_uid = _cli.resolve_account_id(_REGION, _PROFILE)
    cross_account_warning = None
    if not args.account:
        if credential_uid:
            args.account = credential_uid
            print(f"[INFO] UID auto-derived from credential: {_cli.mask_sensitive(args.account)}")
        else:
            args.account = "N/A"
            print("[WARN] Could not auto-derive UID (credential lacks STS access); continuing.")
    elif credential_uid and args.account != credential_uid:
        cross_account_warning = {
            "provided_account": args.account,
            "credential_account": credential_uid,
        }
        print(
            f"[WARN] Account mismatch: --account={_cli.mask_sensitive(args.account)} but the active "
            f"credential belongs to {_cli.mask_sensitive(credential_uid)}. This skill can only "
            f"investigate AccessKeys inside the credential's account ({_cli.mask_sensitive(credential_uid)}); "
            f"cross-account investigation is NOT supported. The findings reflect ONLY "
            f"{_cli.mask_sensitive(credential_uid)} -- empty results do NOT prove the AK is safe. "
            f"Re-run with --profile / credentials for the target account.",
            file=sys.stderr,
        )

    days = min(max(args.days, 1), 90)
    start_time, end_time = _cli.get_time_window(days)
    services = [s.strip() for s in args.services.split(",") if s.strip()]

    print(f"[INFO] Investigating AK: {_cli.mask_sensitive(args.ak)}")
    print(f"[INFO] Account: {_cli.mask_sensitive(args.account)}")
    print(f"[INFO] Time window: {start_time} ~ {end_time}")
    print(f"[INFO] Services to audit: {services}")
    print("")

    # Step 1: Notification Verification
    print("[STEP 1] Querying Security Center for AK leak alerts...")
    notification = query_ak_leak_detection(args.ak, args.days)
    if notification.get("alert_detected"):
        print(f"[STEP 1] Alert detected! AKs: {[_cli.mask_sensitive(a) for a in notification.get('aks_found_in_alert', [])]}")
    else:
        print("[STEP 1] No alert found. Proceeding with user-provided AK.")

    print("[STEP 1] Inferring AK ban status from ActionTrail...")
    ban_info = infer_ban_from_actiontrail(args.ak, start_time, end_time)
    if ban_info.get("ak_ban_inferred"):
        print(f"[STEP 1] AK ban inferred: error codes = {ban_info.get('ban_error_codes', [])}")
    else:
        print("[STEP 1] No AK ban inferred.")
    print("")

    # Step 2: AK Info Query
    print("[STEP 2] Querying AK info via RAM API...")
    account_info = query_ak_info(args.ak, start_time, end_time)
    print(f"[STEP 2] AK status: {account_info.get('status', 'N/A')}")
    print(f"[STEP 2] AK owner: {account_info.get('owner', 'N/A')}")
    print("")

    # Step 3: ActionTrail Audit - Phase A: Ram for sub-accounts
    print("[STEP 3] Phase A: Querying Ram for sub-accounts created by leaked AK...")
    try:
        ram_events_raw = lookup_events(start_time, end_time, service="Ram")
        ram_events = process_events(ram_events_raw, "Ram")
    except Exception as e:
        print(f"[STEP 3] Ram query failed: {e}", file=sys.stderr)
        ram_events = []
    sub_accounts = identify_sub_accounts(ram_events)
    if sub_accounts:
        print(f"[STEP 3] Sub-accounts identified: {sub_accounts}")
    else:
        print("[STEP 3] No sub-accounts created by leaked AK detected.")
    print("")

    # Step 3: Phase B: AK-centric cross-product query
    print("[STEP 3] Phase B: Auditing dangerous operations via AK filter...")
    try:
        ak_events_raw = lookup_events(start_time, end_time, ak=args.ak)
        ak_events = ak_events_raw
    except Exception as e:
        print(f"[WARN] AK-filter query failed: {e}; falling back to ALL query.", file=sys.stderr)
        ak_events = []

    # Merge Ram events
    combined_events = ak_events[:]
    ak_event_ids = {e.get("eventId") for e in ak_events}
    for e in ram_events:
        if e.get("eventId") not in ak_event_ids:
            combined_events.append(e)

    events_by_service: dict[str, list[dict]] = {}
    for svc in services:
        prefix = next((p for p, s in SERVICE_SOURCE_PREFIXES.items() if s == svc), svc.lower())
        svc_events = [e for e in combined_events if e.get("eventSource", "").lower().startswith(prefix)]
        processed = process_events(svc_events, svc)
        events_by_service[svc] = processed
        print(f"[STEP 3] {svc}: {len(processed)} events found.")
    print("")

    # Steps 4-5: Chain-following
    print("[STEP 4-5] Running chain-following trace (AK -> sub-users -> new AKs)...")
    chain_result = trace_ak_chain(args.account, start_time, end_time, args.ak)
    chain_events = chain_result["chain_events"]
    chain_users = chain_result["visited_users"]
    chain_aks = chain_result["visited_aks"]

    for u in chain_users:
        if u not in sub_accounts:
            sub_accounts.append(u)
    sub_accounts.sort()

    if chain_events:
        events_by_service["ChainTrace"] = chain_events

    print(f"[STEP 4-5] Chain trace complete: {len(chain_aks)} AKs, "
          f"{len(chain_users)} users, {len(chain_events)} events discovered.")
    for line in chain_result["chain_log"]:
        print(f"  {line}", file=sys.stderr)
    print("")

    # Build AK designation map (AK-A, AK-B, ...)
    ak_creation_times: dict[str, str] = {}
    leaked_ct = account_info.get("createTime", "")
    if leaked_ct and leaked_ct != "N/A":
        ak_creation_times[args.ak] = leaked_ct
    else:
        ak_creation_times[args.ak] = chain_result.get("ak_first_seen", {}).get(args.ak, "9999-12-31T23:59:59Z")
    for ak_id, first_seen in chain_result.get("ak_first_seen", {}).items():
        if ak_id not in ak_creation_times:
            ak_creation_times[ak_id] = first_seen
    sorted_aks = sorted(ak_creation_times.items(), key=lambda x: x[1])
    ak_designations: dict[str, str] = {}
    for idx, (ak_id, _) in enumerate(sorted_aks):
        ak_designations[ak_id] = f"AK-{chr(ord('A') + idx)}"
    print(f"[STEP 6] AK designations: { {_cli.mask_sensitive(k): v for k, v in ak_designations.items()} }")

    # Step 6: Generate Report
    print(f"[STEP 6] Generating report in {args.format} format...")
    report_content = generate_report(
        ak=args.ak, account=args.account,
        notification=notification, ban_info=ban_info,
        account_info=account_info, events_by_service=events_by_service,
        sub_accounts=sub_accounts, start_time=start_time, end_time=end_time,
        fmt=args.format, ak_designations=ak_designations,
        cross_account_warning=cross_account_warning,
    )

    # Output directory is ensured at the start of main() (os.makedirs).
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"[INFO] Report saved to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
