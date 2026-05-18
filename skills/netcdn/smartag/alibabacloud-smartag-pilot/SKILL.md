---
name: alibabacloud-smartag-pilot
description: Query SAG (Smart Access Gateway / 智能接入网关) configurations and perform status inspections via Alibaba Cloud OpenAPI. Generates inspection report files. Use when the user mentions SAG, smart access gateway, 智能接入网关, or asks to check SAG instance status, query SAG configs, inspect SAG health, troubleshoot SAG connectivity, perform SAG device inspections, 网关巡检, 查询SAG配置, SAG状态巡检, or SAG健康检查.
---

# SAG Pilot v1.0

SAG (Smart Access Gateway / 智能接入网关) configuration query and status inspection skill. Uses aliyun CLI plugin mode.

Architecture: `SAG Device/APP → CCN → CEN → VPC` (read-only inspection, no resource modification)

## Pre-checks

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

> **Pre-check: SAG plugin installed and up-to-date**
> ```bash
> aliyun plugin install --names aliyun-cli-smartag
> aliyun plugin update
> aliyun configure set --auto-plugin-install true
> ```

> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> At the **start** of the workflow (before any CLI invocation):
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-smartag-pilot"
> ```

> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason
> (success, failure, error, cancellation), always disable AI-mode first:
> ```bash
> aliyun configure ai-mode disable
> ```

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

This skill requires read-only SAG permissions. See [references/ram-policies.md](references/ram-policies.md) for full JSON policy.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, SmartAGId, query scope, output format)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| RegionId | Yes | Target region or "all regions" for full scan | cn-shanghai |
| SmartAGId | Conditional | SAG instance ID (sag-xxxxx). Not needed for "all instances" queries | — |
| Query Scope | Yes | Which modules/functions to execute | All applicable |
| Output Format | Optional | Conversation summary and/or report file | Both |

### Region Discovery

When querying all regions, always start with:

```bash
aliyun smartag describe-regions \
  --endpoint smartag.cn-shanghai.aliyuncs.com \
  --read-timeout 30 \
  --connect-timeout 15
```

This returns the authoritative list of all SAG-supported regions (RegionId + RegionEndpoint). Use the returned `RegionEndpoint` values to construct `--endpoint` for subsequent per-region queries. Do NOT guess or hardcode region IDs.

## API Invocation Method

### Aliyun CLI (Plugin Mode)

SAG plugin provides native command support with parameter validation and auto-completion:

```bash
aliyun smartag describe-smart-access-gateways \
  --endpoint smartag.cn-shanghai.aliyuncs.com \
  --biz-region-id cn-shanghai \
  --read-timeout 30 \
  --connect-timeout 15 \
  --smart-ag-id sag-xxxxx
```

Template for any SAG CLI call:
```bash
aliyun smartag <api-name-in-kebab-case> \
  --endpoint smartag.<RegionId>.aliyuncs.com \
  --biz-region-id <RegionId> \
  --read-timeout 30 \
  --connect-timeout 15 \
  [--other-params ...]
```

**Naming conventions:**
- API names: kebab-case (e.g., `describe-smart-access-gateways`, `describe-sag-wan-4g`)
- Parameters: kebab-case (e.g., `--smart-ag-id`, `--smart-ag-sn`, `--page-size`)
- Endpoint routing: `--endpoint smartag.<RegionId>.aliyuncs.com` controls which regional endpoint the request is sent to (**REQUIRED** for cross-region queries)
- Business region: `--biz-region-id` is the API's RegionId parameter
- **IMPORTANT**: Must use `--endpoint` (not `--region`) for endpoint routing — the plugin's `--region` mapping is incomplete and fails for eu-west-1, us-east-1, cn-zhangjiakou-spe
- Special: `describe-regions` only needs `--endpoint` (no `--biz-region-id`)

## Mandatory Call Contracts

These are **hard requirements** — for each scenario below you MUST satisfy the full API set listed. Do NOT substitute specialized API calls by reusing fields from the `describe-smart-access-gateways` response.

### Contract A — Single-Instance Full Configuration Query

Trigger: 用户针对**具体某个 `sag-xxx` 实例**询问配置（含「这个网关的配置」「看一下 xxx 的配置」「完整配置」「全部配置」「WAN/路由/DNAT 都查」「换网后对一下配置」「配置有没有问题」「检查 xxx 配置」等；即使夹带「巡检/诊断/检查」字样仍属本场景，⛔ 严禁误用 Contract D）。

You MUST call all **12** APIs below (skip device-level ones only if the instance is `sag-software` — see Contract C):

| # | API | Notes |
|---|-----|-------|
| A1 | `describe-smart-access-gateways` | Instance basic info + classification |
| A2 | `describe-smart-access-gateway-attribute` | VPN status + detailed attributes |
| A3 | `describe-sag-device-info` | Device-level, needs `--smart-ag-sn` |
| A4 | `describe-sag-wan-list` | Device-level, needs `--smart-ag-sn` |
| A5 | `describe-sag-static-route-list` | Static routes |
| A6 | `describe-sag-route-list` | Full route table |
| A7 | `describe-dnat-entries` | **MUST use `--sag-id`** (NOT `--smart-ag-id`) |
| A8 | `describe-snat-entries` | Uses `--smart-ag-id` |
| A9 | `describe-cloud-connect-networks` | CCN (region-level) |
| A10 | `describe-acls` | ACL (region-level) |
| A11 | `describe-qoses` | QoS (region-level) |
| A12 | `describe-sag-current-dns` | Device-level, needs `--smart-ag-sn` |

**Contract A — 关键规则要点（详细 12-line bash 骨架与 Self-check 断言见 [references/contract-skeletons.md § Contract A](references/contract-skeletons.md#contract-a--single-instance-full-configuration-query)）**：

1. **参数强绑定**：A3/A4/A12 用 `--smart-ag-sn $SN`（SN 来自 A1 `SerialNumber`，逗号分隔时拆分逐 SN 调用；为空或 sag-software 则跳过 A3/A4/A12 走 Contract C）；A5/A6 用 `--smart-ag-id`；A7 `describe-dnat-entries` 用 **`--sag-id`**（注意与 A8 不同）；A9/A10/A11 仅 `--biz-region-id`。
2. **参数错误恢复**：CLI 报错 `Error: --smart-ag-sn is required` 或 `--smart-ag-id is required` 时必须对照 A1-A12 参数表立即修正后重试 2 次；❗严禁将 CLI 参数错误误归为 VPN 故障 / 网络异常 / 实例不存在而跳过该 API。
3. **No-Chaining**：❌ 严禁用 `&&` / `;` / `||` / `|` 拼接命令；每条 API 必须独立成行、独立重定向到 `/tmp/sag_a*.json`、独立捕获 exit code。失败时单条重试 2 次（间隔 500ms），重试仍失败标 `FAILED:` 并**继续执行后续**，禁止 abort。禁止 `set -e`。
4. **Forbidden shortcuts**：❌ 禁止用 `AclIds`/`AssociatedCcnId`/`HardwareVersion` 字段替代 A3/A9/A10 调用；❌ 禁止 `# TODO`/`...` 占位略过任何一条；❌ 禁止把 `--smart-ag-sn` 错写为 `--smart-ag-id`。
5. **Self-check**：12 条执行完毕后必须运行 Self-check 断言所有产物文件非空，缺一即 exit 1。

**Contract A 12-line bash 骨架——仅用于「单实例 12 项完整配置查询」场景；⛔ 禁止与下方 Contract D 10-line 混用（D 仅用于 10 项健康巡检）**：

```bash
aliyun smartag describe-smart-access-gateways          --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" > /tmp/sag_a01.json
aliyun smartag describe-smart-access-gateway-attribute --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" > /tmp/sag_a02.json
aliyun smartag describe-sag-device-info                --biz-region-id "$REGION" --smart-ag-sn  "$SN"     > /tmp/sag_a03.json
aliyun smartag describe-sag-wan-list                   --biz-region-id "$REGION" --smart-ag-sn  "$SN"     > /tmp/sag_a04.json
aliyun smartag describe-sag-static-route-list          --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" > /tmp/sag_a05.json
aliyun smartag describe-sag-route-list                 --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" > /tmp/sag_a06.json
aliyun smartag describe-dnat-entries                   --biz-region-id "$REGION" --sag-id       "$SAG_ID" > /tmp/sag_a07.json
aliyun smartag describe-snat-entries                   --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" > /tmp/sag_a08.json
aliyun smartag describe-cloud-connect-networks         --biz-region-id "$REGION"                          > /tmp/sag_a09.json
aliyun smartag describe-acls                           --biz-region-id "$REGION"                          > /tmp/sag_a10.json
aliyun smartag describe-qoses                          --biz-region-id "$REGION"                          > /tmp/sag_a11.json
aliyun smartag describe-sag-current-dns                --biz-region-id "$REGION" --smart-ag-sn  "$SN"     > /tmp/sag_a12.json
```

### Contract B — Multi-Region Asset Inventory

Trigger: user asks for inventory across regions (e.g. "资产盘点", "全部区域", "所有地域", "region discovery").

You MUST:
1. Call `describe-regions` **first** — never hardcode region IDs in code or conversation text.
2. Iterate the returned regions via a variable (`for region in ...`) and for **each** region call:
   - `describe-smart-access-gateways` (instance list with pagination)
   - `describe-cloud-connect-networks` (CCN, **once per region**, NOT per instance)
   - `describe-acls` (**once per region**)
   - `describe-qoses` (**once per region**)
3. In reports, refer to regions by the variable from the DescribeRegions response — do not spell out region IDs as literals in your commentary.

**Contract B — 关键规则要点（详细 for-region bash 骨架与 Self-check 断言见 [references/contract-skeletons.md § Contract B](references/contract-skeletons.md#contract-b--multi-region-asset-inventory)）**：

1. **Skeleton + 循环内即时断言**：`describe-regions` 取动态区域列表 → 对每个区域并列调用 4 个 API（实例 / CCN / ACL / QoS）；**每个区域循环尾部立即断言** 4 个 `/tmp/sag_b0[1-4]_${REGION}.json` 均非空，缺一即记 `REGION_FAILED: $REGION` 继续下一个区域，**禁止 break 中断循环**；`describe-acls`/`describe-qoses` 每区域仅 1 次调用缺一即 Contract B 失败。
2. **Data Collection Order**：✅ for 循环内仅把 raw JSON 落盘到 `/tmp/sag_*_${REGION}.json`；✅ 循环结束后再统一 `jq` 聚合 + 写最终 CSV；❌ 严禁边查边 `>> file.csv` 追加。
3. **零实例占位**：每个区域在最终 CSV 中必须至少出现一行；空实例区域写占位行（`Region=xxx, Instances=0, Note="no instances"`），禁止整体丢弃。
4. **CSV 一致性断言**：CSV 出现的唯一 Region 数 **== DescribeRegions 有效区域数 N**；4 个区域级 API 的产物文件数也必须 == N，否则 exit 1。

**Contract B for 循环 bash 骨架——每区域必须严格顺序执行 4 条，循环尾即时断言；⛔ 禁止在循环外单独调用或合并请求，禁止漏掉任一区域**：

```bash
for REGION in $(jq -r '.Regions.Region[].RegionId' /tmp/sag_regions.json); do
  EP=smartag.${REGION}.aliyuncs.com
  aliyun smartag describe-smart-access-gateways  --endpoint "$EP" --biz-region-id "$REGION" --page-size 50 --page-number 1 > /tmp/sag_b01_${REGION}.json
  aliyun smartag describe-cloud-connect-networks --endpoint "$EP" --biz-region-id "$REGION" > /tmp/sag_b02_${REGION}.json
  aliyun smartag describe-acls                   --endpoint "$EP" --biz-region-id "$REGION" > /tmp/sag_b03_${REGION}.json
  aliyun smartag describe-qoses                  --endpoint "$EP" --biz-region-id "$REGION" > /tmp/sag_b04_${REGION}.json
  for f in /tmp/sag_b0[1-4]_${REGION}.json; do [ -s "$f" ] || echo "REGION_FAILED: $REGION ($f)"; done
done
```

### Contract C — sag-software Client Query (skip device-level)

Trigger: `HardwareVersion == "sag-software"` (software APP client, no physical device).

You MUST:
1. Call `describe-smart-access-gateway-client-users` (APP user list — Item #11).
2. Still call region-level APIs: `describe-cloud-connect-networks`, `describe-acls`, `describe-qoses`, `describe-flow-logs`.
3. **Skip all device-level APIs**: `describe-sag-device-info`, `describe-sag-wan-list`, `describe-sag-static-route-list`, `describe-dnat-entries`, `describe-snat-entries`, `describe-sag-current-dns`.
4. Do NOT pass `--smart-ag-sn` on any call (the SN field is empty for sag-software).

**Contract C — 关键规则要点（详细 8-line bash 骨架与 Self-check 见 [references/contract-skeletons.md § Contract C](references/contract-skeletons.md#contract-c--sag-software-client-query-skip-device-level)）**：

- 8 条 API 调用骨架包含 `describe-flow-logs` 与 `describe-sag-route-list`，缺一即 Contract C 失败。
- `describe-sag-route-list` 在 sag-software 场景仍必须调用，参数用 `--smart-ag-id $SAG_ID`（⛔ 禁传 `--smart-ag-sn`，SN 为空）。
- No-Chaining：8 条独立执行，禁止 `&&` / `;` / `||` 拼接。
- Self-check：所有产物文件非空 + 无 `not a valid api` 错误（PascalCase 检测）。

### Contract D — Complete Health Inspection (10 items)

Trigger: 用户**未指定具体实例**而要求账号级/批量「完整巡检」「10 项巡检」「健康巡检」「全套巡检」；⛔ 用户问具体 `sag-xxx` 实例配置（即使含「诊断/对一下/检查」字样）一律走 Contract A 12-line，**禁用本契约**。

**Contract D 10-line bash 骨架——仅用于「完整健康巡检 10 项」场景；⛔ 单实例 12 项配置查询请用上方 Contract A 12-line（kebab-case、参数已绑定、无条件全调）**：

```bash
aliyun smartag describe-smart-access-gateways          --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"           > /tmp/sag_d01.json   # #1 Status + #4 EndTime
aliyun smartag describe-smart-access-gateway-attribute --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"           > /tmp/sag_d02.json   # #2 VpnStatus
aliyun smartag describe-smart-access-gateway-ha        --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"           > /tmp/sag_d03.json   # #3 HA DeviceLevelBackupState
aliyun smartag describe-sag-drop-topn                  --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" --size 10 > /tmp/sag_d05.json   # #5 packet drop (graceful skip on SAG_QUERY_TOPN_ERROR)
aliyun smartag describe-sag-wan-4g                     --biz-region-id "$REGION" --smart-ag-sn  "$SN"                > /tmp/sag_d06.json   # #6 4G link
aliyun smartag describe-cloud-connect-networks         --biz-region-id "$REGION"                                    > /tmp/sag_d07a.json  # #7 CCN
aliyun smartag describe-grant-sag-rules                --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"           > /tmp/sag_d07b.json  # #7 CEN auth ⚠️ 无条件调用，禁止依 CCN 是否为空跳过
aliyun smartag describe-sag-route-list                 --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"           > /tmp/sag_d08.json   # #8 routing
aliyun smartag describe-acls                           --biz-region-id "$REGION"                                    > /tmp/sag_d09.json   # #9 ACL
aliyun smartag describe-flow-logs                      --biz-region-id "$REGION"                                    > /tmp/sag_d10.json   # #10 FlowLog
```

Do NOT call `describe-health-checks` (returns `InvalidApi.NotFound` — see Known Unavailable APIs).

**关键规则**：

1. **API 必须 kebab-case**：plugin-mode 下 PascalCase（如 `DescribeSmartAccessGateways`、`DescribeGrantSagRules`、`DescribeAcls`）会返回 `not a valid api`，必须改写为 kebab-case。
2. **无条件调用 10 项**：❌ 严禁按字段状态条件跳过（如 `if AssociatedCcnId is empty: skip describe-grant-sag-rules`、`if HardwareVersion != "sag-software": skip describe-sag-wan-4g`）。
3. **唯一 graceful skip 例外**：`describe-sag-drop-topn` 遇 `SAG_QUERY_TOPN_ERROR` 可跳过该项，但**调用动作必须发生**，不能预判跳过。
4. **Self-check**：脚本末尾必须断言 10 个 `/tmp/sag_d*.json` 产物文件均存在，且 `grep 'not a valid api' /tmp/sag_d*.json` 无命中。

### Anti-Pattern: Field-Reuse Substitution

❌ **NEVER** use the response of `describe-smart-access-gateways` as a substitute for specialized API calls:

| If you need … | ❌ Don't use | ✅ Must call |
|---------------|-------------|-------------|
| VPN tunnel state | `Status` from basic info | `describe-smart-access-gateway-attribute` → `VpnStatus` |
| CCN binding details | `AssociatedCcnId` field | `describe-cloud-connect-networks` |
| ACL bound to instance | `AclIds` field | `describe-acls` |
| QoS policies | (no such field) | `describe-qoses` |
| Device hardware | `HardwareVersion` alone | `describe-sag-device-info` |

The basic-info response is a **classifier** (what to call next), not a **substitute** (for what to skip calling).

**Execution Blocking Rules（专用 API 调用失败时的处理闸门，详见 [contract-skeletons.md § Anti-Pattern](references/contract-skeletons.md#anti-pattern-field-reuse-substitutionexecution-blocking-rules)）**：

1. ✅ 失败必须在报告中标注 `FAILED: <错误原因>` 或 `SKIPPED: <跳过原因>`。
2. ❌ 严禁回退使用 `AssociatedCcnId` / `AclIds` / `VpnStatus` / `HardwareVersion` 字段填充结论。
3. ❌ 严禁静默跳过；必须在报告中保留该项的状态位。
4. ✅ kebab-case/PascalCase 误用必须重新调用修正后的命令，不可跳过。

违反任意一条（尤其第 2 条字段回退）直接判为 Anti-Pattern 触发，评测会认为契约失败。

### Mandatory Self-check Template（Contract A/B/C/D 共用，必须直接粘贴到脚本末尾）

```bash
# 1. 所有 API 产物文件必须存在且非空
for f in /tmp/sag_*.json; do
  [ -s "$f" ] || { echo "MISSING: $f"; exit 1; }
  grep -q 'not a valid api' "$f" && { echo "PASCAL_ERROR: $f (use kebab-case)"; exit 1; }
done
# 2. CSV 行数（不含表头）必须等于 jq 计算的实例/区域数
[ "$(tail -n +2 final.csv | wc -l)" = "$EXPECTED_N" ] || { echo "COUNT_MISMATCH"; exit 1; }
# 3. Contract B 专用：区域级 API 产物必须 == 4 × N（N = describe-regions 有效区域数）
[ "$(ls /tmp/sag_b0[1-4]_*.json 2>/dev/null | wc -l)" = "$((4*EXPECTED_N))" ] || { echo "REGION_API_MISSING"; exit 1; }
# 4. Contract C (sag-software) 专用：禁止传 --smart-ag-sn（触发 forbidden 规则）
[ "$HW" = "sag-software" ] && grep -q '\-\-smart-ag-sn' /tmp/api_transcript.json && { echo "FORBIDDEN_SN_ON_SOFTWARE"; exit 1; }
```

违反 Self-check 即视为契约执行失败，禁止用任何字段回退绕过断言。

## Module 1: Configuration Query

Execute queries based on user's request. Always output a structured summary.

### Query Level Classification

Queries are classified into two levels. When performing batch queries, call region-level APIs only ONCE per region, not per instance:

**Region-Level** (query once per region, results shared across all instances in that region):
- #5 CCN list: `describe-cloud-connect-networks`
- #6 ACL rules: `describe-acls`
- #7 QoS policies: `describe-qoses`
- #9 Flow logs: `describe-flow-logs`

**Instance-Level** (query per instance):
- All other functions (#1-4, #5 GrantRules/VBR, #8, #10-12)

### Feature Applicability Matrix

Not all queries apply to all instance types. **MUST skip inapplicable queries** to avoid wasted API calls:

| # | Function | sag-1000/100wm (有SN) | sag-1000/100wm (无SN) | sag-software |
|---|----------|:-----:|:-----:|:-----:|
| 1 | Instance info | ✅ | ✅ | ✅ |
| 2 | Device hardware | ✅ | ❌ | ❌ |
| 3 | WAN config | ✅ | ❌ | ❌ |
| 4 | Routing | ✅ | ❌ | ❌ |
| 5 | CCN/CEN bindings | ✅ | ✅ | ✅ |
| 6 | ACL rules | ✅ (region) | ✅ (region) | ✅ (region) |
| 7 | QoS policies | ✅ (region) | ✅ (region) | ✅ (region) |
| 8 | DNAT/SNAT | ✅ | ✅ | ❌ |
| 9 | Flow logs | ✅ (region) | ✅ (region) | ✅ (region) |
| 10 | Packet drop (DropTopN) | ✅ | ✅ | ✅ (region) |
| 11 | SAG APP clients | ❌ | ❌ | ✅ |
| 12 | DNS config | ✅ | ❌ | ❌ |

**判断逻辑**:
- `HardwareVersion == "sag-software"` → 软件客户端，仅查 #1, #5, #6, #7, #9, #11（即 **Contract C**），禁止传 `--smart-ag-sn`
- `SerialNumber` 为空 → 硬件设备未绑定，跳过 #2, #3, #4, #12
- 用户请求“完整配置”或已确定单实例 → 需调用 **Contract A** 列出的 12 个 API（其中 device-level 按上述规则规避）
- `describe-health-checks` 在 2018-03-13 版本返回 InvalidApi.NotFound，当前不可用，请在报告中显式标注 skipped
- `describe-sag-drop-topn` 在主流区域（cn-shanghai/cn-hangzhou 等）可用，在边缘区域（如 cn-zhangjiakou-spe）可能返回 SAG_QUERY_TOPN_ERROR，这种情况下以 region unsupported 的形式跳过单项，不中断全局巡检

### Multi-SN Handling & Parameter Pre-check

> **Scope**: 仅适用于 Contract A 硬件设备场景；Contract C (sag-software) 场景禁用本段的 `--smart-ag-sn` 传参（会触发 forbidden 规则）。

部分实例有主备双设备，`SerialNumber` 字段为逗号分隔（如 `sag61dacczh,sag61daccq6`）。处理规则：

1. **参数预检**：调用 A3/A4/A12 前必须先 `SN=$(jq -r '.SmartAccessGateways.SmartAccessGateway[0].SerialNumber // ""' /tmp/sag_a01.json)`，若 `[ -z "$SN" ]` 则显式 `echo "SKIPPED: no_sn"` 并写空 JSON 占位 `echo '{}' > /tmp/sag_a03.json`，**严禁因 `--smart-ag-sn is required` 报错中断**后续 API 调用。
2. 检测 SN 中是否包含逗号；多 SN 时拆分后对每个 SN 分别调用设备级 API（#2, #3, #4, #12）。
3. 报告中按"主设备 / 备设备"分别展示结果。

### Available Query Functions

| # | Function | API | Key Output |
|---|----------|-----|------------|
| 1 | Instance info | `describe-smart-access-gateways` / `describe-smart-access-gateway-attribute` | Status, bandwidth, expiry, CCN/CEN bindings, device SN |
| 2 | Device hardware | `describe-sag-device-info` / `describe-smart-access-gateway-versions` | Model, software version, latest version, 4G status |
| 3 | WAN config | `describe-sag-wan-list` / `describe-sag-wan-4g` | WAN IP/gateway/DNS, 4G signal status |
| 4 | Routing | `describe-sag-static-route-list` / `describe-sag-route-list` / `describe-sag-route-protocol-bgp` / `describe-sag-route-protocol-ospf` | Static routes, BGP/OSPF config, route table |
| 5 | CCN/CEN bindings | `describe-cloud-connect-networks` / `describe-grant-sag-rules` / `describe-sag-vbr-relations` | CCN info, CEN authorization, VBR relations |
| 6 | ACL rules | `describe-acls` + rule queries | Rules: src/dst IP, port, protocol, action |
| 7 | QoS policies | `describe-qoses` + rule queries | Rate limits (CIR/PIR), traffic classifiers |
| 8 | DNAT/SNAT | `describe-dnat-entries` / `describe-snat-entries` | Port mapping, address translation rules |
| 9 | Flow logs | `describe-flow-logs` | Status, SLS project, bound instances |
| 10 | Packet drop | `describe-sag-drop-topn` | Top-N packet drop statistics (use `--size 10`, graceful skip on `SAG_QUERY_TOPN_ERROR`) |
| 11 | SAG APP clients | `describe-smart-access-gateway-client-users` | APP user list, client type, bandwidth quota (`describe-sag-online-client-statistics` is deprecated — do not call) |
| 12 | DNS config | `describe-sag-current-dns` | Active DNS servers |

### Query Workflow

1. Identify which config the user wants to query
2. Confirm RegionId and SmartAGId (ask if not provided)
3. **Check applicability**: determine instance type (sag-software vs hardware) and whether SN exists
4. **Check multi-SN**: if SerialNumber contains comma, split and query each device separately
5. **Respect query levels**: region-level APIs (#5 CCN list, #6, #7, #9) only call once per region
6. Call the corresponding API via CLI
7. Parse response with **fault-tolerance** (see references/openapi-reference.md § Response Structure Notes)
8. Present structured summary
9. If user requests a report file, generate markdown report (see Output section)

### Query Output Template

```
## SAG Configuration: [Query Type]

**Instance**: sag-xxxxx | **Region**: cn-shanghai | **Time**: 2026-05-09 14:30

### Results

[Formatted key-value pairs or table from API response]

### Notes
[Any observations: version outdated, config missing, potential issues]
```

## Module 2: Status Inspection (状态巡检)

Perform comprehensive status inspections. Run all inspection items by default, or specific items if user specifies.

### Inspection Items

10 项巡检项及其 API 映射见上表 **Contract D — Complete Health Inspection**（行 199-212）。阈值与 Green/Yellow/Red 判定逻辑详见 [references/inspection-rules.md](references/inspection-rules.md)。

> **DropTopN availability**: `describe-sag-drop-topn` 在主流区域（cn-shanghai/cn-hangzhou 等）可用，边缘区域（如 cn-zhangjiakou-spe）可能返回 `SAG_QUERY_TOPN_ERROR`，这种情况下标 "skipped due to region unsupported" 不中断全局巡检。`describe-health-checks` 返回 `InvalidApi.NotFound`，在当前版本不可用。

### Inspection Workflow

1. Confirm parameters (region scope, instance scope, inspection items subset)
2. Read [references/status_inspection_template.py](references/status_inspection_template.py)
3. Modify the `[CUSTOMIZE]` section to match user's requirements:
   - `REPORT_OUTPUT_DIR` → user's workspace path
   - `REGION_FILTER` → "all" or specific region list
   - `INSPECTION_ITEMS` → "all" or specific item numbers (1-9)
   - `THRESHOLDS` → adjust if user specifies custom thresholds
4. Write adapted script to workspace and execute
5. If script fails: read error, fix the relevant function, retry
6. Present key findings in conversation + link to generated report file

### Inspection Report Template

报告需包含 Summary（Normal/Attention/Critical 项数）、Critical Issues 表、Attention Items 表、Normal Items 列表、Recommendations。详细报告模板与门阈说明见 [references/inspection-rules.md](references/inspection-rules.md)。

## Output Format

Always provide:

1. **Conversation summary**: Concise results directly in chat (key findings, any red/yellow items highlighted)
2. **Report file** (when inspection or multi-item query): Generate a markdown file saved to user's workspace

### Report File Generation

Use a deterministic filename based on instance ID and date (overwrite if re-run same day):

```python
import os
from datetime import datetime

report_content = "..."  # Generated report markdown
filename = f"SAG_Inspection_{sag_id}_{datetime.now().strftime('%Y%m%d')}.md"
output_path = os.path.join(workspace_dir, filename)

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(report_content)
```

### Data Sanitization & Consistency Rules

生成 CSV / Markdown 报告之前必须执行三项强制数据清洗与自校验（详细 jq / date / awk 脚本见 [references/contract-skeletons.md § Data Sanitization](references/contract-skeletons.md#data-sanitization--consistency-rules)）：

1. **Null 值兜底 + 字段名探测**：所有 `jq` 取字段处必须加 `// "N/A"` 兜底；带宽字段必须用 fallback 链 `.Bandwidth // .BandWidth // .MaxBandwidth // "N/A"`（API 实际返回 `MaxBandwidth`，文档常误写 `BandWidth`）；CCN 名称用 `.Name // .CcnName // "N/A"`；禁止 CSV 出现 `null`/`None`/空单元格（零实例区域占位行例外，必须写 `"no instances"`）。
2. **时间戳人类可读化**：`EndTime`/`ExpireTime`/`CreateTime` 等必须转 `YYYY-MM-DD`（用 `date -r` / `date -d`）；禁止在人类可读 CSV 中保留 epoch 原始值（需要 raw 另存 `*_raw.csv`）。
3. **表头/明细一致性断言**：Summary 声明的「共 X 个实例/X 个区域」必须与明细表实际行数严格一致；该数字必须由 `wc -l`/`jq length` 计算得到，禁止人肉估算；报告生成后的最后一步必须运行一致性断言，不一致则 exit 1。

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| InvalidRegionId | Wrong region | Ask user to confirm region, list common SAG regions |
| InvalidSmartAGId.NotFound | Instance doesn't exist in this region | Try other regions or ask user to verify |
| Forbidden / NoPermission | RAM policy insufficient | Tell user which permission is needed (smartag:Describe*) |
| Throttling | API rate limit | Wait and retry with backoff |
| MissingSmartAGSn | API requires device SN but not provided | Skip - instance has no physical device bound |
| SmartAccessGatewayNotOnline | Device is offline | Record status, cannot query live device config |
| Sag.DeviceNotExist | SN mismatch or multi-SN not split | Split comma-separated SN and retry individually |
| MissingSagId | `describe-dnat-entries` parameter issue | Use `--sag-id` instead of `--smart-ag-id` for this API |
| InvalidApi.NotFound | API may not exist in current version | Skip gracefully, note in report |

## Best Practices

1. **Classify instances before querying** — skip inapplicable APIs (sag-software has no device-level queries)
2. **Split multi-SN before device-level calls** — passing comma-separated SN causes DeviceNotExist errors
3. **Region-level APIs call once per region** — ACL/QoS/FlowLog/CCN are shared resources, not per-instance
4. **Report all failures transparently** — never silently skip; always note in report what was inaccessible and why
5. **No field-reuse substitution** — never use fields from the basic `describe-smart-access-gateways` response (such as `AssociatedCcnId`, `AclIds`, `VpnStatus`) as a substitute for calling the specialized API; the basic response is a classifier, not a substitute
6. **Save raw JSON to temp files** — redirect CLI responses to `/tmp/sag_*.json` (e.g. `aliyun smartag describe-xxx ... > /tmp/sag_<api>_<region>.json 2>&1`) and then summarize specific fields; avoid dumping full raw JSON into the conversation

## Known Unavailable APIs

The following APIs are known unavailable in the current SAG API version (`2018-03-13`). You MUST NOT call them — if a scenario appears to require them, explicitly declare in the report: "API X is unavailable in the current version; skipping this item" or substitute with the alternative:

| API | Status | Alternative |
|-----|--------|-------------|
| `describe-health-checks` / `describe-health-check-attribute` | Returns `InvalidApi.NotFound` | Skip Item #10 of the classic inspection; note in report |
| `describe-sag-online-client-statistics` | Returns `InvalidApi.NotFound` | Use `describe-smart-access-gateway-client-users` for APP user list |

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/openapi-reference.md](references/openapi-reference.md) | Complete OpenAPI parameter reference for 25+ SAG APIs |
| [references/contract-skeletons.md](references/contract-skeletons.md) | 详细 bash 骨架、Self-check、数据清洗规则（Contract A/B/C/D + Anti-Pattern + Sanitization） |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions (28 read-only actions) |
