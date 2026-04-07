# Related APIs - Resource Center

## Single Account Operations

### enable-resource-center

Enable Resource Center service.

**Usage**

```bash
# Enable Resource Center service
aliyun resourcecenter enable-resource-center \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### disable-resource-center

Disable Resource Center service.

**Usage**

```bash
# Disable Resource Center service
aliyun resourcecenter disable-resource-center \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### get-resource-center-service-status

Query Resource Center service status.

**Usage**

```bash
# Check if Resource Center is enabled
aliyun resourcecenter get-resource-center-service-status \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### search-resources

Search resources under the current account.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--filter` | No | None | Filter conditions. Structure: `[{Key: string, MatchType: string, Value: [string, ...]}, ...]`. **See Filter Parameter Definition below for supported Key and MatchType combinations** |
| `--include-deleted-resources` | No | false | Whether to include deleted resources |
| `--max-results` | No | 20 | Maximum number of entries per page. Valid values: 1~500 |
| `--next-token` | No | None | Token for querying the next page of results |
| `--resource-group-id` | No | None | Resource group ID |
| `--sort-criterion` | No | None | Sorting parameters. Structure: `{Key: string, Order: string}` |

**Usage**

```bash
# Search all resources (paginated)
aliyun resourcecenter search-resources \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Search by resource type (ECS instances)
aliyun resourcecenter search-resources \
  --filter '[{"Key":"ResourceType","MatchType":"Equals","Value":["ACS::ECS::Instance"]}]' \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Combined search: ECS + Hangzhou region
aliyun resourcecenter search-resources \
  --filter '[{"Key":"ResourceType","MatchType":"Equals","Value":["ACS::ECS::Instance"]},{"Key":"RegionId","MatchType":"Equals","Value":["cn-hangzhou"]}]' \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Search by tag (Environment=Production)
aliyun resourcecenter search-resources \
  --filter '[{"Key":"Tag","MatchType":"Contains","Value":["{\"key\":\"env\",\"value\":\"prod\"}"]}]' \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Find untagged resources
aliyun resourcecenter search-resources \
  --filter '[{"Key":"Tag","MatchType":"NotExists"}]' \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Search including deleted resources (for auditing or recovery)
aliyun resourcecenter search-resources \
  --include-deleted-resources=true \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### get-resource-counts

Query resource count statistics for the current account.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--filter` | No | None | Filter conditions. Structure: `[{Key: string, MatchType: string, Value: [string, ...]}, ...]`. **See Filter Parameter Definition below for supported Key and MatchType combinations** |
| `--group-by-key` | No | None | Grouping dimension for resource count statistics. Valid values: `ResourceType`, `RegionId`, `ResourceGroupId` |
| `--include-deleted-resources` | No | false | Whether to include deleted resources |

**Usage**

```bash
# Count by resource type
aliyun resourcecenter get-resource-counts \
  --group-by-key ResourceType \
  --user-agent AlibabaCloud-Agent-Skills

# Count by region
aliyun resourcecenter get-resource-counts \
  --group-by-key RegionId \
  --user-agent AlibabaCloud-Agent-Skills

# Count ECS instance distribution by region
aliyun resourcecenter get-resource-counts \
  --group-by-key RegionId \
  --filter '[{"Key":"ResourceType","MatchType":"Equals","Value":["ACS::ECS::Instance"]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### get-resource-configuration

Query single resource configuration details for the current account.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--resource-id` | Yes | None | Resource ID |
| `--resource-region-id` | Yes | None | Region ID. (e.g., `cn-hangzhou`) |
| `--resource-type` | Yes | None | Resource type. You can use the `scripts/query-resource-types.py` script to query accurate resource type codes. (e.g., `ACS::ECS::Instance`) |

**Usage**

```bash
# Get single ECS instance configuration
aliyun resourcecenter get-resource-configuration \
  --resource-type ACS::ECS::Instance \
  --resource-region-id cn-hangzhou \
  --resource-id i-bp1xxx \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### batch-get-resource-configurations

Batch query resource configurations for the current account.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--resources` | No | None | List of resources. Structure: `{RegionId: string, ResourceId: string, ResourceType: string}`. Format: `--resources RegionId=a ResourceId=b ResourceType=c` |

**Usage**

```bash
# Batch get multiple instance configurations
aliyun resourcecenter batch-get-resource-configurations \
  --resources RegionId=cn-hangzhou ResourceId=vtb-xxx ResourceType=ACS::VPC::RouteTable \
  --resources RegionId=cn-shanghai ResourceId=sg-xxx ResourceType=ACS::ECS::SecurityGroup \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### list-tag-keys

Query tag keys under the current account.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--match-type` | No | None | Match type. Valid values: `Equals`, `Prefix` |
| `--max-results` | No | 20 | Maximum number of entries per page. Valid values: 1~100 |
| `--next-token` | No | None | Token for querying the next page of results |
| `--tag-key` | No | None | Tag key |

**Usage**

```bash
# List all tag keys
aliyun resourcecenter list-tag-keys \
  --max-results 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### list-tag-values

Query tag values under the current account.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--tag-key` | Yes | None | Tag key |
| `--match-type` | No | None | Match type. Valid values: `Equals`, `Prefix` |
| `--max-results` | No | 20 | Maximum number of entries per page. Valid values: 1~100 |
| `--next-token` | No | None | Token for querying the next page of results |
| `--tag-value` | No | None | Tag value |

**Usage**

```bash
# List all values for env tag
aliyun resourcecenter list-tag-values \
  --tag-key env \
  --max-results 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Cross-Account Operations (Requires Resource Directory)

### enable-multi-account-resource-center

Enable cross-account resource search.

**Usage**

```bash
# Enable cross-account resource search
aliyun resourcecenter enable-multi-account-resource-center \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### disable-multi-account-resource-center

Disable cross-account resource search.

**Usage**

```bash
# Disable cross-account resource search
aliyun resourcecenter disable-multi-account-resource-center \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### get-multi-account-resource-center-service-status

Query cross-account resource search service status.

**Usage**

```bash
# Check cross-account Resource Center status
aliyun resourcecenter get-multi-account-resource-center-service-status \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### search-multi-account-resources

Search resources across accounts.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--scope` | Yes | None | Search scope. Valid values: Resource Directory ID, Root Folder ID, Folder ID, or Member ID |
| `--filter` | No | None | Filter conditions. Structure: `[{Key: string, MatchType: string, Value: [string, ...]}, ...]`. **See Filter Parameter Definition below for supported Key and MatchType combinations** |
| `--max-results` | No | 20 | Maximum number of entries per page. Valid values: 1~100 |
| `--next-token` | No | None | Token for querying the next page of results |
| `--sort-criterion` | No | None | Sorting parameters. Structure: `{Key: string, Order: string}` |

**Usage**

```bash
# Cross-account resource search
aliyun resourcecenter search-multi-account-resources \
  --scope <ResourceDirectoryId> \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### get-multi-account-resource-counts

Query resource count statistics across accounts.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--scope` | No | None | Search scope. Valid values: Resource Directory ID, Root Folder ID, Folder ID, or Member ID |
| `--filter` | No | None | Filter conditions. Structure: `[{Key: string, MatchType: string, Value: [string, ...]}, ...]`. **See Filter Parameter Definition below for supported Key and MatchType combinations** |
| `--group-by-key` | No | None | Grouping dimension for resource count statistics. Valid values: `ResourceType`, `RegionId`, `ResourceGroupId` |

**Usage**

```bash
# Cross-account count by resource type
aliyun resourcecenter get-multi-account-resource-counts \
  --scope <ResourceDirectoryId> \
  --group-by-key ResourceType \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### get-multi-account-resource-configuration

Query single resource configuration across accounts.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--account-id` | Yes | None | Resource Directory management account ID or member ID |
| `--resource-id` | Yes | None | Resource ID |
| `--resource-region-id` | Yes | None | Region ID. (e.g., `cn-hangzhou`) |
| `--resource-type` | Yes | None | Resource type. You can use the `scripts/query-resource-types.py` script to query accurate resource type codes. (e.g., `ACS::ECS::Instance`) |

**Usage**

```bash
# Get cross-account resource configuration
aliyun resourcecenter get-multi-account-resource-configuration \
  --account-id <AccountId> \
  --resource-type ACS::ECS::Instance \
  --resource-region-id cn-hangzhou \
  --resource-id i-bp1xxx \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### list-multi-account-tag-keys

Query tag keys across accounts.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--scope` | Yes | None | Search scope. Valid values: Resource Directory ID, Root Folder ID, Folder ID, or Member ID |
| `--match-type` | No | None | Match type. Valid values: `Equals`, `Prefix` |
| `--max-results` | No | 20 | Maximum number of entries per page. Valid values: 1~100 |
| `--next-token` | No | None | Token for querying the next page of results |
| `--tag-key` | No | None | Tag key |

**Usage**

```bash
# Cross-account list tag keys
aliyun resourcecenter list-multi-account-tag-keys \
  --scope <ResourceDirectoryId> \
  --max-results 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### list-multi-account-tag-values

Query tag values across accounts.

| Parameter | Required | Default Value | Description |
|-----------|----------|---------------|-------------|
| `--tag-key` | Yes | None | Tag key |
| `--scope` | No | None | Search scope. Valid values: Resource Directory ID, Root Folder ID, Folder ID, or Member ID |
| `--match-type` | No | None | Match type. Valid values: `Equals`, `Prefix` |
| `--max-results` | No | 20 | Maximum number of entries per page. Valid values: 1~100 |
| `--next-token` | No | None | Token for querying the next page of results |
| `--tag-value` | No | None | Tag value |

**Usage**

```bash
# Cross-account list tag values
aliyun resourcecenter list-multi-account-tag-values \
  --scope <ResourceDirectoryId> \
  --tag-key env \
  --max-results 100 \
  --user-agent AlibabaCloud-Agent-Skills
```
---

## Filter Parameter Definition

> **Multiple array elements are combined with logical AND**
> **Filter Parameter Validation Rules** — The `--filter` parameter uses `Key` + `MatchType` + `Value` structure. **MUST** follow the allowed combinations below. Using unsupported `MatchType` for a `Key` will cause API errors.


| Filter Key | Supported MatchType | Description |
| - | - | - |
| `ResourceType` | `Equals` | Exact match on resource type code (e.g., `ACS::ECS::Instance`) |
| `RegionId` | `Equals` | Exact match on region ID (e.g., `cn-hangzhou`) |
| `ResourceId` | `Equals`, `Prefix` | Exact or prefix match on resource ID |
| `ResourceGroupId` | `Equals`, `Exists`, `NotExists` | Exact match or existence check on resource group ID |
| `ResourceName` | `Equals`, `Contains` | Exact match or substring match (`Contains`) on resource name |
| `Tag` | `Contains`, `NotContains`, `NotExists` | Tag-based filtering: contains specific tag, excludes tag, or untagged resources |
| `VpcId` | `Equals` | Exact match on VPC ID |
| `VSwitchId` | `Equals` | Exact match on VSwitch ID |
| `IpAddress` | `Equals`, `Contains` | Exact match or substring match (`Contains`) on IP address |

**Tag filter examples** (JSON array for `--filter`):

1. **`Contains` and `NotContains`** — Use the same `Value` shape: a **JSON string** for the tag (key-only or key+value).

   ```json
   # key-only
   [{"Key":"Tag","MatchType":"Contains","Value":["{\"key\":\"env\"}"]}]
   # key+value
   [{"Key":"Tag","MatchType":"NotContains","Value":["{\"key\":\"env\",\"value\":\"prod\"}"]}]
   ```

2. **`NotExists`** — resources that **have no user tags** (untagged). Use only `Key` and `MatchType`; **do not** pass `Value`.

   ```json
   [{"Key":"Tag","MatchType":"NotExists"}]
   ```