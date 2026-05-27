# Acceptance Criteria: alibabacloud-ddos-native-intercept-query

**Scenario**: DDoS Native Protection (Anti-DDoS Origin) network-layer intercept record query, root-cause attribution, and false-positive remediation guidance.
**Purpose**: Skill testing acceptance criteria — every CLI command and behavior must match the patterns below.

---

# 1. Correct CLI Command Patterns

## 1.1 Product names

#### ✅ CORRECT
- `aliyun ddosbgp ...` — DDoS Native Protection (BGP) plugin
- `aliyun antiddos-public ...` — Anti-DDoS Public plugin

#### ❌ INCORRECT
- `aliyun ddos ...` — wrong product, does not exist
- `aliyun antiddos ...` — wrong product, missing `-public` suffix
- `aliyun ddos-bgp ...` — wrong product, should be `ddosbgp`

## 1.2 Action names — plugin-mode by default, OpenAPI fallback for plugin errors

Default to **plugin-mode kebab-case** for every action. Only when the plugin rejects an action with `unknown command` or `'<Action>' is not a valid api` (meaning the plugin metadata doesn't declare it) fall back to the **OpenAPI route**: `aliyun --auto-plugin-install false <product> <PascalCaseAction> --force` with PascalCase params and no `--version`.

#### ✅ CORRECT — plugin-mode kebab-case (default)
- `aliyun ddosbgp describe-network-layer-intercepts ...` (may fall back to OpenAPI on `aliyun-cli-ddosbgp` 0.3.0 — see below)
- `aliyun ddosbgp describe-instance-list ...`
- `aliyun ddosbgp list-policy-attachment ...`
- `aliyun ddosbgp list-policy ...`
- `aliyun antiddos-public describe-bgp-pack-by-ip ...`
- `aliyun antiddos-public describe-ip-location-service ...`
- `aliyun antiddos-public describe-instance-ip-address ...`

#### ✅ CORRECT — OpenAPI fallback (only after the plugin returns `unknown command` / `is not a valid api`)
- `aliyun --auto-plugin-install false ddosbgp DescribeNetworkLayerIntercepts --force --region <R> --InstanceId ... --StartTime ... --EndTime ... --PageNo 1 --PageSize 10` (the typical case on `aliyun-cli-ddosbgp` 0.3.0)

#### ❌ INCORRECT
- `aliyun ddosbgp describeNetworkLayerIntercepts ...` → camelCase is not supported.
- `aliyun ddosbgp DescribeNetworkLayerIntercepts --force ...` (PascalCase without bypass) → the plugin intercepts before `--force` applies and rejects with `'is not a valid api'`. You must add `--auto-plugin-install false`.
- `aliyun --auto-plugin-install false ddosbgp DescribeNetworkLayerIntercepts --force --version 2018-07-20 ...` → core CLI rejects with `unchecked version`; omit `--version` on the OpenAPI route.
- `aliyun --auto-plugin-install false ddosbgp DescribeNetworkLayerIntercepts --force --instance-id ... --start-time ...` → on the OpenAPI route, parameters must be PascalCase (`--InstanceId`, `--StartTime`).
- Reaching for the OpenAPI fallback before the plugin call has actually errored → use plugin-mode first; only fall back when the plugin metadata is the blocker.

## 1.3 Mandatory flags

Every call to `ddosbgp` and `antiddos-public` MUST include the `User-Agent` header (so Skills traffic can be audited). `--force` is required **only** on the OpenAPI fallback route.

#### ✅ CORRECT — plugin-mode (default)
```bash
aliyun ddosbgp list-policy-attachment \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query \
  --region cn-hangzhou --profile <profile> \
  --ip-port-protocol-list '[{"Ip":"<IP>"}]' --page-no 1 --page-size 10
```

#### ✅ CORRECT — OpenAPI fallback (after plugin errored)
```bash
aliyun --auto-plugin-install false ddosbgp DescribeNetworkLayerIntercepts --force \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query \
  --region cn-hangzhou --profile <profile> \
  --InstanceId <id> --StartTime <ts> --EndTime <ts> --PageNo 1 --PageSize 10
```

#### ❌ INCORRECT
- Missing `--header User-Agent=...` → Skills traffic can't be distinguished from manual traffic; audit/traceability is lost.
- Missing `--auto-plugin-install false` on the fallback route → plugin intercepts and rejects with `'DescribeNetworkLayerIntercepts' is not a valid api`.

## 1.4 `ListPolicy` invocation modes

#### ✅ CORRECT — query a custom IP-specific or Port-specific Mitigation Policy by name
```bash
aliyun ddosbgp list-policy --name <PolicyName> --page-no 1 --page-size 50 \
  --region <region> --profile <profile> --header User-Agent=...
```
> No `--type`, no `--product-type`.

#### ✅ CORRECT — query a default policy by name
```bash
aliyun ddosbgp list-policy --name <PolicyName> \
  --type default --product-type eip \
  --page-no 1 --page-size 50 \
  --region <region> --profile <profile> --header User-Agent=...
```
> Both `--type default` AND `--product-type` are required together.

#### ❌ INCORRECT
```bash
# Missing --product-type — server returns Invalid params. Invalid product type.
aliyun ddosbgp list-policy --type default --name normal --page-no 1 --page-size 50 ...
```

## 1.5 `--product-type` enum values

#### ✅ CORRECT values
- `eip` (Elastic IP — most common for DDoS Native Protection)
- `ecs` (ECS public IP)
- `slb` (SLB public IP)
- `gf-eip` (DDoS Pro EIP)

#### ❌ INCORRECT values
- `EIP`, `Eip` — case-sensitive, must be lowercase
- `gf_eip`, `gfeip` — must be `gf-eip` with hyphen
- `cdn`, `waf` — not valid product types here

## 1.6 `--network-protocol` enum values

#### ✅ CORRECT values
- `tcp`, `udp`, `icmp`

#### ❌ INCORRECT values
- `TCP`, `UDP`, `ICMP` — must be lowercase
- `http`, `https` — these are L7 protocols, not network-layer

## 1.7 `--ip-port-protocol-list` format

#### ✅ CORRECT — JSON array string (plugin-mode `list-policy-attachment`)
```bash
--ip-port-protocol-list '[{"Ip":"<instance_IP>"}]'
```

#### ❌ INCORRECT
```bash
--ip-port-protocol-list 47.118.170.18                 # not a JSON array
--ip-port-protocol-list '{"Ip":"47.118.170.18"}'      # missing outer array
--ip-port-protocol-list '["47.118.170.18"]'           # missing Ip key
```

## 1.8 Timestamp format

#### ✅ CORRECT — Unix seconds (plugin-mode `--start-time` / `--end-time`; OpenAPI fallback `--StartTime` / `--EndTime`)
```bash
--start-time $(($(date +%s) - 3600)) --end-time $(date +%s)
```

#### ❌ INCORRECT
```bash
--start-time 2026-05-21T10:00:00Z                   # ISO 8601 not accepted here
--start-time 1716264000000                          # milliseconds, must be seconds
```

## 1.9 30-day window cap

#### ✅ CORRECT
- `EndTime - StartTime <= 2592000` (30 days). For longer windows, split into multiple calls.

#### ❌ INCORRECT
- Sending a single call with a 60-day window — server rejects; intercept on the client side instead.

---

# 2. Authentication Patterns

## 2.1 Credential probing

#### ✅ CORRECT
```bash
aliyun configure list
```

#### ❌ INCORRECT (security violations)
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID                  # never echo AK/SK
cat ~/.aliyun/config.json                          # don't print credential storage
aliyun configure set --access-key-id AKID...       # never set literal credentials in chat
```

## 2.2 No credentials in CLI invocation

#### ❌ INCORRECT
```bash
aliyun ddosbgp list-policy --access-key-id AKID... --access-key-secret SECRET...
```
> Credentials MUST be configured outside the session via `aliyun configure` or environment variables.

---

# 3. AI-Mode Lifecycle Patterns

## 3.1 Enable at start

#### ✅ CORRECT — before any business CLI call
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query"
```

## 3.2 Disable at every exit

#### ✅ CORRECT — before delivering the final response, on every code path (success / failure / error / cancellation)
```bash
aliyun configure ai-mode disable
```

#### ❌ INCORRECT
- Skipping `ai-mode disable` because the workflow errored out.
- Disabling only on the happy path.

---

# 4. Workflow Pattern Anti-Patterns

#### ❌ INCORRECT — pre-validating the environment before any business work
- Running `aliyun version` / `aliyun plugin list` / `aliyun configure list` proactively before the user has asked a question.
- The skill prescribes **optimistic execution**: go straight to the business commands; diagnose only when a command fails.

#### ❌ INCORRECT — using AskUserQuestion for free-text input
- Asking for IP or InstanceId via AskUserQuestion options. These need precise free-text input → use plain text prompting instead.
- AskUserQuestion's "Other" field is only appropriate for time-range input (free-form natural language that the model can parse).

#### ❌ INCORRECT — silent "no intercepts" on errors
- When `DescribeNetworkLayerIntercepts` times out or returns 5xx, never report "no intercepts found." Surface the original error (including RequestId) instead.

#### ❌ INCORRECT — reporting protection pack attributes inside the intercept overview
- Do NOT mix `BaseThreshold` / `ElasticThreshold` / `ExpireTime` (scrubbing thresholds and billing data) into the intercept analysis report.

#### ❌ INCORRECT — claiming "system anomaly" for `packet_filter` records that don't match `PortRuleList`
- The correct attribution is the **default policy** (template-built-in or AI-deployed) or residual records from a historically deleted rule. See `packet-filter-edge-cases.md`.

---

# 5. Output Format Patterns

## 5.1 Report has exactly 5 sections

#### ✅ CORRECT structure
1. Intercept Overview
2. Intercept Distribution (grouped by `InterceptModule`)
3. Policy Correlation (every module of IP-specific and Port-specific Mitigation Policies listed, even if "Not configured")
4. Root Cause Analysis
5. Remediation Recommendations

## 5.2 Default policy display

#### ✅ CORRECT — show console display name only
- `Remark` non-empty → use `Remark`
- `Remark` empty → map `Name` to display name per `default-policy-details.md`

#### ❌ INCORRECT
- Showing the internal `Name` (e.g. `gf_origin_protect_eip_loose`) directly to the user.
