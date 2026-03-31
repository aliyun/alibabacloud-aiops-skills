#!/usr/bin/env bash
set -euo pipefail

# terraform_runtime_online.sh - Execute Terraform via Alibaba Cloud IaCService
#
# Usage:
#   terraform_runtime_online.sh validate <hcl_file_or_code>
#   terraform_runtime_online.sh plan     <hcl_file_or_code> [existing_state_id]
#   terraform_runtime_online.sh apply    <hcl_file_or_code>                  # fresh apply (first time)
#   terraform_runtime_online.sh apply    <hcl_file_or_code> --state-id <id>  # retry failed apply / update existing state
#   terraform_runtime_online.sh apply    --state-id <id>                     # apply a previously planned state
#   terraform_runtime_online.sh destroy  <state_id> [--force]
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

ENDPOINT="iac.cn-zhangjiakou.aliyuncs.com"
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

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

    local token response status message
    token="$(uuidgen)"
    response=$(aliyun iacservice validate-module \
        --endpoint "$ENDPOINT" \
        --client-token "$token" \
        --source Upload \
        --code "$code" 2>&1) || { echo "$(_red)Error: validate-module failed$(_reset)" >&2; echo "$response" >&2; exit 1; }

    status=$(echo "$response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('status','Unknown'))
except: print('Unknown')
" 2>/dev/null) || status="Unknown"

    message=$(echo "$response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('message',''))
except: print('')
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
        response=$(aliyun iacservice get-execute-state --endpoint "$ENDPOINT" --state-id "$state_id" 2>&1) || true
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
    local code token aliyun_cmd response new_state_id
    code=$(_read_input "$input")
    echo "Planning: $input" >&2
    [[ -n "$state_id" ]] && echo "Using existing state: $state_id" >&2

    token="$(uuidgen)"
    aliyun_cmd="aliyun iacservice execute-terraform-plan --endpoint $ENDPOINT --client-token $token --code \"\$code\""
    [[ -n "$state_id" ]] && aliyun_cmd="$aliyun_cmd --state-id $state_id"

    response=$(eval "$aliyun_cmd" 2>&1) || { echo "$(_red)Error: execute-terraform-plan failed$(_reset)" >&2; echo "$response" >&2; exit 1; }

    new_state_id=$(echo "$response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('stateId',''))
except: print('')
" 2>/dev/null) || new_state_id=""
    [[ -z "$new_state_id" ]] && { echo "$(_red)Error: no stateId in response$(_reset)" >&2; echo "$response" >&2; exit 1; }

    echo "STATE_ID=$new_state_id"
    echo "" >&2; echo "Plan started. stateId: $new_state_id" >&2; echo "Polling..." >&2; echo "" >&2

    "$SELF" poll "$new_state_id" || { echo "$(_red)Plan failed$(_reset)" >&2; exit 1; }

    local final_response final_status error_message
    final_response=$(aliyun iacservice get-execute-state --endpoint "$ENDPOINT" --state-id "$new_state_id" 2>&1) || true
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

    local token aliyun_cmd response new_state_id
    local max_retries=6 retry_delay=10 retry=0
    token="$(uuidgen)"

    _build_cmd() {
        local cmd="aliyun iacservice execute-terraform-apply --endpoint $ENDPOINT --client-token $token"
        [[ -n "$code" ]]     && cmd="$cmd --code \"\$code\""
        [[ -n "$state_id" ]] && cmd="$cmd --state-id $state_id"
        echo "$cmd"
    }

    aliyun_cmd=$(_build_cmd)
    while true; do
        response=$(eval "$aliyun_cmd" 2>&1) && break
        if echo "$response" | grep -q "InvalidOperation.TaskStatus"; then
            retry=$((retry + 1))
            if [[ $retry -ge $max_retries ]]; then
                echo "$(_red)Error: state lock not released after $max_retries retries$(_reset)" >&2
                echo "$response" >&2; exit 1
            fi
            echo "$(_yellow)[Retry $retry/$max_retries] State lock not released, waiting ${retry_delay}s...$(_reset)" >&2
            sleep "$retry_delay"
            token="$(uuidgen)"; aliyun_cmd=$(_build_cmd)
        else
            echo "$(_red)Error: execute-terraform-apply failed$(_reset)" >&2; echo "$response" >&2; exit 1
        fi
    done

    new_state_id=$(echo "$response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('stateId',''))
except: print('')
" 2>/dev/null) || new_state_id=""
    [[ -z "$new_state_id" ]] && { echo "$(_red)Error: no stateId in response$(_reset)" >&2; echo "$response" >&2; exit 1; }

    echo "STATE_ID=$new_state_id"
    echo "" >&2; echo "Apply started. stateId: $new_state_id" >&2; echo "Polling..." >&2; echo "" >&2

    "$SELF" poll "$new_state_id" || { echo "$(_red)Apply failed$(_reset)" >&2; exit 1; }

    local final_response final_status error_message
    final_response=$(aliyun iacservice get-execute-state --endpoint "$ENDPOINT" --state-id "$new_state_id" 2>&1) || true
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
        echo "Usage: $0 destroy <state_id> [--force]"
        echo "Exit 0 = Destroyed, 1 = Failed or not confirmed"
        exit 1
    fi

    local state_id="" force=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --force) force=true; shift ;;
            --help|-h) cmd_destroy --help ;;
            *) state_id="$1"; shift ;;
        esac
    done

    [[ -z "$state_id" ]] && { echo "$(_red)Error: state_id required$(_reset)" >&2; exit 1; }

    # Pre-check: get current state and list resources
    echo "Pre-check: querying state $state_id ..." >&2
    local pre_response pre_status
    pre_response=$(aliyun iacservice get-execute-state --endpoint "$ENDPOINT" --state-id "$state_id" 2>&1) || {
        echo "$(_red)Error: cannot query state $state_id$(_reset)" >&2
        echo "$pre_response" >&2; exit 1
    }

    pre_status=$(echo "$pre_response" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('status','Unknown'))
except: print('Unknown')
" 2>/dev/null) || pre_status="Unknown"

    echo "" >&2
    echo "$(_yellow)⚠️  The following resources will be DESTROYED:$(_reset)" >&2
    echo "$pre_response" | python3 -c "
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
    else: print('  (no resources found in state)')
except Exception as e: print(f'  Could not parse resources: {e}')
" 2>/dev/null || echo "  Could not parse resources" >&2
    echo "" >&2

    if [[ "$force" != true ]]; then
        echo "$(_red)Destruction not confirmed. Add --force to proceed.$(_reset)" >&2
        exit 1
    fi

    echo "Destroying resources for state: $state_id" >&2

    local token response destroy_state_id
    token="$(uuidgen)"
    response=$(aliyun iacservice execute-terraform-destroy \
        --endpoint "$ENDPOINT" \
        --client-token "$token" \
        --state-id "$state_id" 2>&1) || { echo "$(_red)Error: execute-terraform-destroy failed$(_reset)" >&2; echo "$response" >&2; exit 1; }

    destroy_state_id=$(echo "$response" | python3 -c "
import sys,json
try:
    sid=json.load(sys.stdin).get('stateId','')
    print(sid if sid else '$state_id')
except: print('$state_id')
" 2>/dev/null) || destroy_state_id="$state_id"

    echo "Polling..." >&2; echo "" >&2
    "$SELF" poll "$destroy_state_id" || { echo "$(_red)Destroy failed$(_reset)" >&2; exit 1; }

    local final_response final_status
    final_response=$(aliyun iacservice get-execute-state --endpoint "$ENDPOINT" --state-id "$destroy_state_id" 2>&1) || true
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
    echo "  destroy  <state_id> [--force]                Destroy resources"
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
