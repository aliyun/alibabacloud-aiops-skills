#!/usr/bin/env bash
# vpc-fw-lifecycle.sh - Assessment, pre-check, creation, update and (disabled)
# deletion guidance for the Cloud Firewall VPC boundary firewall that protects
# traffic between two VPCs connected by Express Connect / VPC peering.
# Part of alibabacloud-cfw-vpc-peering-firewall-protect skill
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin and Vpc plugin
#   - python3 (route auto-discovery + JSON assembly)
#
# Subcommands:
#   assess   - Read-only: inventory protectable peering pairs; with
#              --local-vpc-id + --peer-vpc-id also a pre-check + creation plan
#   precheck - Local validation of one VPC pair (region/auth/route/mask checks)
#   create   - Create a VPC boundary firewall (CreateVpcFirewallConfigure)
#   update   - Rename / adjust protected CIDRs (ModifyVpcFirewallConfigure, auto-verified)
#   delete   - DISABLED: never deletes. Prints close-vs-release guidance + a
#              read-only impact report

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Next-hop types that represent a cross-VPC peering route (the traffic a VPC
# boundary firewall diverts). VpcPeer = VPC peering connection, RouterInterface
# = Express Connect router interface.
readonly PEERING_NEXT_HOP_TYPES="VpcPeer RouterInterface"

# --- Main Help ---
show_main_help() {
  cat >&2 <<'EOF'
vpc-fw-lifecycle.sh - Assessment / pre-check / create / update for the Cloud
                      Firewall VPC boundary firewall (Express Connect / peering)

USAGE:
  vpc-fw-lifecycle.sh <subcommand> [options]

SUBCOMMANDS:
  assess    Read-only inventory of protectable peering pairs; with
            --local-vpc-id + --peer-vpc-id also a server pre-check + creation plan
  precheck  Local validation of one VPC pair before creation
  create    Create a VPC boundary firewall (switch defaults to close)
  update    Rename / adjust the protected route (CIDR) tables, auto-verified
  delete    DISABLED - prints close-vs-release guidance and a read-only report

GLOBAL OPTIONS:
  --dry-run   Preview CLI command without executing
  --help, -h  Show help for the subcommand

EXAMPLES:
  vpc-fw-lifecycle.sh assess --region cn-hangzhou
  vpc-fw-lifecycle.sh assess --local-vpc-id vpc-aaa --local-region cn-hangzhou \
      --peer-vpc-id vpc-bbb --peer-region cn-hangzhou
  vpc-fw-lifecycle.sh precheck --local-vpc-id vpc-aaa --local-region cn-hangzhou \
      --peer-vpc-id vpc-bbb --peer-region cn-hangzhou
  vpc-fw-lifecycle.sh create --local-vpc-id vpc-aaa --local-region cn-hangzhou \
      --peer-vpc-id vpc-bbb --peer-region cn-hangzhou \
      --vpc-firewall-name vpc-fw-prod --firewall-switch close --yes
  vpc-fw-lifecycle.sh update --vpc-firewall-id vfw-xxxx --vpc-firewall-name new-name

EXIT CODES:
  0  Success
  1  Parameter validation error
  2  API call failed / verification failed / blocked by pre-check
EOF
  exit 0
}

# --- Pure JSON filters (unit-testable; no API calls) ---

# Read JSON-lines of {"rt": <route-table-id>, "entries": [<route entries>]} from
# stdin and emit {"cidr_table_list": [...], "masked32": [...], "ipv6_or_cloud": [...]}
# keeping only entries whose next hop is a peering/Express-Connect interface.
filter_peering_routes() {
  python3 -c '
import sys, json
PEER = {"VpcPeer", "RouterInterface"}
out, masked32, skipped = [], [], []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    o = json.loads(line)
    rt = o.get("rt", "")
    rel = []
    for e in o.get("entries", []):
        cidr = e.get("DestinationCidrBlock", "") or ""
        for h in (e.get("NextHops", {}).get("NextHop", []) or []):
            if h.get("NextHopType") in PEER:
                rel.append({"DestinationCidr": cidr,
                            "NextHopInstanceId": h.get("NextHopId", "")})
                if cidr.endswith("/32"):
                    masked32.append(cidr)
                if cidr.startswith("100.64.") or ":" in cidr:
                    skipped.append(cidr)
                break
    if rel:
        out.append({"RouteTableId": rt, "RouteEntryList": rel})
print(json.dumps({"cidr_table_list": out,
                  "masked32": sorted(set(masked32)),
                  "ipv6_or_cloud": sorted(set(skipped))}))
'
}

# Read a DescribeVpcFirewallDetail JSON from stdin and emit the two CIDR table
# lists (LocalVpcCidrTableList / PeerVpcCidrTableList) in the shape
# ModifyVpcFirewallConfigure expects, plus the current name.
extract_cidr_tables_from_detail() {
  python3 -c '
import sys, json
d = json.load(sys.stdin)
def side(key):
    v = d.get(key, {}) or {}
    out = []
    for t in (v.get("VpcCidrTableList", []) or []):
        rel = []
        for e in (t.get("RouteEntryList", []) or []):
            rel.append({"DestinationCidr": e.get("DestinationCidr", ""),
                        "NextHopInstanceId": e.get("NextHopInstanceId", "")})
        if rel:
            out.append({"RouteTableId": t.get("RouteTableId", ""), "RouteEntryList": rel})
    return out
print(json.dumps({"vpc_firewall_name": d.get("VpcFirewallName", ""),
                  "local": side("LocalVpc"),
                  "peer": side("PeerVpc")}))
'
}

# Read a DescribeVpcFirewallList JSON from stdin and emit an inventory summary:
# configured firewalls, protectable (notconfigured) pairs, and per-item blockers.
summarize_firewall_list() {
  python3 -c '
import sys, json
d = json.load(sys.stdin)
items = d.get("VpcFirewalls", []) or []
configured, protectable = [], []
for it in items:
    row = {
        "vpc_firewall_id": it.get("VpcFirewallId", ""),
        "vpc_firewall_name": it.get("VpcFirewallName", ""),
        "firewall_switch_status": it.get("FirewallSwitchStatus", ""),
        "connect_subtype": it.get("ConnectSubType", ""),
        "region_status": it.get("RegionStatus", ""),
        "result_code": it.get("ResultCode", ""),
        "local_vpc": (it.get("LocalVpc", {}) or {}).get("VpcId", ""),
        "local_vpc_name": (it.get("LocalVpc", {}) or {}).get("VpcName", ""),
        "peer_vpc": (it.get("PeerVpc", {}) or {}).get("VpcId", ""),
        "peer_vpc_name": (it.get("PeerVpc", {}) or {}).get("VpcName", ""),
    }
    st = it.get("FirewallSwitchStatus", "")
    # `configuring` is an undocumented transitional status seen for a minute or two
    # after CreateVpcFirewallConfigure returns. The firewall exists at that point,
    # so it belongs in `configured` - listing it as protectable would invite a
    # second create for a pair that is already being provisioned.
    if st in ("opened", "closed", "configured", "configuring"):
        configured.append(row)
    else:
        blockers = []
        if it.get("ResultCode") == "Unauthorized":
            blockers.append("one or both VPCs are not authorized to Cloud Firewall")
        if it.get("ResultCode") == "RegionDisable":
            blockers.append("region does not support VPC boundary firewall")
        if it.get("RegionStatus") == "disable":
            blockers.append("region is not open for VPC boundary firewall")
        row["blockers"] = blockers
        protectable.append(row)
print(json.dumps({"total": d.get("TotalCount", len(items)),
                  "configured": configured,
                  "protectable": protectable}))
'
}

# --- Route auto-discovery (VPC read APIs) ---

# Discover the peering route entries of one VPC and print the filter result
# JSON ({cidr_table_list, masked32, ipv6_or_cloud}). Prints DISCOVER_FAILED and
# returns 1 when the VPC read permission is missing / the API fails, so callers
# can degrade to requiring explicit --*-cidr-json.
discover_peering_cidr_tables() {
  local region="$1" vpc_id="$2"
  local rt_resp rt_ids rt agg=""
  rt_resp=$(call_vpc_api "DescribeRouteTableList" --RegionId "$region" --VpcId "$vpc_id" --PageSize 50 2>/dev/null) || { printf 'DISCOVER_FAILED'; return 1; }
  rt_ids=$(printf '%s' "$rt_resp" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for t in d.get("RouterTableList", {}).get("RouterTableListType", []) or []:
    rid = t.get("RouteTableId", "")
    if rid:
        print(rid)
' 2>/dev/null) || rt_ids=""
  if [[ -z "$rt_ids" ]]; then
    printf 'DISCOVER_FAILED'
    return 1
  fi
  while IFS= read -r rt; do
    [[ -z "$rt" ]] && continue
    local entry_resp entries_json row
    entry_resp=$(call_vpc_api "DescribeRouteEntryList" --RegionId "$region" --RouteTableId "$rt" --MaxResult 500 2>/dev/null) || entry_resp='{}'
    entries_json=$(printf '%s' "$entry_resp" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(json.dumps(d.get("RouteEntrys", {}).get("RouteEntry", []) or []))
except Exception:
    print("[]")
' 2>/dev/null) || entries_json='[]'
    row=$(python3 -c 'import json,sys; print(json.dumps({"rt": sys.argv[1], "entries": json.loads(sys.argv[2])}))' "$rt" "$entries_json")
    agg="${agg}${row}"$'\n'
  done <<< "$rt_ids"
  printf '%s' "$agg" | filter_peering_routes
}

# --- Subcommand: assess ---
cmd_assess() {
  local REGION="" LOCAL_VPC_ID="" LOCAL_REGION="" PEER_VPC_ID="" PEER_REGION=""
  local MEMBER_UID="" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --region) arg_value "--region" "${@:2}"; REGION="$2"; shift 2 ;;
      --local-vpc-id) arg_value "--local-vpc-id" "${@:2}"; LOCAL_VPC_ID="$2"; shift 2 ;;
      --local-region) arg_value "--local-region" "${@:2}"; LOCAL_REGION="$2"; shift 2 ;;
      --peer-vpc-id) arg_value "--peer-vpc-id" "${@:2}"; PEER_VPC_ID="$2"; shift 2 ;;
      --peer-region) arg_value "--peer-region" "${@:2}"; PEER_REGION="$2"; shift 2 ;;
      --member-uid) arg_value "--member-uid" "${@:2}"; MEMBER_UID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "vpc-fw-lifecycle.sh assess" \
          "Read-only assessment: inventory protectable peering pairs, or a single-pair creation plan" \
          "vpc-fw-lifecycle.sh assess [--region <id>] | [--local-vpc-id <id> --local-region <id> --peer-vpc-id <id> --peer-region <id>]" \
          "  --region <id>          Inventory mode: list configured + protectable pairs
  --local-vpc-id <id>    Plan mode: local VPC of the peering pair
  --local-region <id>    Plan mode: local VPC region
  --peer-vpc-id <id>     Plan mode: peer VPC of the peering pair
  --peer-region <id>     Plan mode: peer VPC region
  --member-uid <uid>     Operate under a member account
  --dry-run              Preview CLI command

  Plan mode adds the server pre-check + route auto-discovery and prints a
  ready-to-run 'create' command. Purely read-only; missing VPC read
  permissions degrade route discovery to a note."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  [[ -n "$REGION" ]] && validate_region "$REGION"
  [[ -n "$LOCAL_VPC_ID" ]] && validate_vpc_id "$LOCAL_VPC_ID"
  [[ -n "$PEER_VPC_ID" ]] && validate_vpc_id "$PEER_VPC_ID"
  [[ -n "$LOCAL_REGION" ]] && validate_region "$LOCAL_REGION"
  [[ -n "$PEER_REGION" ]] && validate_region "$PEER_REGION"
  [[ -n "$MEMBER_UID" ]] && validate_member_uid "$MEMBER_UID"

  # Plan mode requires the full pair identity.
  if [[ -n "$LOCAL_VPC_ID" || -n "$PEER_VPC_ID" ]]; then
    for req in "local-vpc-id:$LOCAL_VPC_ID" "local-region:$LOCAL_REGION" "peer-vpc-id:$PEER_VPC_ID" "peer-region:$PEER_REGION"; do
      validate_required "${req%%:*}" "${req#*:}" || exit 1
    done
    assess_plan "$LOCAL_VPC_ID" "$LOCAL_REGION" "$PEER_VPC_ID" "$PEER_REGION" "$MEMBER_UID"
    return 0
  fi

  # Inventory mode.
  local CLI_ARGS=(--CurrentPage 1 --PageSize 50 --Lang zh)
  [[ -n "$REGION" ]] && CLI_ARGS+=(--RegionNo "$REGION")
  [[ -n "$MEMBER_UID" ]] && CLI_ARGS+=(--MemberUid "$MEMBER_UID")

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeVpcFirewallList \\"
    for ((i=0; i<${#CLI_ARGS[@]}; i+=2)); do
      echo "  ${CLI_ARGS[$i]} '${CLI_ARGS[$((i+1))]}' \\"
    done
    exit 0
  fi

  local response exit_code=0
  response=$(call_cfw_api "DescribeVpcFirewallList" "${CLI_ARGS[@]}") || exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi
  printf '%s' "$response" | summarize_firewall_list
}

# Plan mode: pre-check + route discovery + ready-to-run create command.
assess_plan() {
  local local_vpc_id="$1" local_region="$2" peer_vpc_id="$3" peer_region="$4" member_uid="$5"

  local precheck_json
  precheck_json=$(run_precheck "$local_vpc_id" "$local_region" "$peer_vpc_id" "$peer_region" "$member_uid")

  # Discover routes on both sides (best-effort).
  local local_disc peer_disc local_cidr="[]" peer_cidr="[]" masked32="[]" discover_note=""
  local_disc=$(discover_peering_cidr_tables "$local_region" "$local_vpc_id") || local_disc="DISCOVER_FAILED"
  peer_disc=$(discover_peering_cidr_tables "$peer_region" "$peer_vpc_id") || peer_disc="DISCOVER_FAILED"
  if [[ "$local_disc" == "DISCOVER_FAILED" || "$peer_disc" == "DISCOVER_FAILED" ]]; then
    discover_note="VPC route auto-discovery unavailable (missing vpc:DescribeRouteTableList/DescribeRouteEntryList or no peering route). Pass --local-cidr-json/--peer-cidr-json explicitly to create."
  else
    local_cidr=$(printf '%s' "$local_disc" | python3 -c 'import sys,json;print(json.dumps(json.load(sys.stdin).get("cidr_table_list",[])))')
    peer_cidr=$(printf '%s' "$peer_disc" | python3 -c 'import sys,json;print(json.dumps(json.load(sys.stdin).get("cidr_table_list",[])))')
    # '%s\n' matters: the two discovery payloads are single-line JSON documents
    # and the consumer below parses stdin line by line. Concatenating them with
    # plain '%s' produced "{...}{...}" on one line and json.loads died with
    # "Extra data", taking the whole assess run down. It stayed hidden while the
    # fixtures used nonexistent VPC IDs, because then both sides report
    # DISCOVER_FAILED and this branch is never entered.
    masked32=$(printf '%s\n' "$local_disc" "$peer_disc" | python3 -c '
import sys, json
s = set()
for l in sys.stdin.read().splitlines():
    l = l.strip()
    if not l:
        continue
    try:
        doc = json.loads(l)
    except ValueError:
        continue
    if isinstance(doc, dict):
        s.update(doc.get("masked32", []) or [])
print(json.dumps(sorted(s)))
')
  fi

  python3 - "$precheck_json" "$local_vpc_id" "$local_region" "$peer_vpc_id" "$peer_region" \
            "$local_cidr" "$peer_cidr" "$masked32" "$discover_note" <<'PY'
import json, sys
precheck = json.loads(sys.argv[1])
local_vpc, local_region, peer_vpc, peer_region = sys.argv[2:6]
local_cidr = json.loads(sys.argv[6]); peer_cidr = json.loads(sys.argv[7])
masked32 = json.loads(sys.argv[8]); discover_note = sys.argv[9]
failed = [i for i in precheck.get("items", []) if i.get("status") != "pass"]
actionable = len(failed) == 0 and bool(local_cidr) and bool(peer_cidr) and not masked32
blockers = [i["name"] for i in failed]
risks = []
if masked32:
    risks.append({"what": "route_entry_mask_32",
                  "impact": "peering routes with a /32 mask are NOT protected and enabling the firewall will interrupt access to those CIDRs",
                  "options": ["change the route mask to <= /30 before enabling", "exclude the /32 route from the protected CIDR list"]})
if discover_note:
    risks.append({"what": "route_discovery_degraded", "impact": discover_note, "options": ["grant vpc:DescribeRouteTableList/DescribeRouteEntryList", "pass explicit --local-cidr-json/--peer-cidr-json"]})
cmd = ("vpc-fw-lifecycle.sh create --local-vpc-id %s --local-region %s "
       "--peer-vpc-id %s --peer-region %s --vpc-firewall-name <name> "
       "--firewall-switch close" % (local_vpc, local_region, peer_vpc, peer_region))
plan = {
    "actionable": actionable,
    "precheck": precheck,
    "blockers": blockers,
    "risks": risks,
    "discovered_routes": {"local": local_cidr, "peer": peer_cidr, "masked32": masked32},
    "business_impact": "creation has no impact while the switch stays closed; opening/closing re-learns routes in 5~30 minutes with a second-level flap of long-lived connections",
    "estimated_duration": "creation ~5 minutes; switch ~5~30 minutes",
    "command": cmd,
}
if actionable:
    plan["do_not_execute"] = False
    plan["resolve_first"] = []
    plan["post_steps"] = [
        "present the impact preview, get explicit user confirmation, THEN re-run the command with --yes",
        "poll 'vpc-fw-switch.sh query --vpc-firewall-id <id>' until status is closed/opened (a transitional 'configuring' means keep polling, not failure)",
        "run the Enable/Disable Switch Workflow to start protection (off-peak hours)",
    ]
else:
    # Never hand back a runnable command with --yes while the plan is blocked:
    # copying it verbatim would skip both the pre-check and user confirmation.
    plan["do_not_execute"] = True
    plan["resolve_first"] = blockers
    plan["post_steps"] = [
        "do NOT run the command while actionable is false - resolve every item in resolve_first, then re-run assess",
        "creation would be rejected by the pre-check anyway (ErrorPreCheckFailed)",
    ]
print(json.dumps(plan, ensure_ascii=False, indent=2))
PY
}

# --- Subcommand: precheck ---
cmd_precheck() {
  local LOCAL_VPC_ID="" LOCAL_REGION="" PEER_VPC_ID="" PEER_REGION="" MEMBER_UID="" DRY_RUN=false
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --local-vpc-id) arg_value "--local-vpc-id" "${@:2}"; LOCAL_VPC_ID="$2"; shift 2 ;;
      --local-region) arg_value "--local-region" "${@:2}"; LOCAL_REGION="$2"; shift 2 ;;
      --peer-vpc-id) arg_value "--peer-vpc-id" "${@:2}"; PEER_VPC_ID="$2"; shift 2 ;;
      --peer-region) arg_value "--peer-region" "${@:2}"; PEER_REGION="$2"; shift 2 ;;
      --member-uid) arg_value "--member-uid" "${@:2}"; MEMBER_UID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "vpc-fw-lifecycle.sh precheck" \
          "Local validation of one VPC pair before creation" \
          "vpc-fw-lifecycle.sh precheck --local-vpc-id <id> --local-region <id> --peer-vpc-id <id> --peer-region <id>" \
          "  --local-vpc-id <id>    Local VPC (required)
  --local-region <id>    Local VPC region (required)
  --peer-vpc-id <id>     Peer VPC (required)
  --peer-region <id>     Peer VPC region (required)
  --member-uid <uid>     Operate under a member account
  --dry-run              Preview CLI command

  Checks: region support, both VPCs authorized to CFW, pair not already
  configured, ResultCode clean, peering routes exist, no /32 mask in scope."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "local-vpc-id" "$LOCAL_VPC_ID" || exit 1
  validate_required "local-region" "$LOCAL_REGION" || exit 1
  validate_required "peer-vpc-id" "$PEER_VPC_ID" || exit 1
  validate_required "peer-region" "$PEER_REGION" || exit 1
  validate_vpc_id "$LOCAL_VPC_ID" || exit 1
  validate_vpc_id "$PEER_VPC_ID" || exit 1
  validate_region "$LOCAL_REGION" || exit 1
  validate_region "$PEER_REGION" || exit 1
  [[ -n "$MEMBER_UID" ]] && validate_member_uid "$MEMBER_UID"

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: precheck reads DescribeVpcFirewallList + VPC route tables"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeVpcFirewallList --VpcId '${LOCAL_VPC_ID}' --CurrentPage 1 --PageSize 50"
    exit 0
  fi

  run_precheck "$LOCAL_VPC_ID" "$LOCAL_REGION" "$PEER_VPC_ID" "$PEER_REGION" "$MEMBER_UID"
}

# run_precheck <local_vpc_id> <local_region> <peer_vpc_id> <peer_region> <member_uid>
# Prints a JSON {status, item_count, items[], failed_items[]}. Read-only.
run_precheck() {
  local local_vpc_id="$1" local_region="$2" peer_vpc_id="$3" peer_region="$4" member_uid="$5"

  # Pull the CFW-side facts for this pair (ResultCode / RegionStatus / AuthorizationStatus /
  # whether a firewall already exists). A single query by local VPC ID is enough.
  local list_args=(--CurrentPage 1 --PageSize 50 --Lang zh --VpcId "$local_vpc_id")
  [[ -n "$member_uid" ]] && list_args+=(--MemberUid "$member_uid")
  local list_resp list_err="" list_exit=0
  list_resp=$(call_cfw_api "DescribeVpcFirewallList" "${list_args[@]}") || list_exit=$?
  if [[ $list_exit -ne 0 ]]; then
    # A FAILED call is not the same as an EMPTY result. Swallowing it into '{}'
    # made the pre-check report "the pair is not visible to Cloud Firewall, click
    # Synchronize Assets" after a transient throttling/network error - observed
    # live on 2026-10-21, 1 of 4 identical runs. Carry the reason through so the
    # check names the API failure instead of a missing asset.
    local err_code
    err_code=$(extract_api_error_code "$list_resp")
    list_err="${err_code:-exit ${list_exit}}: $(printf '%s' "$list_resp" | tr '\n\t' '  ' | cut -c1-240)"
    log_warn "DescribeVpcFirewallList failed (${list_err}). The pair-visibility check reports an API failure, not an empty result."
    list_resp="{\"CfwListError\": \"$(json_escape "$list_err")\"}"
  fi

  # Discover peering routes on both sides for the mask/existence checks.
  local local_disc peer_disc
  local_disc=$(discover_peering_cidr_tables "$local_region" "$local_vpc_id") || local_disc="DISCOVER_FAILED"
  peer_disc=$(discover_peering_cidr_tables "$peer_region" "$peer_vpc_id") || peer_disc="DISCOVER_FAILED"

  python3 - "$list_resp" "$local_vpc_id" "$peer_vpc_id" "$local_disc" "$peer_disc" <<'PY'
import json, sys
list_resp = sys.argv[1]
local_vpc, peer_vpc = sys.argv[2], sys.argv[3]
local_disc, peer_disc = sys.argv[4], sys.argv[5]

try:
    lst = json.loads(list_resp)
except Exception:
    lst = {}
if not isinstance(lst, dict):
    lst = {}
# Non-empty only when the DescribeVpcFirewallList call itself failed. That is a
# different fact from "the call succeeded and the pair was not in it".
cfw_list_error = lst.get("CfwListError", "")
items_map = lst.get("VpcFirewalls", []) or []
entry = None
for it in items_map:
    lv = (it.get("LocalVpc", {}) or {}).get("VpcId", "")
    pv = (it.get("PeerVpc", {}) or {}).get("VpcId", "")
    if {lv, pv} == {local_vpc, peer_vpc}:
        entry = it
        break

def disc_ok(d):
    return d != "DISCOVER_FAILED"

def routes(d):
    if not disc_ok(d):
        return None
    try:
        return json.loads(d).get("cidr_table_list", [])
    except Exception:
        return []

def masked(d):
    if not disc_ok(d):
        return []
    try:
        return json.loads(d).get("masked32", [])
    except Exception:
        return []

lr, pr = routes(local_disc), routes(peer_disc)
m32 = sorted(set(masked(local_disc)) | set(masked(peer_disc)))

items = []
def add(name, display, ok, suggestion):
    items.append({"name": name, "display": display,
                  "status": "pass" if ok is True else ("fail" if ok is False else "unknown"),
                  "suggestion": suggestion})

if entry is None:
    if cfw_list_error:
        add("PeeringPairVisible", "Cloud Firewall could be reached to confirm the pair's visibility", False,
            "DescribeVpcFirewallList failed: %s. This is an API/credential/permission failure, NOT proof that the pair is missing - the console asset-sync action is not the remedy here. Retry only if the cause looks transient (Throttling / InternalError); for a parameter error fix the request (VPC ID, region, --MemberUid) and for a permission error grant yundun-cloudfirewall:DescribeVpcFirewallList instead of retrying." % cfw_list_error)
    else:
        add("PeeringPairVisible", "the peering pair is visible to Cloud Firewall (run the Synchronize Assets action if not)", False,
            "The pair was not returned by DescribeVpcFirewallList. Click the Synchronize Assets button on the Peering Connection tab of the VPC boundary firewall page in the console and retry, or verify both VPC IDs and regions.")
    add("RegionSupport", "both VPC regions support the VPC boundary firewall", None,
        "unknown without a CFW list entry")
    add("VpcAuthorized", "both VPCs are authorized to Cloud Firewall", None,
        "unknown without a CFW list entry")
    add("NotAlreadyConfigured", "no VPC firewall is configured for this pair yet", None,
        "unknown without a CFW list entry")
else:
    st = entry.get("FirewallSwitchStatus", "")
    rc = entry.get("ResultCode", "")
    rs = entry.get("RegionStatus", "")
    auth_l = (entry.get("LocalVpc", {}) or {}).get("AuthorizationStatus", "")
    auth_p = (entry.get("PeerVpc", {}) or {}).get("AuthorizationStatus", "")
    add("RegionSupport", "both VPC regions support the VPC boundary firewall", rs != "disable" and rc != "RegionDisable",
        "The region is not open for VPC boundary firewall; pick a supported region (see references/vpc-prerequisites.md).")
    add("VpcAuthorized", "both VPCs are authorized to Cloud Firewall", auth_l == "authorized" and auth_p == "authorized" and rc != "Unauthorized",
        "Authorize Cloud Firewall to access the VPC resources, then retry (see references/vpc-prerequisites.md).")
    add("NotAlreadyConfigured", "no VPC firewall is configured for this pair yet", st in ("notconfigured", ""),
        "A firewall already exists for this pair (status %s). Use 'vpc-fw-switch.sh' to toggle it instead of creating." % st)
    add("ResultCodeClean", "Cloud Firewall reports no blocking ResultCode", rc == "",
        "ResultCode=%s blocks creation; resolve authorization/region first." % rc)

add("LocalRoutesExist", "the local VPC has peering route entries to divert", (None if lr is None else len(lr) > 0),
    "No peering (VpcPeer/RouterInterface) routes found in the local VPC, or route discovery is unavailable. Confirm the peering connection and routes, or pass --local-cidr-json.")
add("PeerRoutesExist", "the peer VPC has peering route entries to divert", (None if pr is None else len(pr) > 0),
    "No peering (VpcPeer/RouterInterface) routes found in the peer VPC, or route discovery is unavailable. Confirm the peering connection and routes, or pass --peer-cidr-json.")
add("NoMask32Route", "no protected route uses a /32 mask (would break access when enabled)", not m32,
    "Routes with a /32 mask are unsupported and enabling the firewall interrupts them: %s. Change the mask to <= /30 first." % (",".join(m32)))

failed = [i["name"] for i in items if i["status"] == "fail"]
status = "pass" if not failed else "fail"
print(json.dumps({"status": status, "item_count": len(items), "items": items, "failed_items": failed,
                  "cfw_list_error": cfw_list_error},
                 ensure_ascii=False, indent=2))
PY
}

# --- Subcommand: create ---
cmd_create() {
  local LOCAL_VPC_ID="" LOCAL_REGION="" PEER_VPC_ID="" PEER_REGION="" FW_NAME="" FW_SWITCH=""
  local LOCAL_CIDR_JSON="" PEER_CIDR_JSON="" MEMBER_UID="" DRY_RUN=false YES=false SKIP_PRECHECK=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --local-vpc-id) arg_value "--local-vpc-id" "${@:2}"; LOCAL_VPC_ID="$2"; shift 2 ;;
      --local-region) arg_value "--local-region" "${@:2}"; LOCAL_REGION="$2"; shift 2 ;;
      --peer-vpc-id) arg_value "--peer-vpc-id" "${@:2}"; PEER_VPC_ID="$2"; shift 2 ;;
      --peer-region) arg_value "--peer-region" "${@:2}"; PEER_REGION="$2"; shift 2 ;;
      --vpc-firewall-name) arg_value "--vpc-firewall-name" "${@:2}"; FW_NAME="$2"; shift 2 ;;
      --firewall-switch) arg_value "--firewall-switch" "${@:2}"; FW_SWITCH="$2"; shift 2 ;;
      --local-cidr-json) arg_value "--local-cidr-json" "${@:2}"; LOCAL_CIDR_JSON="$2"; shift 2 ;;
      --peer-cidr-json) arg_value "--peer-cidr-json" "${@:2}"; PEER_CIDR_JSON="$2"; shift 2 ;;
      --member-uid) arg_value "--member-uid" "${@:2}"; MEMBER_UID="$2"; shift 2 ;;
      --skip-precheck) SKIP_PRECHECK=true; shift ;;
      --yes|-y) YES=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "vpc-fw-lifecycle.sh create" \
          "Create a VPC boundary firewall for a peering pair" \
          "vpc-fw-lifecycle.sh create --local-vpc-id <id> --local-region <id> --peer-vpc-id <id> --peer-region <id> --vpc-firewall-name <name> --firewall-switch <open|close> [--local-cidr-json <json>] [--peer-cidr-json <json>] [--yes]" \
          "  --local-vpc-id <id>       Local VPC (required)
  --local-region <id>       Local VPC region (required)
  --peer-vpc-id <id>        Peer VPC (required)
  --peer-region <id>        Peer VPC region (required)
  --vpc-firewall-name <n>   Firewall instance name (required)
  --firewall-switch <v>     open (auto-enable) | close (create closed, recommended) (required)
  --local-cidr-json <json>  LocalVpcCidrTableList JSON (auto-discovered if omitted)
  --peer-cidr-json <json>   PeerVpcCidrTableList JSON (auto-discovered if omitted)
  --member-uid <uid>        Operate under a member account
  --skip-precheck           Skip the local pre-check (not recommended)
  --yes                     Non-interactive confirmation
  --dry-run                 Preview CLI command

  MANDATORY: every required parameter must come from the user's request. Never
  default a value from these examples. Route tables are auto-discovered from the
  VPC route entries pointing at the peering/Express-Connect next hop; pass
  --*-cidr-json explicitly when auto-discovery is unavailable."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "local-vpc-id" "$LOCAL_VPC_ID" || exit 1
  validate_required "local-region" "$LOCAL_REGION" || exit 1
  validate_required "peer-vpc-id" "$PEER_VPC_ID" || exit 1
  validate_required "peer-region" "$PEER_REGION" || exit 1
  validate_required "vpc-firewall-name" "$FW_NAME" || exit 1
  validate_required "firewall-switch" "$FW_SWITCH" || exit 1
  validate_vpc_id "$LOCAL_VPC_ID" || exit 1
  validate_vpc_id "$PEER_VPC_ID" || exit 1
  validate_region "$LOCAL_REGION" || exit 1
  validate_region "$PEER_REGION" || exit 1
  validate_firewall_name "$FW_NAME" || exit 1
  if [[ "$FW_SWITCH" != "open" && "$FW_SWITCH" != "close" ]]; then
    log_error "Invalid --firewall-switch: ${FW_SWITCH}. Must be 'open' or 'close'"
    exit 1
  fi
  [[ -n "$MEMBER_UID" ]] && validate_member_uid "$MEMBER_UID"

  # Resolve the two CIDR table lists (explicit wins over auto-discovery).
  if [[ -z "$LOCAL_CIDR_JSON" ]]; then
    local disc
    disc=$(discover_peering_cidr_tables "$LOCAL_REGION" "$LOCAL_VPC_ID") || disc="DISCOVER_FAILED"
    if [[ "$disc" == "DISCOVER_FAILED" ]]; then
      log_error "Could not auto-discover the local VPC peering routes (missing vpc read permission or no peering route)."
      log_error "Pass --local-cidr-json explicitly (see references/vpc-prerequisites.md for the format)."
      output_error "RouteDiscoveryFailed" "local VPC route auto-discovery failed"
      exit 2
    fi
    LOCAL_CIDR_JSON=$(printf '%s' "$disc" | python3 -c 'import sys,json;print(json.dumps(json.load(sys.stdin).get("cidr_table_list",[])))')
  fi
  if [[ -z "$PEER_CIDR_JSON" ]]; then
    local disc
    disc=$(discover_peering_cidr_tables "$PEER_REGION" "$PEER_VPC_ID") || disc="DISCOVER_FAILED"
    if [[ "$disc" == "DISCOVER_FAILED" ]]; then
      log_error "Could not auto-discover the peer VPC peering routes (missing vpc read permission or no peering route)."
      log_error "Pass --peer-cidr-json explicitly (see references/vpc-prerequisites.md for the format)."
      output_error "RouteDiscoveryFailed" "peer VPC route auto-discovery failed"
      exit 2
    fi
    PEER_CIDR_JSON=$(printf '%s' "$disc" | python3 -c 'import sys,json;print(json.dumps(json.load(sys.stdin).get("cidr_table_list",[])))')
  fi

  # Reject empty route lists - CreateVpcFirewallConfigure errors with ErrorDestCidrEmpty.
  local local_count peer_count
  local_count=$(printf '%s' "$LOCAL_CIDR_JSON" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)))' 2>/dev/null) || local_count=0
  peer_count=$(printf '%s' "$PEER_CIDR_JSON" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)))' 2>/dev/null) || peer_count=0
  if [[ "$local_count" -eq 0 || "$peer_count" -eq 0 ]]; then
    log_error "One side has no route entries to divert (local=${local_count}, peer=${peer_count})."
    output_error "ErrorDestCidrEmpty" "no route entries on one side of the peering pair"
    exit 2
  fi

  # Pre-check (unless skipped). Blockers abort unless --skip-precheck.
  if [[ "$SKIP_PRECHECK" != "true" ]]; then
    local precheck_json failed_count
    precheck_json=$(run_precheck "$LOCAL_VPC_ID" "$LOCAL_REGION" "$PEER_VPC_ID" "$PEER_REGION" "$MEMBER_UID")
    failed_count=$(printf '%s' "$precheck_json" | python3 -c 'import sys,json;print(len(json.load(sys.stdin).get("failed_items",[])))' 2>/dev/null) || failed_count=0
    if [[ "$failed_count" -gt 0 ]]; then
      log_error "Pre-check reported ${failed_count} blocking item(s). Resolve them before creating (see references/vpc-prerequisites.md)."
      printf '%s\n' "$precheck_json"
      output_error "ErrorPreCheckFailed" "VPC firewall pre-check failed"
      exit 2
    fi
  fi

  local CLI_ARGS=(
    --VpcFirewallName "$FW_NAME"
    --LocalVpcId "$LOCAL_VPC_ID"
    --LocalVpcRegion "$LOCAL_REGION"
    --PeerVpcId "$PEER_VPC_ID"
    --PeerVpcRegion "$PEER_REGION"
    --FirewallSwitch "$FW_SWITCH"
    --LocalVpcCidrTableList "$LOCAL_CIDR_JSON"
    --PeerVpcCidrTableList "$PEER_CIDR_JSON"
    --Lang zh
  )
  [[ -n "$MEMBER_UID" ]] && CLI_ARGS+=(--MemberUid "$MEMBER_UID")

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} CreateVpcFirewallConfigure \\"
    echo "  --VpcFirewallName '${FW_NAME}' \\"
    echo "  --LocalVpcId '${LOCAL_VPC_ID}' --LocalVpcRegion '${LOCAL_REGION}' \\"
    echo "  --PeerVpcId '${PEER_VPC_ID}' --PeerVpcRegion '${PEER_REGION}' \\"
    echo "  --FirewallSwitch '${FW_SWITCH}' \\"
    echo "  --LocalVpcCidrTableList '${LOCAL_CIDR_JSON}' \\"
    echo "  --PeerVpcCidrTableList '${PEER_CIDR_JSON}'"
    exit 0
  fi

  if [[ "$YES" != "true" ]]; then
    # HARD GATE. Creation is irreversible-ish (it makes Cloud Firewall add route
    # entries and a security group inside both VPCs), so a missing --yes must
    # stop here. A warning alone is not enough: the precheck used to mask this by
    # failing first on an already-protected pair, and the moment a pair became
    # protectable the very same command would have created a real firewall.
    log_warn "Creation is a write operation. NOTHING was created."
    log_warn "  Present the impact preview to the user, get an explicit confirmation, then re-run the same command with --yes."
    # The two CIDR blobs are user-supplied JSON, so the preview MUST go through
    # json_escape - embedding it raw produces unparsable output.
    local create_preview="aliyun ${CFW_PRODUCT_CODE} CreateVpcFirewallConfigure --VpcFirewallName '${FW_NAME}' --LocalVpcId '${LOCAL_VPC_ID}' --LocalVpcRegion '${LOCAL_REGION}' --PeerVpcId '${PEER_VPC_ID}' --PeerVpcRegion '${PEER_REGION}' --FirewallSwitch '${FW_SWITCH}' --LocalVpcCidrTableList '${LOCAL_CIDR_JSON}' --PeerVpcCidrTableList '${PEER_CIDR_JSON}'"
    cat <<EOF
{
  "success": false,
  "error_code": "ConfirmationRequired",
  "error_message": "Creating a VPC boundary firewall is a write operation. Review the impact preview, get explicit user confirmation, then re-run the same command with --yes.",
  "vpc_firewall_name": "$(json_escape "$FW_NAME")",
  "command_preview": "$(json_escape "$create_preview")"
}
EOF
    exit 2
  fi

  log_info "Creating VPC boundary firewall '${FW_NAME}' (switch=${FW_SWITCH}) ..."
  local response exit_code=0
  response=$(call_cfw_api "CreateVpcFirewallConfigure" "${CLI_ARGS[@]}") || exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  local fw_id request_id
  fw_id=$(printf '%s' "$response" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("VpcFirewallId",""))' 2>/dev/null) || fw_id=""
  request_id=$(extract_api_request_id "$response")
  cat <<EOF
{
  "success": true,
  "vpc_firewall_id": "${fw_id}",
  "request_id": "${request_id}",
  "firewall_switch": "${FW_SWITCH}",
  "note": "Creation takes ~5 minutes. Poll 'vpc-fw-switch.sh query --vpc-firewall-id ${fw_id}' until the status settles, then run the switch workflow to start protection."
}
EOF
}

# --- Subcommand: update ---
cmd_update() {
  local FW_ID="" FW_NAME="" LOCAL_CIDR_JSON="" PEER_CIDR_JSON="" MEMBER_UID=""
  local DRY_RUN=false SKIP_VERIFY=false YES=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vpc-firewall-id) arg_value "--vpc-firewall-id" "${@:2}"; FW_ID="$2"; shift 2 ;;
      --vpc-firewall-name) arg_value "--vpc-firewall-name" "${@:2}"; FW_NAME="$2"; shift 2 ;;
      --local-cidr-json) arg_value "--local-cidr-json" "${@:2}"; LOCAL_CIDR_JSON="$2"; shift 2 ;;
      --peer-cidr-json) arg_value "--peer-cidr-json" "${@:2}"; PEER_CIDR_JSON="$2"; shift 2 ;;
      --member-uid) arg_value "--member-uid" "${@:2}"; MEMBER_UID="$2"; shift 2 ;;
      --yes|-y) YES=true; shift ;;
      --skip-verify) SKIP_VERIFY=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "vpc-fw-lifecycle.sh update" \
          "Rename / adjust the protected route tables of a VPC firewall (auto-verified)" \
          "vpc-fw-lifecycle.sh update --vpc-firewall-id <vfw-xxxx> [--vpc-firewall-name <name>] [--local-cidr-json <json>] [--peer-cidr-json <json>] [--yes]" \
          "  --vpc-firewall-id <id>    VPC firewall ID (required)
  --vpc-firewall-name <n>   New name (defaults to the current name when omitted)
  --local-cidr-json <json>  New LocalVpcCidrTableList (defaults to the current value)
  --peer-cidr-json <json>   New PeerVpcCidrTableList (defaults to the current value)
  --member-uid <uid>        Operate under a member account
  --yes                     Non-interactive confirmation for the write
  --skip-verify             Skip post-update verification
  --dry-run                 Preview CLI command

  Without --yes this subcommand stops at a hard gate: it prints the impact
  preview and exits 2 with error_code=ConfirmationRequired, and calls nothing.

  ModifyVpcFirewallConfigure REQUIRES the name and both CIDR table lists, so
  omitted fields are read back from DescribeVpcFirewallDetail and passed through
  unchanged."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "vpc-firewall-id" "$FW_ID" || exit 1
  validate_vpc_firewall_id "$FW_ID" || exit 1
  [[ -n "$FW_NAME" ]] && validate_firewall_name "$FW_NAME"
  [[ -n "$MEMBER_UID" ]] && validate_member_uid "$MEMBER_UID"

  # ModifyVpcFirewallConfigure requires the name AND both CIDR table lists.
  # When the caller supplied all three explicitly there is nothing to read back,
  # so skip DescribeVpcFirewallDetail entirely - that keeps --dry-run truly
  # offline (zero API calls) instead of silently issuing a real read.
  if [[ -n "$FW_NAME" && -n "$LOCAL_CIDR_JSON" && -n "$PEER_CIDR_JSON" ]]; then
    log_info "Name and both CIDR table lists supplied; skipping the DescribeVpcFirewallDetail read-back."
  else
    if [[ "$DRY_RUN" == "true" ]]; then
      log_warn "Dry-run still needs one read-only DescribeVpcFirewallDetail call to read back the unspecified field(s). Pass --vpc-firewall-name together with --local-cidr-json and --peer-cidr-json for a fully offline preview."
    fi

    # Read the current detail to fill in the required-but-unspecified fields.
    local detail_args=(--VpcFirewallId "$FW_ID" --Lang zh)
    [[ -n "$MEMBER_UID" ]] && detail_args+=(--MemberUid "$MEMBER_UID")
    local detail exit_code=0
    detail=$(call_cfw_api "DescribeVpcFirewallDetail" "${detail_args[@]}") || exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
      local err_code err_msg
      err_code=$(extract_api_error_code "$detail")
      err_msg=$(extract_api_error_message "$detail")
      diagnose_cfw_error "$err_code" "$err_msg"
      output_error "${err_code:-ProxyNotFound}" "${err_msg:-detail lookup failed}"
      exit 2
    fi

    local extracted current_name
    extracted=$(printf '%s' "$detail" | extract_cidr_tables_from_detail)
    current_name=$(printf '%s' "$extracted" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("vpc_firewall_name",""))')
    [[ -z "$FW_NAME" ]] && FW_NAME="$current_name"
    if [[ -z "$LOCAL_CIDR_JSON" ]]; then
      LOCAL_CIDR_JSON=$(printf '%s' "$extracted" | python3 -c 'import sys,json;print(json.dumps(json.load(sys.stdin).get("local",[])))')
    fi
    if [[ -z "$PEER_CIDR_JSON" ]]; then
      PEER_CIDR_JSON=$(printf '%s' "$extracted" | python3 -c 'import sys,json;print(json.dumps(json.load(sys.stdin).get("peer",[])))')
    fi
    if [[ -z "$FW_NAME" ]]; then
      log_error "Could not resolve a firewall name (detail returned none and --vpc-firewall-name was not given)."
      output_error "ErrorFirewallName" "unable to resolve firewall name"
      exit 2
    fi
  fi

  local CLI_ARGS=(
    --VpcFirewallId "$FW_ID"
    --VpcFirewallName "$FW_NAME"
    --LocalVpcCidrTableList "$LOCAL_CIDR_JSON"
    --PeerVpcCidrTableList "$PEER_CIDR_JSON"
    --Lang zh
  )
  [[ -n "$MEMBER_UID" ]] && CLI_ARGS+=(--MemberUid "$MEMBER_UID")

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} ModifyVpcFirewallConfigure \\"
    echo "  --VpcFirewallId '${FW_ID}' --VpcFirewallName '${FW_NAME}' \\"
    echo "  --LocalVpcCidrTableList '${LOCAL_CIDR_JSON}' \\"
    echo "  --PeerVpcCidrTableList '${PEER_CIDR_JSON}'"
    exit 0
  fi

  if [[ "$YES" != "true" ]]; then
    # HARD GATE. ModifyVpcFirewallConfigure re-submits the name AND both CIDR
    # table lists, so an unconfirmed call can silently drop a route table's
    # diversion. It is also the only subcommand that renames a firewall, which
    # makes it the improvised escape hatch when a create is blocked by the
    # pre-check: without a gate one command renames a real instance.
    local update_preview="aliyun ${CFW_PRODUCT_CODE} ModifyVpcFirewallConfigure --VpcFirewallId '${FW_ID}' --VpcFirewallName '${FW_NAME}' --LocalVpcCidrTableList '${LOCAL_CIDR_JSON}' --PeerVpcCidrTableList '${PEER_CIDR_JSON}'"
    log_warn "Modifying a VPC firewall is a write operation. NOTHING was changed."
    log_warn "  Present the impact preview to the user, get an explicit confirmation, then re-run the same command with --yes."
    cat <<EOF
{
  "success": false,
  "error_code": "ConfirmationRequired",
  "error_message": "Modifying a VPC firewall (rename / protected CIDR tables) is a write operation. Review the impact preview, get explicit user confirmation, then re-run the same command with --yes.",
  "vpc_firewall_id": "$(json_escape "$FW_ID")",
  "vpc_firewall_name": "$(json_escape "$FW_NAME")",
  "impact": "ModifyVpcFirewallConfigure re-submits the name AND both CIDR table lists, so any route table omitted from a list loses its diversion. Changing the protected CIDRs changes which east-west traffic this firewall inspects.",
  "command_preview": "$(json_escape "$update_preview")"
}
EOF
    exit 2
  fi

  local response
  response=$(call_cfw_api "ModifyVpcFirewallConfigure" "${CLI_ARGS[@]}") || exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  # Built-in verification: ModifyVpcFirewallConfigure returns a bare RequestId.
  if [[ "$SKIP_VERIFY" == "true" ]]; then
    printf '{"success": true, "vpc_firewall_id": "%s", "verification": {"verified": false, "reason": "skipped"}}\n' "$FW_ID"
    return 0
  fi
  local attempt verified_name=""
  for attempt in 1 2 3; do
    sleep 2
    local vlist
    vlist=$(call_cfw_api "DescribeVpcFirewallList" --VpcFirewallId "$FW_ID" --CurrentPage 1 --PageSize 1 --Lang zh 2>/dev/null) || vlist='{}'
    verified_name=$(printf '%s' "$vlist" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    fws = d.get("VpcFirewalls", []) or []
    print(fws[0].get("VpcFirewallName", "") if fws else "")
except Exception:
    print("")
' 2>/dev/null) || verified_name=""
    [[ "$verified_name" == "$FW_NAME" ]] && break
  done

  if [[ "$verified_name" == "$FW_NAME" ]]; then
    printf '{"success": true, "vpc_firewall_id": "%s", "verification": {"verified": true, "vpc_firewall_name": "%s"}}\n' "$FW_ID" "$(json_escape "$FW_NAME")"
  else
    log_error "Verification failed: expected name '${FW_NAME}', found '${verified_name}'."
    printf '{"success": false, "error_code": "VerifyFailed", "vpc_firewall_id": "%s", "verification": {"verified": false, "expected": "%s", "found": "%s"}}\n' "$FW_ID" "$(json_escape "$FW_NAME")" "$(json_escape "$verified_name")"
    exit 2
  fi
}

# --- Subcommand: delete (DISABLED) ---
cmd_delete() {
  local FW_ID="" DRY_RUN=false
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vpc-firewall-id) arg_value "--vpc-firewall-id" "${@:2}"; FW_ID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --yes|-y) shift ;;  # accepted but never overrides the lockdown
      --help|-h)
        show_help "vpc-fw-lifecycle.sh delete" \
          "DISABLED - this skill never deletes a VPC firewall" \
          "vpc-fw-lifecycle.sh delete [--vpc-firewall-id <vfw-xxxx>]" \
          "  --vpc-firewall-id <id>  Optional; enables a read-only impact report
  --dry-run               Preview (no-op)

  Releasing a VPC boundary firewall is the user's own console action. This
  subcommand only prints the close-vs-release guidance and, with an ID, a
  read-only impact report."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  log_warn "Deletion is intentionally DISABLED in this skill."
  local report=""
  if [[ -n "$FW_ID" ]]; then
    validate_vpc_firewall_id "$FW_ID" || exit 1
    local detail exit_code=0
    detail=$(call_cfw_api "DescribeVpcFirewallDetail" --VpcFirewallId "$FW_ID" --Lang zh 2>/dev/null) || exit_code=$?
    if [[ $exit_code -eq 0 ]]; then
      report=$(printf '%s' "$detail" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(json.dumps({"vpc_firewall_name": d.get("VpcFirewallName", ""),
                      "firewall_switch_status": d.get("FirewallSwitchStatus", ""),
                      "local_vpc": (d.get("LocalVpc", {}) or {}).get("VpcId", ""),
                      "peer_vpc": (d.get("PeerVpc", {}) or {}).get("VpcId", "")}))
except Exception:
    print("{}")
')
    fi
  fi

  cat <<EOF
{
  "success": false,
  "error_code": "DeletionDisabled",
  "error_message": "This skill never releases a VPC boundary firewall.",
  "close_protection_supported": true,
  "release_guidance": {
    "how": "Cloud Firewall console -> Switch -> VPC Boundary Firewall -> Peering Connection tab -> locate the firewall -> Delete",
    "how_note": "Present this path with the localized console labels, not this English gloss.",
    "api_not_called": "DeleteVpcFirewallConfigure",
    "advice": "Close the switch first during off-peak hours (vpc-fw-switch.sh disable), then delete in the console. Deleting while opened performs close+delete together and may flap traffic."
  },
  "not_reclaimed_assets": [
    "CFW-created custom route table entries (marked 'Created by cloud firewall. Do not modify or delete it.')",
    "Cloud_Firewall_Security_Group security group and its allow policy"
  ],
  "impact_report": ${report:-null}
}
EOF
  exit 2
}

# --- Main Router ---

SUBCOMMAND="${1:-}"
if [[ -z "$SUBCOMMAND" || "$SUBCOMMAND" == "--help" || "$SUBCOMMAND" == "-h" ]]; then
  show_main_help
fi
shift

case "$SUBCOMMAND" in
  assess)
    cmd_assess "$@"
    ;;
  precheck)
    cmd_precheck "$@"
    ;;
  create)
    cmd_create "$@"
    ;;
  update)
    cmd_update "$@"
    ;;
  delete)
    cmd_delete "$@"
    ;;
  *)
    log_error "Unknown subcommand: ${SUBCOMMAND}"
    log_error "Run 'vpc-fw-lifecycle.sh --help' for usage"
    exit 1
    ;;
esac
