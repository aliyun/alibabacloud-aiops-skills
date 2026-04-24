# Acceptance Criteria: sls-query-analysis

**Scenario**: SLS Log Query & Analysis
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Invocation Patterns

### 1. Command Format — verify product and API name

#### CORRECT

```bash
aliyun sls get-logs-v2 \
  --project my-project \
  --logstore my-logstore \
  --from 1740000000 \
  --to 1740003600 \
  --query '* and status: "500"' \
  --line 100
```

#### INCORRECT — Wrong product name

```bash
aliyun log get-logs-v2 --project my-project --logstore my-logstore
```

**Why**: Product name is `sls`, not `log`, `logservice`, `aliyunlog`, or `aliyun-sls`.

### 2. Parameter Format

#### CORRECT — Kebab-case CLI sub-command and flags

```bash
aliyun sls get-logs-v2 \
  --project my-project \
  --logstore my-logstore \
  --from 1740000000 \
  --to 1740003600 \
  --query '* | select count(*) as total from log' \
  --line 100 \
  --offset 0 \
  --reverse true
```

#### INCORRECT — PascalCase sub-command or flags

```bash
# Sub-command in PascalCase
aliyun sls GetLogsV2 --project my-project --logstore my-logstore
aliyun sls GetIndex  --project my-project --logstore my-logstore

# Flags in PascalCase
aliyun sls get-logs-v2 --Project my-project --Logstore my-logstore --From 1740000000 --To 1740003600
```

**Why**: The SLS plugin uses **kebab-case** for both sub-commands (`get-logs-v2`, `get-index`) and flags (`--project`, `--logstore`, `--from`, `--to`, `--query`).

#### INCORRECT — Using `--region-id` instead of `--region`

```bash
aliyun sls get-logs-v2 --region-id cn-hangzhou --project p --logstore l --from 1 --to 2
```

**Why**: The CLI global flag is `--region`, not `--region-id`.

#### INCORRECT — JSON `--params` string (old SDK pattern)

```bash
aliyun sls get-logs-v2 --params '{"Project":"my-project","Logstore":"my-logstore","From":"1740000000","To":"1740003600"}'
```

**Why**: The CLI takes individual flags, not a JSON `--params` blob.

### 3. Authentication — never expose credentials

#### CORRECT — Verify credential profile via default credential chain

```bash
aliyun configure list
```

#### INCORRECT — Passing AK/SK directly in the command

```bash
aliyun sls get-logs-v2 \
  --access-key-id LTAI5tXXXX \
  --access-key-secret 8dXXXX \
  --project p --logstore l --from 1740000000 --to 1740003600
```

**Why**: Credentials must come from the configured profile, environment variables, STS, or RAM role — never be typed into the command line.

#### INCORRECT — Reading or printing raw credentials

```bash
aliyun configure get           # FORBIDDEN: may expose credential details
cat ~/.aliyun/config.json      # FORBIDDEN: may expose credential details
```

#### INCORRECT — Any command that prints environment credentials

```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID       # FORBIDDEN: example of secret output
printenv | grep -i credential           # FORBIDDEN: may reveal secrets
env | grep -i access_key                # FORBIDDEN: may reveal secrets
```

### 4. API Names — verify exact sub-command

#### CORRECT

```
get-logs-v2      # OpenAPI Action: GetLogsV2
get-index        # OpenAPI Action: GetIndex
```

#### INCORRECT

```
GetLogsV2          # PascalCase is the Action name, not the CLI sub-command
GetIndex           # PascalCase is the Action name, not the CLI sub-command
getLogsV2          # Wrong casing
get_logs_v2        # Wrong separator (snake_case)
getlogsv2          # Missing separators
get-logs           # Deprecated — use get-logs-v2
get-logs-2         # Wrong suffix (v2, not 2)
describe-index     # Wrong verb — SLS uses get-, not describe-
get-log-index      # Not a real sub-command — use get-index
```

### 5. Region Parameter

#### CORRECT

```bash
--region cn-hangzhou
--region cn-shanghai
--region ap-southeast-1
--region us-west-1
```

#### INCORRECT

```bash
--region hangzhou       # Missing country prefix
--region cn-hangzhou-1  # Not a real region ID
```

**Why**: Only valid Alibaba Cloud region IDs are accepted (e.g., `cn-hangzhou`, `ap-southeast-1`). The project is region-scoped — a region mismatch returns `ProjectNotExist`.

### 6. Time Parameters

#### CORRECT — Unix timestamp in seconds

```bash
--from 1711324800 --to 1711411200
```

#### INCORRECT — Millisecond timestamps

```bash
--from 1711324800000 --to 1711411200000
```

**Why**: `--from` / `--to` are Unix **seconds**, not milliseconds.

#### INCORRECT — Date or ISO strings

```bash
--from "2024-03-25"             --to "2024-03-26"
--from "2024-03-25T00:00:00Z"   --to "2024-03-26T00:00:00Z"
```

**Why**: Only integer seconds are accepted; date strings must be converted first (e.g., `date -d "2024-03-25 00:00:00 UTC" +%s`).
