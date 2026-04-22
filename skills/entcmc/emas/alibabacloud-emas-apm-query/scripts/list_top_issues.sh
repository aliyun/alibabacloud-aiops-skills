#!/usr/bin/env bash
# list_top_issues.sh - For one AppKey x OS, query get-issues across N biz_modules in parallel,
#                      merge results and take Top N sorted by error rate / count.
#
# Depends only on aliyun-cli + jq.
# This script never calls any backend data source / database.
set -euo pipefail

# Self-detect the script's directory -> Skill root, avoiding reliance on an externally exported $SKILL_DIR
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="${SKILL_DIR:-$(dirname "$SCRIPT_DIR")}"

# --- Defaults ---
APP_KEY=""
OS=""
START_MS=""
END_MS=""
TOP_N=5
ORDER_BY="ErrorRate"          # ErrorRate | ErrorCount | ErrorDeviceCount | ErrorDeviceRate
BIZ_MODULES="crash,anr,lag,custom,memory_leak,memory_alloc"
FILTER_JSON=""                # optional, a full JSON string
GRANULARITY="1"
GRANULARITY_UNIT="DAY"
OUTPUT="table"                # table | json
SLEEP_BETWEEN=0.3             # Jitter between parallel calls to avoid QPS throttling

usage() {
  cat <<'EOF'
Usage:
  list_top_issues.sh --app-key <id> --os <android|iphoneos|harmony> \
                     --start-time <ms> --end-time <ms> \
                     [--top-n 5] [--order-by ErrorRate] \
                     [--biz-modules crash,anr,lag,custom,memory_leak,memory_alloc] \
                     [--filter-json '<JSON>'] \
                     [--granularity 1] [--granularity-unit DAY] \
                     [--output table|json]

Example:
  NOW=$(date +%s); END=$(( NOW * 1000 )); START=$(( (NOW-86400) * 1000 ))
  list_top_issues.sh --app-key 335695934 --os iphoneos \
     --start-time $START --end-time $END --top-n 5 --order-by ErrorRate

Notes:
  - Timestamps are in milliseconds (Unix ms); values passed in seconds (< 1e12) are auto-converted by x1000.
  - biz-module is comma-separated. biz_modules with no data are silently skipped.
  - Omitting --filter-json queries the full set; when supplied, the same filter is applied to every biz_module.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-key) APP_KEY="$2"; shift 2 ;;
    --os) OS="$2"; shift 2 ;;
    --start-time) START_MS="$2"; shift 2 ;;
    --end-time) END_MS="$2"; shift 2 ;;
    --top-n) TOP_N="$2"; shift 2 ;;
    --order-by) ORDER_BY="$2"; shift 2 ;;
    --biz-modules) BIZ_MODULES="$2"; shift 2 ;;
    --filter-json) FILTER_JSON="$2"; shift 2 ;;
    --granularity) GRANULARITY="$2"; shift 2 ;;
    --granularity-unit) GRANULARITY_UNIT="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -z "$APP_KEY" || -z "$OS" || -z "$START_MS" || -z "$END_MS" ]] && { usage; exit 2; }

# Input validation: treat every argument from the Agent as untrusted; enforce type, format and bounds
die()      { echo "[ERROR] $*" >&2; exit 2; }
is_uint()  { [[ "$1" =~ ^[0-9]+$ ]]; }
is_puint() { [[ "$1" =~ ^[1-9][0-9]*$ ]]; }
in_set()   { local v="$1"; shift; for x in "$@"; do [[ "$v" == "$x" ]] && return 0; done; return 1; }

is_uint  "$APP_KEY"  || die "--app-key must be numeric, got: $APP_KEY"
in_set   "$OS" android iphoneos harmony || die "--os must be android|iphoneos|harmony, got: $OS"
is_uint  "$START_MS" || die "--start-time must be a non-negative integer (s or ms), got: $START_MS"
is_uint  "$END_MS"   || die "--end-time must be a non-negative integer (s or ms), got: $END_MS"
is_puint "$TOP_N"    || die "--top-n must be a positive integer, got: $TOP_N"
in_set   "$ORDER_BY" ErrorRate ErrorCount ErrorDeviceCount ErrorDeviceRate \
  || die "--order-by must be ErrorRate|ErrorCount|ErrorDeviceCount|ErrorDeviceRate, got: $ORDER_BY"
is_puint "$GRANULARITY" || die "--granularity must be a positive integer, got: $GRANULARITY"
in_set   "$GRANULARITY_UNIT" MINUTE HOUR DAY || die "--granularity-unit must be MINUTE|HOUR|DAY, got: $GRANULARITY_UNIT"
in_set   "$OUTPUT" table json || die "--output must be table|json, got: $OUTPUT"

# biz_modules whitelist check (comma-separated; every element must match the allowed set)
IFS=',' read -r -a _MODULES_CHECK <<< "$BIZ_MODULES"
[[ "${#_MODULES_CHECK[@]}" -eq 0 ]] && die "--biz-modules must not be empty"
for _bm in "${_MODULES_CHECK[@]}"; do
  in_set "$_bm" crash anr lag custom memory_leak memory_alloc \
    || die "--biz-modules contains invalid value: $_bm (allowed: crash|anr|lag|custom|memory_leak|memory_alloc)"
done

# filter-json is optional; when non-empty it must be valid JSON
if [[ -n "$FILTER_JSON" ]]; then
  if ! command -v jq >/dev/null 2>&1; then
    die "jq is required to validate --filter-json"
  fi
  jq empty <<<"$FILTER_JSON" >/dev/null 2>&1 || die "--filter-json is not valid JSON"
fi

# Auto-promote seconds to milliseconds
[[ "$START_MS" -lt 1000000000000 ]] && START_MS=$(( START_MS * 1000 ))
[[ "$END_MS"   -lt 1000000000000 ]] && END_MS=$(( END_MS * 1000 ))

# Time range boundary: EndTime must not be earlier than StartTime
(( END_MS >= START_MS )) || die "--end-time must be >= --start-time"

# Dependency check
command -v aliyun >/dev/null 2>&1 || { echo "[ERROR] aliyun CLI missing; install per references/cli-installation-guide.md" >&2; exit 3; }
command -v jq     >/dev/null 2>&1 || { echo "[ERROR] jq missing (used to merge results)" >&2; exit 3; }

# Set user-agent (helps backend attribution)
export ALIBABA_CLOUD_USER_AGENT="${ALIBABA_CLOUD_USER_AGENT:-AlibabaCloud-Agent-Skills/alibabacloud-emas-apm-query}"

# Explicit CLI timeouts to avoid indefinite hangs on network issues; callers may override via env vars
export ALIBABA_CLOUD_CONNECT_TIMEOUT="${ALIBABA_CLOUD_CONNECT_TIMEOUT:-30}"
export ALIBABA_CLOUD_READ_TIMEOUT="${ALIBABA_CLOUD_READ_TIMEOUT:-60}"

IFS=',' read -r -a MODULES <<< "$BIZ_MODULES"

TMPDIR=$(mktemp -d -t emas-apm-topissues.XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

pids=()
for bm in "${MODULES[@]}"; do
  (
    OUT_FILE="$TMPDIR/${bm}.json"
    ERR_FILE="$TMPDIR/${bm}.err"

    CMD=(aliyun emas-appmonitor get-issues
         --app-key "$APP_KEY"
         --os "$OS"
         --biz-module "$bm"
         --time-range "StartTime=$START_MS" "EndTime=$END_MS" "Granularity=$GRANULARITY" "GranularityUnit=$GRANULARITY_UNIT"
         --page-index 1 --page-size 50
         --order-by "$ORDER_BY" --order-type desc)

    if [[ -n "$FILTER_JSON" ]]; then
      CMD+=(--filter "$FILTER_JSON")
    fi

    if "${CMD[@]}" > "$OUT_FILE" 2> "$ERR_FILE"; then
      # Tag every item with its biz_module so they can be identified after merging
      jq --arg bm "$bm" '
        if .Model and .Model.Items then
          [ .Model.Items[] | {
              bm: $bm,
              dh: .DigestHash,
              name: .Name,
              status: .Status,
              firstVer: .FirstVersion,
              ec: .ErrorCount,
              er: .ErrorRate,
              edc: .ErrorDeviceCount,
              edr: .ErrorDeviceRate,
              type: .Type,
              reason: .Reason
          } ]
        else []
        end
      ' "$OUT_FILE" > "$TMPDIR/${bm}.norm.json"
    else
      echo "[WARN] biz_module=$bm query failed, see $ERR_FILE" >&2
      echo '[]' > "$TMPDIR/${bm}.norm.json"
    fi
  ) &
  pids+=($!)
  sleep "$SLEEP_BETWEEN"
done

for pid in "${pids[@]}"; do wait "$pid" || true; done

# Merge and sort
SORT_KEY="er"
case "$ORDER_BY" in
  ErrorCount)       SORT_KEY="ec" ;;
  ErrorRate)        SORT_KEY="er" ;;
  ErrorDeviceCount) SORT_KEY="edc" ;;
  ErrorDeviceRate)  SORT_KEY="edr" ;;
esac

MERGED=$(jq -s --argjson n "$TOP_N" --arg key "$SORT_KEY" '
  (add // []) | sort_by(.[$key] // 0) | reverse | .[:$n]
' "$TMPDIR"/*.norm.json)

if [[ "$OUTPUT" == "json" ]]; then
  echo "$MERGED"
else
  # Table output
  printf '%-3s  %-6s  %-14s  %-8s  %-10s  %-8s  %s\n' '#' 'bm' 'digestHash' 'ec' 'er' 'edc' 'name'
  echo "$MERGED" | jq -r '
    to_entries[] | "\(.key+1)\t\(.value.bm)\t\(.value.dh)\t\(.value.ec // 0)\t\(.value.er // 0)\t\(.value.edc // 0)\t\(.value.name // "")"
  ' | awk -F '\t' '{ printf "%-3s  %-6s  %-14s  %-8s  %-10s  %-8s  %s\n", $1, $2, $3, $4, $5, $6, $7 }'

  echo
  echo "# Top $TOP_N sort key: $ORDER_BY"
  echo "# Time window: $(date -r $((START_MS/1000)) "+%F %T") ~ $(date -r $((END_MS/1000)) "+%F %T")"
  echo "# Raw JSON saved to: $TMPDIR/<biz>.json"
fi
