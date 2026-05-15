# Related CLI Commands: alibabacloud-cms-dataset

All CMS Dataset CLI commands (API version 2024-03-30). All commands require `--api-version 2024-03-30`.

## Command Reference

| Command | Description | Key Parameters |
| --- | --- | --- |
| `aliyun cms get-workspace` | Verify workspace exists | `--workspace` |
| `aliyun cms put-workspace` | Create or update a workspace | `--workspace-name`, `--sls-project` (required), `--display-name`, `--description` |
| `aliyun cms list-datasets` | List datasets in a workspace | `--workspace`, `--dataset-name` (filter), `--max-results`, `--next-token` |
| `aliyun cms get-dataset` | Get dataset details and schema | `--workspace`, `--dataset-name` |
| `aliyun cms create-dataset` | Create a new dataset | `--workspace`, `--dataset-name`, `--schema`, `--description` |
| `aliyun cms update-dataset` | Update dataset description | `--workspace`, `--dataset-name`, `--description` |
| `aliyun cms delete-dataset` | Delete a dataset | `--workspace`, `--dataset-name` |
| `aliyun cms execute-query` | Execute a query against a dataset | `--workspace`, `--dataset-name`, `--type`, `--query` |

## Parameter Details

### Common Parameters

| Parameter | Description | Required |
| --- | --- | --- |
| `--api-version` | API version. Always use `2024-03-30` | Yes |
| `--workspace` | CMS workspace ID | Yes |
| `--region` | Region ID. Uses profile region if omitted | No |

### ListDatasets

| Parameter | Description | Required |
| --- | --- | --- |
| `--dataset-name` | Filter by dataset name | No |
| `--max-results` | Maximum number of results (integer) | No |
| `--next-token` | Pagination token | No |

### GetDataset / DeleteDataset

| Parameter | Description | Required |
| --- | --- | --- |
| `--dataset-name` | Dataset name | Yes |

### CreateDataset

| Parameter | Description | Required |
| --- | --- | --- |
| `--dataset-name` | Dataset name (4-63 chars, lowercase, no consecutive underscores) | Yes |
| `--schema` | Schema JSON object (single-quoted string) | Yes |
| `--description` | Dataset description | No |

### UpdateDataset

| Parameter | Description | Required |
| --- | --- | --- |
| `--dataset-name` | Dataset name | Yes |
| `--description` | New description | No |

### ExecuteQuery

| Parameter | Description | Required |
| --- | --- | --- |
| `--dataset-name` | Dataset name | Yes |
| `--type` | Query type. Always pass `SQL` | Yes |
| `--query` | Query text | Yes |

## Example Commands

```bash
# List all datasets
aliyun cms list-datasets --api-version 2024-03-30 --workspace <workspace>

# Get dataset details
aliyun cms get-dataset --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>

# Create dataset
aliyun cms create-dataset --api-version 2024-03-30 --workspace <workspace> \
  --dataset-name <name> --schema '{"field":{"type":"text","chn":true}}' --description "desc"

# Update description
aliyun cms update-dataset --api-version 2024-03-30 --workspace <workspace> \
  --dataset-name <name> --description "new description"

# Delete dataset
aliyun cms delete-dataset --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>

# Execute query
aliyun cms execute-query --api-version 2024-03-30 --workspace <workspace> \
  --dataset-name <name> --type SQL --query 'SELECT count(1) FROM "datasetname"'
```
