#!/usr/bin/env bash
# spec_lookup.sh — Convert between PolarDB-X spec codes and hardware config
# (cores / memory), in both directions.
#
# Data source: official PolarDB-X CreateDBInstance spec list, embedded below as
# the source of truth for this script. Update the DATA table if the spec list changes.
#
# Dependencies:
#   - bash >= 3.2 (macOS default) — no associative arrays used
#   - awk (POSIX)
#
# Usage:
#   # Spec code -> hardware
#   ./scripts/spec_lookup.sh --code polarx.x4.large.2e
#
#   # Hardware -> matching spec code(s)
#   ./scripts/spec_lookup.sh --cores 4 --memory 16
#   ./scripts/spec_lookup.sh --cores 8 --memory 32 --category cn --disk local
#   ./scripts/spec_lookup.sh --cores 4 --memory 16 --type dedicated
#
#   # List everything (optionally filtered)
#   ./scripts/spec_lookup.sh --list --category dn --disk cloud
#
#   # JSON output (append --json to any query)
#   ./scripts/spec_lookup.sh --code mysql.n4.medium.25 --json
#
# Filters (optional, for --cores/--memory and --list):
#   --category  cn | dn | standard
#   --disk      local | cloud
#   --type      general | dedicated
#
# Memory accepts "16", "16G", or "16GB".
#
# Exit codes:
#   0 — Found / listed
#   3 — Invalid arguments
#   4 — No matching spec

set -euo pipefail

# --- Embedded spec table: code|cores|memoryGB|category|disk|type ---
# category: cn (enterprise compute) / dn (enterprise storage) / standard
# disk:     local (custom_local_ssd) / cloud (cloud_auto)
read -r -d '' DATA <<'EOF' || true
polarx.x4.medium.2e|2|8|cn|local|General
polarx.x4.large.2e|4|16|cn|local|General
polarx.x4.xlarge.2e|8|32|cn|local|General
polarx.x4.2xlarge.2e|16|64|cn|local|General
polarx.x8.large.2e|4|32|cn|local|Dedicated
polarx.x2.large.2x|8|16|cn|local|Dedicated
polarx.x4.xlarge.2x|8|32|cn|local|Dedicated
polarx.x8.xlarge.2e|8|64|cn|local|Dedicated
polarx.x8.2xlarge.2e|16|128|cn|local|Dedicated
polarx.x4.4xlarge.2e|32|128|cn|local|Dedicated
polarx.x8.4xlarge.2e|32|256|cn|local|Dedicated
polarx.st.8xlarge.2e|60|470|cn|local|Dedicated
polarx.st.12xlarge.2e|90|720|cn|local|Dedicated
polarx.x4.medium.c2e|2|8|cn|cloud|General
polarx.x4.large.c2e|4|16|cn|cloud|General
polarx.x4.xlarge.c2e|8|32|cn|cloud|General
polarx.x4.2xlarge.c2e|16|64|cn|cloud|General
polarx.x8.large.c2e|4|32|cn|cloud|Dedicated
polarx.x2.large.c2x|8|16|cn|cloud|Dedicated
polarx.x4.xlarge.c2x|8|32|cn|cloud|Dedicated
polarx.x8.xlarge.c2e|8|64|cn|cloud|Dedicated
polarx.x8.2xlarge.c2e|16|128|cn|cloud|Dedicated
polarx.x4.4xlarge.c2e|32|128|cn|cloud|Dedicated
polarx.x8.4xlarge.c2e|32|256|cn|cloud|Dedicated
polarx.st.8xlarge.c2e|60|470|cn|cloud|Dedicated
polarx.st.12xlarge.c2e|90|720|cn|cloud|Dedicated
mysql.n2.medium.25|2|4|dn|local|General
mysql.n4.medium.25|2|8|dn|local|General
mysql.n2.large.25|4|8|dn|local|General
mysql.n4.large.25|4|16|dn|local|General
mysql.n4.xlarge.25|8|32|dn|local|General
mysql.n4.2xlarge.25|16|64|dn|local|General
mysql.x4.large.25|4|16|dn|local|Dedicated
mysql.x8.large.25|4|32|dn|local|Dedicated
mysql.x2.xlarge.25|8|16|dn|local|Dedicated
mysql.x8.xlarge.25|8|64|dn|local|Dedicated
mysql.x8.2xlarge.25|16|128|dn|local|Dedicated
mysql.x4.4xlarge.25|32|128|dn|local|Dedicated
mysql.x8.4xlarge.25|32|256|dn|local|Dedicated
mysql.st.8xlarge.25|60|470|dn|local|Dedicated
mysql.st.12xlarge.25|90|720|dn|local|Dedicated
mysql.x8.45xlarge.25|180|1440|dn|local|Dedicated
mysql.x8.60xlarge.25|240|1920|dn|local|Dedicated
polarx.mysql.n2.medium.c25|2|4|dn|cloud|General
polarx.mysql.n4.medium.c25|2|8|dn|cloud|General
polarx.mysql.n2.large.c25|4|8|dn|cloud|General
polarx.mysql.n4.large.c25|4|16|dn|cloud|General
polarx.mysql.n4.xlarge.c25|8|32|dn|cloud|General
polarx.mysql.n4.2xlarge.c25|16|64|dn|cloud|General
polarx.mysql.x4.large.c25|4|16|dn|cloud|Dedicated
polarx.mysql.x8.large.c25|4|32|dn|cloud|Dedicated
polarx.mysql.x2.xlarge.c25|8|16|dn|cloud|Dedicated
polarx.mysql.x8.xlarge.c25|8|64|dn|cloud|Dedicated
polarx.mysql.x8.2xlarge.c25|16|128|dn|cloud|Dedicated
polarx.mysql.x4.4xlarge.c25|32|128|dn|cloud|Dedicated
polarx.mysql.x8.4xlarge.c25|32|256|dn|cloud|Dedicated
polarx.mysql.st.8xlarge.c25|60|470|dn|cloud|Dedicated
polarx.mysql.st.12xlarge.c25|90|720|dn|cloud|Dedicated
polarx.mysql.x8.45xlarge.c25|180|1440|dn|cloud|Dedicated
polarx.mysql.x8.60xlarge.c25|240|1920|dn|cloud|Dedicated
mysql.n8.small.25|1|8|standard|local|General
mysql.n2.medium.25|2|4|standard|local|General
mysql.n4.medium.25|2|8|standard|local|General
mysql.n8.medium.25|2|16|standard|local|General
mysql.n2.large.25|4|8|standard|local|General
mysql.n4.large.25|4|16|standard|local|General
mysql.n8.large.25|4|32|standard|local|General
mysql.n2.xlarge.25|8|16|standard|local|General
mysql.n4.xlarge.25|8|32|standard|local|General
mysql.n8.xlarge.25|8|64|standard|local|General
mysql.n2.2xlarge.25|16|32|standard|local|General
mysql.n4.2xlarge.25|16|64|standard|local|General
mysql.n8.2xlarge.25|16|128|standard|local|General
mysql.x2.medium.25|2|4|standard|local|Dedicated
mysql.x4.medium.25|2|8|standard|local|Dedicated
mysql.x8.medium.25|2|16|standard|local|Dedicated
mysql.x2.large.25|4|8|standard|local|Dedicated
mysql.x4.large.25|4|16|standard|local|Dedicated
mysql.x8.large.25|4|32|standard|local|Dedicated
mysql.x2.xlarge.25|8|16|standard|local|Dedicated
mysql.x4.xlarge.25|8|32|standard|local|Dedicated
mysql.x8.xlarge.25|8|64|standard|local|Dedicated
mysql.x2.2xlarge.25|16|32|standard|local|Dedicated
mysql.x4.2xlarge.25|16|64|standard|local|Dedicated
mysql.x8.2xlarge.25|16|128|standard|local|Dedicated
mysql.x4.4xlarge.25|32|128|standard|local|Dedicated
mysql.x8.4xlarge.25|32|256|standard|local|Dedicated
mysql.x4.8xlarge.25|64|256|standard|local|Dedicated
mysql.x8.8xlarge.25|64|512|standard|local|Dedicated
mysql.st.12xlarge.25|90|720|standard|local|Dedicated
polarx.mysql.n2.medium.c25|2|4|standard|cloud|General
polarx.mysql.n4.medium.c25|2|8|standard|cloud|General
polarx.mysql.n8.medium.c25|2|16|standard|cloud|General
polarx.mysql.n2.large.c25|4|8|standard|cloud|General
polarx.mysql.n4.large.c25|4|16|standard|cloud|General
polarx.mysql.n8.large.c25|4|32|standard|cloud|General
polarx.mysql.n2.xlarge.c25|8|16|standard|cloud|General
polarx.mysql.n4.xlarge.c25|8|32|standard|cloud|General
polarx.mysql.n8.xlarge.c25|8|64|standard|cloud|General
polarx.mysql.x2.medium.c25|2|4|standard|cloud|Dedicated
polarx.mysql.x4.medium.c25|2|8|standard|cloud|Dedicated
polarx.mysql.x8.medium.c25|2|16|standard|cloud|Dedicated
polarx.mysql.x2.large.c25|4|8|standard|cloud|Dedicated
polarx.mysql.x4.large.c25|4|16|standard|cloud|Dedicated
polarx.mysql.x8.large.c25|4|32|standard|cloud|Dedicated
polarx.mysql.x2.xlarge.c25|8|16|standard|cloud|Dedicated
polarx.mysql.x4.xlarge.c25|8|32|standard|cloud|Dedicated
polarx.mysql.x8.xlarge.c25|8|64|standard|cloud|Dedicated
polarx.mysql.x2.2xlarge.c25|16|32|standard|cloud|Dedicated
polarx.mysql.x4.2xlarge.c25|16|64|standard|cloud|Dedicated
polarx.mysql.x8.2xlarge.c25|16|128|standard|cloud|Dedicated
polarx.mysql.x2.4xlarge.c25|32|64|standard|cloud|Dedicated
polarx.mysql.x4.4xlarge.c25|32|128|standard|cloud|Dedicated
polarx.mysql.x8.4xlarge.c25|32|256|standard|cloud|Dedicated
polarx.mysql.x2.8xlarge.c25|64|128|standard|cloud|Dedicated
polarx.mysql.x4.8xlarge.c25|64|256|standard|cloud|Dedicated
polarx.mysql.x8.8xlarge.c25|64|512|standard|cloud|Dedicated
EOF

usage() {
  sed -n '2,45p' "$0" | sed 's/^# \{0,1\}//'
}

# --- Argument parsing ---
MODE=""
CODE=""
CORES=""
MEMORY=""
CATEGORY=""
DISK=""
TYPE=""
JSON=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --code)     MODE="code"; CODE="${2:-}"; shift 2 ;;
    --cores)    MODE="spec"; CORES="${2:-}"; shift 2 ;;
    --memory)   MEMORY="${2:-}"; shift 2 ;;
    --category) CATEGORY="${2:-}"; shift 2 ;;
    --disk)     DISK="${2:-}"; shift 2 ;;
    --type)     TYPE="$(printf '%s' "${2:-}" | tr '[:upper:]' '[:lower:]')"; shift 2 ;;
    --list)     MODE="list"; shift ;;
    --json)     JSON=1; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) echo "Error: unknown argument '$1'" >&2; usage >&2; exit 3 ;;
  esac
done

# Normalize memory: strip GB/G suffix, keep digits only.
if [[ -n "$MEMORY" ]]; then
  MEMORY="$(printf '%s' "$MEMORY" | grep -oE '[0-9]+' | head -1 || true)"
fi

# Validate filters
if [[ -n "$CATEGORY" && "$CATEGORY" != "cn" && "$CATEGORY" != "dn" && "$CATEGORY" != "standard" ]]; then
  echo "Error: --category must be cn | dn | standard" >&2; exit 3
fi
if [[ -n "$DISK" && "$DISK" != "local" && "$DISK" != "cloud" ]]; then
  echo "Error: --disk must be local | cloud" >&2; exit 3
fi
if [[ -n "$TYPE" && "$TYPE" != "general" && "$TYPE" != "dedicated" ]]; then
  echo "Error: --type must be general | dedicated" >&2; exit 3
fi

# awk program: filter rows, aggregate categories per code, print result.
run_query() {
  local want_code="$1" want_cores="$2" want_mem="$3"
  printf '%s\n' "$DATA" | awk -F'|' \
    -v code="$want_code" -v cores="$want_cores" -v mem="$want_mem" \
    -v cat="$CATEGORY" -v disk="$DISK" -v typ="$TYPE" -v json="$JSON" '
    {
      c=$1; cr=$2; mm=$3; ct=$4; dk=$5; tp=$6;
      if (code!="" && c!=code) next;
      if (cores!="" && cr!=cores) next;
      if (mem!="" && mm!=mem) next;
      if (cat!="" && ct!=cat) next;
      if (disk!="" && dk!=disk) next;
      if (typ!="" && tolower(tp)!=typ) next;
      key=c;
      if (!(key in seen)) { order[n++]=key; cores_[key]=cr; mem_[key]=mm; disk_[key]=dk; type_[key]=tp; }
      seen[key]=1;
      # aggregate categories (unique) and disks
      if (index(cats[key],ct)==0) cats[key]=(cats[key]==""?ct:cats[key]","ct);
      if (index(disks[key],dk)==0) disks[key]=(disks[key]==""?dk:disks[key]","dk);
    }
    END {
      if (n==0) exit 4;
      for (i=0;i<n;i++) {
        k=order[i];
        if (json==1) {
          gc=cats[k]; gsub(/,/,"\",\"",gc);
          gd=disks[k]; gsub(/,/,"\",\"",gd);
          printf "{\"code\":\"%s\",\"cores\":%s,\"memoryGB\":%s,\"type\":\"%s\",\"disk\":[\"%s\"],\"categories\":[\"%s\"]}\n", k, cores_[k], mem_[k], type_[k], gd, gc;
        } else {
          printf "%s\t%sC%sG\t%s cores\t%s GB\t[%s]\t%s\n", k, cores_[k], mem_[k], cores_[k], mem_[k], cats[k], type_[k];
        }
      }
    }'
}

case "$MODE" in
  code)
    if [[ -z "$CODE" ]]; then echo "Error: --code requires a spec code" >&2; exit 3; fi
    if ! run_query "$CODE" "" ""; then
      echo "Error: spec code '$CODE' not found in mapping table." >&2; exit 4
    fi
    ;;
  spec)
    if [[ -z "$CORES" || -z "$MEMORY" ]]; then
      echo "Error: --cores and --memory are both required for hardware lookup" >&2; exit 3
    fi
    if ! run_query "" "$CORES" "$MEMORY"; then
      echo "Error: no spec matches ${CORES} cores / ${MEMORY} GB with the given filters." >&2; exit 4
    fi
    ;;
  list)
    run_query "" "" "" || { echo "Error: no spec matches the given filters." >&2; exit 4; }
    ;;
  *)
    echo "Error: specify --code <spec>, or --cores <N> --memory <G>, or --list" >&2
    usage >&2
    exit 3
    ;;
esac
