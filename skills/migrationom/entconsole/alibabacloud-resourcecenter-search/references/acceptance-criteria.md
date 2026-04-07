# Acceptance Criteria: alibabacloud-resourcecenter-search

**Scenario**: Cross-region, Cross-product, Cross-account Global Resource Inventory, Search & Statistics
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — `resourcecenter`

#### CORRECT
```bash
aliyun resourcecenter search-resources ...
aliyun resourcecenter enable-resource-center ...
```

#### INCORRECT
```bash
aliyun resource-center search-resources ...    # Wrong: product name has no hyphen
aliyun ResourceCenter SearchResources ...      # Wrong: not plugin mode
```

## 2. Commands — All verified via `--help`

| Command | Verified |
|---------|----------|
| `enable-resource-center` | Yes |
| `disable-resource-center` | Yes |
| `get-resource-center-service-status` | Yes |
| `search-resources` | Yes |
| `get-resource-counts` | Yes |
| `get-resource-configuration` | Yes |
| `batch-get-resource-configurations` | Yes |
| `list-tag-keys` | Yes |
| `list-tag-values` | Yes |
| `enable-multi-account-resource-center` | Yes |
| `disable-multi-account-resource-center` | Yes |
| `get-multi-account-resource-center-service-status` | Yes |
| `search-multi-account-resources` | Yes |
| `get-multi-account-resource-counts` | Yes |
| `get-multi-account-resource-configuration` | Yes |
| `list-multi-account-tag-keys` | Yes |
| `list-multi-account-tag-values` | Yes |

## 3. Parameters — All verified via `--help`

### search-resources

| Parameter | Verified | Notes |
|-----------|----------|-------|
| `--filter` | Yes | list, JSON array format: `[{"Key":"...","MatchType":"...","Value":["..."]}]` |
| `--max-results` | Yes | int, range 1~500, default 20 |
| `--next-token` | Yes | string |
| `--sort-criterion` | Yes | object, format: `Key=xxx Order=xxx` |
| `--resource-group-id` | Yes | string |
| `--include-deleted-resources` | Yes | bool |

### search-multi-account-resources

| Parameter | Verified | Notes |
|-----------|----------|-------|
| `--scope` | Yes | **Required**. Resource Directory ID / Root Folder ID / Folder ID / Member ID |
| `--filter` | Yes | list, JSON array format |
| `--max-results` | Yes | int, range 1~100, default 20 |
| `--next-token` | Yes | string |
| `--sort-criterion` | Yes | object |

### get-resource-counts

| Parameter | Verified | Notes |
|-----------|----------|-------|
| `--group-by-key` | Yes | Enum: `ResourceType`, `RegionId`, `ResourceGroupId` |
| `--filter` | Yes | list, JSON array format |
| `--include-deleted-resources` | Yes | bool |

### get-multi-account-resource-counts

| Parameter | Verified | Notes |
|-----------|----------|-------|
| `--scope` | Yes | string, Resource Directory/Folder/Member ID |
| `--group-by-key` | Yes | Enum: `ResourceType`, `RegionId`, `ResourceGroupId` |
| `--filter` | Yes | list, JSON array format |

### get-resource-configuration

| Parameter | Verified | Notes |
|-----------|----------|-------|
| `--resource-id` | Yes | **Required** |
| `--resource-region-id` | Yes | **Required** |
| `--resource-type` | Yes | **Required** |

### list-tag-values

| Parameter | Verified | Notes |
|-----------|----------|-------|
| `--tag-key` | Yes | **Required** |
| `--match-type` | Yes | Enum: `Equals`, `Prefix` |
| `--max-results` | Yes | int, range 1~100, default 20 |

## 4. Enum Values Verified

| Parameter | Command | Valid Values |
|-----------|---------|-------------|
| `--group-by-key` | `get-resource-counts` | `ResourceType`, `RegionId`, `ResourceGroupId` |
| `--group-by-key` | `get-multi-account-resource-counts` | `ResourceType`, `RegionId`, `ResourceGroupId` |
| `--match-type` | `list-tag-keys`, `list-tag-values` | `Equals`, `Prefix` |

## 5. Filter Value Format Verified

The `--filter` parameter accepts a JSON array string:

#### CORRECT
```bash
--filter '[{"Key":"ResourceType","MatchType":"Equals","Value":["ACS::ECS::Instance"]}]'
```

#### INCORRECT
```bash
--filter Key=ResourceType MatchType=Equals Value=ACS::ECS::Instance    # Wrong: not JSON format
--filter '{"Key":"ResourceType","MatchType":"Equals","Value":["ACS::ECS::Instance"]}'  # Wrong: not array
```

## 6. `--user-agent` Flag

#### CORRECT
```bash
aliyun resourcecenter search-resources --max-results 50 --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
aliyun resourcecenter search-resources --max-results 50    # Missing --user-agent
```

All `aliyun` commands in the skill include `--user-agent AlibabaCloud-Agent-Skills`.
