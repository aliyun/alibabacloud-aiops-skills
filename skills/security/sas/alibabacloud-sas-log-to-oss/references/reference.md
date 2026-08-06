
Detailed reference documentation for Alibaba Cloud Log Service (2020-12-30) OSS Export APIs.

## API Overview

| Method | Path | Interface Name |
|--------|------|----------------|
| POST | `/ossexports` | CreateOSSExport - Create an export task |
| GET | `/ossexports` | ListOSSExports - List export tasks |
| GET | `/ossexports/{name}` | GetOSSExport - Get an export task |
| PUT | `/ossexports/{name}` | UpdateOSSExport - Update an export task |
| PUT | `/ossexports/{name}?action=START` | StartOSSExport - Start an export task |
| PUT | `/ossexports/{name}?action=STOP` | StopOSSExport - Stop an export task |
| DELETE | `/ossexports/{name}` | DeleteOSSExport - Delete an export task |
| GET | `/logstores` | ListLogStores - List LogStores |

The request Host format is `{project}.{region}.log.aliyuncs.com`.

---

## CreateOSSExport - Create an Export Task

Exports logs from a LogStore to an OSS Bucket.

**Request Body (CreateOSSExportRequest):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Task name. Lowercase letters, digits, hyphens (-), underscores (_). 2-64 characters, unique within the same Project. |
| `displayName` | string | Yes | Display name. |
| `description` | string | No | Task description. |
| `configuration` | OSSExportConfiguration | Yes | Task configuration, see below. |

**OSSExportConfiguration (Task Configuration):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `logstore` | string | Yes | Source LogStore name. |
| `roleArn` | string | Yes | Read SLS RAM role ARN. Format: `acs:ram::{account_id}:role/aliyunlogdefaultrole` |
| `sink` | OSSExportConfigurationSink | Yes | OSS sink configuration, see below. |
| `fromTime` | long | No | Start time. `1` means from the first log; a Unix timestamp means starting from a specific time. |
| `toTime` | long | No | End time. `0` means run forever; a Unix timestamp means auto-stop at the specified time. |

**OSSExportConfigurationSink (OSS Sink Configuration):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `endpoint` | string | Yes | OSS internal endpoint. Example: `https://oss-cn-hangzhou-internal.aliyuncs.com` |
| `bucket` | string | Yes | OSS Bucket name. Must be in the same region as the SLS Project, and WORM must not be enabled. |
| `prefix` | string | No | OSS file prefix/directory. Cannot start with `/` or `\`. |
| `suffix` | string | No | OSS file suffix. Example: `.json` |
| `roleArn` | string | Yes | Write OSS RAM role ARN. |
| `pathFormat` | string | No | Partition format. Default: `%Y/%m/%d/%H/%M`, follows strptime API. |
| `pathFormatType` | string | No | Partition format type. Value: `time`. |
| `timeZone` | string | No | Time zone. Example: `+0800` for UTC+8. |
| `contentType` | string | Yes | File storage format: `json`, `csv`, `parquet`, `orc`. |
| `contentDetail` | object | Yes | Content configuration, varies by contentType, see below. |
| `compressionType` | string | No | Compression type: `snappy`, `gzip`, `zstd`, `none`. Default: `snappy`. |
| `bufferInterval` | long | No | Buffer interval, in seconds. Range: 300-900. Default: 300. |
| `bufferSize` | long | No | Buffer size, in MB. Range: 5-256. Default: 256. |
| `delaySeconds` | long | No | Delivery delay, in seconds. |

**contentDetail by contentType:**

### JSON Format
```json
{"enableTag": true}
```
- `enableTag` (boolean, required): Whether to deliver tag fields

### CSV Format
```json
{
    "columns": ["field1", "field2", "field3"],
    "delimiter": ",",
    "header": true,
    "lineFeed": "\n",
    "null": "-",
    "quote": "\""
}
```

### Parquet / ORC Format
```json
{
    "columns": [
        {"name": "field1", "type": "string"},
        {"name": "field2", "type": "string"}
    ]
}
```

**Request Example:**

```json
{
    "name": "export-siem-log-to-oss",
    "displayName": "SIEM Log Export",
    "description": "Export SIEM logs to OSS cold storage",
    "configuration": {
        "logstore": "siem-log",
        "roleArn": "acs:ram::123456789012:role/aliyunlogdefaultrole",
        "sink": {
            "endpoint": "https://oss-cn-hangzhou-internal.aliyuncs.com",
            "bucket": "my-cold-storage-bucket",
            "prefix": "sls-export/siem-log/",
            "suffix": ".json",
            "roleArn": "acs:ram::123456789012:role/aliyunlogdefaultrole",
            "pathFormat": "%Y/%m/%d/%H/%M",
            "pathFormatType": "time",
            "timeZone": "+0800",
            "contentType": "json",
            "contentDetail": {"enableTag": true},
            "compressionType": "snappy",
            "bufferInterval": 300,
            "bufferSize": 256,
            "delaySeconds": 0
        },
        "fromTime": 1,
        "toTime": 0
    }
}
```

---

## ListOSSExports - List Export Tasks

Lists all OSS export tasks under a specified Project.

**Query Parameters (ListOSSExportsRequest):**

| Field | Type | Description |
|-------|------|-------------|
| `offset` | int | Pagination offset. Default: 0. |
| `size` | int | Page size. Default: 10. |
| `logstore` | string | Filter by LogStore name. |

**Response (ListOSSExportsResponseBody):**

| Field | Type | Description |
|-------|------|-------------|
| `total` | int | Total number of export tasks. |
| `count` | int | Number of tasks returned in this response. |
| `results` | List[OSSExport] | List of export tasks, see below. |

---

## GetOSSExport - Get an Export Task

Gets detailed information about a specified OSS export task.

**Path Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| `ossExportName` | string | Task name. |

**Response (OSSExport):**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Task name. |
| `displayName` | string | Display name. |
| `description` | string | Task description. |
| `configuration` | OSSExportConfiguration | Task configuration. |
| `status` | string | Task status: `RUNNING` (running), `STOPPED` (stopped), etc. |
| `scheduleId` | string | Schedule ID. |
| `createTime` | long | Creation time (Unix timestamp). |
| `lastModifiedTime` | long | Last modified time (Unix timestamp). |

---

## StartOSSExport / StopOSSExport - Start/Stop an Export Task

Starts or stops a specified OSS export task.

**Path:** `PUT /ossexports/{ossExportName}?action=START` or `?action=STOP`

---

## DeleteOSSExport - Delete an Export Task

Deletes a specified OSS export task.

**Path:** `DELETE /ossexports/{ossExportName}`

---

## UpdateOSSExport - Update an Export Task

Updates the configuration of an existing OSS export task.

**Request Body (UpdateOSSExportRequest):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `displayName` | string | Yes | Display name. |
| `description` | string | No | Task description. |
| `configuration` | OSSExportConfiguration | Yes | Updated task configuration. |

---

## ListLogStores - List LogStores

Lists all LogStores under a specified Project.

**Query Parameters (ListLogStoresRequest):**

| Field | Type | Description |
|-------|------|-------------|
| `offset` | int | Pagination offset. Default: 0. |
| `size` | int | Page size. Max: 500. Default: 200. |
| `logstoreName` | string | Fuzzy match LogStore name. |
| `telemetryType` | string | `None` = all types, `Metrics` = Metrics type only. |
| `mode` | string | `standard` or `query`. |

**Response (ListLogStoresResponseBody):**

| Field | Type | Description |
|-------|------|-------------|
| `total` | int | Total number of LogStores. |
| `count` | int | Number of LogStores returned. |
| `logstores` | List[string] | List of LogStore names. |

---

## OSS File Path Format

The file path exported to OSS follows this pattern:

```
oss://{bucket}/{prefix}/{pathFormat}_{randomID}
```

Example:
```
oss://my-bucket/sls-export/siem-log/2024/01/15/10/30_1484913043351525351_2850008.json
```

Partition format examples:

| pathFormat | Generated Directory |
|------------|---------------------|
| `%Y/%m/%d/%H/%M` | `2024/01/15/10/30` |
| `year=%Y/mon=%m/day=%d/` | `year=2024/mon=01/day=15/` |
| `ds=%Y%m%d/%H` | `ds=20240115/10` |

For compatibility with big data platforms such as Hive/MaxCompute, it is recommended to use the `key=value` format.

---

## Region Endpoint Reference

| Region | SLS Endpoint | OSS Internal Endpoint |
|--------|-------------|----------------------|
| China (Hangzhou) | `cn-hangzhou.log.aliyuncs.com` | `https://oss-cn-hangzhou-internal.aliyuncs.com` |
| China (Shanghai) | `cn-shanghai.log.aliyuncs.com` | `https://oss-cn-shanghai-internal.aliyuncs.com` |
| China (Beijing) | `cn-beijing.log.aliyuncs.com` | `https://oss-cn-beijing-internal.aliyuncs.com` |
| China (Shenzhen) | `cn-shenzhen.log.aliyuncs.com` | `https://oss-cn-shenzhen-internal.aliyuncs.com` |

---

## Python SDK Model Mapping

The mapping between API fields and Python attributes in the `alibabacloud_sls20201230` SDK:

| API Field | SDK Model | Python Attributes |
|-----------|-----------|-------------------|
| - | `CreateOSSExportRequest` | `name`, `display_name`, `description`, `configuration` |
| `configuration` | `OSSExportConfiguration` | `logstore`, `role_arn`, `sink`, `from_time`, `to_time` |
| `sink` | `OSSExportConfigurationSink` | `bucket`, `endpoint`, `prefix`, `suffix`, `role_arn`, `path_format`, `path_format_type`, `time_zone`, `content_type`, `content_detail`, `compression_type`, `buffer_interval`, `buffer_size`, `delay_seconds` |
| - | `ListOSSExportsRequest` | `logstore`, `offset`, `size` |
| - | `ListOSSExportsResponseBody` | `total`, `count`, `results` |
| - | `OSSExport` (response item) | `name`, `display_name`, `description`, `configuration`, `status`, `schedule_id`, `create_time`, `last_modified_time` |
| - | `ListLogStoresRequest` | `logstore_name`, `offset`, `size`, `telemetry_type`, `mode` |
| - | `ListLogStoresResponseBody` | `total`, `count`, `logstores` |

**Client Method Reference:**

| Operation | Method |
|-----------|--------|
| List LogStores | `client.list_log_stores(project, request)` |
| Create export task | `client.create_ossexport(project, request)` |
| List export tasks | `client.list_ossexports(project, request)` |
| Get export task | `client.get_ossexport(project, oss_export_name)` |
| Update export task | `client.update_ossexport(project, oss_export_name, request)` |
| Start export task | `client.start_ossexport(project, oss_export_name)` |
| Stop export task | `client.stop_ossexport(project, oss_export_name)` |
| Delete export task | `client.delete_ossexport(project, oss_export_name)` |
