#!/usr/bin/env bash
# dig_issue.sh - For a known digestHash, run get-issue + get-errors + get-error (N samples)
#                in sequence, and produce a "markdown + raw JSON folder" bundle for analysis.
#
# Depends only on aliyun-cli + jq.
# This script never calls any backend data source / database.
set -euo pipefail

# Self-detect the script's directory -> Skill root, avoiding reliance on an externally exported $SKILL_DIR
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="${SKILL_DIR:-$(dirname "$SCRIPT_DIR")}"

APP_KEY=""
OS=""
BIZ_MODULE=""
DIGEST_HASH=""
START_MS=""
END_MS=""
SAMPLE_SIZE=3
OUT_DIR=""
GRANULARITY="1"
GRANULARITY_UNIT="DAY"

usage() {
  cat <<'EOF'
Usage:
  dig_issue.sh --app-key <id> --os <android|iphoneos|harmony> \
               --biz-module <crash|anr|lag|custom|memory_leak|memory_alloc> \
               --digest-hash <Base36 13 chars> \
               --start-time <ms> --end-time <ms> \
               [--sample-size 3] [--out-dir <dir>]

Example:
  NOW=$(date +%s); END=$(( NOW * 1000 )); START=$(( (NOW-86400*7) * 1000 ))
  dig_issue.sh --app-key 335695934 --os iphoneos --biz-module crash \
    --digest-hash 3JE6F43KCQ1SV --start-time $START --end-time $END --sample-size 3

Output:
  $OUT_DIR/
    01-get-issue.json          # raw get-issue response (TimeRange with Granularity)
    02-get-errors.json         # raw get-errors sample list (TimeRange without Granularity)
    samples/<Uuid>.json        # full get-error response per sample
    report.md                  # structured markdown report
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-key) APP_KEY="$2"; shift 2 ;;
    --os) OS="$2"; shift 2 ;;
    --biz-module) BIZ_MODULE="$2"; shift 2 ;;
    --digest-hash) DIGEST_HASH="$2"; shift 2 ;;
    --start-time) START_MS="$2"; shift 2 ;;
    --end-time) END_MS="$2"; shift 2 ;;
    --sample-size) SAMPLE_SIZE="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --granularity) GRANULARITY="$2"; shift 2 ;;
    --granularity-unit) GRANULARITY_UNIT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -z "$APP_KEY" || -z "$OS" || -z "$BIZ_MODULE" || -z "$DIGEST_HASH" || -z "$START_MS" || -z "$END_MS" ]] && { usage; exit 2; }

# Input validation: treat every argument from the Agent as untrusted; enforce type, format and bounds
die()      { echo "[ERROR] $*" >&2; exit 2; }
is_uint()  { [[ "$1" =~ ^[0-9]+$ ]]; }
is_puint() { [[ "$1" =~ ^[1-9][0-9]*$ ]]; }
in_set()   { local v="$1"; shift; for x in "$@"; do [[ "$v" == "$x" ]] && return 0; done; return 1; }

is_uint  "$APP_KEY"  || die "--app-key must be numeric, got: $APP_KEY"
in_set   "$OS" android iphoneos harmony || die "--os must be android|iphoneos|harmony, got: $OS"
in_set   "$BIZ_MODULE" crash anr lag custom memory_leak memory_alloc \
  || die "--biz-module must be crash|anr|lag|custom|memory_leak|memory_alloc, got: $BIZ_MODULE"
# DigestHash constraint: 13-char Base36 (uppercase digits + letters)
[[ "$DIGEST_HASH" =~ ^[0-9A-Z]{13}$ ]] || die "--digest-hash must be 13 Base36 chars (^[0-9A-Z]{13}$), got: $DIGEST_HASH"
is_uint  "$START_MS"    || die "--start-time must be a non-negative integer (s or ms), got: $START_MS"
is_uint  "$END_MS"      || die "--end-time must be a non-negative integer (s or ms), got: $END_MS"
is_puint "$SAMPLE_SIZE" || die "--sample-size must be a positive integer, got: $SAMPLE_SIZE"
is_puint "$GRANULARITY" || die "--granularity must be a positive integer, got: $GRANULARITY"
in_set   "$GRANULARITY_UNIT" MINUTE HOUR DAY || die "--granularity-unit must be MINUTE|HOUR|DAY, got: $GRANULARITY_UNIT"

# Auto-promote seconds to milliseconds
[[ "$START_MS" -lt 1000000000000 ]] && START_MS=$(( START_MS * 1000 ))
[[ "$END_MS"   -lt 1000000000000 ]] && END_MS=$(( END_MS * 1000 ))

# Time range boundary: EndTime must not be earlier than StartTime
(( END_MS >= START_MS )) || die "--end-time must be >= --start-time"

command -v aliyun >/dev/null 2>&1 || { echo "[ERROR] aliyun CLI missing" >&2; exit 3; }
command -v jq     >/dev/null 2>&1 || { echo "[ERROR] jq missing" >&2; exit 3; }

export ALIBABA_CLOUD_USER_AGENT="${ALIBABA_CLOUD_USER_AGENT:-AlibabaCloud-Agent-Skills/alibabacloud-emas-apm-query}"

# Explicit CLI timeouts to avoid indefinite hangs on network issues; callers may override via env vars
export ALIBABA_CLOUD_CONNECT_TIMEOUT="${ALIBABA_CLOUD_CONNECT_TIMEOUT:-30}"
export ALIBABA_CLOUD_READ_TIMEOUT="${ALIBABA_CLOUD_READ_TIMEOUT:-60}"

[[ -z "$OUT_DIR" ]] && OUT_DIR="./emas-apm-dig-${APP_KEY}-${DIGEST_HASH}-$(date +%s)"
mkdir -p "$OUT_DIR/samples"

echo "[INFO] Output directory: $OUT_DIR"

# 1. get-issue — TimeRange with Granularity
echo "[STEP 1/3] get-issue ..."
aliyun emas-appmonitor get-issue \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ_MODULE" \
  --time-range "StartTime=$START_MS" "EndTime=$END_MS" "Granularity=$GRANULARITY" "GranularityUnit=$GRANULARITY_UNIT" \
  --digest-hash "$DIGEST_HASH" \
  > "$OUT_DIR/01-get-issue.json" 2>"$OUT_DIR/01-get-issue.err" \
  || { echo "[ERROR] get-issue failed, see $OUT_DIR/01-get-issue.err"; exit 4; }

# 2. get-errors — pass only StartTime/EndTime; page-size >=2 to avoid unknown error
PAGE_SIZE=$SAMPLE_SIZE
[[ "$PAGE_SIZE" -lt 2 ]] && PAGE_SIZE=2

echo "[STEP 2/3] get-errors ..."
aliyun emas-appmonitor get-errors \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ_MODULE" \
  --time-range "StartTime=$START_MS" "EndTime=$END_MS" \
  --digest-hash "$DIGEST_HASH" \
  --page-index 1 --page-size "$PAGE_SIZE" \
  > "$OUT_DIR/02-get-errors.json" 2>"$OUT_DIR/02-get-errors.err" \
  || { echo "[ERROR] get-errors failed, see $OUT_DIR/02-get-errors.err"; exit 4; }

# Extract ClientTime + Uuid + Did triples into a TSV
jq -r '.Model.Items // [] | .[] | "\(.ClientTime)\t\(.Uuid)\t\(.Did // "")"' \
  "$OUT_DIR/02-get-errors.json" > "$OUT_DIR/02-get-errors.tsv"

if [[ ! -s "$OUT_DIR/02-get-errors.tsv" ]]; then
  TOTAL=$(jq '.Model.Total // 0' "$OUT_DIR/02-get-errors.json")
  echo "[WARN] get-errors returned no samples (Total=$TOTAL); skipping get-error"
fi

# 3. get-error — fetch one-by-one using the triples
echo "[STEP 3/3] get-error ..."
SAMPLE_IDX=0
while IFS=$'\t' read -r CT UUID DID; do
  SAMPLE_IDX=$((SAMPLE_IDX + 1))
  [[ "$SAMPLE_IDX" -gt "$SAMPLE_SIZE" ]] && break

  echo "  [$SAMPLE_IDX] uuid=$UUID  clientTime=$CT"
  CMD=(aliyun emas-appmonitor get-error
       --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ_MODULE"
       --client-time "$CT"
       --uuid "$UUID"
       --digest-hash "$DIGEST_HASH")
  [[ -n "$DID" ]] && CMD+=(--did "$DID")

  "${CMD[@]}" > "$OUT_DIR/samples/${UUID}.json" 2>"$OUT_DIR/samples/${UUID}.err" \
    || echo "    [WARN] get-error failed, see $OUT_DIR/samples/${UUID}.err"
  sleep 0.2
done < "$OUT_DIR/02-get-errors.tsv"

# 4. Generate the markdown report
REPORT="$OUT_DIR/report.md"
{
  echo "# Issue Dig Report"
  echo
  echo "- **AppKey**: \`$APP_KEY\`"
  echo "- **OS**: \`$OS\`"
  echo "- **BizModule**: \`$BIZ_MODULE\`"
  echo "- **DigestHash**: \`$DIGEST_HASH\`"
  echo "- **TimeRange**: $(date -r $((START_MS/1000)) "+%F %T") ~ $(date -r $((END_MS/1000)) "+%F %T")"
  echo
  echo "## 1. Issue overview (get-issue)"
  echo
  jq -r '
    .Model // {} |
    "- **Name**: \(.Name // "-")\n- **Status**: \(.Status // "-")\n- **FirstVersion**: \(.FirstVersion // "-")\n- **AffectedVersions**: \((.AffectedVersions // []) | join(", "))\n- **ErrorCount**: \(.ErrorCount // 0)\n- **ErrorRate**: \(.ErrorRate // 0)\n- **ErrorDeviceCount**: \(.ErrorDeviceCount // 0)\n- **Type**: \(.Type // "-")\n- **Reason**: \((.Reason // "-") | gsub("\\n"; "    "))"
  ' "$OUT_DIR/01-get-issue.json"
  echo
  echo "### Aggregated stack (Stack)"
  echo
  echo '```'
  jq -r '.Model.Stack // "(empty)"' "$OUT_DIR/01-get-issue.json"
  echo '```'
  echo
  echo "## 2. Sample list (get-errors, first $SAMPLE_SIZE)"
  echo
  echo "| # | ClientTime | Uuid | Did | Utdid |"
  echo "| --- | --- | --- | --- | --- |"
  jq -r '
    .Model.Items // [] | to_entries[] |
    "| \(.key+1) | \(.value.ClientTime) | \(.value.Uuid) | \(.value.Did // "-") | \(.value.Utdid // "-") |"
  ' "$OUT_DIR/02-get-errors.json"
  echo
  echo "## 3. Sample details (get-error)"
  for f in "$OUT_DIR"/samples/*.json; do
    [[ -f "$f" ]] || continue
    uuid=$(basename "$f" .json)
    echo
    echo "### Sample: \`$uuid\`"
    echo
    jq -r '
      .Model // {} |
      "- **AppVersion**: \(.AppVersion // "-")\n- **OsVersion**: \(.OsVersion // "-")\n- **Brand**: \(.Brand // "-")\n- **DeviceModel**: \(.DeviceModel // "-")\n- **Access**: \(.Access // "-")\n- **Country/Province/City**: \(.Country // "-")/\(.Province // "-")/\(.City // "-")\n- **InMainProcess / ForeGround**: \(.InMainProcess // "-") / \(.ForeGround // "-")\n- **ExceptionType**: \(.ExceptionType // "-")\n- **ExceptionSubtype**: \(.ExceptionSubtype // "-")\n- **ExceptionCodes**: \(.ExceptionCodes // "-")\n- **ExceptionMsg**: \((.ExceptionMsg // "-") | gsub("\\n"; "    "))"
    ' "$f"
    echo
    echo "#### Backtrace"
    echo '```'
    jq -r '.Model.Backtrace // "(empty)"' "$f"
    echo '```'
    echo
    echo "#### EventLog (last 3KB)"
    echo '```'
    jq -r '(.Model.EventLog // "(empty)") | (if length > 3000 then .[length-3000:] else . end)' "$f"
    echo '```'
    echo
    echo "#### Page path (Controllers)"
    echo '```'
    jq -r '.Model.Controllers // "(empty)"' "$f"
    echo '```'
  done
  echo
  echo "## 4. Next steps"
  echo
  echo "- If the current directory contains the APP source, follow \`references/troubleshoot-workflow.md\` to map stack frames to source files."
  echo "- Otherwise: switch to the APP source repo root and continue from this report."
} > "$REPORT"

echo
echo "[DONE] Report generated: $REPORT"
