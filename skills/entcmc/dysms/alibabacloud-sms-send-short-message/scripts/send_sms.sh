#!/bin/bash
#
# Alibaba Cloud SMS Service CLI helper.
# Wraps the aliyun CLI to send SMS and query related resources.
#
# Requirements: aliyun-cli >= 3.3.3 + dysmsapi plugin
# Install:      brew install aliyun-cli  (macOS)
# Plugin:       aliyun plugin install --names dysmsapi
#

set -e

# Default configuration
DEFAULT_REGION="cn-hangzhou"
API_VERSION="2017-05-25"
USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message"
READ_TIMEOUT="3"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ========== Input validators ==========

# Validate phone numbers (only digits, commas and plus signs allowed)
validate_phone_numbers() {
    local phone="$1"
    if [[ ! "$phone" =~ ^[0-9,+]+$ ]]; then
        echo -e "${RED}Error: invalid phone number format. Only digits, commas and '+' are allowed.${NC}"
        exit 1
    fi
}

# Validate signature name (forbid shell metacharacters)
validate_sign_name() {
    local sign="$1"
    # Forbid shell metacharacters: $ ` \ " ' ; & | > < ( ) { } [ ] ! # * ?
    if [[ "$sign" =~ [\$\`\\\"\'\'\;\&\|\>\<\(\)\{\}\[\]\!\#\*\?] ]]; then
        echo -e "${RED}Error: signature name contains illegal characters.${NC}"
        exit 1
    fi
}

# Validate template code (only letters, digits and underscore)
validate_template_code() {
    local code="$1"
    if [[ ! "$code" =~ ^[A-Za-z0-9_]+$ ]]; then
        echo -e "${RED}Error: invalid template code. Only letters, digits and underscore are allowed.${NC}"
        exit 1
    fi
}

# Validate date format (digits only, yyyyMMdd)
validate_date() {
    local date="$1"
    if [[ ! "$date" =~ ^[0-9]{8}$ ]]; then
        echo -e "${RED}Error: invalid date format. Expected yyyyMMdd.${NC}"
        exit 1
    fi
}

# Validate JSON parameter (basic check; forbid dangerous characters)
validate_json_param() {
    local json="$1"
    # Forbid shell metacharacters except those required by JSON: " : , { } [ ]
    if [[ "$json" =~ [\$\`\\\;\&\|\>\<\(\)\!\#\*\?] ]]; then
        echo -e "${RED}Error: JSON parameter contains illegal characters.${NC}"
        exit 1
    fi
}

# Validate a generic safe string (forbid dangerous characters)
validate_safe_string() {
    local str="$1"
    local name="$2"
    if [[ "$str" =~ [\$\`\\\"\'\'\;\&\|\>\<\(\)\{\}\[\]\!\#\*\?] ]]; then
        echo -e "${RED}Error: ${name} contains illegal characters.${NC}"
        exit 1
    fi
}

# Help message
show_help() {
    cat << EOF
Alibaba Cloud SMS Service CLI helper

Usage:
  $0 <command> [options]

Commands:
  send              Send an SMS message
  list-signs        List SMS signatures
  list-templates    List SMS templates
  query-sign        Query a specific signature status
  query-template    Query a specific template status
  query-status      Query the send status of an SMS
  query-statistics  Query send statistics by date range

Send options:
  -p, --phone-numbers     Phone numbers (required), comma-separated for multiple
  -s, --sign-name         Signature name (required)
  -t, --template-code     Template code (required)
  -tp, --template-param   Template variables (JSON)
  -o, --out-id            External tracking ID
  --verify                Verify signature & template status before sending

Query options:
  --sign-name             Signature name (required for query-sign)
  --template-code         Template code (required for query-template)
  --send-date             Send date in yyyyMMdd (required for query-status)
  --biz-id                BizId returned by send

Statistics options (query-statistics):
  --start-date            Start date in yyyyMMdd (required)
  --end-date              End date in yyyyMMdd (required)
  --is-globe              Scope: 1 = domestic, 2 = international/HK-Macao-Taiwan (default 1)
  --template-type         Template type: 0=verification, 1=notification, 2=marketing,
                          3=international, 7=digital
  --page-index            Page index, default 1
  --page-size             Page size, default 10 (1-50)

Common options:
  -r, --region            Region ID, default cn-hangzhou
  --profile               Use the given aliyun CLI profile
  -h, --help              Show this help

Examples:
  # Send an SMS
  $0 send -p "13800138000" -s "AliyunDemo" -t "SMS_123456" -tp '{"code":"123456"}'

  # Verify signature/template first
  $0 send -p "13800138000" -s "AliyunDemo" -t "SMS_123456" -tp '{"code":"123456"}' --verify

  # List signatures
  $0 list-signs

  # List templates
  $0 list-templates

  # Query a signature status
  $0 query-sign --sign-name "AliyunDemo"

  # Query a template status
  $0 query-template --template-code "SMS_123456"

  # Query send status
  $0 query-status -p "13800138000" --send-date "20260326"

  # Query send statistics
  $0 query-statistics --start-date "20260301" --end-date "20260326"

EOF
}

# Check whether the aliyun CLI is installed
check_cli() {
    if ! command -v aliyun &> /dev/null; then
        echo -e "${RED}Error: aliyun CLI is not installed.${NC}"
        echo "Please install aliyun CLI first:"
        echo "  macOS: brew install aliyun-cli"
        echo "  Linux: see https://help.aliyun.com/zh/cli/"
        exit 1
    fi
}

# Check whether the dysmsapi plugin is installed
check_plugin() {
    if ! aliyun dysmsapi --help &> /dev/null; then
        echo -e "${YELLOW}Installing the dysmsapi plugin...${NC}"
        aliyun plugin install --names dysmsapi
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: failed to install the dysmsapi plugin.${NC}"
            echo "Install it manually with: aliyun plugin install --names dysmsapi"
            exit 1
        fi
        echo -e "${GREEN}dysmsapi plugin installed successfully.${NC}"
    fi
}

# Check the CLI configuration
check_config() {
    # Verify that credentials are configured (environment variable or config file)
    if [ -z "$ALIBABA_CLOUD_ACCESS_KEY_ID" ] && ! aliyun configure get 2>/dev/null | grep -q "access_key_id"; then
        echo -e "${YELLOW}Warning: aliyun CLI has no credentials configured.${NC}"
        echo "Configure credentials in one of the following ways:"
        echo "  1. Environment variables: export ALIBABA_CLOUD_ACCESS_KEY_ID=xxx && export ALIBABA_CLOUD_ACCESS_KEY_SECRET=xxx"
        echo "  2. ECS instance RAM role (auto-detected on cloud workloads)"
        echo "  3. OIDC token (container workloads)"
        exit 1
    fi
}

# Send an SMS
send_sms() {
    local phone_numbers=""
    local sign_name=""
    local template_code=""
    local template_param=""
    local out_id=""
    local verify=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--phone-numbers)
                phone_numbers="$2"
                shift 2
                ;;
            -s|--sign-name)
                sign_name="$2"
                shift 2
                ;;
            -t|--template-code)
                template_code="$2"
                shift 2
                ;;
            -tp|--template-param)
                template_param="$2"
                shift 2
                ;;
            -o|--out-id)
                out_id="$2"
                shift 2
                ;;
            --verify)
                verify=true
                shift
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    # Validate required parameters
    if [ -z "$phone_numbers" ]; then
        echo -e "${RED}Error: missing phone numbers (-p/--phone-numbers).${NC}"
        exit 1
    fi
    if [ -z "$sign_name" ]; then
        echo -e "${RED}Error: missing signature name (-s/--sign-name).${NC}"
        exit 1
    fi
    if [ -z "$template_code" ]; then
        echo -e "${RED}Error: missing template code (-t/--template-code).${NC}"
        exit 1
    fi

    # Input validation (defends against command injection)
    validate_phone_numbers "$phone_numbers"
    validate_sign_name "$sign_name"
    validate_template_code "$template_code"
    [ -n "$template_param" ] && validate_json_param "$template_param"
    [ -n "$out_id" ] && validate_safe_string "$out_id" "out-id"

    # Pre-send verification
    if [ "$verify" = true ]; then
        echo -e "${YELLOW}Verifying signature status...${NC}"
        local sign_result
        sign_result=$(aliyun dysmsapi get-sms-sign \
            --api-version "$API_VERSION" \
            --user-agent "$USER_AGENT" \
            --read-timeout "$READ_TIMEOUT" \
            ${REGION:+--region "$REGION"} \
            ${PROFILE:+--profile "$PROFILE"} \
            --sign-name "$sign_name" 2>&1)
        local sign_status
        sign_status=$(echo "$sign_result" | grep -o '"SignStatus":[0-9]*' | grep -o '[0-9]*')

        if [ "$sign_status" != "1" ]; then
            echo -e "${RED}Signature verification failed: not approved (status: $sign_status).${NC}"
            echo "$sign_result"
            exit 1
        fi
        echo -e "${GREEN}Signature verified.${NC}"

        echo -e "${YELLOW}Verifying template status...${NC}"
        local template_result
        template_result=$(aliyun dysmsapi get-sms-template \
            --api-version "$API_VERSION" \
            --user-agent "$USER_AGENT" \
            --read-timeout "$READ_TIMEOUT" \
            ${REGION:+--region "$REGION"} \
            ${PROFILE:+--profile "$PROFILE"} \
            --template-code "$template_code" 2>&1)
        local template_status
        template_status=$(echo "$template_result" | grep -o '"TemplateStatus":[0-9]*' | grep -o '[0-9]*')

        if [ "$template_status" != "1" ]; then
            echo -e "${RED}Template verification failed: not approved (status: $template_status).${NC}"
            echo "$template_result"
            exit 1
        fi
        echo -e "${GREEN}Template verified.${NC}"
    fi

    # Build the command via an array (avoid eval)
    local cmd_args=(
        "aliyun" "dysmsapi" "send-sms"
        "--api-version" "$API_VERSION"
        "--user-agent" "$USER_AGENT"
        "--read-timeout" "$READ_TIMEOUT"
        "--phone-numbers" "$phone_numbers"
        "--sign-name" "$sign_name"
        "--template-code" "$template_code"
    )

    [ -n "$template_param" ] && cmd_args+=("--template-param" "$template_param")
    [ -n "$out_id" ] && cmd_args+=("--out-id" "$out_id")
    [ -n "$REGION" ] && cmd_args+=("--region" "$REGION")
    [ -n "$PROFILE" ] && cmd_args+=("--profile" "$PROFILE")

    echo -e "${YELLOW}Sending SMS...${NC}"
    "${cmd_args[@]}"
}

# List signatures
list_signs() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    echo -e "${YELLOW}Querying signature list...${NC}"
    aliyun dysmsapi query-sms-sign-list \
        --api-version "$API_VERSION" \
        --user-agent "$USER_AGENT" \
        --read-timeout "$READ_TIMEOUT" \
        ${REGION:+--region "$REGION"} \
        ${PROFILE:+--profile "$PROFILE"} \
        --page-index 1 \
        --page-size 50
}

# List templates
list_templates() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    echo -e "${YELLOW}Querying template list...${NC}"
    aliyun dysmsapi query-sms-template-list \
        --api-version "$API_VERSION" \
        --user-agent "$USER_AGENT" \
        --read-timeout "$READ_TIMEOUT" \
        ${REGION:+--region "$REGION"} \
        ${PROFILE:+--profile "$PROFILE"} \
        --page-index 1 \
        --page-size 50
}

# Query a specific signature status
query_sign() {
    local sign_name=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --sign-name|-s)
                sign_name="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    if [ -z "$sign_name" ]; then
        echo -e "${RED}Error: missing signature name (--sign-name).${NC}"
        exit 1
    fi

    # Input validation
    validate_sign_name "$sign_name"

    echo -e "${YELLOW}Querying signature status...${NC}"
    aliyun dysmsapi get-sms-sign \
        --api-version "$API_VERSION" \
        --user-agent "$USER_AGENT" \
        --read-timeout "$READ_TIMEOUT" \
        ${REGION:+--region "$REGION"} \
        ${PROFILE:+--profile "$PROFILE"} \
        --sign-name "$sign_name"
}

# Query a specific template status
query_template() {
    local template_code=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --template-code|-t)
                template_code="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    if [ -z "$template_code" ]; then
        echo -e "${RED}Error: missing template code (--template-code).${NC}"
        exit 1
    fi

    # Input validation
    validate_template_code "$template_code"

    echo -e "${YELLOW}Querying template status...${NC}"
    aliyun dysmsapi get-sms-template \
        --api-version "$API_VERSION" \
        --user-agent "$USER_AGENT" \
        --read-timeout "$READ_TIMEOUT" \
        ${REGION:+--region "$REGION"} \
        ${PROFILE:+--profile "$PROFILE"} \
        --template-code "$template_code"
}

# Query the send status
query_status() {
    local phone_number=""
    local send_date=""
    local biz_id=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--phone-numbers)
                phone_number="$2"
                shift 2
                ;;
            --send-date)
                send_date="$2"
                shift 2
                ;;
            --biz-id)
                biz_id="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    if [ -z "$phone_number" ]; then
        echo -e "${RED}Error: missing phone number (-p/--phone-numbers).${NC}"
        exit 1
    fi
    if [ -z "$send_date" ]; then
        # Default to today
        send_date=$(date +%Y%m%d)
        echo -e "${YELLOW}--send-date not provided, defaulting to today: $send_date${NC}"
    fi

    # Input validation
    validate_phone_numbers "$phone_number"
    validate_date "$send_date"
    [ -n "$biz_id" ] && validate_safe_string "$biz_id" "BizId"

    # Build the command via an array (avoid eval)
    local cmd_args=(
        "aliyun" "dysmsapi" "query-send-details"
        "--api-version" "$API_VERSION"
        "--user-agent" "$USER_AGENT"
        "--read-timeout" "$READ_TIMEOUT"
        "--phone-number" "$phone_number"
        "--send-date" "$send_date"
        "--page-size" "10"
        "--current-page" "1"
    )

    [ -n "$biz_id" ] && cmd_args+=("--biz-id" "$biz_id")
    [ -n "$REGION" ] && cmd_args+=("--region" "$REGION")
    [ -n "$PROFILE" ] && cmd_args+=("--profile" "$PROFILE")

    echo -e "${YELLOW}Querying send status...${NC}"
    "${cmd_args[@]}"
}

# Query send statistics
query_statistics() {
    local start_date=""
    local end_date=""
    local is_globe="1"
    local template_type=""
    local sign_name=""
    local page_index="1"
    local page_size="10"

    while [[ $# -gt 0 ]]; do
        case $1 in
            --start-date)
                start_date="$2"
                shift 2
                ;;
            --end-date)
                end_date="$2"
                shift 2
                ;;
            --is-globe)
                is_globe="$2"
                shift 2
                ;;
            --template-type)
                template_type="$2"
                shift 2
                ;;
            --sign-name|-s)
                sign_name="$2"
                shift 2
                ;;
            --page-index)
                page_index="$2"
                shift 2
                ;;
            --page-size)
                page_size="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    if [ -z "$start_date" ]; then
        echo -e "${RED}Error: missing start date (--start-date).${NC}"
        exit 1
    fi
    if [ -z "$end_date" ]; then
        echo -e "${RED}Error: missing end date (--end-date).${NC}"
        exit 1
    fi

    # Input validation
    validate_date "$start_date"
    validate_date "$end_date"
    if [[ ! "$is_globe" =~ ^[12]$ ]]; then
        echo -e "${RED}Error: --is-globe must be 1 (domestic) or 2 (international/HK-Macao-Taiwan).${NC}"
        exit 1
    fi
    if [ -n "$template_type" ] && [[ ! "$template_type" =~ ^[01237]$ ]]; then
        echo -e "${RED}Error: --template-type must be one of 0/1/2/3/7.${NC}"
        exit 1
    fi
    if [[ ! "$page_index" =~ ^[0-9]+$ ]] || [[ ! "$page_size" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Error: --page-index / --page-size must be numbers.${NC}"
        exit 1
    fi
    [ -n "$sign_name" ] && validate_sign_name "$sign_name"

    # Build the command via an array (avoid eval)
    local cmd_args=(
        "aliyun" "dysmsapi" "query-send-statistics"
        "--api-version" "$API_VERSION"
        "--user-agent" "$USER_AGENT"
        "--read-timeout" "$READ_TIMEOUT"
        "--is-globe" "$is_globe"
        "--start-date" "$start_date"
        "--end-date" "$end_date"
        "--page-index" "$page_index"
        "--page-size" "$page_size"
    )

    [ -n "$template_type" ] && cmd_args+=("--template-type" "$template_type")
    [ -n "$sign_name" ] && cmd_args+=("--sign-name" "$sign_name")
    [ -n "$REGION" ] && cmd_args+=("--region" "$REGION")
    [ -n "$PROFILE" ] && cmd_args+=("--profile" "$PROFILE")

    echo -e "${YELLOW}Querying send statistics...${NC}"
    "${cmd_args[@]}"
}

# Main entry
main() {
    # Dependency checks
    check_cli
    check_plugin
    check_config

    # Initialize variables
    REGION="${DEFAULT_REGION}"
    PROFILE=""

    # Parse the command
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    local command=$1
    shift

    case $command in
        send)
            send_sms "$@"
            ;;
        list-signs)
            list_signs "$@"
            ;;
        list-templates)
            list_templates "$@"
            ;;
        query-sign)
            query_sign "$@"
            ;;
        query-template)
            query_template "$@"
            ;;
        query-status)
            query_status "$@"
            ;;
        query-statistics)
            query_statistics "$@"
            ;;
        -h|--help|help)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown command: $command${NC}"
            echo "Run '$0 --help' for usage information."
            exit 1
            ;;
    esac
}

main "$@"
