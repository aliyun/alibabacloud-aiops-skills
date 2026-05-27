# Related CLI Commands

Complete list of `aliyun` CLI commands used by this skill. Both `ddosbgp` and `antiddos-public` are installed as standalone plugins (`aliyun-cli-ddosbgp`, `aliyun-cli-antiddos-public`).

## Command Template

Default to **plugin-mode kebab-case** for every call. Always include the `User-Agent` header for audit/traceability.

```bash
aliyun <product> <kebab-action> \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query \
  [--kebab-param value ...]
```

### Edge case — OpenAPI fallback when the plugin doesn't declare an action

If the plugin returns `unknown command` or `'<Action>' is not a valid api`, the action is not declared in the installed plugin metadata. Bypass the plugin and go through the core CLI's built-in OpenAPI metadata:

```bash
aliyun --auto-plugin-install false <product> <PascalCaseAction> --force \
  --region <region> --profile <profile> \
  --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddos-native-intercept-query \
  [--PascalCaseParam value ...]
```

Fallback rules:
- `--auto-plugin-install false` → bypasses plugin routing; falls through to the core CLI's built-in OpenAPI metadata.
- `--force` → skips parameter-validation noise from the legacy metadata path.
- Do NOT pass `--version` (any explicit version is rejected as `unchecked version` on this route; the core CLI uses its built-in default).
- Use **PascalCase** action and parameters (parsed by the legacy OpenAPI parser, not the plugin's kebab parser).

**Known case as of `aliyun-cli-ddosbgp` 0.3.0**: `DescribeNetworkLayerIntercepts` is not declared in plugin metadata, so this fallback applies. Switch back to plugin-mode kebab-case once a newer plugin release declares `describe-network-layer-intercepts`.

## Commands Used by This Skill

| Product | CLI Invocation | Purpose | Required Permission |
|---------|----------------|---------|---------------------|
| `ddosbgp` | `aliyun ddosbgp describe-network-layer-intercepts` ⚠ falls back to OpenAPI on plugin 0.3.0 | Retrieve network-layer intercept records (core API) | `ddosbgp:DescribeNetworkLayerIntercepts` |
| `ddosbgp` | `aliyun ddosbgp list-policy-attachment` | List protection policies bound to an instance / IP | `ddosbgp:ListPolicyAttachment` |
| `ddosbgp` | `aliyun ddosbgp list-policy` | List or query detailed policy configuration (default / IP-specific Mitigation Policy / Port-specific Mitigation Policy) | `ddosbgp:ListPolicy` |
| `ddosbgp` | `aliyun ddosbgp describe-instance-list` | Enumerate DDoS native protection instances under the active profile | `ddosbgp:DescribeInstanceList` |
| `antiddos-public` | `aliyun antiddos-public describe-bgp-pack-by-ip` | Derive the protection pack `InstanceId` from an instance IP | `antiddos-public:DescribeBgpPackByIp` |
| `antiddos-public` | `aliyun antiddos-public describe-ip-location-service` | Query IP geographic region and asset type | `antiddos-public:DescribeIpLocationService` (optional) |
| `antiddos-public` | `aliyun antiddos-public describe-instance-ip-address` | Query the ECS / EIP / SLB instance associated with an IP and its protection status | `antiddos-public:DescribeInstanceIpAddress` (optional) |

## Key Parameters

### `ddosbgp DescribeNetworkLayerIntercepts`

Parameter names depend on which route the call uses. Default to plugin-mode (kebab-case); when the plugin rejects the action (current state on `aliyun-cli-ddosbgp` 0.3.0), use the OpenAPI fallback column.

| Required | Plugin-mode param | OpenAPI fallback param | Description |
|----------|-------------------|------------------------|-------------|
| Yes | `--instance-id` | `--InstanceId` | Protection pack instance ID (e.g. `ddosbgp-cn-xxx` or `ddosorigin_cn-xxx`) |
| Yes | `--start-time` | `--StartTime` | Unix timestamp (seconds); must be within 30 days of end |
| Yes | `--end-time` | `--EndTime` | Unix timestamp (seconds) |
| Yes | `--page-no` | `--PageNo` | Page number, starts at 1 |
| Yes | `--page-size` | `--PageSize` | Page size, max 50 |
| Optional | `--src-ip` | `--SrcIp` | Filter by source IP |
| Optional | `--destination-ip` | `--DestinationIp` | Filter by destination IP |
| Optional | `--network-protocol` | `--NetworkProtocol` | Filter by protocol: `tcp` / `udp` / `icmp` |
| Optional | `--source-port` | `--SourcePort` | Filter by source port |
| Optional | `--destination-port` | `--DestinationPort` | Filter by destination port |
| Optional | `--protocol-number` | `--ProtocolNumber` | Filter by IP protocol number |

### `ddosbgp ListPolicyAttachment`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--ip-port-protocol-list` | Yes | JSON array, e.g. `'[{"Ip":"47.118.170.18"}]'` |
| `--page-no` | Yes | Page number, starts at 1 |
| `--page-size` | Yes | Page size |
| `--policy-type` | Optional | If omitted, returns all bound policies in one call (default policy + IP-specific Mitigation Policy + Port-specific Mitigation Policy). Note: the raw API response field `PolicyType` still carries the literal `default` / `l3` / `l4` — used only for branching the follow-up `ListPolicy` call |

### `ddosbgp ListPolicy`

Different invocation modes by policy type:

| Mode | Required parameters |
|------|---------------------|
| Query a known custom policy (IP-specific or Port-specific Mitigation Policy) by name | `--name <PolicyName>` — do NOT pass `--type` or `--product-type` |
| Query a known default policy by name | `--name <PolicyName>` + `--type default` + `--product-type <eip\|ecs\|slb\|gf-eip>` |
| List all default policy templates | `--type default` + `--product-type <eip\|ecs\|slb\|gf-eip>` |

> `--product-type` is **mandatory** whenever `--type default` is used. Omitting it returns server error `Invalid params. Invalid product type.`

### `antiddos-public DescribeBgpPackByIp`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--ddos-region-id` | Yes | DDoS region (e.g. `cn-hangzhou`) |
| `--ip` | Yes | Instance IP (destination IP) to query |

### `antiddos-public DescribeInstanceIpAddress`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--ddos-region-id` | Yes | DDoS region |
| `--instance-ip` | Yes | The IP to look up |
| `--instance-type` | Yes | Asset type: `eip` / `ecs` / `slb` / `gf-eip` (also accepted: `ipv6` / `swas` / `waf` / `ga_basic`) |

### `antiddos-public DescribeIpLocationService`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--internet-ip` | Yes | Public IP address |

## Timestamp Generation Helper

```bash
# Last 1 hour
echo "StartTime: $(($(date +%s) - 3600)), EndTime: $(date +%s)"

# Last 24 hours
echo "StartTime: $(($(date +%s) - 86400)), EndTime: $(date +%s)"

# Last 7 days
echo "StartTime: $(($(date +%s) - 604800)), EndTime: $(date +%s)"
```
