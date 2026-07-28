#!/usr/bin/env bash
# ALB Ingress Quick Diagnostic Script
# Usage: bash diagnose.sh <command> [args...]
#
# Commands:
#   check                           - Check environment
#   events <kind> <name> [-n ns]    - Get resource events
#   config <kind> <name> [-n ns]    - Get resource configuration
#   scan [-n ns]                    - Scan all Warning events
#   match <error_message>           - Match known error patterns

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KNOWLEDGE_DIR="${SCRIPT_DIR}/../references"

# ============================================================
# check - Check kubectl environment
# ============================================================
cmd_check() {
    echo "=== Environment Check ==="

    # kubectl
    if command -v kubectl &>/dev/null; then
        local ver
        ver=$(kubectl version --client -o json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('clientVersion',{}).get('gitVersion','unknown'))" 2>/dev/null || echo "unknown")
        echo "[OK] kubectl: ${ver}"
    else
        echo "[FAIL] kubectl not installed"
        echo "  macOS: brew install kubectl"
        echo "  Linux: curl -LO https://dl.k8s.io/release/\$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        return 1
    fi

    # kubeconfig
    local kubeconfig="${KUBECONFIG:-$HOME/.kube/config}"
    if [[ -f "$kubeconfig" ]]; then
        echo "[OK] kubeconfig: ${kubeconfig}"
    else
        echo "[FAIL] kubeconfig not found: ${kubeconfig}"
        echo "  Download from ACK console: Container Service -> Cluster -> Connection Info"
        echo "  Or run cluster_connect.sh to fetch kubeconfig for all clusters"
        return 1
    fi

    # ACK cluster kubeconfig detection
    local ack_configs
    ack_configs=$(ls "$HOME/.kube/ack-"*.yaml 2>/dev/null || true)
    if [[ -n "$ack_configs" ]]; then
        local count
        count=$(echo "$ack_configs" | wc -l | tr -d ' ')
        echo "[INFO] Detected ${count} ACK cluster kubeconfig(s)"
        if [[ -n "${KUBECONFIG:-}" && "$KUBECONFIG" == *"/ack-"* ]]; then
            echo "[OK] Currently using: $(basename "$KUBECONFIG")"
        fi
    fi

    # Cluster connection
    if kubectl cluster-info &>/dev/null; then
        echo "[OK] Cluster connection OK"
    else
        echo "[FAIL] Cannot connect to cluster"
        return 1
    fi

    # ALB Ingress Controller
    local alb_pods
    alb_pods=$(kubectl get pods -n kube-system -l app=load-balancer-controller -o name 2>/dev/null | head -1 || true)
    if [[ -n "$alb_pods" ]]; then
        echo "[OK] ALB Ingress Controller Running"
    else
        alb_pods=$(kubectl get pods -n kube-system 2>/dev/null | grep -i alb || true)
        if [[ -n "$alb_pods" ]]; then
            echo "[OK] Related Pod exists"
        else
            echo "[WARN] ALB Ingress Controller Pod not detected"
        fi
    fi

    echo ""
    echo "=== Cluster Resource Overview ==="
    local albconfig_count ingress_count
    albconfig_count=$(kubectl get albconfig.alibabacloud.com --all-namespaces --no-headers 2>/dev/null | wc -l | tr -d ' ')
    ingress_count=$(kubectl get ingress --all-namespaces --no-headers 2>/dev/null | wc -l | tr -d ' ')
    echo "AlbConfig Count: ${albconfig_count}"
    echo "Ingress Count: ${ingress_count}"
}

# ============================================================
# events - Get events for specified resource
# ============================================================
cmd_events() {
    local kind="${1:-}"
    local name="${2:-}"
    local namespace="default"

    shift 2 2>/dev/null || true
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -n|--namespace) namespace="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [[ -z "$kind" || -z "$name" ]]; then
        echo "Usage: diagnose.sh events <Ingress|AlbConfig> <name> [-n namespace]"
        return 1
    fi

    # Validate inputs: allow only alphanumeric, dash, dot, and slash
    if ! echo "$name" | grep -qE '^[a-zA-Z0-9./_-]+$'; then
        echo "Invalid resource name: $name (only alphanumeric, dash, dot, underscore, slash allowed)"
        return 1
    fi
    if ! echo "$namespace" | grep -qE '^[a-zA-Z0-9.-]+$'; then
        echo "Invalid namespace: $namespace"
        return 1
    fi

    # Normalize kind (use tr for bash 3.x compatibility)
    local kind_lower
    kind_lower=$(echo "$kind" | tr '[:upper:]' '[:lower:]')
    local k8s_kind
    case "$kind_lower" in
        ingress)   k8s_kind="Ingress" ;;
        albconfig) k8s_kind="AlbConfig" ;;
        *)         k8s_kind="$kind" ;;
    esac

    echo "=== Events for ${k8s_kind}/${name} (ns: ${namespace}) ==="
    echo ""

    kubectl get events -n "$namespace" \
        --field-selector "involvedObject.name=${name},involvedObject.kind=${k8s_kind}" \
        --sort-by=.lastTimestamp 2>/dev/null || \
    kubectl get events -n "$namespace" \
        --field-selector "involvedObject.name=${name}" \
        --sort-by=.lastTimestamp 2>/dev/null

    echo ""
    echo "=== Warning Event Details ==="
    kubectl get events -n "$namespace" \
        --field-selector "involvedObject.name=${name},type=Warning" \
        -o json 2>/dev/null | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('items', [])
warnings = [i for i in items if i.get('type') == 'Warning']
if not warnings:
    print('No Warning events')
else:
    for w in warnings:
        print('---')
        print(f\"Reason: {w.get('reason', 'N/A')}\")
        print(f\"Message: {w.get('message', 'N/A')}\")
        print(f\"Count: {w.get('count', 1)}\")
        print(f\"Last: {w.get('lastTimestamp', 'N/A')}\")
" 2>/dev/null || echo "(Parse failed, please check raw events above)"
}

# ============================================================
# config - Get resource full configuration
# ============================================================
cmd_config() {
    local kind="${1:-}"
    local name="${2:-}"
    local namespace="default"

    shift 2 2>/dev/null || true
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -n|--namespace) namespace="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [[ -z "$kind" || -z "$name" ]]; then
        echo "Usage: diagnose.sh config <ingress|albconfig> <name> [-n namespace]"
        return 1
    fi

    # Validate inputs
    if ! echo "$name" | grep -qE '^[a-zA-Z0-9./_-]+$'; then
        echo "Invalid resource name: $name"
        return 1
    fi
    if ! echo "$namespace" | grep -qE '^[a-zA-Z0-9.-]+$'; then
        echo "Invalid namespace: $namespace"
        return 1
    fi

    local kind_lower
    kind_lower=$(echo "$kind" | tr '[:upper:]' '[:lower:]')
    case "$kind_lower" in
        ingress)
            echo "=== Ingress ${namespace}/${name} Configuration ==="
            kubectl get ingress -n "$namespace" "$name" -o yaml
            ;;
        albconfig)
            echo "=== AlbConfig ${name} Configuration ==="
            kubectl get albconfig.alibabacloud.com "$name" -o yaml 2>/dev/null || \
            kubectl get albconfig.alibabacloud.com -n "$namespace" "$name" -o yaml
            ;;
        service|svc)
            echo "=== Service ${namespace}/${name} Configuration ==="
            kubectl describe svc -n "$namespace" "$name"
            ;;
        ingressclass)
            echo "=== IngressClass ${name} ==="
            kubectl get ingressclass "$name" -o yaml
            ;;
        *)
            echo "Unsupported resource type: $kind"
            return 1
            ;;
    esac
}

# ============================================================
# scan - Scan all ALB-related Warning events
# ============================================================
cmd_scan() {
    local namespace=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -n|--namespace) namespace="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    echo "=== Scan ALB Ingress Reconcile Warning Events ==="
    echo ""

    local ns_flag="--all-namespaces"
    [[ -n "$namespace" ]] && ns_flag="-n $namespace"

    # Get AlbConfig Warning events
    echo "--- AlbConfig Warning Events ---"
    kubectl get events $ns_flag --field-selector "type=Warning" -o json 2>/dev/null | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('items', [])
alb_warnings = []
alb_reasons = ('SyncError', 'Failed', 'Warning', 'ReconcileError', 'FailedBuildModel', 'FailedApplyModel')
for i in items:
    obj = i.get('involvedObject', {})
    kind = obj.get('kind', '')
    if kind in ('AlbConfig', 'Ingress'):
        reason = i.get('reason', '')
        if reason in alb_reasons or reason.startswith('Failed'):
            alb_warnings.append(i)
if not alb_warnings:
    print('No ALB-related Warning events found')
else:
    print(f'Found {len(alb_warnings)} ALB-related Warning events:')
    print()
    for w in alb_warnings[-20:]:
        obj = w.get('involvedObject', {})
        ns = obj.get('namespace', 'N/A')
        print(f\"[{obj.get('kind')}/{obj.get('name')}] (ns: {ns})\")
        print(f\"  Message: {w.get('message', 'N/A')[:200]}\")
        print(f\"  Count: {w.get('count', 1)}  Last: {w.get('lastTimestamp', 'N/A')}\")
        print()
" 2>/dev/null || echo "(Parse failed)"
}

# ============================================================
# match - Match known error patterns
# ============================================================
cmd_match() {
    local message="$*"

    if [[ -z "$message" ]]; then
        echo "Usage: diagnose.sh match <error_message>"
        return 1
    fi

    local tree_file="${KNOWLEDGE_DIR}/diagnostic_tree.json"
    if [[ ! -f "$tree_file" ]]; then
        echo "Knowledge base file not found: ${tree_file}"
        return 1
    fi

    # Pass message via stdin to prevent command injection in string interpolation
    echo "$message" | python3 -c "
import json, re, sys

message = sys.stdin.read().strip()
if not message:
    print('Empty error message')
    sys.exit(1)

tree_file = '''$tree_file'''
with open(tree_file, 'r') as f:
    tree = json.load(f)

matched = False
for cat in tree.get('categories', []):
    for err in cat.get('errors', []):
        try:
            if re.search(err['regex'], message, re.IGNORECASE | re.DOTALL):
                matched = True
                print(f\"=== Matched: {err['id']} ===\")
                print(f\"Category: {cat['name']}\")
                print(f\"Severity: {err.get('severity', 'N/A')}\")
                print(f\"Error template: {err.get('message_template', 'N/A')}\")
                print()
                for cause in err.get('causes', []):
                    print(f\"--- Cause {cause['cause_id']}: {cause['summary']} ---\")
                    print(f\"Description: {cause['description']}\")
                    diag = cause.get('diagnostic', {})
                    if diag.get('commands'):
                        print(f\"Diagnostic commands:\")
                        for cmd in diag['commands']:
                            print(f\"  \$ {cmd}\")
                    sol = cause.get('solution')
                    sols = cause.get('solution_options', [])
                    if sol:
                        print(f\"Solution: {sol['title']}\")
                        if sol.get('steps'):
                            for s in sol['steps']:
                                print(f\"  - {s}\")
                        if sol.get('yaml_example'):
                            print(f\"Config example:\")
                            print(sol['yaml_example'])
                    for s in sols:
                        rec = ' (recommended)' if s.get('recommended') else ''
                        print(f\"Option{s['index']}{rec}: {s['title']}\")
                    print()
                break
        except re.error:
            continue
    if matched:
        break

if not matched:
    print('No known error pattern matched')
    print('Suggested checks:')
    print('  1. Ingress/AlbConfig YAML configuration correctness')
    print('  2. IngressClass association with AlbConfig')
    print('  3. ALB Ingress Controller Pod logs')
" 2>/dev/null
}

# ============================================================
# Main entry
# ============================================================
main() {
    local cmd="${1:-help}"
    shift 2>/dev/null || true

    case "$cmd" in
        check)  cmd_check "$@" ;;
        events) cmd_events "$@" ;;
        config) cmd_config "$@" ;;
        scan)   cmd_scan "$@" ;;
        match)  cmd_match "$@" ;;
        help|--help|-h)
            echo "ALB Ingress Diagnostic Tool"
            echo ""
            echo "Usage: bash diagnose.sh <command> [args...]"
            echo ""
            echo "Commands:"
            echo "  check                           Check environment"
            echo "  events <kind> <name> [-n ns]    Get resource events"
            echo "  config <kind> <name> [-n ns]    Get resource configuration"
            echo "  scan [-n ns]                    Scan all Warning events"
            echo "  match <error_message>           Match known error patterns"
            ;;
        *)
            echo "Unknown command: $cmd"
            echo "Run 'diagnose.sh help' to view help"
            return 1
            ;;
    esac
}

main "$@"
