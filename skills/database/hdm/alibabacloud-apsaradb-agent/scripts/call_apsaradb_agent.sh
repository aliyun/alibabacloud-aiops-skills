#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SKILL_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
MANIFEST_PATH="$SKILL_ROOT/references/manifest.json"
ENDPOINT="${APSARADB_AGENT_ENDPOINT:-das.cn-shanghai.aliyuncs.com}"
SOURCE="yaochi-console"
READ_TIMEOUT="${APSARADB_AGENT_READ_TIMEOUT:-180}"
CONNECT_TIMEOUT="${APSARADB_AGENT_CONNECT_TIMEOUT:-30}"
QUERY=""
SESSION_ID=""
PROFILE=""
EXTRA_INFO="{}"
DEBUG=false
DRY_RUN=false
CONFIRM_ACTION=""
EXPECTED_TOOL=""
EXPECTED_ARGS=""
APPROVED_PLAN=""
CONFIRMED_CARD=""
CONFIRMED_PLAN=""
CONFIRMATION_DIR=""
READONLY_REQUEST=false
APPROVAL_ATTEMPTED=false
POST_APPROVAL_CONTENT=false
OPERATION_CANCELLED=false
SKILL_SESSION_ID="${SKILL_SESSION_ID:-}"
SKILL_VERSION="${SKILL_VERSION:-}"
USER_AGENT=""
STREAM_DIR=""
ALIYUN_PID=""
PARSED_SESSION_ID=""
PARSED_EVENT_COUNT=0
SESSION_ID_EMITTED=false
LAST_ERROR_CODE=""
ERROR_HAS_PROGRESS=false
PARSED_UNKNOWN_OUTPUT=false
THROTTLE_RETRIES="${APSARADB_AGENT_THROTTLE_RETRIES:-10}"

usage() {
    cat >&2 <<EOF
Alibaba Cloud ApsaraDB Agent CLI Tool

Consultation, diagnostics, and operation planning are available without approval.
An approved change requires an exact match against the server confirmation card. Destructive
operations and local write-command fallbacks are unsupported.

Usage:
  $(basename "$0") <query> [options]

Arguments:
  <query>                  Natural-language query; use '-' to read from stdin

Required environment:
  SKILL_SESSION_ID         Fresh 32-character lowercase hexadecimal ID
  SKILL_VERSION            Exact references/manifest.json version

Options:
  --session-id <uuid>      Reuse a server SessionID for a related follow-up
  --source <source>        Backend source route (default: yaochi-console)
  --extra-info <json>      JSON object string (default: {}); optional readonly mode
  --confirmation-dir <dir> Private live-card inbox (normally supplied by agent_job.py)
  --confirm approve       Compatibility: one exact already approved operation
  --expect-tool <api>     Exact approved API; required with --confirm approve
  --expect-args <json>    Complete approved argument object; required with approval
  --profile <name>         Existing aliyun CLI profile
  --debug, -d              Print redacted request and tool progress to stderr
  --dry-run                Print the signed request shape without sending it
  --help, -h               Show this help

Concurrent-limit recovery:
  APSARADB_AGENT_THROTTLE_RETRIES: 0-10 retries (default 10), only for an
  explicit admission rejection before response events, session or approval.
  Accepted operations and confirmation callbacks are never replayed.

Security:
  Never include passwords, tokens, AccessKeys, credentials, or private keys
  in the query or metadata; such input is rejected.

Examples:
  $(basename "$0") "List my database instances in cn-hangzhou"
  $(basename "$0") "Continue the analysis" --session-id "123e4567-e89b-12d3-a456-426614174000"
  $(basename "$0") "Analyze r-xxx memory usage" --source tair-console
  printf '%s' "Compare PolarDB and RDS" | $(basename "$0") -
EOF
}

debug_log() {
    if [[ "$DEBUG" == "true" ]]; then
        printf '[DEBUG] %s\n' "$*" >&2
    fi
}

require_option_value() {
    local option="$1"
    local value="${2:-}"

    if [[ -z "$value" || "$value" == --* ]]; then
        printf 'Error: %s requires a value.\n' "$option" >&2
        exit 2
    fi
}

json_field_from_lines() {
    local raw="$1"
    local filter="$2"
    local line value

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line#data:}"
        line="${line# }"
        [[ -z "$line" ]] && continue
        if printf '%s' "$line" | jq -e . >/dev/null 2>&1; then
            value=$(printf '%s' "$line" | jq -r "$filter // empty" 2>/dev/null) || true
            if [[ -n "$value" ]]; then
                printf '%s\n' "$value"
                return
            fi
        fi
    done <<<"$raw"
}

extract_error_code() {
    local raw="$1" value
    value=$(json_field_from_lines "$raw" '.Code // .ErrorCode // .code // .errorCode // .data.Code // .data.ErrorCode // .data.code // .data.errorCode') || true
    if [[ -z "$value" ]]; then
        value=$(printf '%s\n' "$raw" | sed -nE 's/.*"(Code|ErrorCode|code|errorCode)"[[:space:]]*:[[:space:]]*"([^"]+)".*/\2/p' | head -n 1)
    fi
    printf '%s' "$value"
}

extract_error_message() {
    local raw="$1" value
    value=$(json_field_from_lines "$raw" '.Message // .ErrorMessage // .Description // .message // .errorMessage // .description // .data.Message // .data.ErrorMessage // .data.message // .data.errorMessage') || true
    if [[ -z "$value" ]]; then
        value=$(printf '%s\n' "$raw" | sed -nE 's/.*"(Message|ErrorMessage|Description|message|errorMessage|description)"[[:space:]]*:[[:space:]]*"([^"]+)".*/\2/p' | head -n 1)
    fi
    printf '%s' "$value"
}

extract_auth_action() {
    local raw="$1" value
    value=$(json_field_from_lines "$raw" '.AuthAction // .authAction // .Data.AuthAction // .data.AuthAction // .data.authAction') || true
    if [[ -z "$value" ]]; then
        value=$(printf '%s\n' "$raw" | sed -nE 's/.*"(AuthAction|authAction)"[[:space:]]*:[[:space:]]*"([^"]+)".*/\2/p' | head -n 1)
    fi
    printf '%s' "$value"
}

extract_request_id() {
    local raw="$1" value
    value=$(json_field_from_lines "$raw" '.RequestId // .RequestID // .requestId // .requestID // .data.RequestId // .data.requestId') || true
    if [[ -z "$value" ]]; then
        value=$(printf '%s\n' "$raw" | sed -nE 's/.*"(RequestId|RequestID|requestId|requestID)"[[:space:]]*:[[:space:]]*"([^"]+)".*/\2/p' | head -n 1)
    fi
    printf '%s' "$value"
}

error_suggestion() {
    local code="$1"
    local auth_action="$2"

    case "$code" in
        *Forbidden*|*NoPermission*|*Unauthorized*)
            printf 'Grant RAM action %s to the current CLI identity, then retry.' "${auth_action:-hdm:GetYaoChiAgent}"
            ;;
        *InvalidAccessKeyId*|*SignatureDoesNotMatch*|*InvalidSecurityToken*|*SecurityToken*)
            printf 'Refresh the existing aliyun CLI profile outside this agent session, then retry.'
            ;;
        *Throttling*|*ConcurrentLimit*)
            printf 'Wait for an existing request to finish; do not start parallel retries.'
            ;;
        *Timeout*|*Connection*|*ServiceUnavailable*)
            printf 'Check connectivity to %s and retry once with user awareness.' "$ENDPOINT"
            ;;
        *)
            printf 'Review the CLI profile, DAS plugin, RAM permission, and request parameters, then retry.'
            ;;
    esac
}

text_has_sensitive_assignment() {
    local raw="$1"
    printf '%s' "$raw" | grep -Eiq "(password|passwd|secret|token|credential|access[_-]?key|private[_-]?key)[[:alnum:]_-]*[[:space:]_\"']*(=|:)" \
        || printf '%s' "$raw" | grep -Eq '(密码|口令|密钥)[[:space:]]*(=|:|：)' \
        || printf '%s' "$raw" | grep -Eq '(^|[^0-9A-Za-z])(LTAI|STS\.)[0-9A-Za-z]{12,}' \
        || printf '%s' "$raw" | grep -Eq -- '-----BEGIN [A-Z ]*PRIVATE KEY-----'
}

print_structured_error() {
    local raw="$1"
    local code message auth_action request_id suggestion sensitive_raw=false

    code=$(extract_error_code "$raw") || true
    LAST_ERROR_CODE="$code"
    if [[ "$(json_field_from_lines "$raw" '[
        (.Content // .content), (.SessionId // .sessionId // .session_id),
        (.ReasoningContent // .reasoningContent // .reasoning_content),
        (.QueryId // .queryId), (.FunctionCall // .function_call),
        (.UiFunctionCall // .ui_function_call), (.SubAgentCall // .sub_agent_call)
    ] | any(. != null and . != "" and . != [] and . != {})')" == "true" ]]; then
        ERROR_HAS_PROGRESS=true
    fi
    message=$(extract_error_message "$raw") || true
    auth_action=$(extract_auth_action "$raw") || true
    request_id=$(extract_request_id "$raw") || true
    suggestion=$(error_suggestion "$code" "$auth_action")
    if text_has_sensitive_assignment "$raw"; then
        sensitive_raw=true
        message="Sensitive error details were redacted."
    fi

    printf '\n[ApsaraDB Agent Error]\n' >&2
    printf 'ErrorCode: %s\n' "${code:-Unknown}" >&2
    printf 'ErrorMessage: %s\n' "${message:-No detailed message returned by aliyun CLI.}" >&2
    [[ -n "$auth_action" ]] && printf 'AuthAction: %s\n' "$auth_action" >&2
    [[ -n "$request_id" ]] && printf 'RequestId: %s\n' "$request_id" >&2
    printf 'Suggestion: %s\n' "$suggestion" >&2
    if [[ "$DEBUG" == "true" ]]; then
        if [[ "$sensitive_raw" == "true" ]]; then
            printf 'RawError: <redacted>\n' >&2
        else
            printf 'RawError:\n%s\n' "$raw" >&2
        fi
    fi
}

json_has_sensitive_key() {
    local raw="$1"
    printf '%s' "$raw" | jq -e '
        def sensitive_key:
            ascii_downcase | test("password|passwd|secret|token|credential|access[_-]?key|private[_-]?key");
        def contains_sensitive:
            if type == "object" then
                any(to_entries[]; (.key | sensitive_key) or (.value | contains_sensitive))
            elif type == "array" then
                any(.[]; contains_sensitive)
            else
                false
            end;
        contains_sensitive
    ' >/dev/null 2>&1
}

summarize_tool_calls() {
    local raw="$1"
    printf '%s' "$raw" | jq -c '
        [if type == "array" then .[] elif type == "object" then . else empty end
         | .ToolName // .toolName // .tool_name // "unknown"]
    ' 2>/dev/null || printf '["unknown"]'
}

has_human_confirm() {
    local ui_calls="$1"
    printf '%s' "$ui_calls" | jq -e '
        any(if type == "array" then .[] elif type == "object" then . else empty end;
            (.ToolName // .toolName // .tool_name) == "humanConfirm")
    ' >/dev/null 2>&1
}

looks_like_error() {
    local raw="$1"
    [[ "$raw" == *"SDKError"* ]] \
        || [[ "$raw" == *"ERROR:"* ]] \
        || [[ "$raw" == *"Error:"* ]] \
        || [[ -n "$(extract_error_code "$raw")" ]]
}

check_dependencies() {
    local cli_version major minor patch credential_status

    if ! command -v aliyun >/dev/null 2>&1; then
        printf 'Error: aliyun CLI is required (version 3.5.0 or later).\n' >&2
        printf 'See references/cli-installation-guide.md.\n' >&2
        exit 1
    fi
    if ! command -v jq >/dev/null 2>&1; then
        printf 'Error: jq is required for JSON validation and stream parsing.\n' >&2
        printf 'See references/cli-installation-guide.md.\n' >&2
        exit 1
    fi
    cli_version=$(aliyun version 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1) || true
    if [[ -z "$cli_version" ]]; then
        printf 'Error: unable to determine aliyun CLI version; version 3.5.0 or later is required.\n' >&2
        exit 1
    fi
    IFS=. read -r major minor patch <<<"$cli_version"
    if ((major < 3 || (major == 3 && minor < 5))); then
        printf 'Error: aliyun CLI 3.5.0 or later is required; found %s.\n' "$cli_version" >&2
        printf 'Upgrade the CLI before retrying; see references/cli-installation-guide.md.\n' >&2
        exit 1
    fi
    if ! credential_status=$(aliyun configure list 2>/dev/null) || ! printf '%s' "$credential_status" | jq -Rse --arg profile "$PROFILE" '
        split("\n") | any(.[];
            split("|") | map(gsub("^\\s+|\\s+$"; "")) |
            length >= 3 and .[2] == "Valid" and
            (if $profile == "" then .[0] | endswith(" *")
             else .[0] | sub(" \\*$"; "") == $profile end)
        )' >/dev/null 2>&1; then
        printf 'Error: the selected aliyun CLI credential profile is missing or invalid.\n' >&2
        printf 'Configure credentials outside this session, then retry.\n' >&2
        exit 1
    fi
    if ! aliyun das get-yao-chi-agent --help >/dev/null 2>&1; then
        printf 'Error: DAS CLI plugin is unavailable.\n' >&2
        printf 'Install it with: aliyun plugin install --names aliyun-cli-das\n' >&2
        exit 1
    fi
    debug_log "aliyun CLI version: $cli_version"
}

# Probe local plugin validation only. --cli-dry-run never sends an agent request.
# Keep SOURCE canonical for operation policy; WIRE_SOURCE is transport-only.
resolve_wire_source() {
    local canonical="$1" alias=""
    local probe_args=(das get-yao-chi-agent --query 'Source compatibility check'
        --extra-info '{"mode":"readonly"}' --cli-dry-run)
    [[ -n "${PROFILE:-}" ]] && probe_args+=(--profile "$PROFILE")
    [[ -n "${ENDPOINT:-}" ]] && probe_args+=(--endpoint "$ENDPOINT")
    WIRE_SOURCE="$canonical"
    SOURCE_PROBE_ERROR=""
    if SOURCE_PROBE_ERROR=$(aliyun "${probe_args[@]}" --source "$canonical" 2>&1); then
        return 0
    fi
    # Only a local source-enum rejection permits an alias probe, never a network
    # error, credential error or any response from a live request.
    if ! printf '%s' "$SOURCE_PROBE_ERROR" | jq -e --arg source "$canonical" '
        (.message // "") | contains("--source value \"" + $source + "\" is not allowed")
    ' >/dev/null 2>&1; then
        return 1
    fi
    case "$canonical" in
        yaochi-console) alias=yaochi ;;
        polardb-console) alias=polardb ;;
        tair-console) alias=tair ;;
        mongodb-console) alias=mongodb ;;
        lindorm-console) alias=lindorm ;;
        polarx-console) alias=polarx ;;
        dbs-console) alias=dbs ;;
        *) return 1 ;;
    esac
    if SOURCE_PROBE_ERROR=$(aliyun "${probe_args[@]}" --source "$alias" 2>&1); then
        WIRE_SOURCE="$alias"
        return 0
    fi
    return 1
}

validate_input() {
    local query_length=${#QUERY}
    local valid_source=false
    local known_source manifest_version
    local known_sources=(
        yaochi-console polardb-console polardb-pg-console tair-console mongodb-console
        lindorm-console polarx-console dbs-console gpdb-console adbmysql-console
        clickhouse-console selectdb-console dts-console
    )

    if [[ ! -f "$MANIFEST_PATH" ]]; then
        printf 'Error: references/manifest.json is missing.\n' >&2
        exit 2
    fi
    manifest_version=$(jq -er '.version | select(type == "string" and length > 0)' "$MANIFEST_PATH" 2>/dev/null) || {
        printf 'Error: references/manifest.json must contain a non-empty string version.\n' >&2
        exit 2
    }
    if [[ -z "$SKILL_SESSION_ID" || ! "$SKILL_SESSION_ID" =~ ^[0-9a-f]{32}$ ]]; then
        printf 'Error: SKILL_SESSION_ID must be a fresh 32-character lowercase hexadecimal value.\n' >&2
        exit 2
    fi
    if [[ -z "$SKILL_VERSION" || "$SKILL_VERSION" != "$manifest_version" ]]; then
        printf 'Error: SKILL_VERSION must exactly match references/manifest.json.\n' >&2
        exit 2
    fi
    if [[ -z "$QUERY" ]]; then
        printf 'Error: query must not be empty.\n' >&2
        usage
        exit 2
    fi
    if ((query_length > 4000)); then
        printf 'Error: query exceeds the 4000-character limit.\n' >&2
        exit 2
    fi
    if text_has_sensitive_assignment "$QUERY"; then
        printf 'Error: the query appears to contain a password, token, AccessKey, or private key.\n' >&2
        printf 'Remove the secret value and retry; never send secrets to ApsaraDB Agent.\n' >&2
        exit 2
    fi
    if [[ -n "$SESSION_ID" && ! "$SESSION_ID" =~ ^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$ ]]; then
        printf 'Error: --session-id must be a UUID returned by ApsaraDB Agent.\n' >&2
        exit 2
    fi
    for known_source in "${known_sources[@]}"; do
        if [[ "$SOURCE" == "$known_source" ]]; then
            valid_source=true
            break
        fi
    done
    if [[ "$valid_source" != "true" ]]; then
        printf 'Error: unsupported --source value: %s\n' "$SOURCE" >&2
        exit 2
    fi
    if [[ -n "$PROFILE" && ! "$PROFILE" =~ ^[a-zA-Z0-9._-]+$ ]]; then
        printf 'Error: --profile may contain only letters, numbers, dots, underscores, and hyphens.\n' >&2
        exit 2
    fi
    EXTRA_INFO=$(printf '%s' "$EXTRA_INFO" |
        jq -ces 'select(length == 1) | .[0] | select(type == "object")' 2>/dev/null) || {
        printf 'Error: --extra-info must contain exactly one JSON object.\n' >&2
        exit 2
    }
    if json_has_sensitive_key "$EXTRA_INFO" || text_has_sensitive_assignment "$EXTRA_INFO"; then
        printf 'Error: --extra-info must not contain passwords, secrets, tokens, credentials, or key material.\n' >&2
        exit 2
    fi
    if ! printf '%s' "$EXTRA_INFO" | jq -e '(has("mode") | not) or .mode == "readonly"' >/dev/null 2>&1; then
        printf 'Error: --extra-info mode must be readonly; use the explicit confirmation path for supported operations.\n' >&2
        exit 2
    fi
    if printf '%s' "$EXTRA_INFO" | jq -e '.mode == "readonly"' >/dev/null; then
        READONLY_REQUEST=true
    fi
    if [[ -n "$CONFIRMATION_DIR" ]]; then
        python3 "$SCRIPT_DIR/operation_confirmation.py" check-dir --directory "$CONFIRMATION_DIR" >/dev/null || exit 2
    fi
    if [[ -z "$CONFIRM_ACTION" && -z "$EXPECTED_TOOL" && -z "$EXPECTED_ARGS" ]]; then
        return
    fi
    if [[ "$CONFIRM_ACTION" != "approve" || -z "$EXPECTED_TOOL" || -z "$EXPECTED_ARGS" ||
          "$DRY_RUN" == "true" || -n "$SESSION_ID" || "$EXTRA_INFO" != "{}" ]]; then
        printf 'Error: approval requires --confirm approve, --expect-tool, and --expect-args in a fresh request without extra metadata or dry run.\n' >&2
        exit 2
    fi
    APPROVED_PLAN=$(printf '%s' "$EXPECTED_ARGS" | python3 "$SCRIPT_DIR/operation_confirmation.py" normalize \
        --tool "$EXPECTED_TOOL" --reject-secrets 2>/dev/null) || {
        printf 'Error: forbidden operation, malformed or secret-bearing approval arguments; no request sent.\n' >&2
        exit 2
    }
    # Compatibility path only. Normal requests preserve the business query and
    # let the service generate its concrete operation/ordering plan.
    QUERY="Execute this exact already approved plan through the registered product tool and its real humanConfirm event. Do not substitute tools, modify parameters or perform additional writes. If unavailable, stop. Approved plan: $(jq -cn --arg tool "$EXPECTED_TOOL" --argjson args "$EXPECTED_ARGS" '{tool:$tool,args:$args}')"

    if ((${#QUERY} > 4000)); then
        printf 'Error: operation query and approved plan exceed the 4000-character limit.\n' >&2
        exit 2
    fi
}

normalize_operation() {
    printf '%s' "$2" | python3 "$SCRIPT_DIR/operation_confirmation.py" normalize --tool "$1" 2>/dev/null
}

is_uuid() {
    [[ "$1" =~ ^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$ ]]
}

send_confirmation() {
    local id="$1" approved="$2" output
    local args=(das create-yao-chi-agent-confirm
        --confirmation-id "$id" --approved "$approved" --session-id "$PARSED_SESSION_ID"
        --endpoint "$ENDPOINT" --read-timeout "$READ_TIMEOUT" --connect-timeout "$CONNECT_TIMEOUT"
        --user-agent "$USER_AGENT")
    [[ -n "$PROFILE" ]] && args+=(--profile "$PROFILE")
    # No ToolArgs override, generic RPC fallback, or retry. Never log a raw callback body.
    if ! output=$(aliyun "${args[@]}" 2>&1) || ! printf '%s' "$output" |
        jq -es --arg id "$id" --argjson approved "$approved" '
            length == 1 and (.[0] |
            type == "object" and .ConfirmationId == $id and .Approved == $approved
            and ((has("ToolArgsReceived") | not) or .ToolArgsReceived == false))
        ' >/dev/null 2>&1; then
        printf '[ConfirmationUnverified] Callback outcome is unknown. Do not replay; verify resource state with a new readonly query.\n' >&2
        return 1
    fi
}

handle_operation_card() {
    local ui_calls="$1" card id tool args actual decision
    card=$(printf '%s' "$ui_calls" | jq -ce '
        [if type == "array" then .[] else . end
         | select((.ToolName // .toolName // .tool_name) == "humanConfirm")
         | (.ArgsText // .argsText // .args)
         | if type == "string" then fromjson else . end]
        | select(length == 1) | .[0] | select(type == "object")
    ' 2>/dev/null) || {
        printf '[OperationBlocked] Invalid or multiple confirmation cards.\n' >&2
        return 1
    }
    id=$(printf '%s' "$card" | jq -r '.confirmation_id // .confirmationId // empty')
    decision=$(printf '%s' "$card" | jq -r '.approved // .Approved // empty')
    if ! is_uuid "$id" || ! is_uuid "$PARSED_SESSION_ID"; then
        printf '[OperationBlocked] Confirmation or originating session ID is invalid.\n' >&2
        return 1
    fi
    tool=$(printf '%s' "$card" | jq -r '.tool_name // .toolName // empty')
    args=$(printf '%s' "$card" | jq -c '.tool_args // .toolArgs // null')
    actual=$(normalize_operation "$tool" "$args") || actual=""
    if [[ -n "$CONFIRMED_CARD" && "$id" == "$CONFIRMED_CARD" && "$actual" == "$CONFIRMED_PLAN" &&
          ( "$decision" == "0" || "$decision" == "1" ) ]]; then
        return 0
    fi
    if [[ -n "$CONFIRMATION_DIR" && -z "$APPROVED_PLAN" && "$decision" == "0" && -n "$actual" ]]; then
        local outcome approved
        if ! outcome=$(printf '%s' "$card" | python3 "$SCRIPT_DIR/operation_confirmation.py" wait \
            --directory "$CONFIRMATION_DIR" --session-id "$PARSED_SESSION_ID"); then
            send_confirmation "$id" false || return 1
            printf '[OperationBlocked] Live confirmation could not be established. No approval sent.\n' >&2
            return 1
        fi
        approved=$(printf '%s' "$outcome" | jq -r '.approved')
        # The local decision is consumed before the callback: never retry it.
        CONFIRMED_CARD="$id"
        CONFIRMED_PLAN="$actual"
        [[ "$approved" == "true" ]] && APPROVAL_ATTEMPTED=true
        send_confirmation "$id" "$approved" || return 1
        if [[ "$approved" != "true" ]]; then
            OPERATION_CANCELLED=true
            printf '[OperationCancelled] User rejected or the confirmation deadline expired.\n' >&2
            return 1
        fi
        POST_APPROVAL_CONTENT=false
        printf '[ConfirmationAccepted] Approved live operation %s; verify execution separately.\n' "$tool" >&2
        return 0
    fi
    if [[ -z "$CONFIRMED_CARD" && "$decision" == "0" && -n "$actual" && "$actual" == "$APPROVED_PLAN" ]]; then
        CONFIRMED_CARD="$id"
        CONFIRMED_PLAN="$actual"
        APPROVAL_ATTEMPTED=true
        send_confirmation "$id" true || return 1
        POST_APPROVAL_CONTENT=false
        printf '[ConfirmationAccepted] Approved exact operation %s. Verify the resource state separately; this is not an execution result.\n' "$EXPECTED_TOOL" >&2
        return 0
    fi
    if [[ "$decision" == "0" && "$id" != "$CONFIRMED_CARD" ]]; then
        send_confirmation "$id" false || return 1
    fi
    printf '[OperationBlocked] Forbidden, changed, expired or unapproved confirmation card.\n' >&2
    return 1

}

is_terminal_payload() {
    printf '%s' "$1" | jq -e '.Done == true or .done == true or .IsFinished == true or .is_finished == true' >/dev/null 2>&1
}

process_json_payload() {
    local json="$1"
    local payload error_code content session reasoning function_calls ui_calls sub_agent_calls

    if ! printf '%s' "$json" | jq -e . >/dev/null 2>&1; then
        return 2
    fi
    if [[ "$(printf '%s' "$json" | jq -r 'if .data == "[DONE]" then "true" else "false" end' 2>/dev/null)" == "true" ]]; then
        return 3
    fi

    payload=$(printf '%s' "$json" | jq -c 'if (.data | type) == "object" then .data else . end')
    error_code=$(printf '%s' "$payload" | jq -r '.Code // .ErrorCode // .code // .errorCode // empty')
    if [[ -n "$error_code" ]] || printf '%s' "$payload" | jq -e '
        ((.message // .Message // "") | type == "string" and length > 0)
        and ((has("recovery") or has("did_you_mean")))
        and ((.Content // .content // .SessionId // .sessionId // "") == "")
    ' >/dev/null 2>&1; then
        print_structured_error "$payload"
        return 1
    fi

    content=$(printf '%s' "$payload" | jq -r '.Content // .content // empty')

    session=$(printf '%s' "$payload" | jq -r '.SessionId // .sessionId // .session_id // empty')
    if [[ -n "$session" ]]; then
        if [[ -n "$CONFIRMATION_DIR" && -n "$SESSION_ID" && "$session" != "$SESSION_ID" ]]; then
            printf '[OperationBlocked] Follow-up stream does not match its requested session.\n' >&2
            return 1
        fi
        if [[ ( -n "$APPROVED_PLAN" || -n "$CONFIRMATION_DIR" ) && -n "$PARSED_SESSION_ID" && "$session" != "$PARSED_SESSION_ID" ]]; then
            printf '[OperationBlocked] The operation stream changed its conversation ID.\n' >&2
            return 1
        fi
        PARSED_SESSION_ID="$session"
    fi

    ui_calls=$(printf '%s' "$payload" | jq -c '.UiFunctionCall // .ui_function_call // empty')
    if [[ "$DEBUG" == "true" ]]; then
        reasoning=$(printf '%s' "$payload" | jq -r '.ReasoningContent // .reasoningContent // .reasoning_content // empty')
        [[ -n "$reasoning" ]] && debug_log "ReasoningContent received and omitted from logs."
        function_calls=$(printf '%s' "$payload" | jq -c '.FunctionCall // .function_call // empty')
        [[ -n "$function_calls" ]] && debug_log "FunctionCall tools: $(summarize_tool_calls "$function_calls")"
        [[ -n "$ui_calls" ]] && debug_log "UiFunctionCall tools: $(summarize_tool_calls "$ui_calls")"
        sub_agent_calls=$(printf '%s' "$payload" | jq -c '.SubAgentCall // .sub_agent_call // empty')
        [[ -n "$sub_agent_calls" ]] && debug_log "SubAgentCall tools: $(summarize_tool_calls "$sub_agent_calls")"
    fi
    if [[ -n "$ui_calls" ]] && has_human_confirm "$ui_calls"; then
        if [[ -n "$APPROVED_PLAN" || ( -n "$CONFIRMATION_DIR" && "$READONLY_REQUEST" != "true" ) ]]; then
            [[ -n "$content" ]] && printf '%s\n' "$content"
            PARSED_EVENT_COUNT=$((PARSED_EVENT_COUNT + 1))
            handle_operation_card "$ui_calls" || return 1
            if is_terminal_payload "$payload"; then
                return 3
            fi
            return 0
        fi
        if printf '%s' "$EXTRA_INFO" | jq -e '.mode == "readonly"' >/dev/null 2>&1; then
            printf '\n[ReadonlyViolation] The service requested confirmation in readonly mode.\n' >&2
        else
            printf '\n[ApprovalRequired] No exact operation was approved. No confirmation callback was sent.\n' >&2
        fi
        return 1
    fi

    if [[ -n "$content" ]]; then
        printf '%s' "$content"
        [[ "$APPROVAL_ATTEMPTED" == "true" ]] && POST_APPROVAL_CONTENT=true
    fi
    PARSED_EVENT_COUNT=$((PARSED_EVENT_COUNT + 1))
    if is_terminal_payload "$payload"; then
        return 3
    fi
    return 0
}

parse_stream() {
    local line data result pending_buffer=""
    PARSED_SESSION_ID=""
    PARSED_EVENT_COUNT=0
    PARSED_FINISHED=false
    PARSED_UNKNOWN_OUTPUT=false

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        [[ -z "$line" ]] && continue
        if [[ "$line" == "done" || "$line" == "[DONE]" ]]; then
            PARSED_FINISHED=true
            break
        fi
        data="$line"
        if [[ "$data" == data:* ]]; then
            data="${data#data:}"
            data="${data# }"
            [[ -z "$data" ]] && continue
            if [[ "$data" == "[DONE]" || "$data" == "done" ]]; then
                PARSED_FINISHED=true
                break
            fi
        fi

        set +e
        process_json_payload "$data"
        result=$?
        set -e
        case "$result" in
            0)
                ;;
            1)
                return 1
                ;;
            2)
                pending_buffer+="$line"$'\n'
                # A CLI SDK error envelope is not agent progress. Anything
                # else unparseable makes an operation's admission uncertain.
                if ! looks_like_error "$line" &&
                   [[ ! "$line" =~ ^[[:space:]]*(StatusCode:|Code:|Message:|Detail:|Data:|RequestId:) ]]; then
                    PARSED_UNKNOWN_OUTPUT=true
                fi
                ;;
            3)
                PARSED_FINISHED=true
                break
                ;;
        esac
    done

    if [[ -n "$pending_buffer" ]]; then
        if looks_like_error "$pending_buffer"; then
            print_structured_error "$pending_buffer"
            return 1
        fi
        if ((PARSED_EVENT_COUNT == 0)); then
            print_structured_error 'No valid response events were returned by aliyun CLI.'
            return 1
        fi
        debug_log "Ignored non-JSON transport output."
    fi

    if ((PARSED_EVENT_COUNT == 0)); then
        print_structured_error 'No response events were returned by aliyun CLI.'
        return 1
    fi

    printf '\n'
    emit_session_id
    if [[ "$PARSED_FINISHED" != "true" ]]; then
        debug_log "Response stream ended with clean EOF; completion depends on the aliyun CLI exit code."
    fi
}

emit_session_id() {
    if [[ "$SESSION_ID_EMITTED" == "false" && "$PARSED_SESSION_ID" =~ ^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$ ]]; then
        printf '\n[SessionID] %s\n' "$PARSED_SESSION_ID" >&2
        SESSION_ID_EMITTED=true
    fi
}

cleanup() {
    local exit_code=$?
    if ((exit_code != 0)) && [[ "$APPROVAL_ATTEMPTED" == "true" ]]; then
        printf '[OperationUnverified] An approval was attempted. Verify the resulting state with a separate readonly query; never replay.\n' >&2
    fi
    if ((exit_code != 0 && PARSED_EVENT_COUNT > 0)); then
        emit_session_id
        if [[ "$OPERATION_CANCELLED" != "true" ]]; then
            printf '\n[IncompleteResponse] Request failed after response events; stdout may be partial. Keep the failure status; verify any approved operation by a separate readonly request, never replay it.\n' >&2
        fi
    fi
    if [[ -n "$ALIYUN_PID" ]] && kill -0 "$ALIYUN_PID" 2>/dev/null; then
        kill "$ALIYUN_PID" 2>/dev/null || true
        wait "$ALIYUN_PID" 2>/dev/null || true
    fi
    if [[ -n "$STREAM_DIR" && -d "$STREAM_DIR" ]]; then
        rm -rf "$STREAM_DIR"
    fi
}

trap cleanup EXIT
trap 'exit 130' INT TERM

while (($# > 0)); do
    case "$1" in
        --session-id|--source|--extra-info|--profile|--confirm|--expect-tool|--expect-args|--confirmation-dir)
            require_option_value "$1" "${2:-}"
            case "$1" in
                --session-id) SESSION_ID="$2" ;;
                --source) SOURCE="$2" ;;
                --extra-info) EXTRA_INFO="$2" ;;
                --profile) PROFILE="$2" ;;
                --confirmation-dir) CONFIRMATION_DIR="$2" ;;
                --confirm) CONFIRM_ACTION="$2" ;;
                --expect-tool) EXPECTED_TOOL="$2" ;;
                --expect-args) EXPECTED_ARGS="$2" ;;
            esac
            shift 2
            ;;
        --debug|-d)
            DEBUG=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -)
            if [[ -n "$QUERY" ]]; then
                printf 'Error: provide exactly one query.\n' >&2
                exit 2
            fi
            QUERY=$(cat)
            shift
            ;;
        -* )
            printf 'Error: unknown option: %s\n' "$1" >&2
            usage
            exit 2
            ;;
        *)
            if [[ -n "$QUERY" ]]; then
                printf 'Error: provide exactly one query.\n' >&2
                exit 2
            fi
            QUERY="$1"
            shift
            ;;
    esac
done

if [[ ! "$THROTTLE_RETRIES" =~ ^([0-9]|10)$ ]]; then
    printf 'Error: APSARADB_AGENT_THROTTLE_RETRIES must be an integer from 0 to 10.\n' >&2
    exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
    printf 'Error: Python 3 is required for generic confirmation handling.\n' >&2
    exit 1
fi
check_dependencies
validate_input
if [[ -n "$APPROVED_PLAN" || -n "$CONFIRMATION_DIR" ]] && ! aliyun das create-yao-chi-agent-confirm --help >/dev/null 2>&1; then
    printf 'Error: the official DAS plugin does not expose operation confirmation. Upgrade it before executing an operation.\n' >&2
    exit 1
fi

if ! resolve_wire_source "$SOURCE"; then
    printf '[SourceCompatibilityError] Local DAS validation failed for route %s; no agent request was sent. Inspect aliyun das get-yao-chi-agent --help-search source. Do not bypass the plugin or switch products.\n' "$SOURCE" >&2
    print_structured_error "$SOURCE_PROBE_ERROR"
    exit 2
fi

USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-apsaradb-agent/${SKILL_SESSION_ID} skill-version/${SKILL_VERSION}"
cli_args=(
    das get-yao-chi-agent
    --query "$QUERY"
    --source "$WIRE_SOURCE"
    --extra-info "$EXTRA_INFO"
    --endpoint "$ENDPOINT"
    --read-timeout "$READ_TIMEOUT"
    --connect-timeout "$CONNECT_TIMEOUT"
    --user-agent "$USER_AGENT"
)
[[ -n "$SESSION_ID" ]] && cli_args+=(--session-id "$SESSION_ID")
[[ -n "$PROFILE" ]] && cli_args+=(--profile "$PROFILE")
[[ "$DRY_RUN" == "true" ]] && cli_args+=(--cli-dry-run)

debug_log "Source: $SOURCE (CLI: $WIRE_SOURCE)"
debug_log "Endpoint: $ENDPOINT"
debug_log "User-Agent: $USER_AGENT"
debug_log "ExtraInfo: $EXTRA_INFO"
debug_log "SessionID: ${SESSION_ID:-new conversation}"

if [[ "$DRY_RUN" == "true" ]]; then
    exec aliyun "${cli_args[@]}"
fi

STREAM_DIR=$(mktemp -d)
stream_fifo="$STREAM_DIR/aliyun-stream"
mkfifo "$stream_fifo"

attempt=0
while true; do
    LAST_ERROR_CODE=""
    ERROR_HAS_PROGRESS=false
    aliyun "${cli_args[@]}" >"$stream_fifo" 2>&1 &
    ALIYUN_PID=$!
    if parse_stream <"$stream_fifo"; then
        parser_exit_code=0
    else
        parser_exit_code=$?
    fi

    aliyun_was_killed=false
    # EOF can arrive before the child exits. Do not kill a child whose stream
    # drained normally: wait for its actual status, including late failures.
    if ((parser_exit_code != 0)) || [[ "$PARSED_FINISHED" == "true" ]]; then
        if kill "$ALIYUN_PID" 2>/dev/null; then
            aliyun_was_killed=true
        fi
    fi
    if wait "$ALIYUN_PID"; then
        aliyun_exit_code=0
    else
        aliyun_exit_code=$?
    fi
    ALIYUN_PID=""
    if [[ "$aliyun_was_killed" == "true" && "$PARSED_FINISHED" == "true" &&
          $parser_exit_code -eq 0 && $aliyun_exit_code -eq 143 ]]; then
        aliyun_exit_code=0
    fi
    if ((parser_exit_code == 0 && aliyun_exit_code == 0)); then
        if [[ ( -n "$APPROVED_PLAN" && -z "$CONFIRMED_CARD" ) ||
              ( -n "$CONFIRMED_CARD" && "$PARSED_FINISHED" != "true" &&
                ( "$POST_APPROVAL_CONTENT" != "true" || "$PARSED_UNKNOWN_OUTPUT" == "true" ) ) ]]; then
            printf '[OperationUnverified] No approved confirmation with a completed response. Verify readonly; do not replay.\n' >&2
            exit 1
        fi
        # The official CLI can finish successfully at EOF without a Done event.
        # Wait above for its actual exit status; never infer success from prose.
        if [[ "$PARSED_FINISHED" != "true" ]]; then
            printf '[StreamCompleted] CLI exited 0 at EOF without an explicit end marker.\n' >&2
        fi
        if [[ "$APPROVAL_ATTEMPTED" == "true" ]]; then
            printf '[OperationVerificationRequired] Request completed; independently verify the resulting resource/order/task readonly. Never replay the operation.\n' >&2
        fi
        exit 0
    fi

    # A rejected GetYaoChiAgent admission has not reached a confirmation card
    # or submitted a product write. Retry only that identical request. Once
    # there is progress, a card or an attempted callback, never replay it.
    if [[ "$LAST_ERROR_CODE" == "Throttling.UserConcurrentLimit" &&
          "$ERROR_HAS_PROGRESS" == "false" && -z "$PARSED_SESSION_ID" &&
          -z "$CONFIRMED_CARD" &&
          ( ( -z "$APPROVED_PLAN" && -z "$CONFIRMATION_DIR" ) || "$PARSED_UNKNOWN_OUTPUT" == "false" ) ]] &&
       ((PARSED_EVENT_COUNT == 0 && attempt < THROTTLE_RETRIES)); then
        delay=$((30 * (1 << attempt)))
        ((delay > 120)) && delay=120
        delay=$((delay + RANDOM % 30))
        attempt=$((attempt + 1))
        printf '[ThrottleRetry] %s/%s: waiting %ss before sequential retry on source %s.\n' "$attempt" "$THROTTLE_RETRIES" "$delay" "$SOURCE" >&2
        sleep "$delay"
        continue
    fi
    if ((parser_exit_code != 0)); then
        exit "$parser_exit_code"
    fi
    exit "$aliyun_exit_code"
done
