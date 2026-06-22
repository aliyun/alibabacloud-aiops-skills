# Related Commands — Kafka Capacity Assessment Skill

## Kafka Product Commands

| Command | Description | Key Parameters |
|:---|:---|:---|
| `aliyun alikafka get-instance-list` | Retrieve instance information for a specified region | `--biz-region-id` (required), `--instance-id`, `--series` |

### Parameter Details

#### get-instance-list

| Parameter | Type | Required | Description |
|:---|:---|:---|:---|
| `--biz-region-id` | string | Yes | Region ID of the instance |
| `--instance-id` | list | No | Instance ID list; format: `--instance-id value1 value2 value3` |
| `--series` | string | No | Instance series identifier; valid values: `v2`, `v3`, `confluent` |
| `--order-id` | string | No | Order ID (not supported for Serverless instances) |
| `--resource-group-id` | string | No | Resource group ID |
| `--tag` | list | No | Tag list; format: `--tag Key=a Value=b` |

## CloudMonitor Commands

| Command | Description | Key Parameters |
|:---|:---|:---|
| `aliyun cms describe-metric-list` | Query monitoring data for a specified cloud product | `--namespace` (required), `--metric-name` (required), `--start-time`, `--end-time`, `--period`, `--dimensions` |

### Parameter Details

#### describe-metric-list

| Parameter | Type | Required | Description |
|:---|:---|:---|:---|
| `--namespace` | string | Yes | Data namespace for the cloud product; fixed value for Kafka: `acs_kafka` |
| `--metric-name` | string | Yes | Metric name; select the metric corresponding to the instance series |
| `--start-time` | string | No | Start time; supports `YYYY-MM-DD HH:mm:ss` format or Unix timestamp in milliseconds |
| `--end-time` | string | No | End time; the interval between StartTime and EndTime must not exceed 31 days |
| `--period` | string | No | Aggregation interval in seconds; valid values: 15, 60, 900, 3600 |
| `--dimensions` | string | No | Monitoring dimensions in JSON format; e.g., `[{"instanceId":"xxx"}]` |
| `--express` | string | No | Real-time computation expression; currently only `groupby` is supported |
| `--length` | string | No | Number of records per page; maximum: 1,440 |
| `--next-token` | string | No | Pagination cursor |

## Auxiliary Commands

| Command | Description |
|:---|:---|
| `aliyun version` | Display CLI version (must be >= 3.3.3) |
| `aliyun configure list` | Display the current credential configuration status |
| `aliyun configure set --auto-plugin-install true` | Enable automatic plugin installation |
| `aliyun plugin update` | Update all installed plugins |
