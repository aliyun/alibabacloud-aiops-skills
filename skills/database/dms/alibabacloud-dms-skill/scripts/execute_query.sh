#!/bin/bash
# Execute SQL query against a DMS database using aliyun-cli.
#
# Prerequisites:
#   - aliyun-cli installed (brew install aliyun-cli)
#   - aliyun configure set --mode AK --access-key-id <AK> --access-key-secret <SK> --region cn-hangzhou
#   - jq installed for JSON parsing (brew install jq)
#
# Usage:
#   ./execute_query.sh --db-id 12345 --sql "SELECT 1"
#   ./execute_query.sh --db-id 12345 --sql "SHOW TABLES" --json
#   ./execute_query.sh --db-id 12345 --sql "SELECT * FROM users LIMIT 5" --logic

set -e

# Default region
REGION="${REGION:-cn-hangzhou}"

# Parse arguments
DB_ID=""
SQL=""
LOGIC=false
OUTPUT_JSON=false

print_help() {
    echo "Usage: $0 --db-id <database_id> --sql <sql_statement> [options]"
    echo ""
    echo "Required arguments:"
    echo "  --db-id <id>      Database ID"
    echo "  --sql <statement> SQL statement to execute"
    echo ""
    echo "Optional arguments:"
    echo "  --logic           Use logic database mode"
    echo "  --json            Output results in JSON format"
    echo "  --region <region> Aliyun region (default: cn-hangzhou)"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --db-id 12345 --sql \"SELECT 1\""
    echo "  $0 --db-id 12345 --sql \"SHOW TABLES\" --json"
    echo "  $0 --db-id 12345 --sql \"SELECT * FROM users LIMIT 5\" --logic"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --db-id)
            DB_ID="$2"
            shift 2
            ;;
        --sql)
            SQL="$2"
            shift 2
            ;;
        --logic)
            LOGIC=true
            shift
            ;;
        --json)
            OUTPUT_JSON=true
            shift
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            print_help >&2
            exit 1
            ;;
        *)
            echo "Unexpected argument: $1" >&2
            print_help >&2
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$DB_ID" ]]; then
    echo "Error: --db-id is required" >&2
    print_help >&2
    exit 1
fi

# Validate DB_ID: must be a positive integer (Long type)
if ! echo "$DB_ID" | grep -qE '^[0-9]+$'; then
    echo "Error: --db-id 必须是正整数" >&2
    exit 1
fi
if [[ ${#DB_ID} -gt 19 ]]; then
    echo "Error: --db-id 超出有效范围 (最大 19 位数字)" >&2
    exit 1
fi

if [[ -z "$SQL" ]]; then
    echo "Error: --sql is required" >&2
    print_help >&2
    exit 1
fi

# Validate SQL: length 1-10000 characters
if [[ ${#SQL} -gt 10000 ]]; then
    echo "Error: SQL 语句长度不能超过 10000 个字符" >&2
    exit 1
fi
if [[ ${#SQL} -lt 1 ]]; then
    echo "Error: SQL 语句不能为空" >&2
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

# SQL safety check - block destructive operations
SQL_UPPER=$(echo "$SQL" | tr '[:lower:]' '[:upper:]')
if echo "$SQL_UPPER" | grep -qE '^\s*(DELETE|DROP|UPDATE|TRUNCATE|ALTER|RENAME)\s'; then
    echo "Error: 安全检查失败 - 不允许执行破坏性 SQL 操作 (DELETE/DROP/UPDATE/TRUNCATE/ALTER/RENAME)" >&2
    exit 1
fi
if echo "$SQL_UPPER" | grep -qE '\s(DELETE\s+FROM|DROP\s+TABLE|DROP\s+DATABASE|UPDATE\s+.+\s+SET|TRUNCATE\s+TABLE)\s'; then
    echo "Error: 安全检查失败 - 不允许执行破坏性 SQL 操作 (DELETE/DROP/UPDATE/TRUNCATE)" >&2
    exit 1
fi

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

# Step 2: Execute SQL Script
echo "Executing SQL on database $DB_ID..." >&2

# Build command arguments
CMD_ARGS=(
    "dms-enterprise" "ExecuteScript"
    "--Tid" "$TID"
    "--DbId" "$DB_ID"
    "--Script" "$SQL"
    "--region" "$REGION"
    "--user-agent" "$USER_AGENT"
    "--read-timeout" "$READ_TIMEOUT"
    "--connect-timeout" "$CONNECT_TIMEOUT"
)

if [[ "$LOGIC" == "true" ]]; then
    CMD_ARGS+=("--Logic" "true")
fi

EXEC_RESPONSE=$(aliyun "${CMD_ARGS[@]}" 2>&1)

# Check if the request was successful
SUCCESS=$(echo "$EXEC_RESPONSE" | jq -r '.Success')
if [[ "$SUCCESS" != "true" ]]; then
    ERROR_MSG=$(echo "$EXEC_RESPONSE" | jq -r '.ErrorMessage // "Unknown error"')
    echo "Error: 执行SQL失败 - $ERROR_MSG" >&2
    exit 1
fi

# Extract results
RESULTS=$(echo "$EXEC_RESPONSE" | jq '.Results.Results // []')

if [[ "$OUTPUT_JSON" == "true" ]]; then
    # Output JSON format
    echo "$RESULTS" | jq '.'
else
    # Output table format
    RESULT_COUNT=$(echo "$RESULTS" | jq 'length')
    
    if [[ "$RESULT_COUNT" -eq 0 ]]; then
        echo "查询完成，无返回结果"
    else
        for ((i=0; i<RESULT_COUNT; i++)); do
            RESULT=$(echo "$RESULTS" | jq ".[$i]")
            
            if [[ "$RESULT_COUNT" -gt 1 ]]; then
                echo "--- 结果集 $((i+1)) ---"
            fi
            
            RESULT_SUCCESS=$(echo "$RESULT" | jq -r '.Success')
            if [[ "$RESULT_SUCCESS" != "true" ]]; then
                MSG=$(echo "$RESULT" | jq -r '.Message // "Unknown error"')
                echo "错误: $MSG"
                continue
            fi
            
            # Get column names
            COLUMNS=$(echo "$RESULT" | jq -r '.ColumnNames // [] | @tsv')
            if [[ -n "$COLUMNS" ]]; then
                echo "$COLUMNS"
                echo "--------------------------------------------------"
            fi
            
            # Get rows
            ROWS=$(echo "$RESULT" | jq -r '.Rows.Row // []')
            ROW_COUNT=$(echo "$ROWS" | jq 'length')
            
            for ((j=0; j<ROW_COUNT; j++)); do
                ROW_VALUES=$(echo "$ROWS" | jq -r ".[$j].RowValue // [] | @tsv")
                echo "$ROW_VALUES"
            done
            
            TOTAL_ROWS=$(echo "$RESULT" | jq -r '.RowCount // 0')
            echo ""
            echo "($TOTAL_ROWS rows)"
        done
    fi
fi
