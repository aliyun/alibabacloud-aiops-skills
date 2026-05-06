---
name: alibabacloud-ddos-security-monitor
description: |
  [user] Perform security inspection and monitoring for Alibaba Cloud DDoS security products,
  covering DDoS Basic Protection, DDoS Native Protection, and DDoS Anti-DDoS Pro/Premium.
  Supports querying blackhole/scrubbing events, QPS spikes/drops, L4 traffic anomalies,
  HTTP status code (4xx/5xx) period-over-period surges, origin status code anomalies,
  and instance asset inventory. Use this Skill when users need security inspection,
  DDoS protection status checks, attack event queries, traffic anomaly investigation,
  or to confirm whether DDoS security products are provisioned.
  Triggers: "DDoS inspection", "security check", "DDoS protection check", "attack event query", "traffic anomaly"
---

# DDoS Security Product Inspection & Monitoring

This skill performs security inspection on DDoS security products under an Alibaba Cloud account, entirely through Aliyun CLI direct OpenAPI calls without any scripts or SDKs.

**Architecture**: `antiddos-public (Basic Protection) + ddosbgp (Native Protection) + ddoscoo (Anti-DDoS Pro/Premium) -> CLI OpenAPI -> Inspection Report`

## Product & API Overview

| Product | CLI Code | Use Case |
|---------|----------|----------|
| DDoS Basic Protection | `antiddos-public` | Default free protection for ECS/SLB, Region param: `--ddos-region-id` |
| DDoS Native Protection | `ddosbgp` | Paid upgrade, native IP-level protection, Region param: `--biz-region-id` or `--region` |
| DDoS Anti-DDoS Pro/Premium | `ddoscoo` | Dedicated Anti-DDoS IP, L4/L7 protection, Region param: `--region` |

> **[MUST] Strict product routing isolation**: APIs of the three products MUST NEVER be mixed. NEVER substitute `ddoscoo` APIs for `ddosbgp` queries or vice versa. If mixing is detected, abort immediately.
>
> **[MUST] ddosbgp endpoint routing**: `ddosbgp describe-instance-list` default endpoint does NOT support mainland China Regions. You MUST specify `--endpoint ddosbgp.cn-hangzhou.aliyuncs.com` for ALL `describe-instance-list` calls.
>
> **[MUST] Easily confused API warning**:
>
> | Scenario | Correct Command | Wrong Command (FORBIDDEN) |
> |----------|----------------|--------------------------|
> | **Native Protection** attack events | `ddosbgp describe-ddos-event` (singular) | ~~`ddoscoo describe-ddos-events`~~ |
> | **Anti-DDoS Pro** attack events | `ddoscoo describe-ddos-events` (plural) | ~~`ddosbgp describe-ddos-event`~~ |

## Pre-checks

> **Aliyun CLI >= 3.3.3 required** — see [CLI Installation Guide](references/cli-installation-guide.md).
> **Credentials required** — see [CLI Credential Setup](references/cli-setup.md). Run `aliyun configure list` to verify.
> **RAM permissions** — see [RAM Permission Policies](references/ram-policies.md).
>
> **[MUST] Permission Failure Handling:** On permission errors: 1) Read `references/ram-policies.md` 2) Use `ram-permission-diagnose` skill 3) Pause until user confirms permissions granted.
>
> **[MUST] AI-Mode lifecycle** — Enable before any CLI invocation, disable at EVERY exit point:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddos-security-monitor"
> ```

## Parameter Confirmation

> **IMPORTANT**: ALL user-customizable parameters MUST be confirmed with the user before execution.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| Inspection product scope | Optional | Basic/Native/Anti-DDoS Pro, default all | All |
| Time range | Optional | Inspection time window | Last 24 hours |
| Comparison mode | Optional | Day-over-day / week-over-week / custom | Day-over-day |
| Basic Protection instance-type | Optional | ecs/slb/eip/ipv6/swas/waf/ga_basic | ecs |

## Region Strategy

> **[MUST] ddosbgp Region traversal (dynamic + hardcoded fallback)**:
> - **Hardcoded baseline** (12 Regions, MUST NOT be reduced): `cn-hangzhou cn-shanghai cn-beijing cn-shenzhen cn-hongkong ap-southeast-1 ap-southeast-2 ap-southeast-3 ap-southeast-5 ap-northeast-1 us-west-1 eu-central-1`
> - **Dynamic expansion**: Call `aliyun ddosbgp describe-regions` (NOT ECS), **union** with baseline (only add, never subtract). If dynamic fetch fails, use baseline directly.
> - **Count validation**: Final list >= 12 Regions. ALL must be traversed, NEVER break due to empty/error.
>
> **antiddos-public**: Query from `cn-hangzhou` only (centralized).
> **ddoscoo**: MUST query both `cn-hangzhou` + `ap-southeast-1`.

## Core Inspection Workflow

### Phase 1: Environment, Credential & Permission Pre-check

```bash
# 1.1 Check CLI version + enable AI-Mode
aliyun version
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddos-security-monitor"

# 1.2 Set global timeout and enable auto plugin install
aliyun configure set --auto-plugin-install true --connect-timeout 10 --read-timeout 30
aliyun plugin update

# 1.3 Check credential configuration
aliyun configure list

# 1.4 Validate permissions (one call per product)
aliyun antiddos-public describe-instance-ip-address \
  --ddos-region-id cn-hangzhou --instance-type ecs --current-page 1 --page-size 1
aliyun ddosbgp describe-instance-list --page-no 1 --page-size 1 --region cn-hangzhou --endpoint ddosbgp.cn-hangzhou.aliyuncs.com
aliyun ddoscoo describe-instances --page-number 1 --page-size 1 --region cn-hangzhou
aliyun ddoscoo describe-instances --page-number 1 --page-size 1 --region ap-southeast-1
```

- Normal JSON -> permission OK | `Forbidden.RAM` / `NoPermission` -> see [RAM Policies](references/ram-policies.md)

> **[MUST] Abort rule**: If any pre-check fails 3 consecutive times, run `aliyun configure ai-mode disable`, output error report, and terminate.

### Phase 2: Product Inventory Check (Multi-Region Mandatory Traversal)

> **[MUST] Loop rules**: ALL Regions must be queried. On ANY error (InvalidRegionId/Empty/Throttling), log and `continue` — break/exit is FORBIDDEN. After loop, verify EXECUTED >= 12 (ddosbgp) or = 2 (ddoscoo). Log results immediately after each call — relying on memory is FORBIDDEN.
>
> **Empty result handling**: `Total: 0` → log "no instances", continue | Error code → log error, continue | Normal → extract instance IDs.
> After traversal, compile **Region -> Instance ID list** mapping for Phase 4.

```bash
# 2.1 Basic Protection assets
aliyun antiddos-public describe-instance-ip-address \
  --ddos-region-id cn-hangzhou --instance-type ecs --current-page 1 --page-size 50

# 2.2 Native Protection - [MUST execute full loop in single bash]
BASELINE="cn-hangzhou cn-shanghai cn-beijing cn-shenzhen cn-hongkong ap-southeast-1 ap-southeast-2 ap-southeast-3 ap-southeast-5 ap-northeast-1 us-west-1 eu-central-1"
DYNAMIC=$(aliyun ddosbgp describe-regions 2>/dev/null | grep -o '"RegionId":"[^"]*"' | cut -d'"' -f4 | tr '\n' ' ')
if [ -n "$DYNAMIC" ]; then
  ALL_REGIONS=$(echo "$BASELINE $DYNAMIC" | tr ' ' '\n' | sort -u | tr '\n' ' ')
else
  ALL_REGIONS="$BASELINE"
fi
EXECUTED=0
for region in $ALL_REGIONS; do
  # [MANDATORY] NEVER break/return/exit - on ANY error, MUST continue
  echo "=== ddosbgp query $region ==="
  # [CRITICAL] Must specify --endpoint for mainland China Regions
  RESULT=$(aliyun ddosbgp describe-instance-list --page-no 1 --page-size 50 --region $region --endpoint ddosbgp.cn-hangzhou.aliyuncs.com 2>&1)
  echo "$RESULT"
  if echo "$RESULT" | grep -q "InvalidRegionId\|ErrorCode"; then
    echo "[WARN] $region returned error, logged and continuing"
  fi
  EXECUTED=$((EXECUTED+1))
  continue
done
echo "=== Regions executed: $EXECUTED ==="

# 2.3 Native Protection associated IPs (per discovered instance, uses --biz-region-id)
aliyun ddosbgp describe-pack-ip-list \
  --instance-id <instance-id> --page-no 1 --page-size 50 --biz-region-id <region-id>

# 2.4 Anti-DDoS Pro instances [MUST query both Regions]
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region cn-hangzhou
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region ap-southeast-1

# 2.5 Anti-DDoS Pro associated domains (per discovered instance)
aliyun ddoscoo describe-domains --instance-ids <instance-id> --region <region-id>
```

> **[MUST] End validation**: 1) Region count: ddosbgp >= 12, ddoscoo = 2 2) Product isolation: no mixed API prefixes 3) Instance deduplication: Global instances (CoverageType=4) appear in every Region — deduplicate by InstanceId

### Phase 3: Confirm Comparison Period

Ask user for comparison period, parse into second-precision Unix timestamps. **[MUST] Use bash `date` command — manual calculation FORBIDDEN:**

```bash
BASE_END=$(date +%s)
BASE_START=$((BASE_END - 86400))
COMPARE_END=$((BASE_START))
COMPARE_START=$((COMPARE_END - 86400))
# Week-over-week: offset 604800s | Hour-over-hour: offset 3600s
echo "Base: $BASE_START ~ $BASE_END | Compare: $COMPARE_START ~ $COMPARE_END"
```

### Phase 4: Execute Inspection & Generate Report

> **[MUST] Sequential Execution Guard**: Execute API chains **strictly in order** for EACH instance. Do NOT stop at "planning" — every API MUST have an actual `aliyun` command executed with visible output. After each sub-step (4.1/4.2/4.3), print `echo "[Step 4.X Complete]"`. Proceeding to 4.4/4.5 without all calls completed is FORBIDDEN.
>
> **[MUST] Route by inventory**: No instances in ALL Regions → execute probe calls (`--instance-id dummy`) on cn-hangzhou to preserve trace, report "not provisioned". Some Regions have instances → inspect those, skip empty Regions. **NEVER** substitute product APIs.

#### 4.1 Basic Protection Inspection

```bash
# Has assets: real ID | No assets: probe call
aliyun antiddos-public describe-ddos-event-list \
  --ddos-region-id <region-id> --instance-type <type> --instance-id <id> \
  --current-page 1 --page-size 50
# Probe: --instance-id dummy --ddos-region-id cn-hangzhou --instance-type ecs
```

> **[MANDATORY CHECKPOINT 4.1]** Confirm describe-ddos-event-list returned JSON or explicit error. If not executed, retry now. Do NOT proceed to 4.2 until confirmed.

#### 4.2 Native Protection Inspection (ddosbgp APIs ONLY)

> **[MUST]** `ddosbgp` APIs only. Attack events: `describe-ddos-event` (**singular**). L4 traffic: `describe-traffic` (MUST call). Region params: describe-ddos-event/describe-pack-ip-list use `--biz-region-id`; describe-traffic uses `--region`.
> Has instances → all 3 APIs per instance | ALL empty → 3 probe calls on cn-hangzhou (all required)

```bash
aliyun ddosbgp describe-ddos-event \
  --instance-id <id> --start-time <ts> --end-time <ts> \
  --page-no 1 --page-size 50 --biz-region-id <region-id>
aliyun ddosbgp describe-pack-ip-list \
  --instance-id <id> --page-no 1 --page-size 50 --biz-region-id <region-id>
aliyun ddosbgp describe-traffic \
  --instance-id <id> --start-time <ts> --end-time <ts> --region <region-id>
# Probe: --instance-id dummy, --biz-region-id cn-hangzhou (describe-traffic: --region cn-hangzhou)
```

> **[MANDATORY CHECKPOINT 4.2]** You MUST now verify all 3 ddosbgp APIs were actually executed by checking terminal output. If describe-ddos-event OR describe-pack-ip-list OR describe-traffic has zero terminal output, STOP and execute the missing call(s) NOW. Two consecutive failures to complete all 3 → output error log and terminate. Do NOT proceed to 4.3 until all 3 confirmed.

#### 4.3 Anti-DDoS Pro/Premium Inspection (ddoscoo APIs ONLY)

> **[MUST]** `ddoscoo` APIs only. Has instances → all APIs per instance | Both Regions empty → probe calls on cn-hangzhou

```bash
aliyun ddoscoo describe-ddos-events \
  --instance-ids <id> --start-time <ts> --end-time <ts> \
  --page-number 1 --page-size 50 --region <region-id>
aliyun ddoscoo describe-domain-qps-list \
  --start-time <ts> --end-time <ts> --interval 300 --region <region-id>
aliyun ddoscoo describe-port-flow-list \
  --instance-ids <id> --start-time <ts> --end-time <ts> \
  --interval 300 --region <region-id>
aliyun ddoscoo describe-domain-status-code-list \
  --start-time <ts> --end-time <ts> --interval 300 \
  --query-type gf --region <region-id>
aliyun ddoscoo describe-domain-status-code-list \
  --start-time <ts> --end-time <ts> --interval 300 \
  --query-type upstrem --region <region-id>
# Probe: --instance-ids dummy, --region cn-hangzhou (same 5 APIs)
```

> **[MANDATORY CHECKPOINT 4.3]** Verify all 5 ddoscoo APIs have terminal output. Any missing → execute now. Do NOT proceed to 4.4.

#### 4.4 Period-over-Period Analysis

Change rate = (Base - Compare) / Compare × 100%. Thresholds: ±30%~±100% → Attention | >±100% → Anomaly | Blackhole/scrubbing present → Anomaly.

#### 4.5 Report Output

> **Mandatory**: Follow [Report Template](references/report-template.md), no sections omitted. Group assets by Region.
>
> **[MUST] Data consistency validation**:
> 1. **Aggregation**: Summary numbers must exactly match detail list counts
> 2. **Deduplication**: Same instance/IP across Regions → deduplicate before counting
> 3. **Empty value annotation (hard rule)**: Empty array `[]` → write `0 (API returned empty)` or `Query failed (ErrorCode: XXX)`. FORBIDDEN: vague phrases like "no anomaly found", "appears to be a false alarm". Key metrics with empty data MUST include `[DATA MISSING]` tag at section start
> 4. **Cross-validation**: Summary totals = sum of Region details
> 5. **Call record verification**: Claimed API calls and conclusions must match actual execution. Fabrication FORBIDDEN
> 6. **Raw Data Binding**: Copy-paste exact values from terminal output into report. FORBIDDEN: inferring from memory, writing "no domains" if API returned domains. Use `grep`/`jq` to verify before finalizing
>
> **[MUST] Pre-computation verification (hard blocker)**:
> **[STRICT MODE] Directly writing `echo "<number>"` with pre-filled values is FORBIDDEN and counts as fabrication. You MUST use `grep`/`jq`/`wc` to parse actual terminal output or saved log. The verification script must contain pipe commands that extract real data, NOT hardcoded echo statements.**
> ```bash
> # [STRICT] Count API calls from terminal history - must use grep, not hardcoded echo
> echo "=== Call statistics ==="
> # Example: grep -c "aliyun antiddos-public" /path/to/terminal.log  (adapt to your log method)
> echo "antiddos-public: $(grep -c 'antiddos-public' <<< "$TERMINAL_LOG")"
> echo "ddosbgp: $(grep -c 'aliyun ddosbgp' <<< "$TERMINAL_LOG")"
> echo "ddoscoo: $(grep -c 'aliyun ddoscoo' <<< "$TERMINAL_LOG")"
> # [STRICT] Count assets from API responses - must use jq/grep, not hardcoded
> echo "=== Asset statistics (from API JSON responses) ==="
> # Parse actual JSON outputs, e.g.: jq '.InstanceList | length', jq '.DomainList | length'
> ```
> **Output must contain pipe commands (`grep`, `jq`, `wc -l`). Pure `echo "number"` without pipes = fabrication = abort.**
> **Mismatch with report draft → abort, re-traverse log, re-run. Report MUST quote the verification output snippet.**

## Cleanup

> **[MUST] Mandatory exit safeguard**: Regardless of exit reason (success, failure, cancellation, timeout), the final step MUST unconditionally execute AI-Mode disable + verification. Highest priority, cannot be overridden.

```bash
aliyun configure ai-mode disable
# Verify: try status command, if unsupported fall back to configure list
VERIFY=$(aliyun configure ai-mode status 2>&1)
if echo "$VERIFY" | grep -q "not a valid\|unknown\|error"; then
  # Fallback: check via configure list output
  aliyun configure list | grep -i "ai-mode\|agent"
fi
# If still uncertain, run disable again to be safe
aliyun configure ai-mode disable
```

> **[MUST]** Only write "AI-Mode confirmed disabled" if verification succeeded. If both `status` and `configure list` fail to confirm, write "AI-Mode disable executed but verification inconclusive (CLI compatibility issue)" — do NOT claim confirmed.

## References

| Resource | Path |
|----------|------|
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| RAM Permission Policies | [references/ram-policies.md](references/ram-policies.md) |
| API Parameter Reference | [references/api-reference.md](references/api-reference.md) |
| CLI Command Table | [references/related-commands.md](references/related-commands.md) |
| Inspection Report Template | [references/report-template.md](references/report-template.md) |
| Verification Method | [references/verification-method.md](references/verification-method.md) |
| Acceptance Criteria | [references/acceptance-criteria.md](references/acceptance-criteria.md) |
