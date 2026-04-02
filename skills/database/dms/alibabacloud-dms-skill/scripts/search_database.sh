#!/bin/bash
# Search DMS databases by keyword using aliyun-cli.
#
# Prerequisites:
#   - aliyun-cli installed (brew install aliyun-cli)
#   - aliyun configure set --mode AK --access-key-id <AK> --access-key-secret <SK> --region cn-hangzhou
#   - jq installed for JSON parsing (brew install jq)
#
# Usage:
#   ./search_database.sh <keyword>
#   ./search_database.sh testdb
#   ./search_database.sh testdb --json

set -e

# Default region
REGION="${REGION:-cn-hangzhou}"

# Parse arguments
KEYWORD=""
OUTPUT_JSON=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)
            OUTPUT_JSON=true
            shift
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 <keyword> [--json] [--region <region>]"
            echo ""
            echo "Arguments:"
            echo "  keyword       Search keyword for database name"
            echo "  --json        Output results in JSON format"
            echo "  --region      Aliyun region (default: cn-hangzhou)"
            echo ""
            echo "Examples:"
            echo "  $0 mydb"
            echo "  $0 mydb --json"
            echo "  $0 mydb --region cn-shanghai"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            KEYWORD="$1"
            shift
            ;;
    esac
done

if [[ -z "$KEYWORD" ]]; then
    echo "Error: keyword is required" >&2
    echo "Usage: $0 <keyword> [--json] [--region <region>]" >&2
    exit 1
fi

# Validate KEYWORD: length 1-128 characters, alphanumeric and common symbols only
if [[ ${#KEYWORD} -gt 128 ]]; then
    echo "Error: keyword 长度不能超过 128 个字符" >&2
    exit 1
fi
if ! echo "$KEYWORD" | grep -qE '^[a-zA-Z0-9_\-\.]+$'; then
    echo "Error: keyword 只能包含字母、数字、下划线、连字符和点号" >&2
    exit 1
fi

# Validate REGION: must match Alibaba Cloud region format
if ! echo "$REGION" | grep -qE '^[a-z]{2,3}-[a-z]+-?[0-9]*$'; then
    echo "Error: region 格式不正确，应为阿里云 Region ID 格式 (如 cn-hangzhou, cn-shanghai, us-west-1)" >&2
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required for JSON parsing. Install with: brew install jq" >&2
    exit 1
fi

# Check if aliyun cli is installed
if ! command -v aliyun &> /dev/null; then
    echo "Error: aliyun-cli is not installed. Install with: brew install aliyun-cli" >&2
    exit 1
fi

# User-Agent for tracking
USER_AGENT="AlibabaCloud-Agent-Skills"

# Timeout settings (in seconds)
READ_TIMEOUT=10
CONNECT_TIMEOUT=10

# Step 1: Get Tenant ID (Tid)
echo "Fetching Tenant ID..." >&2
TID_RESPONSE=$(aliyun dms-enterprise GetUserActiveTenant \
    --region "$REGION" \
    --user-agent "$USER_AGENT" \
    --read-timeout "$READ_TIMEOUT" \
    --connect-timeout "$CONNECT_TIMEOUT" 2>&1)

# Check if the request was successful
if ! echo "$TID_RESPONSE" | jq -e '.Success' > /dev/null 2>&1; then
    echo "Error: Failed to get Tenant ID" >&2
    echo "$TID_RESPONSE" >&2
    exit 1
fi

SUCCESS=$(echo "$TID_RESPONSE" | jq -r '.Success')
if [[ "$SUCCESS" != "true" ]]; then
    ERROR_MSG=$(echo "$TID_RESPONSE" | jq -r '.ErrorMessage // "Unknown error"')
    echo "Error: $ERROR_MSG" >&2
    exit 1
fi

TID=$(echo "$TID_RESPONSE" | jq -r '.Tenant.Tid')
if [[ -z "$TID" || "$TID" == "null" ]]; then
    echo "Error: Failed to extract Tid from response" >&2
    exit 1
fi

echo "Tenant ID: $TID" >&2

# Step 2: Search Database
echo "Searching databases with keyword: $KEYWORD" >&2
SEARCH_RESPONSE=$(aliyun dms-enterprise SearchDatabase \
    --Tid "$TID" \
    --SearchKey "$KEYWORD" \
    --region "$REGION" \
    --user-agent "$USER_AGENT" \
    --read-timeout "$READ_TIMEOUT" \
    --connect-timeout "$CONNECT_TIMEOUT" 2>&1)

# Check if the request was successful
SUCCESS=$(echo "$SEARCH_RESPONSE" | jq -r '.Success')
if [[ "$SUCCESS" != "true" ]]; then
    ERROR_MSG=$(echo "$SEARCH_RESPONSE" | jq -r '.ErrorMessage // "Unknown error"')
    echo "Error: $ERROR_MSG" >&2
    exit 1
fi

# Extract database list
DATABASES=$(echo "$SEARCH_RESPONSE" | jq '.SearchDatabaseList.SearchDatabase // []')

if [[ "$OUTPUT_JSON" == "true" ]]; then
    # Output JSON format
    echo "$DATABASES" | jq '.'
else
    # Output table format
    DB_COUNT=$(echo "$DATABASES" | jq 'length')
    
    if [[ "$DB_COUNT" -eq 0 ]]; then
        echo "未找到匹配的数据库"
    else
        echo ""
        echo "共找到 $DB_COUNT 个匹配:"
        echo ""
        printf "%-15s %-25s %-12s %-30s\n" "DATABASE_ID" "SCHEMA_NAME" "DB_TYPE" "HOST:PORT"
        printf "%s\n" "-------------------------------------------------------------------------------------"
        
        echo "$DATABASES" | jq -r '.[] | "\(.DatabaseId // "N/A")|\(.SchemaName // "N/A")|\(.DbType // "N/A")|\(.Host // "N/A"):\(.Port // "N/A")"' | \
        while IFS='|' read -r db_id schema_name db_type host_port; do
            printf "%-15s %-25s %-12s %-30s\n" "$db_id" "$schema_name" "$db_type" "$host_port"
        done
    fi
fi
