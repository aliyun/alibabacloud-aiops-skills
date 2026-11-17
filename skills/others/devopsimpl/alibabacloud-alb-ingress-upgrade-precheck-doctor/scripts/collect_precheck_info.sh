#!/usr/bin/env bash
# collect_precheck_info.sh
# ALB Ingress Controller upgrade precheck information collection script
# Usage: bash collect_precheck_info.sh --cluster-id <id> --region <region> [--alb-id <lb_id>] [--profile <name>]
#
# kubectl is optional: when kubectl is missing or cannot reach the cluster, the
# kubectl-based sections (Warning events, AlbConfig) are skipped and the script
# continues with aliyun CLI only (version, SLS DryRun logs, ALB configuration).
#
# Collected information:
#   1. ALB Ingress Controller current installed version
#   2. Latest 50 Warning events in kube-system namespace
#   3. AlbConfig list and associated ALB instance IDs
#   4. ALB instance basic attributes (name, edition, network type, etc.)
#   5. Listener details (port, protocol, certificate, ACL binding, compression, etc.)
#   6. ACL details (name, type, entry list)
#   7. Server group details and backend servers (scheduler, health check, sticky session, backends)

set -euo pipefail

# ============================================================
# Argument Parsing
# ============================================================
CLUSTER_ID=""
REGION=""
PROFILE=""
ALB_ID=""
KUBECTL_OK=false

usage() {
    echo "Usage: bash collect_precheck_info.sh --cluster-id <cluster_id> --region <region_id> [--alb-id <lb_id>] [--profile <aliyun_profile>]"
    echo ""
    echo "Options:"
    echo "  --cluster-id   ACK cluster ID (required)"
    echo "  --region       Alibaba Cloud region (required, e.g. cn-hangzhou)"
    echo "  --alb-id       ALB instance ID managed by AlbConfig (optional, skips AlbConfig lookup)"
    echo "  --profile      aliyun CLI profile (optional, defaults to active profile)"
    echo "  -h, --help     Show help"
    exit 0
}

require_value() {
    if [[ $# -lt 2 || -z "$2" || "$2" == -* ]]; then
        echo "Error: $1 requires a value" >&2
        exit 1
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cluster-id) require_value "$@"; CLUSTER_ID="$2"; shift 2 ;;
        --region)     require_value "$@"; REGION="$2";     shift 2 ;;
        --alb-id)     require_value "$@"; ALB_ID="$2";     shift 2 ;;
        --profile)    require_value "$@"; PROFILE="$2";    shift 2 ;;
        -h|--help)    usage ;;
        *) echo "Unknown argument: $1" >&2; echo "Run --help for usage" >&2; exit 1 ;;
    esac
done

if [[ -z "$CLUSTER_ID" || -z "$REGION" ]]; then
    echo "Error: --cluster-id and --region are required" >&2
    echo "Run bash collect_precheck_info.sh --help for usage" >&2
    exit 1
fi

# ============================================================
# Input allowlist: Agent/user arguments are only passed to the CLI and SLS as resource IDs;
# values that do not match the expected format are rejected before any external command runs.
# ============================================================
validate_arg() {
    local name="$1" value="$2" pattern="$3"
    if [[ ! "$value" =~ $pattern ]]; then
        echo "Error: invalid $name '$value' (expected pattern $pattern)" >&2
        exit 1
    fi
}

validate_arg "--cluster-id" "$CLUSTER_ID" '^[a-z0-9]{8,64}$'
validate_arg "--region"     "$REGION"     '^[a-z]{2,4}(-[a-z0-9]{1,16}){1,4}$'
if [[ -n "$ALB_ID" ]]; then
    validate_arg "--alb-id" "$ALB_ID" '^alb-[a-z0-9]{8,64}$'
fi
if [[ -n "$PROFILE" ]]; then
    validate_arg "--profile" "$PROFILE" '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'
    [[ "$PROFILE" != *..* ]] || { echo "Error: invalid --profile" >&2; exit 1; }
fi

# IDs taken from API/kubectl output must pass validation too and may never start with an option prefix.
is_safe_id() {
    [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9-]{0,63}$ ]]
}

# ============================================================
# Observability: session ID and skill version (failure gate, runs before any cloud call)
# ============================================================
# Fresh random 32-character lowercase hex session ID, reused by every CLI call of this run.
if ! SESSION_ID=$(python3 -c 'import secrets; print(secrets.token_hex(16))' 2>/dev/null); then
    echo "Error: failed to generate session ID; aborting before any cloud call" >&2
    exit 1
fi
if [[ ! "$SESSION_ID" =~ ^[0-9a-f]{32}$ ]]; then
    echo "Error: failed to generate a 32-character lowercase hex session ID; aborting before any cloud call" >&2
    exit 1
fi

# Skill version from references/manifest.json; a missing or invalid manifest stops the run.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_FILE="$SCRIPT_DIR/../references/manifest.json"
if ! SKILL_VERSION=$(python3 -c '
import json, re, sys
with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
version = data.get("version") if isinstance(data, dict) else None
pattern = r"[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?"
if not isinstance(version, str) or re.fullmatch(pattern, version) is None:
    sys.exit(1)
print(version)
' "$MANIFEST_FILE" 2>/dev/null); then
    echo "Error: cannot read a valid 'version' from $MANIFEST_FILE; aborting before any cloud call" >&2
    exit 1
fi
PERMISSION_ERROR_PATTERN='Forbidden|NoPermission|Unauthorized|NotAuthorized|AccessDenied'
PLUGIN_MISSING_PATTERN="Plugin '(aliyun-cli-[a-z0-9-]+)' is required"
# Missing plugins are recorded here (calls run in subshells) and reported once at the end
MISSING_PLUGIN_DIR=$(mktemp -d)
trap 'rm -rf "$MISSING_PLUGIN_DIR"' EXIT


# ============================================================
# Helper Functions
# ============================================================

# Plugin-mode (lowercase-hyphenated) commands only. stdin is /dev/null, so a missing plugin
# can never be installed through the CLI's interactive prompt; the command just fails and
# the user is told which plugin to install (references/cli-installation-guide.md).
aliyun_cmd() {
    local cmd=(aliyun "$@")
    cmd+=(--read-timeout 30 --connect-timeout 10 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-alb-ingress-upgrade-precheck-doctor/$SESSION_ID skill-version/$SKILL_VERSION")
    [[ -n "$PROFILE" ]] && cmd+=(--profile "$PROFILE")
    local out rc=0
    out=$("${cmd[@]}" </dev/null 2>&1) || rc=$?
    if [[ "$out" =~ $PLUGIN_MISSING_PATTERN ]]; then
        : > "$MISSING_PLUGIN_DIR/${BASH_REMATCH[1]}"
    fi
    printf '%s\n' "$out"
    return "$rc"
}

# ALB read-only OpenAPI via the aliyun-cli-alb plugin
alb_cmd() {
    aliyun_cmd alb "$@" --region "$REGION"
}

section() {
    echo ""
    echo "=================================================================="
    echo "# $1"
    echo "=================================================================="
}

# ============================================================
# Prerequisites Check
# ============================================================
check_prerequisites() {
    local has_error=false

    for tool in aliyun python3; do
        if ! command -v "$tool" &>/dev/null; then
            echo "[FAIL] $tool is not installed or not in PATH" >&2
            has_error=true
        fi
    done

    if [[ "$has_error" == "true" ]]; then
        echo "Please install missing tools and retry" >&2
        exit 1
    fi

    # Only the local CLI version is checked; plugins are not prechecked. A missing plugin is reported by
    # aliyun_cmd after the call fails. The script never installs plugins (stdin is /dev/null, so the
    # CLI install prompt can never be answered).
    local cli_version
    cli_version=$(aliyun version) || { echo "[FAIL] Cannot inspect aliyun CLI version" >&2; exit 1; }
    if ! python3 -c 'import re,sys; m=re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", sys.argv[1].strip()); sys.exit(0 if m and tuple(map(int,m.groups())) >= (3,3,3) else 1)' "$cli_version"; then
        echo "[FAIL] aliyun CLI >= 3.3.3 is required; see references/cli-installation-guide.md" >&2
        exit 1
    fi

    # kubectl is optional: degrade to aliyun CLI only when it is unavailable
    if ! command -v kubectl &>/dev/null; then
        echo "[WARN] kubectl is not installed, skipping kubectl-based sections (Warning events, AlbConfig)"
    elif ! kubectl cluster-info --request-timeout=10s &>/dev/null; then
        echo "[WARN] kubectl cannot connect to cluster, skipping kubectl-based sections (Warning events, AlbConfig)"
    else
        KUBECTL_OK=true
    fi
}

# Resolve ALB instance IDs: --alb-id > AlbConfig status > ListLoadBalancers in region
resolve_lb_ids() {
    if [[ -n "$ALB_ID" ]]; then
        echo "$ALB_ID"
        return
    fi

    local ids=""
    if [[ "$KUBECTL_OK" == "true" ]]; then
        ids=$(kubectl get albconfig.alibabacloud.com --all-namespaces -o json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
ids = []
for item in data.get('items', []):
    lb_id = item.get('status', {}).get('loadBalancer', {}).get('id', '')
    if lb_id and lb_id not in ids:
        ids.append(lb_id)
for i in ids:
    print(i)
" 2>/dev/null) || true
    fi

    if [[ -z "$ids" ]]; then
        ids=$(alb_cmd list-load-balancers --max-results 20 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
for lb in (data.get('LoadBalancers', []) or [])[:5]:
    if lb.get('LoadBalancerId'):
        print(lb['LoadBalancerId'])
" 2>/dev/null) || true
    fi
    echo "$ids"
}

# ============================================================
# Step 1: ALB Ingress Controller Version
# ============================================================
collect_controller_version() {
    section "ALB Ingress Controller Version Info"

    local result
    result=$(aliyun_cmd cs describe-cluster-addons-version \
        --cluster-id "$CLUSTER_ID" \
        --region "$REGION" 2>&1) || true

    if echo "$result" | python3 -c "
import sys, json
raw = sys.stdin.read()
try:
    data = json.loads(raw)
    addons = data.get('addons') if isinstance(data, dict) else data
    if addons is None and isinstance(data, dict):
        # Response keyed by component name: {\"alb-ingress-controller\": {...}}
        addons = [dict(v, component_id=k) for k, v in data.items() if isinstance(v, dict)]
    if not addons:
        print('[INFO] alb-ingress-controller component not found, may not be installed')
    else:
        for a in addons:
            print(f\"Component: {a.get('component_id', a.get('component_name', 'N/A'))}\")
            print(f\"Current Version: {a.get('current_version', a.get('version', 'N/A'))}\")
            print(f\"Latest Version: {a.get('next_version', a.get('latest_version', 'N/A'))}\")
            print(f\"Upgrade Available: {a.get('can_upgrade', 'N/A')}\")
except (json.JSONDecodeError, ValueError, AttributeError):
    print('[WARN] Response parse failed, raw output:')
    print(raw[:500])
" 2>/dev/null; then
        :
    else
        echo "[WARN] Version query failed, raw output:"
        echo "$result" | head -10
    fi
}

# ============================================================
# Step 2: Warning Events
# ============================================================
collect_warning_events() {
    section "kube-system Warning Events (latest 50)"

    if [[ "$KUBECTL_OK" != "true" ]]; then
        echo "[SKIP] kubectl unavailable, use the SLS DryRun Precheck Logs section below to identify the failed operation"
        return
    fi

    echo "--- AlbConfig Warning Events ---"
    kubectl get events \
        --field-selector "type=Warning,involvedObject.kind=AlbConfig" \
        --sort-by=.lastTimestamp \
        -A 2>/dev/null | tail -30 || echo "[INFO] No AlbConfig Warning events"

    echo ""
    echo "--- Ingress Warning Events ---"
    kubectl get events \
        --field-selector "type=Warning,involvedObject.kind=Ingress" \
        --sort-by=.lastTimestamp \
        -A 2>/dev/null | tail -30 || echo "[INFO] No Ingress Warning events"

    echo ""
    echo "--- kube-system All Warning Events (for precheck failure info) ---"
    kubectl get events -n kube-system \
        --field-selector "type=Warning" \
        --sort-by=.lastTimestamp 2>/dev/null | tail -50 || echo "[INFO] No kube-system Warning events"
}

# ============================================================
# Step 3: AlbConfig List and Associated ALB Instances
# ============================================================
collect_albconfig_info() {
    section "AlbConfig List"

    if [[ "$KUBECTL_OK" != "true" ]]; then
        echo "[SKIP] kubectl unavailable, ask the user for the AlbConfig/Ingress YAML (kubectl get albconfig <name> -o yaml) to compare expected values"
        return
    fi

    local albconfigs
    albconfigs=$(kubectl get albconfig.alibabacloud.com --all-namespaces 2>/dev/null) || true

    if [[ -z "$albconfigs" ]]; then
        echo "[INFO] No AlbConfig resource found in cluster"
        return
    fi

    echo "$albconfigs"
    echo ""

    # Output each AlbConfig detail and extract ALB instance IDs
    while IFS= read -r name; do
        [[ -z "$name" || "$name" == "NAME" ]] && continue
        [[ "$name" =~ ^[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?$ ]] || continue
        echo "--- AlbConfig: $name ---"
        kubectl get albconfig "$name" -o json 2>/dev/null | python3 -c "
import sys, json

data = json.load(sys.stdin)
spec = data.get('spec', {})
status = data.get('status', {})

lb = spec.get('loadBalancer', {})
print(f\"  ALB Instance ID: {status.get('loadBalancer', {}).get('id', '(not created or not synced)')}\")
print(f\"  ALB Name: {lb.get('name', 'N/A')}\")
print(f\"  Edition: {lb.get('edition', 'N/A')}\")
print(f\"  Address Type: {lb.get('addressType', 'N/A')}\")
print(f\"  Deletion Protection: {lb.get('deletionProtectionEnabled', 'N/A')}\")

listeners = spec.get('listeners', [])
print(f\"  Listener Count: {len(listeners)}\")
for l in listeners:
    print(f\"    - Port:{l.get('port','N/A')} Protocol:{l.get('protocol','N/A')}\")
" 2>/dev/null || kubectl get albconfig "$name" -o yaml | head -60
        echo ""
    done < <(kubectl get albconfig.alibabacloud.com --all-namespaces -o custom-columns="NAME:.metadata.name" --no-headers 2>/dev/null)
}

# ============================================================
# Step 4: ALB Instance Attributes (from AlbConfig ALB IDs)
# ============================================================
collect_alb_instance_info() {
    section "ALB Instance Actual Configuration (via aliyun CLI)"

    local lb_ids
    lb_ids=$(resolve_lb_ids)

    if [[ -z "$lb_ids" ]]; then
        echo "[INFO] No ALB instance found in region $REGION, pass --alb-id <lb_id> to specify the AlbConfig-managed instance"
        return
    fi

    while IFS= read -r lb_id; do
        [[ -z "$lb_id" ]] && continue
        is_safe_id "$lb_id" || { echo "[SKIP] Unexpected ALB instance ID format: $lb_id"; continue; }
        echo "--- ALB Instance: $lb_id ---"
        local lb_json
        lb_json=$(alb_cmd get-load-balancer-attribute --load-balancer-id "$lb_id") || {
            if echo "$lb_json" | grep -qi "NotFound"; then
                echo "  [NOT FOUND] ALB instance $lb_id does not exist in $REGION (deleted or wrong region)"
            elif echo "$lb_json" | grep -qiE "$PERMISSION_ERROR_PATTERN"; then
                echo "  [PERMISSION DENIED] Required read-only action: alb:GetLoadBalancerAttribute (see references/ram-policies.md)"
            else
                echo "  [WARN] Failed to query $lb_id details:"
            fi
            echo "$lb_json" | grep -E "ErrorCode|Message" | head -3 | sed 's/^/  /' || true
            echo ""
            continue
        }
        echo "$lb_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
lb = data.get('LoadBalancer', data)
fields = {
    'ALB Instance ID':  lb.get('LoadBalancerId', 'N/A'),
    'ALB Name':         lb.get('LoadBalancerName', 'N/A'),
    'Edition':          lb.get('LoadBalancerEdition', 'N/A'),
    'Status':           lb.get('LoadBalancerStatus', 'N/A'),
    'Address Type':     lb.get('AddressType', 'N/A'),
    'Deletion Protect': str(lb.get('DeletionProtectionConfig', {}).get('Enabled', 'N/A')),
    'Modify Protect':   lb.get('ModificationProtectionConfig', {}).get('Status', 'N/A'),
    'Access Log Project': lb.get('AccessLogConfig', {}).get('LogProject', '(not configured)'),
    'Access Log Store': lb.get('AccessLogConfig', {}).get('LogStore', '(not configured)'),
    'Resource Group':   lb.get('ResourceGroupId', 'N/A'),
}
for k, v in fields.items():
    print(f'  {k}: {v}')
" 2>/dev/null || echo "[WARN] Failed to query $lb_id details"
        echo ""
    done <<< "$lb_ids"
}

# ============================================================
# Step 5: Listener Details (GetListenerAttribute + ListRules)
# ============================================================
collect_listener_details() {
    section "Listener Details (GetListenerAttribute + ListRules)"

    local lb_ids
    lb_ids=$(resolve_lb_ids)

    if [[ -z "$lb_ids" ]]; then
        echo "[INFO] No ALB instance ID found, skipping listener details"
        return
    fi

    while IFS= read -r lb_id; do
        [[ -z "$lb_id" ]] && continue
        is_safe_id "$lb_id" || continue

        echo "--- ALB: $lb_id Listener List ---"
        local listeners_json
        listeners_json=$(alb_cmd list-listeners --load-balancer-ids "$lb_id" 2>/dev/null) || true

        local listener_ids
        listener_ids=$(echo "$listeners_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
listeners = data.get('Listeners', [])
for l in listeners:
    print(l.get('ListenerId', ''))
" 2>/dev/null) || true

        if [[ -z "$listener_ids" ]]; then
            echo "  [INFO] No listeners on this ALB instance"
            continue
        fi

        while IFS= read -r listener_id; do
            [[ -z "$listener_id" ]] && continue
            is_safe_id "$listener_id" || continue
            echo "  Listener ID: $listener_id"
            alb_cmd get-listener-attribute --listener-id "$listener_id" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
l = data.get('Listener', data)
fields = {
    'Listener Port':    l.get('ListenerPort', 'N/A'),
    'Protocol':         l.get('ListenerProtocol', 'N/A'),
    'Default Cert':     (l.get('Certificates') or [{}])[0].get('CertificateId', '(none)'),
    'Extra Certs':      max(len(l.get('Certificates', []) or []) - 1, 0),
    'Gzip Enabled':     str(l.get('GzipEnabled', 'N/A')),
    'HTTP2 Enabled':    str(l.get('Http2Enabled', 'N/A')),
    'Idle Timeout':     l.get('IdleTimeout', 'N/A'),
    'Request Timeout':  l.get('RequestTimeout', 'N/A'),
    'XForwardedFor':  l.get('XForwardedForConfig', {}),
    'ACL Type':         l.get('AclConfig', {}).get('AclType', '(not bound)'),
    'ACL IDs':        [a.get('AclId','') for a in l.get('AclConfig', {}).get('AclRelations', [])] if l.get('AclConfig') else [],
}
for k, v in fields.items():
    print(f'    {k}: {v}')
" 2>/dev/null || echo "    [WARN] Failed to query listener $listener_id"
            echo "    Forwarding Rules:"
            alb_cmd list-rules --listener-ids "$listener_id" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
rules = data.get('Rules', [])
if not rules:
    print('      [INFO] No forwarding rules')
for r in rules[:20]:
    conds = [c.get('Type', '') + ':' + json.dumps(c.get('HostConfig') or c.get('PathConfig') or c.get('HeaderConfig') or {}, ensure_ascii=False) for c in r.get('RuleConditions', [])]
    acts = [a.get('Type', '') for a in r.get('RuleActions', [])]
    print(f\"      - {r.get('RuleId', 'N/A')} name:{r.get('RuleName', '')} priority:{r.get('Priority', 'N/A')} conditions:{conds} actions:{acts}\")
" 2>/dev/null || echo "      [WARN] Failed to query forwarding rules"
        done <<< "$listener_ids"
        echo ""
    done <<< "$lb_ids"
}

# ============================================================
# Step 6: ACL Details (ListAcls + ListAclEntries)
# ============================================================
collect_acl_details() {
    section "ACL Details (ListAcls + ListAclEntries)"

    # List all ACLs in this region
    local acls_json
    acls_json=$(alb_cmd list-acls 2>/dev/null) || true

    local acl_ids
    acl_ids=$(echo "$acls_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
acls = data.get('Acls', [])
for a in acls:
    print(a.get('AclId', ''))
" 2>/dev/null) || true

    if [[ -z "$acl_ids" ]]; then
        echo "[INFO] No ACL access control policies in this region"
        return
    fi

    # ListAcls already returns basic info, parse directly
    echo "$acls_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
acls = data.get('Acls', [])
for a in acls:
    acl_id = a.get('AclId', 'N/A')
    acl_name = a.get('AclName', 'N/A')
    ip_version = a.get('AddressIPVersion', 'N/A')
    print(f'--- ACL: {acl_id} ({acl_name}) ---')
    print(f'  IP Version: {ip_version}')
" 2>/dev/null

    # Query ACL entries one by one
    while IFS= read -r acl_id; do
        [[ -z "$acl_id" ]] && continue
        is_safe_id "$acl_id" || continue
        echo "  ACL $acl_id entries:"
        alb_cmd list-acl-entries --acl-id "$acl_id" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
entries = data.get('AclEntries', [])
if not entries:
    print('    [INFO] No entries')
else:
    for e in entries[:10]:
        print(f'    - {e.get(\"Entry\", \"N/A\")} desc:{e.get(\"Description\", \"\")}')
    if len(entries) > 10:
        print(f'    ... total {len(entries)} entries, showing first 10')
" 2>/dev/null || echo "    [WARN] Failed to query ACL $acl_id entries"
    done <<< "$acl_ids"
    echo ""
}

# ============================================================
# Step 7: SLS Log Query (DryRun Precheck Failure Logs)
# ============================================================
collect_sls_dryrun_logs() {
    section "SLS DryRun Precheck Logs (last 1 hour)"

    local sls_project="k8s-log-${CLUSTER_ID}"
    local sls_logstore="alb-${CLUSTER_ID}"
    local now
    now=$(python3 -c "import time; print(int(time.time()))")
    local from=$((now - 3600))

    # Check if Logstore exists
    local logstore_check
    logstore_check=$(aliyun_cmd sls get-log-store --project "$sls_project" --logstore "$sls_logstore" --region "$REGION" 2>&1) || true

    if echo "$logstore_check" | grep -q '"logstoreName"'; then
        echo "SLS Project: $sls_project"
        echo "SLS Logstore: $sls_logstore"
        echo ""
    elif echo "$logstore_check" | grep -qiE "$PERMISSION_ERROR_PATTERN"; then
        echo "[PERMISSION DENIED] No read access to SLS $sls_project / $sls_logstore"
        echo "Required read-only actions: log:GetLogStore, log:GetLogStoreLogs (see references/ram-policies.md)"
        echo "Raw response: $logstore_check" | head -5
        return
    else
        echo "[WARN] SLS Logstore does not exist or no access: $sls_project / $sls_logstore"
        echo "Raw response: $logstore_check" | head -5
        echo "[INFO] Skipping SLS log collection, please confirm ALB component logs are delivered to SLS"
        return
    fi

    echo "--- DryRun Key Error Logs ---"
    aliyun_cmd sls get-logs \
        --project "$sls_project" \
        --logstore "$sls_logstore" \
        --region "$REGION" \
        --query "DryRun OR FailedPrecheck OR FailedApplyModel OR \"reconcile loadbalancer failed\" OR \"create event finished\"" \
        --from "$from" \
        --to "$now" \
        --line 30 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data:
        print('[INFO] No DryRun related logs in the last 1 hour')
    else:
        for entry in data:
            ts = entry.get('_time_', entry.get('__time__', ''))
            content = entry.get('content', '')
            container = entry.get('_container_name_', '')
            print(f'[{ts}] [{container}] {content}')
            print()
except (json.JSONDecodeError, ValueError) as e:
    print(f'[WARN] SLS log parse failed: {e}')
" 2>/dev/null || echo "[WARN] SLS log query failed"

    echo ""
    echo "--- DryRun Config Comparison Logs (synthesize/unmatch/need to update) ---"
    aliyun_cmd sls get-logs \
        --project "$sls_project" \
        --logstore "$sls_logstore" \
        --region "$REGION" \
        --query "\"Dryrun need\" OR \"synthesize\" OR \"unmatch\" OR \"need to update ALB\" OR \"IsAccessLogTracingConfigNeedUpdate\" OR \"IsListenerExtraCertificatesNeedUpdate\" OR \"need to leave security group\"" \
        --from "$from" \
        --to "$now" \
        --line 20 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data:
        print('[INFO] No config comparison logs in the last 1 hour')
    else:
        for entry in data:
            ts = entry.get('_time_', entry.get('__time__', ''))
            content = entry.get('content', '')
            print(f'[{ts}] {content}')
            print()
except (json.JSONDecodeError, ValueError) as e:
    print(f'[WARN] SLS log parse failed: {e}')
" 2>/dev/null || echo "[WARN] SLS config comparison log query failed"
}

# ============================================================
# Step 8: Server Group Details (ListServerGroups + ListServerGroupServers)
# ============================================================
collect_servergroup_details() {
    section "Server Group Details (ListServerGroups + ListServerGroupServers)"

    # Get all server groups in region, ListServerGroups returns basic attributes
    local sgs_json
    sgs_json=$(alb_cmd list-server-groups 2>/dev/null) || true

    # Parse server group attributes from ListServerGroups result
    local sg_entries
    sg_entries=$(echo "$sgs_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
sgs = data.get('ServerGroups', [])
for sg in sgs:
    sg_id = sg.get('ServerGroupId', '')
    sg_name = sg.get('ServerGroupName', 'N/A')
    sg_type = sg.get('ServerGroupType', 'N/A')
    scheduler = sg.get('Scheduler', 'N/A')
    protocol = sg.get('Protocol', 'N/A')
    hc_enabled = str(sg.get('HealthCheckConfig', {}).get('HealthCheckEnabled', 'N/A'))
    sticky_enabled = str(sg.get('StickySessionConfig', {}).get('StickySessionEnabled', 'N/A'))
    print(f'{sg_id}|{sg_name}|{sg_type}|{scheduler}|{protocol}|{hc_enabled}|{sticky_enabled}')
" 2>/dev/null) || true

    if [[ -z "$sg_entries" ]]; then
        echo "[INFO] No server groups in this region"
        return
    fi

    while IFS='|' read -r sg_id sg_name sg_type scheduler protocol hc_enabled sticky_enabled; do
        [[ -z "$sg_id" ]] && continue
        is_safe_id "$sg_id" || continue
        echo "--- ServerGroup: $sg_id ($sg_name) ---"
        echo "  Type: $sg_type  Scheduler: $scheduler  Protocol: $protocol  HealthCheck: $hc_enabled  Sticky: $sticky_enabled"

        # ListServerGroupServers
        echo "  Backend server list:"
        alb_cmd list-server-group-servers --server-group-id "$sg_id" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
servers = data.get('Servers', [])
if not servers:
    print('    [INFO] No backend servers')
else:
    for s in servers[:10]:
        print(f'    - {s.get(\"ServerId\", \"N/A\")} ip:{s.get(\"ServerIp\", \"N/A\")}:{s.get(\"Port\", \"N/A\")}  Type:{s.get(\"ServerType\", \"N/A\")}  Weight:{s.get(\"Weight\", \"N/A\")}  Status:{s.get(\"Status\", \"N/A\")}')
    if len(servers) > 10:
        print(f'    ... total {len(servers)} servers, showing first 10')
" 2>/dev/null || echo "    [WARN] Failed to query backend servers"
        echo ""
    done <<< "$sg_entries"
}

# ============================================================
# Main Flow
# ============================================================
main() {
    echo "ALB Ingress Controller Upgrade Precheck Information Collection"
    echo "Cluster ID: $CLUSTER_ID  Region: $REGION${ALB_ID:+  ALB ID: $ALB_ID}"
    echo "Collection Time: $(date '+%Y-%m-%d %H:%M:%S')"

    check_prerequisites
    collect_controller_version
    collect_warning_events
    collect_sls_dryrun_logs
    collect_albconfig_info
    collect_alb_instance_info
    collect_listener_details
    collect_acl_details
    collect_servergroup_details

    local missing
    missing=$(ls "$MISSING_PLUGIN_DIR")
    if [[ -n "$missing" ]]; then
        echo ""
        section "[PLUGIN MISSING] aliyun CLI plugins not installed"
        echo "The sections above that depend on these plugins have no data: $(echo $missing)"
        echo "Nothing was installed automatically. Ask the user to install them (references/cli-installation-guide.md):"
        echo "  aliyun plugin install --names $(echo $missing)"
    fi

    echo ""
    section "Collection Complete"
    echo "Based on the information above:"
    echo "1. Check error operation names in Warning events (e.g. UpdateALBListenerAttribute)"
    echo "2. Refer to references/precheck_errors.md to find comparison fields"
    echo "3. Compare AlbConfig/Ingress expected vs ALB actual values to find inconsistencies"
    echo "4. Choose remediation direction and re-run precheck"
}

main
