#!/bin/bash
# ODPS Information Schema Query Helper
# Portable version - configure ODPS_CMD path before use

# MCP Mode:
# When maxcompute-catalog MCP is available, the AI agent should use MCP tools
# (list_tables, get_table_schema, execute_sql, etc.) instead of this script.
# This script serves as the odpscmd fallback channel.
# See references/mcp-tools-reference.md for MCP tool details.

# Configuration - modify these paths for your environment
ODPS_CMD="${ODPS_CMD:-odpscmd}"  # Path to odpscmd binary, or set ODPS_CMD env var
NS_FLAG="SET odps.namespace.schema=true;"

usage() {
    echo "Usage: $0 [OPTIONS] <query_type>"
    echo ""
    echo "Options:"
    echo "  -p, --project <name>    Specify project"
    echo "  -d, --date <YYYYMMDD>   Specify date for historical queries (default: yesterday)"
    echo "  -t, --timeout <seconds> Execution timeout in seconds (default: 300)"
    echo "  -h, --help              Show this help"
    echo ""
    echo "Query types:"
    echo "  tables                  List all tables with sizes"
    echo "  top-storage             Top 20 tables by storage"
    echo "  columns <table>         Show columns for a table"
    echo "  partitions <table>      Show partitions for a table"
    echo "  failed-tasks            Failed tasks for a date"
    echo "  cu-hours                Daily CU-hour trend"
    echo "  cost-by-owner           Cost breakdown by owner"
    echo "  permissions             Permission audit"
    echo "  user-roles              User-role matrix"
    echo "  comment-coverage        Metadata governance coverage"
    echo "  tunnel-daily            Daily tunnel volume"
    echo "  zombie-tables           Tables not accessed in 90 days (with NULL-safe COALESCE)"
    echo "  cost-by-type            Cost breakdown by task type"
    echo "  quota-usage             Top 20 users by CU hours (7-day)"
    echo "  permission-audit        Active non-owner permissions (expired filtered)"
    echo "  smoke-test              Minimal IS query to verify namespace flag"
    echo "  custom <sql>            Custom SQL (auto-prepends namespace flag)"
    echo ""
    echo "Examples:"
    echo "  $0 top-storage"
    echo "  $0 columns my_table"
    echo "  $0 failed-tasks -d 20240101"
    echo "  $0 custom 'SELECT table_name FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES LIMIT 10;'"
}

# Default date: yesterday
DATE=$(date -v-1d '+%Y%m%d' 2>/dev/null || date -d 'yesterday' '+%Y%m%d' 2>/dev/null)
PROJECT=""
TIMEOUT=300
QUERY_TYPE=""
TABLE_NAME=""
CUSTOM_SQL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project) PROJECT="$2"; shift 2 ;;
        -d|--date) DATE="$2"; shift 2 ;;
        -t|--timeout) TIMEOUT="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *)
            if [ -z "$QUERY_TYPE" ]; then
                QUERY_TYPE="$1"
            elif [ -z "$TABLE_NAME" ]; then
                TABLE_NAME="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$QUERY_TYPE" ]; then
    usage
    exit 1
fi

# Validate DATE format (YYYYMMDD)
if ! echo "$DATE" | grep -qE '^[0-9]{8}$'; then
    echo "Error: invalid date format. Expected YYYYMMDD (e.g., 20240101)."
    exit 1
fi

# Build SQL based on query type
case $QUERY_TYPE in
    tables)
        SQL="$NS_FLAG SELECT table_name, owner_name, data_length / 1024 / 1024 / 1024 AS size_gb FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES ORDER BY data_length DESC LIMIT 50;"
        ;;
    top-storage)
        SQL="$NS_FLAG SELECT table_name, owner_name, data_length / 1024 / 1024 / 1024 AS size_gb, lifecycle FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES WHERE table_type = 'MANAGED_TABLE' ORDER BY data_length DESC LIMIT 20;"
        ;;
    columns)
        if [ -z "$TABLE_NAME" ]; then echo "Error: table name required"; exit 1; fi
        if ! echo "$TABLE_NAME" | grep -qE '^[a-zA-Z0-9_]{1,128}$'; then
            echo "Error: invalid table name. Only letters, digits, and underscores allowed (max 128 chars)."
            exit 1
        fi
        SQL="$NS_FLAG SELECT column_name, data_type, is_nullable, column_comment FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.COLUMNS WHERE table_name = '$TABLE_NAME' ORDER BY ordinal_position;"
        ;;
    partitions)
        if [ -z "$TABLE_NAME" ]; then echo "Error: table name required"; exit 1; fi
        if ! echo "$TABLE_NAME" | grep -qE '^[a-zA-Z0-9_]{1,128}$'; then
            echo "Error: invalid table name. Only letters, digits, and underscores allowed (max 128 chars)."
            exit 1
        fi
        SQL="$NS_FLAG SELECT partition_name, data_length / 1024 / 1024 AS size_mb, create_time FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.PARTITIONS WHERE table_name = '$TABLE_NAME' ORDER BY partition_name DESC LIMIT 50;"
        ;;
    failed-tasks)
        SQL="$NS_FLAG SELECT task_name, task_type, owner_name, start_time, end_time FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY WHERE ds = '$DATE' AND status = 'Failed' ORDER BY start_time DESC;"
        ;;
    cu-hours)
        SQL="$NS_FLAG SELECT ds, COUNT(*) AS task_count, SUM(cost_cpu) / 100.0 / 3600 AS cu_hours FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -14, 'dd'), 'yyyymmdd') GROUP BY ds ORDER BY ds DESC LIMIT 30;"
        ;;
    cost-by-owner)
        SQL="$NS_FLAG SELECT owner_name, COUNT(*) AS task_count, SUM(cost_cpu) / 100.0 / 3600 AS cu_hours FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY WHERE ds = '$DATE' GROUP BY owner_name ORDER BY cu_hours DESC;"
        ;;
    permissions)
        SQL="$NS_FLAG SELECT p.table_name, p.user_name, p.privilege_type, t.owner_name FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLE_PRIVILEGES p JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES t ON p.table_catalog = t.table_catalog AND p.table_name = t.table_name WHERE p.user_name != t.owner_name ORDER BY p.table_name;"
        ;;
    user-roles)
        SQL="$NS_FLAG SELECT u.user_name, r.role_name FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.USERS u LEFT JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.USER_ROLES ur ON u.user_id = ur.user_id AND u.user_catalog = ur.user_role_catalog LEFT JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.ROLES r ON ur.role_name = r.role_name AND ur.user_role_catalog = r.role_catalog ORDER BY u.user_name, r.role_name;"
        ;;
    comment-coverage)
        SQL="$NS_FLAG SELECT 'Tables' AS entity, COUNT(CASE WHEN table_comment IS NOT NULL AND table_comment != '' THEN 1 END) AS commented, COUNT(*) AS total, COUNT(CASE WHEN table_comment IS NOT NULL AND table_comment != '' THEN 1 END) * 100.0 / COUNT(*) AS coverage_pct FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES UNION ALL SELECT 'Columns', COUNT(CASE WHEN column_comment IS NOT NULL AND column_comment != '' THEN 1 END), COUNT(*), COUNT(CASE WHEN column_comment IS NOT NULL AND column_comment != '' THEN 1 END) * 100.0 / COUNT(*) FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.COLUMNS;"
        ;;
    tunnel-daily)
        SQL="$NS_FLAG SELECT ds, COUNT(*) AS tunnel_count, SUM(data_size) / 1024 / 1024 / 1024 AS volume_gb FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TUNNELS_HISTORY WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -14, 'dd'), 'yyyymmdd') GROUP BY ds ORDER BY ds DESC LIMIT 14;"
        ;;
    zombie-tables)
        SQL="$NS_FLAG SELECT table_name, owner_name, data_length / 1024 / 1024 / 1024 AS size_gb, COALESCE(last_access_time, last_modified_time) AS last_access, lifecycle FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES WHERE COALESCE(last_access_time, last_modified_time) < DATEADD(GETDATE(), -90, 'dd') AND table_type = 'MANAGED_TABLE' AND data_length IS NOT NULL ORDER BY data_length DESC;"
        ;;
    cost-by-type)
        SQL="$NS_FLAG SELECT task_type, COUNT(*) AS task_count, SUM(cost_cpu) / 100.0 / 3600 AS cu_hours, SUM(input_bytes) / 1024 / 1024 / 1024 AS input_gb FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY WHERE ds = '$DATE' GROUP BY task_type ORDER BY cu_hours DESC;"
        ;;
    quota-usage)
        SQL="$NS_FLAG SELECT task_type, owner_name, SUM(cost_cpu) / 100.0 / 3600 AS cu_hours FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -7, 'dd'), 'yyyymmdd') GROUP BY task_type, owner_name ORDER BY cu_hours DESC LIMIT 20;"
        ;;
    permission-audit)
        SQL="$NS_FLAG SELECT p.table_name, p.user_name, p.privilege_type, t.owner_name FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLE_PRIVILEGES p JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES t ON p.table_catalog = t.table_catalog AND p.table_name = t.table_name WHERE p.user_name != t.owner_name AND (p.expired IS NULL OR p.expired > GETDATE()) ORDER BY p.table_name;"
        ;;
    smoke-test)
        SQL="$NS_FLAG SELECT COUNT(*) AS table_count FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES LIMIT 1;"
        ;;
    custom)
        if [ -z "$TABLE_NAME" ]; then echo "Error: SQL required for custom query"; exit 1; fi
        CUSTOM_SQL="$TABLE_NAME"
        # Reject DDL/DML — custom mode only allows SELECT (DQL)
        if echo "$CUSTOM_SQL" | grep -qiE '^\s*(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|MERGE|LOAD|UNLOAD)\b'; then
            echo "Error: DDL/DML statements are not allowed in custom mode. Only SELECT queries are supported."
            exit 1
        fi
        # Reject SELECT * (violates no-SELECT-* rule)
        if echo "$CUSTOM_SQL" | grep -qiE 'SELECT\s+\*\s+FROM'; then
            echo "Error: SELECT * is not allowed. Use explicit column names."
            exit 1
        fi
        # Check if SQL already has the namespace flag
        if [[ "$CUSTOM_SQL" != *"$NS_FLAG"* ]]; then
            SQL="$NS_FLAG $CUSTOM_SQL"
        else
            SQL="$CUSTOM_SQL"
        fi
        ;;
    *)
        echo "Unknown query type: $QUERY_TYPE"
        usage
        exit 1
        ;;
esac

# Execute
CMD="$ODPS_CMD"
if [ -n "$PROJECT" ]; then
    if ! echo "$PROJECT" | grep -qE '^[a-zA-Z][a-zA-Z0-9_]{2,27}$'; then
        echo "Error: invalid project name. Must start with a letter, contain only letters/digits/underscores, and be 3-28 chars."
        exit 1
    fi
    CMD="$CMD --project=$PROJECT"
fi

echo "Query type: $QUERY_TYPE"
[ -n "$PROJECT" ] && echo "Project: $PROJECT"
echo "---"
timeout "$TIMEOUT" $CMD -e "$SQL"
