#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  httpdns-openapi.sh <command> [options]

Commands:
  account-info [--raw]
  add-domain --domain <domain> [--account-id <id>] --yes
  delete-domain --domain <domain> [--account-id <id>] --yes
  describe-domains [--account-id <id>] [--page-number <n>] [--page-size <n>]
  list-domains [--page-number <n>] [--page-size <n>] [--search <text>] [--without-metering-data <true|false>]
  resolve-statistics --domain <domain> --granularity <value> --time-span <n> [--protocol-name <name>]
  resolve-count-summary --granularity <value> --time-span <n>
  refresh-cache --domains <domain> [domain...] --yes

Global:
  --profile <name>
  --yes, --confirm-mutation    Confirm a mutating add/delete/refresh command.

Examples:
  scripts/httpdns-openapi.sh account-info
  scripts/httpdns-openapi.sh add-domain --domain www.example.com --yes
  scripts/httpdns-openapi.sh resolve-statistics --domain www.example.com --granularity day --time-span 7
USAGE
}

require_value() {
  local name="$1"
  local value="${2:-}"
  if [[ -z "$value" ]]; then
    echo "missing required option: $name" >&2
    exit 2
  fi
}

fail_validation() {
  echo "$1" >&2
  exit 2
}

cmd="${1:-}"
if [[ -z "$cmd" || "$cmd" == "-h" || "$cmd" == "--help" ]]; then
  usage
  exit 0
fi
shift

args=()
profile_name=""
domain=""
account_id=""
page_number=""
page_size=""
search=""
without_metering_data=""
granularity=""
time_span=""
protocol_name=""
domains=()
raw_output=false
confirm_mutation=false

append_domains_value() {
  local value="$1"
  if [[ "$value" == \[*\] ]]; then
    local stripped="${value#[}"
    stripped="${stripped%]}"
    stripped="${stripped//\"/}"
    stripped="${stripped//\'/}"
    local parsed=()
    local part
    IFS=',' read -r -a parsed <<< "$stripped"
    for part in "${parsed[@]}"; do
      part="$(printf '%s' "$part" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
      if [[ -n "$part" ]]; then
        domains+=("$part")
      fi
    done
  else
    domains+=("$value")
  fi
}

validate_domain_value() {
  local name="$1"
  local value="$2"
  if [[ ${#value} -gt 253 ]]; then
    fail_validation "$name is too long: $value"
  fi
  if [[ ! "$value" =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$ ]]; then
    fail_validation "$name must be a DNS domain name: $value"
  fi
}

validate_integer_range() {
  local name="$1"
  local value="$2"
  local min="$3"
  local max="$4"
  if [[ -z "$value" ]]; then
    return
  fi
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    fail_validation "$name must be an integer: $value"
  fi
  local numeric=$((10#$value))
  if (( numeric < min || numeric > max )); then
    fail_validation "$name must be between $min and $max: $value"
  fi
}

validate_optional_pattern() {
  local name="$1"
  local value="$2"
  local pattern="$3"
  local message="$4"
  if [[ -n "$value" && ! "$value" =~ $pattern ]]; then
    fail_validation "$name $message: $value"
  fi
}

validate_inputs() {
  if [[ -n "$domain" ]]; then
    validate_domain_value "--domain" "$domain"
  fi
  local item
  for item in "${domains[@]}"; do
    validate_domain_value "--domains" "$item"
  done
  validate_optional_pattern "--account-id" "$account_id" '^[0-9]{1,20}$' "must contain 1 to 20 digits"
  validate_optional_pattern "--profile" "$profile_name" '^[A-Za-z0-9_.@:/-]{1,128}$' "contains unsupported characters"
  validate_optional_pattern "--search" "$search" '^[A-Za-z0-9._*-]{1,128}$' "contains unsupported characters"
  validate_optional_pattern "--granularity" "$granularity" '^(hour|day)$' "must be hour or day"
  validate_optional_pattern "--protocol-name" "$protocol_name" '^(http|https|http6|https6|doh)$' "must be one of http, https, http6, https6, or doh"
  validate_optional_pattern "--without-metering-data" "$without_metering_data" '^(true|false)$' "must be true or false"
  validate_integer_range "--page-number" "$page_number" 1 100000
  validate_integer_range "--page-size" "$page_size" 1 1000
  validate_integer_range "--time-span" "$time_span" 1 366
}

require_mutation_confirmation() {
  local action="$1"
  local target="$2"
  if [[ "$confirm_mutation" == true || "${HTTPDNS_CONFIRM_MUTATION:-}" =~ ^(1|true|yes)$ ]]; then
    return
  fi
  fail_validation "refusing to run mutating command '$action' for '$target' without explicit confirmation; pass --yes after confirming the exact target"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      require_value "$1" "${2:-}"
      profile_name="$2"
      shift 2
      ;;
    --domain)
      require_value "$1" "${2:-}"
      domain="$2"
      shift 2
      ;;
    --account-id)
      require_value "$1" "${2:-}"
      account_id="$2"
      shift 2
      ;;
    --page-number)
      require_value "$1" "${2:-}"
      page_number="$2"
      shift 2
      ;;
    --page-size)
      require_value "$1" "${2:-}"
      page_size="$2"
      shift 2
      ;;
    --search)
      require_value "$1" "${2:-}"
      search="$2"
      shift 2
      ;;
    --without-metering-data)
      require_value "$1" "${2:-}"
      without_metering_data="$2"
      shift 2
      ;;
    --granularity)
      require_value "$1" "${2:-}"
      granularity="$2"
      shift 2
      ;;
    --time-span)
      require_value "$1" "${2:-}"
      time_span="$2"
      shift 2
      ;;
    --protocol-name)
      require_value "$1" "${2:-}"
      protocol_name="$2"
      shift 2
      ;;
    --domains)
      shift
      if [[ $# -eq 0 || "$1" == --* ]]; then
        echo "missing required option: --domains" >&2
        exit 2
      fi
      while [[ $# -gt 0 && "$1" != --* ]]; do
        append_domains_value "$1"
        shift
      done
      ;;
    --raw)
      raw_output=true
      shift
      ;;
    --yes|--confirm-mutation)
      confirm_mutation=true
      shift
      ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

validate_inputs

append_if_set() {
  local key="$1"
  local value="$2"
  if [[ -n "$value" ]]; then
    args+=("$key" "$value")
  fi
}

run_httpdns() {
  local api_name="$1"
  shift
  local command=(aliyun httpdns "$api_name")
  while [[ $# -gt 0 ]]; do
    command+=("$1")
    shift
  done
  if [[ -n "$profile_name" ]]; then
    command+=(--profile "$profile_name")
  fi
  exec "${command[@]}"
}

mask_sensitive_output() {
  sed -E \
    -e 's/(AccessKeyId=)[^&[:space:]"]+/\1***/g' \
    -e 's/(Signature=)[^&[:space:]"]+/\1***/g' \
    -e 's/(SignatureNonce=)[^&[:space:]"]+/\1***/g' \
    -e 's/("[^"]*(Secret|Key|Token|Password|Pwd)[^"]*"[[:space:]]*:[[:space:]]*")[^"]*(")/\1***\3/gI'
}

run_httpdns_masked() {
  local api_name="$1"
  shift
  local command=(aliyun httpdns "$api_name")
  while [[ $# -gt 0 ]]; do
    command+=("$1")
    shift
  done
  if [[ -n "$profile_name" ]]; then
    command+=(--profile "$profile_name")
  fi

  set +e
  local output
  output="$("${command[@]}" 2>&1)"
  local status=$?
  set -e
  printf '%s\n' "$output" | mask_sensitive_output
  exit "$status"
}

case "$cmd" in
  account-info)
    if [[ "$raw_output" == true ]]; then
      run_httpdns get-account-info
    fi
    run_httpdns_masked get-account-info
    ;;
  add-domain)
    require_value "--domain" "$domain"
    require_mutation_confirmation "add-domain" "$domain"
    args=(--domain-name "$domain")
    append_if_set --account-id "$account_id"
    run_httpdns add-domain "${args[@]+"${args[@]}"}"
    ;;
  delete-domain)
    require_value "--domain" "$domain"
    require_mutation_confirmation "delete-domain" "$domain"
    args=(--domain-name "$domain")
    append_if_set --account-id "$account_id"
    run_httpdns delete-domain "${args[@]+"${args[@]}"}"
    ;;
  describe-domains)
    append_if_set --account-id "$account_id"
    append_if_set --page-number "$page_number"
    append_if_set --page-size "$page_size"
    run_httpdns describe-domains "${args[@]+"${args[@]}"}"
    ;;
  list-domains)
    append_if_set --page-number "$page_number"
    append_if_set --page-size "$page_size"
    append_if_set --search "$search"
    append_if_set --without-metering-data "$without_metering_data"
    run_httpdns list-domains "${args[@]+"${args[@]}"}"
    ;;
  resolve-statistics)
    require_value "--domain" "$domain"
    require_value "--granularity" "$granularity"
    require_value "--time-span" "$time_span"
    args=(--domain-name "$domain" --granularity "$granularity" --time-span "$time_span")
    append_if_set --protocol-name "$protocol_name"
    run_httpdns get-resolve-statistics "${args[@]+"${args[@]}"}"
    ;;
  resolve-count-summary)
    require_value "--granularity" "$granularity"
    require_value "--time-span" "$time_span"
    args=(--granularity "$granularity" --time-span "$time_span")
    run_httpdns get-resolve-count-summary "${args[@]+"${args[@]}"}"
    ;;
  refresh-cache)
    if [[ ${#domains[@]} -eq 0 ]]; then
      echo "missing required option: --domains" >&2
      exit 2
    fi
    require_mutation_confirmation "refresh-cache" "${domains[*]}"
    run_httpdns refresh-resolve-cache --domains "${domains[@]}"
    ;;
  *)
    echo "unknown command: $cmd" >&2
    usage >&2
    exit 2
    ;;
esac
