---
name: alibabacloud-waf-billing-backup
description:
  Query and back up Alibaba Cloud WAF 3.0 billing data. Use this Skill when a
  user asks to check WAF bills, export WAF cost details, back up WAF billing
  data locally, or analyze daily/hourly SeCU and Credit usage. The Skill
  retrieves instance information, daily bill summaries, and hourly cost
  breakdowns (function fees, traffic processing fees, Credit usage) via
  aliyun-cli, then exports the results as JSON and CSV files to the local
  workspace.
metadata:
  author: aes-sec-skills
  license: MIT
  compatibility:
    - aliyun-cli >= 3.3.3
    - WAF 3.0 postpaid or prepaid instance
---

# WAF 3.0 Billing Query and Local Backup

> **Read-only Skill**: This Skill only invokes Describe/List read-only APIs. Any Create/Modify/Delete/Release operation is strictly prohibited.

Query Alibaba Cloud WAF 3.0 billing data via OpenAPI. This Skill supports:
- Retrieving WAF instance ID and region information
- Querying daily bill summaries for pay-as-you-go instances (SeCU / Credit / cost)
- Drilling down into hourly function fees, traffic processing fees, and Credit usage details
- Querying elastic postpaid bills for prepaid instances (optional)
- Exporting raw data and summary reports as local JSON / CSV backups

---

## Prerequisites

### 1. Dependency Check

Verify the `aliyun-cli` version:

```bash
aliyun version
```

Version >= 3.3.3 is required. If it is not installed or the version is too low, refer to [references/cli-installation-guide.md](references/cli-installation-guide.md).

### 2. Credential Configuration Check

Security rules:
- Never read, echo, or print AK/SK values
- Never read or cat credential files (e.g., `~/.aliyun/config.json`)
- Never ask users to enter AK/SK directly in conversation or on the command line
- Never use `aliyun configure set` with plaintext credential values
- Only `aliyun configure list` is allowed to check credential status

```bash
aliyun configure list
```

If no valid configuration exists, prompt the user to configure credentials before retrying. Reference: https://help.aliyun.com/zh/cli/configure-credentials

### 3. RAM Permissions

This Skill requires read-only WAF permissions. See [references/ram-policies.md](references/ram-policies.md) for the full minimum RAM policy.

### 4. CLI Global Parameters

All `aliyun` commands must include:

```
--version 2021-10-01 --force --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills
```

---

## Core Workflow

### Step 1: Retrieve WAF Instance Information

```bash
aliyun waf-openapi describe-instance \
  --version 2021-10-01 --force \
  --region cn-hangzhou \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

Extract from the returned JSON:
- `InstanceId`: WAF instance ID
- `RegionId`: instance region (`cn-hangzhou` for Mainland China, `ap-southeast-1` for outside Mainland China)

Region selection rules:
1. If the user explicitly provides a region (e.g., "my instance is in ap-southeast-1"), use that region first.
2. If no region is given, first try `--region cn-hangzhou`.
3. If `cn-hangzhou` returns an empty instance, retry with `--region ap-southeast-1`.
4. If the user asks to check a specific region first and the instance is not found there, retry the other region.

Always record the final `RegionId` actually used for subsequent bill queries.

### Step 2: Determine Instance Billing Type and Query Time Range

Determine the instance type from the `PayType` field returned by `describe-instance`:
- `POSTPAY`: pay-as-you-go instance; use `describe-postpay-bills` / `describe-elastic-bills`
- `PREPAY`: subscription instance; for elastic postpaid bills use `describe-prepay-daily-bills`

Default time-range rules:
- If not specified, query the last 7 days
- For "today's estimated bill", use 00:00:00 today to the last complete hour

> **Important reminder**: WAF 3.0 pay-as-you-go bills are settled on a **T+1** basis. If the query range includes today, only the estimated bill up to the last complete hour can be retrieved. The final bill for today will be generated on the next day. Before execution, inform the user: "Data for today is an estimated bill; the final bill is subject to T+1 actual settlement."
>
> **T+1 auto-adjustment rule**: If the user's request is about "today" or the natural query range ends on today, you must adjust the bill query to **yesterday** (00:00:00 yesterday to 23:59:59 yesterday) and clearly state: "Because WAF 3.0 pay-as-you-go bills are settled on a T+1 basis, today's final bill is not yet available. I have adjusted the query to yesterday's final bill." Do not query today's data as the final answer unless the user explicitly asks for an estimated bill.

Calculate Unix timestamps (seconds, UTC):

```bash
# Last 7 days
START_TS=$(date -u -v-7d +%s)
END_TS=$(date -u +%s)

# Specific date (macOS)
START_TS=$(date -u -j -f '%Y-%m-%d %H:%M:%S' '2026-08-23 00:00:00' +%s)
END_TS=$(date -u -j -f '%Y-%m-%d %H:%M:%S' '2026-08-23 23:59:59' +%s)

# Linux alternative
# START_TS=$(date -u -d '2026-08-23 00:00:00' +%s)
# END_TS=$(date -u -d '2026-08-23 23:59:59' +%s)
```

### Step 3: Query Daily Bill Summary

Suitable for the "bill list" view. For daily granularity, do **not** pass `PeriodType`; the API defaults to daily aggregation:

```bash
aliyun waf-openapi describe-postpay-bills \
  --version 2021-10-01 --force \
  --region <RegionId> \
  --InstanceId <InstanceId> \
  --StartTime <START_TS> \
  --EndTime <END_TS> \
  --MaxResults 100 \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

The returned `BillDetail` array contains daily `Cu`, `TrafficCu`, `FunctionCu`, `Credit`, `ChargeData`, etc.

### Step 4: Query Hourly Function Fee / Credit Details

Corresponds to the console "View Details → Hourly Cost Details". You **must** explicitly pass `--PeriodType hour` to retrieve hourly breakdowns. Omitting this parameter may return daily data instead of hourly data:

```bash
aliyun waf-openapi describe-postpay-bills \
  --version 2021-10-01 --force \
  --region <RegionId> \
  --InstanceId <InstanceId> \
  --StartTime <START_TS> \
  --EndTime <END_TS> \
  --PeriodType hour \
  --MaxResults 24 \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Important**: Always invoke this as a **separate call** from the daily summary query. The daily summary (Step 3) and the hourly details (Step 4) must be **two distinct `aliyun` commands**. The only difference from Step 3 is the addition of `--PeriodType hour`. Do not rely on the API default granularity for hourly details; explicitly pass `--PeriodType hour` every time hourly breakdown is required.

For each returned record:
1. Parse `ChargeData` (JSON string) to obtain SeCU function/traffic usage details
2. Parse `CreditChargeData` (JSON string) to obtain Credit usage details
3. Convert usage to cost according to pricing rules

### Step 5: Cost Conversion

| Metering Unit | Unit Price |
| --- | --- |
| **SeCU** | 0.05 CNY / SeCU |
| **Credit** | 100 Credit = 1 CNY |

Cost for a single record:
```
Cost(CNY) = Cu * 0.05 + Credit * 0.01
```

> Except for the WAF instance fee, SeCU is counted per full hour and rounded up. The WAF instance fee is billed at the actual rate of 0.5 SeCU/hour.

### Step 6: Local Backup

Backup directories are organized in a **year/month/day** hierarchy for long-term archiving:

```
waf-billing-backups/
├── 2026/
│   ├── 08/
│   │   ├── 23/
│   │   │   ├── waf-billing-raw-20260823-2047.json
│   │   │   ├── waf-billing-daily-20260823-2047.csv
│   │   │   ├── waf-billing-hourly-20260823-2047.csv
│   │   │   └── waf-billing-chargedata-20260823-2047.csv
│   │   └── 24/
│   │       └── ...
```

Example of generating directories and saving files (macOS/Linux):

```bash
# Directory hierarchy based on the query end date
BACKUP_YEAR=$(date -u -r <END_TS> +%Y)
BACKUP_MONTH=$(date -u -r <END_TS> +%m)
BACKUP_DAY=$(date -u -r <END_TS> +%d)
BACKUP_DIR="./waf-billing-backups/${BACKUP_YEAR}/${BACKUP_MONTH}/${BACKUP_DAY}"
mkdir -p "$BACKUP_DIR"

# File name timestamp
TIMESTAMP=$(date -u +%Y%m%d-%H%M)

# Save raw API response
aliyun ... > "${BACKUP_DIR}/waf-billing-raw-${TIMESTAMP}.json"

# Summary CSV example columns
# date,hour,cu,traffic_cu,function_cu,credit,traffic_credit,function_credit,cost_rmb
```

> **Linux alternative**: `date -u -d @<END_TS> +%Y/%m/%d`

Backup file naming convention:
- Raw response: `waf-billing-raw-{YYYYMMDD-HHMM}.json`
- Daily summary: `waf-billing-daily-{YYYYMMDD-HHMM}.csv`
- Hourly details: `waf-billing-hourly-{YYYYMMDD-HHMM}.csv`
- Function fee details: `waf-billing-chargedata-{YYYYMMDD-HHMM}.csv`

---

## Output Format

### Terminal Summary

Output a Markdown summary to the user:

```markdown
## WAF 3.0 Billing Summary

- **Instance ID**: {InstanceId}
- **Query Range**: {START} ~ {END}
- **Total SeCU**: {total_cu}
- **Total Credit**: {total_credit}
- **Estimated Total Cost**: {total_cost} CNY

### Daily Summary

| Date | SeCU | Credit | Cost(CNY) |
| --- | --- | --- | --- |
| 2026-08-23 | 1184 | 0 | 59.20 |
| ... | ... | ... | ... |

### Local Backup Files

- `waf-billing-raw-20260824-2047.json`
- `waf-billing-daily-20260824-2047.csv`
- `waf-billing-hourly-20260824-2047.csv`
```

### Error Handling

| Scenario | Detection | Handling |
| --- | --- | --- |
| Missing/invalid credentials | `InvalidAccessKeyId.NotFound`, `SignatureDoesNotMatch` | Prompt user to check `aliyun configure list` |
| Insufficient RAM permissions | `Forbidden.RAM`, `NoPermission` | Prompt user to add permissions from [references/ram-policies.md](references/ram-policies.md) |
| Instance does not exist | Empty `InstanceId` returned | Retry with another `--region` or confirm the instance is activated |
| Invalid time range | `InvalidParameter` | Check `StartTime` / `EndTime` are Unix timestamps in seconds |
| Query range includes today | `EndTime` >= 00:00:00 today | Inform user: "Today is an estimated bill; the final bill is subject to T+1 settlement" |
| Throttling | `Throttling` | Wait 2 seconds and retry, up to 3 times |

---

## Observability

All `aliyun` CLI commands invoked by this Skill must include the following User-Agent header template:

```
--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}
```

At runtime, replace the placeholders:
- `{SKILL_NAME}` → `alibabacloud-waf-billing-backup`
- `{session-id}` → a unique 32-character hexadecimal identifier for the current Skill execution session

### Session-ID Rules

- **Format**: strictly a 32-character hexadecimal string (e.g., `a1b2c3d4e5f678901234567890123456`).
- **Generation**: generate exactly once per Skill execution session using a cryptographically secure random source.
- **Consistency**: the same `session-id` must be reused across **all** API calls within a single Skill execution.
- **Scope**: do not reuse a session-id across different Skill executions.
- **Security**: do not include any user identity, AK/SK, or sensitive metadata in the UA string.

---

## References

| Reference | Description |
| --- | --- |
| `references/cli-installation-guide.md` | aliyun-cli installation and configuration guide |
| `references/ram-policies.md` | Minimum RAM permissions required |
| `references/billing-fields-reference.md` | Billing field and cost item mapping |
| `related_apis.yaml` | OpenAPI list invoked by this Skill |
