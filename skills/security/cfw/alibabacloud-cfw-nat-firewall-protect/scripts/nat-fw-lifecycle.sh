#!/usr/bin/env bash
# nat-fw-lifecycle.sh - Manage Cloud Firewall NAT firewall lifecycle
# Part of alibabacloud-cfw-nat-firewall-protect skill
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin and Vpc plugin
#   - python3 (for JSON parsing)
#
# Subcommands:
#   precheck - Run creation pre-check for a NAT gateway (CreateNatFirewallPreCheck)
#   quota    - Query NAT firewall quota (DescribeNatFirewallQuota)
#   assess   - Read-only planning: inventory unprotected NAT gateways and
#              recommend auto/manual diversion mode per gateway
#   prepare  - Prepare manual-mode assets: dedicated vswitch + NEW custom
#              route table (idempotent)
#   route-diff - Deep-diagnose custom route entry inconsistency across a
#              VPC's route tables and print resolution options (read-only)
#   create   - Create a NAT firewall (auto or manual vswitch mode, CreateSecurityProxy)
#   delete   - DISABLED: refuses and explains the console path (releasing a
#              firewall is the user's own deliberate action; read-only)
#   update   - Rename / change engine strict mode (UpdateSecurityProxy)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# --- Main Help ---
show_main_help() {
  cat >&2 <<'EOF'
nat-fw-lifecycle.sh - Manage Cloud Firewall NAT firewall lifecycle

USAGE:
  nat-fw-lifecycle.sh <subcommand> [options]

SUBCOMMANDS:
  precheck  Run creation pre-check for a NAT gateway
  quota     Query NAT firewall quota (used/total authorizations)
  assess    Read-only assessment: list unprotected NAT gateways and recommend
            the diversion mode (auto / manual) for each
  prepare   Prepare manual-mode assets: dedicated vswitch + NEW custom route
            table (idempotent: reuses existing qualifying assets)
  route-diff Diagnose custom route entry inconsistency across a VPC's route
            tables: per-table diff, next-hop classification, and both
            resolution options (manual diversion / alignment plan). Read-only
  create    Create a NAT firewall (auto or manual vswitch traffic diversion mode)
  delete    Delete a NAT firewall
  update    Rename a NAT firewall or change its engine strict mode

GLOBAL OPTIONS:
  --dry-run   Preview CLI command without executing
  --help, -h  Show help for the subcommand

EXAMPLES:
  nat-fw-lifecycle.sh quota
  nat-fw-lifecycle.sh assess --region cn-hangzhou
  nat-fw-lifecycle.sh precheck --nat-gateway-id ngw-bp1xxxx --region cn-hangzhou --vpc-id vpc-bp1xxxx
  nat-fw-lifecycle.sh prepare --region cn-hangzhou --vpc-id vpc-bp1xxxx --nat-gateway-id ngw-bp1xxxx --vswitch-cidr 10.0.4.0/24 --yes
  nat-fw-lifecycle.sh route-diff --region cn-hangzhou --vpc-id vpc-bp1xxxx
  nat-fw-lifecycle.sh create --nat-gateway-id ngw-bp1xxxx --region cn-hangzhou --vpc-id vpc-bp1xxxx --proxy-name nat-fw-prod --yes
  nat-fw-lifecycle.sh delete --proxy-id proxy-bp1xxxx --yes
  nat-fw-lifecycle.sh update --proxy-id proxy-bp1xxxx --strict-mode 1

EXIT CODES:
  0  Success
  1  Parameter validation error
  2  API call failed
EOF
  exit 0
}

# --- JSON helpers (python3) ---

json_parse() {
  # Usage: json_parse <json> <python_expr_on_obj>
  local json="$1"
  local expr="$2"
  printf '%s' "$json" | python3 -c "import sys, json; d = json.load(sys.stdin); print($expr)" 2>/dev/null
}

# Check whether a route table contains a 0.0.0.0/0 entry.
# Prints: yes | no | unknown (unknown on API failure, e.g. missing permission).
route_table_has_default_route() {
  local region="$1" rt_id="$2"
  local resp exit_code=0 found
  resp=$(call_vpc_api "DescribeRouteEntryList" --RegionId "$region" --RouteTableId "$rt_id" --MaxResult 100 2>/dev/null) || exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    echo "unknown"
    return 0
  fi
  found=$(printf '%s' "$resp" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
for e in d.get("RouteEntrys", {}).get("RouteEntry", []):
    if e.get("DestinationCidrBlock") == "0.0.0.0/0":
        print("yes")
        break
else:
    print("no")
') || { echo "unknown"; return 0; }
  echo "${found:-unknown}"
}

# Profile the CUSTOM entries of a route table (manual-mode diversion table
# hygiene, constraint 5). Manual mode requires a NEWLY created custom route
# table; the only legitimate pre-existing entries are cross-VPC return routes
# (peering / VPN / TR attachment / VBR next hops, see nat-prerequisites.md
# "Mandatory human steps"). Business routes (ECS instance, ENI, HaVip, another
# NAT gateway ...) mean the table is a production table and reusing it would
# reroute live traffic through the firewall diversion vswitch.
# Output: single TAB-separated line
#   <default_flag>\t<nondefault_count>\t<next_hop_types>\t<samples>
#     default_flag : yes | no | unknown
#     types        : distinct next-hop types joined by '+' ('' when none)
#     samples      : up to 3 "cidr>Type:Id" items joined by spaces
route_table_entry_profile() {
  local region="$1" rt_id="$2"
  local resp exit_code=0
  resp=$(call_vpc_api "DescribeRouteEntryList" --RegionId "$region" --RouteTableId "$rt_id" --RouteEntryType Custom --MaxResult 100 2>/dev/null) || exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    printf 'unknown\t0\t\t'
    return 0
  fi
  printf '%s' "$resp" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print("unknown\t0\t\t"); sys.exit(0)
default_flag = "no"; types = []; samples = []; count = 0
for e in d.get("RouteEntrys", {}).get("RouteEntry", []):
    cidr = e.get("DestinationCidrBlock", "")
    hops = e.get("NextHops", {}).get("NextHop") or [{}]
    ht = hops[0].get("NextHopType", ""); hid = hops[0].get("NextHopId", "")
    if cidr == "0.0.0.0/0":
        default_flag = "yes"
        continue
    count += 1
    if ht and ht not in types:
        types.append(ht)
    if len(samples) < 3:
        samples.append("%s>%s:%s" % (cidr, ht, hid))
print("%s\t%d\t%s\t%s" % (default_flag, count, "+".join(types), " ".join(samples)))
' 2>/dev/null || printf 'unknown\t0\t\t'
}

# Split the next-hop types of a route table into the ones NOT acceptable for a
# manual-mode diversion table. Input: types joined by '+'. Output: comma-joined
# disqualifying types ('' when all are plausible cross-VPC return routes).
route_table_disqualifying_types() {
  printf '%s' "${1:-}" | python3 -c '
import sys
# Cross-VPC return-route next hops the official manual-mode steps allow.
allow = {"VpcPeer", "VpnGateway", "RouterInterface", "VBR", "Attachment", "TunnelInterface"}
types = [t for t in sys.stdin.read().strip().split("+") if t]
print(",".join([t for t in types if t not in allow]))
' 2>/dev/null || true
}

# Count ENIs attached to a vswitch (manual-mode constraint 6: the diversion
# vswitch must be dedicated, with no other cloud resources on it). Previously a
# human-checklist-only item; automated here, degrading to "unknown" when
# ecs:DescribeNetworkInterfaces is not granted.
# Output: integer | "unknown"
vswitch_attached_eni_count() {
  local region="$1" vswitch_id="$2"
  local resp exit_code=0
  resp=$(call_ecs_api "DescribeNetworkInterfaces" --RegionId "$region" --VSwitchId "$vswitch_id" --MaxResults 100 2>/dev/null) || exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    echo "unknown"
    return 0
  fi
  printf '%s' "$resp" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print("unknown"); sys.exit(0)
print(len(d.get("NetworkInterfaceSets", {}).get("NetworkInterfaceSet", [])))
' 2>/dev/null || echo "unknown"
}

# Discover route entries whose next hop is the given NAT gateway.
# Scans every route table of the VPC via:
#   1. Vpc DescribeRouteTableList --VpcId <vpc> (paginated)
#   2. Vpc DescribeRouteEntryList --RouteTableId <rt> --NextHopId <nat> --NextHopType NatGateway
# Output: TSV lines "DestinationCidr<TAB>NextHopId<TAB>NextHopType<TAB>RouteTableId" on stdout
discover_nat_route_entries() {
  local region="$1" vpc_id="$2" nat_gw_id="$3"

  command -v python3 &>/dev/null || { log_error "python3 is required for route discovery"; return 1; }

  # Step 1: collect route table IDs of the VPC (paginate, page size 50)
  local rt_ids=() page=1
  while :; do
    local rt_response rt_exit=0
    rt_response=$(call_vpc_api "DescribeRouteTableList" \
      --RegionId "$region" --VpcId "$vpc_id" \
      --PageNumber "$page" --PageSize 50) || rt_exit=$?
    if [[ $rt_exit -ne 0 ]]; then
      local err_code
      err_code=$(extract_api_error_code "$rt_response")
      log_error "Failed to list route tables of VPC ${vpc_id}: ${err_code:-unknown}"
      return $rt_exit
    fi

    local ids_in_page
    ids_in_page=$(json_parse "$rt_response" "'\\n'.join(t['RouteTableId'] for t in d.get('RouterTableList', {}).get('RouterTableListType', []))")
    if [[ -n "$ids_in_page" ]]; then
      while IFS= read -r rt_id; do
        [[ -n "$rt_id" ]] && rt_ids+=("$rt_id")
      done <<< "$ids_in_page"
    fi

    local total_count
    total_count=$(json_parse "$rt_response" "d.get('TotalCount', 0)")
    if [[ -z "$total_count" || $((page * 50)) -ge "$total_count" ]]; then
      break
    fi
    page=$((page + 1))
  done

  if [[ ${#rt_ids[@]} -eq 0 ]]; then
    log_error "No route tables found in VPC ${vpc_id}"
    return 1
  fi
  log_info "Found ${#rt_ids[@]} route table(s) in VPC ${vpc_id}"

  # Step 2: for each route table, find entries with next hop = NAT gateway
  local rt_id entry_response entry_exit entries
  for rt_id in "${rt_ids[@]}"; do
    entry_exit=0
    entry_response=$(call_vpc_api "DescribeRouteEntryList" \
      --RegionId "$region" --RouteTableId "$rt_id" \
      --MaxResult 100) || entry_exit=$?
    if [[ $entry_exit -ne 0 ]]; then
      log_warn "Failed to query route entries of route table ${rt_id}, skipping"
      continue
    fi
    entries=$(json_parse "$entry_response" "'\\n'.join('\\t'.join([e.get('DestinationCidrBlock',''), n.get('NextHopId',''), n.get('NextHopType',''), e.get('RouteTableId','$rt_id')]) for e in d.get('RouteEntrys', {}).get('RouteEntry', []) for n in e.get('NextHops', {}).get('NextHop', []) if n.get('NextHopId') == '$nat_gw_id')")
    if [[ -n "$entries" ]]; then
      printf '%s\n' "$entries"
    fi
  done
}

# --- Subcommand: precheck ---
cmd_precheck() {
  local NAT_GATEWAY_ID="" REGION="" VPC_ID="" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --nat-gateway-id) arg_value "--nat-gateway-id" "${@:2}"; NAT_GATEWAY_ID="$2"; shift 2 ;;
      --region) arg_value "--region" "${@:2}"; REGION="$2"; shift 2 ;;
      --vpc-id) arg_value "--vpc-id" "${@:2}"; VPC_ID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "nat-fw-lifecycle.sh precheck" \
          "Run NAT firewall creation pre-check (one-click check)" \
          "nat-fw-lifecycle.sh precheck --nat-gateway-id <id> --region <id> --vpc-id <id>" \
          "  --nat-gateway-id <id>  NAT gateway ID (required)
  --region <id>          Region ID (required)
  --vpc-id <id>          VPC ID (required)
  --dry-run              Preview CLI command
  --help, -h             Show this help

  Triggers CreateNatFirewallPreCheck, then polls
  DescribeNatFirewallPrecheckDetail every 3 seconds (max 30 seconds)."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "nat-gateway-id" "$NAT_GATEWAY_ID" || exit 1
  validate_required "region" "$REGION" || exit 1
  validate_required "vpc-id" "$VPC_ID" || exit 1
  validate_nat_gateway_id "$NAT_GATEWAY_ID" || exit 1
  validate_region "$REGION" || exit 1
  validate_vpc_id "$VPC_ID" || exit 1

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} CreateNatFirewallPreCheck \\"
    echo "  --NatGatewayId '${NAT_GATEWAY_ID}' \\"
    echo "  --RegionNo '${REGION}' \\"
    echo "  --VpcId '${VPC_ID}' \\"
    echo "  --Lang 'zh'"
    echo "# then poll:"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeNatFirewallPrecheckDetail \\"
    echo "  --NatGatewayId '${NAT_GATEWAY_ID}' \\"
    echo "  --RegionNo '${REGION}' \\"
    echo "  --Lang 'zh'"
    exit 0
  fi

  # Trigger pre-check
  local response exit_code=0
  response=$(call_cfw_api "CreateNatFirewallPreCheck" \
    --NatGatewayId "$NAT_GATEWAY_ID" --RegionNo "$REGION" --VpcId "$VPC_ID" --Lang zh) || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  # Poll pre-check result
  log_info "Pre-check triggered, polling result ..."
  local detail="" i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 3
    local detail_exit=0
    detail=$(call_cfw_api "DescribeNatFirewallPrecheckDetail" \
      --NatGatewayId "$NAT_GATEWAY_ID" --RegionNo "$REGION" --Lang zh) || detail_exit=$?
    if [[ $detail_exit -eq 0 && -n "$detail" ]]; then
      output_success "$detail"
      exit 0
    fi
  done

  log_error "Pre-check result not available after 30 seconds"
  output_error "PrecheckTimeout" "Pre-check result not available within 30 seconds; retry DescribeNatFirewallPrecheckDetail later"
  exit 2
}

# --- Subcommand: quota ---
cmd_quota() {
  local DRY_RUN=false
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "nat-fw-lifecycle.sh quota" \
          "Query NAT firewall quota (authorization usage)" \
          "nat-fw-lifecycle.sh quota" \
          "  --dry-run   Preview CLI command
  --help, -h  Show this help"
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeNatFirewallQuota --Lang 'zh'"
    exit 0
  fi

  local response exit_code=0
  response=$(call_cfw_api "DescribeNatFirewallQuota" --Lang zh) || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  output_success "$response"
}

# --- Subcommand: create ---

# Pre-check the diversion vswitch CIDR before creation (fail fast):
#   1. Local format validation via python3 ipaddress
#   2. Must be a subnet of the VPC CIDR (incl. secondary CIDRs)
#   3. Must not overlap any existing vswitch in the VPC
# On missing VPC read permissions the check degrades to a warning and lets
# the API enforce the constraint later. Returns 0 if OK, 1 if blocked.
check_vswitch_cidr() {
  local region="$1" vpc_id="$2" cidr="$3"

  command -v python3 &>/dev/null || { log_warn "python3 unavailable; skipping CIDR pre-check"; return 0; }

  # Step 1: local format validation (no API call)
  local fmt_err
  fmt_err=$(python3 - "$cidr" <<'PY'
import sys, ipaddress
try:
    ipaddress.ip_network(sys.argv[1], strict=True)
except ValueError as e:
    print(e)
PY
)
  if [[ -n "$fmt_err" ]]; then
    log_error "Invalid --vswitch-cidr '${cidr}': ${fmt_err}"
    return 1
  fi

  # Step 2: fetch VPC CIDR (primary + secondary).
  # Try DescribeVpcAttribute first, fall back to DescribeVpcs (accounts often
  # grant one but not the other; both return CidrBlock + SecondaryCidrBlocks).
  local vpc_resp vpc_exit=0 vpc_cidr secondary_cidrs
  vpc_resp=$(call_vpc_api "DescribeVpcAttribute" --RegionId "$region" --VpcId "$vpc_id") || vpc_exit=$?
  if [[ $vpc_exit -eq 0 ]]; then
    vpc_cidr=$(json_parse "$vpc_resp" "d.get('CidrBlock', '')")
    secondary_cidrs=$(json_parse "$vpc_resp" "','.join(d.get('SecondaryCidrBlocks', {}).get('SecondaryCidrBlock', []))")
  else
    log_info "DescribeVpcAttribute unavailable, falling back to DescribeVpcs ..."
    vpc_exit=0
    vpc_resp=$(call_vpc_api "DescribeVpcs" --RegionId "$region" --VpcId "$vpc_id") || vpc_exit=$?
    if [[ $vpc_exit -eq 0 ]]; then
      vpc_cidr=$(json_parse "$vpc_resp" "(d.get('Vpcs', {}).get('Vpc') or [{}])[0].get('CidrBlock', '')")
      secondary_cidrs=$(json_parse "$vpc_resp" "','.join((d.get('Vpcs', {}).get('Vpc') or [{}])[0].get('SecondaryCidrBlocks', {}).get('SecondaryCidrBlock', []))")
    fi
  fi
  if [[ $vpc_exit -ne 0 || -z "$vpc_cidr" ]]; then
    log_warn "CIDR pre-check: could not read VPC CIDR (missing vpc:DescribeVpcAttribute / vpc:DescribeVpcs permission?). Overlap-only check will continue; range check skipped."
    vpc_cidr=""
    secondary_cidrs=""
  fi

  # Step 3: enumerate existing vswitches (paginated)
  local existing="" page=1
  while :; do
    local vs_resp vs_exit=0
    vs_resp=$(call_vpc_api "DescribeVSwitches" --RegionId "$region" --VpcId "$vpc_id" --PageNumber "$page" --PageSize 50) || vs_exit=$?
    if [[ $vs_exit -ne 0 ]]; then
      log_warn "CIDR pre-check: DescribeVSwitches failed (missing vpc:DescribeVSwitches permission?). Skipping pre-check; the create API will validate later."
      return 0
    fi
    local rows
    rows=$(json_parse "$vs_resp" "'\\n'.join('\\t'.join([v['VSwitchId'], v['CidrBlock'], v.get('VSwitchName', '')]) for v in d.get('VSwitches', {}).get('VSwitch', []))")
    [[ -n "$rows" ]] && existing+="${rows}"$'\n'
    local vs_total
    vs_total=$(json_parse "$vs_resp" "d.get('TotalCount', 0)")
    if [[ -z "$vs_total" || $((page * 50)) -ge "$vs_total" ]]; then
      break
    fi
    page=$((page + 1))
  done

  # Step 4: conflict analysis + free-CIDR suggestions.
  # NOTE: script via -c (not a heredoc) - a heredoc would override the pipe
  # and the existing-vswitch data would never reach sys.stdin.
  local verdict_line
  verdict_line=$(printf '%s' "$existing" | python3 -c '
import sys, ipaddress
target = ipaddress.ip_network(sys.argv[1])
vpc_cidrs = [c for c in sys.argv[2].split(",") if c]
nets = [ipaddress.ip_network(c) for c in vpc_cidrs]
if nets and not any(target.subnet_of(n) for n in nets):
    print("OUT_OF_VPC\t" + ", ".join(vpc_cidrs)); sys.exit(0)
existing = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line: continue
    parts = line.split("\t")
    existing.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
def label(vid, vcidr, vn):
    return vid + "(" + vcidr + (", " + vn if vn else "") + ")"
conflicts = [label(vid, vcidr, vn)
             for vid, vcidr, vn in existing
             if target.overlaps(ipaddress.ip_network(vcidr))]
used = [ipaddress.ip_network(v) for _, v, _ in existing]
parent = next((n for n in nets if target.subnet_of(n)), (nets[0] if nets else None))
sugs = []
if parent is not None and parent.prefixlen <= 24:
    count = 0
    for sub in parent.subnets(new_prefix=28):
        count += 1
        if count > 20000: break
        if not any(sub.overlaps(u) for u in used):
            sugs.append(str(sub))
            if len(sugs) >= 3: break
line = ("CONFLICT\t" + "; ".join(conflicts)) if conflicts else "OK"
if sugs:
    line += "\tFree /28 candidates: " + ", ".join(sugs)
print(line)
' "$cidr" "${vpc_cidr},${secondary_cidrs}")

  local verdict
  verdict=$(printf '%s' "$verdict_line" | cut -f1)
  if [[ -z "$verdict_line" ]]; then
    log_error "CIDR pre-check internal error (python3 analysis produced no output). Refusing to proceed."
    return 1
  fi
  case "$verdict" in
    OK)
      log_info "CIDR pre-check passed: ${cidr} is free inside VPC ${vpc_id}"
      return 0
      ;;
    OUT_OF_VPC)
      log_error "--vswitch-cidr ${cidr} is outside the VPC CIDR range ($(printf '%s' "$verdict_line" | cut -f2)). Choose a subnet inside the VPC."
      return 1
      ;;
    CONFLICT)
      log_error "--vswitch-cidr ${cidr} overlaps existing vswitch(es): $(printf '%s' "$verdict_line" | cut -f2)"
      local suggestion
      suggestion=$(printf '%s' "$verdict_line" | cut -f3)
      [[ -n "$suggestion" ]] && log_info "$suggestion"
      return 1
      ;;
    *)
      log_error "CIDR pre-check internal error (unexpected verdict: ${verdict_line}). Refusing to proceed."
      return 1
      ;;
  esac
}

# Pre-check a user-provided vswitch for MANUAL diversion mode (fail fast).
# Hard constraints enforced here (official doc + CreateSecurityProxy behavior):
#   1. vswitch exists and belongs to the same VPC as the NAT gateway
#   2. same availability zone as the NAT gateway (NatGatewayPrivateInfo.IzNo)
#   3. prefix >= /28
#   4. AvailableIpAddressCount > number of EIPs bound to the NAT gateway
# Also surfaces what the CLI cannot reliably verify:
#   5. route table bound to the vswitch must be a NEW custom table with no
#      0.0.0.0/0 entry (system table or a default route -> server rejects with
#      ErrorDefaultRouteConflicts)
#   6. vswitch must have no other cloud resources attached
# Missing VPC read permissions degrade to warnings (API enforces later).
# Returns 0 if OK, 1 if blocked.
check_vswitch_manual() {
  local region="$1" vpc_id="$2" nat_gw_id="$3" vswitch_id="$4"

  command -v python3 &>/dev/null || { log_warn "python3 unavailable; skipping manual-mode vswitch pre-check"; return 0; }

  # Step 1: fetch the vswitch attributes
  local vs_resp vs_exit=0
  vs_resp=$(call_vpc_api "DescribeVSwitches" --RegionId "$region" --VSwitchId "$vswitch_id") || vs_exit=$?
  if [[ $vs_exit -ne 0 ]]; then
    log_warn "Manual-mode pre-check: DescribeVSwitches failed (missing vpc:DescribeVSwitches permission?). Skipping pre-check; the create API will validate later."
    return 0
  fi
  local vs_vpc vs_zone vs_cidr vs_avail vs_rt_id vs_rt_type
  vs_vpc=$(json_parse "$vs_resp" "(d.get('VSwitches', {}).get('VSwitch') or [{}])[0].get('VpcId', '')")
  if [[ -z "$vs_vpc" ]]; then
    log_error "Vswitch ${vswitch_id} was not found in region ${region}."
    log_error "Environment drift: vswitches referenced by a previous 'assess' may have been deleted or modified in the console meanwhile. Re-run 'nat-fw-lifecycle.sh assess --region ${region}' to refresh candidates."
    return 1
  fi
  vs_zone=$(json_parse "$vs_resp" "(d.get('VSwitches', {}).get('VSwitch') or [{}])[0].get('ZoneId', '')")
  vs_cidr=$(json_parse "$vs_resp" "(d.get('VSwitches', {}).get('VSwitch') or [{}])[0].get('CidrBlock', '')")
  vs_avail=$(json_parse "$vs_resp" "(d.get('VSwitches', {}).get('VSwitch') or [{}])[0].get('AvailableIpAddressCount', 0)")
  vs_rt_id=$(json_parse "$vs_resp" "(d.get('VSwitches', {}).get('VSwitch') or [{}])[0].get('RouteTable', {}).get('RouteTableId', '')")
  vs_rt_type=$(json_parse "$vs_resp" "(d.get('VSwitches', {}).get('VSwitch') or [{}])[0].get('RouteTable', {}).get('RouteTableType', '')")

  # Step 2: fetch the NAT gateway attributes
  local ng_resp ng_exit=0
  ng_resp=$(call_vpc_api "DescribeNatGateways" --RegionId "$region" --NatGatewayId "$nat_gw_id") || ng_exit=$?
  if [[ $ng_exit -ne 0 ]]; then
    log_warn "Manual-mode pre-check: DescribeNatGateways failed (missing vpc:DescribeNatGateways permission?). Skipping pre-check; the create API will validate later."
    return 0
  fi
  local ng_zone ng_eips
  ng_zone=$(json_parse "$ng_resp" "(d.get('NatGateways', {}).get('NatGateway') or [{}])[0].get('NatGatewayPrivateInfo', {}).get('IzNo', '')")
  ng_eips=$(json_parse "$ng_resp" "len((d.get('NatGateways', {}).get('NatGateway') or [{}])[0].get('IpLists', {}).get('IpList', []))")
  [[ -z "$ng_eips" ]] && ng_eips=0

  # Step 3: hard constraint checks (1~4)
  local failures=()
  if [[ "$vs_vpc" != "$vpc_id" ]]; then
    failures+=("vswitch belongs to VPC ${vs_vpc}, but the NAT gateway VPC is ${vpc_id} (they must be the same VPC)")
  fi
  if [[ -n "$ng_zone" && "$vs_zone" != "$ng_zone" ]]; then
    failures+=("vswitch is in zone ${vs_zone}, but the NAT gateway is in zone ${ng_zone} (they must be in the same zone)")
  fi
  local prefix
  prefix=$(python3 -c "import sys,ipaddress; print(ipaddress.ip_network(sys.argv[1]).prefixlen)" "$vs_cidr" 2>/dev/null || echo "")
  if [[ -z "$prefix" ]]; then
    log_warn "Could not parse vswitch CIDR '${vs_cidr}'; skipping prefix check"
  elif [[ "$prefix" -gt 28 ]]; then
    failures+=("vswitch CIDR ${vs_cidr} is /${prefix}; manual mode requires a prefix of /28 or larger network (e.g. /28, /24)")
  fi
  if [[ "$vs_avail" -le "$ng_eips" ]]; then
    failures+=("vswitch has ${vs_avail} available IPs, but the NAT gateway binds ${ng_eips} EIP(s); available IPs must be greater than the EIP count")
  fi

  if [[ ${#failures[@]} -gt 0 ]]; then
    local f
    for f in "${failures[@]}"; do
      log_error "Manual-mode pre-check failed: ${f}"
    done
    log_error "Pick a different vswitch (see references/nat-prerequisites.md, Traffic Diversion Mode)."
    return 1
  fi

  # Step 4: route-table check (constraint 5). The server adds a 0.0.0.0/0 ->
  # NAT entry into the route table bound to this vswitch; a pre-existing
  # default route is rejected with ErrorDefaultRouteConflicts.
  if [[ -z "$vs_rt_id" || "$vs_rt_type" == "System" ]]; then
    log_error "Manual-mode pre-check failed: vswitch ${vswitch_id} is bound to the SYSTEM route table (${vs_rt_id:-none}). Manual mode requires a NEW custom route table created and bound to the vswitch BEFORE creation."
    return 1
  fi
  local profile default_found nd_count nd_types nd_samples
  profile=$(route_table_entry_profile "$region" "$vs_rt_id")
  IFS=$'\t' read -r default_found nd_count nd_types nd_samples <<< "$profile"
  if [[ "$default_found" == "yes" ]]; then
    log_error "Manual-mode pre-check failed: route table ${vs_rt_id} (bound to the vswitch) already contains a 0.0.0.0/0 entry. The create API rejects this with ErrorDefaultRouteConflicts - bind a fresh custom route table without a default route."
    return 1
  fi
  if [[ "$default_found" == "unknown" ]]; then
    log_warn "Route table check: could not list entries of ${vs_rt_id} (missing vpc:DescribeRouteEntryList permission?). Ensure it has NO 0.0.0.0/0 entry; the create API will enforce this."
  else
    log_info "Route table check: ${vs_rt_id} (Custom) bound to the vswitch, no 0.0.0.0/0 entry."
  fi

  # Constraint 5 continued: the table must be the NEWLY created one for this
  # firewall. Only cross-VPC return routes may pre-exist (official manual step
  # 2); business routes mean this is a production table.
  if [[ "${nd_count:-0}" -gt 0 ]]; then
    local bad_types
    bad_types=$(route_table_disqualifying_types "$nd_types")
    if [[ -n "$bad_types" ]]; then
      log_error "Manual-mode pre-check failed: route table ${vs_rt_id} carries business routes (next hop ${bad_types}: ${nd_samples})."
      log_error "Manual mode requires a NEWLY created clean custom route table - reusing a production table would reroute live traffic through the firewall diversion vswitch. Run 'nat-fw-lifecycle.sh prepare --nat-gateway-id ${nat_gw_id} --region ${region} --vpc-id ${vpc_id}' or create a dedicated table in the console."
      return 1
    fi
    log_warn "Route table ${vs_rt_id} is NOT empty: ${nd_count} pre-existing entry/entries (${nd_samples})."
    log_warn "Proceed ONLY if these are the intended cross-VPC return routes; otherwise bind a freshly created custom route table."
  fi

  # Constraint 6: the diversion vswitch must carry no other cloud resources.
  local eni_count
  eni_count=$(vswitch_attached_eni_count "$region" "$vswitch_id")
  if [[ "$eni_count" == "unknown" ]]; then
    log_warn "Resource check: could not list ENIs of ${vswitch_id} (missing ecs:DescribeNetworkInterfaces permission?). Confirm manually that NO other cloud resources are attached."
  elif [[ "$eni_count" -gt 0 ]]; then
    log_error "Manual-mode pre-check failed: ${eni_count} ENI(s) are attached to ${vswitch_id}. The diversion vswitch must be dedicated and empty (no ECS/ENI/SLB ...)."
    return 1
  else
    log_info "Resource check: no ENI attached to ${vswitch_id}."
  fi

  # Step 5: constraints the CLI cannot verify -> mandatory human checklist
  log_info "Manual-mode pre-check passed: vswitch ${vswitch_id} (${vs_cidr}, zone ${vs_zone}, ${vs_avail} free IPs) satisfies the hard constraints."
  log_warn "MANUAL MODE CHECKLIST - confirm before proceeding (the CLI cannot verify these):"
  log_warn "  1. Route table ${vs_rt_id} is the NEW custom table created for this firewall (${nd_count:-0} pre-existing entry/entries detected)."
  log_warn "  2. No non-ENI resources (e.g. SLB) occupy ${vswitch_id}."
  log_warn "  3. Cross-VPC return routes (if any) have been added to ${vs_rt_id}."
  return 0
}
cmd_create() {
  local NAT_GATEWAY_ID="" REGION="" VPC_ID="" PROXY_NAME=""
  local FIREWALL_SWITCH="close" STRICT_MODE="0" ROUTE_ENTRY_JSON="" VSWITCH_CIDR="" VSWITCH_ID="" YES=false DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --nat-gateway-id) arg_value "--nat-gateway-id" "${@:2}"; NAT_GATEWAY_ID="$2"; shift 2 ;;
      --region) arg_value "--region" "${@:2}"; REGION="$2"; shift 2 ;;
      --vpc-id) arg_value "--vpc-id" "${@:2}"; VPC_ID="$2"; shift 2 ;;
      --proxy-name) arg_value "--proxy-name" "${@:2}"; PROXY_NAME="$2"; shift 2 ;;
      --firewall-switch) arg_value "--firewall-switch" "${@:2}"; FIREWALL_SWITCH="$2"; shift 2 ;;
      --strict-mode) arg_value "--strict-mode" "${@:2}"; STRICT_MODE="$2"; shift 2 ;;
      --route-entry-json) arg_value "--route-entry-json" "${@:2}"; ROUTE_ENTRY_JSON="$2"; shift 2 ;;
      --vswitch-cidr) arg_value "--vswitch-cidr" "${@:2}"; VSWITCH_CIDR="$2"; shift 2 ;;
      --vswitch-id) arg_value "--vswitch-id" "${@:2}"; VSWITCH_ID="$2"; shift 2 ;;
      --yes) YES=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "nat-fw-lifecycle.sh create" \
          "Create a NAT firewall (auto or manual vswitch diversion mode)" \
          "nat-fw-lifecycle.sh create --nat-gateway-id <id> --region <id> --vpc-id <id> --proxy-name <name> (--vswitch-cidr <cidr> | --vswitch-id <id>) --yes [options]" \
          "  --nat-gateway-id <id>       NAT gateway ID (required)
  --region <id>               Region ID (required)
  --vpc-id <id>               VPC ID (required)
  --proxy-name <name>         NAT firewall name, 4~50 chars (required)
  --vswitch-cidr <cidr>       AUTO mode (recommended): CIDR for the auto-created
                              diversion vswitch (e.g. 10.0.3.0/28; must be free
                              inside the VPC)
  --vswitch-id <id>           MANUAL mode: reuse an EXISTING vswitch. Mutually
                              exclusive with --vswitch-cidr. Before running,
                              you MUST create a NEW custom route table and bind
                              it to the vswitch (no 0.0.0.0/0 entry in it).
  --firewall-switch <s>       open or close after creation (default: close)
  --strict-mode <0|1>         Engine mode: 0=loose (default), 1=strict
  --route-entry-json <json>   Manual route entry list JSON, format:
                              [{\"DestinationCidr\":\"0.0.0.0/0\",\"NextHopId\":\"ngw-xx\",
                                \"NextHopType\":\"NatGateway\",\"RouteTableId\":\"vtb-xx\"}]
                              If omitted, routes are auto-discovered via VPC APIs.
  --yes                       Confirm execution (required)
  --dry-run                   Preview CLI command
  --help, -h                  Show this help

  WARNING: Creation takes about 2~5 minutes per bound EIP and modifies VPC
  route tables automatically. Run 'precheck' first. See
  references/nat-prerequisites.md for all prerequisites."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "nat-gateway-id" "$NAT_GATEWAY_ID" || exit 1
  validate_required "region" "$REGION" || exit 1
  validate_required "vpc-id" "$VPC_ID" || exit 1
  validate_required "proxy-name" "$PROXY_NAME" || exit 1
  validate_nat_gateway_id "$NAT_GATEWAY_ID" || exit 1
  validate_region "$REGION" || exit 1
  validate_vpc_id "$VPC_ID" || exit 1
  validate_proxy_name "$PROXY_NAME" || exit 1
  validate_strict_mode "$STRICT_MODE" || exit 1
  if [[ -n "$VSWITCH_CIDR" && -n "$VSWITCH_ID" ]]; then
    log_error "--vswitch-cidr (auto mode) and --vswitch-id (manual mode) are mutually exclusive. Provide exactly one."
    exit 1
  fi
  if [[ -z "$VSWITCH_CIDR" && -z "$VSWITCH_ID" ]]; then
    log_error "Diversion mode not specified: provide --vswitch-cidr <cidr> (auto mode, recommended) or --vswitch-id <id> (manual mode)."
    exit 1
  fi
  [[ -n "$VSWITCH_ID" ]] && { validate_vswitch_id "$VSWITCH_ID" || exit 1; }
  if [[ "$FIREWALL_SWITCH" != "open" && "$FIREWALL_SWITCH" != "close" ]]; then
    log_error "Invalid --firewall-switch: ${FIREWALL_SWITCH}. Must be open or close"
    exit 1
  fi

  # Fail fast before any heavy work:
  #  auto mode   -> verify the new diversion CIDR is free inside the VPC
  #  manual mode -> verify the reused vswitch satisfies the hard constraints
  if [[ -n "$VSWITCH_CIDR" ]]; then
    check_vswitch_cidr "$REGION" "$VPC_ID" "$VSWITCH_CIDR" || exit 1
  else
    check_vswitch_manual "$REGION" "$VPC_ID" "$NAT_GATEWAY_ID" "$VSWITCH_ID" || exit 1
  fi

  # Resolve route entries: manual JSON or auto-discovery
  local route_lines=""
  if [[ -n "$ROUTE_ENTRY_JSON" ]]; then
    command -v python3 &>/dev/null || { log_error "python3 is required to parse --route-entry-json"; exit 1; }
    route_lines=$(json_parse "$ROUTE_ENTRY_JSON" "'\\n'.join('\\t'.join([e['DestinationCidr'], e['NextHopId'], e['NextHopType'], e['RouteTableId']]) for e in d)")
    if [[ -z "$route_lines" ]]; then
      log_error "Failed to parse --route-entry-json. Expected a JSON array of route entry objects."
      exit 1
    fi
  else
    log_info "Auto-discovering route entries pointing to ${NAT_GATEWAY_ID} ..."
    route_lines=$(discover_nat_route_entries "$REGION" "$VPC_ID" "$NAT_GATEWAY_ID") || {
      log_error "Automatic route discovery failed."
      log_error "Fix: pass the route entries manually via --route-entry-json."
      exit 2
    }
  fi

  if [[ -z "$route_lines" ]]; then
    log_error "No route entries found whose next hop is ${NAT_GATEWAY_ID}."
    log_error "The VPC must have a route (usually 0.0.0.0/0) pointing to this NAT gateway."
    log_error "See references/nat-prerequisites.md. You may also pass --route-entry-json manually."
    exit 1
  fi

  # Build CLI args (NatRouteEntryList is a structured repeat list)
  local CLI_ARGS=(
    --NatGatewayId "$NAT_GATEWAY_ID"
    --ProxyName "$PROXY_NAME"
    --RegionNo "$REGION"
    --VpcId "$VPC_ID"
    --FirewallSwitch "$FIREWALL_SWITCH"
    --StrictMode "$STRICT_MODE"
    --Lang zh
  )
  if [[ -n "$VSWITCH_ID" ]]; then
    CLI_ARGS+=(--VswitchAuto "false" --VswitchId "$VSWITCH_ID")
  else
    CLI_ARGS+=(--VswitchAuto "true" --VswitchCidr "$VSWITCH_CIDR")
  fi
  local line idx=1
  while IFS=$'\t' read -r cidr nh_id nh_type rt_id; do
    [[ -z "$cidr" ]] && continue
    CLI_ARGS+=(--NatRouteEntryList.$idx.DestinationCidr "$cidr")
    CLI_ARGS+=(--NatRouteEntryList.$idx.NextHopId "$nh_id")
    CLI_ARGS+=(--NatRouteEntryList.$idx.NextHopType "$nh_type")
    CLI_ARGS+=(--NatRouteEntryList.$idx.RouteTableId "$rt_id")
    idx=$((idx + 1))
  done <<< "$route_lines"

  if [[ $idx -eq 1 ]]; then
    log_error "Failed to assemble route entry list"
    exit 1
  fi
  log_info "Assembled $((idx - 1)) route entry(ies) for NatRouteEntryList"

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} CreateSecurityProxy \\"
    for ((i=0; i<${#CLI_ARGS[@]}; i+=2)); do
      echo "  ${CLI_ARGS[$i]} '${CLI_ARGS[$((i+1))]}' \\"
    done
    exit 0
  fi

  if [[ "$YES" != "true" ]]; then
    log_error "Creating a NAT firewall modifies VPC route tables. Pass --yes to confirm."
    output_error "NotConfirmed" "Operation requires --yes flag to confirm"
    exit 1
  fi

  # Execute with timeout retry. Creation validates CEN route conflicts and
  # can time out on large CENs (service-order evidence). A timeout does NOT
  # prove the request was rejected, so before every retry we verify via
  # DescribeSecurityProxy whether the firewall was created anyway - this
  # guards against duplicate creation.
  log_info "Creating NAT firewall ${PROXY_NAME} ..."
  local response="" exit_code=0 attempt=1 max_attempts=3
  while :; do
    exit_code=0
    response=$(call_cfw_api "CreateSecurityProxy" "${CLI_ARGS[@]}") || exit_code=$?
    [[ $exit_code -eq 0 ]] && break

    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")

    # Only timeout-like failures are retried; anything else is deterministic
    if printf '%s %s' "${err_code:-}" "${err_msg:-}" | grep -qiE 'timeout|timed out|deadline|SocketTimeout|ServerUnreachable|connection reset'; then
      if [[ $attempt -ge $max_attempts ]]; then
        log_error "CreateSecurityProxy timed out after ${max_attempts} attempts. The request may still take effect - poll 'nat-fw-switch.sh query --nat-gateway-id ${NAT_GATEWAY_ID}' before retrying manually."
        diagnose_cfw_error "$err_code" "$err_msg"
        output_error "${err_code:-CreateTimeout}" "${err_msg:-API call timed out}"
        exit 2
      fi
      log_warn "CreateSecurityProxy timed out (attempt ${attempt}/${max_attempts}). Verifying whether the firewall was created anyway ..."
      sleep 5
      local verify_resp="" verify_exit=0 found_id=""
      verify_resp=$(call_cfw_api "DescribeSecurityProxy" --NatGatewayId "$NAT_GATEWAY_ID" --PageNo 1 --PageSize 10 --Lang zh 2>/dev/null) || verify_exit=$?
      if [[ $verify_exit -eq 0 ]]; then
        found_id=$(json_parse "$verify_resp" "(d.get('ProxyList') or [{}])[0].get('ProxyId', '')")
      fi
      if [[ -n "$found_id" ]]; then
        log_info "Found NAT firewall ${found_id} for ${NAT_GATEWAY_ID}: the timed-out request succeeded, no retry needed."
        response="$verify_resp"
        exit_code=0
        break
      fi
      attempt=$((attempt + 1))
      log_info "No firewall created yet - retrying CreateSecurityProxy (attempt ${attempt}/${max_attempts}) ..."
      continue
    fi

    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  done

  local request_id
  request_id=$(extract_api_request_id "$response")
  cat <<EOF
{
  "success": true,
  "action": "create",
  "proxy_name": "${PROXY_NAME}",
  "nat_gateway_id": "${NAT_GATEWAY_ID}",
  "firewall_switch": "${FIREWALL_SWITCH}",
  "request_id": "${request_id:-}",
  "note": "Creation takes about 2~5 minutes per bound EIP. Poll status with 'nat-fw-switch.sh query --nat-gateway-id ${NAT_GATEWAY_ID}' until configuring -> normal."
}
EOF
}

# --- Subcommand: delete ---
# --- Leftover asset check after deletion ---
# Deleting a NAT firewall does NOT reclaim the diversion assets:
#   - manual mode: the user-provided vswitch + its custom route table stay;
#   - auto mode: the Cloud_Firewall_ROUTE_TABLE typically remains as an orphan
#     (unbound) custom route table and can be reused by 'prepare'.
# Read-only scan; degrades silently on missing VPC read permissions.
check_leftover_assets() {
  local region="$1" vpc_id="$2" vswitch_id="$3"
  local rt_resp rt_exit=0

  if [[ -n "$vswitch_id" ]]; then
    log_warn "Leftover asset: diversion vswitch ${vswitch_id} is NOT deleted by the firewall deletion. It can be reused for a future NAT firewall ('prepare' reuses qualifying vswitches), or cleaned up manually in the VPC console."
  fi

  command -v python3 &>/dev/null || return 0
  rt_resp=$(call_vpc_api "DescribeRouteTableList" --RegionId "$region" --VpcId "$vpc_id" --PageNumber 1 --PageSize 50 2>/dev/null) || rt_exit=$?
  if [[ $rt_exit -ne 0 ]]; then
    log_info "Leftover asset scan skipped (missing vpc:DescribeRouteTableList permission or API failed)."
    return 0
  fi

  local orphans orphan_count=0 rt_line rt_id rt_name
  orphans=$(printf '%s' "$rt_resp" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for rt in d.get("RouterTableList", {}).get("RouterTableListType", []):
    if rt.get("RouteTableType") != "Custom":
        continue
    bound = rt.get("VSwitchIds", {}).get("VSwitchId", []) or []
    if bound:
        continue
    print("%s\t%s" % (rt.get("RouteTableId", ""), rt.get("RouteTableName", "")))
' 2>/dev/null) || true

  while IFS=$'\t' read -r rt_id rt_name; do
    [[ -z "$rt_id" ]] && continue
    orphan_count=$((orphan_count + 1))
    if [[ "$rt_name" == *Cloud_Firewall* ]]; then
      log_warn "Leftover asset: orphan custom route table ${rt_id} (${rt_name}) left by a previous auto-mode NAT firewall. Reusable by 'prepare' for the next manual-mode firewall, or delete it in the VPC console."
    else
      log_info "Leftover asset: unbound custom route table ${rt_id} (${rt_name:-no name}) found in VPC ${vpc_id} - reusable by 'prepare'."
    fi
  done <<< "$orphans"

  if [[ $orphan_count -eq 0 ]]; then
    log_info "No orphan custom route tables found in VPC ${vpc_id} right now. Assets may be released asynchronously; re-check later if expected."
  fi
  return 0
}

# DELETION IS DISABLED BY DESIGN.
#
# Closing a NAT firewall (SwitchSecurityProxy --Switch close) and deleting it
# (DeleteSecurityProxy) are fundamentally different: closing only flips the
# switch - the firewall instance, its authorization quota and its diversion
# assets all stay in place, and it can be re-enabled at any time. Deleting
# RELEASES the resource: the auto-mode diversion vswitch is reclaimed, the
# authorization is freed, and the action cannot be undone.
#
# This Skill therefore never calls DeleteSecurityProxy. Users may close
# protection through the switch workflow; releasing the resource must be done
# by the user in the Cloud Firewall console, deliberately and with full context.
# This subcommand stays available only to explain that boundary and to hand out
# the information needed for the console operation (current status + which
# diversion assets would be left behind), all strictly READ-ONLY.
cmd_delete() {
  local PROXY_ID="" YES=false DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --proxy-id) arg_value "--proxy-id" "${@:2}"; PROXY_ID="$2"; shift 2 ;;
      --yes) YES=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "nat-fw-lifecycle.sh delete" \
          "DISABLED: deleting a NAT firewall is out of scope for this Skill" \
          "nat-fw-lifecycle.sh delete --proxy-id <id>   (always refuses; prints guidance)" \
          "  --proxy-id <id>  NAT firewall ID (optional; enables the read-only report)
  --dry-run        Show that no write API would be called
  --help, -h       Show this help

  This command NEVER deletes anything - DeleteSecurityProxy is not called
  anywhere in this Skill.

  Close vs delete:
    close   (supported)  nat-fw-switch.sh disable --proxy-ids <id>
                         Flips the switch off. The firewall instance, its
                         authorization quota and diversion assets remain;
                         protection can be re-enabled later. Causes a 1~2
                         second interruption of long-lived connections.
    delete  (NOT supported here)
                         Releases the firewall resource irreversibly. Do it in
                         the Cloud Firewall console: NAT边界防火墙 -> locate the
                         firewall -> 删除.

  When --proxy-id is given, a READ-ONLY report is printed: the firewall's
  current status and the diversion assets that would NOT be reclaimed
  (manual-mode vswitch, orphan custom route tables), so the console operation
  can be planned properly."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: this command calls NO write API. Deletion is disabled by design."
    echo "# no write API would be called - DeleteSecurityProxy is not used by this Skill"
    echo "# to stop protection instead: aliyun ${CFW_PRODUCT_CODE} SwitchSecurityProxy --ProxyId '${PROXY_ID:-<id>}' --Switch 'close'"
    exit 0
  fi

  log_error "Deleting a NAT firewall is DISABLED in this Skill: it releases the resource irreversibly."
  log_warn "To stop protection without releasing anything, close the switch instead:"
  log_warn "  bash scripts/nat-fw-switch.sh disable --proxy-ids ${PROXY_ID:-<proxy-id>}"
  log_warn "To actually release the firewall, do it yourself in the Cloud Firewall console (NAT边界防火墙 -> 删除)."
  [[ "$YES" == "true" ]] && log_warn "--yes does NOT override this restriction."

  # Read-only context for the console operation (best effort; never blocks).
  local pre_status="" pre_vpc="" pre_region="" pre_vsw="" pre_name=""
  if [[ -n "$PROXY_ID" ]] && validate_proxy_id "$PROXY_ID" 2>/dev/null; then
    local pre_resp pre_exit=0
    pre_resp=$(call_cfw_api "DescribeSecurityProxy" --ProxyId "$PROXY_ID" --PageNo 1 --PageSize 10 --Lang zh 2>/dev/null) || pre_exit=$?
    if [[ $pre_exit -eq 0 ]]; then
      pre_status=$(json_parse "$pre_resp" "(d.get('ProxyList') or [{}])[0].get('Status', '')")
      pre_name=$(json_parse "$pre_resp" "(d.get('ProxyList') or [{}])[0].get('ProxyName', '')")
      pre_vpc=$(json_parse "$pre_resp" "(d.get('ProxyList') or [{}])[0].get('VpcId', '')")
      pre_region=$(json_parse "$pre_resp" "(d.get('ProxyList') or [{}])[0].get('RegionNo', '')")
      pre_vsw=$(json_parse "$pre_resp" "(d.get('ProxyList') or [{}])[0].get('VSwitchId', '')")
    fi
    if [[ -n "$pre_status" ]]; then
      log_info "Current status of ${PROXY_ID} (${pre_name:-unnamed}): ${pre_status}"
      case "$pre_status" in
        normal|opening)
          log_warn "It is currently ENABLED: a console deletion performs close+delete at once and flaps long-lived connections for 1~2 seconds. Closing first during off-peak hours avoids surprises."
          ;;
        closed)
          log_info "It is already closed: releasing it in the console will not affect business traffic."
          ;;
      esac
      if [[ -n "$pre_region" && -n "$pre_vpc" ]]; then
        log_info "Assets that would NOT be reclaimed after a console deletion:"
        check_leftover_assets "$pre_region" "$pre_vpc" "$pre_vsw"
      fi
    else
      log_warn "Could not read ${PROXY_ID} (not found, or missing read permission) - no status report available."
    fi
  fi

  output_error "DeletionDisabled" "Deleting a NAT firewall is not supported by this Skill (it releases the resource irreversibly). Use 'nat-fw-switch.sh disable' to close protection, or delete it yourself in the Cloud Firewall console."
  exit 1
}

# --- Subcommand: update ---

# Post-update verification (guards against silent API success).
# UpdateSecurityProxy returns success even for unknown ProxyIds, so the API
# response alone proves nothing. This function re-reads the firewall state:
#   Step A: DescribeSecurityProxy  -> existence check + RegionNo discovery
#   Step B: DescribeNatFirewallList -> field comparison (ProxyName / StrictMode)
# NOTE: DescribeSecurityProxy does NOT return StrictMode; only
# DescribeNatFirewallList does (verified 2026-08-10).
# Prints a verification result JSON to stdout.
# Returns 0 if verified, 1 if verification failed / inconclusive.
verify_update_result() {
  local proxy_id="$1" expected_name="$2" expected_strict="$3" attempt

  sleep 3

  # Step A: existence check + region discovery (retry to tolerate sync delay)
  local proxy_resp="" proxy_exit region_no=""
  for attempt in 1 2 3; do
    proxy_exit=0
    proxy_resp=$(call_cfw_api "DescribeSecurityProxy" --ProxyId "$proxy_id" --PageNo 1 --PageSize 10 --Lang zh) || proxy_exit=$?
    if [[ $proxy_exit -eq 0 ]]; then
      region_no=$(json_parse "$proxy_resp" "(d.get('ProxyList') or [{}])[0].get('RegionNo', '')")
      [[ -n "$region_no" ]] && break
    fi
    log_warn "Verification attempt ${attempt}: proxy not visible yet, retrying ..."
    sleep 5
  done

  if [[ -z "$region_no" ]]; then
    cat <<EOF
{
  "verified": false,
  "reason": "proxy_not_found",
  "detail": "UpdateSecurityProxy reported success but ${proxy_id} does not exist. The API silently accepts unknown ProxyIds - the update was NOT applied.",
  "request_id": "$(extract_api_request_id "$proxy_resp")"
}
EOF
    return 1
  fi

  # Step B: field comparison via DescribeNatFirewallList (StrictMode source)
  local list_resp="" list_exit=0 actual_name="" actual_strict=""
  for attempt in 1 2 3; do
    list_exit=0
    list_resp=$(call_cfw_api "DescribeNatFirewallList" --RegionNo "$region_no") || list_exit=$?
    if [[ $list_exit -eq 0 ]]; then
      local fields
      fields=$(json_parse "$list_resp" "'\\t'.join([(f.get('ProxyName') or f.get('FirewallName') or ''), str(f.get('StrictMode', ''))]) for f in d.get('NatFirewallList', []) if f.get('ProxyId') == '$proxy_id' or []")
      if [[ -n "$fields" ]]; then
        actual_name=$(printf '%s' "$fields" | cut -f1)
        actual_strict=$(printf '%s' "$fields" | cut -f2)
      fi
    fi
    # Name is the primary signal; StrictMode may lag one sync cycle
    if [[ -n "$actual_name" && "$actual_name" == "$expected_name" ]]; then
      if [[ -z "$expected_strict" || "$actual_strict" == "$expected_strict" ]]; then
        break
      fi
    fi
    sleep 5
  done

  if [[ $list_exit -ne 0 ]]; then
    cat <<EOF
{
  "verified": false,
  "reason": "verify_api_failed",
  "detail": "DescribeNatFirewallList failed (check yundun-cloudfirewall:DescribeNatFirewallList permission). The update API call itself succeeded; verify manually in the console.",
  "request_id": "$(extract_api_request_id "$list_resp")"
}
EOF
    return 1
  fi

  if [[ -z "$actual_name" ]]; then
    cat <<EOF
{
  "verified": false,
  "reason": "proxy_not_in_region_list",
  "detail": "Proxy ${proxy_id} exists (Step A) but was not found in DescribeNatFirewallList for ${region_no}. Verify manually."
}
EOF
    return 1
  fi

  local mismatches=()
  [[ "$actual_name" != "$expected_name" ]] && mismatches+=("ProxyName expected '${expected_name}' actual '${actual_name}'")
  if [[ -n "$expected_strict" && "$actual_strict" != "$expected_strict" ]]; then
    mismatches+=("StrictMode expected '${expected_strict}' actual '${actual_strict}'")
  fi

  if [[ ${#mismatches[@]} -gt 0 ]]; then
    cat <<EOF
{
  "verified": false,
  "reason": "field_mismatch",
  "detail": "$(IFS='; '; echo "${mismatches[*]}")",
  "proxy_name": "${actual_name}",
  "strict_mode": "${actual_strict}"
}
EOF
    return 1
  fi

  cat <<EOF
{
  "verified": true,
  "proxy_name": "${actual_name}",
  "strict_mode": "${actual_strict}"
}
EOF
  return 0
}

cmd_update() {
  local PROXY_ID="" PROXY_NAME="" STRICT_MODE="" SKIP_VERIFY=false DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --proxy-id) arg_value "--proxy-id" "${@:2}"; PROXY_ID="$2"; shift 2 ;;
      --proxy-name) arg_value "--proxy-name" "${@:2}"; PROXY_NAME="$2"; shift 2 ;;
      --strict-mode) arg_value "--strict-mode" "${@:2}"; STRICT_MODE="$2"; shift 2 ;;
      --skip-verify) SKIP_VERIFY=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "nat-fw-lifecycle.sh update" \
          "Rename a NAT firewall or change its engine strict mode" \
          "nat-fw-lifecycle.sh update --proxy-id <id> [--proxy-name <name>] [--strict-mode 0|1]" \
          "  --proxy-id <id>      NAT firewall ID (required)
  --proxy-name <name>  New name, 4~50 chars (API requires this field;
                       pass the current name if only changing strict mode)
  --strict-mode <0|1>  Engine mode: 0=loose, 1=strict
  --skip-verify        Skip built-in post-update verification (not recommended;
                       UpdateSecurityProxy silently succeeds on unknown ProxyIds)
  --dry-run            Preview CLI command
  --help, -h           Show this help

  After the API call, the script automatically verifies the change:
  existence via DescribeSecurityProxy, then ProxyName/StrictMode via
  DescribeNatFirewallList. Exit code 0 = change verified, 2 = failed."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "proxy-id" "$PROXY_ID" || exit 1
  validate_proxy_id "$PROXY_ID" || exit 1
  [[ -n "$PROXY_NAME" ]] && { validate_proxy_name "$PROXY_NAME" || exit 1; }
  [[ -n "$STRICT_MODE" ]] && { validate_strict_mode "$STRICT_MODE" || exit 1; }

  if [[ -z "$PROXY_NAME" && -z "$STRICT_MODE" ]]; then
    log_error "Nothing to update: provide --proxy-name and/or --strict-mode"
    exit 1
  fi
  if [[ -z "$PROXY_NAME" ]]; then
    log_error "The UpdateSecurityProxy API requires ProxyName. Query the current name via 'nat-fw-switch.sh query --proxy-id ${PROXY_ID}' and pass it back with --proxy-name."
    exit 1
  fi

  local CLI_ARGS=(--ProxyId "$PROXY_ID" --ProxyName "$PROXY_NAME" --Lang zh)
  [[ -n "$STRICT_MODE" ]] && CLI_ARGS+=(--StrictMode "$STRICT_MODE")

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} UpdateSecurityProxy \\"
    for ((i=0; i<${#CLI_ARGS[@]}; i+=2)); do
      echo "  ${CLI_ARGS[$i]} '${CLI_ARGS[$((i+1))]}' \\"
    done
    exit 0
  fi

  log_info "Updating NAT firewall ${PROXY_ID} ..."
  local response exit_code=0
  response=$(call_cfw_api "UpdateSecurityProxy" "${CLI_ARGS[@]}") || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  local request_id
  request_id=$(extract_api_request_id "$response")
  log_info "UpdateSecurityProxy accepted (RequestId: ${request_id:-unknown}). Note: this API reports success even for unknown ProxyIds - verifying ..."

  if [[ "$SKIP_VERIFY" == "true" ]]; then
    log_warn "--skip-verify set: skipping built-in verification"
    cat <<EOF
{
  "success": true,
  "action": "update",
  "proxy_id": "${PROXY_ID}",
  "request_id": "${request_id:-}",
  "verified": false,
  "note": "Verification skipped (--skip-verify). Confirm manually via DescribeNatFirewallList."
}
EOF
    exit 0
  fi

  local verify_json verify_exit=0
  verify_json=$(verify_update_result "$PROXY_ID" "$PROXY_NAME" "$STRICT_MODE") || verify_exit=$?

  if [[ $verify_exit -ne 0 ]]; then
    log_error "Post-update verification FAILED. The update may NOT have taken effect."
    output_error "VerifyFailed" "$verify_json"
    exit 2
  fi

  log_info "Verification passed: change confirmed on the live firewall."
  cat <<EOF
{
  "success": true,
  "action": "update",
  "proxy_id": "${PROXY_ID}",
  "request_id": "${request_id:-}",
  "verification": ${verify_json}
}
EOF
}

# --- Subcommand: assess ---

# Enumerate all vswitches of a VPC (paginated).
# Output TSV lines: VSwitchId<TAB>Name<TAB>ZoneId<TAB>CidrBlock<TAB>AvailableIpAddressCount<TAB>RouteTableId<TAB>RouteTableType
# Returns 1 on API failure (e.g. missing vpc:DescribeVSwitches permission).
enumerate_vswitches() {
  local region="$1" vpc_id="$2"
  local page=1 out=""
  while :; do
    local vs_resp vs_exit=0
    vs_resp=$(call_vpc_api "DescribeVSwitches" --RegionId "$region" --VpcId "$vpc_id" --PageNumber "$page" --PageSize 50) || vs_exit=$?
    if [[ $vs_exit -ne 0 ]]; then
      return 1
    fi
    local rows
    rows=$(json_parse "$vs_resp" "'\\n'.join('\\t'.join([v.get('VSwitchId',''), str(v.get('VSwitchName','')).replace('\\t',' ').replace('\\n',' '), v.get('ZoneId',''), v.get('CidrBlock',''), str(v.get('AvailableIpAddressCount',0)), v.get('RouteTable',{}).get('RouteTableId',''), v.get('RouteTable',{}).get('RouteTableType','')]) for v in d.get('VSwitches',{}).get('VSwitch',[]))")
    [[ -n "$rows" ]] && out+="${rows}"$'\n'
    local vs_total
    vs_total=$(json_parse "$vs_resp" "d.get('TotalCount', 0)")
    if [[ -z "$vs_total" || $((page * 50)) -ge "$vs_total" ]]; then
      break
    fi
    page=$((page + 1))
  done
  printf '%s' "$out"
}

# Read the VPC primary + secondary CIDRs (DescribeVpcAttribute -> DescribeVpcs fallback).
# Output: "primary<TAB>secondary1,secondary2" (fields empty on failure).
fetch_vpc_cidrs() {
  local region="$1" vpc_id="$2"
  local vpc_resp vpc_exit=0 vpc_cidr="" secondary=""
  vpc_resp=$(call_vpc_api "DescribeVpcAttribute" --RegionId "$region" --VpcId "$vpc_id" 2>/dev/null) || vpc_exit=$?
  if [[ $vpc_exit -eq 0 ]]; then
    vpc_cidr=$(json_parse "$vpc_resp" "d.get('CidrBlock', '')")
    secondary=$(json_parse "$vpc_resp" "','.join(d.get('SecondaryCidrBlocks', {}).get('SecondaryCidrBlock', []))")
  else
    vpc_exit=0
    vpc_resp=$(call_vpc_api "DescribeVpcs" --RegionId "$region" --VpcId "$vpc_id" 2>/dev/null) || vpc_exit=$?
    if [[ $vpc_exit -eq 0 ]]; then
      vpc_cidr=$(json_parse "$vpc_resp" "(d.get('Vpcs', {}).get('Vpc') or [{}])[0].get('CidrBlock', '')")
      secondary=$(json_parse "$vpc_resp" "','.join((d.get('Vpcs', {}).get('Vpc') or [{}])[0].get('SecondaryCidrBlocks', {}).get('SecondaryCidrBlock', []))")
    fi
  fi
  printf '%s\t%s' "$vpc_cidr" "$secondary"
}

# Compare custom route entries across the VPC's route tables.
# Background: when a VPC has multiple route tables, NAT firewall creation /
# switch-on validates that all of them carry identical CUSTOM entries;
# mismatched tables (typically extra VpnGateway / peer / prefix-list routes)
# fail server-side with ErrorNatCustomRouteEntryDifferent. Service-order
# analysis shows this is the top cause of auto-mode failure. WHY: auto mode
# builds the firewall's diversion-vswitch route table from the VPC's custom
# entries; with inconsistent tables it would inherit entries (vppeer /
# vpngateway) that some business vswitches deliberately do not want, and
# since all diverted traffic forwards through the firewall vswitch, those
# entries would diffuse routes into traffic paths never designed for them.
# Detect it client-side so assess can warn before creation is attempted.
# SCOPE: the server validates the route tables that actually PARTICIPATE in the
# diversion, i.e. those holding an entry whose next hop is the NAT gateway (the
# console lists exactly those entries under "选择路由表"). Tables with no route to
# the gateway are never diverted, so comparing them produces FALSE POSITIVES.
# Pass the diversion set via <scope_csv> to compare only those tables; without
# it, every route table of the VPC is compared (informational, may over-warn).
# This also explains the real-world workaround "缩小开墙范围": fewer diverted
# tables means fewer tables to compare.
# Comparison is capped at the first 10 route tables and 3 entry pages each.
# Output (stdout): "consistent:<tables>" | "inconsistent:<detail>" | "unknown:<reason>"
check_route_entry_consistency() {
  local region="$1" vpc_id="$2" scope_csv="${3:-}"

  command -v python3 &>/dev/null || { echo "unknown:python3 unavailable"; return 0; }

  # Step 1: determine which route tables to compare - the diversion set when
  # provided, otherwise every route table of the VPC (paginated).
  local rt_ids=() page=1
  if [[ -n "$scope_csv" ]]; then
    local old_ifs_scope="$IFS"
    IFS=','; rt_ids=($scope_csv); IFS="$old_ifs_scope"
  else
    while :; do
      local rt_resp rt_exit=0
      rt_resp=$(call_vpc_api "DescribeRouteTableList" --RegionId "$region" --VpcId "$vpc_id" --PageNumber "$page" --PageSize 50 2>/dev/null) || rt_exit=$?
      if [[ $rt_exit -ne 0 ]]; then
        echo "unknown:DescribeRouteTableList failed"
        return 0
      fi
      local ids_in_page
      ids_in_page=$(json_parse "$rt_resp" "'\\n'.join(t['RouteTableId'] for t in d.get('RouterTableList', {}).get('RouterTableListType', []))")
      if [[ -n "$ids_in_page" ]]; then
        while IFS= read -r rt_id; do
          [[ -n "$rt_id" ]] && rt_ids+=("$rt_id")
        done <<< "$ids_in_page"
      fi
      local total_count
      total_count=$(json_parse "$rt_resp" "d.get('TotalCount', 0)")
      if [[ -z "$total_count" || $((page * 50)) -ge "$total_count" ]]; then break; fi
      page=$((page + 1))
    done
  fi

  local table_count=${#rt_ids[@]}
  if [[ $table_count -lt 2 ]]; then
    echo "consistent:${table_count}"
    return 0
  fi
  # Cap API cost: compare at most the first 10 tables
  if [[ $table_count -gt 10 ]]; then
    rt_ids=("${rt_ids[@]:0:10}")
  fi

  # Step 2: fetch custom entries of each table and compare against the first.
  # NOTE: the "first table" must be tracked by INDEX, not by whether ref_sig
  # is empty - a table with ZERO custom entries yields an empty signature,
  # and an emptiness test would silently reset the reference on every later
  # table, so no comparison would ever run (always reports consistent).
  local ref_rt="${rt_ids[0]}" ref_sig="" ref_set=false sig="" mismatched=""
  local rt_id
  for rt_id in "${rt_ids[@]}"; do
    local entries_raw="" next_token="" loop_guard=0 ent_resp ent_exit=0
    while :; do
      loop_guard=$((loop_guard + 1)); [[ $loop_guard -gt 3 ]] && break
      ent_exit=0
      if [[ -n "$next_token" ]]; then
        ent_resp=$(call_vpc_api "DescribeRouteEntryList" --RegionId "$region" --RouteTableId "$rt_id" --RouteEntryType Custom --MaxResult 100 --NextToken "$next_token" 2>/dev/null) || ent_exit=$?
      else
        ent_resp=$(call_vpc_api "DescribeRouteEntryList" --RegionId "$region" --RouteTableId "$rt_id" --RouteEntryType Custom --MaxResult 100 2>/dev/null) || ent_exit=$?
      fi
      if [[ $ent_exit -ne 0 ]]; then
        echo "unknown:DescribeRouteEntryList failed for ${rt_id}"
        return 0
      fi
      local chunk
      chunk=$(json_parse "$ent_resp" "'\\n'.join('\\t'.join([e.get('DestinationCidrBlock',''), ','.join(sorted(set((n.get('NextHopType','') + ':' + n.get('NextHopId','')) for n in e.get('NextHops', {}).get('NextHop', []))))]) for e in d.get('RouteEntrys', {}).get('RouteEntry', []))")
      [[ -n "$chunk" ]] && entries_raw+="${chunk}"$'\n'
      next_token=$(json_parse "$ent_resp" "d.get('NextToken', '') or ''")
      [[ -z "$next_token" ]] && break
    done
    # Normalized signature: sorted unique "cidr<TAB>nexthops" lines
    sig=$(printf '%s' "$entries_raw" | python3 -c '
import sys
print("\n".join(sorted(set(l.rstrip("\n") for l in sys.stdin if l.strip()))))
') || { echo "unknown:signature build failed for ${rt_id}"; return 0; }

    if [[ "$ref_set" == "false" ]]; then
      ref_sig="$sig"
      ref_set=true
      continue
    fi
    if [[ "$sig" != "$ref_sig" ]]; then
      local diff_out
      diff_out=$(printf '%s\n---SEP---\n%s\n' "$ref_sig" "$sig" | python3 -c '
import sys
data = sys.stdin.read().split("---SEP---")
a = set(l for l in data[0].splitlines() if l.strip())
b = set(l for l in data[1].splitlines() if l.strip())
samples = sorted((a - b) | (b - a))[:2]
print("; ".join(s.replace("\t", " -> ") for s in samples))
') || diff_out=""
      mismatched+="${mismatched:+, }${rt_id} differs from ${ref_rt}${diff_out:+ (e.g. ${diff_out})}"
    fi
  done

  if [[ -n "$mismatched" ]]; then
    echo "inconsistent:${mismatched}"
  else
    echo "consistent:${#rt_ids[@]}"
  fi
}

# Resolve a REAL resource quota via Quotas Center (GetProductQuota).
# Prints the quota limit on stdout. Returns non-zero when the permission is
# missing or the quota item is unknown - callers must then treat the limit as
# UNKNOWN, never fall back to the documentation default (customers may have
# raised their quotas; assuming defaults produces false blockers).
resolve_quota_limit() {
  local product_code="$1" action_code="$2"
  local q_resp q_exit=0
  q_resp=$(call_quotas_api "get-product-quota" --product-code "$product_code" --quota-action-code "$action_code" 2>/dev/null) || q_exit=$?
  [[ $q_exit -ne 0 ]] && return 1
  local q_val
  q_val=$(json_parse "$q_resp" "d.get('Quota', {}).get('TotalQuota', '')")
  [[ -z "$q_val" || "$q_val" == "None" ]] && return 1
  printf '%s' "$q_val"
}

# Count CUSTOM route tables of a VPC (the quota vpc_quota_route_tables_num,
# Quotas Center action code vpc/q_e1mq5l, covers custom tables only; the
# system route table is free).
count_custom_route_tables() {
  local region="$1" vpc_id="$2"
  local page=1 custom_count=0
  while :; do
    local rt_resp rt_exit=0
    rt_resp=$(call_vpc_api "DescribeRouteTableList" --RegionId "$region" --VpcId "$vpc_id" --PageNumber "$page" --PageSize 50 2>/dev/null) || rt_exit=$?
    [[ $rt_exit -ne 0 ]] && return 1
    local page_custom
    page_custom=$(json_parse "$rt_resp" "sum(1 for t in d.get('RouterTableList', {}).get('RouterTableListType', []) if t.get('RouteTableType') == 'Custom')")
    custom_count=$((custom_count + ${page_custom:-0}))
    local rt_total
    rt_total=$(json_parse "$rt_resp" "d.get('TotalCount', 0)")
    if [[ -z "$rt_total" || $((page * 50)) -ge "$rt_total" ]]; then
      break
    fi
    page=$((page + 1))
  done
  printf '%s' "$custom_count"
}

# Count custom route entries whose next hop is a VpnGateway, per route table.
# Emits "<rt_id>\t<count>" lines covering every CUSTOM table of the VPC, so
# callers can sum the whole VPC (quota vpc_quota_vpn_custom_route_entry,
# Quotas Center action code vpc/q_62f05n, is a VPC-level limit) or just the
# diversion scope. Returns 1 when tables cannot be listed; a per-table entry
# query failure emits "<rt_id>\tunknown".
count_vpn_route_entries_per_table() {
  local region="$1" vpc_id="$2"
  local rt_ids=() page=1
  while :; do
    local rt_resp rt_exit=0
    rt_resp=$(call_vpc_api "DescribeRouteTableList" --RegionId "$region" --VpcId "$vpc_id" --PageNumber "$page" --PageSize 50 2>/dev/null) || rt_exit=$?
    [[ $rt_exit -ne 0 ]] && return 1
    local ids_page
    ids_page=$(json_parse "$rt_resp" "'\\n'.join(t['RouteTableId'] for t in d.get('RouterTableList', {}).get('RouterTableListType', []) if t.get('RouteTableType') == 'Custom')")
    if [[ -n "$ids_page" ]]; then
      while IFS= read -r rid; do
        [[ -n "$rid" ]] && rt_ids+=("$rid")
      done <<< "$ids_page"
    fi
    local rt_total
    rt_total=$(json_parse "$rt_resp" "d.get('TotalCount', 0)")
    if [[ -z "$rt_total" || $((page * 50)) -ge "$rt_total" ]]; then
      break
    fi
    page=$((page + 1))
  done

  local rt_id
  # bash 3.2 (the macOS default) treats "${arr[@]}" on an EMPTY array as an
  # unbound variable under `set -u` and aborts. Without the guarded expansion
  # below, a VPC with no custom route tables made this function fail, so the
  # caller could not distinguish a genuine 0 from a failed scan.
  for rt_id in ${rt_ids[@]+"${rt_ids[@]}"}; do
    local vpn_count=0 next_token="" pg ent_resp ent_exit=0
    for pg in 1 2 3; do
      ent_exit=0
      if [[ -n "$next_token" ]]; then
        ent_resp=$(call_vpc_api "DescribeRouteEntryList" --RegionId "$region" --RouteTableId "$rt_id" --RouteEntryType Custom --MaxResult 100 --NextToken "$next_token" 2>/dev/null) || ent_exit=$?
      else
        ent_resp=$(call_vpc_api "DescribeRouteEntryList" --RegionId "$region" --RouteTableId "$rt_id" --RouteEntryType Custom --MaxResult 100 2>/dev/null) || ent_exit=$?
      fi
      if [[ $ent_exit -ne 0 ]]; then
        printf '%s\tunknown\n' "$rt_id"
        vpn_count=-1
        break
      fi
      local page_vpn
      page_vpn=$(json_parse "$ent_resp" "sum(1 for e in d.get('RouteEntrys', {}).get('RouteEntry', []) for n in e.get('NextHops', {}).get('NextHop', []) if n.get('NextHopType') == 'VpnGateway')")
      vpn_count=$((vpn_count + ${page_vpn:-0}))
      next_token=$(json_parse "$ent_resp" "d.get('NextToken', '') or ''")
      [[ -z "$next_token" ]] && break
    done
    [[ "$vpn_count" -ge 0 ]] && printf '%s\t%s\n' "$rt_id" "$vpn_count"
  done
  # Reaching this point means the scan itself succeeded - possibly with zero
  # rows, which is a legitimate "0 VPN routes" answer. Return success explicitly
  # so the caller does not inherit the exit code of the last conditional above.
  return 0
}

# Read-only planning step: inventory NAT gateways without a NAT firewall and
# recommend the best diversion mode per gateway:
#   - quota and already-protected gateways (DescribeSecurityProxy)
#   - per unprotected gateway: zone / EIP count / SNAT / DNAT status
#   - per VPC: free /28 candidates (auto mode) and eligible existing vswitches
#     bound to a clean custom route table (manual mode)
#   - per VPC: custom route entry consistency across route tables
#   - per VPC/gateway: post-creation quota projection (route tables,
#     vswitches, VPN custom routes, SNAT entries) resolved via Quotas Center
# Emits a JSON report; exit 0 on success, 2 on hard API failure.
cmd_assess() {
  local REGION="" VPC_ID="" NAT_GATEWAY_ID="" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --region) arg_value "--region" "${@:2}"; REGION="$2"; shift 2 ;;
      --vpc-id) arg_value "--vpc-id" "${@:2}"; VPC_ID="$2"; shift 2 ;;
      --nat-gateway-id) arg_value "--nat-gateway-id" "${@:2}"; NAT_GATEWAY_ID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "nat-fw-lifecycle.sh assess" \
          "Assess how to enable NAT firewall protection (read-only planning)" \
          "nat-fw-lifecycle.sh assess --region <id> [--vpc-id <id>] [--nat-gateway-id <id>]" \
          "  --region <id>  Region ID (required)
  --vpc-id <id>   Optional: only assess NAT gateways of this VPC
  --nat-gateway-id <id>  Optional: deep single-gateway evaluation. Adds the
                         server-side pre-check and emits a ready-to-execute
                         'plan' object (mode, parameters, risks, command).
  --dry-run       Show the APIs that would be called
  --help, -h      Show this help

  Lists NAT gateways that have no NAT firewall yet, analyzes each VPC
  (free /28 CIDRs, existing vswitches, custom route tables) and recommends
  auto mode (--vswitch-cidr) or manual mode (--vswitch-id) per gateway.
  Read-only: safe to run at any time."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "region" "$REGION" || exit 1
  validate_region "$REGION" || exit 1
  [[ -n "$VPC_ID" ]] && { validate_vpc_id "$VPC_ID" || exit 1; }
  [[ -n "$NAT_GATEWAY_ID" ]] && { validate_nat_gateway_id "$NAT_GATEWAY_ID" || exit 1; }

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: assess would call (all read-only)"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeNatFirewallQuota"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeSecurityProxy --PageNo 1 --PageSize 50"
    echo "aliyun Vpc DescribeNatGateways --RegionId '${REGION}' [--VpcId '${VPC_ID:-}']"
    echo "aliyun Vpc DescribeVpcAttribute / DescribeVpcs --VpcId <each VPC>"
    echo "aliyun Vpc DescribeVSwitches --VpcId <each VPC>"
    echo "aliyun Vpc DescribeForwardTableEntries --ForwardTableId <per gateway>"
    echo "aliyun Vpc DescribeRouteTableList + DescribeRouteEntryList --VpcId <each VPC>  (route-entry consistency)"
    echo "aliyun Vpc DescribeRouteEntryList --RouteTableId <per manual candidate>"
    echo "aliyun quotas get-product-quota --product-code vpc --quota-action-code q_e1mq5l (vpc_quota_route_tables_num) / q_b7klmn (vpc_quota_vswitches_num) / q_62f05n (vpc_quota_vpn_custom_route_entry)"
    echo "aliyun quotas get-product-quota --product-code nat --quota-action-code q_fwiygs (natgw_quota_snat_entry_num)"
    exit 0
  fi

  command -v python3 &>/dev/null || { log_error "python3 is required for assess"; exit 1; }

  # Step 1: quota
  local total_count="" used_count=""
  local quota_resp quota_exit=0
  quota_resp=$(call_cfw_api "DescribeNatFirewallQuota" --Lang zh) || quota_exit=$?
  if [[ $quota_exit -eq 0 ]]; then
    total_count=$(json_parse "$quota_resp" "d.get('TotalCount', 0)")
    used_count=$(json_parse "$quota_resp" "d.get('UsedCount', 0)")
    if [[ -n "$total_count" && -n "$used_count" && "$used_count" -ge "$total_count" ]]; then
      log_warn "Quota exhausted (${used_count}/${total_count}): purchase more NAT firewall authorizations before creating."
    fi
  else
    log_warn "Failed to query NAT firewall quota; continuing without it."
  fi

  # Step 1b: resolve the REAL resource quotas for the post-creation quota
  # projection. Quotas Center is the only trusted source: documentation
  # defaults must NOT be substituted because customers may have raised their
  # quotas, and a guessed default produces false blockers (hallucination).
  # When the quotas permission is missing the projection degrades to
  # "unknown" and the report tells the user exactly which permission to add.
  local QUOTA_RT_LIMIT="" QUOTA_VSW_LIMIT="" QUOTA_VPN_LIMIT="" QUOTA_SNAT_LIMIT=""
  local QUOTAS_DENIED=false
  QUOTA_RT_LIMIT=$(resolve_quota_limit "vpc" "q_e1mq5l") || QUOTA_RT_LIMIT=""
  QUOTA_VSW_LIMIT=$(resolve_quota_limit "vpc" "q_b7klmn") || QUOTA_VSW_LIMIT=""
  QUOTA_VPN_LIMIT=$(resolve_quota_limit "vpc" "q_62f05n") || QUOTA_VPN_LIMIT=""
  QUOTA_SNAT_LIMIT=$(resolve_quota_limit "nat" "q_fwiygs") || QUOTA_SNAT_LIMIT=""
  if [[ -z "$QUOTA_RT_LIMIT$QUOTA_VSW_LIMIT$QUOTA_VPN_LIMIT$QUOTA_SNAT_LIMIT" ]]; then
    QUOTAS_DENIED=true
    log_warn "No resource quota could be resolved (missing quotas:GetProductQuota permission?). The post-creation quota projection will be 'unknown' - grant the permission per references/ram-policies.md and re-run assess."
  fi

  # Step 2: existing NAT firewalls (protected gateways), paginated via PageNo
  local protected_rows="" page=1
  while :; do
    local sp_resp sp_exit=0
    sp_resp=$(call_cfw_api "DescribeSecurityProxy" --PageNo "$page" --PageSize 50 --Lang zh) || sp_exit=$?
    if [[ $sp_exit -ne 0 ]]; then
      local sp_err
      sp_err=$(extract_api_error_code "$sp_resp")
      log_error "Failed to query existing NAT firewalls (DescribeSecurityProxy): ${sp_err:-unknown}"
      output_error "${sp_err:-UnknownError}" "DescribeSecurityProxy failed"
      exit 2
    fi
    local prows pline
    prows=$(json_parse "$sp_resp" "'\\n'.join('\\t'.join([p.get('NatGatewayId',''), p.get('ProxyId',''), str(p.get('ProxyName','')).replace('\\t',' '), p.get('Status','')]) for p in d.get('ProxyList', []))")
    if [[ -n "$prows" ]]; then
      while IFS= read -r pline; do
        [[ -n "$pline" ]] && protected_rows+="P"$'\t'"${pline}"$'\n'
      done <<< "$prows"
    fi
    local sp_total
    sp_total=$(json_parse "$sp_resp" "d.get('TotalCount', 0)")
    if [[ -z "$sp_total" || $((page * 50)) -ge "$sp_total" ]]; then
      break
    fi
    page=$((page + 1))
  done

  # Step 3: enumerate NAT gateways (paginated)
  local gw_rows="" page2=1
  while :; do
    local gw_resp gw_exit=0
    if [[ -n "$VPC_ID" ]]; then
      gw_resp=$(call_vpc_api "DescribeNatGateways" --RegionId "$REGION" --VpcId "$VPC_ID" --PageNumber "$page2" --PageSize 50) || gw_exit=$?
    else
      gw_resp=$(call_vpc_api "DescribeNatGateways" --RegionId "$REGION" --PageNumber "$page2" --PageSize 50) || gw_exit=$?
    fi
    if [[ $gw_exit -ne 0 ]]; then
      local gw_err
      gw_err=$(extract_api_error_code "$gw_resp")
      log_error "Failed to list NAT gateways (DescribeNatGateways): ${gw_err:-unknown}"
      output_error "${gw_err:-UnknownError}" "DescribeNatGateways failed (missing vpc:DescribeNatGateways permission?)"
      exit 2
    fi
    local grows
    grows=$(json_parse "$gw_resp" "'\\n'.join('\\t'.join([g['NatGatewayId'], str(g.get('Name','')).replace('\\t',' '), g.get('VpcId',''), g.get('NatGatewayPrivateInfo',{}).get('IzNo',''), g.get('Status',''), str(len(g.get('IpLists',{}).get('IpList',[]))), str(len(g.get('SnatTableIds',{}).get('SnatTableId',[]))), ','.join(g.get('ForwardTableIds',{}).get('ForwardTableId',[])), ','.join(g.get('SnatTableIds',{}).get('SnatTableId',[]))]) for g in d.get('NatGateways',{}).get('NatGateway',[]))")
    [[ -n "$grows" ]] && gw_rows+="${grows}"$'\n'
    local gw_total
    gw_total=$(json_parse "$gw_resp" "d.get('TotalCount', 0)")
    if [[ -z "$gw_total" || $((page2 * 50)) -ge "$gw_total" ]]; then
      break
    fi
    page2=$((page2 + 1))
  done

  # Step 4: per-gateway assessment (skip gateways that already have a firewall)
  local assess_rows="" CONSISTENCY_CACHE="" QUOTA_CACHE="" TARGET_PROTECTED=""
  local gw_id gw_name gw_vpc gw_zone gw_status gw_eips gw_snat_tables gw_fwd_ids gw_snat_ids
  while IFS=$'\t' read -r gw_id gw_name gw_vpc gw_zone gw_status gw_eips gw_snat_tables gw_fwd_ids gw_snat_ids; do
    [[ -z "$gw_id" ]] && continue
    # Single-gateway mode: ignore everything else.
    if [[ -n "$NAT_GATEWAY_ID" && "$gw_id" != "$NAT_GATEWAY_ID" ]]; then
      continue
    fi
    if printf '%s' "$protected_rows" | cut -f2 | grep -qx "$gw_id"; then
      log_info "Skipping ${gw_id} (${gw_name}): already protected by a NAT firewall"
      [[ -n "$NAT_GATEWAY_ID" ]] && TARGET_PROTECTED="$gw_id"
      continue
    fi
    log_info "Assessing unprotected NAT gateway ${gw_id} (${gw_name}) in VPC ${gw_vpc} ..."

    local blockers="" notes=""
    [[ "$gw_eips" == "0" ]] && blockers+="no EIP bound (bind at least 1 EIP first);"
    [[ "$gw_snat_tables" == "0" ]] && blockers+="no SNAT table (configure SNAT entries first);"

    # SNAT ENTRY count: a SNAT table that exists but holds 0 entries blocks
    # creation exactly like a missing table (server-side pre-check failure
    # "NAT网关未配置SNAT条目"). Count actual entries so assess matches the
    # precheck verdict. Degrades to a note without vpc:DescribeSnatTableEntries.
    local snat_entry_count=-1
    if [[ "$gw_snat_tables" != "0" ]]; then
      local snat_arr old_ifs_snat="$IFS" stb_id stb_resp stb_exit=0 stb_cnt
      if [[ -n "$gw_snat_ids" ]]; then
        snat_entry_count=0
        IFS=','; snat_arr=($gw_snat_ids); IFS="$old_ifs_snat"
        for stb_id in "${snat_arr[@]}"; do
          [[ -z "$stb_id" ]] && continue
          stb_exit=0
          stb_resp=$(call_vpc_api "DescribeSnatTableEntries" --RegionId "$REGION" --SnatTableId "$stb_id" --PageSize 1 2>/dev/null) || stb_exit=$?
          if [[ $stb_exit -eq 0 ]]; then
            stb_cnt=$(json_parse "$stb_resp" "d.get('TotalCount', 0)")
            snat_entry_count=$((snat_entry_count + ${stb_cnt:-0}))
          else
            snat_entry_count=-1
            notes+="could not read SNAT entry count of ${stb_id} (missing vpc:DescribeSnatTableEntries permission?);"
            break
          fi
        done
        if [[ "$snat_entry_count" -eq 0 ]]; then
          blockers+="SNAT table exists but contains 0 entries (configure at least one SNAT entry in the NAT gateway console);"
        fi
      else
        notes+="SNAT table IDs unavailable for entry counting;"
      fi
    fi

    # DNAT entry count (each forward table)
    local dnat_total=0
    if [[ -n "$gw_fwd_ids" ]]; then
      local fwd_id old_ifs="$IFS" fwd_arr
      IFS=','; fwd_arr=($gw_fwd_ids); IFS="$old_ifs"
      for fwd_id in "${fwd_arr[@]}"; do
        local fwd_resp fwd_exit=0 fwd_count
        fwd_resp=$(call_vpc_api "DescribeForwardTableEntries" --RegionId "$REGION" --ForwardTableId "$fwd_id" --PageSize 1 2>/dev/null) || fwd_exit=$?
        if [[ $fwd_exit -eq 0 ]]; then
          fwd_count=$(json_parse "$fwd_resp" "d.get('TotalCount', 0)")
          dnat_total=$((dnat_total + ${fwd_count:-0}))
        else
          notes+="could not read DNAT count of ${fwd_id} (missing vpc:DescribeForwardTableEntries permission?);"
        fi
      done
    fi
    [[ "$dnat_total" -gt 0 ]] && blockers+="${dnat_total} DNAT entrie(s) exist (must be deleted before creating a NAT firewall);"

    # VPC CIDRs + vswitch inventory
    local vpc_cidr_line vpc_cidr secondary_cidrs
    vpc_cidr_line=$(fetch_vpc_cidrs "$REGION" "$gw_vpc")
    vpc_cidr=$(printf '%s' "$vpc_cidr_line" | cut -f1)
    secondary_cidrs=$(printf '%s' "$vpc_cidr_line" | cut -f2)
    [[ -z "$vpc_cidr" ]] && notes+="could not read VPC CIDR (missing vpc:DescribeVpcAttribute/DescribeVpcs permission?);"

    local vs_rows=""
    vs_rows=$(enumerate_vswitches "$REGION" "$gw_vpc") || { vs_rows=""; notes+="could not list vswitches (missing vpc:DescribeVSwitches permission?);"; }

    # Diversion scope: the route tables that hold an entry whose next hop is
    # THIS NAT gateway. Only those participate in the diversion, so only those
    # are compared for custom-entry consistency (comparing every VPC table
    # over-warns - see check_route_entry_consistency SCOPE note). Zero entries
    # means there is nothing to divert at all -> auto-mode creation would fail
    # with MissingNatRouteEntryList.
    local nat_rt_csv="" nat_entry_count=0
    nat_rt_csv=$({ discover_nat_route_entries "$REGION" "$gw_vpc" "$gw_id" 2>/dev/null || true; } | { cut -f4 || true; } | { sort -u || true; } | { paste -sd, - || true; })
    nat_rt_csv="${nat_rt_csv//[[:space:]]/}"
    if [[ -n "$nat_rt_csv" ]]; then
      nat_entry_count=$(printf '%s' "$nat_rt_csv" | awk -F',' '{print NF}')
    else
      # NOTE: blockers are joined with ';' by the renderer, so the message text
      # must never contain a semicolon or it gets split into bogus entries.
      blockers+="no route entry points to this NAT gateway - nothing to divert, add a 0.0.0.0/0 route to ${gw_id} in the business route table first, otherwise creation fails with MissingNatRouteEntryList;"
    fi

    # Route-entry consistency across the DIVERSION route tables (cached per
    # scope). Inconsistent custom entries make auto-mode creation fail
    # server-side with ErrorNatCustomRouteEntryDifferent - warn early, never
    # block.
    local consistency="" cache_hit=""
    if [[ -z "$nat_rt_csv" ]]; then
      consistency="consistent:0"
    else
      if [[ -n "$CONSISTENCY_CACHE" ]]; then
        # grep exits 1 on no match; under set -e + pipefail that would kill the
        # script, so absorb the failure explicitly.
        cache_hit=$(printf '%s\n' "$CONSISTENCY_CACHE" | { grep "^${nat_rt_csv}"$'\t' || true; } | cut -f2-)
      fi
      if [[ -n "$cache_hit" ]]; then
        consistency="$cache_hit"
      else
        consistency=$(check_route_entry_consistency "$REGION" "$gw_vpc" "$nat_rt_csv")
        CONSISTENCY_CACHE+="${CONSISTENCY_CACHE:+$'\n'}${nat_rt_csv}"$'\t'"${consistency}"
      fi
    fi
    notes+="diversion scope: ${nat_entry_count} route table(s) carry a route to ${gw_id}${nat_rt_csv:+ (${nat_rt_csv})};"

    # VPN-pointing custom route entries per route table (cached per VPC).
    # Feeds the VPC-level quota projection (vpc_quota_vpn_custom_route_entry)
    # and the auto-mode inheritance estimate for the diversion scope.
    local vpn_rows="" vpn_cache_hit="" vpn_scan_ok=false
    if [[ -n "$QUOTA_CACHE" ]]; then
      vpn_cache_hit=$(printf '%s\n' "$QUOTA_CACHE" | { grep "^${gw_vpc}"$'\t' || true; } | cut -f2-)
    fi
    if [[ -n "$vpn_cache_hit" ]]; then
      # Cached value is "<ok|fail>:<rows joined by |>": the scan OUTCOME has to be
      # cached as well, because an empty row set is a legitimate result (a VPC
      # with no custom route tables genuinely has 0 VPN routes) and must not be
      # confused with a failed scan.
      if [[ "$vpn_cache_hit" == ok:* ]]; then
        vpn_scan_ok=true
        vpn_rows="${vpn_cache_hit#ok:}"
        vpn_rows="${vpn_rows//|/$'\n'}"
      fi
    else
      if vpn_rows=$(count_vpn_route_entries_per_table "$REGION" "$gw_vpc" 2>/dev/null); then
        vpn_scan_ok=true
        QUOTA_CACHE+="${QUOTA_CACHE:+$'\n'}${gw_vpc}"$'\t'"ok:${vpn_rows//$'\n'/|}"
      else
        vpn_rows=""
        QUOTA_CACHE+="${QUOTA_CACHE:+$'\n'}${gw_vpc}"$'\t'"fail:"
      fi
    fi
    case "$consistency" in
      inconsistent:*)
        notes+="route-entry consistency check FAILED across the diversion route tables: ${consistency#inconsistent:} - auto-mode creation may fail with ErrorNatCustomRouteEntryDifferent; run 'nat-fw-lifecycle.sh route-diff --region ${REGION} --vpc-id ${gw_vpc}' for the per-table diff and the two resolution options (A: manual-mode diversion, recommended; B: align custom entries, high risk);"
        ;;
      unknown:*)
        notes+="route-entry consistency could not be verified (${consistency#unknown:});"
        ;;
    esac

    # Free /28 candidates inside the VPC (auto-mode options)
    local free_cidrs=""
    if [[ -n "$vpc_cidr" ]]; then
      free_cidrs=$(printf '%s' "$vs_rows" | python3 -c '
import sys, ipaddress
used = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line: continue
    try: used.append(ipaddress.ip_network(line.split("\t")[3]))
    except (ValueError, IndexError): pass
nets = []
for c in sys.argv[1].split(","):
    if not c: continue
    try: nets.append(ipaddress.ip_network(c))
    except ValueError: pass
sugs = []
for parent in nets:
    if parent.prefixlen > 24: continue
    for sub in parent.subnets(new_prefix=28):
        if not any(sub.overlaps(u) for u in used):
            sugs.append(str(sub))
        if len(sugs) >= 3: break
    if len(sugs) >= 3: break
print(",".join(sugs))
' "${vpc_cidr},${secondary_cidrs}") || free_cidrs=""
    fi

    # Manual-mode candidates: same zone, prefix <= /28, free IPs > EIPs,
    # bound to a custom route table; then drop those whose table already
    # holds a 0.0.0.0/0 entry.
    local manual_candidates=""
    manual_candidates=$(printf '%s' "$vs_rows" | python3 -c '
import sys, ipaddress
zone = sys.argv[1]; eips = int(sys.argv[2])
out = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line: continue
    p = line.split("\t")
    if len(p) < 7: continue
    vid, vname, vzone, cidr, avail, rt_id, rt_type = p[:7]
    if vzone != zone: continue
    if rt_type != "Custom": continue
    try:
        if ipaddress.ip_network(cidr).prefixlen > 28: continue
    except ValueError: continue
    try:
        if int(avail) <= eips: continue
    except ValueError: continue
    out.append("|".join([vid, vname, cidr, avail, rt_id]))
print(",".join(out))
' "$gw_zone" "$gw_eips") || manual_candidates=""

    local filtered_candidates="" clean_candidates="" reuse_candidates=""
    if [[ -n "$manual_candidates" ]]; then
      local cand cand_arr old_ifs2="$IFS"
      IFS=','; cand_arr=($manual_candidates); IFS="$old_ifs2"
      for cand in "${cand_arr[@]}"; do
        [[ -z "$cand" ]] && continue
        local cand_id cand_rt profile drt nd_count nd_types nd_samples
        cand_id=$(printf '%s' "$cand" | awk -F'|' '{print $1}')
        cand_rt=$(printf '%s' "$cand" | awk -F'|' '{print $5}')
        profile=$(route_table_entry_profile "$REGION" "$cand_rt")
        IFS=$'\t' read -r drt nd_count nd_types nd_samples <<< "$profile"
        if [[ "$drt" == "yes" ]]; then
          notes+="manual candidate ${cand_id} excluded: route table ${cand_rt} already has a 0.0.0.0/0 entry;"
          continue
        fi
        # Constraint 6: the diversion vswitch must be dedicated and empty.
        local eni_count
        eni_count=$(vswitch_attached_eni_count "$REGION" "$cand_id")
        if [[ "$eni_count" =~ ^[0-9]+$ ]] && [[ "$eni_count" -gt 0 ]]; then
          notes+="manual candidate ${cand_id} excluded: ${eni_count} ENI(s) attached to the vswitch - the diversion vswitch must carry no other cloud resources;"
          continue
        fi
        # Constraint 5: manual mode needs a NEWLY created clean custom route
        # table. Pre-existing entries are tolerable ONLY when they look like the
        # cross-VPC return routes the official manual steps allow.
        local clean="yes"
        if [[ "${nd_count:-0}" -gt 0 ]]; then
          local bad_types
          bad_types=$(route_table_disqualifying_types "$nd_types")
          if [[ -n "$bad_types" ]]; then
            notes+="manual candidate ${cand_id} excluded: route table ${cand_rt} carries business routes (next hop ${bad_types}: ${nd_samples}) - manual mode requires a NEWLY created clean custom route table, run 'nat-fw-lifecycle.sh prepare';"
            continue
          fi
          clean="no"
          notes+="manual candidate ${cand_id}: route table ${cand_rt} is NOT freshly created - it already holds ${nd_count} entry/entries (${nd_samples}); acceptable only if these are the intended cross-VPC return routes;"
        fi
        local enc="${cand}|${drt}|${clean}|${nd_count:-0}|${nd_samples}|${eni_count}"
        if [[ "$clean" == "yes" ]]; then
          clean_candidates+="${clean_candidates:+,}${enc}"
        else
          reuse_candidates+="${reuse_candidates:+,}${enc}"
        fi
      done
      # Freshly created empty tables rank first, so suggested_vswitch_id always
      # prefers a clean table over a reusable-but-dirty one.
      filtered_candidates="$clean_candidates"
      if [[ -n "$reuse_candidates" ]]; then
        filtered_candidates="${filtered_candidates:+${filtered_candidates},}${reuse_candidates}"
      fi
    fi
    manual_candidates="$filtered_candidates"

    # Post-creation quota projection. Creation (auto mode) consumes one custom
    # route table, one vswitch and one SNAT entry; the firewall diversion
    # route table also inherits every VPN-pointing custom entry of the
    # diversion scope, and vpc_quota_vpn_custom_route_entry counts them at VPC
    # level. Manual mode reuses user-created assets (+0/+0) but still adds one
    # SNAT entry. Limits come from Quotas Center only - "unknown" stays
    # unknown rather than guessing documentation defaults.
    local qp_route_tables="-1" qp_vswitches="-1" qp_vpn_total="-1" qp_vpn_inherit="-1"
    qp_route_tables=$(count_custom_route_tables "$REGION" "$gw_vpc" 2>/dev/null) || qp_route_tables="-1"
    if [[ -n "$vs_rows" ]]; then
      qp_vswitches=$(printf '%s\n' "$vs_rows" | grep -c '^vsw-' || true)
    fi
    # A successful scan with zero rows means a genuine 0, so gate on the scan
    # outcome - not on whether any row came back.
    if [[ "$vpn_scan_ok" == "true" ]]; then
      qp_vpn_total=$(printf '%s\n' "$vpn_rows" | python3 -c '
import sys
t = 0
for l in sys.stdin:
    p = l.strip().split("\t")
    if len(p) == 2 and p[1].isdigit(): t += int(p[1])
print(t)
') || qp_vpn_total="-1"
      qp_vpn_inherit=$(printf '%s\n' "$vpn_rows" | python3 -c '
import sys
scope = set(sys.argv[1].split(",")) if sys.argv[1] else set()
t = 0
for l in sys.stdin:
    p = l.strip().split("\t")
    if len(p) == 2 and p[1].isdigit() and p[0] in scope: t += int(p[1])
print(t)
' "$nat_rt_csv") || qp_vpn_inherit="-1"
    fi

    # Recommendation
    local mode="none"
    if [[ -z "$blockers" ]]; then
      if [[ -n "$free_cidrs" ]]; then
        mode="auto"
      elif [[ -n "$manual_candidates" ]]; then
        mode="manual"
      fi
    fi

    assess_rows+="$(printf 'G\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' \
      "$gw_id" "$gw_name" "$gw_vpc" "$gw_zone" "$gw_status" "$gw_eips" "$gw_snat_tables" \
      "$dnat_total" "$vpc_cidr" "$free_cidrs" "$manual_candidates" "$blockers" "$notes" "$mode" "$snat_entry_count" \
      "$qp_route_tables" "$qp_vswitches" "$qp_vpn_total" "$qp_vpn_inherit")"$'\n'
  done <<< "$gw_rows"

  # Step 5: render the JSON report.
  # ASSESS IS A POINT-IN-TIME SNAPSHOT: users may create/delete vswitches,
  # SNAT entries or whole gateways in the console at any moment, so every
  # report carries assessed_at + a freshness warning, and create re-verifies
  # all candidates at execution time.
  local assessed_at
  assessed_at=$(date '+%Y-%m-%d %H:%M:%S')
  local report_json
  report_json=$(printf '%s%s' "$protected_rows" "$assess_rows" | python3 -c '
import sys, json
region, total, used = sys.argv[1], sys.argv[2], sys.argv[3]
assessed_at = sys.argv[4]
q_rt, q_vsw, q_vpn, q_snat = sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8]
quotas_denied = sys.argv[9] == "true"

def qi(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None
LIMITS = {"route_tables": qi(q_rt), "vswitches": qi(q_vsw), "vpn_routes": qi(q_vpn), "snat_entries": qi(q_snat)}

def proj_item(key, current, inc):
    lim = LIMITS[key]
    # Usage counters carry -1 as the "could not read" sentinel (same convention as
    # snat_entry_count, and what an empty VPN-route scan yields). Any negative
    # value MUST collapse to unknown: leaving it as a number would project
    # nonsense like current=-1 / after_create=-1 and, since -1 never exceeds the
    # limit, silently report status "ok" for a check that never actually ran.
    if current is not None and current < 0:
        current = None
    out = {"current": current}
    if current is None:
        out["status"] = "unknown"
        out["reason"] = "usage could not be read (missing VPC read permission)"
        return out
    out["after_create"] = current + inc
    if lim is None:
        out["status"] = "unknown"
        out["reason"] = "quota not resolved - grant quotas:GetProductQuota (references/ram-policies.md) and re-run assess; documentation defaults are NOT assumed"
        return out
    out["limit"] = lim
    if out["after_create"] > lim:
        out["status"] = "exceeded"
    elif out["after_create"] * 100 >= lim * 80:
        out["status"] = "warning"
    else:
        out["status"] = "ok"
    return out

protected = []; gateways = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line: continue
    p = line.split("\t")
    if p[0] == "P" and len(p) >= 5:
        protected.append({"nat_gateway_id": p[1], "proxy_id": p[2], "proxy_name": p[3], "status": p[4]})
    elif p[0] == "G" and len(p) >= 20:
        gw = {
            "nat_gateway_id": p[1], "name": p[2], "vpc_id": p[3], "zone": p[4], "status": p[5],
            "eip_count": int(p[6] or 0), "snat_table_count": int(p[7] or 0), "snat_entry_count": int(p[15]) if p[15].lstrip("-").isdigit() else None,
            "dnat_entry_count": int(p[8] or 0),
            "vpc_cidr": p[9],
            "free_cidr_candidates": [c for c in p[10].split(",") if c],
            "manual_candidates": [],
            "blockers": [b for b in p[12].split(";") if b],
            "notes": [n for n in p[13].split(";") if n],
        }
        for cand in [c for c in p[11].split(",") if c]:
            f = cand.split("|")
            gw["manual_candidates"].append({"vswitch_id": f[0], "name": f[1], "cidr": f[2],
                                            "free_ips": int(f[3] or 0), "route_table_id": f[4],
                                            "default_route_check": f[5] if len(f) > 5 else "unknown",
                                            "route_table_clean": f[6] if len(f) > 6 else "unknown",
                                            "route_table_entry_count": int(f[7] or 0) if len(f) > 7 else 0,
                                            "route_table_entries": f[8] if len(f) > 8 else "",
                                            "attached_eni_count": f[9] if len(f) > 9 else "unknown"})
        # Post-creation quota projection. Auto mode consumes 1 custom route
        # table + 1 vswitch + 1 SNAT entry, and the firewall diversion route
        # table inherits the diversion-scope VPN custom entries (counted by
        # the VPC-level VPN quota). Manual mode reuses user assets (+0/+0)
        # but still adds 1 SNAT entry.
        mode = p[14]
        cur_rt, cur_vsw, cur_vpn, vpn_inh = (qi(p[16]), qi(p[17]), qi(p[18]), qi(p[19]))
        if mode == "auto":
            qp = {
                "route_tables": proj_item("route_tables", cur_rt, 1),
                "vswitches": proj_item("vswitches", cur_vsw, 1),
                "snat_entries": proj_item("snat_entries", gw["snat_entry_count"], 1),
                "vpn_custom_routes": proj_item("vpn_routes", cur_vpn, max(vpn_inh or 0, 0)),
            }
            if vpn_inh is not None and vpn_inh > 0:
                qp["vpn_custom_routes"]["note"] = "auto mode: the firewall diversion route table inherits %d VPN-pointing entr(y/ies) from the diversion scope" % vpn_inh
        else:
            qp = {
                "route_tables": proj_item("route_tables", cur_rt, 0),
                "vswitches": proj_item("vswitches", cur_vsw, 0),
                "snat_entries": proj_item("snat_entries", gw["snat_entry_count"], 1),
                "vpn_custom_routes": proj_item("vpn_routes", cur_vpn, 0),
            }
            if vpn_inh is not None and vpn_inh > 0:
                qp["vpn_custom_routes"]["note"] = ("manual mode: nothing is inherited by default, BUT if cross-VPC "
                    "traffic should be protected the user must manually add the return routes (incl. %d "
                    "VPN-pointing entr(y/ies) from the diversion scope) to the firewall route table - "
                    "that can still exhaust this quota; raise the quota or clean up redundant routes first" % vpn_inh)
        gw["quota_projection"] = qp

        rec = {"mode": mode}
        inconsistent = any("ErrorNatCustomRouteEntryDifferent" in n for n in gw["notes"])
        if mode == "auto":
            rec["reason"] = "VPC has free /28 address space; auto mode needs no manual preparation and the vswitch is reclaimed on deletion"
            if inconsistent:
                rec["reason"] += "; WARNING: custom route entries differ across route tables - creation may fail with ErrorNatCustomRouteEntryDifferent; if it does, retry in manual mode (--vswitch-id)"
            rec["suggested_vswitch_cidr"] = gw["free_cidr_candidates"][0]
        elif mode == "manual":
            rec["reason"] = "no free /28 in VPC, but an existing vswitch satisfies the manual-mode constraints; confirm the human checklist before creating"
            if inconsistent:
                rec["reason"] += "; note: route-entry inconsistency detected - manual mode avoids the ErrorNatCustomRouteEntryDifferent check"
            first = gw["manual_candidates"][0]
            if first.get("route_table_clean") != "yes":
                rec["reason"] += ("; WARNING: no candidate bound to a freshly created EMPTY custom route table - %s reuses table %s that already holds %d entry/entries (%s); "
                                  "verify these are the intended cross-VPC return routes, or run 'prepare' to build clean assets"
                                  % (first["vswitch_id"], first["route_table_id"],
                                     first["route_table_entry_count"], first["route_table_entries"]))
            rec["suggested_vswitch_id"] = first["vswitch_id"]
        elif gw["blockers"]:
            rec["reason"] = "fix the blockers first, then re-run assess"
        else:
            rec["reason"] = "no free /28 and no eligible existing vswitch; add a VPC secondary CIDR, create a dedicated vswitch + custom route table, or use the console"
        # Quota-driven downgrade: auto mode that would exhaust the route-table
        # / vswitch / VPN-route quota must fall back to manual mode (or none).
        if rec["mode"] == "auto":
            exceeded = [k for k in ("route_tables", "vswitches", "vpn_custom_routes")
                        if qp.get(k, {}).get("status") == "exceeded"]
            if exceeded:
                if gw["manual_candidates"]:
                    rec["mode"] = "manual"
                    rec["reason"] = "quota projection: auto-mode creation would exceed %s; manual mode reuses existing assets" % ", ".join(exceeded)
                    rec["suggested_vswitch_id"] = gw["manual_candidates"][0]["vswitch_id"]
                    rec.pop("suggested_vswitch_cidr", None)
                else:
                    rec["mode"] = "none"
                    rec["reason"] = "quota projection: auto-mode creation would exceed %s and no manual-mode candidate exists; raise the quota or free resources first" % ", ".join(exceeded)
                    rec.pop("suggested_vswitch_cidr", None)
            elif any(qp.get(k, {}).get("status") == "warning" for k in ("route_tables", "vswitches", "vpn_custom_routes", "snat_entries")):
                rec["reason"] += "; WARNING: quota projection near the limit (see quota_projection) - consider raising the quota before creating"
        gw["recommendation"] = rec
        gateways.append(gw)
print(json.dumps({
    "action": "assess",
    "region": region,
    "assessed_at": assessed_at,
    "freshness_warning": "Point-in-time snapshot. Console changes (vswitch/SNAT/route-table/gateway edits) are NOT reflected after this moment - re-run assess right before create if anything may have changed.",
    "quota": {"total": total, "used": used},
    "quota_projection_note": ("resource quotas resolved via Quotas Center (GetProductQuota)"
                              if not quotas_denied else
                              "UNAVAILABLE: quotas:GetProductQuota is missing - grant it per references/ram-policies.md and re-run assess; limits are reported as unknown, documentation defaults are deliberately NOT assumed"),
    "protected_firewalls": protected,
    "unprotected_gateways": gateways,
}, indent=2, ensure_ascii=False))
' "$REGION" "${total_count:-}" "${used_count:-}" "$assessed_at" "${QUOTA_RT_LIMIT:-}" "${QUOTA_VSW_LIMIT:-}" "${QUOTA_VPN_LIMIT:-}" "${QUOTA_SNAT_LIMIT:-}" "$QUOTAS_DENIED")

  if [[ -z "$report_json" ]]; then
    log_error "assess failed to build the report (python3 render error)"
    exit 2
  fi

  # Step 6 (single-gateway mode only): turn the assessment into an actionable
  # PLAN. Runs the server-side pre-check too, so the user gets ONE complete
  # proposal (mode + parameters + risks + ready-to-run command) instead of a
  # chain of separate questions.
  if [[ -n "$NAT_GATEWAY_ID" ]]; then
    if [[ -n "$TARGET_PROTECTED" ]]; then
      report_json=$(printf '%s' "$report_json" | python3 -c '
import sys, json
d = json.load(sys.stdin)
gw = sys.argv[1]
cur = [p for p in d.get("protected_firewalls", []) if p.get("nat_gateway_id") == gw]
d["target_nat_gateway_id"] = gw
d["plan"] = {
    "actionable": False,
    "reason": "this NAT gateway already has a NAT firewall - nothing to create",
    "existing_firewall": cur[0] if cur else None,
    "next_step": "use nat-fw-switch.sh enable/disable to change its protection switch, or delete it first to re-create",
}
print(json.dumps(d, indent=2, ensure_ascii=False))
' "$NAT_GATEWAY_ID") || { log_error "failed to render the plan"; exit 2; }
      log_info "Plan: ${NAT_GATEWAY_ID} is already protected; no creation needed."
      output_success "$report_json"
      exit 0
    fi

    # Server-side pre-check (authoritative dependency verdict)
    local target_vpc precheck_json="" pre_exit=0
    target_vpc=$(json_parse "$report_json" "([g['vpc_id'] for g in d.get('unprotected_gateways', []) if g['nat_gateway_id'] == '${NAT_GATEWAY_ID}'] or [''])[0]")
    if [[ -z "$target_vpc" ]]; then
      log_warn "Gateway ${NAT_GATEWAY_ID} not found among the region's NAT gateways; the plan will omit the server pre-check."
    else
      log_info "Running the server-side pre-check for ${NAT_GATEWAY_ID} ..."
      local pre_trigger
      pre_trigger=$(call_cfw_api "CreateNatFirewallPreCheck" --NatGatewayId "$NAT_GATEWAY_ID" --RegionNo "$REGION" --VpcId "$target_vpc" --Lang zh 2>/dev/null) || pre_exit=$?
      if [[ $pre_exit -ne 0 ]]; then
        log_warn "Could not trigger the server pre-check; the plan will rely on client-side checks only."
      else
        local pi
        for pi in 1 2 3 4 5 6 7 8 9 10; do
          sleep 3
          local pd_exit=0 pd_resp
          pd_resp=$(call_cfw_api "DescribeNatFirewallPrecheckDetail" --NatGatewayId "$NAT_GATEWAY_ID" --RegionNo "$REGION" --Lang zh 2>/dev/null) || pd_exit=$?
          if [[ $pd_exit -eq 0 && -n "$pd_resp" ]]; then
            precheck_json="$pd_resp"
            break
          fi
        done
        [[ -z "$precheck_json" ]] && log_warn "Server pre-check result not available within 30s; the plan will rely on client-side checks only."
      fi
    fi

    report_json=$(printf '%s\n---PRECHECK---\n%s\n' "$report_json" "${precheck_json:-}" | python3 -c '
import sys, json, re
raw = sys.stdin.read().split("---PRECHECK---")
d = json.loads(raw[0])
pre_raw = raw[1].strip() if len(raw) > 1 else ""
gw_id = sys.argv[1]

# --- server pre-check summary -------------------------------------------------
pre = {"available": False, "status": "unknown", "failed_items": [], "item_count": 0}
if pre_raw:
    try:
        pj = json.loads(pre_raw)
        detail = pj.get("PrecheckDetail", {}) or {}
        # Requirement-style labels: raw API item names can be awkward,
        # e.g. the negative phrasing "NAT网关未配置DNAT条目" reads like a state
        # description; users need the requirement (no DNAT entries allowed).
        PRECHECK_DISPLAY = {
            "NAT网关未配置DNAT条目": "NAT网关必须无DNAT条目（DNAT条目与NAT防火墙互斥，存在时必须先删除）",
        }
        items = []
        for grp in detail.get("PrecheckEntityGroups", []) or []:
            for ent in grp.get("PrecheckEntities", []) or []:
                name = ent.get("Name", "")
                items.append({"group": grp.get("Name", ""), "name": name,
                              "display": PRECHECK_DISPLAY.get(name, name),
                              "status": ent.get("Status", ""), "suggestion": ent.get("Suggestion", "")})
        pre = {
            "available": True,
            "status": detail.get("PrecheckStatus", "unknown"),
            "checked_at": detail.get("PrecheckTimestamp", ""),
            "item_count": len(items),
            # Full item list: SKILL.md requires presenting EVERY pre-check item
            # (with the friendly `display` label). Exposing only failed_items
            # made that impossible on the common all-passed path and forced a
            # redundant `precheck` run.
            "items": items,
            "failed_items": [i for i in items if i["status"] != "passed"],
        }
    except Exception:
        pass
d["precheck"] = pre
d["target_nat_gateway_id"] = gw_id

cands = [g for g in d.get("unprotected_gateways", []) if g["nat_gateway_id"] == gw_id]
if not cands:
    d["plan"] = {"actionable": False,
                 "reason": "NAT gateway not found in this region (check the ID and region)"}
    print(json.dumps(d, indent=2, ensure_ascii=False)); sys.exit(0)
g = cands[0]
rec = g.get("recommendation", {})
mode = rec.get("mode", "none")
notes = g.get("notes", [])
blockers = list(g.get("blockers", []))
if pre["available"] and pre["status"] != "passed":
    for it in pre["failed_items"]:
        blockers.append("server pre-check failed: %s (%s)" % (it["display"], it["group"]))

# --- risks -------------------------------------------------------------------
risks = []
inconsistent = any("ErrorNatCustomRouteEntryDifferent" in n for n in notes)
if inconsistent and mode == "auto":
    risks.append({
        "id": "route_entry_inconsistent",
        "severity": "medium",
        "what": "the route tables participating in the diversion do NOT carry identical custom entries",
        "impact": "auto-mode creation may be rejected with ErrorNatCustomRouteEntryDifferent",
        "options": ["proceed and fall back to manual mode if it fails",
                    "switch to manual mode now (--vswitch-id, needs a dedicated vswitch)",
                    "align the custom entries first (HIGH risk, run route-diff for the plan)"],
    })
for n in notes:
    if "could not read" in n or "could not list" in n or "could not be verified" in n:
        risks.append({"id": "degraded_check", "severity": "low",
                      "what": n.rstrip(";"), "impact": "this dependency was not verified client-side"})
dirty = [c for c in g.get("manual_candidates", []) if c.get("route_table_clean") != "yes"]
if mode == "manual" and dirty:
    risks.append({"id": "reused_route_table", "severity": "medium",
                  "what": "the diversion route table already holds %d entry/entries (%s)" % (
                      dirty[0]["route_table_entry_count"], dirty[0]["route_table_entries"]),
                  "impact": "acceptable only if these are the intended cross-VPC return routes"})

# --- parameters --------------------------------------------------------------
name_seed = re.sub(r"[^0-9A-Za-z_-]", "-", g.get("name") or gw_id)[:42].strip("-") or gw_id[-8:]
suggested_name = ("nat-fw-" + name_seed)[:50]
eips = g.get("eip_count", 0) or 0
params = {
    "nat_gateway_id": gw_id,
    "region": d["region"],
    "vpc_id": g["vpc_id"],
    "proxy_name": {"suggested": suggested_name, "rule": "4~50 characters", "needs_confirmation": True},
    "diversion": {},
    "firewall_switch": {"default": "close", "needs_confirmation": True,
                        "note": "close = no business impact; open = 1~2s flap of long-lived connections during route switching"},
    "strict_mode": {"default": "0", "needs_confirmation": True,
                    "note": "0 = loose (availability first), 1 = strict (blocks unidentifiable app/domain traffic when a deny rule exists)"},
}
cmd = None
if mode == "auto":
    cidr = rec.get("suggested_vswitch_cidr", "")
    params["diversion"] = {"mode": "auto", "vswitch_cidr": cidr,
                           "alternatives": g.get("free_cidr_candidates", [])[1:3],
                           "note": "Cloud Firewall creates the diversion vswitch + custom route table and reclaims them on deletion"}
    cmd = ("bash scripts/nat-fw-lifecycle.sh create --nat-gateway-id %s --region %s --vpc-id %s "
           "--proxy-name %s --vswitch-cidr %s --firewall-switch close --strict-mode 0 --yes"
           % (gw_id, d["region"], g["vpc_id"], suggested_name, cidr))
elif mode == "manual":
    vsw = rec.get("suggested_vswitch_id", "")
    params["diversion"] = {"mode": "manual", "vswitch_id": vsw,
                           "candidates": g.get("manual_candidates", []),
                           "note": "the vswitch stays a user asset and is NOT reclaimed when the firewall is deleted"}
    cmd = ("bash scripts/nat-fw-lifecycle.sh create --nat-gateway-id %s --region %s --vpc-id %s "
           "--proxy-name %s --vswitch-id %s --firewall-switch close --strict-mode 0 --yes"
           % (gw_id, d["region"], g["vpc_id"], suggested_name, vsw))

quota = d.get("quota", {})
try:
    quota_ok = int(quota.get("used", 0)) < int(quota.get("total", 0))
except (TypeError, ValueError):
    quota_ok = None

d["plan"] = {
    "actionable": bool(cmd) and not blockers and quota_ok is not False,
    "mode": mode,
    "gateway": {"nat_gateway_id": gw_id, "name": g.get("name", ""), "vpc_id": g["vpc_id"],
                "zone": g.get("zone", ""), "eip_count": eips,
                "snat_entry_count": g.get("snat_entry_count"), "dnat_entry_count": g.get("dnat_entry_count")},
    "quota": {"used": quota.get("used"), "total": quota.get("total"), "sufficient": quota_ok},
    "parameters": params,
    "blockers": blockers,
    "risks": risks,
    "estimated_duration": "about %s minutes (2~5 min per bound EIP x %d EIP)" % (
        "%d~%d" % (2 * max(eips, 1), 5 * max(eips, 1)), max(eips, 1)),
    "business_impact": "none while the switch stays closed; enabling switches the NAT route and flaps long-lived connections for 1~2 seconds",
    "reversibility": "deleting a closed firewall has no business impact; auto-mode diversion assets are reclaimed on deletion",
    "command": cmd,
    "post_steps": ["poll status until configuring -> closed/normal",
                   "if protection should be active, run the three-phase enable workflow (nat-fw-switch.sh enable)"],
}
if blockers:
    d["plan"]["reason"] = "resolve the blockers, then re-run assess"
elif not cmd:
    d["plan"]["reason"] = rec.get("reason", "no diversion mode available")
print(json.dumps(d, indent=2, ensure_ascii=False))
' "$NAT_GATEWAY_ID") || { log_error "failed to render the plan"; exit 2; }
  fi

  log_info "Assessment complete: $(printf '%s' "$assess_rows" | grep -c '^G' || true) unprotected gateway(s) found."
  output_success "$report_json"
}

# --- Subcommand: prepare ---

# One-click manual-mode preparation (the human steps from the official docs,
# automated and made idempotent):
#   1. Find or create a dedicated vswitch in the NAT gateway's availability
#      zone (prefix >= /28, free IPs > bound-EIP count).
#   2. Find or create a NEW custom route table WITHOUT a 0.0.0.0/0 entry and
#      bind it to the vswitch.
# Existing qualifying assets are REUSED (orphan Cloud_Firewall_ROUTE_TABLE
# leftovers from previous firewall deletions are preferred), so re-running is
# safe. Requires vpc:CreateVSwitch / vpc:CreateRouteTable /
# vpc:AssociateRouteTable only for the parts that are actually created.
# --- Subcommand: route-diff (read-only) ---
# Deep diagnosis for ErrorNatCustomRouteEntryDifferent: shows WHICH custom
# entries differ across the VPC's route tables, classifies the divergent
# next-hop types, and prints BOTH resolution options:
#   A) manual-mode diversion (safe default, touches no existing routes)
#   B) aligning custom entries (HIGH risk, global forwarding change;
#      plan only - this command NEVER modifies routes)
cmd_route_diff() {
  local REGION="" VPC_ID="" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --region) arg_value "--region" "${@:2}"; REGION="$2"; shift 2 ;;
      --vpc-id) arg_value "--vpc-id" "${@:2}"; VPC_ID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "nat-fw-lifecycle.sh route-diff" \
          "Diagnose custom route entry inconsistency across a VPC's route tables (read-only)" \
          "nat-fw-lifecycle.sh route-diff --region <id> --vpc-id <id>" \
          "  --region <id>  Region ID (required)
  --vpc-id <id>   VPC ID (required)
  --dry-run       Show the APIs that would be called
  --help, -h      Show this help

  Use this when 'assess' reports a route-entry consistency warning or when
  creation fails with ErrorNatCustomRouteEntryDifferent. Output contains the
  per-table entry diff, a next-hop-type classification (VPN/peer/CEN routes
  indicate business topology that should NOT be touched), and both resolution
  options: A) manual-mode diversion (recommended), B) an alignment plan
  (add/remove lists) that must be reviewed and executed by the network team."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "region" "$REGION" || exit 1
  validate_required "vpc-id" "$VPC_ID" || exit 1
  validate_region "$REGION" || exit 1
  validate_vpc_id "$VPC_ID" || exit 1

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing APIs that would be called"
    echo "aliyun Vpc DescribeRouteTableList --RegionId ${REGION} --VpcId ${VPC_ID} (paginated)"
    echo "aliyun Vpc DescribeRouteEntryList --RegionId ${REGION} --RouteTableId <each table> --RouteEntryType Custom (paginated, first 10 tables)"
    exit 0
  fi

  command -v python3 &>/dev/null || { log_error "python3 is required for route-diff"; exit 1; }

  # Step 1: route tables of the VPC (paginated)
  # TSV: rt_id<TAB>rt_type<TAB>rt_name<TAB>bound_vswitch_count
  local tables_tsv="" page=1
  while :; do
    local rt_resp rt_exit=0
    rt_resp=$(call_vpc_api "DescribeRouteTableList" --RegionId "$REGION" --VpcId "$VPC_ID" --PageNumber "$page" --PageSize 50) || rt_exit=$?
    if [[ $rt_exit -ne 0 ]]; then
      local rt_err
      rt_err=$(extract_api_error_code "$rt_resp")
      output_error "${rt_err:-UnknownError}" "DescribeRouteTableList failed"
      exit 2
    fi
    local t_chunk
    t_chunk=$(json_parse "$rt_resp" "'\\n'.join('\\t'.join([t.get('RouteTableId',''), t.get('RouteTableType',''), str(t.get('RouteTableName','')).replace('\\t',' '), str(len(t.get('VSwitchIds',{}).get('VSwitchId',[]) or []))]) for t in d.get('RouterTableList', {}).get('RouterTableListType', []))")
    [[ -n "$t_chunk" ]] && tables_tsv+="${t_chunk}"$'\n'
    local t_total
    t_total=$(json_parse "$rt_resp" "d.get('TotalCount', 0)")
    if [[ -z "$t_total" || $((page * 50)) -ge "$t_total" ]]; then break; fi
    page=$((page + 1))
  done

  # Step 2: custom entries per table (cap: first 10 tables, 3 pages each)
  # TSV: rt_id<TAB>cidr<TAB>nexthops("Type:Id,...")
  local entries_tsv="" rt_ids_csv="" t_line
  while IFS=$'\t' read -r t_line; do
    [[ -z "$t_line" ]] && continue
    local tid
    tid=$(printf '%s' "$t_line" | cut -f1)
    rt_ids_csv+="${rt_ids_csv:+,}${tid}"
  done <<< "$tables_tsv" || true

  local old_ifs_rd="$IFS" rd_arr rt_id
  IFS=','; rd_arr=($rt_ids_csv); IFS="$old_ifs_rd"
  local rd_count=${#rd_arr[@]} rd_idx=0
  for rt_id in "${rd_arr[@]:-}"; do
    [[ -z "$rt_id" ]] && continue
    rd_idx=$((rd_idx + 1)); [[ $rd_idx -gt 10 ]] && break
    local next_token="" loop_guard=0 ent_resp ent_exit=0
    while :; do
      loop_guard=$((loop_guard + 1)); [[ $loop_guard -gt 3 ]] && break
      ent_exit=0
      if [[ -n "$next_token" ]]; then
        ent_resp=$(call_vpc_api "DescribeRouteEntryList" --RegionId "$REGION" --RouteTableId "$rt_id" --RouteEntryType Custom --MaxResult 100 --NextToken "$next_token" 2>/dev/null) || ent_exit=$?
      else
        ent_resp=$(call_vpc_api "DescribeRouteEntryList" --RegionId "$REGION" --RouteTableId "$rt_id" --RouteEntryType Custom --MaxResult 100 2>/dev/null) || ent_exit=$?
      fi
      if [[ $ent_exit -ne 0 ]]; then
        log_warn "DescribeRouteEntryList failed for ${rt_id} (missing vpc:DescribeRouteEntryList permission?); table excluded from comparison."
        break
      fi
      local e_chunk
      e_chunk=$(json_parse "$ent_resp" "'\\n'.join('\\t'.join([e.get('DestinationCidrBlock',''), ','.join(sorted(set((n.get('NextHopType','') + ':' + n.get('NextHopId','')) for n in e.get('NextHops', {}).get('NextHop', [])))) or '-']) for e in d.get('RouteEntrys', {}).get('RouteEntry', []))")
      if [[ -n "$e_chunk" ]]; then
        local eline
        while IFS= read -r eline; do
          [[ -n "$eline" ]] && entries_tsv+="${rt_id}"$'\t'"${eline}"$'\n'
        done <<< "$e_chunk" || true
      fi
      next_token=$(json_parse "$ent_resp" "d.get('NextToken', '') or ''")
      [[ -z "$next_token" ]] && break
    done
  done

  # Step 3: analyze + render the JSON report (read-only; plan is advice only)
  local report
  report=$(printf '%s\n===ENTRIES===\n%s' "$tables_tsv" "$entries_tsv" | python3 -c '
import sys, json
raw = sys.stdin.read()
parts = raw.split("===ENTRIES===")
tables = [l.split("\t") for l in parts[0].splitlines() if l.strip() and len(l.split("\t")) >= 4]
entries = [l.split("\t") for l in (parts[1] if len(parts) > 1 else "").splitlines() if l.strip() and len(l.split("\t")) >= 3]
TOPO = {"VpnGateway", "VpcPeer", "RouterInterface", "Attachment", "TransitRouter", "VBR"}
tids = [t[0] for t in tables]
own = {tid: set() for tid in tids}
for rt, cidr, nh in entries:
    if rt in own:
        own[rt].add((cidr, nh))
union = set()
for s in own.values(): union |= s
intersection = set(union)
for s in own.values(): intersection &= s
divergent = sorted(union - intersection)
consistent = len(divergent) == 0
types_seen = set()
diff_rows = []
for cidr, nh in divergent:
    holders = [t for t in tids if (cidr, nh) in own[t]]
    diff_rows.append({"cidr": cidr, "next_hops": nh, "present_in": holders,
                      "missing_from": [t for t in tids if t not in holders]})
    for part in nh.split(","):
        hop_type = part.split(":")[0]
        if hop_type and hop_type != "-":
            types_seen.add(hop_type)
classification = "none"
if divergent:
    if types_seen and types_seen.issubset(TOPO):
        classification = "business_topology"
    elif types_seen & TOPO:
        classification = "mixed"
    else:
        classification = "other"
plan_add = [{"cidr": c, "next_hops": nh, "add_to_tables": [t for t in tids if (c, nh) not in own[t]]}
            for c, nh in divergent]
plan_remove = [{"cidr": c, "next_hops": nh, "remove_from_tables": [t for t in tids if (c, nh) in own[t]]}
               for c, nh in divergent]
options = []
recommendation = "none"
if not consistent:
    recommendation = "manual_diversion"
    options = [
        {"id": "A", "name": "manual-mode diversion (recommended)", "risk": "low",
         "summary": "Divert via a dedicated vswitch bound to a NEW custom route table; existing route tables stay untouched. Run: nat-fw-lifecycle.sh prepare ... then create --vswitch-id <vsw>."},
        {"id": "B", "name": "align custom route entries", "risk": "HIGH",
         "summary": "Make every route table carry identical custom entries per alignment_plan (union = add missing entries everywhere; intersection = remove divergent entries). Adding/removing entries changes forwarding for ALL vswitches bound to those tables and may blackhole or reroute production traffic. Must be reviewed and executed by the network team; this command NEVER modifies routes."}
    ]
note = "route-diff is read-only." if consistent else (
    "Divergent next-hop types are business-topology routes (VPN/peering/CEN) - strongly prefer option A; propagating or deleting such routes is a production network change." if classification in ("business_topology", "mixed")
    else "Review each divergent entry with the network team before choosing option B; option A remains the risk-free path.")
print(json.dumps({
    "consistent": consistent,
    "route_table_count": len(tids),
    "route_tables": [{"id": t[0], "type": t[1], "name": t[2],
                      "bound_vswitch_count": int(t[3]) if t[3].isdigit() else 0,
                      "custom_entry_count": len(own.get(t[0], set()))} for t in tables],
    "divergent_entries": diff_rows,
    "divergent_next_hop_types": sorted(types_seen),
    "classification": classification,
    "alignment_plan": {"union_add": plan_add, "intersection_remove": plan_remove},
    "options": options,
    "recommendation": recommendation,
    "note": note
}, ensure_ascii=False, indent=2))
') || { output_error "AnalysisFailed" "route diff analysis failed"; exit 2; }

  if printf '%s' "$report" | grep -q '"consistent": true'; then
    log_info "All route tables carry identical custom entries - auto mode is safe from the consistency standpoint."
  else
    log_warn "Route-entry inconsistency detected. Two resolution options are in the report: (A) manual-mode diversion - recommended, zero impact on existing routes; (B) align entries - HIGH risk global forwarding change, execute manually with the network team."
  fi
  printf '%s\n' "$report"
}

cmd_prepare() {
  local REGION="" VPC_ID="" NAT_GATEWAY_ID="" VSWITCH_CIDR="" VSWITCH_NAME="nat-fw-diversion" RT_NAME="nat-fw-diversion-rt" YES=false DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --region) arg_value "--region" "${@:2}"; REGION="$2"; shift 2 ;;
      --vpc-id) arg_value "--vpc-id" "${@:2}"; VPC_ID="$2"; shift 2 ;;
      --nat-gateway-id) arg_value "--nat-gateway-id" "${@:2}"; NAT_GATEWAY_ID="$2"; shift 2 ;;
      --vswitch-cidr) arg_value "--vswitch-cidr" "${@:2}"; VSWITCH_CIDR="$2"; shift 2 ;;
      --vswitch-name) arg_value "--vswitch-name" "${@:2}"; VSWITCH_NAME="$2"; shift 2 ;;
      --route-table-name) arg_value "--route-table-name" "${@:2}"; RT_NAME="$2"; shift 2 ;;
      --yes) YES=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "nat-fw-lifecycle.sh prepare" \
          "Prepare manual-mode assets: dedicated vswitch + NEW custom route table" \
          "nat-fw-lifecycle.sh prepare --region <id> --vpc-id <id> --nat-gateway-id <id> --vswitch-cidr <cidr> --yes" \
          "  --region <id>           Region ID (required)
  --vpc-id <id>           VPC of the NAT gateway (required)
  --nat-gateway-id <id>   NAT gateway to protect; determines the availability
                          zone and EIP count of the diversion vswitch (required)
  --vswitch-cidr <cidr>   CIDR for the new vswitch; only used when no existing
                          qualifying vswitch can be reused (>= /28 inside VPC)
  --vswitch-name <name>   Name for a newly created vswitch (default: nat-fw-diversion)
  --route-table-name <n>  Name for a newly created route table (default: nat-fw-diversion-rt)
  --yes                   Confirm execution (required for any creation)
  --dry-run               Show the plan without changing anything
  --help, -h              Show this help

  Idempotent: existing qualifying vswitches (same zone, >= /28, enough free
  IPs) and orphan custom route tables (unbound, no 0.0.0.0/0 entry) are
  REUSED. Requires vpc:CreateVSwitch / vpc:CreateRouteTable /
  vpc:AssociateRouteTable only for the pieces actually created."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "region" "$REGION" || exit 1
  validate_required "vpc-id" "$VPC_ID" || exit 1
  validate_required "nat-gateway-id" "$NAT_GATEWAY_ID" || exit 1
  validate_region "$REGION" || exit 1
  validate_vpc_id "$VPC_ID" || exit 1
  validate_nat_gateway_id "$NAT_GATEWAY_ID" || exit 1

  # Step 1: NAT gateway attributes (zone + EIP count)
  local ng_resp ng_exit=0 gw_zone="" gw_eips=0
  ng_resp=$(call_vpc_api "DescribeNatGateways" --RegionId "$REGION" --NatGatewayId "$NAT_GATEWAY_ID") || ng_exit=$?
  if [[ $ng_exit -ne 0 ]]; then
    local ng_err
    ng_err=$(extract_api_error_code "$ng_resp")
    log_error "DescribeNatGateways failed (${ng_err:-unknown}): cannot determine the gateway's zone/EIPs."
    output_error "${ng_err:-UnknownError}" "DescribeNatGateways failed"
    exit 2
  fi
  gw_zone=$(json_parse "$ng_resp" "(d.get('NatGateways', {}).get('NatGateway') or [{}])[0].get('NatGatewayPrivateInfo', {}).get('IzNo', '')")
  gw_eips=$(json_parse "$ng_resp" "len((d.get('NatGateways', {}).get('NatGateway') or [{}])[0].get('IpLists', {}).get('IpList', []))")
  [[ -z "$gw_eips" ]] && gw_eips=0
  local gw_actual_vpc
  gw_actual_vpc=$(json_parse "$ng_resp" "(d.get('NatGateways', {}).get('NatGateway') or [{}])[0].get('VpcId', '')")
  if [[ -z "$gw_zone" ]]; then
    log_error "NAT gateway ${NAT_GATEWAY_ID} not found in ${REGION} (or missing zone info)."
    output_error "GatewayNotFound" "NAT gateway ${NAT_GATEWAY_ID} not found in ${REGION}"
    exit 2
  fi
  if [[ -n "$gw_actual_vpc" && "$gw_actual_vpc" != "$VPC_ID" ]]; then
    log_error "NAT gateway ${NAT_GATEWAY_ID} belongs to VPC ${gw_actual_vpc}, not ${VPC_ID}."
    output_error "VpcMismatch" "Gateway VPC ${gw_actual_vpc} != requested ${VPC_ID}"
    exit 1
  fi
  log_info "Gateway ${NAT_GATEWAY_ID}: zone ${gw_zone}, ${gw_eips} EIP(s)."

  # Step 2: look for a reusable vswitch (same VPC+zone, >= /28, free IPs > EIPs)
  local vs_rows reuse_vsw="" reuse_vsw_rt="" reuse_vsw_rt_type=""
  vs_rows=$(enumerate_vswitches "$REGION" "$VPC_ID") || { vs_rows=""; log_warn "Could not list vswitches (missing vpc:DescribeVSwitches?); will create a new one."; }
  if [[ -n "$vs_rows" ]]; then
    local cand_rows cand_line
    cand_rows=$(printf '%s' "$vs_rows" | python3 -c '
import sys, ipaddress
zone = sys.argv[1]; eips = int(sys.argv[2])
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line: continue
    p = line.split("\t")
    if len(p) < 7: continue
    vid, vname, vzone, cidr, avail, rt_id, rt_type = p[:7]
    if vzone != zone: continue
    try:
        if ipaddress.ip_network(cidr).prefixlen > 28: continue
    except ValueError: continue
    try:
        if int(avail) <= eips: continue
    except ValueError: continue
    print("\t".join([vid, vname, cidr, avail, rt_id, rt_type]))
' "$gw_zone" "$gw_eips") || cand_rows=""
    while IFS=$'\t' read -r cand_line; do
      [[ -z "$cand_line" ]] && continue
      local c_vid c_cidr c_avail c_rt c_rt_type
      c_vid=$(printf '%s' "$cand_line" | cut -f1); c_cidr=$(printf '%s' "$cand_line" | cut -f3)
      c_avail=$(printf '%s' "$cand_line" | cut -f4); c_rt=$(printf '%s' "$cand_line" | cut -f5)
      c_rt_type=$(printf '%s' "$cand_line" | cut -f6)
      if [[ "$c_rt_type" != "Custom" ]]; then
        log_info "Candidate ${c_vid} (${c_cidr}, ${c_avail} free IPs) is bound to the SYSTEM route table - cannot reuse without rebinding; skipping."
        continue
      fi
      local drt
      drt=$(route_table_has_default_route "$REGION" "$c_rt")
      if [[ "$drt" == "yes" ]]; then
        log_info "Candidate ${c_vid}: route table ${c_rt} already has a 0.0.0.0/0 entry - skipping."
        continue
      fi
      reuse_vsw="$c_vid"; reuse_vsw_rt="$c_rt"; reuse_vsw_rt_type="$c_rt_type"
      log_info "Reusing existing vswitch ${c_vid} (${c_cidr}, ${c_avail} free IPs) bound to custom table ${c_rt}."
      break
    done <<< "$cand_rows" || true
  fi

  # Step 3: vswitch decision
  local vsw_action="reuse" new_vsw_id=""
  if [[ -z "$reuse_vsw" ]]; then
    vsw_action="create"
    if [[ -z "$VSWITCH_CIDR" ]]; then
      log_error "No reusable vswitch found in ${VPC_ID} zone ${gw_zone} (needs >= /28 with > ${gw_eips} free IPs bound to a clean custom route table). Pass --vswitch-cidr to create one (run 'assess' for free candidates)."
      output_error "MissingVswitchCidr" "No reusable vswitch; --vswitch-cidr is required to create one"
      exit 1
    fi
    if [[ -n "$vs_rows" ]]; then
      local overlap
      overlap=$(printf '%s' "$vs_rows" | python3 -c '
import sys, ipaddress
try: new = ipaddress.ip_network(sys.argv[1])
except ValueError: sys.exit(0)
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line: continue
    p = line.split("\t")
    if len(p) < 4: continue
    try:
        if ipaddress.ip_network(p[3]).overlaps(new):
            print(p[0])
            break
    except ValueError: pass
' "$VSWITCH_CIDR") || overlap=""
      if [[ -n "$overlap" ]]; then
        log_error "CIDR ${VSWITCH_CIDR} overlaps existing vswitch ${overlap}. Pick a free segment (run 'assess' for suggestions)."
        output_error "CidrOverlap" "${VSWITCH_CIDR} overlaps vswitch ${overlap}"
        exit 1
      fi
    fi
  fi

  # Step 4: route table decision. When creating a new vswitch, prefer reusing
  # an ORPHAN custom table (unbound, no default route) - e.g. the
  # Cloud_Firewall_ROUTE_TABLE leftover from a previous firewall deletion.
  local rt_action="reuse" new_rt_id=""
  if [[ -n "$reuse_vsw" ]]; then
    new_rt_id="$reuse_vsw_rt"
  else
    local rt_resp rt_exit=0 orphan_rows=""
    rt_resp=$(call_vpc_api "DescribeRouteTableList" --RegionId "$REGION" --VpcId "$VPC_ID" --PageSize 50 2>/dev/null) || rt_exit=$?
    if [[ $rt_exit -eq 0 ]]; then
      orphan_rows=$(json_parse "$rt_resp" "'\\n'.join('\\t'.join([t.get('RouteTableId',''), str(t.get('RouteTableName','')).replace('\\t',' ')]) for t in d.get('RouterTableList', {}).get('RouterTableListType', []) if t.get('RouteTableType') == 'Custom' and not t.get('VSwitchIds', {}).get('VSwitchId', []))") || orphan_rows=""
    else
      log_warn "Could not list route tables (missing vpc:DescribeRouteTableList?); will create a new one."
    fi
    local orphan_line
    while IFS=$'\t' read -r orphan_line; do
      [[ -z "$orphan_line" ]] && continue
      local o_id o_name drt2
      o_id=$(printf '%s' "$orphan_line" | cut -f1); o_name=$(printf '%s' "$orphan_line" | cut -f2)
      drt2=$(route_table_has_default_route "$REGION" "$o_id")
      [[ "$drt2" == "yes" ]] && continue
      new_rt_id="$o_id"; rt_action="reuse_orphan"
      log_info "Reusing orphan custom route table ${o_id} (${o_name:-unnamed}): unbound and no 0.0.0.0/0 entry."
      break
    done <<< "$orphan_rows" || true
    [[ -z "$new_rt_id" ]] && rt_action="create"
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing preparation plan"
    if [[ "$vsw_action" == "reuse" ]]; then
      echo "# vswitch: REUSE ${reuse_vsw} (already bound to ${reuse_vsw_rt})"
    else
      echo "aliyun Vpc CreateVSwitch --RegionId '${REGION}' --ZoneId '${gw_zone}' --VpcId '${VPC_ID}' --CidrBlock '${VSWITCH_CIDR}' --VSwitchName '${VSWITCH_NAME}'"
    fi
    case "$rt_action" in
      reuse) echo "# route table: REUSE ${new_rt_id} (already bound to the vswitch)" ;;
      reuse_orphan) echo "aliyun Vpc AssociateRouteTable --RegionId '${REGION}' --RouteTableId '${new_rt_id}' --VSwitchId <new vswitch id>" ;;
      create)
        echo "aliyun Vpc CreateRouteTable --RegionId '${REGION}' --VpcId '${VPC_ID}' --RouteTableName '${RT_NAME}'"
        echo "aliyun Vpc AssociateRouteTable --RegionId '${REGION}' --RouteTableId <new table id> --VSwitchId <new vswitch id>"
        ;;
    esac
    exit 0
  fi

  if [[ "$YES" != "true" ]]; then
    log_error "prepare creates VPC resources. Pass --yes to confirm."
    output_error "NotConfirmed" "Operation requires --yes flag to confirm"
    exit 1
  fi

  # Step 5: execute
  if [[ "$vsw_action" == "create" ]]; then
    log_info "Creating vswitch ${VSWITCH_CIDR} (${VSWITCH_NAME}) in zone ${gw_zone} ..."
    local cv_resp cv_exit=0
    cv_resp=$(call_vpc_api "CreateVSwitch" --RegionId "$REGION" --ZoneId "$gw_zone" --VpcId "$VPC_ID" --CidrBlock "$VSWITCH_CIDR" --VSwitchName "$VSWITCH_NAME") || cv_exit=$?
    if [[ $cv_exit -ne 0 ]]; then
      local cv_err cv_msg
      cv_err=$(extract_api_error_code "$cv_resp"); cv_msg=$(extract_api_error_message "$cv_resp")
      if [[ "$cv_err" == "Forbidden.RAM" || "$cv_err" == *NoPermission* ]]; then
        log_error "Missing permission vpc:CreateVSwitch. Run 'validate-cli.sh --check-permission --mode manual' to see the full list, then grant and retry."
      fi
      output_error "${cv_err:-UnknownError}" "${cv_msg:-CreateVSwitch failed}"
      exit 2
    fi
    new_vsw_id=$(json_parse "$cv_resp" "d.get('VSwitchId', '')")
    log_info "Vswitch created: ${new_vsw_id}"
  else
    new_vsw_id="$reuse_vsw"
  fi

  if [[ "$rt_action" == "create" ]]; then
    log_info "Creating custom route table ${RT_NAME} ..."
    local cr_resp cr_exit=0
    cr_resp=$(call_vpc_api "CreateRouteTable" --RegionId "$REGION" --VpcId "$VPC_ID" --RouteTableName "$RT_NAME") || cr_exit=$?
    if [[ $cr_exit -ne 0 ]]; then
      local cr_err cr_msg
      cr_err=$(extract_api_error_code "$cr_resp"); cr_msg=$(extract_api_error_message "$cr_resp")
      if [[ "$cr_err" == "Forbidden.RAM" || "$cr_err" == *NoPermission* ]]; then
        log_error "Missing permission vpc:CreateRouteTable. Run 'validate-cli.sh --check-permission --mode manual' to see the full list, then grant and retry."
      fi
      output_error "${cr_err:-UnknownError}" "${cr_msg:-CreateRouteTable failed}"
      exit 2
    fi
    new_rt_id=$(json_parse "$cr_resp" "d.get('RouteTableId', '')")
    log_info "Route table created: ${new_rt_id}"
  fi

  if [[ "$rt_action" == "create" || "$rt_action" == "reuse_orphan" || "$vsw_action" == "create" ]]; then
    if [[ "$rt_action" != "reuse" ]]; then
      log_info "Binding route table ${new_rt_id} to vswitch ${new_vsw_id} ..."
      local ab_resp ab_exit=0
      ab_resp=$(call_vpc_api "AssociateRouteTable" --RegionId "$REGION" --RouteTableId "$new_rt_id" --VSwitchId "$new_vsw_id") || ab_exit=$?
      if [[ $ab_exit -ne 0 ]]; then
        local ab_err ab_msg
        ab_err=$(extract_api_error_code "$ab_resp"); ab_msg=$(extract_api_error_message "$ab_resp")
        if [[ "$ab_err" == "Forbidden.RAM" || "$ab_err" == *NoPermission* ]]; then
          log_error "Missing permission vpc:AssociateRouteTable. Run 'validate-cli.sh --check-permission --mode manual' to see the full list, then grant and retry."
        fi
        output_error "${ab_err:-UnknownError}" "${ab_msg:-AssociateRouteTable failed}"
        exit 2
      fi
    fi
  fi

  cat <<EOF
{
  "success": true,
  "action": "prepare",
  "vswitch": {"id": "${new_vsw_id}", "action": "${vsw_action}"},
  "route_table": {"id": "${new_rt_id}", "action": "${rt_action}"},
  "gateway": {"nat_gateway_id": "${NAT_GATEWAY_ID}", "zone": "${gw_zone}", "eip_count": ${gw_eips}},
  "next_step": "nat-fw-lifecycle.sh create --nat-gateway-id ${NAT_GATEWAY_ID} --region ${REGION} --vpc-id ${VPC_ID} --proxy-name <name> --vswitch-id ${new_vsw_id} --yes",
  "note": "Both assets are USER-owned. Deleting the NAT firewall later will NOT reclaim them."
}
EOF
}

# --- Main Router ---

SUBCOMMAND="${1:-}"
if [[ -z "$SUBCOMMAND" || "$SUBCOMMAND" == "--help" || "$SUBCOMMAND" == "-h" ]]; then
  show_main_help
fi
shift

case "$SUBCOMMAND" in
  precheck)
    cmd_precheck "$@"
    ;;
  quota)
    cmd_quota "$@"
    ;;
  assess)
    cmd_assess "$@"
    ;;
  prepare)
    cmd_prepare "$@"
    ;;
  route-diff)
    cmd_route_diff "$@"
    ;;
  create)
    cmd_create "$@"
    ;;
  delete)
    cmd_delete "$@"
    ;;
  update)
    cmd_update "$@"
    ;;
  *)
    log_error "Unknown subcommand: ${SUBCOMMAND}"
    log_error "Run 'nat-fw-lifecycle.sh --help' for usage"
    exit 1
    ;;
esac
