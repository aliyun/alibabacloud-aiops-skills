---
name: alibabacloud-waf-security-monitor
description: |
  Perform security inspection and monitoring for Alibaba Cloud WAF (Web Application Firewall),
  covering CNAME-based domain access, hybrid cloud access, and cloud product access assets.
  Supports querying Web attacks, CC attacks, Bot attacks, API security events, traffic analysis
  (QPS/bandwidth), HTTP status code anomalies (4xx/5xx period-over-period), protection status,
  certificate expiry, and instance asset inventory. Use this Skill when users need WAF security
  inspection, protection status checks, attack event queries, traffic anomaly investigation,
  or to confirm whether WAF products are provisioned.
  Triggers: "WAF inspection", "WAF security check", "Web attack query", "traffic anomaly", "certificate check"
---

# WAF Security Product Inspection & Monitoring

This skill performs comprehensive security inspection for Alibaba Cloud WAF 3.0 instances across both business regions (cn-hangzhou and ap-southeast-1). It covers asset inventory (CNAME domains, cloud product access, SSL certificates), attack event statistics (Bot/CC via bot_manager templates), traffic analysis (QPS/bandwidth with period-over-period), HTTP status code anomaly detection (4xx/5xx), and protection status checks (alarms, DDoS, pause status). Outputs a structured inspection report following a standardized template.

**Architecture**: `waf-openapi (WAF 3.0) -> aliyun CLI plugin mode (kebab-case) -> Dual-Region Inspection -> Structured Report`

## Pre-checks

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**Pre-check: Script dependencies**
> Scripts in `scripts/` require Python 3 (standard library only, no third-party packages).
> See `scripts/requirements.txt` for details.

## Observability Initialization (MUST run before any command)

```bash
if [ -z "$SKILL_SESSION_ID" ]; then
  export SKILL_SESSION_ID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null | tr -d '-' || uuidgen | tr -d '-' | tr 'A-F' 'a-f')"
fi
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-waf-security-monitor/${SKILL_SESSION_ID}"
export ALIBABA_CLOUD_OTEL_TRACEPARENT="00-${SKILL_SESSION_ID}-01"
export ALIBABA_CLOUD_OTEL_BAGGAGE="skill=alibabacloud-waf-security-monitor,source=agent-skills"
```

Do not skip, alter formats, or place PII in baggage.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Policy

All permissions are **read-only** (Describe/List only). See [references/ram-policies.md](references/ram-policies.md) for the full policy JSON.

| Category | API Actions | Type |
|----------|------------|------|
| Asset Management | DescribeInstance, DescribeDomains, DescribeCloudResourceList | Read-only |
| Attack Events | DescribeDefenseRuleStatistics, DescribeApisecEvents | Read-only |
| Traffic Analysis | DescribeFlowChart, DescribePeakTrend, DescribeFlowTopResource, DescribeFlowTopUrl | Read-only |
| Status Codes | DescribeResponseCodeTrendGraph | Read-only |
| Protection Status | DescribePauseProtectionStatus, DescribeAlarmList, DescribeDDoSStatus | Read-only |
| Certificates | DescribeCerts | Read-only |
| Defense | DescribeDefenseTemplates, DescribeMajorProtectionBlackIps | Read-only |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** -- Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default Value |
|-----------|-------------------|-------------|---------------|
| Time range | Optional | Inspection time window | Last 24 hours |
| Comparison mode | Optional | Period-over-period baseline | Day-over-day |
| Region scope | Optional | Which WAF regions to inspect | Both cn-hangzhou and ap-southeast-1 |

> **Note: InstanceId is auto-discovered — no user input needed.** Phase 1 calls `describe-instance` for each region to obtain the WAF InstanceId automatically. All subsequent API calls use the discovered value. Users never need to provide `--instance-id` manually.

## Core Inspection Workflow

> **Execution guidance**:
> - **Region rules**: WAF 3.0 has only two business regions: `cn-hangzhou` and `ap-southeast-1`. Query both independently -- each has its own InstanceId. Use `--region` flag only (`--region-id` causes "unknown flag" errors, `--biz-region-id` does not route correctly). See [API Reference](references/api-reference.md).
> - **User-Agent per command**: Every `aliyun waf-openapi` CLI call MUST include `--user-agent "$ALIBABA_CLOUD_USER_AGENT"` flag (set during Observability Initialization).
> - **Same shell session for Phase 1-2-3-4**: Variables like `REGION_INSTANCES`, `BASE_START`, `EFFECTIVE_BOT_ID` are shared across phases. Splitting into separate shells loses these values and causes undefined-variable errors.
> - Run each code block via bash. Do not just describe/plan.
> - Use `RESULT` as the variable name for API call outputs, because the verification script (`scripts/verify_output.py`) and the log aggregation pattern depend on consistent variable naming.
> - Append every `aliyun waf-openapi` output to `/tmp/waf_skill_output.log` -- the verification script in Phase 4.7 parses this single file for completeness checks.
> - On error: report to user and continue. On empty result: report "0" -- do not omit the section.

### Phase 1-2-3: Environment, Assets & Timestamps (SINGLE BLOCK)

```bash
# === Phase 1: Heartbeat ===
HEARTBEAT_CN=$(aliyun waf-openapi describe-instance \
  --region cn-hangzhou --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$HEARTBEAT_CN" > /tmp/waf_skill_output.log
HEARTBEAT_INTL=$(aliyun waf-openapi describe-instance \
  --region ap-southeast-1 --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$HEARTBEAT_INTL" >> /tmp/waf_skill_output.log

# Setup
aliyun version
aliyun configure set --auto-plugin-install true --connect-timeout 10 --read-timeout 30 2>/dev/null || true
aliyun plugin update 2>/dev/null || true

# === Phase 2.1: Instance discovery (from heartbeat, no redundant calls) ===
declare -A REGION_INSTANCES
for region in cn-hangzhou ap-southeast-1; do
  if [ "$region" = "cn-hangzhou" ]; then RAW="$HEARTBEAT_CN"; else RAW="$HEARTBEAT_INTL"; fi
  IDS=$(echo "$RAW" | python3 -c "
import sys,json,re
raw=sys.stdin.read()
raw=re.sub(r'[\x00-\x1f\x7f]','',raw)
try:
  d=json.loads(raw)
  if 'InstanceId' in d: print(d['InstanceId'])
except:
  for line in raw.splitlines():
    if '\"InstanceId\"' in line and 'waf_' in line:
      print(line.split('\"InstanceId\"')[1].split('\"')[1]); break
" 2>/dev/null)
  REGION_INSTANCES[$region]="$IDS"
  echo "[MAPPING] $region -> $IDS"
done
echo "[CHECK] cn-hangzhou=${REGION_INSTANCES[cn-hangzhou]} | ap-southeast-1=${REGION_INSTANCES[ap-southeast-1]}"

# DEGRADED FALLBACK
[ -z "${REGION_INSTANCES[cn-hangzhou]}" ] && REGION_INSTANCES[cn-hangzhou]="UNKNOWN" && echo "[DEGRADED] cn-hangzhou=UNKNOWN"
[ -z "${REGION_INSTANCES[ap-southeast-1]}" ] && REGION_INSTANCES[ap-southeast-1]="UNKNOWN" && echo "[DEGRADED] ap-southeast-1=UNKNOWN"

# === Phase 2.2: Domains (use page-size 10 -- larger values like 100 trigger API parameter errors) ===
for region in cn-hangzhou ap-southeast-1; do
  for instance_id in ${REGION_INSTANCES[$region]}; do
    RESULT=$(aliyun waf-openapi describe-domains \
      --instance-id $instance_id --region $region \
      --page-number 1 --page-size 10 \
      --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
    echo "$RESULT" >> /tmp/waf_skill_output.log
  done
done

# === Phase 2.3: Cloud resources + Certificates ===
for region in cn-hangzhou ap-southeast-1; do
  for instance_id in ${REGION_INSTANCES[$region]}; do
    RESULT=$(aliyun waf-openapi describe-cloud-resource-list \
      --instance-id $instance_id --region $region \
      --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
    echo "$RESULT" >> /tmp/waf_skill_output.log
    # Cross-region mismatch detection: flag resources whose ResourceRegionId != WAF instance region
    echo "$RESULT" | python3 scripts/detect_region_mismatch.py \
      --region "$region" --instance-id "$instance_id" >> /tmp/waf_skill_output.log
    RESULT=$(aliyun waf-openapi describe-certs \
      --instance-id $instance_id --region $region \
      --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
    echo "$RESULT" >> /tmp/waf_skill_output.log
  done
done

# === Phase 3: Timestamps ===
if [ -n "$BASE_END" ] && ! echo "$BASE_END" | grep -qE '^[0-9]+$'; then
  echo "[ERROR] BASE_END is not a valid integer: $BASE_END"; exit 1
fi
if [ -n "$BASE_START" ] && ! echo "$BASE_START" | grep -qE '^[0-9]+$'; then
  echo "[ERROR] BASE_START is not a valid integer: $BASE_START"; exit 1
fi
BASE_END=${BASE_END:-$(date +%s)}; BASE_START=${BASE_START:-$((BASE_END - 86400))}
COMPARE_END=$((BASE_START)); COMPARE_START=$((COMPARE_END - (BASE_END - BASE_START)))
echo "[TIMESTAMP] BASE=$BASE_START~$BASE_END COMPARE=$COMPARE_START~$COMPARE_END"
echo "[PHASE 1-2-3 DONE] Instances: cn-hangzhou=${REGION_INSTANCES[cn-hangzhou]} ap-southeast-1=${REGION_INSTANCES[ap-southeast-1]}"
```

> **Abort rule**: Per-region independent. cn-hangzhou fail does not mean skip ap-southeast-1.
> Only terminate on `InvalidAccessKeyId` (credential problem affects all regions). Otherwise use degraded mode with UNKNOWN placeholder.

### Phase 4: Inspection (Per-Region, Per-Instance)

> **All code blocks 4.1-4.5 should execute regardless of prior results**, because each inspection dimension is independent.
> - Error in call N: log the error and immediately execute call N+1.
> - Every call must include `--user-agent "$ALIBABA_CLOUD_USER_AGENT"` flag.
> - Every call: `RESULT=$(aliyun waf-openapi <cmd> --region $region --user-agent "$ALIBABA_CLOUD_USER_AGENT" ... 2>&1); echo "$RESULT" >> /tmp/waf_skill_output.log`
> - Loop: `for region in cn-hangzhou ap-southeast-1; do for instance_id in ${REGION_INSTANCES[$region]}; do`
> - After each region completes 4.1-4.5, print: `echo "[CHECKPOINT] region=$region ALL phases done"`
> - Do not use break/continue/return inside the region loop.

#### 4.1 Defense Templates

> Use python3 for JSON extraction (not grep/sed/awk/bash string ops). See [Defense Templates Guide](references/defense-templates.md).

```bash
RESULT=$(aliyun waf-openapi describe-defense-templates \
  --instance-id $instance_id --region $region \
  --page-number 1 --page-size 50 \
  --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$RESULT" >> /tmp/waf_skill_output.log

BOT_TEMPLATE_ID=$(echo "$RESULT" | python3 scripts/extract_bot_template.py 2>/dev/null)
if ! echo "$BOT_TEMPLATE_ID" | grep -qE '^[0-9]+$'; then BOT_TEMPLATE_ID=""; fi
EFFECTIVE_BOT_ID="${BOT_TEMPLATE_ID:-0}"
echo "[TEMPLATE] BOT=$EFFECTIVE_BOT_ID region=$region"
```

> - `describe-defense-rule-statistics` only supports `bot_manager`. Other scenes return `DefenseSceneNotSupported`.
> - Empty template-id: use `0` fallback (ensures call reaches server; server returns "template not found" which gets logged).

#### 4.2 Attack Events (3 calls per instance)

> **CC Detection Mapping**: CC attack data comes from `describe-defense-rule-statistics` (primary-key=scene/action/status).
> If the API returns empty, write "CC/Bot attacks: 0 (no block records in this period)" -- avoid writing "not detected" which implies active detection occurred.

```bash
for key in scene action status; do
  RESULT=$(aliyun waf-openapi describe-defense-rule-statistics \
    --instance-id $instance_id --primary-key $key \
    --template-id $EFFECTIVE_BOT_ID --region $region \
    --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
  echo "$RESULT" >> /tmp/waf_skill_output.log
done
RESULT=$(aliyun waf-openapi describe-apisec-events \
  --instance-id $instance_id --region $region \
  --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$RESULT" >> /tmp/waf_skill_output.log
RESULT=$(aliyun waf-openapi describe-major-protection-black-ips \
  --instance-id $instance_id --region $region \
  --page-number 1 --page-size 50 \
  --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$RESULT" >> /tmp/waf_skill_output.log
```

#### 4.3 Traffic (base + compare, both required)

```bash
for api in describe-flow-chart describe-peak-trend; do
  RESULT=$(aliyun waf-openapi $api \
    --instance-id $instance_id --region $region \
    --start-timestamp $BASE_START --end-timestamp $BASE_END --interval 300 \
    --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
  echo "$RESULT" >> /tmp/waf_skill_output.log
done
# COMPARE period (execute even if base returned empty)
for api in describe-flow-chart describe-peak-trend; do
  RESULT=$(aliyun waf-openapi $api \
    --instance-id $instance_id --region $region \
    --start-timestamp $COMPARE_START --end-timestamp $COMPARE_END --interval 300 \
    --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
  echo "$RESULT" >> /tmp/waf_skill_output.log
done
RESULT=$(aliyun waf-openapi describe-flow-top-resource \
  --instance-id $instance_id --region $region \
  --start-timestamp $BASE_START --end-timestamp $BASE_END \
  --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$RESULT" >> /tmp/waf_skill_output.log
RESULT=$(aliyun waf-openapi describe-flow-top-url \
  --instance-id $instance_id --region $region \
  --start-timestamp $BASE_START --end-timestamp $BASE_END \
  --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
echo "$RESULT" >> /tmp/waf_skill_output.log
echo "[SELF-CHECK-4.3] region=$region BASE+COMPARE flow calls done."
```

#### 4.4 HTTP Status Codes (4 calls per region: 2 types x 2 periods)

```bash
for type_val in waf upstream; do
  for start_ts end_ts in $BASE_START $BASE_END $COMPARE_START $COMPARE_END; do
    RESULT=$(aliyun waf-openapi describe-response-code-trend-graph \
      --instance-id $instance_id --region $region \
      --start-timestamp $start_ts --end-timestamp $end_ts \
      --interval 300 --type $type_val \
      --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
    echo "$RESULT" >> /tmp/waf_skill_output.log
  done
done
echo "[CHECKPOINT-4.4] region=$region status_code_calls=4."
```

#### 4.5 Protection Status

```bash
for api in describe-pause-protection-status describe-alarm-list describe-ddos-status; do
  RESULT=$(aliyun waf-openapi $api \
    --instance-id $instance_id --region $region \
    --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1)
  echo "$RESULT" >> /tmp/waf_skill_output.log
done
echo "[CHECKPOINT] region=$region ALL phases done"
```

> Cert threshold: <7d=Critical, <30d=Warning, >=30d=Normal. Data from Phase 2.3 describe-certs (do not re-call).

#### 4.6 Period-over-Period

Change rate = (Base - Compare) / Compare x 100%. Thresholds: +/-50-100%=Attention, >+/-100%=Anomaly.

#### 4.7 Report & Verification

> **Report**: Follow [Report Template](references/report-template.md). Group by Region.
>
> **Cross-Region Mismatch**: After verification, check if the log contains `[REGION_MISMATCH_SUMMARY]` lines. If present, include a "Cross-Region Resource Risk" section in the report listing each mismatched resource. Treat as a configuration risk item in the Conclusion.
>
> **Error vs Empty** -- distinguishing these prevents misrepresenting API failures as "zero incidents":
> - API 200 + `[]` -> `0 (API returned empty)`
> - API error -> `[QUERY FAILED (ErrorCode: XXX)]`
> - Do not write `0` when API returned error.
>
> **Verification** -- run this before writing the report to catch data omissions:
> ```bash
> python3 scripts/verify_output.py /tmp/waf_skill_output.log
> ```
>
> **Report integrity rules**:
> - All report numbers should come from log parsing. Hardcoded values without API source = fabrication.
> - Do not attribute domains across regions.
> - Do not write "attacks detected" when block count = 0.
> - Do not infer specific paths/endpoints not present in API response.
> - If `QUERY FAILED` exceeds 50% of sections, the conclusion should state "incomplete assessment".
> - Every data point should cite its source API.
>
> **Empty-data report rules**:
> - API returns empty array/0: write "No data returned for this period (API returned empty)"
> - Do not write speculative descriptions like "no significant attacks detected", "traffic remained stable"
> - Period-over-period: if base=0 and compare=0, write "Both periods have no data, cannot calculate"
> - Period-over-period: if compare=0 and base>0, write "Compare period has no data, no baseline"
>
> **Cert & Timestamp rules**:
> - Certificate expiry days should reference the `[CERT]` lines output by `scripts/verify_output.py`. Do not compute days-to-expiry via bash arithmetic.
> - Use `python3 datetime` or `date -d @ts` for timestamp-to-date conversion.
> - Before generating the report, cross-check: verify script `[VERIFY] Domains` = report domain list; `[CERT]` count = report certificate count.

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed evaluation layers and pass/fail criteria covering execution evidence, parameter correctness, result handling, and anti-fabrication rules.

## Cleanup

> No explicit cleanup required. All operations are read-only and no resources are provisioned.

## Best Practices

1. Always query both WAF business regions (cn-hangzhou, ap-southeast-1) independently
2. Use `--region` only -- never `--region-id` or `--biz-region-id`
3. Every `aliyun waf-openapi` command must include `--user-agent "$ALIBABA_CLOUD_USER_AGENT"`
4. Use python3 for JSON extraction, never grep/sed/awk on API responses
5. Filter defense templates by `DefenseScene=bot_manager` only -- all other scenes return errors
6. Execute all inspection phases regardless of prior errors -- each dimension is independent
7. Distinguish API errors from empty results in the report
8. Use `scripts/verify_output.py` to validate data completeness before writing the report
9. Never fabricate data -- all numbers must trace to API responses in the log file
10. Execute all inspection phases regardless of prior errors -- each dimension is independent
11. Use `--page-size 10` for describe-domains (larger values trigger API parameter errors)

## References

| Resource | Path |
|----------|------|
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| CLI Setup | [references/cli-setup.md](references/cli-setup.md) |
| RAM Policies | [references/ram-policies.md](references/ram-policies.md) |
| API Reference | [references/api-reference.md](references/api-reference.md) |
| Defense Templates | [references/defense-templates.md](references/defense-templates.md) |
| Report Template | [references/report-template.md](references/report-template.md) |
| CLI Commands | [references/related-commands.md](references/related-commands.md) |
| Verification Method | [references/verification-method.md](references/verification-method.md) |
| Acceptance Criteria | [references/acceptance-criteria.md](references/acceptance-criteria.md) |
