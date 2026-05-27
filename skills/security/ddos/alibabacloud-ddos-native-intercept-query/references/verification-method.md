# Success Verification Method

This skill performs **read-only** investigation; no resources are created or modified. "Success" means: the investigation reached a definitive conclusion that the user can act on, and every CLI call returned a parseable response (or a documented, expected empty result).

## Step-by-Step Verification

### Step 1 — Verify environment readiness

```bash
aliyun version
aliyun plugin list | grep -E 'aliyun-cli-(ddosbgp|antiddos-public)'
aliyun configure list
```

**Expected:**
- `aliyun version` ≥ `3.3.3`
- Both `aliyun-cli-ddosbgp` and `aliyun-cli-antiddos-public` plugins are present
- At least one profile with `Valid` credential status

### Step 2 — Verify IP role / InstanceId derivation

```bash
aliyun antiddos-public describe-bgp-pack-by-ip \
  --ddos-region-id <region> --ip <instance_IP> \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
```

**Expected:** Response contains a non-empty `DdosbgpInstanceId` (e.g. `ddosbgp-cn-xxx` or `ddosorigin_cn-xxx`).

**Failure modes:**
- Empty `InstanceList` → IP is not under any protection pack in the current profile/region. The skill should prompt the user to verify IP / switch profile / switch region before continuing.
- Multiple `DdosbgpInstanceId` → list all of them and ask the user which one to query.

### Step 3 — Verify intercept records query

```bash
aliyun ddosbgp describe-network-layer-intercepts \
  --instance-id <instance_ID> \
  --start-time $(($(date +%s) - 3600)) --end-time $(date +%s) \
  --page-no 1 --page-size 10 \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
```

> **Edge case** — on `aliyun-cli-ddosbgp` 0.3.0 this action is not in plugin metadata, so the call above errors with `unknown command` or `'DescribeNetworkLayerIntercepts' is not a valid api`. Fall back to the OpenAPI route per `related-commands.md` Command Template:
> ```bash
> aliyun --auto-plugin-install false ddosbgp DescribeNetworkLayerIntercepts --force \
>   --region <region> --profile <profile> \
>   --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query \
>   --InstanceId <instance_ID> \
>   --StartTime $(($(date +%s) - 3600)) --EndTime $(date +%s) \
>   --PageNo 1 --PageSize 10
> ```

**Expected:** Response contains `TotalCnt`, `InterceptionRecordCount`, and an `InterceptionRecords` array.

**Empty `InterceptionRecordCount = 0` is not a failure** — the skill must report which time window and which filters were tried, so the user can decide whether to query again with wider parameters.

### Step 4 — Verify policy attachment query

```bash
aliyun ddosbgp list-policy-attachment \
  --ip-port-protocol-list '[{"Ip":"<DestinationIp>"}]' \
  --page-no 1 --page-size 10 \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
```

**Expected:** Response contains an `AttachmentList` with at least one entry; each entry has `PolicyName`, `PolicyId`, and `PolicyType`. The raw `PolicyType` value is one of `default` (default policy), `l3` (IP-specific Mitigation Policy), or `l4` (Port-specific Mitigation Policy). Use the literal value for branching only; show the friendly name in any user-facing output.

### Step 5 — Verify policy configuration query

For IP-specific Mitigation Policy / Port-specific Mitigation Policy:
```bash
aliyun ddosbgp list-policy --name <PolicyName> \
  --page-no 1 --page-size 50 \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
```

For default:
```bash
aliyun ddosbgp list-policy --name <PolicyName> \
  --type default --product-type <eip|ecs|slb|gf-eip> \
  --page-no 1 --page-size 50 \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query
```

**Expected:** Response contains a `PolicyList` whose `Content` field carries the rule configuration (`BlackIpList` / `PortRuleList` / etc.) corresponding to the intercept modules found in Step 3.

## Final Report Verification Checklist

After every workflow run, verify the final report against this checklist:

- [ ] Reports the instance IP, InstanceId, query time window, `TotalCnt`, and current sample count
- [ ] Does **not** include `BaseThreshold` / `ElasticThreshold` / `ExpireTime` / billing specs (those are protection pack attributes, not intercept data)
- [ ] Groups intercept records by `InterceptModule` and shows counts
- [ ] Attributes every intercept record to a specific policy (custom policy name, default policy template name, or `global_blacklist` → system-level)
- [ ] For IP-specific Mitigation Policy / Port-specific Mitigation Policy display, lists **all modules** with "Not configured" for empty ones
- [ ] For `packet_filter` records that don't match any `PortRuleList` rule, the report explicitly attributes them to the default policy (template-built-in or AI-deployed) — does **not** claim "system anomaly" or "data mismatch"
- [ ] For false-positive scenarios, provides remediation recommendations with whitelist-first priority
- [ ] No raw AK/SK or credential values appear anywhere in output
