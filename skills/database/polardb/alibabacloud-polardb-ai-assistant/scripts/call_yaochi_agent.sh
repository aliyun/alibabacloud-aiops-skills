#!/usr/bin/env bash
# =============================================================================
# call_yaochi_agent.sh - Alibaba Cloud YaoChi Agent CLI Script
# =============================================================================
# Invokes get-yao-chi-agent API via aliyun CLI DAS plugin with streaming response.
# Requires DAS plugin: aliyun plugin install --names aliyun-cli-das
# Uses existing aliyun CLI credentials (aliyun configure), no extra setup needed.
#
# Usage:
#   bash call_yaochi_agent.sh "List PolarDB clusters in Hangzhou region"
#   bash call_yaochi_agent.sh "Analyze cluster pc-xxx performance" --session-id <session-id>
#   echo "List clusters" | bash call_yaochi_agent.sh -
# =============================================================================

set -euo pipefail

# --- Configuration ---
ENDPOINT="das.cn-shanghai.aliyuncs.com"
SOURCE="polardb-console"
READ_TIMEOUT=180
CONNECT_TIMEOUT=30

# --- Variables ---
QUERY=""
SESSION_ID=""
PROFILE=""
DEBUG=false
OBSERVABILITY_SESSION_ID="${ALIBABACLOUD_AGENT_SKILL_SESSION_ID:-}"

# --- Functions ---
usage() {
    cat >&2 <<EOF
Alibaba Cloud YaoChi Agent CLI Tool (based on aliyun CLI)

Usage:
  $(basename "$0") <query> [options]

Arguments:
  <query>              Query content (natural language), use '-' to read from stdin

Options:
  --session-id <id>    Session ID for multi-turn conversation
  --profile <name>     Specify aliyun CLI profile
  --debug, -d          Enable debug mode
  --help, -h           Show help information

Examples:
  $(basename "$0") "List PolarDB clusters in Hangzhou region"
  $(basename "$0") "Analyze cluster pc-xxx performance" --session-id "sess-xxx"
  echo "List clusters" | $(basename "$0") -
EOF
}

debug_log() {
    if [[ "$DEBUG" == "true" ]]; then
        echo "[DEBUG] $*" >&2
    fi
}

generate_observability_session_id() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 16
        return 0
    fi

    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-' | cut -c1-32
        return 0
    fi

    od -An -N16 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n'
}

json_field_from_lines() {
    local raw="$1"
    local jq_filter="$2"
    local line

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" ]] && continue
        if echo "$line" | jq -e . &>/dev/null 2>&1; then
            local value
            value=$(echo "$line" | jq -r "$jq_filter // empty" 2>/dev/null) || true
            if [[ -n "$value" ]]; then
                echo "$value"
                return 0
            fi
        fi
    done <<< "$raw"
}

extract_error_code() {
    local raw="$1"
    local value

    value=$(json_field_from_lines "$raw" '.Code // .ErrorCode // .code // .errorCode') || true
    if [[ -n "$value" ]]; then
        echo "$value"
        return 0
    fi

    value=$(echo "$raw" | sed -nE 's/.*"(Code|ErrorCode|code|errorCode)"[[:space:]]*:[[:space:]]*"([^"]+)".*/\2/p' | head -n 1)
    if [[ -z "$value" ]]; then
        value=$(echo "$raw" | sed -nE 's/^[[:space:]]*(Code|ErrorCode)[[:space:]]*:[[:space:]]*([^[:space:]]+).*/\2/p' | head -n 1)
    fi
    echo "$value"
}

extract_error_message() {
    local raw="$1"
    local value

    value=$(json_field_from_lines "$raw" '.Message // .ErrorMessage // .Description // .message // .errorMessage // .description') || true
    if [[ -n "$value" ]]; then
        echo "$value"
        return 0
    fi

    value=$(echo "$raw" | sed -nE 's/.*"(Message|ErrorMessage|Description|message|errorMessage|description)"[[:space:]]*:[[:space:]]*"([^"]+)".*/\2/p' | head -n 1)
    if [[ -z "$value" ]]; then
        value=$(echo "$raw" | sed -nE 's/^[[:space:]]*(Message|ErrorMessage|Description)[[:space:]]*:[[:space:]]*(.*)$/\2/p' | head -n 1)
    fi
    echo "$value"
}

extract_auth_action() {
    local raw="$1"
    local value

    value=$(json_field_from_lines "$raw" '.AuthAction // .authAction // .Data.AuthAction // .data.AuthAction') || true
    if [[ -n "$value" ]]; then
        echo "$value"
        return 0
    fi

    value=$(echo "$raw" | sed -nE 's/.*"(AuthAction|authAction)"[[:space:]]*:[[:space:]]*"([^"]+)".*/\2/p' | head -n 1)
    if [[ -z "$value" ]]; then
        value=$(echo "$raw" | sed -nE 's/^[[:space:]]*(AuthAction|authAction)[[:space:]]*:[[:space:]]*([^[:space:]]+).*/\2/p' | head -n 1)
    fi
    echo "$value"
}

extract_request_id() {
    local raw="$1"
    local value

    value=$(json_field_from_lines "$raw" '.RequestId // .requestId // .RequestID // .requestID') || true
    if [[ -n "$value" ]]; then
        echo "$value"
        return 0
    fi

    value=$(echo "$raw" | sed -nE 's/.*"(RequestId|requestId|RequestID|requestID)"[[:space:]]*:[[:space:]]*"([^"]+)".*/\2/p' | head -n 1)
    if [[ -z "$value" ]]; then
        value=$(echo "$raw" | sed -nE 's/^[[:space:]]*(RequestId|RequestID)[[:space:]]*:[[:space:]]*([^[:space:]]+).*/\2/p' | head -n 1)
    fi
    echo "$value"
}

error_suggestion() {
    local code="$1"
    local auth_action="$2"

    case "$code" in
        *Forbidden*|*NoPermission*|*Unauthorized*)
            if [[ -n "$auth_action" ]]; then
                echo "Grant the RAM action $auth_action to the current aliyun CLI identity, then retry."
            else
                echo "Grant the required RAM permissions for YaoChi Agent and PolarDB read-only access, then retry."
            fi
            ;;
        *InvalidAccessKeyId*|*SignatureDoesNotMatch*|*InvalidSecurityToken*|*SecurityToken*)
            echo "Check aliyun CLI credentials with 'aliyun configure get'; refresh expired STS/OAuth credentials if needed."
            ;;
        *Throttling*|*ConcurrentLimit*)
            echo "Wait for the previous query to finish and retry. YaoChi Agent allows at most 2 concurrent sessions per account."
            ;;
        *Timeout*|*Connection*|*ServiceUnavailable*)
            echo "Check network connectivity to das.cn-shanghai.aliyuncs.com and retry; use --debug if the issue persists."
            ;;
        "")
            echo "Run the same command with --debug and inspect the raw Aliyun CLI error."
            ;;
        *)
            echo "Review the Aliyun CLI error details below, apply the suggested permission or configuration fix, then retry."
            ;;
    esac
}

print_structured_error() {
    local raw="$1"
    local code message auth_action request_id suggestion

    code=$(extract_error_code "$raw") || true
    message=$(extract_error_message "$raw") || true
    auth_action=$(extract_auth_action "$raw") || true
    request_id=$(extract_request_id "$raw") || true
    suggestion=$(error_suggestion "$code" "$auth_action")

    echo "" >&2
    echo "[YaoChi Agent Error]" >&2
    echo "ErrorCode: ${code:-Unknown}" >&2
    echo "ErrorMessage: ${message:-No detailed message returned by aliyun CLI.}" >&2
    if [[ -n "$auth_action" ]]; then
        echo "AuthAction: $auth_action" >&2
    fi
    if [[ -n "$request_id" ]]; then
        echo "RequestId: $request_id" >&2
    fi
    echo "Suggestion: $suggestion" >&2
    echo "Reference: references/ram-policies.md" >&2
    echo "Reference: references/verification-method.md" >&2
    if [[ -n "$code" ]]; then
        echo "Troubleshooting: https://api.aliyun.com/troubleshoot?q=$code" >&2
    fi
    if [[ "$DEBUG" == "true" ]]; then
        echo "RawError:" >&2
        echo "$raw" >&2
    fi
}

looks_like_cli_error() {
    local raw="$1"

    [[ "$raw" == *"SDKError"* ]] \
        || [[ "$raw" == *"Error:"* ]] \
        || [[ -n "$(extract_error_code "$raw")" ]]
}

# Check dependencies
check_dependencies() {
    if ! command -v aliyun &>/dev/null; then
        echo "Error: aliyun CLI not found, please install (>= 3.3.3)" >&2
        echo "Install: download and review the official installer before running it locally" >&2
        echo "See: references/cli-installation-guide.md" >&2
        exit 1
    fi

    if ! command -v jq &>/dev/null; then
        echo "Error: jq is required to parse JSON response" >&2
        echo "Install:" >&2
        echo "  macOS:  brew install jq" >&2
        echo "  Ubuntu: sudo apt-get install jq" >&2
        echo "  CentOS: sudo yum install jq" >&2
        exit 1
    fi

    local version
    version=$(aliyun version 2>/dev/null || echo "0.0.0")
    debug_log "aliyun CLI version: $version"

    # Ensure DAS plugin is installed (get-yao-chi-agent requires plugin for Signature V3)
    if ! aliyun das get-yao-chi-agent --help &>/dev/null 2>&1; then
        echo "Error: DAS plugin not installed" >&2
        echo "Please install manually: aliyun plugin install --names aliyun-cli-das" >&2
        exit 1
    fi
}

# Stream parse response (read from stdin line by line, output in real-time)
# DAS plugin returns streaming JSON (one {"data": {...}} per line) or SSE format
parse_sse_streaming() {
    local session_id=""
    local format_detected=false
    local is_sse=false
    local is_json_stream=false
    local pending_buffer=""

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        [[ -z "$line" ]] && continue

        # Detect response format on first line
        if [[ "$format_detected" == false ]]; then
            if [[ "$line" =~ ^data: ]]; then
                is_sse=true
                debug_log "Detected SSE format response"
            elif echo "$line" | jq -e '.data' &>/dev/null 2>&1; then
                is_json_stream=true
                debug_log "Detected streaming JSON format response (DAS plugin)"
            else
                # Check if error response
                local error_code
                error_code=$(echo "$line" | jq -r '.Code // empty' 2>/dev/null) || true
                if [[ -n "$error_code" ]]; then
                    print_structured_error "$line"
                    return 1
                fi
                # Try to handle as plain JSON response
                local content
                content=$(echo "$line" | jq -r '.Content // .Data // empty' 2>/dev/null) || true
                if [[ -n "$content" ]]; then
                    printf "%s" "$content"
                    session_id=$(echo "$line" | jq -r '.SessionId // empty' 2>/dev/null) || true
                    format_detected=true
                    continue
                fi

                pending_buffer+="${line}"$'\n'
                continue
            fi
            format_detected=true
        fi

        # Process SSE format
        if [[ "$is_sse" == true ]]; then
            if [[ "$line" =~ ^data:\ ?(.*) ]]; then
                local data="${BASH_REMATCH[1]}"
                [[ -z "$data" ]] && continue
                [[ "$data" == "[DONE]" ]] && break

                local chunk_content
                chunk_content=$(echo "$data" | jq -r '.Content // empty' 2>/dev/null) || true
                [[ -n "$chunk_content" ]] && printf "%s" "$chunk_content"

                local chunk_session
                chunk_session=$(echo "$data" | jq -r '.SessionId // empty' 2>/dev/null) || true
                [[ -n "$chunk_session" ]] && session_id="$chunk_session"

                if [[ "$DEBUG" == "true" ]]; then
                    local reasoning
                    reasoning=$(echo "$data" | jq -r '.ReasoningContent // empty' 2>/dev/null) || true
                    [[ -n "$reasoning" ]] && debug_log "Reasoning: $reasoning"
                fi
            fi
        fi

        # Process streaming JSON format
        if [[ "$is_json_stream" == true ]]; then
            local done_marker
            done_marker=$(echo "$line" | jq -r 'if (.data == "[DONE]") or (((.data | type) == "object") and (.data.Done == true or .data.done == true)) then "true" else empty end' 2>/dev/null) || true
            [[ "$done_marker" == "true" ]] && break

            local chunk_content
            chunk_content=$(echo "$line" | jq -r '.data.Content // empty' 2>/dev/null) || true
            [[ -n "$chunk_content" ]] && printf "%s" "$chunk_content"

            local chunk_session
            chunk_session=$(echo "$line" | jq -r '.data.SessionId // empty' 2>/dev/null) || true
            [[ -n "$chunk_session" ]] && session_id="$chunk_session"

            if [[ "$DEBUG" == "true" ]]; then
                local reasoning
                reasoning=$(echo "$line" | jq -r '.data.ReasoningContent // empty' 2>/dev/null) || true
                [[ -n "$reasoning" ]] && debug_log "Reasoning: $reasoning"
            fi
        fi
    done

    if [[ "$format_detected" == false && -n "$pending_buffer" ]]; then
        if looks_like_cli_error "$pending_buffer"; then
            print_structured_error "$pending_buffer"
            return 1
        fi
        printf "%s" "$pending_buffer"
        return 0
    fi

    # Output newline (end of content)
    echo ""

    # Output session ID (to stderr for multi-turn conversation)
    if [[ -n "$session_id" ]]; then
        echo "" >&2
        echo "[SessionID] $session_id" >&2
    fi
}

# --- Argument parsing ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --session-id)
            SESSION_ID="$2"
            shift 2
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --debug|-d)
            DEBUG=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -)
            QUERY=$(cat)
            shift
            ;;
        -*)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
        *)
            QUERY="$1"
            shift
            ;;
    esac
done

# --- Input validation ---
# Max query length (reasonable limit for natural language queries)
MAX_QUERY_LENGTH=4000
# Max session ID length
MAX_SESSION_ID_LENGTH=128
# Session ID format: alphanumeric, hyphens, underscores only
SESSION_ID_PATTERN='^[a-zA-Z0-9_-]+$'

validate_input() {
    # Validate QUERY
    if [[ -z "$QUERY" ]]; then
        usage
        exit 1
    fi

    local query_length=${#QUERY}
    if [[ $query_length -gt $MAX_QUERY_LENGTH ]]; then
        echo "Error: Query too long ($query_length chars). Maximum allowed: $MAX_QUERY_LENGTH" >&2
        exit 1
    fi

    # Validate SESSION_ID if provided
    if [[ -n "$SESSION_ID" ]]; then
        local session_id_length=${#SESSION_ID}
        if [[ $session_id_length -gt $MAX_SESSION_ID_LENGTH ]]; then
            echo "Error: Session ID too long ($session_id_length chars). Maximum allowed: $MAX_SESSION_ID_LENGTH" >&2
            exit 1
        fi

        if [[ ! "$SESSION_ID" =~ $SESSION_ID_PATTERN ]]; then
            echo "Error: Invalid session ID format. Only alphanumeric, hyphens, and underscores allowed." >&2
            exit 1
        fi
    fi

    # Validate PROFILE if provided (alphanumeric, hyphens, underscores, dots)
    if [[ -n "$PROFILE" ]]; then
        if [[ ! "$PROFILE" =~ ^[a-zA-Z0-9._-]+$ ]]; then
            echo "Error: Invalid profile name format." >&2
            exit 1
        fi
    fi

    if [[ -z "$OBSERVABILITY_SESSION_ID" ]]; then
        OBSERVABILITY_SESSION_ID="$(generate_observability_session_id)"
    fi

    if [[ ! "$OBSERVABILITY_SESSION_ID" =~ ^[0-9a-f]{32}$ ]]; then
        echo "Error: ALIBABACLOUD_AGENT_SKILL_SESSION_ID must be a 32-character lowercase hexadecimal string." >&2
        exit 1
    fi
}

# --- Validation ---
validate_input

check_dependencies

# --- Build CLI command arguments ---
# Use DAS plugin's kebab-case command, supports Signature V3
cli_args=(das get-yao-chi-agent
    --query "$QUERY"
    --source "$SOURCE"
    --endpoint "$ENDPOINT"
    --read-timeout "$READ_TIMEOUT"
    --connect-timeout "$CONNECT_TIMEOUT"
    --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-polardb-ai-assistant/${OBSERVABILITY_SESSION_ID}"
)

if [[ -n "$SESSION_ID" ]]; then
    cli_args+=(--session-id "$SESSION_ID")
fi

if [[ -n "$PROFILE" ]]; then
    cli_args+=(--profile "$PROFILE")
fi

# --- Output query info ---
echo "[Query] $QUERY" >&2
if [[ -n "$SESSION_ID" ]]; then
    echo "[SessionID] $SESSION_ID" >&2
fi
echo "============================================================" >&2
echo "[YaoChi Agent Response]" >&2

debug_log "Executing: aliyun ${cli_args[*]}"

# --- Execute and stream parse ---
# Use a FIFO so the parser can stop on stream end markers and then terminate
# a CLI plugin process that keeps the connection open.
STREAM_DIR=$(mktemp -d)
STREAM_FIFO="$STREAM_DIR/aliyun-stream"
mkfifo "$STREAM_FIFO"

set +e
aliyun "${cli_args[@]}" >"$STREAM_FIFO" 2>&1 &
ALIYUN_PID=$!

parse_sse_streaming <"$STREAM_FIFO"
parser_exit_code=$?

aliyun_was_killed=false
if jobs -pr | grep -qx "$ALIYUN_PID"; then
    kill "$ALIYUN_PID" 2>/dev/null || true
    aliyun_was_killed=true
fi

wait "$ALIYUN_PID"
exit_code=$?
set -e
rm -rf "$STREAM_DIR"

if [[ "$aliyun_was_killed" == "true" && $parser_exit_code -eq 0 ]]; then
    exit_code=0
fi

if [[ $exit_code -ne 0 || $parser_exit_code -ne 0 ]]; then
    # Non-zero exit but content already output via pipe, just log debug info
    debug_log "aliyun CLI exit code: $exit_code (streaming response may return non-zero)"
    if [[ $exit_code -ne 0 ]]; then
        exit "$exit_code"
    fi
    exit "$parser_exit_code"
fi
