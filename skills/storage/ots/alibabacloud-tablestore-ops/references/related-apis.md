# Tablestore CLI - Related APIs Reference (Read-Only)

Complete reference for Tablestore CLI **read-only** commands for instance and data table operations via `aliyun otsutil`.

> **Note:** All commands are executed using `aliyun otsutil <command>` format. Credentials are managed via `aliyun configure`.

## Instance Read Commands

### config

Configure instance endpoint for table operations. Note: Credentials are handled by Aliyun CLI (`aliyun configure`), not this command.

**Syntax:**
```bash
aliyun otsutil config [--endpoint <endpoint>] [--instance <instanceName>]
```

**Parameters:**

| Parameter | Required | Type | Description | Example |
|-----------|----------|------|-------------|---------|
| `--endpoint` | No | String | Instance endpoint URL. Required to operate on instance resources. | `https://myinstance.cn-hangzhou.ots.aliyuncs.com` |
| `--instance` | No | String | Instance name. Required to operate on instance resources. | `myinstance` |

**Endpoint Format:**

| Network Type | Format |
|--------------|--------|
| Public | `https://<instance_name>.<region_id>.ots.aliyuncs.com` |
| VPC | `https://<instance_name>.<region_id>.vpc.tablestore.aliyuncs.com` |

**Examples:**

```bash
# Configure instance endpoint
aliyun otsutil config --endpoint https://myinstance.cn-hangzhou.ots.aliyuncs.com --instance myinstance
```

**Response:**
```json
{
  "Endpoint": "https://myinstance.cn-hangzhou.ots.aliyuncs.com",
  "AccessKeyId": "LTAI5t***",
  "AccessKeySecret": "7NR2***",
  "AccessKeySecretToken": "",
  "Instance": "myinstance"
}
```

---

### describe_instance

Get detailed information about a specific instance.

**Syntax:**
```bash
aliyun otsutil describe_instance -r <regionId> -n <instanceName>
```

**Parameters:**

| Parameter | Required | Type | Description | Example |
|-----------|----------|------|-------------|---------|
| `-n` | Yes | String | Name of the instance to describe. | `myinstance` |
| `-r` | Yes | String | Region ID where the instance is located. | `cn-hangzhou` |

**Example:**
```bash
aliyun otsutil describe_instance -r cn-hangzhou -n myinstance
```

**Response:**
```json
{
  "ClusterType": "ssd",
  "CreateTime": "2024-07-18 09:15:10",
  "Description": "First instance created by CLI.",
  "InstanceName": "myinstance",
  "Network": "NORMAL",
  "Quota": {
    "EntityQuota": 64
  },
  "ReadCapacity": 5000,
  "Status": 1,
  "TagInfos": {},
  "UserId": "1379************",
  "WriteCapacity": 5000
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ClusterType` | String | Storage type: `ssd` (high-performance) or `hybrid` (capacity) |
| `CreateTime` | String | Instance creation timestamp |
| `Description` | String | User-defined instance description |
| `InstanceName` | String | Instance name |
| `Network` | String | Network type: `NORMAL` (public) or `VPC` |
| `Quota.EntityQuota` | Integer | Maximum number of tables allowed |
| `ReadCapacity` | Integer | Reserved read throughput (CU) |
| `Status` | Integer | Instance status: `1` = Running |
| `TagInfos` | Object | User-defined tags |
| `UserId` | String | Alibaba Cloud account ID |
| `WriteCapacity` | Integer | Reserved write throughput (CU) |

---

### list_instance

List all instances in a specified region.

**Syntax:**
```bash
aliyun otsutil list_instance -r <regionId>
```

**Parameters:**

| Parameter | Required | Type | Description | Example |
|-----------|----------|------|-------------|---------|
| `-r` | Yes | String | Region ID to list instances from. | `cn-hangzhou` |

**Example:**
```bash
aliyun otsutil list_instance -r cn-hangzhou
```

**Response:**
```json
[
  "myinstance",
  "another-instance",
  "test-instance"
]
```

**Notes:**
- Returns an empty array `[]` if no instances exist in the region
- Only lists instances owned by the authenticated account

---

## Data Table Read Commands

### use

Select a data table for subsequent operations.

**Syntax:**
```bash
aliyun otsutil use --wc -t <tableName>
```

**Parameters:**

| Parameter | Required | Type | Description | Example |
|-----------|----------|------|-------------|--------|
| `--wc` | No | Flag | Indicates target is a data table (wide column) or index table | N/A |
| `-t, --table` | Yes | String | Table name to select | `mytable` |

**Example:**
```bash
aliyun otsutil use -t mytable
```

---

### list

List table names under the current instance.

**Syntax:**
```bash
aliyun otsutil list [options]
```

**Parameters:**

| Parameter | Required | Type | Description | Example |
|-----------|----------|------|-------------|--------|
| `-a, --all` | No | Flag | List all table names (data + timeseries) | N/A |
| `-d, --detail` | No | Flag | List tables with detailed information | N/A |
| `-w, --wc` | No | Flag | List only data table (wide column) names | N/A |
| `-t, --ts` | No | Flag | List only timeseries table names | N/A |

**Examples:**
```bash
# List tables of the current type
aliyun otsutil list

# List all tables
aliyun otsutil list -a

# List only data tables
aliyun otsutil list -w

# List only timeseries tables
aliyun otsutil list -t
```

---

### desc

View detailed table information including primary keys, TTL, max versions, and throughput.

**Syntax:**
```bash
aliyun otsutil desc [-t <tableName>] [-f <format>] [-o <outputPath>]
```

**Parameters:**

| Parameter | Required | Type | Description | Example |
|-----------|----------|------|-------------|--------|
| `-t, --table` | No | String | Table name. If omitted, describes the currently selected table (via `use`) | `mytable` |
| `-f, --print_format` | No | String | Output format: `json` (default) or `table` | `json` |
| `-o, --output` | No | String | Save output to a local JSON file | `/tmp/meta.json` |

**Examples:**
```bash
# Describe the currently selected table
aliyun otsutil desc

# Describe a specific table
aliyun otsutil desc -t mytable

# Output in table format
aliyun otsutil desc -t mytable -f table

# Save table info to file
aliyun otsutil desc -t mytable -o /tmp/table_meta.json
```

**Response:**
```json
{
  "Name": "mytable",
  "Meta": {
    "Pk": [
      { "C": "uid", "T": "string", "Opt": "none" },
      { "C": "pid", "T": "integer", "Opt": "none" }
    ]
  },
  "Option": {
    "TTL": -1,
    "Version": 1
  },
  "CU": {
    "Read": 0,
    "Write": 0
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `Name` | String | Table name |
| `Meta.Pk[].C` | String | Primary key column name |
| `Meta.Pk[].T` | String | Primary key type: `string`, `integer`, `binary` |
| `Meta.Pk[].Opt` | String | Option: `none` or `auto` (auto-increment) |
| `Option.TTL` | Integer | Data time-to-live in seconds (`-1` = never expire) |
| `Option.Version` | Integer | Max attribute column versions retained |
| `CU.Read` | Integer | Reserved read capacity units |
| `CU.Write` | Integer | Reserved write capacity units |

---

## Other Useful Commands

### help

Display help information for commands.

**Syntax:**
```bash
aliyun otsutil help
aliyun otsutil help <command>
```

**Example:**
```bash
aliyun otsutil help desc
```

### quit / exit

Not applicable for `aliyun otsutil` - commands are executed directly without entering an interactive session.

---

## API Mapping

| CLI Command | Underlying API | Description |
|-------------|---------------|-------------|
| `aliyun otsutil config` | N/A (local config) | Configure instance endpoint |
| `aliyun otsutil describe_instance` | GetInstance | Get instance details |
| `aliyun otsutil list_instance` | ListInstance | List instances in region |
| `aliyun otsutil use` | N/A (local selection) | Select table for operations |
| `aliyun otsutil list` | ListTable | List tables in instance |
| `aliyun otsutil desc` | DescribeTable | Get table details |

## Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `OTSParameterInvalid` | Invalid parameter value | Check parameter format and constraints |
| `OTSQuotaExhausted` | Quota limit reached | Contact support to increase quota |
| `OTSServerBusy` | Server temporarily unavailable | Retry after a short delay |
| `OTSInternalServerError` | Internal server error | Retry or contact support |
| `OTSAuthFailed` | Authentication failed | Verify AccessKey credentials |
| `OTSPermissionDenied` | Permission denied | Check RAM policy permissions |

## Region Reference

| Region Name | Region ID |
|-------------|-----------|
| China (Hangzhou) | cn-hangzhou |
| China (Shanghai) | cn-shanghai |
| China (Qingdao) | cn-qingdao |
| China (Beijing) | cn-beijing |
| China (Zhangjiakou) | cn-zhangjiakou |
| China (Hohhot) | cn-huhehaote |
| China (Ulanqab) | cn-wulanchabu |
| China (Shenzhen) | cn-shenzhen |
| China (Heyuan) | cn-heyuan |
| China (Guangzhou) | cn-guangzhou |
| China (Chengdu) | cn-chengdu |
| China (Hong Kong) | cn-hongkong |
| Singapore | ap-southeast-1 |
| Sydney | ap-southeast-2 |
| Malaysia (Kuala Lumpur) | ap-southeast-3 |
| Indonesia (Jakarta) | ap-southeast-5 |
| India (Mumbai) | ap-south-1 |
| Japan (Tokyo) | ap-northeast-1 |
| US (Silicon Valley) | us-west-1 |
| US (Virginia) | us-east-1 |
| Germany (Frankfurt) | eu-central-1 |
| UK (London) | eu-west-1 |
| UAE (Dubai) | me-east-1 |
