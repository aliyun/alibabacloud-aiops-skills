# PTS Scene JSON Reference

This document provides complete JSON structure reference for creating PTS stress testing scenarios.

## Basic Scene Structure (GET Request)

Minimum required fields for a working PTS scene:

```json
{
  "SceneName": "<SCENE_NAME>",
  "RelationList": [
    {
      "RelationName": "serial-link-1",
      "ApiList": [
        {
          "ApiName": "api-1",
          "Url": "<TARGET_URL>",
          "Method": "GET",
          "TimeoutInSecond": 10,
          "RedirectCountLimit": 10,
          "HeaderList": [
            {
              "HeaderName": "User-Agent",
              "HeaderValue": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
          ],
          "CheckPointList": [
            {
              "CheckPoint": "",
              "CheckType": "STATUS_CODE",
              "Operator": "eq",
              "ExpectValue": "200"
            }
          ]
        }
      ]
    }
  ],
  "LoadConfig": {
    "TestMode": "concurrency_mode",
    "MaxRunningTime": 1,
    "AutoStep": false,
    "Configuration": {
      "AllConcurrencyBegin": 10,
      "AllConcurrencyLimit": 10
    }
  },
  "AdvanceSetting": {
    "LogRate": 1,
    "ConnectionTimeoutInSecond": 5
  }
}
```

## Complete Scene Structure (All Fields)

For advanced scenarios with POST requests, file parameters, and global variables:

```json
{
  "SceneName": "my-stress-test",
  "RelationList": [
    {
      "RelationName": "user-flow",
      "ApiList": [
        {
          "ApiName": "login-api",
          "Url": "https://api.example.com/login",
          "Method": "POST",
          "Body": {
            "ContentType": "application/json",
            "BodyValue": "{\"username\":\"${name}\",\"token\":\"${global}\"}"
          },
          "TimeoutInSecond": 10,
          "RedirectCountLimit": 0,
          "HeaderList": [
            {
              "HeaderName": "Content-Type",
              "HeaderValue": "application/json"
            }
          ],
          "ExportList": [
            {
              "ExportName": "userId",
              "ExportType": "BODY_JSON",
              "ExportValue": "$.data.userId"
            }
          ],
          "CheckPointList": [
            {
              "CheckPoint": "",
              "CheckType": "STATUS_CODE",
              "Operator": "eq",
              "ExpectValue": "200"
            }
          ]
        }
      ],
      "FileParameterExplainList": [
        {
          "FileName": "users.csv",
          "FileParamName": "name,uid",
          "CycleOnce": false,
          "BaseFile": true
        }
      ]
    }
  ],
  "LoadConfig": {
    "TestMode": "concurrency_mode",
    "MaxRunningTime": 10,
    "AutoStep": true,
    "Increment": 30,
    "KeepTime": 3,
    "Configuration": {
      "AllConcurrencyBegin": 10,
      "AllConcurrencyLimit": 100
    }
  },
  "AdvanceSetting": {
    "LogRate": 10,
    "ConnectionTimeoutInSecond": 10,
    "SuccessCode": "429",
    "DomainBindingList": [
      {
        "Domain": "api.example.com",
        "Ips": ["1.1.1.1", "2.2.2.2"]
      }
    ]
  },
  "FileParameterList": [
    {
      "FileName": "users.csv",
      "FileOssAddress": "https://bucket.oss.aliyuncs.com/users.csv"
    }
  ],
  "GlobalParameterList": [
    {
      "ParamName": "global",
      "ParamValue": "test-token-123"
    }
  ]
}
```

## Field Reference

### Root Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `SceneName` | string | Yes | Name of the stress testing scenario |
| `SceneId` | string | No | Scene ID (required for updating existing scene) |
| `RelationList` | array | Yes | List of serial links (request chains) |
| `LoadConfig` | object | Yes | Load testing configuration |
| `AdvanceSetting` | object | Recommended | Advanced settings for timeout, logging, etc. |
| `FileParameterList` | array | No | CSV file parameters for data-driven testing |
| `GlobalParameterList` | array | No | Global variables available to all APIs |

### API Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ApiName` | string | Yes | Name of the API |
| `Url` | string | Yes | Target URL |
| `Method` | string | Yes | HTTP method (GET, POST, PUT, DELETE, etc.) |
| `TimeoutInSecond` | int | Recommended | Request timeout in seconds (default: 10) |
| `RedirectCountLimit` | int | Recommended | Max redirects (10 for normal, 0 to disable) |
| `HeaderList` | array | Recommended | HTTP request headers |
| `Body` | object | No | Request body (for POST/PUT requests) |
| `CheckPointList` | array | Recommended | Response validation assertions |
| `ExportList` | array | No | Extract values from response |

### Body Configuration

| Field | Type | Description |
|-------|------|-------------|
| `ContentType` | string | Content type (application/json, application/x-www-form-urlencoded) |
| `BodyValue` | string | Request body content, supports `${variable}` placeholders |

### HeaderList Item

| Field | Type | Description |
|-------|------|-------------|
| `HeaderName` | string | Header name (e.g., Content-Type, User-Agent) |
| `HeaderValue` | string | Header value |

### CheckPointList Item

| Field | Type | Description |
|-------|------|-------------|
| `CheckPoint` | string | Check point name (can be empty) |
| `CheckType` | string | Type: STATUS_CODE, BODY_JSON, BODY_TEXT, HEADER, RT |
| `Operator` | string | Operator: eq, ne, gt, lt, ge, le, contains, not_contains |
| `ExpectValue` | string | Expected value |

### ExportList Item

| Field | Type | Description |
|-------|------|-------------|
| `ExportName` | string | Variable name to export |
| `ExportType` | string | Type: BODY_JSON, BODY_TEXT, HEADER, COOKIE |
| `ExportValue` | string | JSONPath or extraction expression |

### LoadConfig Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `TestMode` | string | Yes | `concurrency_mode` or `tps_mode` |
| `MaxRunningTime` | int | Yes | Duration in **minutes** (range: 1-1440) |
| `AutoStep` | bool | No | Enable gradual concurrency increase |
| `Increment` | int | No | Concurrency increase interval (seconds) |
| `KeepTime` | int | No | Hold time at each level (minutes) |
| `Configuration` | object | Yes | Concurrency/TPS limits |

### Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `AllConcurrencyBegin` | int | Starting concurrent users |
| `AllConcurrencyLimit` | int | Maximum concurrent users |
| `AllRpsBegin` | int | Starting RPS (for tps_mode) |
| `AllRpsLimit` | int | Maximum RPS (for tps_mode) |

### AdvanceSetting Fields

| Field | Type | Description |
|-------|------|-------------|
| `LogRate` | int | Log sampling rate (1-100) |
| `ConnectionTimeoutInSecond` | int | Connection timeout in seconds |
| `SuccessCode` | string | Additional HTTP codes to treat as success (e.g., "429") |
| `DomainBindingList` | array | Custom DNS resolution |

### FileParameterList Item

| Field | Type | Description |
|-------|------|-------------|
| `FileName` | string | CSV file name |
| `FileOssAddress` | string | OSS URL of the CSV file |

### FileParameterExplainList Item

| Field | Type | Description |
|-------|------|-------------|
| `FileName` | string | CSV file name (must match FileParameterList) |
| `FileParamName` | string | Comma-separated column names |
| `CycleOnce` | bool | Use each row only once |
| `BaseFile` | bool | Is this the base file for iteration |

### GlobalParameterList Item

| Field | Type | Description |
|-------|------|-------------|
| `ParamName` | string | Variable name (use as `${ParamName}` in URLs/Body) |
| `ParamValue` | string | Variable value |

## Common Patterns

### Simple GET Request

```json
{
  "ApiName": "homepage",
  "Url": "https://example.com",
  "Method": "GET",
  "TimeoutInSecond": 10,
  "RedirectCountLimit": 10,
  "HeaderList": [
    {"HeaderName": "User-Agent", "HeaderValue": "Mozilla/5.0"}
  ],
  "CheckPointList": [
    {"CheckPoint": "", "CheckType": "STATUS_CODE", "Operator": "eq", "ExpectValue": "200"}
  ]
}
```

### POST with JSON Body

```json
{
  "ApiName": "login",
  "Url": "https://api.example.com/login",
  "Method": "POST",
  "Body": {
    "ContentType": "application/json",
    "BodyValue": "{\"username\":\"test\",\"password\":\"123456\"}"
  },
  "TimeoutInSecond": 10,
  "RedirectCountLimit": 0,
  "HeaderList": [
    {"HeaderName": "Content-Type", "HeaderValue": "application/json"}
  ],
  "CheckPointList": [
    {"CheckPoint": "", "CheckType": "STATUS_CODE", "Operator": "eq", "ExpectValue": "200"}
  ]
}
```

### Gradual Load Increase

```json
{
  "LoadConfig": {
    "TestMode": "concurrency_mode",
    "MaxRunningTime": 10,
    "AutoStep": true,
    "Increment": 60,
    "KeepTime": 2,
    "Configuration": {
      "AllConcurrencyBegin": 10,
      "AllConcurrencyLimit": 100
    }
  }
}
```

This configuration starts with 10 concurrent users and increases every 60 seconds, holding each level for 2 minutes, until reaching 100 concurrent users.
