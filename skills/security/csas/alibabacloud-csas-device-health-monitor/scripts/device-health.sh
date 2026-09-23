#!/usr/bin/env bash
# Dependencies: Bash >= 3.2, jq >= 1.6, and Alibaba Cloud CLI >= 3.3.3.
# All CSAS API calls are read-only. A local resume file is optional scan state.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SESSION_ID=""
SKILL_VERSION=""
USER_AGENT=""
SCAN_TEMP_DIR=""
CSAS_PLUGIN_READY=0
CSAS_PROFILE="${CSAS_PROFILE:-}"
CSAS_REGION="${CSAS_REGION:-}"

log() { printf '%s\n' "$*" >&2; }
die() { log "error: $*"; exit "${2:-2}"; }
json_error() { jq -n --arg message "$1" '{success:false,error:$message}'; }

require_tools() {
  command -v aliyun >/dev/null 2>&1 || die "aliyun CLI is required" 1
  command -v jq >/dev/null 2>&1 || die "jq is required" 1
}

ensure_csas_plugin() {
  # Plugin setup is local-only. Do this immediately before a CSAS API call so
  # --help and invalid-input paths do not change the caller's CLI installation.
  [ "$CSAS_PLUGIN_READY" -eq 1 ] && return 0
  if aliyun plugin list 2>/dev/null | awk '$1 == "aliyun-cli-csas" { found=1 } END { exit !found }'; then
    CSAS_PLUGIN_READY=1
    return 0
  fi
  log "installing required local CLI plugin: aliyun-cli-csas"
  if ! aliyun plugin install --name aliyun-cli-csas < /dev/null >&2; then
    die "unable to install local dependency aliyun-cli-csas; run 'aliyun plugin install --name aliyun-cli-csas' and retry" 1
  fi
  CSAS_PLUGIN_READY=1
}

cloud_init() {
  [ -n "$USER_AGENT" ] && return
  local manifest="$SKILL_ROOT/references/manifest.json"
  [ -f "$manifest" ] || die "references/manifest.json is missing" 1
  SKILL_VERSION="$(jq -er '.version | select(type == "string" and length > 0)' "$manifest")" \
    || die "references/manifest.json has no non-empty version" 1
  # Read a fixed number of bytes before formatting; avoid SIGPIPE under pipefail.
  SESSION_ID="$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
  [[ "$SESSION_ID" =~ ^[0-9a-f]{32}$ ]] || die "unable to generate a 32-character lowercase hexadecimal session id" 1
  USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-csas-device-health-monitor/${SESSION_ID} skill-version/${SKILL_VERSION}"
}

csas_exec() {
  if [ -n "$CSAS_PROFILE" ] && [ -n "$CSAS_REGION" ]; then
    aliyun --profile "$CSAS_PROFILE" --region "$CSAS_REGION" csas "$@" --user-agent "$USER_AGENT"
  elif [ -n "$CSAS_PROFILE" ]; then
    aliyun --profile "$CSAS_PROFILE" csas "$@" --user-agent "$USER_AGENT"
  elif [ -n "$CSAS_REGION" ]; then
    aliyun --region "$CSAS_REGION" csas "$@" --user-agent "$USER_AGENT"
  else
    aliyun csas "$@" --user-agent "$USER_AGENT"
  fi
}

# The user agent is required for every cloud API call. Do not add it to local CLI commands.
csas() {
  cloud_init
  ensure_csas_plugin
  local attempt=1 max_attempts=4 delay=1 output error_file error_text rc
  while [ "$attempt" -le "$max_attempts" ]; do
    error_file="$(mktemp "${TMPDIR:-/tmp}/csas-error.XXXXXX")"
    if output="$(csas_exec "$@" 2>"$error_file")"; then
      rm -f -- "$error_file"
      printf '%s\n' "$output"
      return 0
    fi
    rc=$?
    error_text="$(cat "$error_file")"
    rm -f -- "$error_file"
    if [ "$attempt" -lt "$max_attempts" ] && [[ "$error_text" =~ Throttl|TooMany|RequestLimit|ServiceUnavailable|InternalError|Timeout|timeout|connection|Connection|HTTP.5[0-9][0-9]|HTTP.429 ]]; then
      log "CSAS call failed with a retriable error (attempt $attempt/$max_attempts); retrying in ${delay}s"
      sleep "$delay"
      delay=$((delay * 2))
      attempt=$((attempt + 1))
      continue
    fi
    log "CSAS call failed after $attempt attempt(s): $error_text"
    return "$rc"
  done
}

validate_number() { [[ "$2" =~ ^[0-9]+([.][0-9]+)?$ ]] || die "$1 must be numeric"; }
validate_percent() { validate_number "$1" "$2"; awk -v value="$2" 'BEGIN { exit !(value >= 0 && value <= 100) }' || die "$1 must be between 0 and 100"; }
validate_positive_int() { [[ "$2" =~ ^[1-9][0-9]*$ ]] || die "$1 must be a positive integer"; }
now_epoch() { date +%s; }

resolve_device() {
  local supplied="$1" listed matches count
  # DeviceTag values are not uniformly UUIDs (for example, some mobile tags
  # begin with A-). Resolve an exact tag first, then treat the input as a hostname.
  listed="$(csas list-user-devices --current-page 1 --page-size 1 --device-tags "$supplied")" || die "failed to resolve device tag" 1
  matches="$(jq --arg tag "$supplied" '[.Devices[]? | select(.DeviceTag == $tag)]' <<<"$listed")"
  count="$(jq 'length' <<<"$matches")"
  if [ "$count" -eq 1 ]; then
    jq -r '.[0].DeviceTag' <<<"$matches"
    return
  fi
  listed="$(csas list-user-devices --current-page 1 --page-size 500 --hostname "$supplied")" || die "failed to resolve hostname" 1
  matches="$(jq --arg name "$supplied" '[.Devices[]? | select(.Hostname == $name)]' <<<"$listed")"
  count="$(jq 'length' <<<"$matches")"
  [ "$count" -eq 1 ] || die "hostname must resolve to exactly one device (found $count)" 2
  jq -r '.[0].DeviceTag' <<<"$matches"
}

trend_summary() {
  # stdin: WorkloadList array or a direct array. args: threshold consecutive max_gap_seconds
  local threshold="$1" consecutive="$2" max_gap="${3:-900}"
  jq --argjson threshold "$threshold" --argjson need "$consecutive" --argjson max_gap "$max_gap" '
    def points: (if type == "array" then . else (.WorkloadList // .workloadList // []) end)
      | map(select((.Timestamp|type) == "number" and (.Workload|type) == "number")) | sort_by(.Timestamp);
    def streaks($p): reduce $p[] as $x
      ({current:0,longest:0,breaches:0,gap_breaks:0,previous:null};
       if (.previous != null and ($x.Timestamp - .previous) > $max_gap) then .current = 0 | .gap_breaks += 1 else . end |
       if $x.Workload >= $threshold then
         .current += 1 | .longest = ([.longest,.current]|max) | .breaches += 1 | .points += [$x]
       else .current = 0 end | .previous = $x.Timestamp);
    points as $p | streaks($p) as $s |
    if ($p|length) == 0 then
      {status:"insufficient_data",sample_count:0,approximation:"No workload samples in the requested window."}
    else
      {status:(if $s.longest >= $need then "warning" elif $s.breaches > 0 then "observation" else "healthy" end),
       sample_count:($p|length),min:($p|map(.Workload)|min),max:($p|map(.Workload)|max),
       average:(($p|map(.Workload)|add / length) * 100 | round / 100),threshold:$threshold,
       consecutive_required:$need,max_gap_seconds:$max_gap,breach_count:$s.breaches,longest_consecutive_breach:$s.longest,gap_break_count:$s.gap_breaks,
       approximation:"Workload points are approximately 10-minute samples; duration is not exact."}
    end'
}

detail_metrics() {
  # stdin: GetUserDevice response or selected Device object. args: disk threshold, battery threshold
  local disk_threshold="$1" battery_threshold="$2"
  jq --argjson disk_threshold "$disk_threshold" --argjson battery_threshold "$battery_threshold" '
    (.Device // .) as $d |
    def present_num($v): ($v != null and ($v|type) == "number");
    ($d.DiskUsed // null) as $used | ($d.DiskAvailable // null) as $available |
    ($d.TerminalInfoCollectTime // null) as $collect_time |
    ($used + $available) as $total |
    {device_tag:$d.DeviceTag,hostname:$d.Hostname,device_type:$d.DeviceType,username:$d.Username,
     collect_time:$collect_time,
     disk:(if (present_num($used) and present_num($available) and $total > 0) then
       ($used / $total * 100) as $percent |
       {status:(if $percent >= 95 then "critical" elif $percent >= $disk_threshold then "warning" else "healthy" end),
        used:$used,available:$available,usage_percent:($percent * 100 | round / 100),threshold:$disk_threshold}
       else {status:"insufficient_data",used:$used,available:$available,threshold:$disk_threshold} end),
     battery:(($d.BatteryHealthPercentage // null) as $health |
       if present_num($health) then
         if ($health == 0 and ((present_num($collect_time) | not) or $collect_time <= 0) and ((present_num($used) and present_num($available)) | not or $total <= 0)) then
           {status:"insufficient_data",snapshot_status:"critical",health_percentage:$health,threshold:$battery_threshold,
            reason:"Zero battery health cannot be corroborated because the device snapshot has no valid collection time or disk capacity."}
         else {status:(if $health < 60 then "critical" elif $health < $battery_threshold then "warning" elif $health <= 85 then "info" else "healthy" end),health_percentage:$health,threshold:$battery_threshold}
         end
       else {status:"insufficient_data",health_percentage:null,threshold:$battery_threshold} end)}
  '
}

fetch_detail() { csas get-user-device --device-tag "$1"; }
fetch_trend() { csas get-user-device-workload-trend --device-tag "$1" --workload-type "$2" --from "$3" --to "$4"; }
fetch_listed_device() { csas list-user-devices --current-page 1 --page-size 1 --device-tags "$1"; }

list_devices() {
  local limit=20 sort_by=UpdateTime raw
  [ "${1:-}" != "--help" ] || { usage list-devices; return; }
  while [ "$#" -gt 0 ]; do case "$1" in
    --limit) limit="$2"; shift 2;; --sort-by) sort_by="$2"; shift 2;; *) die "unknown list-devices argument: $1";; esac; done
  validate_positive_int limit "$limit"; [ "$limit" -le 500 ] || die "--limit must not exceed 500"
  case "$sort_by" in Username|AppVersion|UpdateTime|CreateTime) ;; *) die "--sort-by is not supported";; esac
  raw="$(csas list-user-devices --current-page 1 --page-size "$limit" --sort-by "$sort_by")" || die "device list query failed" 1
  jq '{success:true,fleet_total:(.TotalNum // 0),devices:[.Devices[]? | {device_tag:.DeviceTag,hostname:.Hostname,device_type:.DeviceType,device_status:(.DeviceStatus // "insufficient_data"),update_time:.UpdateTime}]}' <<<"$raw"
}

workload_trend() {
  local device="" metric="" days="" from="" to="" threshold=90 consecutive=2 max_gap=900
  [ "${1:-}" != "--help" ] || { usage workload-trend; return; }
  while [ "$#" -gt 0 ]; do case "$1" in
    --device) device="$2"; shift 2;; --metric) metric="$2"; shift 2;; --days) days="$2"; shift 2;;
    --from) from="$2"; shift 2;; --to) to="$2"; shift 2;; --threshold) threshold="$2"; shift 2;;
    --consecutive) consecutive="$2"; shift 2;; --max-gap-seconds) max_gap="$2"; shift 2;; *) die "unknown workload-trend argument: $1";; esac; done
  [ -n "$device" ] && [[ "$metric" == cpu || "$metric" == mem ]] || die "--device and --metric cpu|mem are required"
  validate_percent threshold "$threshold"; validate_positive_int consecutive "$consecutive"; validate_positive_int max_gap "$max_gap"
  if [ -n "$days" ]; then validate_positive_int days "$days"; [ -z "$from$to" ] || die "--days cannot be combined with --from/--to"; to="$(now_epoch)"; from="$((to - days * 86400))"; fi
  [ -n "$from" ] && [ -n "$to" ] || die "provide --days or both --from and --to"; validate_positive_int from "$from"; validate_positive_int to "$to"; [ "$from" -lt "$to" ] || die "--from must be less than --to"
  local tag raw summary; tag="$(resolve_device "$device")"; raw="$(fetch_trend "$tag" "$metric" "$from" "$to")" || die "workload query failed" 1; summary="$(trend_summary "$threshold" "$consecutive" "$max_gap" <<<"$raw")"
  jq -n --arg tag "$tag" --arg metric "$metric" --argjson from "$from" --argjson to "$to" --argjson summary "$summary" '{success:true,device_tag:$tag,metric:$metric,from:$from,to:$to,summary:$summary}'
}

device_report() {
  local device="" days=7 cpu_threshold=90 mem_threshold=90 disk_threshold=85 battery_threshold=80 consecutive=2 max_gap=900
  [ "${1:-}" != "--help" ] || { usage device-report; return; }
  while [ "$#" -gt 0 ]; do case "$1" in --device) device="$2"; shift 2;; --days) days="$2"; shift 2;; --cpu-threshold) cpu_threshold="$2"; shift 2;; --mem-threshold) mem_threshold="$2"; shift 2;; --disk-threshold) disk_threshold="$2"; shift 2;; --battery-threshold) battery_threshold="$2"; shift 2;; --consecutive) consecutive="$2"; shift 2;; --max-gap-seconds) max_gap="$2"; shift 2;; *) die "unknown device-report argument: $1";; esac; done
  [ -n "$device" ] || die "--device is required"; validate_positive_int days "$days"; validate_percent cpu_threshold "$cpu_threshold"; validate_percent mem_threshold "$mem_threshold"; validate_percent disk_threshold "$disk_threshold"; validate_percent battery_threshold "$battery_threshold"; validate_positive_int consecutive "$consecutive"; validate_positive_int max_gap "$max_gap"
  local tag to from detail listed listed_status cpu mem metrics collection_time collection_status; tag="$(resolve_device "$device")"; to="$(now_epoch)"; from="$((to - days * 86400))"; detail="$(fetch_detail "$tag")" || die "detail query failed" 1
  listed="$(fetch_listed_device "$tag")" || die "device status query failed" 1
  listed_status="$(jq -r --arg tag "$tag" '[.Devices[]? | select(.DeviceTag == $tag) | .DeviceStatus][0] // "insufficient_data"' <<<"$listed")"
  cpu="$(fetch_trend "$tag" cpu "$from" "$to")" || die "CPU workload query failed" 1; mem="$(fetch_trend "$tag" mem "$from" "$to")" || die "memory workload query failed" 1
  metrics="$(detail_metrics "$disk_threshold" "$battery_threshold" <<<"$detail")"
  collection_time="$(jq -r '.collect_time // empty' <<<"$metrics")"
  if [ -z "$collection_time" ] || ! is_valid_time "$collection_time"; then collection_status="insufficient_data"
  elif is_recent_time "$collection_time" "$from"; then collection_status="recently_reporting"
  else collection_status="stale_or_unparseable"; fi
  metrics="$(jq --arg status "$collection_status" --arg device_status "$listed_status" '. + {collection_status:$status,device_status:$device_status}' <<<"$metrics")"
  jq -n --argjson metrics "$metrics" --argjson cpu "$(trend_summary "$cpu_threshold" "$consecutive" "$max_gap" <<<"$cpu")" --argjson memory "$(trend_summary "$mem_threshold" "$consecutive" "$max_gap" <<<"$mem")" --argjson from "$from" --argjson to "$to" '{success:true,window:{from:$from,to:$to},device:$metrics,cpu:$cpu,memory:$memory}'
}

is_valid_time() {
  # A zero, negative, or non-10-digit numeric value is an absent/invalid Unix timestamp.
  local value="$1"
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    [[ "$value" =~ ^[1-9][0-9]{9}$ ]]
  elif date -j -f '%Y-%m-%d %H:%M:%S' "$value" +%s >/dev/null 2>&1; then
    return 0
  elif date -d "$value" +%s >/dev/null 2>&1; then
    return 0
  else
    return 1
  fi
}

is_recent_time() {
  # CSAS list responses use YYYY-MM-DD HH:MM:SS; detail collection time can be Unix seconds.
  # Return false on absent, malformed, or stale values.
  local value="$1" cutoff="$2" epoch
  is_valid_time "$value" || return 1
  if [[ "$value" =~ ^[0-9]{10}$ ]]; then
    epoch="$value"
  elif date -j -f '%Y-%m-%d %H:%M:%S' "$value" +%s >/dev/null 2>&1; then
    epoch="$(date -j -f '%Y-%m-%d %H:%M:%S' "$value" +%s)"
  elif date -d "$value" +%s >/dev/null 2>&1; then
    epoch="$(date -d "$value" +%s)"
  else return 1; fi
  [ "$epoch" -ge "$cutoff" ]
}

write_resume() {
  local file="$1" tags_file="$2" tmp
  [ -n "$file" ] || return 0
  mkdir -p "$(dirname "$file")"; tmp="${file}.tmp.$$"
  jq -n --arg generated "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --slurpfile tags "$tags_file" \
    '{schema_version:1,generated_at:$generated,processed_device_tags:$tags[0]}' >"$tmp"
  mv "$tmp" "$file"
}

health_scan() {
  local days=7 limit=100 type=all cpu_threshold=90 mem_threshold=90 disk_threshold=85 battery_threshold=80 consecutive=2 delay=1 resume_file=""
  [ "${1:-}" != "--help" ] || { usage health-scan; return; }
  while [ "$#" -gt 0 ]; do case "$1" in
    --days) days="$2"; shift 2;; --limit) limit="$2"; shift 2;; --type) type="$2"; shift 2;;
    --cpu-threshold) cpu_threshold="$2"; shift 2;; --mem-threshold) mem_threshold="$2"; shift 2;; --disk-threshold) disk_threshold="$2"; shift 2;; --battery-threshold) battery_threshold="$2"; shift 2;; --consecutive) consecutive="$2"; shift 2;; --delay-seconds) delay="$2"; shift 2;; --resume-file) resume_file="$2"; shift 2;; *) die "unknown health-scan argument: $1";; esac; done
  validate_positive_int days "$days"; validate_positive_int limit "$limit"; [ "$limit" -le 100 ] || die "--limit must not exceed 100"; validate_positive_int consecutive "$consecutive"; validate_number delay "$delay"
  for v in "$cpu_threshold" "$mem_threshold" "$disk_threshold" "$battery_threshold"; do validate_percent threshold "$v"; done
  case "$type" in all|Windows|macOS|Linux|Windows_Wuying|Android|iOS|Harmony) ;; *) die "--type is not a supported CSAS device type";; esac
  local to from cutoff page=1 listed total=0 item tag device_type device_status update_time detail metrics cpu mem cpu_summary mem_summary issues record
  local scanned=0 mobile=0 no_recent=0 errors=0 flagged=0
  local temp_dir tags_file flagged_file; temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/device-health.XXXXXX")"; SCAN_TEMP_DIR="$temp_dir"; trap 'if [ -n "${SCAN_TEMP_DIR:-}" ]; then rm -rf -- "$SCAN_TEMP_DIR"; fi' EXIT
  tags_file="$temp_dir/processed.json"; flagged_file="$temp_dir/flagged.json"; printf '[]\n' >"$tags_file"; printf '[]\n' >"$flagged_file"
  if [ -n "$resume_file" ] && [ -f "$resume_file" ]; then jq -e '.processed_device_tags | type == "array"' "$resume_file" >"$tags_file" || die "invalid resume file" 2; fi
  to="$(now_epoch)"; from="$((to - days * 86400))"; cutoff="$from"
  while [ "$scanned" -lt "$limit" ]; do
    listed="$(csas list-user-devices --current-page "$page" --page-size 500 --sort-by UpdateTime)" || die "device list query failed" 1
    total="$(jq -r '.TotalNum // 0' <<<"$listed")"
    [ "$(jq '(.Devices // []) | length' <<<"$listed")" -gt 0 ] || break
    while IFS= read -r item; do
      [ "$scanned" -lt "$limit" ] || break
      tag="$(jq -r '.DeviceTag // empty' <<<"$item")"; [ -n "$tag" ] || continue
      jq -e --arg tag "$tag" 'index($tag) != null' "$tags_file" >/dev/null && continue
      device_type="$(jq -r '.DeviceType // "unknown"' <<<"$item")"; device_status="$(jq -r '.DeviceStatus // "insufficient_data"' <<<"$item")"; update_time="$(jq -r '.UpdateTime // ""' <<<"$item")"
      [ "$type" = all ] || [ "$type" = "$device_type" ] || continue
      scanned=$((scanned + 1)); log "scanning $scanned/$limit"
      if ! detail="$(fetch_detail "$tag")"; then errors=$((errors + 1)); jq --arg tag "$tag" '. + [$tag]' "$tags_file" >"$tags_file.tmp" && mv "$tags_file.tmp" "$tags_file"; write_resume "$resume_file" "$tags_file"; continue; fi
      metrics="$(detail_metrics "$disk_threshold" "$battery_threshold" <<<"$detail")"
      metrics="$(jq --arg device_status "$device_status" '. + {device_status:$device_status}' <<<"$metrics")"
      cpu_summary='{"status":"insufficient_data","reason":"not queried"}'; mem_summary="$cpu_summary"
      if [[ "$device_type" == Android || "$device_type" == iOS || "$device_type" == Harmony ]]; then mobile=$((mobile + 1))
      elif ! is_recent_time "$update_time" "$cutoff"; then no_recent=$((no_recent + 1)); cpu_summary='{"status":"insufficient_data","reason":"device has no recent report in window"}'; mem_summary="$cpu_summary"
      else
        sleep "$delay"
        if cpu="$(fetch_trend "$tag" cpu "$from" "$to")" && mem="$(fetch_trend "$tag" mem "$from" "$to")"; then
          cpu_summary="$(trend_summary "$cpu_threshold" "$consecutive" <<<"$cpu")"; mem_summary="$(trend_summary "$mem_threshold" "$consecutive" <<<"$mem")"
        else errors=$((errors + 1)); fi
      fi
      issues="$(jq -n --argjson m "$metrics" --argjson cpu "$cpu_summary" --argjson mem "$mem_summary" '
        [ (if $m.disk.status == "healthy" or $m.disk.status == "insufficient_data" then empty else {metric:"disk_usage",value:$m.disk.usage_percent,threshold:$m.disk.threshold,severity:$m.disk.status} end),
          (if $m.battery.status == "healthy" or $m.battery.status == "insufficient_data" then empty else {metric:"battery_health",value:$m.battery.health_percentage,threshold:$m.battery.threshold,severity:$m.battery.status} end),
          (if $cpu.status == "warning" then {metric:"cpu",value:$cpu.max,threshold:$cpu.threshold,severity:"warning",consecutive:$cpu.longest_consecutive_breach} else empty end),
          (if $mem.status == "warning" then {metric:"memory",value:$mem.max,threshold:$mem.threshold,severity:"warning",consecutive:$mem.longest_consecutive_breach} else empty end) ]')"
      if [ "$(jq 'length' <<<"$issues")" -gt 0 ]; then
        flagged=$((flagged + 1)); record="$(jq -n --argjson m "$metrics" --argjson cpu "$cpu_summary" --argjson mem "$mem_summary" --argjson issues "$issues" '{device_tag:$m.device_tag,hostname:$m.hostname,device_type:$m.device_type,device_status:$m.device_status,username:$m.username,issues:$issues,evidence:{disk:$m.disk,battery:$m.battery,collect_time:$m.collect_time,cpu:$cpu,memory:$mem}}')"
        jq --argjson item "$record" '. + [$item]' "$flagged_file" >"$flagged_file.tmp" && mv "$flagged_file.tmp" "$flagged_file"
      fi
      jq --arg tag "$tag" '. + [$tag]' "$tags_file" >"$tags_file.tmp" && mv "$tags_file.tmp" "$tags_file"; write_resume "$resume_file" "$tags_file"
    done < <(jq -c '.Devices[]?' <<<"$listed")
    page=$((page + 1)); [ "$page" -le 10000 ] || break
  done
  jq -n --argjson from "$from" --argjson to "$to" --argjson total "$total" --argjson scanned "$scanned" --argjson mobile "$mobile" --argjson no_recent "$no_recent" --argjson errors "$errors" --argjson flagged "$(cat "$flagged_file")" --arg resume "$resume_file" '{success:($errors == 0),window:{from:$from,to:$to},fleet_total:$total,scanned_devices:$scanned,skipped:{mobile:$mobile,no_recent_data:$no_recent},errors:$errors,flagged_count:($flagged|length),flagged:$flagged,resume_file:(if $resume == "" then null else $resume end)}'
}
usage() {
  case "${1:-}" in
    list-devices) printf '%s\n' 'Usage: device-health.sh list-devices [--limit N] [--sort-by Username|AppVersion|UpdateTime|CreateTime]' ;;
    device-report) printf '%s\n' 'Usage: device-health.sh device-report --device <DeviceTag-or-hostname> [--days N] [--cpu-threshold P] [--mem-threshold P] [--disk-threshold P] [--battery-threshold P] [--consecutive N] [--max-gap-seconds N]' ;;
    workload-trend) printf '%s\n' 'Usage: device-health.sh workload-trend --device <DeviceTag-or-hostname> --metric cpu|mem (--days N | --from EPOCH --to EPOCH) [--threshold P] [--consecutive N] [--max-gap-seconds N]' ;;
    health-scan) printf '%s\n' 'Usage: device-health.sh health-scan [--days N] [--limit N] [--type TYPE] [--cpu-threshold P] [--mem-threshold P] [--disk-threshold P] [--battery-threshold P] [--consecutive N] [--delay-seconds N] [--resume-file PATH]' ;;
    *) printf '%s\n' 'Usage: device-health.sh [--profile PROFILE] [--region REGION] <device-report|workload-trend|health-scan> [options]' ;;
  esac
}

if [ "${DEVICE_HEALTH_LIB_ONLY:-}" != 1 ]; then
  require_tools
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --profile) [ "$#" -ge 2 ] || die "--profile requires a value"; CSAS_PROFILE="$2"; shift 2 ;;
      --region) [ "$#" -ge 2 ] || die "--region requires a value"; CSAS_REGION="$2"; shift 2 ;;
      *) break ;;
    esac
  done
  command="${1:-}"; [ -n "$command" ] || { usage; exit 2; }; shift
  case "$command" in list-devices) list_devices "$@";; device-report) device_report "$@";; workload-trend) workload_trend "$@";; health-scan) health_scan "$@";; --help|-h|help) usage;; *) die "unknown command: $command";; esac
fi
