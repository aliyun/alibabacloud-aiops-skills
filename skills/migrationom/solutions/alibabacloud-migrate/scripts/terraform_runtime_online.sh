#!/usr/bin/env bash
set -euo pipefail

# terraform_runtime_online.sh - Execute Terraform via Alibaba Cloud IaCService
#
# Usage:
#   terraform_runtime_online.sh validate <hcl_file_or_code>
#   terraform_runtime_online.sh plan     <hcl_file_or_code> [existing_state_id]
#   terraform_runtime_online.sh apply    <hcl_file_or_code>                  # fresh apply (first time)
#   terraform_runtime_online.sh apply    <hcl_file_or_code> --state-id <id>  # retry after FAILURE only (not for in-place updates)
#   terraform_runtime_online.sh apply    --state-id <id>                     # apply a previously planned state (after plan)
#   terraform_runtime_online.sh destroy  <state_id>
#   terraform_runtime_online.sh poll     <state_id> [max_attempts] [interval_seconds]
#
# ⚠️  STATE_ID REUSE RULE:
#   - plan  → apply: do NOT pass the plan stateId to apply (IaCService locks plan states)
#   - Once a STATE_ID exists (from a previous apply), ALL subsequent changes to the same
#     deployment MUST reuse it via --state-id, including:
#       • Retrying after a failed/partial apply
#       • Adding new resources to main.tf
#       • Modifying existing resource configuration
#     Only the very first apply of a brand-new deployment runs without --state-id.
#     A fresh apply without --state-id creates a NEW state and causes duplicate resources.
#
#   Online runtime — changing existing infra (e.g. rename):
#     1) plan  <main.tf> <STATE_ID>     # STATE_ID from last successful apply
#     2) apply --state-id <STATE_ID>     # use the STATE_ID printed by plan (materialize plan)
#     Do NOT use: apply main.tf --state-id ... after status is Applied — API returns InvalidOperation.JobStatus.

ENDPOINT="iac.cn-zhangjiakou.aliyuncs.com"
IAC_USER_AGENT="AlibabaCloud-Agent-Skills"
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

# ClientToken (IaC OpenAPI): retry after 5xx with the SAME token; after 2xx success or a 4xx
# failure, the next API invocation must use a NEW token. (TaskStatus lock retry = new token.)

# TF_LOG_REDACT=1 (default): mask IPs and long resource ids in stderr JSON snippets
# Set TF_LOG_REDACT=0 to print raw API responses (avoid in shared logs).

# ---------------------------------------------------------------------------
# Safety: IaC state id format (defense-in-depth for --state-id injection)
# ---------------------------------------------------------------------------
_validate_state_id() {
    local s="${1:-}"
    if [[ ! "$s" =~ ^[A-Za-z0-9_-]+$ ]] || [[ ${#s} -lt 8 ]] || [[ ${#s} -gt 128 ]]; then
        echo "$(_red)Error: invalid state-id format$(_reset)" >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Optional redaction for multi-line strings printed to stderr
# ---------------------------------------------------------------------------
_redact_multiline() {
    if [[ "${TF_LOG_REDACT:-1}" != "1" ]]; then
        cat
        return 0
    fi
    python3 -c '
import re, sys
t = sys.stdin.read()
t = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED-IP]", t)
t = re.sub(r"\b(?:[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12})\b", "[REDACTED-UUID]", t, flags=re.I)
t = re.sub(r"\b\d{12}\b", "[REDACTED-ACCOUNT]", t)
sys.stdout.write(t)
' 2>/dev/null || cat
}

# ---------------------------------------------------------------------------
# Color helpers (degrade gracefully if tput unavailable)
# ---------------------------------------------------------------------------
_green()  { command -v tput &>/dev/null && tput setaf 2; }
_red()    { command -v tput &>/dev/null && tput setaf 1; }
_yellow() { command -v tput &>/dev/null && tput setaf 3; }
_reset()  { command -v tput &>/dev/null && tput sgr0; }

# ---------------------------------------------------------------------------
# Shared helper: resolve file-or-inline input to CODE variable
# ---------------------------------------------------------------------------
_read_input() {
    local input="$1"
    if [[ -f "$input" ]]; then
        cat "$input"
    else
        printf '%s' "$input"
    fi
}

_iac_new_client_token() { uuidgen; }

# First StatusCode: NNN in aliyun CLI / SDK error text; empty if unknown
_iac_http_status_from_output() {
    printf '%s' "${1:-}" | python3 -c "
import re, sys
t = sys.stdin.read()
m = re.search(r'StatusCode:\s*(\d{3})\b', t)
print(m.group(1) if m else '')
" 2>/dev/null || true
}

_iac_is_5xx() { [[ "${1:-}" =~ ^5[0-9]{2}$ ]]; }

# stdin = execute-* API body (NDJSON lines and/or single JSON object, pretty or minified)
# $1 = optional fallback when stateId missing (e.g. destroy passes original state_id)
_iac_extract_state_id() {
    FALLBACK_ID="${1:-}" python3 -c "
import json, os, sys
raw = sys.stdin.read()
fb = os.environ.get('FALLBACK_ID', '') or ''
sid = ''
for line in raw.splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
        inner = d.get('data', d)
        s = inner.get('stateId')
        if s:
            sid = str(s)
    except Exception:
        pass
if not sid:
    try:
        d = json.loads(raw)
        inner = d.get('data', d)
        s = inner.get('stateId', '')
        if s:
            sid = str(s)
    except Exception:
        pass
if not sid:
    i = raw.find('{')
    if i >= 0:
        try:
            d = json.loads(raw[i:])
            inner = d.get('data', d)
            s = inner.get('stateId', '')
            if s:
                sid = str(s)
        except Exception:
            pass
print(sid or fb)
" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# cmd: validate
# ---------------------------------------------------------------------------
cmd_validate() {
    if [[ $# -lt 1 || "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "Usage: $0 validate <hcl_file_or_code>"
        echo "Exit 0 = Validated, 1 = Errored"
        exit 1
    fi

    local input="$1"
    local code
    code=$(_read_input "$input")
    echo "Validating: $input" >&2

    local token response status message ec http attempt
    token="$(_iac_new_client_token)"
    attempt=0
    ec=1
    while [[ $attempt -lt 10 ]]; do
        attempt=$((attempt + 1))
        ec=0
        response=$(aliyun iacservice validate-module \
            --endpoint "$ENDPOINT" \
            --user-agent "$IAC_USER_AGENT" \
            --client-token "$token" \
            --source Upload \
            --code "$code" 2>&1) || ec=$?
        if [[ $ec -eq 0 ]]; then
            break
        fi
        http=$(_iac_http_status_from_output "$response")
        if _iac_is_5xx "$http"; then
            echo "$(_yellow)[Retry $attempt/10] validate-module HTTP $http — same ClientToken$(_reset)" >&2
            sleep $((attempt * 2))
            continue
        fi
        echo "$(_red)Error: validate-module failed$(_reset)" >&2
        echo "$response" | _redact_multiline >&2
        exit 1
    done
    if [[ $ec -ne 0 ]]; then
        echo "$(_red)Error: validate-module failed after HTTP 5xx retries$(_reset)" >&2
        echo "$response" | _redact_multiline >&2
        exit 1
    fi

    # validate-module may stream multiple JSON lines; status lives under data.*
    status=$(echo "$response" | python3 -c "
import sys,json
st='Unknown'
for line in sys.stdin.read().splitlines():
    line=line.strip()
    if not line:
        continue
    try:
        d=json.loads(line)
        inner=d.get('data',d)
        s=inner.get('status')
        if s:
            st=str(s)
    except Exception:
        pass
print(st)
" 2>/dev/null) || status="Unknown"

    message=$(echo "$response" | python3 -c "
import sys,json
msg=''
for line in sys.stdin.read().splitlines():
    line=line.strip()
    if not line:
        continue
    try:
        d=json.loads(line)
        inner=d.get('data',d)
        m=inner.get('message')
        if m is not None:
            msg=str(m)
    except Exception:
        pass
print(msg)
" 2>/dev/null) || message=""

    echo "" >&2
    if [[ "$status" == "Validated" ]]; then
        echo "$(_green)Validated$(_reset)" >&2
        [[ -n "$message" ]] && echo "$message" >&2
        exit 0
    else
        echo "$(_red)Validation failed: $status$(_reset)" >&2
        [[ -n "$message" ]] && echo "$message" >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# cmd: poll
# ---------------------------------------------------------------------------
cmd_poll() {
    if [[ $# -lt 1 || "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "Usage: $0 poll <state_id> [max_attempts] [interval_seconds]"
        echo "Exit 0 = terminal state reached, 1 = timeout or Errored"
        exit 1
    fi

    local state_id="$1"
    _validate_state_id "$state_id"
    local max="${2:-60}"
    local interval="${3:-10}"
    local terminal_states=("Planned" "PlannedAndFinished" "Applied" "Errored" "Canceled" "Discarded")

    _is_terminal() {
        local s="$1"
        for t in "${terminal_states[@]}"; do [[ "$s" == "$t" ]] && return 0; done
        return 1
    }

    local attempt=0 response status
    while [[ $attempt -lt $max ]]; do
        attempt=$((attempt + 1))
        response=$(aliyun iacservice get-execute-state --endpoint "$ENDPOINT" --user-agent "$IAC_USER_AGENT" --state-id "$state_id" 2>&1) || true
        status=$(echo "$response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('status','Unknown'))
except: print('Unknown')
" 2>/dev/null) || status="Unknown"

        if [[ "$status" == "Errored" ]]; then
            echo "[$attempt/$max] $(_red)Status: $status$(_reset)" >&2
        elif _is_terminal "$status"; then
            echo "[$attempt/$max] $(_green)Status: $status$(_reset)" >&2
        else
            echo "[$attempt/$max] $(_yellow)Status: $status$(_reset)" >&2
        fi

        if _is_terminal "$status"; then
            if [[ "$status" == "Errored" ]]; then
                local errmsg
                errmsg=$(echo "$response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('errorMessage','Unknown error'))
except: print('Unknown error')
" 2>/dev/null) || errmsg="Unknown error"
                echo "$(_red)Error: $errmsg$(_reset)" >&2
                exit 1
            fi
            exit 0
        fi

        [[ $attempt -lt $max ]] && sleep "$interval"
    done

    echo "$(_red)Timeout: $max attempts reached$(_reset)" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# cmd: plan
# ---------------------------------------------------------------------------
cmd_plan() {
    if [[ $# -lt 1 || "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "Usage: $0 plan <hcl_file_or_code> [existing_state_id]"
        echo "Output: STATE_ID=<id>  PLAN_OUTPUT_FILE=<path>"
        echo "Exit 0 = Planned/PlannedAndFinished, 1 = Errored"
        exit 1
    fi

    local input="$1"
    local state_id="${2:-}"
    local code token response new_state_id attempt ec http
    code=$(_read_input "$input")
    echo "Planning: $input" >&2
    [[ -n "$state_id" ]] && echo "Using existing state: $state_id" >&2

    token="$(_iac_new_client_token)"
    attempt=0
    ec=1
    response=""
    [[ -n "$state_id" ]] && _validate_state_id "$state_id"
    while [[ $attempt -lt 10 ]]; do
        attempt=$((attempt + 1))
        ec=0
        if [[ -n "$state_id" ]]; then
            response=$(
                aliyun iacservice execute-terraform-plan \
                    --endpoint "$ENDPOINT" \
                    --user-agent "$IAC_USER_AGENT" \
                    --client-token "$token" \
                    --code "$code" \
                    --state-id "$state_id" 2>&1
            ) || ec=$?
        else
            response=$(
                aliyun iacservice execute-terraform-plan \
                    --endpoint "$ENDPOINT" \
                    --user-agent "$IAC_USER_AGENT" \
                    --client-token "$token" \
                    --code "$code" 2>&1
            ) || ec=$?
        fi
        if [[ $ec -eq 0 ]]; then
            break
        fi
        http=$(_iac_http_status_from_output "$response")
        if _iac_is_5xx "$http"; then
            echo "$(_yellow)[Retry $attempt/10] execute-terraform-plan HTTP $http — same ClientToken$(_reset)" >&2
            sleep $((attempt * 2))
            continue
        fi
        echo "$(_red)Error: execute-terraform-plan failed$(_reset)" >&2
        echo "$response" | _redact_multiline >&2
        exit 1
    done
    if [[ $ec -ne 0 ]]; then
        echo "$(_red)Error: execute-terraform-plan failed after HTTP 5xx retries$(_reset)" >&2
        echo "$response" | _redact_multiline >&2
        exit 1
    fi

    new_state_id=$(printf '%s' "$response" | _iac_extract_state_id)
    [[ -z "$new_state_id" ]] && {
        echo "$(_red)Error: no stateId in response$(_reset)" >&2
        echo "$response" | _redact_multiline >&2
        exit 1
    }

    echo "STATE_ID=$new_state_id"
    echo "" >&2; echo "Plan started. stateId: $new_state_id" >&2; echo "Polling..." >&2; echo "" >&2

    "$SELF" poll "$new_state_id" || { echo "$(_red)Plan failed$(_reset)" >&2; exit 1; }

    local final_response final_status error_message
    final_response=$(aliyun iacservice get-execute-state --endpoint "$ENDPOINT" --user-agent "$IAC_USER_AGENT" --state-id "$new_state_id" 2>&1) || true
    final_status=$(echo "$final_response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('status','Unknown'))
except: print('Unknown')
" 2>/dev/null) || final_status="Unknown"

    echo "" >&2
    if [[ "$final_status" == "Planned" || "$final_status" == "PlannedAndFinished" ]]; then
        echo "$(_green)Plan completed: $final_status$(_reset)" >&2

        local plan_file="/tmp/tf_plan_${new_state_id}.txt"
        local plan_summary
        plan_summary=$(echo "$final_response" | python3 -c "
import sys,json,re
plan_file=sys.argv[1]
try:
    data=json.loads(sys.stdin.read(),strict=False)
    lf=data.get('logFile',{})
    log=lf.get('tf-plan.run.log','') if isinstance(lf,dict) else (lf if isinstance(lf,str) else '')
    if not log: print('  No plan details available'); sys.exit(0)
    clean=re.sub(r'\x1b\[[0-9;]*[a-zA-Z]','',log)
    open(plan_file,'w').write(clean)
    lines=clean.split('\n')
    summary=[l for l in lines if ('# ' in l and ('will be' in l or 'must be' in l)) or l.strip().startswith('Plan:') or 'No changes' in l]
    for s in (summary or ['  (see full output for details)']): print('  '+s.strip())
except Exception as e: print(f'  Could not parse: {e}')
" "$plan_file" 2>/dev/null) || plan_summary="  Could not parse plan details"

        echo "" >&2
        echo "=== Plan Summary ===" >&2
        echo "$plan_summary" >&2
        [[ -f "$plan_file" ]] && { echo "" >&2; echo "Full output: cat $plan_file" >&2; }
        echo "====================" >&2
        echo "PLAN_OUTPUT_FILE=$plan_file"
        exit 0
    elif [[ "$final_status" == "Errored" ]]; then
        error_message=$(echo "$final_response" | python3 -c "
import sys,json
try: m=json.load(sys.stdin).get('errorMessage',''); m and print(m)
except: pass
" 2>/dev/null) || error_message=""
        echo "$(_red)Plan failed: $final_status$(_reset)" >&2
        [[ -n "$error_message" ]] && echo "$(_red)Error: $error_message$(_reset)" >&2
        exit 1
    else
        echo "$(_yellow)Plan status: $final_status$(_reset)" >&2
        exit 0
    fi
}

# ---------------------------------------------------------------------------
# cmd: apply
# ---------------------------------------------------------------------------
cmd_apply() {
    if [[ $# -lt 1 || "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "Usage:"
        echo "  $0 apply <hcl_file_or_code>                     # first apply of a brand-new deployment"
        echo "  $0 apply <hcl_file_or_code> --state-id <id>     # any subsequent change to an existing deployment"
        echo "  $0 apply --state-id <id>                        # apply a previously planned state"
        echo ""
        echo "  STATE_ID REUSE RULE:"
        echo "  Once a STATE_ID exists, ALL subsequent operations on the same deployment MUST"
        echo "  pass --state-id, including: retry after failure, add resources, modify config."
        echo "  Starting a fresh apply (without --state-id) creates a NEW state and causes"
        echo "  duplicate resource creation."
        echo ""
        echo "Output: STATE_ID=<id>"
        echo "Exit 0 = Applied, 1 = Errored"
        exit 1
    fi

    local input="" state_id="" code=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --state-id) state_id="${2:-}"; shift 2 ;;
            --help|-h)  cmd_apply --help ;;
            *)          input="$1"; shift ;;
        esac
    done

    [[ -z "$input" && -z "$state_id" ]] && { echo "$(_red)Error: provide HCL code/file or --state-id$(_reset)" >&2; exit 1; }
    [[ -n "$input" ]] && { code=$(_read_input "$input"); echo "Applying: $input" >&2; }
    [[ -n "$state_id" ]] && echo "Using existing state: $state_id" >&2

    local token response new_state_id
    local max_retries=6 retry_delay=10 retry=0
    local r5=0
    token="$(_iac_new_client_token)"

    _invoke_apply() {
        if [[ -n "$code" && -n "$state_id" ]]; then
            _validate_state_id "$state_id"
            aliyun iacservice execute-terraform-apply \
                --endpoint "$ENDPOINT" \
                --user-agent "$IAC_USER_AGENT" \
                --client-token "$token" \
                --code "$code" \
                --state-id "$state_id"
        elif [[ -n "$code" ]]; then
            aliyun iacservice execute-terraform-apply \
                --endpoint "$ENDPOINT" \
                --user-agent "$IAC_USER_AGENT" \
                --client-token "$token" \
                --code "$code"
        elif [[ -n "$state_id" ]]; then
            _validate_state_id "$state_id"
            aliyun iacservice execute-terraform-apply \
                --endpoint "$ENDPOINT" \
                --user-agent "$IAC_USER_AGENT" \
                --client-token "$token" \
                --state-id "$state_id"
        else
            return 1
        fi
    }

    _invoke_apply_capture() { _invoke_apply 2>&1; }

    while true; do
        response=$(_invoke_apply_capture) && break
        http=$(_iac_http_status_from_output "$response")
        if _iac_is_5xx "$http"; then
            r5=$((r5 + 1))
            if [[ $r5 -ge 10 ]]; then
                echo "$(_red)Error: execute-terraform-apply failed after HTTP 5xx retries (same ClientToken)$(_reset)" >&2
                echo "$response" | _redact_multiline >&2
                exit 1
            fi
            echo "$(_yellow)[Retry $r5/10] execute-terraform-apply HTTP $http — same ClientToken$(_reset)" >&2
            sleep $((r5 * 3))
            continue
        fi
        if echo "$response" | grep -q "InvalidOperation.TaskStatus"; then
            retry=$((retry + 1))
            if [[ $retry -ge $max_retries ]]; then
                echo "$(_red)Error: state lock not released after $max_retries retries$(_reset)" >&2
                echo "$response" | _redact_multiline >&2
                exit 1
            fi
            echo "$(_yellow)[Retry $retry/$max_retries] State lock (HTTP 4xx) — new ClientToken, waiting ${retry_delay}s...$(_reset)" >&2
            sleep "$retry_delay"
            token="$(_iac_new_client_token)"
            continue
        else
            echo "$(_red)Error: execute-terraform-apply failed$(_reset)" >&2
            echo "$response" | _redact_multiline >&2
            exit 1
        fi
    done

    new_state_id=$(printf '%s' "$response" | _iac_extract_state_id)
    [[ -z "$new_state_id" ]] && {
        echo "$(_red)Error: no stateId in response$(_reset)" >&2
        echo "$response" | _redact_multiline >&2
        exit 1
    }

    echo "STATE_ID=$new_state_id"
    echo "" >&2; echo "Apply started. stateId: $new_state_id" >&2; echo "Polling..." >&2; echo "" >&2

    "$SELF" poll "$new_state_id" || { echo "$(_red)Apply failed$(_reset)" >&2; exit 1; }

    local final_response final_status error_message
    final_response=$(aliyun iacservice get-execute-state --endpoint "$ENDPOINT" --user-agent "$IAC_USER_AGENT" --state-id "$new_state_id" 2>&1) || true
    final_status=$(echo "$final_response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('status','Unknown'))
except: print('Unknown')
" 2>/dev/null) || final_status="Unknown"

    echo "" >&2
    if [[ "$final_status" == "Applied" ]]; then
        echo "$(_green)Apply completed: $final_status$(_reset)" >&2
        echo "" >&2; echo "Resources:" >&2
        echo "$final_response" | python3 -c "
import sys,json
try:
    data=json.load(sys.stdin)
    s=data.get('state','')
    state=json.loads(s) if isinstance(s,str) else s
    resources=state.get('resources',[]) if state else []
    if resources:
        for r in resources:
            for i in r.get('instances',[]):
                print(f'  {r[\"type\"]}.{r[\"name\"]}: {i.get(\"attributes\",{}).get(\"id\",\"N/A\")}')
    else: print('  No resources found')
except Exception as e: print(f'  Could not parse resources: {e}')
" 2>/dev/null || echo "  Could not parse resources" >&2
        exit 0
    elif [[ "$final_status" == "Errored" ]]; then
        error_message=$(echo "$final_response" | python3 -c "
import sys,json
try: m=json.load(sys.stdin).get('errorMessage',''); m and print(m)
except: pass
" 2>/dev/null) || error_message=""
        echo "$(_red)Apply failed: $final_status$(_reset)" >&2
        [[ -n "$error_message" ]] && echo "$(_red)Error: $error_message$(_reset)" >&2
        exit 1
    else
        echo "$(_yellow)Apply status: $final_status$(_reset)" >&2; exit 0
    fi
}

# ---------------------------------------------------------------------------
# cmd: destroy
# ---------------------------------------------------------------------------
cmd_destroy() {
    if [[ $# -lt 1 || "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "Usage: $0 destroy <state_id>"
        echo "Exit 0 = Destroyed, 1 = Failed"
        exit 1
    fi

    local state_id="$1"
    [[ -z "$state_id" ]] && { echo "$(_red)Error: state_id required$(_reset)" >&2; exit 1; }
    _validate_state_id "$state_id"
    echo "Destroying resources for state: $state_id" >&2

    local token response destroy_state_id attempt ec http
    token="$(_iac_new_client_token)"
    attempt=0
    ec=1
    response=""
    while [[ $attempt -lt 10 ]]; do
        attempt=$((attempt + 1))
        ec=0
        response=$(aliyun iacservice execute-terraform-destroy \
            --endpoint "$ENDPOINT" \
            --user-agent "$IAC_USER_AGENT" \
            --client-token "$token" \
            --state-id "$state_id" 2>&1) || ec=$?
        if [[ $ec -eq 0 ]]; then
            break
        fi
        http=$(_iac_http_status_from_output "$response")
        if _iac_is_5xx "$http"; then
            echo "$(_yellow)[Retry $attempt/10] execute-terraform-destroy HTTP $http — same ClientToken$(_reset)" >&2
            sleep $((attempt * 2))
            continue
        fi
        echo "$(_red)Error: execute-terraform-destroy failed$(_reset)" >&2
        echo "$response" | _redact_multiline >&2
        exit 1
    done
    if [[ $ec -ne 0 ]]; then
        echo "$(_red)Error: execute-terraform-destroy failed after HTTP 5xx retries$(_reset)" >&2
        echo "$response" | _redact_multiline >&2
        exit 1
    fi

    destroy_state_id=$(printf '%s' "$response" | _iac_extract_state_id "$state_id")

    echo "Polling..." >&2; echo "" >&2
    "$SELF" poll "$destroy_state_id" || { echo "$(_red)Destroy failed$(_reset)" >&2; exit 1; }

    local final_response final_status
    final_response=$(aliyun iacservice get-execute-state --endpoint "$ENDPOINT" --user-agent "$IAC_USER_AGENT" --state-id "$destroy_state_id" 2>&1) || true
    final_status=$(echo "$final_response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('status','Unknown'))
except: print('Unknown')
" 2>/dev/null) || final_status="Unknown"

    echo "" >&2
    if [[ "$final_status" == "Applied" || "$final_status" == "Canceled" || "$final_status" == "Discarded" ]]; then
        echo "$(_green)Destroy completed: $final_status$(_reset)" >&2; exit 0
    elif [[ "$final_status" == "Errored" ]]; then
        local errmsg
        errmsg=$(echo "$final_response" | python3 -c "
import sys,json
try: m=json.load(sys.stdin).get('errorMessage',''); m and print(m)
except: pass
" 2>/dev/null) || errmsg=""
        echo "$(_red)Destroy failed: $final_status$(_reset)" >&2
        [[ -n "$errmsg" ]] && echo "$(_red)Error: $errmsg$(_reset)" >&2
        exit 1
    else
        echo "$(_yellow)Destroy status: $final_status$(_reset)" >&2; exit 0
    fi
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
usage() {
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "Commands:"
    echo "  validate <hcl_file_or_code>                  Validate HCL syntax"
    echo "  plan     <hcl_file_or_code> [state_id]       Preview changes"
    echo "  apply    <hcl_file_or_code> [--state-id id]  Create/update infrastructure"
    echo "  apply    --state-id <id>                     Apply planned state"
    echo "  destroy  <state_id>                          Destroy resources"
    echo "  poll     <state_id> [max] [interval]         Poll execution status"
    echo ""
    echo "Run '$0 <command> --help' for per-command usage."
    exit 1
}

COMMAND="${1:-}"
shift || true

case "$COMMAND" in
    validate) cmd_validate "$@" ;;
    plan)     cmd_plan     "$@" ;;
    apply)    cmd_apply    "$@" ;;
    destroy)  cmd_destroy  "$@" ;;
    poll)     cmd_poll     "$@" ;;
    *)        usage ;;
esac
