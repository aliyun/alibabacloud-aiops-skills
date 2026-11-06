#!/usr/bin/env bash
# vpc-fw-engine.sh - Read and adjust the IPS defense configuration and the ACL
# engine mode of ONE VPC boundary firewall (Express Connect / peering family).
#
# These settings are NOT parameters of CreateVpcFirewallConfigure /
# ModifyVpcFirewallConfigure; they live behind two dedicated write APIs:
#   modify-vpc-firewall-default-ips-config  (run mode / rule class / capabilities)
#   ModifyVpcFirewallAclEngineMode          (strict vs loose ACL engine mode)
# Both are write operations with direct protection-strength impact, so every
# set follows: impact preview -> explicit confirmation (--yes) -> execute ->
# read-back verification. --dry-run prints the command and changes nothing.
#
# CLI NAMING IS DELIBERATELY MIXED. aliyun CLI 3.4.x registers the two IPS APIs
# under their kebab-case names only ("DescribeVpcFirewallDefaultIpsConfig is not
# a valid api"), and a kebab-case API name only accepts kebab-case flags. The
# ACL engine mode API and DescribeVpcFirewallList are registered in PascalCase
# and take PascalCase flags. Each call below uses the form the CLI accepts.
#
# A VPC firewall that has never been configured (FirewallSwitchStatus
# "notconfigured") has no engine instance: both write APIs reject its ID with
# ErrorParametersFirewallId. Such a firewall is therefore refused here with
# FirewallNotConfigured and routed to the create workflow instead.
#
# Usage: bash scripts/vpc-fw-engine.sh <ips|acl-engine> [options]
#
# NOTE: bash 3.2 compatible on purpose (the macOS default). No `local -n`
# namerefs, no unguarded "${arr[@]}" expansion.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

# --- Shared helpers ---------------------------------------------------------

# Read existence, switch status, ACL engine mode and the list-level IPS block in
# ONE call. DescribeVpcFirewallList is the only API that returns
# AclConfig.StrictMode, and it answers for unconfigured firewalls too, so it is
# also the not-found / not-configured gate for both subcommands.
# Prints: <status> <strict_mode> <connect_sub_type> <run_mode> <rule_class> <basic_rules> <enable_all_patch>
# or the single token NOTFOUND.
read_fw_state() { # <vpc-firewall-id> [member-uid]
  local fw_id="$1" member_uid="${2:-}"
  local args=(--VpcFirewallId "$fw_id" --CurrentPage 1 --PageSize 10 --Lang zh)
  if [[ -n "$member_uid" ]]; then args+=(--MemberUid "$member_uid"); fi
  local resp
  resp=$(call_cfw_api "DescribeVpcFirewallList" ${args[@]+"${args[@]}"}) || {
    printf '%s' "$resp"
    return 1
  }
  printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
fws = d.get("VpcFirewalls") or []
if not fws:
    print("NOTFOUND")
    sys.exit(0)
fw = fws[0]
acl = fw.get("AclConfig") or {}
ips = fw.get("IpsConfig") or {}
print(" ".join(str(x) for x in (
    fw.get("FirewallSwitchStatus") or "unknown",
    acl.get("StrictMode", -1),
    fw.get("ConnectSubType") or "unknown",
    ips.get("RunMode", -1),
    ips.get("RuleClass", -1),
    ips.get("BasicRules", -1),
    ips.get("EnableAllPatch", -1),
)))
' || return 1
}

# Read the authoritative IPS configuration. The dedicated describe API is tried
# first (quietly, because it is expected to fail for an unconfigured firewall);
# the IpsConfig block already fetched from DescribeVpcFirewallList is the
# fallback, so the caller always gets four integers back.
# Prints: <source-api> <run_mode> <rule_class> <basic_rules> <enable_all_patch>
read_ips_effective() { # <vpc-firewall-id> <member-uid> <list_run_mode> <list_rule_class> <list_basic_rules> <list_enable_all_patch>
  local fw_id="$1" member_uid="${2:-}"
  local args=(--vpc-firewall-id "$fw_id")
  if [[ -n "$member_uid" ]]; then args+=(--member-uid "$member_uid"); fi
  local resp parsed
  resp=$(call_cfw_api "describe-vpc-firewall-default-ips-config" ${args[@]+"${args[@]}"} 2>/dev/null) || resp=""
  if [[ -n "$resp" ]]; then
    parsed=$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
keys = ("RunMode", "RuleClass", "BasicRules", "EnableAllPatch")
if any(d.get(k) is None for k in keys):
    sys.exit(1)
print(" ".join(str(int(d[k])) for k in keys))
' 2>/dev/null) || parsed=""
    if [[ -n "$parsed" ]]; then
      printf 'DescribeVpcFirewallDefaultIpsConfig %s' "$parsed"
      return 0
    fi
  fi
  printf 'DescribeVpcFirewallList %s %s %s %s' "$3" "$4" "$5" "$6"
}

# Validate a 0/1 flag value.
validate_bool_flag() { # <name> <value>
  if [[ "$2" != "0" && "$2" != "1" ]]; then
    log_error "Invalid --${1}: '${2}'. Must be exactly 0 or 1."
    return 1
  fi
}

# Validate the IPS rule class (1 loose / 2 medium / 3 strict).
validate_rule_class() {
  if [[ "$1" != "1" && "$1" != "2" && "$1" != "3" ]]; then
    log_error "Invalid --rule-class: '${1}'. Must be 1 (loose), 2 (medium) or 3 (strict)."
    return 1
  fi
}

# Human label for a numeric enum, kept in one place so preview and output agree.
enum_label() { # <field> <value>
  case "$1" in
    run_mode)         if [[ "$2" == "1" ]]; then printf 'block'; else printf 'observe'; fi ;;
    rule_class)       case "$2" in 1) printf 'loose' ;; 2) printf 'medium' ;; 3) printf 'strict' ;; 0) printf 'not applicable' ;; *) printf 'unknown' ;; esac ;;
    basic_rules)      if [[ "$2" == "1" ]]; then printf 'on'; else printf 'off'; fi ;;
    enable_all_patch) if [[ "$2" == "1" ]]; then printf 'on'; else printf 'off'; fi ;;
    strict_mode)      if [[ "$2" == "1" ]]; then printf 'strict'; else printf 'loose'; fi ;;
    *)                printf 'unknown' ;;
  esac
}

# Emit the structured refusal used when a write is requested without --yes.
refuse_without_confirmation() { # <what> <command-preview>
  cat <<EOF
{
  "success": false,
  "error_code": "ConfirmationRequired",
  "error_message": "$(json_escape "$1") is a write operation. Review the impact preview above, get explicit user confirmation, then re-run the same command with --yes.",
  "command_preview": "$(json_escape "$2")"
}
EOF
  exit 2
}

# Refuse an engine write on a firewall that has no engine instance yet.
refuse_not_configured() { # <vpc-firewall-id> <status> <what>
  log_error "Diagnosis: VPC firewall ${1} is '${2}' - it has no engine instance, so ${3} cannot be applied."
  log_error "  Fix: create and enable the VPC firewall first (vpc-fw-lifecycle.sh assess / create, then vpc-fw-switch.sh open), then re-run this command."
  printf '{"success": false, "error_code": "FirewallNotConfigured", "vpc_firewall_id": "%s", "firewall_switch_status": "%s", "error_message": "The VPC firewall is not configured yet, so it has no IPS/ACL engine instance to modify. Create and enable it first, then adjust the engine settings."}\n' "$1" "$2"
  exit 2
}

# `configuring` is an undocumented transitional status seen for a minute or two
# after CreateVpcFirewallConfigure returns, before the first `closed`. Whether the
# engine instance already exists at that point was NOT probed, so this neither
# refuses nor silently proceeds: warn, and let the API be the authority. A write
# that is too early surfaces as ErrorParametersFirewallId /
# ErrorFirewallStatusCannotModify, both of which diagnose_cfw_error explains.
warn_if_provisioning() { # <vpc-firewall-id> <status>
  if [[ "$2" == "configuring" ]]; then
    log_warn "VPC firewall ${1} is still 'configuring' (provisioning after creation). The engine instance may not exist yet; if this write is rejected, poll 'vpc-fw-switch.sh query --vpc-firewall-id ${1}' until the status settles to closed/opened and retry."
  fi
}

# Render one "current -> target" diff line of the impact preview.
preview_line() { # <field> <current> <target> <display-name>
  local cur="$2" tgt="$3"
  if [[ "$cur" == "$tgt" ]]; then
    printf '  - %s: %s (%s) - unchanged\n' "$4" "$cur" "$(enum_label "$1" "$cur")" >&2
  else
    printf '  - %s: %s (%s) -> %s (%s)\n' "$4" "$cur" "$(enum_label "$1" "$cur")" "$tgt" "$(enum_label "$1" "$tgt")" >&2
  fi
}

# Turn a comma separated downgrade list into a JSON array literal.
downgrades_to_json() {
  if [[ -z "$1" ]]; then
    printf '[]'
    return 0
  fi
  printf '%s' "$1" | python3 -c 'import json,sys;print(json.dumps([x.strip() for x in sys.stdin.read().split(",") if x.strip()]))'
}

# --- ips --------------------------------------------------------------------

cmd_ips() {
  local FW_ID="" RUN_MODE="" RULE_CLASS="" BASIC_RULES="" ENABLE_ALL_PATCH="" MEMBER_UID=""
  local DRY_RUN=false YES=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vpc-firewall-id) arg_value "--vpc-firewall-id" "${@:2}"; FW_ID="$2"; shift 2 ;;
      --run-mode) arg_value "--run-mode" "${@:2}"; RUN_MODE="$2"; shift 2 ;;
      --rule-class) arg_value "--rule-class" "${@:2}"; RULE_CLASS="$2"; shift 2 ;;
      --basic-rules) arg_value "--basic-rules" "${@:2}"; BASIC_RULES="$2"; shift 2 ;;
      --enable-all-patch) arg_value "--enable-all-patch" "${@:2}"; ENABLE_ALL_PATCH="$2"; shift 2 ;;
      --member-uid) arg_value "--member-uid" "${@:2}"; MEMBER_UID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --yes|-y) YES=true; shift ;;
      --help|-h)
        show_help "vpc-fw-engine.sh ips" \
          "Read or adjust the IPS defense configuration of one VPC boundary firewall" \
          "vpc-fw-engine.sh ips --vpc-firewall-id <vfw-xxxx> [--run-mode 0|1] [--rule-class 1|2|3] [--basic-rules 0|1] [--enable-all-patch 0|1] [--member-uid <uid>] [--yes] [--dry-run]" \
          "  --vpc-firewall-id <id>   Required. The VPC boundary firewall instance
  --run-mode <0|1>         IPS defense mode: 0=observe, 1=block
  --rule-class <1|2|3>     IPS rule group: 1=loose, 2=medium, 3=strict. Optional;
                           only sent when given. The service derives it from the
                           run mode: observe always stores 0, block normalises 0 to 3
  --basic-rules <0|1>      Basic-rules capability switch
  --enable-all-patch <0|1> Virtual-patching capability switch
  --member-uid <uid>       Member account UID when operating from a management account
  --dry-run                Print the modify command without executing it
  --yes                    Non-interactive confirmation for the write

  With no write options this subcommand is a read-only GET of the current config.
  Omitted write options are filled from the current values, so a partial change
  never silently resets the other three fields.
  Requires a configured firewall; a 'notconfigured' one is refused."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "vpc-firewall-id" "$FW_ID" || exit 1
  validate_vpc_firewall_id "$FW_ID" || exit 1
  if [[ -n "$MEMBER_UID" ]]; then validate_member_uid "$MEMBER_UID" || exit 1; fi
  # Every enum is validated locally BEFORE the first API call, so a typo costs
  # nothing and never reaches the service.
  if [[ -n "$RUN_MODE" ]]; then validate_bool_flag "run-mode" "$RUN_MODE" || exit 1; fi
  if [[ -n "$RULE_CLASS" ]]; then validate_rule_class "$RULE_CLASS" || exit 1; fi
  if [[ -n "$BASIC_RULES" ]]; then validate_bool_flag "basic-rules" "$BASIC_RULES" || exit 1; fi
  if [[ -n "$ENABLE_ALL_PATCH" ]]; then validate_bool_flag "enable-all-patch" "$ENABLE_ALL_PATCH" || exit 1; fi

  local state status strict_mode subtype list_run_mode list_rule_class list_basic_rules list_enable_all_patch
  state=$(read_fw_state "$FW_ID" "$MEMBER_UID") || {
    local code msg
    code=$(extract_api_error_code "$state"); msg=$(extract_api_error_message "$state")
    diagnose_cfw_error "$code" "$msg"
    output_error "${code:-UnknownError}" "${msg:-DescribeVpcFirewallList failed}"
    exit 2
  }
  if [[ "$state" == "NOTFOUND" ]]; then
    diagnose_cfw_error "ErrorVpcFirewallNotFound" ""
    output_error "ErrorVpcFirewallNotFound" "No VPC boundary firewall with id ${FW_ID} is visible to this account."
    exit 2
  fi
  read -r status strict_mode subtype list_run_mode list_rule_class list_basic_rules list_enable_all_patch <<<"$state"

  local ips_source cur_run_mode cur_rule_class cur_basic_rules cur_enable_all_patch
  ips_source=$(read_ips_effective "$FW_ID" "$MEMBER_UID" "$list_run_mode" "$list_rule_class" "$list_basic_rules" "$list_enable_all_patch")
  read -r ips_source cur_run_mode cur_rule_class cur_basic_rules cur_enable_all_patch <<<"$ips_source"
  # The dedicated read is attempted with its stderr suppressed (it is expected to
  # fail for an unconfigured firewall), so name the source that was actually used
  # instead of leaving an invisible API call in the log.
  if [[ "$ips_source" == "DescribeVpcFirewallDefaultIpsConfig" ]]; then
    log_info "IPS configuration read from DescribeVpcFirewallDefaultIpsConfig."
  else
    log_info "Dedicated IPS read unavailable; using the IpsConfig block from DescribeVpcFirewallList."
  fi

  local configured=true
  if [[ "$status" == "notconfigured" ]]; then configured=false; fi

  # --- GET mode: nothing to change. ---
  if [[ -z "$RUN_MODE" && -z "$RULE_CLASS" && -z "$BASIC_RULES" && -z "$ENABLE_ALL_PATCH" ]]; then
    if [[ "$configured" != "true" ]]; then
      log_warn "VPC firewall ${FW_ID} is '${status}'. The values below are the account defaults that WOULD apply once it is configured; there is no live engine instance to read."
    fi
    printf '{"success": true, "mode": "get", "vpc_firewall_id": "%s", "firewall_switch_status": "%s", "configured": %s, "source_api": "%s", "ips_config": {"run_mode": %s, "rule_class": %s, "basic_rules": %s, "enable_all_patch": %s}, "labels": {"run_mode": "%s", "rule_class": "%s", "basic_rules": "%s", "enable_all_patch": "%s"}, "note": "Read-only. Pass --run-mode/--rule-class/--basic-rules/--enable-all-patch with --yes to change."}\n' \
      "$FW_ID" "$status" "$configured" "$ips_source" \
      "$cur_run_mode" "$cur_rule_class" "$cur_basic_rules" "$cur_enable_all_patch" \
      "$(enum_label run_mode "$cur_run_mode")" "$(enum_label rule_class "$cur_rule_class")" \
      "$(enum_label basic_rules "$cur_basic_rules")" "$(enum_label enable_all_patch "$cur_enable_all_patch")"
    exit 0
  fi

  # --- SET mode: fill the omitted fields from the current values. ---
  if [[ "$configured" != "true" ]]; then
    refuse_not_configured "$FW_ID" "$status" "an IPS configuration change"
  fi
  warn_if_provisioning "$FW_ID" "$status"

  local tgt_run_mode="${RUN_MODE:-$cur_run_mode}"
  local tgt_basic_rules="${BASIC_RULES:-$cur_basic_rules}"
  local tgt_enable_all_patch="${ENABLE_ALL_PATCH:-$cur_enable_all_patch}"

  # --rule-class is OPTIONAL, and the service DERIVES it from the run mode. Five
  # live probes on 2026-10-21 established:
  #   run_mode 0 (observe) -> RuleClass is stored as 0 no matter what you send
  #   run_mode 1 (block)   -> omitting the flag preserves the current value, and a
  #                           0 carried over from observe mode is normalised to 3
  # So send it only when the user explicitly asked for it, and verify against the
  # value the service will actually store. Comparing against the number we sent
  # used to produce a spurious VerifyFailed on every switch to observe mode.
  local send_rule_class=false rule_class_derived=false
  local tgt_rule_class
  if [[ -n "$RULE_CLASS" ]]; then
    send_rule_class=true
    tgt_rule_class="$RULE_CLASS"
  else
    tgt_rule_class="$cur_rule_class"
  fi
  if [[ "$tgt_run_mode" == "0" ]]; then
    if [[ "$tgt_rule_class" != "0" ]]; then rule_class_derived=true; fi
    tgt_rule_class=0
  elif [[ "$tgt_rule_class" == "0" ]]; then
    rule_class_derived=true
    tgt_rule_class=3
  fi

  # Impact preview: current -> target, flagging every protection downgrade.
  local downgrades="" field cur tgt
  log_info "Impact preview for the IPS configuration of ${FW_ID}:"
  preview_line run_mode "$cur_run_mode" "$tgt_run_mode" "IPS defense mode"
  preview_line rule_class "$cur_rule_class" "$tgt_rule_class" "IPS rule group"
  preview_line basic_rules "$cur_basic_rules" "$tgt_basic_rules" "basic rules"
  preview_line enable_all_patch "$cur_enable_all_patch" "$tgt_enable_all_patch" "virtual patching"
  if [[ "$rule_class_derived" == "true" ]]; then
    if [[ "$tgt_run_mode" == "0" ]]; then
      log_warn "The IPS rule group does not apply in observe mode: the service stores RuleClass=0 whatever is sent, so ${tgt_rule_class} is expected, not the ${RULE_CLASS:-current} you see above. The rule group becomes meaningful again once you switch back to block mode."
    else
      log_warn "RuleClass=0 (left over from observe mode) is not valid in block mode: the service normalises it to 3 (strict), so ${tgt_rule_class} is what the read-back must show."
    fi
  fi

  for field in run_mode rule_class basic_rules enable_all_patch; do
    case "$field" in
      run_mode)         cur="$cur_run_mode";         tgt="$tgt_run_mode" ;;
      rule_class)       cur="$cur_rule_class";       tgt="$tgt_rule_class"
                        if [[ "$rule_class_derived" == "true" ]]; then continue; fi ;;
      basic_rules)      cur="$cur_basic_rules";      tgt="$tgt_basic_rules" ;;
      enable_all_patch) cur="$cur_enable_all_patch"; tgt="$tgt_enable_all_patch" ;;
    esac
    if [[ "$tgt" -lt "$cur" ]]; then
      downgrades="${downgrades:+${downgrades}, }${field} ${cur}($(enum_label "$field" "$cur")) -> ${tgt}($(enum_label "$field" "$tgt"))"
    fi
  done

  if [[ -n "$downgrades" ]]; then
    log_warn "PROTECTION DOWNGRADE detected: ${downgrades}."
    log_warn "  Lowering the IPS defense mode or rule group, or switching a capability off, reduces what attacks are detected or blocked on this VPC boundary. State this explicitly to the user and prefer an off-peak window."
  else
    log_info "No protection downgrade in this change."
  fi

  # --rule-class appears in the command only when the user asked for it; sending a
  # value the service is going to override anyway would just misrepresent the call.
  local rule_class_flag=""
  if [[ "$send_rule_class" == "true" ]]; then rule_class_flag=" --rule-class ${RULE_CLASS}"; fi
  local cmd_preview="aliyun Cloudfw modify-vpc-firewall-default-ips-config --vpc-firewall-id ${FW_ID} --run-mode ${tgt_run_mode}${rule_class_flag} --basic-rules ${tgt_basic_rules} --enable-all-patch ${tgt_enable_all_patch} --lang zh"
  if [[ -n "$MEMBER_UID" ]]; then cmd_preview="${cmd_preview} --member-uid ${MEMBER_UID}"; fi

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing the command preview, nothing is modified"
    printf '%s\n' "$cmd_preview"
    exit 0
  fi
  if [[ "$YES" != "true" ]]; then
    refuse_without_confirmation "Modifying the IPS configuration" "$cmd_preview"
  fi

  # kebab-case API name -> kebab-case flags (see the header note).
  local args=(
    --vpc-firewall-id "$FW_ID"
    --run-mode "$tgt_run_mode"
    --basic-rules "$tgt_basic_rules"
    --enable-all-patch "$tgt_enable_all_patch"
    --lang zh
  )
  if [[ "$send_rule_class" == "true" ]]; then args+=(--rule-class "$RULE_CLASS"); fi
  if [[ -n "$MEMBER_UID" ]]; then args+=(--member-uid "$MEMBER_UID"); fi

  local response exit_code=0
  response=$(call_cfw_api "modify-vpc-firewall-default-ips-config" ${args[@]+"${args[@]}"}) || exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    local code msg
    code=$(extract_api_error_code "$response"); msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$code" "$msg"
    output_error "${code:-UnknownError}" "${msg:-modify-vpc-firewall-default-ips-config failed}"
    exit 2
  fi

  # Read-back verification: the modify API returns only a RequestId, so the
  # change is proven only once a read reports the target values. The fallback
  # values handed to read_ips_effective are re-read from the API every attempt -
  # never the target - so a failed dedicated read cannot fake a pass.
  local attempt verified="false" live_raw="" live_fields=""
  local live_status live_strict live_subtype live_run_mode live_rule_class live_basic_rules live_enable_all_patch
  local want="${tgt_run_mode} ${tgt_rule_class} ${tgt_basic_rules} ${tgt_enable_all_patch}"
  for attempt in 1 2 3; do
    live_fields=""
    state=$(read_fw_state "$FW_ID" "$MEMBER_UID" 2>/dev/null) || state=""
    if [[ -n "$state" && "$state" != "NOTFOUND" ]]; then
      read -r live_status live_strict live_subtype live_run_mode live_rule_class live_basic_rules live_enable_all_patch <<<"$state"
      live_raw=$(read_ips_effective "$FW_ID" "$MEMBER_UID" "$live_run_mode" "$live_rule_class" "$live_basic_rules" "$live_enable_all_patch" 2>/dev/null) || live_raw=""
      live_fields="${live_raw#* }"
      if [[ "$live_raw" == "$live_fields" ]]; then live_fields=""; fi
    fi
    if [[ "$live_fields" == "$want" ]]; then
      verified="true"
      break
    fi
    if [[ "$attempt" -lt 3 ]]; then sleep 2; fi
  done

  local downgrade_json
  downgrade_json=$(downgrades_to_json "$downgrades")

  if [[ "$verified" == "true" ]]; then
    printf '{"success": true, "mode": "set", "vpc_firewall_id": "%s", "previous": {"run_mode": %s, "rule_class": %s, "basic_rules": %s, "enable_all_patch": %s}, "applied": {"run_mode": %s, "rule_class": %s, "basic_rules": %s, "enable_all_patch": %s}, "rule_class_derived_by_service": %s, "downgrades": %s, "verification": {"verified": true, "attempts": %d}}\n' \
      "$FW_ID" \
      "$cur_run_mode" "$cur_rule_class" "$cur_basic_rules" "$cur_enable_all_patch" \
      "$tgt_run_mode" "$tgt_rule_class" "$tgt_basic_rules" "$tgt_enable_all_patch" \
      "$rule_class_derived" "$downgrade_json" "$attempt"
    exit 0
  fi

  log_error "Verification failed: the live IPS config '${live_fields:-unreadable}' does not match the requested '${want}'."
  printf '{"success": false, "error_code": "VerifyFailed", "vpc_firewall_id": "%s", "verification": {"verified": false, "expected": "%s", "found": "%s"}}\n' \
    "$FW_ID" "$want" "${live_fields:-unreadable}"
  exit 2
}

# --- acl-engine -------------------------------------------------------------

cmd_acl_engine() {
  local FW_ID="" STRICT_MODE="" MEMBER_UID=""
  local DRY_RUN=false YES=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vpc-firewall-id) arg_value "--vpc-firewall-id" "${@:2}"; FW_ID="$2"; shift 2 ;;
      --strict-mode) arg_value "--strict-mode" "${@:2}"; STRICT_MODE="$2"; shift 2 ;;
      --member-uid) arg_value "--member-uid" "${@:2}"; MEMBER_UID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --yes|-y) YES=true; shift ;;
      --help|-h)
        show_help "vpc-fw-engine.sh acl-engine" \
          "Read or adjust the ACL engine mode (strict vs loose) of one VPC boundary firewall" \
          "vpc-fw-engine.sh acl-engine --vpc-firewall-id <vfw-xxxx> [--strict-mode 0|1] [--member-uid <uid>] [--yes] [--dry-run]" \
          "  --vpc-firewall-id <id>  Required. The VPC boundary firewall instance
  --strict-mode <0|1>       ACL engine mode: 1=strict, 0=loose
  --member-uid <uid>        Member account UID when operating from a management account
  --dry-run                 Print the ModifyVpcFirewallAclEngineMode command without executing it
  --yes                     Non-interactive confirmation for the write

  With no --strict-mode this subcommand is a read-only GET of the current mode.
  Strict mode enforces configured domain/application policies against unknown
  traffic; loose mode lets unknown traffic pass to protect availability.
  Requires a configured firewall; a 'notconfigured' one is refused."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "vpc-firewall-id" "$FW_ID" || exit 1
  validate_vpc_firewall_id "$FW_ID" || exit 1
  if [[ -n "$MEMBER_UID" ]]; then validate_member_uid "$MEMBER_UID" || exit 1; fi
  # Validated locally before the first API call (see cmd_ips).
  if [[ -n "$STRICT_MODE" ]]; then validate_bool_flag "strict-mode" "$STRICT_MODE" || exit 1; fi

  local state status cur_mode
  state=$(read_fw_state "$FW_ID" "$MEMBER_UID") || {
    local code msg
    code=$(extract_api_error_code "$state"); msg=$(extract_api_error_message "$state")
    diagnose_cfw_error "$code" "$msg"
    output_error "${code:-UnknownError}" "${msg:-DescribeVpcFirewallList failed}"
    exit 2
  }
  if [[ "$state" == "NOTFOUND" ]]; then
    diagnose_cfw_error "ErrorVpcFirewallNotFound" ""
    output_error "ErrorVpcFirewallNotFound" "No VPC boundary firewall with id ${FW_ID} is visible to this account."
    exit 2
  fi
  # Fields 3..7 (connect subtype and the list-level IPS block) are not used here.
  local unused_subtype unused_run_mode unused_rule_class unused_basic_rules unused_enable_all_patch
  read -r status cur_mode unused_subtype unused_run_mode unused_rule_class unused_basic_rules unused_enable_all_patch <<<"$state"

  local configured=true
  if [[ "$status" == "notconfigured" ]]; then configured=false; fi

  # --- GET mode. ---
  if [[ -z "$STRICT_MODE" ]]; then
    if [[ "$configured" != "true" ]]; then
      log_warn "VPC firewall ${FW_ID} is '${status}'. The mode below is the account default that WOULD apply once it is configured; there is no live engine instance to read."
    fi
    printf '{"success": true, "mode": "get", "vpc_firewall_id": "%s", "firewall_switch_status": "%s", "configured": %s, "strict_mode": %d, "label": "%s", "note": "Read-only. Pass --strict-mode with --yes to change."}\n' \
      "$FW_ID" "$status" "$configured" "$cur_mode" "$(enum_label strict_mode "$cur_mode")"
    exit 0
  fi

  if [[ "$configured" != "true" ]]; then
    refuse_not_configured "$FW_ID" "$status" "an ACL engine mode change"
  fi
  warn_if_provisioning "$FW_ID" "$status"

  log_info "Impact preview for the ACL engine mode of ${FW_ID}:"
  preview_line strict_mode "$cur_mode" "$STRICT_MODE" "ACL engine mode"

  local downgrade="false"
  if [[ "$cur_mode" == "1" && "$STRICT_MODE" == "0" ]]; then
    downgrade="true"
    log_warn "PROTECTION DOWNGRADE detected: strict_mode 1(strict) -> 0(loose)."
    log_warn "  In loose mode, traffic from unrecognized applications or domains is allowed without further policy matching, so deny policies aimed at unknown traffic stop applying. State this explicitly to the user before proceeding."
  elif [[ "$cur_mode" == "0" && "$STRICT_MODE" == "1" ]]; then
    log_warn "Strict mode enforces configured domain/application policies against unrecognized traffic; if a deny policy matches unknown traffic it will be blocked. Review the VPC boundary ACL policies first to avoid interrupting legitimate business."
  else
    log_info "No change in the ACL engine mode."
  fi

  local cmd_preview="aliyun Cloudfw ModifyVpcFirewallAclEngineMode --VpcFirewallId ${FW_ID} --StrictMode ${STRICT_MODE}"
  if [[ -n "$MEMBER_UID" ]]; then cmd_preview="${cmd_preview} --MemberUid ${MEMBER_UID}"; fi

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing the command preview, nothing is modified"
    printf '%s\n' "$cmd_preview"
    exit 0
  fi
  if [[ "$YES" != "true" ]]; then
    refuse_without_confirmation "Modifying the ACL engine mode" "$cmd_preview"
  fi

  # PascalCase API name -> PascalCase flags (see the header note).
  local args=(--VpcFirewallId "$FW_ID" --StrictMode "$STRICT_MODE")
  if [[ -n "$MEMBER_UID" ]]; then args+=(--MemberUid "$MEMBER_UID"); fi

  local response exit_code=0
  response=$(call_cfw_api "ModifyVpcFirewallAclEngineMode" ${args[@]+"${args[@]}"}) || exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    local code msg
    code=$(extract_api_error_code "$response"); msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$code" "$msg"
    output_error "${code:-UnknownError}" "${msg:-ModifyVpcFirewallAclEngineMode failed}"
    exit 2
  fi

  local attempt verified="false" live_mode="" live_state=""
  # Only field 2 (the strict mode) is consumed; the rest are positional filler.
  local live_status live_subtype live_run_mode live_rule_class live_basic_rules live_enable_all_patch
  for attempt in 1 2 3; do
    live_mode=""
    live_state=$(read_fw_state "$FW_ID" "$MEMBER_UID" 2>/dev/null) || live_state=""
    if [[ -n "$live_state" && "$live_state" != "NOTFOUND" ]]; then
      read -r live_status live_mode live_subtype live_run_mode live_rule_class live_basic_rules live_enable_all_patch <<<"$live_state"
    fi
    if [[ "$live_mode" == "$STRICT_MODE" ]]; then
      verified="true"
      break
    fi
    if [[ "$attempt" -lt 3 ]]; then sleep 2; fi
  done

  if [[ "$verified" == "true" ]]; then
    printf '{"success": true, "mode": "set", "vpc_firewall_id": "%s", "previous": %d, "applied": %d, "downgrade": %s, "verification": {"verified": true, "attempts": %d}}\n' \
      "$FW_ID" "$cur_mode" "$STRICT_MODE" "$downgrade" "$attempt"
    exit 0
  fi

  log_error "Verification failed: the live ACL engine mode '${live_mode:-unreadable}' does not match the requested '${STRICT_MODE}'."
  printf '{"success": false, "error_code": "VerifyFailed", "vpc_firewall_id": "%s", "verification": {"verified": false, "expected": %d, "found": "%s"}}\n' \
    "$FW_ID" "$STRICT_MODE" "${live_mode:-unreadable}"
  exit 2
}

# --- Main Router ---

SUBCOMMAND="${1:-}"
[[ $# -gt 0 ]] && shift

case "$SUBCOMMAND" in
  ips) cmd_ips "$@" ;;
  acl-engine) cmd_acl_engine "$@" ;;
  ""|--help|-h|help)
    show_help "vpc-fw-engine.sh" \
      "Read / adjust the IPS defense config and the ACL engine mode of a VPC boundary firewall" \
      "vpc-fw-engine.sh <ips|acl-engine> [options]" \
      "  ips         Read or adjust the IPS defense mode / rule group / capabilities
  acl-engine  Read or adjust the ACL engine mode (strict vs loose)

Both subcommands are read-only GETs unless a write option is given. A write
needs --yes after an explicit user confirmation; --dry-run previews the exact
aliyun CLI command without executing it. Both writes require a configured VPC
firewall - a 'notconfigured' one has no engine instance and is refused."
    ;;
  *)
    log_error "Unknown subcommand: ${SUBCOMMAND}"
    log_error "Available subcommands: ips, acl-engine"
    exit 1
    ;;
esac
