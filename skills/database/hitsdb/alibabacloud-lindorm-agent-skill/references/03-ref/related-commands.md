# Aliyun CLI Command List

This document lists all Aliyun CLI commands used by this Skill. `aliyun lindorm ...` manages instances, connection endpoints, whitelists, and other cloud resources. Monitoring uses `aliyun cms`; see "CloudMonitor CLI". To execute SQL, use `lindorm-cli`; see `lindorm-cli-guide.md`.

## Lindorm Instance Management CLI

`aliyun lindorm` is the official Lindorm plugin distributed with Aliyun CLI. This document was verified with plugin `v0.2.20` and Aliyun CLI `3.4.1`. `--lindorm-region` and `--lindorm-profile` were added in plugin `v0.2.20`; upgrade older versions first. The plugin still calls Lindorm OpenAPI, product name `hitsdb`, API version `2020-06-15`, so RAM authorization continues to use `hitsdb:*` actions. See `ram-policies.md`.

### Plugin Installation and Verification

```bash
# Enable automatic plugin installation, recommended.
aliyun configure set --auto-plugin-install true
aliyun plugin update

# Verify the plugin. Aliyun CLI must be >= 3.4.1.
aliyun lindorm --version
```

> The plugin is also available as a **standalone binary**, `lindorm-open-api-cli`. It is precompiled, requires neither Go nor git, automatically downloads by OS and architecture, verifies SHA256, and installs under `~/.lindorm-open-api-cli/bin`:
>
> ```bash
> # Linux / macOS
> curl -fsSL https://lindorm-open-api-cli.oss-cn-hangzhou.aliyuncs.com/scripts/install.sh | sh
> export PATH="$HOME/.lindorm-open-api-cli/bin:$PATH"
> # Windows (PowerShell)
> #   irm https://lindorm-open-api-cli.oss-cn-hangzhou.aliyuncs.com/scripts/install.ps1 | iex
> ```
>
> Override defaults with `LINDORM_CLI_BASE_URL`, `LINDORM_CLI_VERSION`, or `LINDORM_CLI_HOME`. Subcommands and parameters are identical to plugin mode. The only difference is that standalone mode also accepts `--region` and `--profile`; in plugin mode, the parent `aliyun` CLI consumes them.

### Credentials

Credential priority, highest first:

1. Environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID` and `ALIBABA_CLOUD_ACCESS_KEY_SECRET`; with `ALIBABA_CLOUD_SECURITY_TOKEN`, STS mode is used.
2. `--aliyun-profile <name>`: reuse Aliyun CLI credentials from `~/.aliyun/config.json`. AK, OAuth, and StsToken modes are supported; OAuth automatically includes the SecurityToken.
3. Locally encrypted credentials created by `auth login`.
4. Fallback: automatically read the current Aliyun CLI profile.

> **[MUST]** Never run `auth login --ak ... --sk ...` inside an Agent session. It accepts AK/SK in plaintext on the command line and violates the security rules in SKILL.md. Use `--aliyun-profile <name>`. If no credentials exist, stop and ask the user to configure them outside the session.

Recommended OAuth usage, which avoids manual AK/SK management:

```bash
aliyun configure --mode OAuth --profile my-oauth     # One-time browser authorization.
aliyun lindorm instance list --aliyun-profile my-oauth --lindorm-region cn-hangzhou
```

For interactive VPC/VSwitch selection, when `--vpc-id` or `--vswitch-id` is omitted, the credential must also allow `DescribeVpcs` and `DescribeVSwitches` from vpc-20160428.

### Invocation Conventions

- The **instance ID is positional**, not `--instance-id`: `aliyun lindorm v1 instance describe ld-xxx`.
- `aliyun lindorm instance ...` aliases `aliyun lindorm v2 instance ...`; explicitly use `v1 instance ...` for V1.
- Global parameters: `--lindorm-region`, `--lindorm-profile`, `--aliyun-profile`, `--output table|json|yaml`, `--yes`, `--non-interactive`, and `-v`.
- Pass the region with `--lindorm-region`, never `--region`; similarly, use `--lindorm-profile`. The parent `aliyun` CLI consumes `--region` and `--profile`, so the plugin never receives them. The command may still succeed against the wrong region, while the plugin writes a `note:` to stderr. See "Region Parameter".
- Fields from `--output json` use snake_case rather than the OpenAPI response's PascalCase. "Return Value Structure" documents the actual plugin output.

### Architecture Selection: Detect First, Then Choose the Command

| User description | Route |
|---|---|
| Mentions "new architecture", "engine", or LindormTabular/Search/Stream/TSDB | V2 |
| Provides an `ld-xxx` ID without architecture | Detect first: inspect `arch` from `instance list`. For one instance, `v1 instance describe` also works because the underlying shared `GetLindormInstance` returns the correct `service_type` for V2 rather than 404. |
| Explicitly describes the old architecture with core, lindorm, and solr nodes | V1 |
| Uncertain | Do not guess. Detect first, consistent with SKILL.md → "Version Detection". |

> Outside the shared detection path, a V1 instance sent to a V2 endpoint always returns 404. If `v2 ... describe` reports NotFound, retry with `v1 ... describe`.

### Query Commands

| CLI command | Description | Required parameters | Key returned fields, `--output json` |
|----------|------|---------|-------------|
| `aliyun lindorm regions list` | List supported regions | None | Array: `region_id`, `local_name`, `region_endpoint` |
| `aliyun lindorm summary` | Query the region-agnostic all-region overview | None | `total`, `running_count`, `locking_count`, `regions[]` |
| `aliyun lindorm instance list` | List mixed V1/V2 instances | `--lindorm-region`; optional `--query`, `--page`, and `--page-size` | Array: `instance_id`, `instance_name`, `status`, `region_id`, `zone_id`, `arch`, `service_type`, `network_type`, `create_time` |
| `aliyun lindorm v1 instance describe` | Query configuration, version, and status; connection endpoints are absent | `<instance-id>`, `--lindorm-region` | `service_type`, `arch_version`, `disk_category`, `instance_storage`, `disk_threshold`, `engines[]` |
| `aliyun lindorm v2 instance describe` | Query V2 details, including engine topology and connection endpoints | `<instance-id>`, `--lindorm-region` | `service_type`, `cloud_storage_type`, `cloud_storage_size`, `engines[]` with `node_groups[]`, `connect_address_list[]` |
| `aliyun lindorm v1 instance engine-list` | Query each engine's host:port and public/private network | `<instance-id>`, `--lindorm-region` | Array: `engine_type`, `net_type`, `net_type_code`, `access_type`, `connection_string`, `port` |
| `aliyun lindorm v1 instance storage` | Query V1 storage details | `<instance-id>`, `--lindorm-region` | `fs_capacity`, `fs_used_hot/cold`, `used_on_lindorm_table*`, `disks[]` |
| `aliyun lindorm v2 instance storage` | Query V2 storage details | `<instance-id>`, `--lindorm-region` | `capacity_by_disk_category[]`, `usage_by_disk_category[]` |
| `aliyun lindorm v1 instance whitelist get` | Query the IP whitelist | `<instance-id>`, `--lindorm-region` | `groups[]`: `group_name`, `security_ip_list` |
| `aliyun lindorm v1 instance security-group get` | Query bound ECS security groups | `<instance-id>`, `--lindorm-region` | Security group list |
| `aliyun lindorm vpc list` | List VPCs in a region | `--lindorm-region` | VPC list |
| `aliyun lindorm vpc vswitch` | List VSwitches | `--lindorm-region`; optional `--vpc-id` and `--zone-id` | VSwitch list |

> `whitelist`, `security-group`, `engine-list`, and `switch-pay-type` are identical under `v1 instance` and `v2 instance` because the underlying APIs are shared. `storage` is architecture-specific: `v1 instance storage` against V2 returns HTTP 200 with an empty body, while the reverse returns 451. Confirm the architecture first; see SKILL.md → "Version Detection".

### Management Commands

> These commands are billable or destructive. Confirm parameters with the user before execution. `create` and `modify` support `--dry-run`.

| CLI command | Description | Required parameters |
|----------|------|---------|
| `aliyun lindorm v1 instance create` | Create a V1 instance | `--name`, `--zone-id`, `--vpc-id`, `--vswitch-id`, `--instance-storage`, `--lindorm-spec`, `--lindorm-num` |
| `aliyun lindorm v2 instance create` | Create a V2 instance | `--name`, `--vpc-id`, `--arch-version`, `--engine`, `--cloud-storage-type`, `--cloud-storage-size` |
| `aliyun lindorm v1 instance modify` | Modify V1; one UpgradeType per call | `<instance-id>` plus one change item |
| `aliyun lindorm v2 instance modify` | Modify V2 using read-modify-write | `<instance-id>` plus one change item |
| `aliyun lindorm v1 instance release` | Irreversibly release a POSTPAY V1 instance | `<instance-id>`; optional `--immediate` |
| `aliyun lindorm v2 instance release` | Irreversibly release a POSTPAY V2 instance | `<instance-id>` |
| `aliyun lindorm v1 instance whitelist update` | Update an IP whitelist; `--ips` replaces the entire group | `<instance-id>`, `--ips`; optional `--group` / `--delete` |
| `aliyun lindorm v1 instance security-group update` | Replace bound ECS security groups | `<instance-id>`, `--groups` |
| `aliyun lindorm v1 instance switch-pay-type` | Convert the billing method | `<instance-id>`, `--pay-type`; conversion to PREPAY also requires `--pricing-cycle` and `--duration` |
| `aliyun hitsdb update-lindorm-instance-attribute` | Update instance attributes, such as the instance name | `--instance-id`, `--region` |

> ⚠️ The final row still uses the raw OpenAPI form. As of plugin v0.2.20, `aliyun lindorm` has no command for `update-lindorm-instance-attribute`, so call it with `aliyun hitsdb`.
>
> Equivalent `whitelist update`, `security-group update`, and `switch-pay-type` commands exist under `v2 instance` with the same parameters.

### Execution Examples

```bash
# List regions.
aliyun lindorm regions list

# Query the region-agnostic instance overview.
aliyun lindorm summary

# List instances in a region.
aliyun lindorm instance list --lindorm-region cn-shanghai

# Search instances by a partial name or ID.
aliyun lindorm instance list --lindorm-region cn-shanghai --query prod

# Query V1 details; this can also obtain service_type for any architecture.
aliyun lindorm v1 instance describe ld-uf6nbdlx5n34q6l6t --lindorm-region cn-shanghai

# Query V2 details, including connect_address_list.
aliyun lindorm v2 instance describe ld-uf6nbdlx5n34q6l6t --lindorm-region cn-shanghai

# Query connection endpoints for each engine.
aliyun lindorm v1 instance engine-list ld-uf6nbdlx5n34q6l6t --lindorm-region cn-shanghai

# Query storage details using the architecture-specific command.
aliyun lindorm v1 instance storage ld-uf6cx7381qw2u5u8w --lindorm-region cn-shanghai
aliyun lindorm v2 instance storage ld-uf6nbdlx5n34q6l6t --lindorm-region cn-shanghai --output json

# Query the IP whitelist.
aliyun lindorm v1 instance whitelist get ld-uf6nbdlx5n34q6l6t --lindorm-region cn-shanghai
```

### Return Value Structure

#### `instance list` → List Instances

The top level is an array without an `InstanceList` or `Total` wrapper. Use `arch` directly for V1/V2 routing.

```json
[
  {
    "instance_id": "ld-xxx",
    "instance_name": "",
    "status": "ACTIVATION",
    "region_id": "cn-shenzhen",
    "zone_id": "cn-shenzhen-f",
    "arch": "v2",
    "service_type": "lindorm_v2",
    "network_type": "vpc",
    "create_time": "2026-07-22 10:29:57"
  }
]
```

> Note: This command does not return engine enablement flags, `Enable*`. Use `engines[]` from `v1/v2 instance describe` when engine information is required.

#### `v1 instance describe` → Query Configuration, Version, and Status

Includes engine node counts, specifications, and versions, but not connection endpoints. The underlying `GetLindormInstance` is shared by V1 and V2 and returns the correct `service_type` for V2.

```json
{
  "instance_id": "ld-xxx",
  "status": "ACTIVATION",
  "service_type": "lindorm_v2",
  "arch_version": "1.0",
  "region_id": "cn-shenzhen",
  "zone_id": "cn-shenzhen-f",
  "network_type": "vpc",
  "vpc_id": "vpc-xxx",
  "vswitch_id": "vsw-xxx",
  "pay_type": "POSTPAY",
  "disk_category": "cloud_essd",
  "instance_storage": "160",
  "disk_threshold": "80",
  "deletion_protection": false,
  "engines": [
    {
      "engine": "lindorm",
      "core_count": "2",
      "cpu_count": "4",
      "memory_size": "16GB",
      "specification": "lindorm.g.xlarge",
      "latest_version": "2.8.6.4"
    }
  ],
  "request_id": "..."
}
```

#### `v2 instance describe` → Query V2 Details

V2-only command that additionally returns node-group topology and `connect_address_list`.

```json
{
  "instance_id": "ld-xxx",
  "status": "ACTIVATION",
  "service_type": "lindorm_v2",
  "cloud_storage_type": "StandardStorage",
  "cloud_storage_size": 160,
  "disk_threshold": 80,
  "engines": [
    {
      "engine": "lindorm",
      "version": "2.8.6.4",
      "node_groups": [
        {
          "group_id": "...",
          "node_spec": "lindorm.g.xlarge",
          "quantity": 2,
          "cpu_core_count": 4,
          "memory_size_gib": 16,
          "status": "ACTIVATION"
        }
      ]
    }
  ],
  "connect_address_list": [
    { "type": "INTRANET", "address": "ld-xxx-proxy-lindorm-vpc.lindorm.aliyuncs.com", "port": 33060 }
  ],
  "request_id": "..."
}
```

> `connect_address_list[].type` is `INTRANET` or `INTERNET`. It corresponds semantically to `net_type` from `engine-list`, but uses different values.

#### `instance engine-list` → Query Connection Endpoints

The top level is an array flattened by engine and endpoint, without `EngineList[].NetInfoList[]` nesting. Engines without reachable endpoints, such as bds or compute, are still listed with empty endpoint fields.

```json
[
  {
    "engine_type": "lindorm",
    "net_type": "VPC",
    "net_type_code": "2",
    "access_type": 6,
    "connection_string": "ld-xxx-proxy-lindorm-vpc.lindorm.aliyuncs.com",
    "port": 33060
  },
  {
    "engine_type": "lindorm",
    "net_type": "VPC",
    "net_type_code": "2",
    "access_type": 1,
    "connection_string": "ld-xxx-proxy-lindorm-vpc.lindorm.aliyuncs.com",
    "port": 30020
  },
  {
    "engine_type": "file",
    "net_type": "VPC",
    "net_type_code": "2",
    "connection_string": "ld-xxx-proxy-file-vpc.lindorm.aliyuncs.com",
    "port": 9000
  }
]
```

**net_type**: `net_type` is `VPC` or `PUBLIC`; `net_type_code` is `"2"` for VPC and `"0"` for public.

#### `instance whitelist get` → Query the IP Whitelist

```json
{
  "instance_id": "ld-xxx",
  "groups": [
    { "group_name": "default", "security_ip_list": "127.0.0.1" },
    { "group_name": "office", "security_ip_list": "140.205.0.0/24" }
  ],
  "request_id": "..."
}
```

#### `v1 instance storage` → V1 Storage Details

```json
{
  "instance_id": "ld-xxx",
  "valid": "true",
  "fs_capacity": "85899345920",
  "fs_capacity_hot": "85899345920",
  "fs_capacity_cold": "0",
  "fs_used_hot": "35338",
  "fs_used_cold": "0",
  "used_on_lindorm_table": "35338",
  "used_on_lindorm_table_data": "12814",
  "used_on_lindorm_table_wal": "4874",
  "used_hot_on_lindorm_table": "35338",
  "used_cold_on_lindorm_table": "0",
  "disks": [
    {
      "disk_type": "StandardCloudStorage",
      "capacity": "85899345920",
      "used": "153277552",
      "used_lindorm_table": "34673",
      "used_lindorm_tsdb": "0",
      "used_lindorm_search": "0",
      "used_other": "..."
    }
  ]
}
```

> All units are bytes encoded as strings. Convert them to numbers before calculation.

#### `v2 instance storage` → V2 Storage Details

```json
{
  "instance_id": "ld-xxx",
  "capacity_by_disk_category": [
    { "category": "STD_CLOUD_ESSD_PL0", "capacity": 160, "usedCapacity": 0, "mode": "CLOUD_STORAGE", "perfLevel": "PL0" }
  ],
  "usage_by_disk_category": [
    {
      "diskType": "StandardCloudStorage",
      "capacity": 171798691840,
      "used": 2159229,
      "usedLindormTable": 29152,
      "usedLindormTsdb": 0,
      "usedLindormSearch3": 0,
      "usedLindormColumn3": 0,
      "usedLindormVector3": 0,
      "usedLindormMessage3": 0,
      "usedLindormSpark": 0,
      "usedOther": 2130077
    }
  ],
  "request_id": "..."
}
```

> ⚠️ Top-level keys use snake_case, but keys inside the arrays remain camelCase, including `usedCapacity`, `diskType`, `usedLindormTable`, and `perfLevel`. The API returns free-form maps that the plugin passes through. Table output cannot flatten these fields; use `--output json`.
>
> `capacity_by_disk_category` is in GB, while `usage_by_disk_category` is in bytes.

#### Capacity Units, Important

The API response does not declare units and the CLI does not convert them. Verified comparisons:

| Field | Unit | Evidence |
|---|---|---|
| V1 `fs_capacity` | **bytes** | A 2160 GB capacity returns `2319282339840`, exactly 2160×1024³ |
| V2 `usage_by_disk_category[].capacity` | **bytes** | A 320 GB capacity returns `343597383680`, exactly 320×1024³ |
| V2 `capacity_by_disk_category[].capacity` | **GB** | Returns `320`, matching `cloud_storage_size: 320` from describe |

> ⚠️ Units for the various `used*` fields are not yet confirmed. Their magnitudes are much smaller than `capacity` in the same response. For example, `capacity=343597383680` and `used=8419884`; interpreting `used` as bytes gives only 8 MB for a four-engine instance, while KB would imply about 8 GB. The latter is only an inference and is not verified.
>
> The `used*` components sum to `used`, verified as 114865+153597+8151422 = 8419884. Percentage and composition analysis is safe, but confirm the unit before reporting absolute values.

---

### Parameter Descriptions

#### `--lindorm-region` Region Parameter

> ⚠️ Use `--lindorm-region`, never `--region`. `--region` is a global option of the parent `aliyun` CLI, which consumes it instead of forwarding it to the plugin. The command may still succeed against the profile's region rather than the requested region, which is more dangerous than a visible error. The plugin writes a warning to stderr; do not ignore it:
>
> ```
> note: using region cn-shenzhen (from profile/environment). '--region' is consumed by the aliyun CLI
> and never reaches this plugin — use '--lindorm-region <region>' to override.
> ```
>
> The same applies to `--profile`; the plugin-side option is `--lindorm-profile`. From plugin `--help`:
>
> ```
> --lindorm-region string    Same as --region; use this under 'aliyun lindorm', where --region is consumed by the aliyun CLI
> --lindorm-profile string   Same as --profile; use this under 'aliyun lindorm', where --profile is consumed by the aliyun CLI
> ```
>
> Without `--lindorm-region`, the region comes from `active_profile` in `~/.lindorm-open-api-cli/config.json`. Always pass `--lindorm-region` explicitly and verify `region_id` in the output before responding.
>
> Exception: `profile create --region <region>` defines its own command-local option, so use it as written.

| Region ID | Region Name |
|---------|---------|
| `cn-shanghai` | East China 2, Shanghai, default |
| `cn-beijing` | North China 2, Beijing |
| `cn-hangzhou` | East China 1, Hangzhou |
| `cn-shenzhen` | South China 1, Shenzhen |
| `cn-zhangjiakou` | North China 3, Zhangjiakou |
| `cn-qingdao` | North China 1, Qingdao |
| `cn-wulanchabu` | North China 6, Ulanqab |
| `cn-guangzhou` | South China 3, Guangzhou |
| `cn-chengdu` | Southwest China 1, Chengdu |

Run `aliyun lindorm regions list` for the complete list.

#### Instance ID, Positional Argument

Format: `ld-xxx`, starting with `ld-` followed by letters and digits. Pass it as a positional argument immediately after the subcommand; do not use `--instance-id`:

```bash
aliyun lindorm v1 instance describe ld-xxx      # ✅
aliyun lindorm v1 instance describe --instance-id ld-xxx   # ❌ unknown flag
aliyun lindorm v1 instance describe            # ❌ accepts 1 arg(s), received 0
```

#### `service_type` Instance Type, Returned Field

The plugin does not provide an input filter by type. `service_type` is returned by `instance list` and `instance describe`; filter the `--output json` result locally. See SKILL.md → "Version Detection" for the complete list.

| Value | Description |
|----|------|
| `lindorm` | Lindorm V1 single-zone instance |
| `lindorm_multizone` | Lindorm V1 multi-zone instance |
| `lindorm_multizone_basic` | Lindorm V1 multi-zone basic instance |
| `lindorm_v2` | Lindorm V2 single-zone instance |
| `lindorm_v2_multizone` | Lindorm V2 multi-zone basic instance |
| `lindorm_v2_multizone_ha` | Lindorm V2 multi-zone high-availability instance |
| `serverless_lindorm` | Lindorm Serverless instance |
| `lindorm_standalone` | Lindorm single-node development/test instance |

#### Pagination and Fuzzy Search

`instance list` supports three filter parameters and does not support `--service-type`, `--support-engine`, or `--pager`:

| Parameter | Description |
|------|------|
| `--query <keyword>` | Fuzzy-match the instance name or ID |
| `--page <n>` | Page number, default 1 |
| `--page-size <n>` | Items per page, default 20, maximum 100 |

#### Engine Type Details

For engine type details, see SKILL.md -> "Engine type details".

---

## CloudMonitor CLI

**Product name**: `cms`
**Namespace**: `acs_lindorm`

### Plugin Installation

```bash
# Install the CloudMonitor plugin.
aliyun plugin install --names cms
```

### Query Commands

| CLI Command | Description | Required Parameters |
|----------|------|---------|
| `aliyun cms describe-metric-meta-list` | Query metric list | `--namespace`, `--region`; `--region` is optional |
| `aliyun cms describe-metric-last` | Query latest data | `--namespace`, `--metric-name`, `--dimensions`; `--region` is optional and automatically located by instanceId |
| `aliyun cms describe-metric-data` | Query historical data | `--namespace`, `--metric-name`, `--dimensions`, `--start-time`, `--end-time`; `--region` is optional and automatically located by instanceId |

### Execution Examples

```bash
# Query Lindorm monitoring metric list.
aliyun cms describe-metric-meta-list --namespace acs_lindorm

# Query latest CPU idle rate data.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6nbdlx5n34q6l6t"}]'

# Query latest memory usage rate data.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name mem_used_percent \
    --dimensions '[{"instanceId":"ld-uf6nbdlx5n34q6l6t"}]'

# Query historical monitoring data, specified time range.
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6nbdlx5n34q6l6t"}]' \
    --start-time "2026-04-14 08:00:00" \
    --end-time "2026-04-14 09:00:00" \
    --period 60
```

### Return Value Structure

#### describe-metric-meta-list -> Query Metric List

```json
{
  "Code": 200,
  "Resources": {
    "Resource": [
      {
        "MetricName": "cpu_idle",
        "Namespace": "acs_lindorm",
        "Description": "CPU idle rate",
        "Unit": "%",
        "Periods": "60,300",
        "Dimensions": "userId,instanceId,host",
        "Statistics": "Average,Maximum,Minimum"
      }
    ]
  }
}
```

#### describe-metric-last -> Query Latest Data

```json
{
  "Code": "200",
  "Period": "60",
  "Datapoints": "[{\"timestamp\":1776414660000,\"instanceId\":\"ld-xxx\",\"host\":\"table-1\",\"userId\":\"149xxx\",\"Average\":93.241,\"Maximum\":94.217,\"Minimum\":91.082}]"
}
```

> Note: `Datapoints` is a JSON **string** and requires secondary parsing. Each data point contains `host`, the node name, and `userId`.

#### describe-metric-data -> Query Historical Data

The returned structure is the same as `describe-metric-last`, and `Datapoints` contains data at multiple time points.

---

### Parameter Descriptions

#### `--dimensions` Dimension Parameter, JSON Array

**Format description**: On Linux/macOS, wrap it with single quotes and no escaping is required. On Windows CMD, use double quotes plus escaping.

```bash
# ✅ Recommended Linux/macOS format, single quotes, no escaping required.
--dimensions '[{"instanceId":"ld-xxx"}]'

# ✅ Windows CMD format, double quotes plus escaping.
--dimensions "[{\"instanceId\":\"ld-xxx\"}]"
```

Multi-dimension example:
```bash
--dimensions "[{\"instanceId\":\"ld-xxx\"},{\"instanceId\":\"ld-yyy\"}]"
```

#### `--start-time` / `--end-time` Time Parameters

For time format descriptions, see SKILL.md -> "Time format".

#### `--period` Collection Period, Seconds

| Value | Description |
|----|------|
| `60` | 1 minute, default |
| `300` | 5 minutes |
| `900` | 15 minutes |
| `3600` | 1 hour |

---

Common monitoring metrics are described in `references/02-ops/monitoring-guide.md`.

---

## Output Format and Local Filtering

`aliyun lindorm` does not support the native Aliyun CLI options `--cli-query` or `--pager`. Use `--output json` with `jq` for local filtering:

```bash
# Return only instance ID, name, and status.
aliyun lindorm instance list --lindorm-region cn-shanghai --output json \
    | jq -r '.[] | [.instance_id, .instance_name, .status] | @tsv'

# Show only V2 instances.
aliyun lindorm instance list --lindorm-region cn-shanghai --output json \
    | jq '[.[] | select(.arch == "v2")]'

# Return only engine type and connection endpoint.
aliyun lindorm v1 instance engine-list ld-xxx --lindorm-region cn-shanghai --output json \
    | jq -r '.[] | [.engine_type, .connection_string, .port] | @tsv'

# cms remains a native Aliyun CLI command and supports --cli-query.
aliyun cms describe-metric-last \
    --namespace acs_lindorm --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-xxx"}]' \
    --cli-query 'Datapoints'
```

---

## Paginated Query

The plugin has no `--pager`; increment `--page` explicitly:

```bash
aliyun lindorm instance list --lindorm-region cn-shanghai --page 1 --page-size 100
aliyun lindorm instance list --lindorm-region cn-shanghai --page 2 --page-size 100
```

---

## Automation, CI/CD

In CI, explicitly pass the region, VPC, and VSwitch. Under `--non-interactive`, no interactive selection occurs, and missing IDs fail immediately without making a network request.

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=$AK
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=$SK

lindorm-open-api-cli instance create --name "ci-${BUILD_ID}" --non-interactive \
  --lindorm-region cn-hangzhou \
  --zone-id cn-hangzhou-h --vpc-id "$VPC" --vswitch-id "$VSW" \
  --arch-version 1.0 --pay-type POSTPAY \
  --engine TABLE:lindorm.g.2xlarge:2 \
  --cloud-storage-type PerformanceStorage --cloud-storage-size 400 \
  --wait --output json > out.json

INSTANCE_ID=$(jq -r .instance_id out.json)
trap 'lindorm-open-api-cli instance release "$INSTANCE_ID" --yes --immediate' EXIT
```

---

## Common Pitfalls

- **Using `--region` in plugin mode**: it is silently ignored, the command runs against the wrong region, and rc remains 0. Use `--lindorm-region`.
- **Wrong architecture**: a V1 instance sent to a V2 endpoint always returns 404.
- **Asymmetric `storage` mismatch**: `v1 instance storage` against V2 returns an empty result with rc=0 and can be misread as zero storage usage.
- **`summary` may omit an entire region**: one observed result returned eight regions with a self-consistent `total=24` but omitted cn-beijing, which actually had four instances. Do not rely on it alone for capacity inventory or asset cleanup that requires exact counts.
- **Do not rerun `summary` or `regions list` per region**: these APIs do not accept RegionId. A different region only changes the endpoint, not the result.
- **VPC/VSwitch mismatch**: `vswitch-id` must belong to `vpc-id` and the same zone as `zone-id`, otherwise creation may remain in `Failed`.
- **Each multi-zone VSwitch belongs to its zone**: for architecture 2.0/3.0, primary, standby, and coordinator VSwitch IDs must match their respective zone IDs.
- **Cross-account profile mismatch**: for long-term switching, run both `auth use <name>` and `profile use <name>`. Switching only one can pair the wrong region with the wrong AccessKey.
- **Concurrent modification**: `modify` is rejected unless the instance is `ACTIVATION`. Describe it and wait for that status.
- **Different network field vocabularies**: `engine-list` uses `PUBLIC`/`VPC`, raw codes `0`/`2`, while V2 `describe` uses `INTRANET`/`INTERNET` in `connect_address_list.type`.
- **Legacy lowercase engine identifiers in `engine-list`**: V2 `describe` returns `TABLE`, `LSEARCH`, `LAI`, or `COMPUTE`, while `engine-list` returns identifiers such as `lindorm`, `lai`, and `file`. Map them explicitly when correlating results.
- **Structured output**: always use `--output json` in scripts; do not parse human-readable tables.

---

## OpenAPI Name Mapping

| Command | V1 architecture | V2 architecture |
|---|---|---|
| `instance create` | CreateLindormInstance | CreateLindormV2Instance |
| `instance describe` | GetLindormInstance | GetLindormV2InstanceDetails |
| `instance list` | GetLindormInstanceList | GetLindormInstanceList, ServiceType=lindorm_v2 |
| `instance modify` | UpgradeLindormInstance | UpdateLindormV2Instance |
| `instance release` | ReleaseLindormInstance | ReleaseLindormV2Instance |
| `instance switch-pay-type` | ModifyInstancePayType, shared | Same |
| `instance whitelist get` | GetInstanceIpWhiteList, shared | Same |
| `instance whitelist update` | UpdateInstanceIpWhiteList | ModifyLindormV2WhiteIpList |
| `instance security-group get` | GetInstanceSecurityGroups, shared | Same |
| `instance security-group update` | UpdateInstanceSecurityGroups | ModifyLindormV2InstanceSecurityGroups |
| `regions list` | DescribeRegions, shared and region-agnostic | Same |
| `summary` | GetInstanceSummary, shared and region-agnostic | Same |
| `instance engine-list` | GetLindormInstanceEngineList, shared | Same |
| `v1 instance storage` | GetLindormFsUsedDetail | — |
| `v2 instance storage` | — | GetLindormV2StorageUsage |

Interactive VPC/VSwitch selection uses `DescribeVpcs` and `DescribeVSwitches` from vpc-20160428.

> RAM authorization continues to use `hitsdb:*` actions. See `ram-policies.md`.
>
> OpenAPI overview: https://help.aliyun.com/zh/lindorm/developer-reference/api-hitsdb-2020-06-15-overview

---

## Error Handling

| Error Message | Cause | Solution |
|---------|------|---------|
| `Instance.IsNotValid` | Invalid or nonexistent instance ID | Confirm the ID with `aliyun lindorm instance list --lindorm-region <region>` |
| `InvalidParameter.InstanceId` | Incorrect instance ID format | Use the `ld-xxx` format |
| `InstanceNotFound` | Instance does not exist | Check whether `--lindorm-region` is the instance region. Misusing `--region` silently queries the wrong region. |
| `Forbidden.RAM` | Insufficient permissions | Add `AliyunLindormReadOnlyAccess` |
| `Throttling.User` | API throttling | Reduce the request rate or retry later |

---

## Related Documents

- Lindorm API documentation: https://help.aliyun.com/zh/lindorm/developer-reference/api-reference
- CloudMonitor API documentation: https://help.aliyun.com/zh/cms/developer-reference/api-reference
- Aliyun CLI installation guide: `./cli-installation-guide.md`
- **Instance write operations**, including create, modify, release, and billing conversion: `../02-ops/instance-lifecycle.md`
- Whitelist / security group: `../02-ops/network-access-control.md`
- Lindorm CLI, the data-plane SQL client: `./lindorm-cli-guide.md`
- HBase Shell guide: `./hbase-shell-guide.md`
