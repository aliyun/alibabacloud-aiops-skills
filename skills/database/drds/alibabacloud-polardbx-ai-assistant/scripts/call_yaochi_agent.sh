#!/usr/bin/env bash
# =============================================================================
# call_yaochi_agent.sh - Alibaba Cloud YaoChi Agent CLI Script (PolarDB-X)
# =============================================================================
# Invokes get-yao-chi-agent API via aliyun CLI DAS plugin with streaming response.
# Requires DAS plugin: aliyun plugin install --names aliyun-cli-das
# Uses existing aliyun CLI credentials (aliyun configure), no extra setup needed.
#
# Usage:
#   bash call_yaochi_agent.sh "List PolarDB-X instances in Hangzhou region"
#   bash call_yaochi_agent.sh "Analyze instance pxc-xxx performance" --session-id <session-id>
#   echo "List instances" | bash call_yaochi_agent.sh -
# =============================================================================

set -euo pipefail

# --- Configuration ---
ENDPOINT="das.cn-shanghai.aliyuncs.com"
SOURCE="polarx"
READ_TIMEOUT=180
CONNECT_TIMEOUT=30
THROTTLE_RETRY_MAX=3
THROTTLE_RETRY_INTERVAL=20

# --- Variables ---
QUERY=""
SESSION_ID=""
PROFILE=""
DEBUG=false

# --- Functions ---
usage() {
    cat >&2 <<EOF
Alibaba Cloud YaoChi Agent CLI Tool - PolarDB-X (based on aliyun CLI)

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
  $(basename "$0") "List PolarDB-X instances in Hangzhou region"
  $(basename "$0") "Analyze instance pxc-xxx performance" --session-id "sess-xxx"
  echo "List instances" | $(basename "$0") -
EOF
}

debug_log() {
    if [[ "$DEBUG" == "true" ]]; then
        echo "[DEBUG] $*" >&2
    fi
}

# Check dependencies
check_dependencies() {
    if ! command -v aliyun &>/dev/null; then
        echo "Error: aliyun CLI not found, please install (>= 3.3.1)" >&2
        echo "Install: curl -fsSL https://aliyuncli.alicdn.com/install.sh | bash" >&2
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
        debug_log "DAS plugin not installed, auto-installing..."
        aliyun plugin install --names aliyun-cli-das >&2 || {
            echo "Error: Failed to install DAS plugin, please run manually: aliyun plugin install --names aliyun-cli-das" >&2
            exit 1
        }
    fi
}

# Stream parse response (read from stdin line by line, output in real-time)
# DAS plugin returns streaming JSON (one {"data": {...}} per line) or SSE format
parse_sse_streaming() {
    local session_id=""
    local format_detected=false
    local is_sse=false
    local is_json_stream=false
    local error_buffer=""

    while IFS= read -r line; do
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
                # Might be error response or plain JSON, buffer first
                error_buffer="$line"
                # Check if error response
                local error_code
                error_code=$(echo "$line" | jq -r '.Code // empty' 2>/dev/null) || true
                if [[ -n "$error_code" ]]; then
                    local error_msg
                    error_msg=$(echo "$line" | jq -r '.Message // empty' 2>/dev/null) || true
                    echo "Error: ${error_msg:-Unknown error} (${error_code})" >&2
                    if [[ "$error_code" == *"Throttling"* ]] || [[ "$error_code" == *"ConcurrentLimit"* ]]; then
                        echo "Max 2 concurrent sessions per account. Please wait for previous query to complete." >&2
                        return 2
                    fi
                    return 1
                fi
                # Try to handle as plain JSON response
                local content
                content=$(echo "$line" | jq -r '.Content // .Data // empty' 2>/dev/null) || true
                if [[ -n "$content" ]]; then
                    printf "%s" "$content"
                    session_id=$(echo "$line" | jq -r '.SessionId // empty' 2>/dev/null) || true
                else
                    # Cannot parse, output as-is
                    echo "$line"
                fi
                format_detected=true
                continue
            fi
            format_detected=true
        fi

        # Process SSE format
        if [[ "$is_sse" == true ]]; then
            if [[ "$line" =~ ^data:\ ?(.*) ]]; then
                local data="${BASH_REMATCH[1]}"
                [[ "$data" == "[DONE]" || -z "$data" ]] && continue

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

# --- Validation ---
if [[ -z "$QUERY" ]]; then
    usage
    exit 1
fi

check_dependencies

# --- Build CLI command arguments ---
# Use DAS plugin's kebab-case command, supports Signature V3
cli_args=(das get-yao-chi-agent
    --query "$QUERY"
    --source "$SOURCE"
    --endpoint "$ENDPOINT"
    --read-timeout "$READ_TIMEOUT"
    --connect-timeout "$CONNECT_TIMEOUT"
    --user-agent AlibabaCloud-Agent-Skills
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

# --- Execute and stream parse (with throttling retry) ---
for (( attempt=1; attempt<=THROTTLE_RETRY_MAX; attempt++ )); do
    debug_log "Attempt $attempt/$THROTTLE_RETRY_MAX: aliyun ${cli_args[*]}"

    set +e
    aliyun "${cli_args[@]}" 2>&1 | parse_sse_streaming
    parse_exit=${PIPESTATUS[1]}
    set -e

    # Exit code 2 = throttling error, retry after waiting
    if [[ $parse_exit -eq 2 ]]; then
        if [[ $attempt -lt $THROTTLE_RETRY_MAX ]]; then
            echo "[Retry] Throttling detected, waiting ${THROTTLE_RETRY_INTERVAL}s before retry ($attempt/$THROTTLE_RETRY_MAX)..." >&2
            sleep "$THROTTLE_RETRY_INTERVAL"
            continue
        else
            echo "[Retry] Throttling persists after $THROTTLE_RETRY_MAX attempts, giving up." >&2
            exit 1
        fi
    fi

    # Any other result (success or non-throttling error), stop retrying
    break
done
