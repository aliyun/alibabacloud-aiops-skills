# Related API Commands — DataWorks Data Governance Tag Management

> Note: DataWorks Data Governance Tag APIs are called primarily via the Python Common SDK (ROA style).
> If the `aliyun dataworks` CLI plugin supports these commands, plugin mode can be used
> (requires the `aliyun dataworks` plugin to be installed).

## Tag Key Management

| Operation | API Name | HTTP Method | Path | Description |
|-----------|---------|-------------|------|-------------|
| Create tag key | CreateDataAssetTag | POST | `/api/v1/data-governance/tags` | Create a new tag key with optional initial values |
| Update tag key | UpdateDataAssetTag | PUT | `/api/v1/data-governance/tags` | Update a tag key's values, description, or managers |
| List tag keys | ListDataAssetTags | GET | `/api/v1/data-governance/tags` | Paginated query of tag keys; supports fuzzy search by Key and filtering by Category |

## Data Asset Query

| Operation | API Name | HTTP Method | Path | Description |
|-----------|---------|-------------|------|-------------|
| List data assets | ListDataAssets | GET | `/api/v1/data-governance/assets` | Paginated query of data assets by type, tags, name, owner, or IDs; supports sorting |

## Data Asset Bind / Unbind

| Operation | API Name | HTTP Method | Path | Description |
|-----------|---------|-------------|------|-------------|
| Bind tags to assets | TagDataAssets | POST | `/api/v1/data-governance/tags/bind` | Batch-bind tags to data assets; Tags max 20, DataAssetIds max 100 |
| Unbind tags from assets | UnTagDataAssets | POST | `/api/v1/data-governance/tags/unbind` | Batch-unbind tags from data assets |

## Key Parameter Reference

### ListDataAssets — Type Values

| Value | Description |
|-------|-------------|
| `Table` | Data table |
| `Task` | Scheduling task |
| `Node` | Data development node |
| `WorkFlow` | Scheduling workflow |
| `DataServiceApi` | Data service API |
| `DataQualityRule` | Data quality rule |

### ListDataAssets — SortBy Values

| Value | Description |
|-------|-------------|
| `CreateTime Desc` / `CreateTime Asc` | Sort by creation time (default: `CreateTime Desc`) |
| `ModifyTime Desc` / `ModifyTime Asc` | Sort by modification time |
| `HealthScore Desc` / `HealthScore Asc` | Sort by health score |

### DataAssetType Values (TagDataAssets / UnTagDataAssets)

| Value | Description |
|-------|-------------|
| `ACS::DataWorks::Table` | DataWorks data table |
| `ACS::DataWorks::Task` | DataWorks task (requires `ProjectId` + `EnvType`) |

### Category Values

| Value | Description |
|-------|-------------|
| `Normal` | Standard tag (default) |
| `CUSTOM` | Custom tag |

### ValuePolicy Example

```json
{"type": "string", "content": "^L[1-7]$"}
```

- `type`: Value type, e.g. `string`
- `content`: Regular expression to restrict allowed tag value formats

## Python SDK Quick Reference

```python
# List all tags
resp = list_data_asset_tags(client, page_number=1, page_size=100)

# List data assets of type Table, filtered by tag and name keyword
resp = list_data_assets(
    client,
    asset_type='Table',
    tags=[{"Key": "data_level", "Value": "L1"}],
    name='dwd_',
    page_number=1,
    page_size=10
)

# Create tag key "data_level" with initial values L1–L3
resp = create_data_asset_tag(
    client,
    key='data_level',
    values=['L1', 'L2', 'L3'],
    description='Data asset security level',
    value_policy='{"type":"string","content":"^L[1-7]$"}',
    category='Normal'
)

# Bind a tag to a table
resp = tag_data_assets(
    client,
    tags=[{"Key": "data_level", "Value": "L1"}],
    data_asset_ids=["maxcompute-table.my_project.my_table"],
    data_asset_type="ACS::DataWorks::Table"
)
```
