# Lindorm CLI Agent Skill Guide

Lindorm CLI usage guide for AI Agents. Lindorm CLI is the official command-line tool for Alibaba Cloud Lindorm Database. It supports the MySQL protocol for the wide table engine and the Avatica protocol for the time series engine, and works out of the box without extra dependencies.

---

## Core Workflow

In each new session, the Agent should execute the following sequence:

```text
1. Installation detection / version verification (>= 2.3.0) / automatic installation or upgrade -> 2. Interactive collection of connection information -> 3. Connection probe -> 4. Get Tool Schema -> 5. Execute SQL as needed
```

---

## Phase 1: Installation Detection, Version Verification, and Automatic Installation

> **Minimum required version: 2.3.0**. Versions earlier than this do not support Agent-oriented core capabilities such as `--tool-schema`, `--auto-limit`, `--quiet`, `--field`, and structured error JSON. Direct Agent use of old versions may cause parsing failures and security risks. **The Agent must pass version verification in Phase 1 before entering Phase 2. Otherwise, it must not continue.**

### Step 1: Installation Detection

The Agent first checks whether `lindorm-cli` is installed:

```bash
which lindorm-cli 2>/dev/null && lindorm-cli --version
```

- **Installed** -> Go to Step 2, version verification.
- **Not installed** -> Go to Step 3, automatic installation.

### Step 2: Version Verification, Hard Gate

The Agent must parse the version number and compare it with the minimum requirement **2.3.0**:

```bash
CLI_VERSION=$(lindorm-cli --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
REQUIRED="2.3.0"

# Compare versions. sort -V sorts the lowest version first, so the check passes when REQUIRED is first.
if [ "$(printf '%s\n%s' "$REQUIRED" "$CLI_VERSION" | sort -V | head -n1)" = "$REQUIRED" ]; then
  echo "Version OK: $CLI_VERSION (>= $REQUIRED)"
else
  echo "Version TOO OLD: $CLI_VERSION (< $REQUIRED), upgrade required" >&2
  exit 1
fi
```

**Verification result handling**:

| Result | Agent Behavior |
|------|-----------|
| Version >= 2.3.0 | Passed. Enter Phase 2. |
| Version < 2.3.0 | **Block**. Ask the user to upgrade, then enter Step 3. |

When the version requirement is not met, the Agent should explain why and propose an upgrade:

> **[Agent tells the user]**: The current lindorm-cli version is `X.Y.Z`, which is lower than the minimum Agent-required version 2.3.0. Old versions do not support Agent-oriented non-interactive output, structured errors, and related capabilities. Continuing may cause parsing failures and security risks. Do you want to automatically upgrade to the latest version?

- User agrees -> Go to Step 3 and install to the existing `lindorm-cli` directory, replacing the old version.
- User refuses -> The Agent **must not continue** to later phases. Tell the user to upgrade manually and retry.

### Step 3: Automatic Installation / Upgrade

The Agent automatically selects the corresponding version according to the current operating system and CPU architecture:

**Platform download URL mapping**:

| OS | ARCH | Download URL |
|----|------|---------|
| Linux | x86_64 / AMD64 | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-linux-latest.tar.gz` |
| Linux | ARM64 | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-linux-arm64-latest.tar.gz` |
| macOS | AMD64 (Intel) | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-mac-amd64-latest.tar.gz` |
| macOS | ARM64 (Apple Silicon) | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-mac-arm64-latest.tar.gz` |
| Windows | x86_64 | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-windows-x64-latest.zip` |

**Automatic installation / upgrade script, macOS / Linux**:

```bash
# Agent automatically detects the platform and installs the CLI.
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "${OS}-${ARCH}" in
  linux-x86_64|linux-amd64)  DL_URL="https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-linux-latest.tar.gz" ;;
  linux-arm64|linux-aarch64) DL_URL="https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-linux-arm64-latest.tar.gz" ;;
  darwin-x86_64|darwin-amd64) DL_URL="https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-mac-amd64-latest.tar.gz" ;;
  darwin-arm64)               DL_URL="https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-mac-arm64-latest.tar.gz" ;;
  *) echo "Unsupported platform: ${OS}-${ARCH}" >&2; exit 1 ;;
esac

curl --connect-timeout 30 -m 120 -L -o /tmp/lindorm-cli.tar.gz "$DL_URL"
tar -xzf /tmp/lindorm-cli.tar.gz -C /tmp
chmod +x /tmp/lindorm-cli

# Upgrade scenario: install to the existing lindorm-cli directory, replacing the old version.
EXISTING_PATH=$(which lindorm-cli 2>/dev/null)
if [ -n "$EXISTING_PATH" ]; then
  INSTALL_DIR=$(dirname "$EXISTING_PATH")
  mv /tmp/lindorm-cli "$INSTALL_DIR/lindorm-cli"
  echo "Upgraded lindorm-cli at $INSTALL_DIR"
# Fresh installation: preferably install to ~/.local/bin; otherwise leave it in /tmp.
elif [ -d "$HOME/.local/bin" ]; then
  mv /tmp/lindorm-cli "$HOME/.local/bin/lindorm-cli"
else
  echo "lindorm-cli installed at /tmp/lindorm-cli"
fi
rm -f /tmp/lindorm-cli.tar.gz

# Verify installation result.
lindorm-cli --version || /tmp/lindorm-cli --version
```

**Windows installation, manual prompt to the user**:

1. Download ZIP: `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-windows-x64-latest.zip`
2. Extract it and add the directory to PATH.
3. Verify: `lindorm-cli --version`

> **After installation / upgrade is complete**, the Agent must return to Step 2 and perform version verification. It may enter Phase 2 only after confirming that the version is >= 2.3.0.

---

## Phase 2: Interactive Collection of Connection Information

The Agent should collect the following required connection parameters from the user:

> **[Agent asks the user]**: Please provide the following Lindorm connection information:
> 1. **Connection address**, domain:port, such as `ld-xxx-proxy-lindorm-pub.lindorm.aliyuncs.com:33060`
> 2. **Username**, default `root`
> 3. **Password**
> 4. **Default database**, default `default`
> 5. **Engine type**: wide table engine, MySQL protocol on port 33060, or time series engine, Avatica protocol on port 8242?

### Connection Address Format Rules

After collecting the information, the Agent automatically assembles the correct URL format according to the engine type:

| Engine | Protocol | URL Format | Example |
|------|------|---------|------|
| Wide table engine | MySQL | `<host>:33060` or `mysql://<host>:33060` | `ld-xxx-proxy-lindorm.lindorm.rds.aliyuncs.com:33060` |
| Time series engine | Avatica | `jdbc:lindorm:tsdb:url=http://<host>:8242` | `jdbc:lindorm:tsdb:url=http://ld-xxx-proxy-tsdb.lindorm.rds.aliyuncs.com:8242` |

> **Protocol selection**: The wide table engine uses MySQL protocol port 33060, and the time series engine uses Avatica protocol port 8242.

> **V1/V2 domain differences**: V2 instance domains are `*.lindorm.aliyuncs.com`; V1 instance domains are `*.lindorm.rds.aliyuncs.com`. The Agent can obtain the precise address by running `aliyun hitsdb get-lindorm-instance-engine-list --instance-id <id>`.

### Environment Variable Configuration, Recommended

After collecting connection information, the Agent should configure environment variables to avoid passing sensitive parameters in every call:

```bash
export LINDORM_URL="mysql://<host>:33060"
export LINDORM_USER="<username>"
export LINDORM_PASSWORD="<password>"
export LINDORM_DATABASE="<database>"
export LINDORM_SAFE_MODE=true
```

> **Security rules**:
> - **NEVER** pass passwords directly in command-line parameters. Always use environment variables or `--password-stdin`.
> - **NEVER** echo password values in the conversation.
> - Priority: CLI parameters > environment variables > default values.

---

## Phase 3: Connection Probe

After configuration is complete, the Agent must execute a connection probe to verify network reachability and credential correctness:

```bash
lindorm-cli --format json --execute "SELECT 1" 2>/dev/null
```

### Connection Failure Diagnostics

| Exit Code | Meaning | Agent Handling Suggestion |
|--------|------|---------------|
| 0 | Connection succeeds | Continue subsequent operations |
| 3 | Server / SQL error | Check whether the username and password are correct |
| 5 | Timeout | Network / firewall issue |

**Troubleshooting steps for connection timeout or refusal**, which the Agent should proactively report:

1. **Check the Lindorm whitelist**: Confirm that the client IP has been added to the instance whitelist.
   ```bash
   aliyun hitsdb get-instance-ip-white-list --instance-id <id>
   ```
2. **Check network link reachability**:
   ```bash
   # Test whether the port is reachable.
   nc -zv <host> <port> -w 5
   ```
3. **Distinguish internal and public addresses**: Public addresses require public access to be enabled. The suffix usually contains `-pub` or `-public`.
4. **Check VPC networking**: If an internal address is used, confirm that the client and the Lindorm instance are in the same VPC.

> **[Agent prompts the user]**: Connection failed, exit code=5, timeout. Possible causes: 1) The client IP has not been added to the Lindorm whitelist; 2) An internal address is used while the client is not in the same VPC; 3) Public access has not been enabled for the public address. Please check and retry.

---

## Phase 4: Get Tool Schema, Required for Each New Session

After a connection is successfully established, the Agent **must** use `--tool-schema` to get the lindorm-cli capability declaration and Cookbook:

```bash
lindorm-cli --tool-schema
```

**Output structure**, JSON:

```json
{
  "capabilities_version": 1,
  "version": "2.x.x",
  "engines": ["mysql", "avatica"],
  "formats": ["json", "jsonl", "csv", "column", "table", "vertical"],
  "exit_codes": {
    "0": "success",
    "1": "general",
    "2": "usage",
    "3": "server",
    "4": "io",
    "5": "timeout",
    "9": "internal"
  },
  "flags": ["batch", "concurrent", "format", "max-rows", "safe-mode", "auto-limit", "quiet", "field", ...],
  "cookbook": {
    "sections": [
      { "id": "environment_config", "title": "Environment configuration", "content": "..." },
      { "id": "stdout_stderr_contract", "title": "stdout / stderr contract", "content": "..." },
      { "id": "exit_codes_error_handling", "title": "Exit codes and error handling", "content": "..." },
      { "id": "common_operations", "title": "Common operation templates", "content": "..." },
      { "id": "e2e_examples", "title": "End-to-end examples", "content": "..." },
      { "id": "claude_code_integration", "title": "Claude Code integration guide", "content": "..." },
      { "id": "notes", "title": "Notes", "content": "..." }
    ]
  }
}
```

**Agent behavior rules**:
- Execute `--tool-schema` once in every new session to discover features supported by the current CLI version.
- Determine supported parameters and behavior based on `version` and `flags`.
- Determine available protocols based on `engines`.
- Determine whether new parameters such as `--auto-limit`, `--quiet`, and `--field` are supported based on `flags`.
- Extract operation templates from `cookbook.sections` as references for SQL execution.

> **Lightweight alternative**: If only basic CLI capabilities are needed, such as version, protocols, output formats, and exit codes, use `lindorm-cli --capabilities`. It outputs a more compact JSON without the Cookbook and is suitable for quick version compatibility checks.

---

## Phase 5: Agent Invocation Specification

### Baseline Parameter Combination

When executing interactive queries or exploration, the Agent **must** include the following baseline parameters, except for data export scenarios. See the "Data Export" section below:

```bash
lindorm-cli \
  --format json \
  --safe-mode \
  --max-rows 1000 \
  --auto-limit 1000 \
  --execute "YOUR SQL HERE"
```

| Parameter | Purpose | Description |
|------|------|------|
| `--format json` | Output pure JSON to stdout | Easy for Agent programs to parse. In versions >= 2.3.1, VARCHAR is output as plaintext. In versions <= 2.3.0, VARCHAR is output as base64. When string fields are involved, decode them or use `csv` / `table` format instead. |
| `--safe-mode` | Intercept high-risk SQL | **Must always be included. Do not proactively remove it**. Even if the user has confirmed the intent of a destructive operation, the first execution must still include this parameter. See "Security Mode - Double Check Protocol". |
| `--max-rows 1000` | Hard client-side result truncation | Prevent large result sets from exhausting tokens. |
| `--auto-limit 1000` | Automatically inject server-side LIMIT | Automatically append LIMIT N to SELECT statements without LIMIT. Use it as the default Agent protection parameter. |
| `--execute "SQL"` | Non-interactive mode | Exit after execution. Suitable for Agent invocation. |

### stdout / stderr Separation Contract

When `--format` is `json` or `jsonl`, the CLI strictly separates output:

| Output Target | Content | Agent Handling Method |
|---------|------|---------------|
| **stdout** | Pure data. `json` is a single JSON object, and `jsonl` is JSON Lines. | Parse this stream to get query results. |
| **stderr** | Errors, structured JSON, row statistics, and truncation warnings | Use for error handling and logs. |

```bash
# Correct: parse stdout only.
result=$(lindorm-cli --format json --execute "SELECT * FROM sensor LIMIT 5" 2>/dev/null)
echo "$result" | jq '.'
```

### JSON Output Structure

The stdout output of `--format json` is a **single object** that contains three keys:

```json
{"columns":["id","name"], "columnTyps":["VARCHAR","VARCHAR"], "rows":[["r1","alice"],["r2","bob"]]}
```

| Key | Type | Description |
|-----|------|------|
| `columns` | string[] | Column name list |
| `columnTyps` | string[] | Column type list. Note that the spelling is `Typs`, not `Types`. |
| `rows` | any[][] | Data rows. Each row is an array of values. |

> **⚠️ Parsing pitfall**: To get the row count, use `len(d["rows"])`. **Do not** use `len(d)`. The latter returns the number of JSON object keys, fixed at 3: `columns` + `columnTyps` + `rows`, not the result row count.

```python
# ❌ Incorrect: len(d) returns the number of keys, 3, not row count.
import json; d = json.load(sys.stdin); print(len(d))  # Outputs 3

# ✅ Correct: len(d["rows"]) returns the actual row count.
import json; d = json.load(sys.stdin); print(len(d["rows"]))  # Outputs actual row count
```

### Exit Codes and Error Handling

| Exit Code | Name | Meaning | Agent Handling Suggestion |
|--------|------|------|---------------|
| `0` | success | Execution succeeded | Parse stdout JSON |
| `1` | general | Unclassified error | Record stderr logs |
| `2` | usage | Parameter / usage error | Check flag spelling and parameter format |
| `3` | server | Server / SQL error | Parse stderr JSON for details |
| `4` | io | Local I/O error | Check file path and permissions |
| `5` | timeout | Operation timeout | Increase `--connectTimeout` and retry |
| `9` | internal | Internal error, panic | Escalate for manual handling |

**Structured error JSON**, output to stderr:

```json
{"kind":"server","error_no":1146,"sql_state":"42S02","message":"Table 'db1.not_exist' doesn't exist","exit_code":3}
```

> **Note**: In versions >= 2.3.1, `--safe-mode` interception outputs structured JSON to stderr, as shown above. In versions <= 2.3.0, stderr is plain text. The Agent handles it by matching exit code plus the keyword `[safe mode]`.

| Field | Type | Description |
|------|------|------|
| `kind` | string | `server` / `usage` / `misc` |
| `error_no` | int | Server error code |
| `sql_state` | string | SQL State code |
| `message` | string | Error description |
| `exit_code` | int | Same as the process exit code |

### Error Handling Template

```bash
output=$(lindorm-cli --format json --execute "YOUR SQL" 2>/tmp/lindorm_err.json)
rc=$?

case $rc in
  0) echo "$output" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2, ensure_ascii=False))" ;;
  2) echo "Usage error, check flag spelling" >&2 ;;
  3) error_msg=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('message','unknown'))" < /tmp/lindorm_err.json 2>/dev/null || cat /tmp/lindorm_err.json)
     echo "Server error: $error_msg" >&2 ;;
  5) echo "Timeout, retrying with longer timeout..." >&2
     output=$(lindorm-cli --format json --connectTimeout 60s --execute "YOUR SQL" 2>/dev/null) ;;
  *) echo "Unexpected error (exit=$rc)" >&2 ;;
esac
```

---

## Common Operations Cookbook

> The following examples depend on the `LINDORM_*` environment variables configured in Phase 2. For complete SQL syntax, see [sql-operations.md](../01-dev/sql-operations.md).

### Schema Exploration

```bash
# List all databases.
lindorm-cli --format json --execute "SHOW DATABASES" 2>/dev/null

# List all tables in the current database.
lindorm-cli --format json --execute "SHOW TABLES" 2>/dev/null

# View table schema.
lindorm-cli --format json --execute "DESCRIBE sensor" 2>/dev/null

# View CREATE TABLE statement.
lindorm-cli --format json --execute "SHOW CREATE TABLE sensor" 2>/dev/null

# Query after switching database. --splitCommand outputs each SQL independently. Use jsonl format to avoid concatenation issues.
lindorm-cli --format jsonl --execute "USE mydb; SHOW TABLES;" --splitCommand 2>/dev/null
```

### Data Query

```bash
# Safe query with row limit.
lindorm-cli --format json --safe-mode --max-rows 100 \
  --execute "SELECT * FROM sensor WHERE device_id = 'dev001' ORDER BY ts DESC" \
  2>/dev/null

# Aggregate statistics.
lindorm-cli --format json --execute "SELECT COUNT(*) AS cnt FROM sensor" 2>/dev/null

# Batch execute multiple SQL statements.
lindorm-cli --format json --splitCommand \
  --execute "USE mydb; SELECT COUNT(*) AS cnt FROM t1; SELECT COUNT(*) AS cnt FROM t2;" \
  2>/dev/null

# Read SQL from stdin, pipeline mode.
echo "SELECT * FROM sensor LIMIT 10;" | lindorm-cli --format json --execute "-" 2>/dev/null
```

### Data Export

> **Note**: The `--max-rows` parameter in the baseline parameter set does not apply to data export scenarios. Otherwise, export results may be silently truncated. Control the export range through SQL `WHERE` / `LIMIT` clauses.

```bash
# Export as CSV.
lindorm-cli --format csv --execute "SELECT * FROM sensor" --output ./export.csv

# Export as JSON.
lindorm-cli --format json --execute "SELECT * FROM sensor" --output ./export.json 2>/dev/null

# Export CSV without header.
lindorm-cli --format csv --csvNoHeader --execute "SELECT * FROM sensor" --output ./export.csv
```

### Data Import

```bash
# Import from CSV.
lindorm-cli --table sensor --input ./data.csv --batch 2000 --concurrent 10

# Import from JSON.
lindorm-cli --table sensor --input ./data.json --batch 2000 --concurrent 10
```

### Connection Diagnostics

```bash
# Check connection.
lindorm-cli --format json --execute "SELECT 1" 2>/dev/null
rc=$?
if [ $rc -eq 0 ]; then echo "Connection OK"; else echo "Connection failed (exit=$rc)"; fi

# View version information.
lindorm-cli --version
```

------

## SQL Syntax Notes

> **Key point**: The SQL parser of Lindorm CLI has subtle differences from the mysql client. The Agent must pay attention to the following CLI-specific pitfalls. For complete SQL syntax, including UPSERT/INSERT semantics, transaction limits, and inefficient query handling, see [sql-operations.md](../01-dev/sql-operations.md).

### CREATE TABLE: PRIMARY KEY Position

Lindorm CLI requires `PRIMARY KEY` to be written **inside** the column definition parentheses:

```sql
-- ✅ Correct: PRIMARY KEY is inside the column definition parentheses.
CREATE TABLE t1 (id VARCHAR NOT NULL, name VARCHAR, score INT, PRIMARY KEY(id));

-- ❌ Incorrect: PRIMARY KEY is an independent clause. The mysql client may accept it, but lindorm-cli --execute reports an error.
CREATE TABLE t1 (id VARCHAR NOT NULL, name VARCHAR, score INT) PRIMARY KEY (id);
```

> Error message: `"Encountered PRIMARY PRIMARY"`

### Reserved Word Column Names

Avoid using SQL reserved words such as `value`, `key`, and `timestamp` as column names. **The complete list of reserved and non-reserved keywords can be queried through `SELECT * FROM information_schema.KEYWORDS`**. See [sql-operations.md](../01-dev/sql-operations.md#reserved-keywords). If they must be used, escape them with **backticks** in lindorm-cli. Note: use double quotes when connecting directly through the MySQL protocol.

```sql
-- ❌ Incorrect: "value" is a reserved word.
CREATE TABLE t1 (id VARCHAR, value INT, PRIMARY KEY(id));

-- ✅ Correct: backtick escaping, lindorm-cli.
CREATE TABLE t1 (id VARCHAR, `value` INT, PRIMARY KEY(id));

-- ✅ Correct: double-quote escaping, MySQL protocol direct connection / JDBC.
CREATE TABLE t1 (id VARCHAR, "value" INT, PRIMARY KEY(id));
```

### Agent Handling Flow for Inefficient Queries

When the Agent executes SQL through lindorm-cli and encounters the `This query may be a full table scan` or `Detect inefficient query` error, it **must** follow this flow:

1. **Analyze the cause**: Check whether the WHERE condition lacks the first primary key column or misses indexes. See [sql-operations.md](../01-dev/sql-operations.md#inefficient-query-full-table-scan).
2. **Prefer solutions 1-4**: Guide the user to optimize query conditions, create indexes, and so on.
3. **Use solution 5 only after user confirmation**: If the user insists on forced execution, the Agent must explain the risk and obtain explicit confirmation.

> **[Agent must ask the user]**: The current query triggered inefficient query interception. The `/*+ _l_allow_filtering_ */` Hint can force execution, but **forcing a full table scan may introduce performance and stability risks**. In large-data scenarios, it may cause query timeout or affect overall instance performance. Do you confirm using the Hint to force execution?

If the user confirms, execute with the Hint:

```bash
lindorm-cli --format json --safe-mode --max-rows 1000 --auto-limit 1000 \
  --execute "SELECT /*+ _l_allow_filtering_ */ * FROM test WHERE p2 = 10" \
  2>/dev/null
```

> **Risk warning**: Forced inefficient query execution means full table scan. It is recommended to always use `--max-rows` or SQL `LIMIT` to limit the scan range. The long-term solution should prioritize creating indexes or optimizing query conditions. For complete risk descriptions and solutions, see [sql-operations.md](../01-dev/sql-operations.md#inefficient-query-full-table-scan).

### Other SQL Notes

- **Lindorm does not support transactions**: Disable transactions when using ORM frameworks. UPDATE supports only single-row updates, and WHERE must specify all primary keys. See [sql-operations.md](../01-dev/sql-operations.md#transaction-limits).
- **Connection idle timeout**: The server actively disconnects connections that have been idle for 10 minutes. The Agent should probe the connection again after a long period of inactivity. See [sql-operations.md](../01-dev/sql-operations.md#connection-idle-timeout).
- **UPSERT / INSERT semantics**: INSERT and UPSERT have the same semantics. When a primary key conflict occurs, data is overwritten and updated. See [sql-operations.md](../01-dev/sql-operations.md#upsert---insert-or-update-data).

---

## Output Format Reference

| Format | Description | Agent Usage Scenario |
|------|------|---------------|
| `json` | Single JSON object, `{"columns","columnTyps","rows"}` | **Agent default**, stdout outputs pure JSON |
| `jsonl` | JSON Lines, one JSON per line | Stream processing and log collection |
| `csv` | CSV format | Data export, can be used with `--csvNoHeader` |
| `table` | Table format, default | Human inspection in terminal |
| `column` | Column-aligned text | Compact display |
| `vertical` | Vertical display, similar to MySQL `\G` | Wide-table single-row display |

---

## Parameter Quick Reference

| Parameter | Description | Default |
|------|------|--------|
| `--url` | Connection address, supports MySQL and Avatica formats | — |
| `--database` | Default database | `default` |
| `--username` | Username | — |
| `--password` | Password, recommended to use environment variables instead | — |
| `--password-stdin` | Read password from stdin, mutually exclusive with `--password` | `false` |
| `--format` | Output format | `table` |
| `--execute` | Execute SQL and exit; `"-"` reads from stdin | — |
| `--safe-mode` | Intercept high-risk SQL operations | `false` |
| `--max-rows` | Maximum output rows, >= 1 | Unlimited |
| `--auto-limit` | Automatically inject LIMIT N for SELECT statements without LIMIT | `0`, disabled |
| `--quiet` | Output bare values, one per line, for single-column queries | `false` |
| `--field` | Extract one specified field from the result set. If specified multiple times, only the last one takes effect. | — |
| `--splitCommand` | Split multiple SQL statements by semicolon | `false` |
| `--pretty` | Pretty-print JSON output | `false` |
| `--csvNoHeader` | CSV without header | `false` |
| `--nullString` | Custom NULL value representation | MySQL: `\N`, Avatica: empty |
| `--connectTimeout` | Connection timeout | `30s` |
| `--output` | Export query results to a file | — |
| `--input` | Import file path, must be used with `--table` | — |
| `--table` | Target table name for import | — |
| `--batch` | Import / export batch size | `2000` |
| `--concurrent` | Number of concurrent import / export threads | `10` |
| `--precision` | Timestamp precision, Avatica protocol only | `rfc3339` |
| `--capabilities` | Output capability declaration JSON and exit | `false` |
| `--tool-schema` | Output capability declaration + Cookbook JSON and exit | `false` |
| `--skip-tls-verify` | Skip TLS certificate verification | `true` |
| `--debug` | Debug mode | `false` |
| `--version` | Show version information and exit | — |

### Environment Variables

| Environment Variable | Equivalent Parameter | Description |
|---------|---------|------|
| `LINDORM_URL` | `--url` | Connection address |
| `LINDORM_USER` | `--username` | Username |
| `LINDORM_PASSWORD` | `--password` | Password |
| `LINDORM_DATABASE` | `--database` | Database |
| `LINDORM_SAFE_MODE` | `--safe-mode` | Safe mode |
| `LINDORM_AUTO_LIMIT` | `--auto-limit` | Automatic LIMIT injection |

---

## End-to-End Workflow Examples

### Complete Schema Exploration + Data Preview

```bash
#!/bin/bash
set -euo pipefail

# List all tables. JSON output structure: {"columns":[...], "columnTyps":[...], "rows":[...]}.
echo "=== Tables ===" >&2
lindorm-cli --format json --execute "SHOW TABLES" 2>/dev/null | python3 -c "
import sys,json; d=json.load(sys.stdin)
for row in d['rows']: print(row[0])
"

# View target table schema.
echo "=== Schema of sensor ===" >&2
lindorm-cli --format json --execute "DESCRIBE sensor" 2>/dev/null | python3 -c "
import sys,json; d=json.load(sys.stdin)
for i,col in enumerate(d['columns']): print(col, end='\t')
print()
for row in d['rows']: print('\t'.join(str(v) for v in row))
"

# Preview the first 5 rows.
echo "=== Preview ===" >&2
lindorm-cli --format json --max-rows 5 --execute "SELECT * FROM sensor" 2>/dev/null | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(json.dumps({'columns': d['columns'], 'rows': d['rows'][:5]}, indent=2, ensure_ascii=False))
"
```

### Robust Query with Retry

```bash
#!/bin/bash
MAX_RETRIES=3
RETRY_DELAY=2

run_query() {
  local sql="$1"
  local attempt=1

  while [ $attempt -le $MAX_RETRIES ]; do
    output=$(lindorm-cli --format json --max-rows 1000 --execute "$sql" 2>/tmp/lindorm_err.json)
    rc=$?

    if [ $rc -eq 0 ]; then
      echo "$output"
      return 0
    elif [ $rc -eq 5 ]; then
      echo "Attempt $attempt/$MAX_RETRIES: timeout, retrying in ${RETRY_DELAY}s..." >&2
      sleep $RETRY_DELAY
      RETRY_DELAY=$((RETRY_DELAY * 2))
      attempt=$((attempt + 1))
    else
      echo "Non-retryable error (exit=$rc):" >&2
      cat /tmp/lindorm_err.json >&2
      return $rc
    fi
  done

  echo "All $MAX_RETRIES attempts failed" >&2
  return 1
}

run_query "SELECT * FROM sensor LIMIT 100"
```

### Safe Data Analysis with Protection

```bash
#!/bin/bash
set -euo pipefail

export LINDORM_SAFE_MODE=true

# Count rows. JSON structure: {"columns":["total"], "rows":[[5]]}.
count=$(lindorm-cli --format json --execute "SELECT COUNT(*) AS total FROM sensor" 2>/dev/null)
total=$(echo "$count" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][0][0])")
echo "Total rows: $total" >&2

# Aggregate by device.
lindorm-cli --format json --max-rows 100 \
  --execute "SELECT device_id, COUNT(*) AS cnt, AVG(temperature) AS avg_temp FROM sensor GROUP BY device_id ORDER BY cnt DESC" \
  2>/dev/null | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(json.dumps({'columns': d['columns'], 'rows': d['rows']}, indent=2, ensure_ascii=False))
"

# safe-mode intercepts dangerous operations. Versions <= 2.3.0 output text to stderr, and versions >= 2.3.1 output structured JSON.
lindorm-cli --format json --execute "DROP TABLE sensor" 2>/tmp/lindorm_err.txt
rc=$?
if [ $rc -ne 0 ]; then
  echo "Blocked (expected): $(cat /tmp/lindorm_err.txt)" >&2
fi
```

### Batch Export + Data Pipeline

```bash
#!/bin/bash
set -euo pipefail

# Export the latest 24 hours of data as CSV.
lindorm-cli --format csv \
  --execute "SELECT device_id, ts, temperature, humidity FROM sensor WHERE ts > NOW() - INTERVAL 24 HOUR" \
  --output ./recent_data.csv

echo "Exported to recent_data.csv" >&2
wc -l ./recent_data.csv >&2

# Use Python for secondary filtering. JSON structure: {"columns":[...], "rows":[...]}.
lindorm-cli --format json --max-rows 5000 \
  --execute "SELECT * FROM sensor WHERE temperature > 30" \
  2>/dev/null | python3 -c "
import sys,json; d=json.load(sys.stdin)
cols=d['columns']; hi=cols.index('humidity')
filtered=[r for r in d['rows'] if r[hi] and r[hi]>60]
print(json.dumps({'columns':cols,'rows':filtered}, indent=2, ensure_ascii=False))
"
```

### Multi-Database Operations

```bash
#!/bin/bash
set -euo pipefail

for db in db_prod db_staging db_test; do
  echo "=== $db ===" >&2
  lindorm-cli --database "$db" --format json \
    --execute "SHOW TABLES" 2>/dev/null | python3 -c "
import sys,json; d=json.load(sys.stdin)
for row in d['rows']: print(row[0])
" 2>/dev/null || true
done
```

---

## TSDB Time Series Engine Connection

For complete SQL operations of the time series engine, including table creation, writes, and time range queries, see [sql-operations.md](../01-dev/sql-operations.md#tsdb-time-series-engine-sql-operations).

CLI command for connecting to the time series engine:

```bash
# Connect to the time series engine. Avatica protocol, fixed port 8242.
lindorm-cli --url 'jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242' \
  --username root --password-stdin

# Query with specified time precision.
lindorm-cli --url 'jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242' \
  --username root --password-stdin \
  --precision ms \
  --format json --execute "SELECT * FROM ts_test" 2>/dev/null
```

---

## Safe Mode

Enable it with `--safe-mode`. It automatically intercepts the following high-risk SQL operations:

| Intercepted Operation |
|-------------|
| `TRUNCATE TABLE` |
| `DROP TABLE` |
| `OFFLINE TABLE` |
| `DELETE FROM` |
| `DROP DATABASE` |

It can also be enabled through an environment variable: `export LINDORM_SAFE_MODE=true`

> Safe mode automatically removes SQL comments and normalizes whitespace before matching, so it cannot be bypassed by injecting comments.

### Double Check Protocol, Agent + CLI Dual Protection

The Agent and `--safe-mode` together form two independent security defenses. The Agent is responsible for confirming user intent, while CLI `--safe-mode` is responsible for tool-level interception. **Both defenses must be triggered in sequence. Do not skip either one.**

**Complete flow**:

```text
User requests a destructive operation, such as DROP TABLE.
│
├─ First defense: Agent confirms intent.
│   Agent asks the user whether they really want to execute the operation.
│   └─ User confirms -> Continue.
│
├─ Second defense: CLI --safe-mode interception.
│   Agent executes with --safe-mode -> CLI intercepts and returns an error.
│   └─ Agent reports the interception information to the user and asks for confirmation again:
│      "lindorm-cli safe mode has intercepted this operation. Do you want to remove --safe-mode protection and execute it again?"
│   └─ User confirms for the second time -> Continue.
│
└─ Execute: Agent removes --safe-mode and executes the SQL again.
```

**Agent behavior rules**:

1. **Do not proactively remove `--safe-mode`**: Even if the user has confirmed intent in the first defense, the first execution **must** still include `--safe-mode`.
2. **Report after interception**: After receiving a safe-mode interception error, the Agent must show the error information to the user and explicitly state that "this is the CLI safe-mode protection mechanism".
3. **Remove only after second confirmation**: The Agent may remove `--safe-mode` and execute again only after the user gives explicit second confirmation on the safe-mode interception information.
4. **Single-use authorization**: Each authorization to remove `--safe-mode` applies only to the current operation. Subsequent operations must restore `--safe-mode`.

**Example interaction**:

```text
User: Delete the device_sensor table.
Agent: This is a destructive operation and data cannot be recovered after deletion. Confirm that you want to delete the device_sensor table?
User: Confirmed.
Agent: [Executes DROP TABLE with --safe-mode -> intercepted]
Agent: lindorm-cli safe mode intercepted the DROP TABLE operation. Do you want to remove --safe-mode protection and execute it again?
User: Yes, execute it.
Agent: [Removes --safe-mode and executes DROP TABLE -> succeeded]
```

---

## Lindorm CLI Limitations

1. **The wide table engine uses the MySQL protocol**: The wide table engine connects through MySQL port 33060 for better ecosystem compatibility, while the time series engine connects through Avatica port 8242.
2. **CREATE TABLE syntax**: Inline `PRIMARY KEY` must be used and cannot be written as an independent clause.
3. **JSON format encoding**: In versions >= 2.3.1, VARCHAR is output as plaintext. In versions <= 2.3.0, VARCHAR is output as base64. The Agent should use `--tool-schema` to get the version number and decide how to handle it.
4. **Non-interactive mode**: `--execute` mode executes one command each time, unless `--splitCommand` is used. Use pipelines or multiple calls for multi-command workflows.
5. **Character encoding**: lindorm-cli outputs UTF-8.
6. **NULL value display**: The MySQL protocol displays NULL as `\N` by default. It can be customized as an empty string through `--nullString ""`.
7. **Timeout settings**: The default connection timeout is 30 seconds. For large queries, extend it with `--connectTimeout 60s`.

---

## References

- Official wide table engine documentation: https://help.aliyun.com/zh/lindorm/user-guide/use-lindorm-cli-to-connect-to-and-use-lindormtable
- Official time series engine documentation: https://help.aliyun.com/zh/lindorm/user-guide/use-lindorm-cli-to-connect-to-and-use-lindorm-tsdb
