#!/bin/bash
# Shared helpers for aws-scan-region.sh and aws-scan-enrich.sh
# Source this file — do not execute directly.

export AWS_SCAN_CMD_TIMEOUT="${AWS_SCAN_CMD_TIMEOUT:-120}"
AWS_SCAN_REDACT="${AWS_SCAN_REDACT:-1}"
AWS_SCAN_MAX_PARALLEL="${AWS_SCAN_MAX_PARALLEL:-20}"
export AWS_RETRY_MODE="${AWS_RETRY_MODE:-standard}"
export AWS_MAX_ATTEMPTS="${AWS_MAX_ATTEMPTS:-5}"

# ── timeout wrapper (GNU timeout → perl fallback → no timeout) ───────────────
_run_scan_cmd() {
    if command -v timeout >/dev/null 2>&1; then
        timeout --signal=TERM "$AWS_SCAN_CMD_TIMEOUT" "$@"
    elif command -v perl >/dev/null 2>&1; then
        perl -e 'alarm $ENV{AWS_SCAN_CMD_TIMEOUT}; exec @ARGV' -- "$@"
    else
        "$@"
    fi
}

# ── redact sensitive data (IPs, AWS IDs, account numbers) ────────────────────
_redact_inventory() {
    if [[ "$AWS_SCAN_REDACT" != "1" ]]; then
        cat
        return 0
    fi
    python3 -c '
import re, sys
t = sys.stdin.read()
t = re.sub(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b", "[REDACTED-IP]", t)
t = re.sub(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}\b", "[REDACTED-CIDR]", t)
t = re.sub(r"\b(i-[0-9a-f]{8,17}|vol-[0-9a-f]{8,17}|eni-[0-9a-f]{8,17}|snap-[0-9a-f]{8,17})\b", "[REDACTED-AWSID]", t, flags=re.I)
t = re.sub(r"\b(?:vpc|subnet|rtb|sg|igw|nat|eipalloc|vpce)-[0-9a-f]{8,17}\b", "[REDACTED-AWSID]", t, flags=re.I)
t = re.sub(r"\b[0-9]{12}\b", "[REDACTED-ACCOUNT]", t)
sys.stdout.write(t)
' 2>/dev/null || cat
}

# ── region validation ────────────────────────────────────────────────────────
validate_aws_region() {
    local r="$1"
    if [[ ! "$r" =~ ^[a-z0-9-]+$ ]] || [[ ${#r} -gt 32 ]]; then
        echo "Invalid AWS region (use alphanumeric and hyphens only): $r" >&2
        exit 1
    fi
}

# ── parallel job throttle ────────────────────────────────────────────────────
# Call _wait_for_slot before launching each background job.
# Keeps running background jobs <= AWS_SCAN_MAX_PARALLEL.
_wait_for_slot() {
    while (( $(jobs -rp | wc -l) >= AWS_SCAN_MAX_PARALLEL )); do
        sleep 0.3
    done
}

# ── merge job files, filtering empty sections ────────────────────────────────
# Usage: _merge_jobs <jobs_dir> <title> <output_file>
_merge_jobs() {
    local jobs_dir="$1" title="$2" output_file="$3"
    local _tmp
    _tmp="$(mktemp)"
    {
        echo "# $title"
        echo "Generated: $(date)"
        echo "Scanner: $(basename "$0")"
        echo ""
        echo "---"
        echo ""
        while IFS= read -r f; do
            [ -f "$f" ] || continue
            # skip sections whose code block is empty (## Title\n```\n```\n)
            if python3 -c "
import re, sys
t = open(sys.argv[1]).read()
# match code block: backticks, optional content, backticks
m = re.search(r'\x60{3}\n(.*?)\x60{3}', t, re.S)
sys.exit(0 if m and m.group(1).strip() == '' else 1)
" "$f" 2>/dev/null; then
                continue
            fi
            cat "$f"
        done < <(find "$jobs_dir" -maxdepth 1 -name '*.txt' | sort)
    } > "$_tmp"
    _redact_inventory < "$_tmp" > "$output_file"
    rm -f "$_tmp"
}

# ── elapsed time helper ──────────────────────────────────────────────────────
_print_elapsed() {
    local start="$1"
    local elapsed=$(( $(date +%s) - start ))
    echo "Total time: ${elapsed}s"
}
