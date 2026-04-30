---
name: alibabacloud-ddoscoo-intercept-query
description: |
  Query Alibaba Cloud DDoS Pro (ddoscoo) block/intercept reasons via SLS full logs and ddoscoo CLI. Analyzes detailed information about intercepted requests including CC protection rules, precise access control rules, region blocking, and IP blacklist policies.
  Use when users report being blocked by DDoS Pro, encounter block pages, or need to investigate and remediate DDoS protection rules.
  Trigger words: "DDoS block query", "blocked by DDoS Pro", "DDoS intercept", "ddoscoo intercept query", "CC block", "precise access control block", "高防拦截查询", "request blocked by anti-ddos"
---

# DDoS Pro (Anti-DDoS Pro) Intercept Query

## Scenario Description

Query and analyze DDoS Pro (ddoscoo) block/intercept events using SLS full logs and ddoscoo CLI commands. When a user reports being blocked by DDoS Pro or encounters a block page, this skill discovers DDoS instances, checks full log configuration, queries SLS logs by Request ID, retrieves rule details, and outputs a structured analysis report with recommendations.

**Architecture**: `DDoS Pro Instance → Full Log (SLS) → Log Query → Rule Analysis → Report`

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

**Pre-check: Aliyun CLI plugin update required**

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**Pre-check: AI-Mode Lifecycle**

> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query"
> ```
> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason (workflow success, failure, error, user cancellation, or session end), always disable AI-mode first. AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

**Pre-check: SLS CLI plugin required**

> [MUST] Install the SLS CLI plugin before any log query operations:
> ```bash
> aliyun component install sls
> ```
> Verify the plugin is available:
> ```bash
> aliyun sls --help
> ```
> If `aliyun component install` is not available, use the legacy command:
> ```bash
> aliyun plugin install --names aliyun-cli-sls
> ```

## Environment Variables

No additional environment variables required. Authentication is handled via the Aliyun CLI credential chain.

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
>
> **Note on 401 Unauthorized errors**: A `401 The security token has expired` error means the STS temporary credential has expired — this is **not** a RAM permission issue. Ask the user to refresh credentials outside this session via `aliyun configure`, then retry.

## RAM Policy

See [references/ram-policies.md](references/ram-policies.md) for the full list of required permissions.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| Request ID | Required | The traceid from DDoS Pro's block response page | None |
| Domain | Optional | The website domain configured in DDoS Pro (auto-discovered if not provided) | Auto-discover |
| DDoS Instance ID | Optional | DDoS Pro instance ID (auto-discovered if not provided) | Auto-discover |
| SLS Project | Optional | SLS Project name (auto-discovered if not provided) | Auto-discover |
| SLS Logstore | Optional | SLS Logstore name (auto-discovered if not provided) | Auto-discover |
| RegionId | Optional | DDoS Pro region: `cn-hangzhou` (China Mainland) or `ap-southeast-1` (International) | cn-hangzhou |

## Core Workflow

> **[MUST] Required API Call Sequence** — The following API calls MUST be executed in order for every invocation of this skill. Do NOT skip any step, even if you believe the result is known in advance:
> 1. **Step 2a** → `ddoscoo DescribeInstances` (both regions) + if domain unknown: `DescribeWebAccessLogDispatchStatus` for domain discovery only
> 2. **Step 2b** → `ddoscoo DescribeSlsOpenStatus` + `DescribeLogStoreExistStatus` + `DescribeSlsLogstoreInfo`
> 3. **Step 2c** → `ddoscoo DescribeWebAccessLogStatus` only (domain must be known from user or Step 2a; `DescribeWebAccessLogDispatchStatus` is NOT permitted here)
> 4. **Step 3** → `sls GetLogs` (query block log by Request ID)
> 5. **Step 5** → Output analysis report

> **[MUST] User-Agent Header** — Every `aliyun` CLI command in this skill MUST include `--header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` to identify the caller.

> **[MUST] 敏感数据脱敏 — 全局规则，贯穿所有输出** — 以下规则适用于整个工作流的**所有输出**，包括最终报告、中间分析、日志引用、补充说明的任何段落，不得在任何位置还原已脱敏的数据：
> - **Client IP**：仅保留第一段，其余用 `*` 替代。**适用于所有输出格式**（JSON 字段、纯文本段落均须脱敏）：
>   - 纯文本段落：`140.205.11.30` → `140.*.*.*`；"来自 IP 140.205.11.30 的请求" → "来自 IP 140.*.*.* 的请求"
>   - JSON 字段引用：`"real_client_ip": "140.205.11.30"` → `"real_client_ip": "140.*.*.*"`
> - **Cookie / Authorization / Token**：整个值替换为 `[MASKED]`，包括在引用原始日志字段时
> - **Query Parameters**：所有参数值替换为 `***`。示例：`?token=abc&name=test` → `?token=***&name=***`
> - **User-Agent 字符串**：截取前 32 个字符

### Step 1: Information Collection

Confirm the Request ID (traceid) with the user. Guide them to obtain it from:
1. The block page displayed in the browser (shows Request ID directly)
2. The HTML body of DDoS Pro's block (intercept) response (contains traceid)

Optionally collect the domain name if the user knows which website was blocked.

### Step 2: Discover DDoS Pro Instances and Verify Full Log Service

#### Step 2a: Discover DDoS Pro Instances and Protected Domains

```bash
# Query DDoS Pro instances (API endpoint region: cn-hangzhou for China, ap-southeast-1 for International)
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region ap-southeast-1 --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

> **[MUST] Instance Discovery Validation** — After calling `describe-instances`, inspect the response:
> - If `Instances` is a non-empty array → record the instance(s) and proceed to Step 2b.
> - If `Instances` is empty (`[]`) for one region → retry with the other region before proceeding.
> - If both regions return empty → stop and inform the user: "No DDoS Pro instances were found under this account. Please verify your credentials and region."
> - **Do NOT proceed to Step 2b or beyond if `describe-instances` returns no results.** An empty instance list means subsequent SLS and log queries will also fail — continuing will produce an empty or incorrect report.

> **[MUST] Domain Discovery** — Step 2c requires a known domain name to call `describe-web-access-log-status`. If the user did NOT provide the domain in their message, discover it HERE in Step 2a before proceeding:
> ```bash
> # Discover all protected domains (domain discovery only — do NOT use the log status from this response)
> aliyun ddoscoo describe-web-access-log-dispatch-status --page-number 1 --page-size 10 --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
> ```
> Extract the domain name(s) from the response and record them. This API is used **only for domain name discovery**, not for checking log status. The actual log status check happens in Step 2c using `describe-web-access-log-status`.

> **[MUST] International Region API Error Recovery**: If any `ap-southeast-1` API call returns `InvalidRosettaRegionId`, `400 Bad Request`, or similar region-level errors:
> 1. **Do NOT abandon the workflow** — continue with available data
> 2. For SLS-related operations: International DDoS Pro SLS projects are typically hosted in `cn-hangzhou` (not `ap-southeast-1`), with project names like `ddosdip-project-<uid>-ap-southeast-1`. Always try `cn-hangzhou` as the SLS region.
> 3. For rule query APIs (e.g., `describe-web-precise-access-rule`, `describe-l7-global-rule`): If `ap-southeast-1` fails, retry the same API call using `cn-hangzhou` endpoint
> 4. **[MUST] Never skip a user-requested query step** due to region API errors — always attempt recovery via the alternative region before reporting failure

#### Step 2b: Check SLS and Full Log Status

First check if SLS is opened and log store exists:

```bash
aliyun ddoscoo describe-sls-open-status --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
aliyun ddoscoo describe-log-store-exist-status --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

Then get the SLS logstore info (project, logstore, capacity, TTL):

```bash
aliyun ddoscoo describe-sls-logstore-info --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

> **[IMPORTANT] Fallback for SLS Info Retrieval**: If `describe-sls-logstore-info` returns an error (e.g., `400 InvalidRosettaRegionId` in `ap-southeast-1`), use the following fallback methods in order:
>
> **Fallback 1** — Get SLS info from domain log status (requires knowing a domain):
> ```bash
> aliyun ddoscoo describe-web-access-log-status --domain '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
> ```
> Extract `SlsProject` and `SlsLogstore` from the response.
>
> **Fallback 2** — List all SLS projects and find the ddoscoo one:
> ```bash
> aliyun sls list-project --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
> ```
> Look for project names containing `ddoscoo` or `ddosdip`. Note: International DDoS Pro SLS projects may also be hosted in `cn-hangzhou`.

#### Step 2c: Check Domain Full Log Status

> **⛔ FORBIDDEN: `describe-web-access-log-dispatch-status` is NOT used in this step.**
> Domain discovery was completed in Step 2a. This step has exactly ONE permitted API call.

By this point the domain name MUST be known (provided by the user, or discovered in Step 2a). Call:

```bash
aliyun ddoscoo describe-web-access-log-status --domain '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

- 若返回 `SlsConfigStatus=true`，说明已开启，直接进入 Step 3。
- 若未开启，告知用户并征得同意后开启：

```bash
aliyun ddoscoo enable-web-access-log-config --domain '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

> **Constraint**: This skill only supports **enabling** full log (`enable-web-access-log-config`). Disabling is **not permitted** via this skill. Never call `disable-web-access-log-config`.

> **[IMPORTANT] Error Handling for Enable**: If `enable-web-access-log-config` returns an error:
> - `DomainDoNotBelongToYou` — Domain is not configured in this DDoS Pro instance. Verify the domain belongs to this instance, or try the other region (`cn-hangzhou` ↔ `ap-southeast-1`).
> - `403 Forbidden` / RAM permission error — See references/ram-policies.md.
>
> **[IMPORTANT] Historical Logs**: Enabling full log only records **future** requests. If the block event occurred **before** enabling, no SLS log will exist for that Request ID. Inform the user: "Full log has been enabled, but the historical block event cannot be queried via SLS. Please reproduce the block and retry with the new Request ID."

### Step 3: Query SLS Logs

> **[MUST]** Use the SLS CLI plugin (`aliyun sls get-logs`) for all log queries.

Use the SLS project/logstore obtained from Step 2 to query block logs:

```bash
# Query SLS logs via plugin-mode call
TO_TIME=$(python3 -c "import time; print(int(time.time()))")
FROM_TIME=$((TO_TIME - 86400))
aliyun sls get-logs \
  --project <project-name> \
  --logstore <logstore-name> \
  --from $FROM_TIME \
  --to $TO_TIME \
  --query "<request-id>" \
  --reverse true \
  --lines 100 \
  --region <sls-region> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

If no results found in the last 24 hours, progressively expand the time range:
- Last 3 days: `FROM_TIME=$((TO_TIME - 86400 * 3))`
- Last 7 days: `FROM_TIME=$((TO_TIME - 86400 * 7))`
- Last 30 days: `FROM_TIME=$((TO_TIME - 86400 * 30))`
- Maximum (based on TTL): `FROM_TIME=$((TO_TIME - 86400 * <ttl_days>))`

> **Fallback method** — If the SLS plugin command above fails (e.g., plugin not installed), use the Python script:
> ```bash
> python3 scripts/get_ddos_logs.py \
>   --project <project-name> \
>   --logstore <logstore-name> \
>   --request-id <request-id> \
>   --region <sls-region>
> ```

**Note**: DDoS Pro full log SLS region mapping:
- China Mainland instances (`cn-hangzhou`): SLS project is in `cn-hangzhou`
- International instances (`ap-southeast-1`): SLS project is **also typically in `cn-hangzhou`** (not `ap-southeast-1`), with project names like `ddosdip-project-<uid>-ap-southeast-1`

> **[MUST]** Do NOT guess SLS project names. Always use the exact project/logstore values obtained from Step 2b (`describe-sls-logstore-info` or its fallback). If both APIs failed, use `aliyun sls list-project --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query` to discover projects containing `ddoscoo` or `ddosdip`.

### Step 4: Query Rule Details

After obtaining the SLS log, extract key fields to determine the block type and query the specific rule configuration.

#### Step 4a: Identify Block Type from Log Fields

The two most important log fields for identifying the block type are:

- **`cc_phase`** — Identifies which protection module triggered the block
- **`last_owner`** — Format is `<rule_name>|<source>`, where `source` is `manual` (user-created) or `clover` (auto-generated)

**`cc_phase` → Block Type → Query API Mapping:**

| `cc_phase` value | Block Type | Rule Detail Query Command |
|------------------|-----------|-------------------------|
| `gfcc` / `cc` | CC Protection (频率控制自定义规则) | `describe-web-cc-rules-v2` |
| `gfacl` / `acl` | Precise Access Control (精确访问控制) | `describe-web-precise-access-rule` |
| `gfai` / `ai` | AI Smart Protection (AI智能防护) | `describe-web-cc-protect-switch` |
| `gfglobal` / `global` / `gf_rule` | Global Defense Policy (全局防护策略) | `describe-l7-global-rule` |
| `gfbwip` / `blacklist` | IP Blacklist (IP黑名单) | `describe-web-rules` (BlackList field) |
| `gfareaban` / `region` / `geo` | Region Blocking (区域封禁) | `describe-web-area-block-configs` |

Other useful log fields:

| Log Field | Description |
|-----------|-------------|
| `cc_action` | Action taken: `block`, `captcha`, `close`, `watch` |
| `cc_rule_id` | Specific rule ID that triggered |
| `cc_blocks` | Whether the request was blocked (`1` = yes) |
| `final_action` | Final action taken on the request |
| `final_plugin` | Block plugin identifier |
| `traceid` | Request trace ID (same as Request ID in block page) |
| `matched_host` | The domain that matched the request |
| `host` | The Host header from the request |
| `real_client_ip` | Client's real IP address |
| `last_owner` | `<rule_name>\|<source>` — identifies which rule and its origin |
| `isp_line` | DDoS Pro 接入线路（如：电信、联通、移动、香港、海外等）。**注意**：此字段反映的是 DDoS Pro 的接入线路，不等同于客户端的物理位置。报告中应表述为"请求经由 {isp_line} 线路接入"，不可将其直接等同于客户端所在地区 |

#### Step 4b: Query Strategy Switch Status (策略预检)

**[MUST] Before querying specific rules**, first check which protection modules are enabled:

```bash
aliyun ddoscoo describe-web-cc-protect-switch --domains.1 '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

This returns all switch states. Key fields:

| Field | Description | Values |
|-------|-------------|--------|
| `CcEnable` | CC protection master switch | `0` (off) / `1` (on) |
| `CcCustomRuleEnable` | Custom CC rules switch | `0` / `1` |
| `PreciseRuleEnable` | Precise Access Control (ACL) switch | `0` / `1` |
| `CcGlobalSwitch` | Global defense switch | `close` / `open` |
| `AiRuleEnable` | AI smart protection switch | `0` / `1` |
| `AiMode` | AI mode | `watch` / `defense` |
| `AiTemplate` | AI level | `level30` / `level60` / `level90` |
| `BlackWhiteListEnable` | IP blacklist/whitelist switch | `0` / `1` |
| `RegionBlockEnable` | Region blocking switch | `0` / `1` |

#### Step 4c: Query Specific Rule Details

Based on `cc_phase`, call the corresponding API to fetch the rule configuration.

**If `cc_phase` = `cc` → CC Protection Rules:**
```bash
# Query all CC rules for the domain; use --owner manual for user rules, clover for auto rules
aliyun ddoscoo describe-web-cc-rules-v2 --domain '<domain>' --offset 0 --page-size 30 --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```
Then find the specific rule by matching `last_owner`'s rule name (the part before `|`) against the rule's `name` field in the response.

**If `cc_phase` = `gfacl` → Precise Access Control (ACL) Rules:**
```bash
aliyun ddoscoo describe-web-precise-access-rule --domains.1 '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```
Then find the specific rule by matching `last_owner`'s rule name against the rule's `Name` field in the response.

**If `cc_phase` = `ai` → AI Smart Protection:**
```bash
# AI protection has no individual rules; check mode and level from switch status
aliyun ddoscoo describe-web-cc-protect-switch --domains.1 '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```
Report the `AiMode` (watch/defense), `AiTemplate` (level30/60/90), and `AiRuleEnable` status.

**If `cc_phase` = `global` or `gf_rule` → Global Defense Policy:**
```bash
# Get global rule list with RuleId, Action, Enabled, Description
aliyun ddoscoo describe-l7-global-rule --domain '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

**If `cc_phase` = `blacklist` → IP Blacklist/Whitelist:**
```bash
# Get blacklist and whitelist IPs from domain web rules
aliyun ddoscoo describe-web-rules --domain '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```
Extract `BlackList` and `WhiteList` arrays from the response.

**If `cc_phase` = `region` or `geo` → Region Blocking:**
```bash
aliyun ddoscoo describe-web-area-block-configs --domains.1 '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```
Check which regions have `Block = 1`.

> **[IMPORTANT] Domain Not Found**: If the domain query returns `DomainNotExist`, the domain may have been removed from DDoS Pro after the block event. Report this to the user — the log is still valid but rule details cannot be retrieved.

See [references/domain-security-policy.md](references/domain-security-policy.md) for the complete domain security policy management reference including rule creation, modification, deletion, and field reference tables.

### Step 5: Output Analysis Report

> **[MUST] Sensitive Data Masking** — Apply the global masking rules defined in Core Workflow to all fields in this report, including any supplementary paragraphs. Never restore masked data in any section.

```markdown
## DDoS Pro Intercept Analysis Report

### Request Information
- Request ID: {request_traceid}
- Block Time: {time}
- Client IP: {masked_real_client_ip, e.g. 192.***.***.***}
- ISP Line: {isp_line}（DDoS Pro 接入线路，非客户端实际位置）
- Domain: {matched_host}
- Request URL: {host}{request_path}?{masked_query_params}

### Block Details
- Rule ID: {final_rule_id 或 cc_rule_id；若日志中两个字段均不存在，输出 "N/A - 日志中未记录规则 ID"，不可省略此行}
- Block Type: {final_plugin / cc_phase}
- Action: {final_action or cc_action}

### Recommendations
{Based on block type, refer to references/common-block-reasons.md}
```

## Troubleshooting

### No Logs Found

1. Re-check SLS and log store status (Step 2b)
2. Check domain full log switch:
   ```bash
   aliyun ddoscoo describe-web-access-log-status --domain '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
   ```
3. Enable if disabled (check-then-act):
   ```bash
   aliyun ddoscoo enable-web-access-log-config --domain '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
   ```
4. Check all domain log dispatch status:
   ```bash
   aliyun ddoscoo describe-web-access-log-dispatch-status --page-number 1 --page-size 50 --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
   ```

### Request ID Not Found

1. Verify Request ID format (typically 30+ hex characters)
2. Script auto-expands search up to 90 days
3. Try both regions (`cn-hangzhou` and `ap-southeast-1`)
4. Check log retention (TTL) via `describe-sls-logstore-info`

### Multi-Instance Scenarios

DDoS Pro instances may span both regions. Query logs across all discovered SLS projects until the Request ID is found.

## Rule Operation Constraints

See [references/rule-operations.md](references/rule-operations.md) for detailed instructions.

When user requests to disable a rule:
1. Check current status first (idempotent check-then-act)
2. Only disable operations are permitted; never delete rules
3. Confirm with user before executing

**Disable CC Rule**:
```bash
aliyun ddoscoo disable-web-cc-rule --domain '<domain>' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

**Disable Precise Access Control**:
```bash
aliyun ddoscoo modify-web-precise-access-switch --domain '<domain>' --config '{"PreciseRuleEnable": 0}' --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

## Success Verification Method

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

**Expected Outcome**: Intercept analysis report generated with complete request information, rule details, and actionable recommendations.

**Verification**: After querying with a known Request ID, the output should contain all fields in the report template.

## Cleanup

This skill is read-only by default and does not create persistent resources. No cleanup required unless:
- Full log was enabled for a domain during execution (inform user; this skill only enables, never disables)
- CC rules were disabled (can be re-enabled via `enable-web-cc-rule`)

## Best Practices

1. Always query both regions (`cn-hangzhou` and `ap-southeast-1`) for instance discovery
2. **[MUST]** Use `aliyun sls get-logs` (plugin mode, kebab-case) for SLS log queries
3. Do NOT guess SLS project/logstore names — always obtain them from `describe-sls-logstore-info` or `describe-web-access-log-status`
4. Check domain full log status before querying to avoid empty results
5. **[MUST]** Mask sensitive data in output reports: Client IP → `first_octet.*.*.*`, query parameters → `***`, cookies/tokens → `[MASKED]`
6. Use idempotent check-then-act pattern before any write operations
7. Never delete rules — only disable/enable operations are permitted

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission requirements |
| [references/common-block-reasons.md](references/common-block-reasons.md) | Common block reasons and recommendations |
| [references/rule-config-details.md](references/rule-config-details.md) | Rule configuration field descriptions |
| [references/rule-operations.md](references/rule-operations.md) | Rule operation policy and constraints |
| [references/domain-security-policy.md](references/domain-security-policy.md) | Domain security policy management (query, create, modify, delete rules) |
| [references/related-commands.md](references/related-commands.md) | All CLI commands used in this skill |
| [references/verification-method.md](references/verification-method.md) | Success verification steps |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and upgrade guide |
