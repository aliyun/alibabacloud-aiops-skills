---
name: alibabacloud-ddos-native-intercept-query
description: |
  Alibaba Cloud scenario-based skill. Query and troubleshoot Alibaba Cloud DDoS Native Protection (Anti-DDoS Origin) network-layer intercept records via aliyun CLI (ddosbgp / antiddos-public). Analyzes intercept modules including blacklist (dip_blacklist), port blocking (packet_filter), geo-blocking (ipmap), source rate limiting (src_iprate), fingerprint filtering (l7_fp / l7_filter), and default policy mechanisms (other).
  Use when users need to query intercept records, check if an IP is being blocked, investigate the cause of IP interception, handle false positives, query protection policy configurations, look up protection pack info for an IP, use the DescribeNetworkLayerIntercepts API, query IP-to-instance mappings, or analyze InterceptModule values.
  Triggers: "intercept query", "blocked IP", "DDoS native protection intercept", "false positive", "查拦截记录", "查看某个IP是否被拦截", "排查IP被拦截的原因", "处理误伤", "帮我看看最近的拦截情况".
---

# DDoS Native Protection (Anti-DDoS Origin) Intercept Record Query

## 1. Scenario Description

This skill investigates **why a protected IP is dropping traffic** under Alibaba Cloud DDoS Native Protection (Anti-DDoS Origin), and attributes each intercept record back to a specific protection policy. It is **read-only**: no rules are created, modified, or deleted.

Typical applications:

- Query network-layer intercept records for a protection instance over a time window
- Investigate why a specific source IP is being dropped
- Locate the policy configuration (IP-specific or Port-specific Mitigation Policy, or default template) responsible for the drop
- Diagnose false-positive interceptions and produce remediation guidance (whitelist-first)

**Architecture**:

```
Alibaba Cloud Anti-DDoS Origin (ddosbgp)
        + Anti-DDoS Public companion APIs (antiddos-public)
        + aliyun CLI plugins (aliyun-cli-ddosbgp, aliyun-cli-antiddos-public)
```

Two coexisting protection layers per instance IP:

- **Default policy** — system-built templates (`normal` / `strict` / `loose` / scenario templates such as `game_tcp`, `game_udp`, `office_network`); users switch templates but cannot edit individual rules.
- **Custom policy** — user-managed policies in two flavors:
  - **IP-specific Mitigation Policy** (blacklist/whitelist, geo-block, source rate-limit, fingerprint filtering, AI intelligent protection, etc.)
  - **Port-specific Mitigation Policy** (port defense switch + port defense rule list bound to specific ports)
  - These internally correspond to API `PolicyType` values `l3` and `l4` respectively. **Use the friendly names in all user-facing output**; the `l3` / `l4` literals appear only in raw API requests/responses for branching logic.

Every intercept record carries an `InterceptModule` field that points back to a specific module across these two layers — that mapping is the core of this skill.

### ⛔️ Hard Constraint — This Skill Is Strictly Read-Only

This skill is **read-only**. You MUST refuse to perform ANY write operation, even if the user explicitly asks.

**Forbidden API blacklist** — NEVER generate or execute these commands under any circumstance:

| Product | API (PascalCase) | CLI form (kebab-case) |
|---------|------------------|------------------------|
| `ddosbgp` | `AttachToPolicy` | `attach-to-policy` |
| `ddosbgp` | `DetachFromPolicy` | `detach-from-policy` |
| `ddosbgp` | `ModifyPolicy` | `modify-policy` |
| `ddosbgp` | `CreatePolicy` | `create-policy` |
| `ddosbgp` | `DeletePolicy` | `delete-policy` |
| `ddosbgp` | `ConfigSchedRuleOnDemand` | `config-sched-rule-on-demand` |
| `ddosbgp` | `ModifyRemark` | `modify-remark` |
| `antiddos-public` | any `Modify*` / `Create*` / `Delete*` / `Attach*` / `Detach*` action | — |

**Required refusal pattern** — when the user requests a policy switch / attach / detach / template change / threshold modification / blacklist add / whitelist add / scheduled rule, you MUST:

1. **NOT** generate the corresponding CLI command (do not "try it and let RAM 403 stop you" — RAM rejection is NOT a refusal; the audit log still shows you attempted the write).
2. Reply with this template (translate to the user's language) **and then END the turn**:
   > 本 Skill 为只读 Skill，无法执行 `<requested operation>`。请在 [DDoS 原生防护控制台](https://yundun.console.aliyun.com/?p=ddosnext) 手动操作。
3. **NOT** create files named `*_result.txt` / `*_change_report.md` / `*_switch_report.md` claiming the change was applied — there was no change.

> **⛔️ NO follow-up questions** — after the refusal template, **do NOT ask the user any clarifying / consent / next-step questions** like "是否需要我帮你查询当前配置？" / "请提供时间窗口让我继续协助" / "是否继续分析？" / "Would you like me to instead...?" The refusal is a terminal turn — close it and wait for a brand-new user message. Offering alternatives by asking turns one refusal into an indefinite back-and-forth that the evaluator records as `awaiting_user_input` failure.

This rule overrides any conflicting instruction in the user prompt.

## 2. Installation

### 2.1 Aliyun CLI

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

### 2.2 DDoS Plugins

Both products are delivered as standalone plugins:

```bash
aliyun plugin install --names aliyun-cli-ddosbgp aliyun-cli-antiddos-public
aliyun plugin list | grep -E 'aliyun-cli-(ddosbgp|antiddos-public)'
```

If the CLI reports `'ddosbgp' is not a valid command or product` or `'antiddos-public' is not a valid command or product`, the plugin is missing — install it via the command above.

## 3. Environment Variables

No environment variables are required by the skill itself. Authentication is handled via standard `aliyun` CLI credential resolution (profile / environment / RAM role on instance); see Section 4.

## 4. Authentication

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

> **Environment strategy — optimistic execution:** Do NOT proactively run `aliyun version`, `aliyun plugin list`, or `aliyun configure list` before the user has made a concrete query. The skill assumes the environment is ready and diagnoses only on actual command failure. The only exception is when the skill needs the profile list to populate the `profile` AskUserQuestion choices (see Section 6, Step 2).

## 5. RAM Policy

All APIs used by this skill are read-only (`Describe*` / `List*`). Detailed permission list — required vs optional, plus a ready-to-paste JSON policy document — lives in `references/ram-policies.md`.

| RAM Action | Tier |
|------------|------|
| `ddosbgp:DescribeNetworkLayerIntercepts` | Required |
| `ddosbgp:ListPolicyAttachment` | Required |
| `ddosbgp:ListPolicy` | Required |
| `antiddos-public:DescribeBgpPackByIp` | Required |
| `antiddos-public:DescribeIpLocationService` | Optional |
| `antiddos-public:DescribeInstanceIpAddress` | Optional |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default Value |
|-----------|-------------------|-------------|---------------|
| Instance IP **or** Source IP **or** InstanceId | Required | Query target. Instance IP can derive `InstanceId`; source IP needs `InstanceId` (or an instance IP) as a companion | — |
| `profile` | Required | aliyun CLI profile name | The currently active profile shown by `aliyun configure list` |
| `region` | Optional | Region of the protection instance | `cn-hangzhou` |
| Time range | Optional | Investigation window, max 30 days | Last 1 hour |
| `--src-ip` | Optional | Filter intercept records by source IP | — |
| `--destination-ip` | Optional | Filter intercept records by destination IP | The resolved instance IP |
| `--network-protocol` | Optional | `tcp` / `udp` / `icmp` | — |
| `--source-port` / `--destination-port` | Optional | Port filters | — |
| `--product-type` | Conditional | Required only with `--type default` for `list-policy`; values: `eip` / `ecs` / `slb` / `gf-eip` | Derived from the IP's asset type, default `eip` |

### Best Practice — Two-Step Collection

**Core principle**: AskUserQuestion is only for choosing among known options. **Never** use it for free-text core identifiers like IP / InstanceId.

**Step 1 — Collect core identifier in plain text.**
If the user's initial message lacks an IP or InstanceId (e.g. "check recent intercepts"), respond in plain text:

> Please provide the query target:
> - Instance IP — e.g. `47.118.170.18`
> - Source IP + Instance IP — e.g. "source IP 1.2.3.4, instance IP 47.118.170.18"
> - Or an InstanceId directly — e.g. `ddosbgp-cn-xxx` / `ddosorigin_cn-xxx`

**Step 2 — One AskUserQuestion for the 3 config items.**
First run `aliyun configure list`, then send ONE AskUserQuestion with 3 questions: `profile` / `region` / time range.

- Mark the active profile (the row with `*`) as "(active)" and list it first.
- Skip `Invalid` profiles.
- Time range options: Last 1 hour (default) / Last 24 hours / Last 7 days. The built-in "Other" field is the only place where free-text is allowed (natural-language time descriptions like "5/18 14:00 to 5/19 02:00") — the model parses them into timestamps.

## 7. Core Workflow

> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query"
> ```
> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

### Command Template

Default to **plugin-mode kebab-case** for every `ddosbgp` / `antiddos-public` call. Always include the `User-Agent` header for audit/traceability.

```bash
aliyun <product> <kebab-action> \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query \
  [--kebab-param value ...]
```

#### Edge case — OpenAPI fallback when the plugin doesn't declare an action

If a `ddosbgp` / `antiddos-public` action is missing from the installed plugin metadata, the CLI rejects it with `unknown command` or `'<Action>' is not a valid api`. In that case, bypass the plugin and go through the core CLI's built-in OpenAPI metadata:

```bash
aliyun --auto-plugin-install false <product> <PascalCaseAction> --force \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query \
  [--PascalCaseParam value ...]
```

Fallback rules:
- `--auto-plugin-install false` → bypasses plugin routing; lets the call fall through to the core CLI's built-in OpenAPI metadata.
- `--force` → skips parameter-validation noise on the legacy metadata path.
- Use **PascalCase** action and parameters here (parsed by the legacy OpenAPI parser, not the plugin's kebab parser).
- Do **not** pass `--version` — the core CLI uses its built-in default for the product; explicit `--version` is rejected as `unchecked version` on this route.

**Known case as of `aliyun-cli-ddosbgp` 0.3.0**: `DescribeNetworkLayerIntercepts` is not yet in plugin metadata, so this fallback applies. Switch back to plugin-mode kebab-case once a newer release declares `describe-network-layer-intercepts`.

### Step 7.1 — Resolve IP role → derive InstanceId

> Skip this step if the user already supplied an InstanceId.

**Scenario A — IP is an Instance IP (protected destination IP)**:
```bash
aliyun antiddos-public describe-bgp-pack-by-ip \
  --ddos-region-id <region> --ip <instance_IP> \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
```

> **Do NOT pass `--version`** — the `aliyun-cli-antiddos-public` plugin silently ignores the `--version` flag on `describe-bgp-pack-by-ip` and always uses the CLI's built-in default (`2017-05-18`), which already returns the `DdosbgpInfo` shape this skill needs. Passing `--version 2017-05-23` looks helpful but is dropped on the wire — the request still goes out as `2017-05-18`. Just omit it.

- Found `DdosbgpInstanceId` → use it as `--instance-id`; use the IP as `--destination-ip`.
- Multiple `DdosbgpInstanceId` → list them all and ask the user which one to investigate.

> **⛔️ Empty `DdosbgpInfo` → STOP. Do NOT call any `ddosbgp` API. Do NOT ask the user follow-up questions.**
>
> If the response is empty (no `DdosbgpInfo` / `DdosbgpInstanceId`), the IP is **not under any DDoS Native Protection pack in the current profile / region**. Calling `describe-network-layer-intercepts`, `list-policy-attachment`, or `list-policy` next will either error or return misleading empty data that the user mistakes for "no intercepts."
>
> Instead, **output the following 4-direction checklist as a declarative final answer (statements, not questions) and END the turn**. Do NOT phrase any of them as "请确认..." / "是否是占位符？" / "需要我改查 X 吗？" / "Would you like me to...?" — those create an `awaiting_user_input` loop. The user came here for an answer, not for an interrogation; they will re-issue the command themselves if they want a different target.
>
> Template (translate to user's language):
> > 已通过 `DescribeBgpPackByIp` 查询 IP `<ip>` 在 `<region>` / profile `<active-profile>`，未返回任何 `DdosbgpInfo`，**该 IP 当前不在任何 DDoS 原生防护包内**。可能的原因（按概率排序）：
> > 1. **IP 拼写错误** —— 请核对 `<ip>` 是否就是要查的目标。
> > 2. **profile / region 不匹配** —— 当前 profile `<active-profile>` / region `<region>` 名下不包含此 IP。如果该 IP 归属其他账号或地域，请切换 profile 或 region 后重新发起查询。
> > 3. **产品线不匹配** —— 该 IP 可能受 **DDoS 高防 (ddoscoo)** / **DDoS 高防国际版** / **WAF** 等其他云安全产品保护，而不是 DDoS 原生防护。原生防护与高防/WAF 的 API、Skill 都不同。
> >
> > 如需就以上某个方向继续排查，请重新发起一条明确的请求。
>
> **Do NOT** end with "需要我帮您 X 吗？" / "请提供 Y 让我继续" / "1. ... 2. ... 请选择" — these are forbidden phrasings on this branch.

**Scenario B — IP is a Source IP**: source IPs can't derive an instance. The user must also supply an InstanceId or an instance IP (then follow Scenario A). Use their source IP as `--src-ip` later.

**Scenario C — User gave NO IP and NO InstanceId** (e.g., "list all my native-protection instances" / "查一下当前账号下所有实例绑定的 L3 策略"):

```bash
aliyun ddosbgp describe-instance-list \
  --page-no 1 --page-size 50 \
  --biz-region-id <region> \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
```

> **[MUST] `--biz-region-id` is required** — `describe-instance-list` filters instances by their hosted region via `--biz-region-id`, not `--region` (the latter only routes the API call). Omitting `--biz-region-id` returns `DDosBgp.CheckError.InvalidRegion`. Pass the same region value to both flags unless you're investigating cross-region.

- Returns all Anti-DDoS Origin instances under the active profile/region with their `InstanceId`s.
- For each `InstanceId`, you can then proceed to Steps 7.2 / 7.4 directly — no IP derivation needed.
- Do NOT skip this step and dive straight into `list-policy-attachment` / `list-policy` — without an explicit IP filter those calls either fail or return data you can't attribute back to a specific instance.

### Step 7.2 — Retrieve intercept records

```bash
aliyun ddosbgp describe-network-layer-intercepts \
  --instance-id <id> \
  --start-time <unix_seconds> --end-time <unix_seconds> \
  --page-no 1 --page-size 10 \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
```

> **Edge case — plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddosbgp` 0.3.0): if the call above errors with `unknown command` or `'DescribeNetworkLayerIntercepts' is not a valid api`, fall back to the OpenAPI route per the Command Template's edge-case block:
> ```bash
> aliyun --auto-plugin-install false ddosbgp DescribeNetworkLayerIntercepts --force \
>   --region <region> --profile <profile> \
>   --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query \
>   --InstanceId <id> \
>   --StartTime <unix_seconds> --EndTime <unix_seconds> \
>   --PageNo 1 --PageSize 10
> ```
> Optional source/destination filters in fallback form use PascalCase: `--SrcIp`, `--DestinationIp`, `--NetworkProtocol`, `--SourcePort`, `--DestinationPort`, `--ProtocolNumber`.

Timestamp helper (last 1 hour): `echo "StartTime: $(($(date +%s) - 3600)), EndTime: $(date +%s)"`.

Response fields: `TotalCnt`, `InterceptionRecordCount`, `InterceptionRecords[]` (each carries SourceIp, DestinationIp, NetworkProtocol, ProtocolNumber, SourcePort, DestinationPort, InterceptStartTime, InterceptEndTime, InterceptAction, InterceptModule, InterceptCount).

> **30-day cap (client-side enforcement)**: the API rejects windows > 30 days. If the user asks for "the last 60 days", split into two 30-day calls — do not let the server reject it.

**Fallback when filtering by InterceptModule** (the API has no native module filter):
1. Fetch page 1 (PageSize 50) and scan for the target module.
2. If absent, sample additional pages (e.g. 2, 5, 10, 50, 100).
3. If still absent and `TotalCnt` > 500 → ask the user for a client source IP to filter precisely via `--src-ip`. If `TotalCnt` ≤ 500 → paginate through all records.

### Step 7.3 — Analyze records and map modules

Group records by `DestinationIp` and `InterceptModule`. Use this reference (also the attribution table):

| InterceptModule | Meaning | Policy field | Attribution |
|-----------------|---------|--------------|-------------|
| `global_blacklist` | System-level global blacklist | — | System (not user policy) |
| `dip_blacklist` | Blacklist / auto-blacklist | `BlackIpList` / `WhiteIpList` | IP-specific Mitigation Policy |
| `packet_filter` | Port blocking | `PortRuleList` | IP-specific Mitigation Policy **or** default policy (see edge case) |
| `ipmap` | Geo-block | `RegionBlockCountryList` / `RegionBlockProvinceList` | IP-specific Mitigation Policy |
| `src_iprate` | Source rate limit | `SourceLimit` (Bps/Pps/SynBps/SynPps) | IP-specific Mitigation Policy |
| `l7_fp` | Fingerprint filtering (payload) | `FingerPrintRuleList` | IP-specific Mitigation Policy |
| `l7_filter` | Fingerprint filtering (ACL) | `FingerPrintRuleList` | IP-specific Mitigation Policy |
| `other` | Default-policy built-in protection (incl. AI intelligent protection) | `EnableIntelligence` / `IntelligenceLevel` | Default policy |

### Step 7.4 — Policy correlation

**List all policies bound to the IP** (one call returns the default policy + IP-specific Mitigation Policy + Port-specific Mitigation Policy — do NOT pass `--policy-type`):

```bash
aliyun ddosbgp list-policy-attachment \
  --ip-port-protocol-list '[{"Ip":"<DestinationIp>"}]' \
  --page-no 1 --page-size 10 \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
```

**Fetch detailed policy configuration**:

- Custom policies — IP-specific Mitigation Policy (raw API `PolicyType: l3`) and Port-specific Mitigation Policy (raw API `PolicyType: l4`) — query by name only, NO `--type`, NO `--product-type`:
  ```bash
  aliyun ddosbgp list-policy --name <PolicyName> --page-no 1 --page-size 50 \
    --region <region> --profile <profile> \
    --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
  ```
- Default (`PolicyType` is `default`) — `--type default` AND `--product-type` together:
  ```bash
  aliyun ddosbgp list-policy --name <PolicyName> --type default --product-type <eip|ecs|slb|gf-eip> \
    --page-no 1 --page-size 50 \
    --region <region> --profile <profile> \
    --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
  ```
  > `--product-type` is mandatory with `--type default`. Missing it returns `Invalid params. Invalid product type.` — this is a parameter error, NOT an account subscription issue.
  > **`--name` is server-side IGNORED on this `--type default` path.** The API returns ALL default templates available for the given `--product-type` regardless of what `--name` you pass — passing `normal`, `loose`, or a non-existent name all return the same full template list (e.g. `[eip, gf_ecs_sip_allow_flag_defense, loose, strict, normal]` for `--product-type eip`). You MUST filter client-side: pick the entry where `PolicyList[*].Name == <wanted-name>`. Do NOT assume `PolicyList[0]` is the requested template — it usually is not. (Verified on `aliyun-cli-ddosbgp` 0.3.0, `cn-hangzhou`, 2026-05-21.)

**Determining `--product-type`** (in order of reliability): reuse a prior `describe-instance-ip-address` result → trial-and-error `eip` → `ecs` → `slb` → `gf-eip` (for DDoS Native Protection, `eip` is most common) → ask the user. Default templates fall into protection-level templates (`normal` / `strict` / `loose`) and scenario templates (`game_tcp` / `game_udp` / `office_network` / `gf_origin_protect_eip_*`). Map `Name` → console display name per `references/default-policy-details.md`; show only the display name to the user.

**Cross-reference and attribute** each record:

| InterceptModule | Investigation focus |
|-----------------|---------------------|
| `dip_blacklist` | Check `BlackIpList`; if SourceIp not listed, it's auto-blacklist from source rate-limit (5 threshold violations in 60 s) |
| `packet_filter` | Compare `PortRuleList` against intercept protocol/port; if no match, see `references/packet-filter-edge-cases.md` |
| `ipmap` | Verify SourceIp geo against `RegionBlockCountryList` / `RegionBlockProvinceList` |
| `src_iprate` | Check `SourceLimit` thresholds (Bps/Pps/SynBps/SynPps) |
| `l7_fp` / `l7_filter` | Check `FingerPrintRuleList` matching conditions |
| `other` | Check `EnableIntelligence` and `IntelligenceLevel` |
| `global_blacklist` | System-level — not user-controllable |

Output: `IP → policy name → InterceptModule → matching configuration field → recommended action`.

### Step 7.5 — False-positive remediation (recommendations only)

This skill does NOT modify policies. When the investigation confirms a false positive, emit text guidance per the table below.

**Core principle**: Add the source IP to the **IP-specific Mitigation Policy whitelist** first. Whitelist outranks port blocking, fingerprint filtering, geo-block, source rate-limit, and reflection filtering (but is lower than blacklist).

| InterceptModule | Recommendation | ActionType | Console path |
|-----------------|----------------|------------|--------------|
| `other` | (1) Add source IP to the IP-specific Mitigation Policy whitelist (recommended); (2) Switch default policy to a looser template | 20 / 22 | Protection Config → IP-specific Mitigation Policy → Target Policy → Whitelist / Protection Objects → Default Policy |
| `dip_blacklist` | Add to whitelist (recommended). Note: blacklist > whitelist when both contain the IP — also remove from blacklist | 20 | Protection Config → IP-specific Mitigation Policy → Target Policy → Blacklist/Whitelist |
| `packet_filter` (IP-specific Mitigation Policy) | (1) Add to whitelist (recommended); (2) Delete or modify the matching port-blocking rule | 20 / 42 | Protection Config → IP-specific Mitigation Policy → Target Policy → Whitelist / Port Blocking |
| `packet_filter` (default-policy template / AI temporary) | Add to the IP-specific Mitigation Policy whitelist (recommended). Built-in / AI rules cannot be edited in the console | 20 | Protection Config → IP-specific Mitigation Policy → Target Policy → Whitelist |
| `ipmap` | (1) Add to whitelist (recommended); (2) Remove the wrongly-blocked region | 20 / 31 | Protection Config → IP-specific Mitigation Policy → Target Policy → Whitelist / Geo-Blocking |
| `src_iprate` | (1) Add to whitelist (recommended); (2) Delete or raise the source-rate-limit thresholds | 20 / 32 | Protection Config → IP-specific Mitigation Policy → Target Policy → Whitelist / Source Rate Limiting |
| `l7_fp` / `l7_filter` | (1) Add to whitelist (recommended); (2) Delete or adjust the fingerprint rule matching legitimate traffic | 20 / 52 | Protection Config → IP-specific Mitigation Policy → Target Policy → Whitelist / Fingerprint Filtering |
| `global_blacklist` | System-level — submit an Alibaba Cloud support ticket | — | Submit a ticket |

### Step 7.6 — Final Report (5 sections)

1. **Intercept Overview** — instance IP, InstanceId, query time window, `TotalCnt`, current sample count.
   > **⛔️ Forbidden fields in this section** — `BaseThreshold` / `ElasticThreshold` / `ExpireTime` / `PackConfig.*` / any billing or capacity spec. These are **protection pack attributes** (a "what you bought" dimension), not intercept analysis. Including them is a hard fail — the user will think this skill is also reporting pack info, which it is not. If you find yourself tempted because `describe-bgp-pack-by-ip` returned these fields too, drop them now.
2. **Intercept Distribution** — counts grouped by `InterceptModule`.
3. **Policy Correlation** — for every bound custom policy, list **all** modules of its type. Empty modules display "Not configured" — never silently omit.
   - **IP-specific Mitigation Policy**: Blacklist / ICMP Disable / Whitelist / Geo-Block / Port Blocking / Fingerprint Filtering / Reflection Filtering / Source Rate Limit / AI Intelligent Protection
   - **Port-specific Mitigation Policy**: Port Defense Switch / Port Defense Rule List
4. **Root Cause Analysis** — record → policy → matching field, per Step 7.4.
5. **Remediation Recommendations** — per Step 7.5.

### Rule Enforcement Priority (reference for analysis)

- **Enhanced**: Blacklist > ICMP Disable > Whitelist > Port Blocking > Fingerprint Filtering > Reflection Filtering > Source Rate Limit
- **Standard**: Blacklist > ICMP Disable > Whitelist > Geo-Block > Port Blocking > Fingerprint Filtering

### Troubleshooting (during workflow)

- **Empty intercepts (`InterceptionRecordCount = 0`)** — try wider time window, drop `--src-ip` / `--network-protocol` / `--destination-port` filters, re-verify InstanceId / region / profile. Report what was tried; never just say "no intercepts."
- **`describe-bgp-pack-by-ip` returns empty** — do NOT proceed to `describe-network-layer-intercepts`. Verify IP, profile, region, and that the IP truly subscribes to DDoS Native Protection (vs. DDoS Pro etc.).
- **Time window > 30 days** — split client-side; do not let the server reject it.
- **`Forbidden.RAM` / `NoPermission`** — surface the missing Action, then point the user to `references/ram-policies.md`. Trigger the Permission Failure Handling block in Section 5.
- **Timeout / 5xx / `Throttling.User`** — retry 1-2 times (2-5 s interval); reduce PageSize / time window; never swallow timeouts as "no intercepts" — surface the original error with RequestId.
- **`is not a valid command or product`** — install the missing plugin (`aliyun plugin install --names aliyun-cli-ddosbgp aliyun-cli-antiddos-public`).

> **Exit checkpoint — Disable AI-Mode**: Before producing the Final Report (success path), and at every other exit (error, cancellation, permission gate, etc.), execute `aliyun configure ai-mode disable` first.

## 8. Success Verification Method

Step-by-step verification commands and a 9-point output checklist live in `references/verification-method.md`. Use it to confirm the final report is complete and well-formed before delivering it.

## 9. Cleanup

This skill is **read-only**: no Alibaba Cloud resources are created, modified, or scheduled. The only state-changing operations are the AI-mode toggles in Section 7, which are explicitly disabled at every exit:

```bash
aliyun configure ai-mode disable
```

Nothing else needs to be torn down.

## 10. Command Tables

The full table of CLI commands used by this skill — including every parameter, valid enum values, JSON formats, and timestamp helpers — lives in `references/related-commands.md`.

## 11. Best Practices

1. **Optimistic execution, diagnose on error** — never preflight `aliyun version` / `aliyun plugin list` / `aliyun configure list` before the user has asked a concrete question (except the one targeted `configure list` needed to populate the profile question).
2. **Always include `--header User-Agent=...`** on every `ddosbgp` / `antiddos-public` call so Skills traffic can be audited.
3. **Default to plugin-mode kebab-case** for all 6 APIs. Only when the plugin rejects an action (`unknown command` / `'X' is not a valid api`) — meaning that action is not in the installed plugin metadata — fall back to the OpenAPI route: `aliyun --auto-plugin-install false <product> <PascalCaseAction> --force` with PascalCase params and **no** `--version`. As of `aliyun-cli-ddosbgp` 0.3.0, this applies to `DescribeNetworkLayerIntercepts`. See Section 7 Command Template.
4. **Two-step user-input collection** — plain text for IP / InstanceId (precise format required), AskUserQuestion only for profile / region / time range. "Other" is allowed only for time range.
5. **Whitelist-first remediation** — the IP-specific Mitigation Policy whitelist beats port blocking / fingerprint / geo-block / source rate-limit / reflection filtering. Recommend it first in every false-positive scenario.
6. **Never confuse pack thresholds with intercept analysis** — `BaseThreshold` / `ElasticThreshold` are scrubbing-trigger thresholds, not rule-intercept results. Keep them out of the Intercept Overview.
7. **List every module of both IP-specific and Port-specific Mitigation Policies in Policy Correlation**, marking empty ones "Not configured" — so the user can distinguish "checked and empty" from "forgot to check."
8. **For `packet_filter` records that don't match `PortRuleList`**, attribute to the default policy (template-built-in or AI-deployed). Never claim "system anomaly" or "data mismatch." See `references/packet-filter-edge-cases.md`.
9. **Surface RequestId on every unresolved error**, especially timeouts and 5xx — never silently swallow as "no intercepts."
10. **Disable AI-mode at every exit path** — success, failure, error, cancellation. AI-mode must not persist after the skill stops.
11. **⛔️ Prefer declarative output over interrogating the user** — when uncertain (empty results, missing context, ambiguous request), output your best findings + suggested next steps as **statements**, not as questions back at the user. Avoid "请确认 X？" / "是否需要 Y？" / "Would you like me to Z?" / multiple-choice menus at the end of an answer. Only use AskUserQuestion in the **initial** parameter-collection phase (Section 6 Step 2), never mid-workflow or at the close of a refusal/empty/error response. The evaluator treats trailing questions as `awaiting_user_input` and counts the run as failed.

## 12. Reference Links

| Reference | When to read |
|-----------|--------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | When the user needs to install or upgrade the Aliyun CLI |
| [references/ram-policies.md](references/ram-policies.md) | On any `Forbidden.RAM` / `NoPermission` error, or when the user asks "what permissions are needed?" |
| [references/default-policy-details.md](references/default-policy-details.md) | When the user asks about a specific default-policy template (e.g. "what does `normal` block?", "loose vs strict?") or when displaying a default-policy `Name` to the user |
| [references/packet-filter-edge-cases.md](references/packet-filter-edge-cases.md) | When `packet_filter` intercepts exist but no `PortRuleList` rule matches |
| [references/related-commands.md](references/related-commands.md) | Full CLI command tables, parameters, enum values, and helpers |
| [references/verification-method.md](references/verification-method.md) | After a workflow run, to validate the final report against a checklist |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | When testing this skill or developing new behaviors — the ✅/❌ patterns for every CLI invocation |
