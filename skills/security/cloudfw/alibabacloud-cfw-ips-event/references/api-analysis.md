# API Analysis - IPS Alert Event Analysis

Product: Cloud Firewall
API Version: 2017-12-07
Product Code: cloudfw

---

## 1. Alert Statistics

### DescribeRiskEventStatistic

**Description**: Query IPS alert statistics for a specified time range, including total attack counts, block counts, severity distribution, and untreated event counts. This provides an overview of the current security posture.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| StartTime | Long | Yes | Start time for the query (Unix timestamp in seconds) |
| EndTime | Long | Yes | End time for the query (Unix timestamp in seconds) |

**Key Response Fields**:

```
{
  "RequestId": String,              // Request ID
  "TotalAttackCnt": Integer,        // Total attack event count
  "TotalDropCnt": Integer,          // Total blocked/dropped count
  "TotalWarnCnt": Integer,          // Total warning count
  "TotalMonitorCnt": Integer,       // Total monitor/observe count
  "TotalHighCnt": Integer,          // Total high-severity event count
  "TotalMediumCnt": Integer,        // Total medium-severity event count
  "TotalLowCnt": Integer,           // Total low-severity event count
  "TotalUntreatedCnt": Integer      // Total untreated event count
}
```

---

## 2. Alert Events

### DescribeRiskEventGroup

**Description**: Query detailed IPS alert event list with grouping, filtering, and pagination support. This is the core API for alert event analysis, providing comprehensive event details including source/destination, attack type, handling status, and geo-location information.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| CurrentPage | Integer | Yes | Page number for pagination (starts from 1) |
| PageSize | Integer | Yes | Number of items per page (max 50) |
| StartTime | Long | Yes | Start time for the query (Unix timestamp in seconds) |
| EndTime | Long | Yes | End time for the query (Unix timestamp in seconds) |
| DataType | String | No | Data type filter (default: "1") |
| Direction | String | No | Traffic direction filter: "in" (inbound) or "out" (outbound) |
| SrcIP | String | No | Source IP address filter |
| DstIP | String | No | Destination IP address filter |
| VulLevel | String | No | Vulnerability severity filter: "1" (low), "2" (medium), "3" (high) |

**Key Response Fields**:

```
{
  "RequestId": String,              // Request ID
  "TotalCount": Integer,            // Total number of matching events (for pagination)
  "DataList": [                     // Array of alert event groups
    {
      "EventName": String,          // Event name/title
      "EventCount": Integer,        // Number of occurrences of this event
      "Description": String,        // Event description
      "SrcIP": String,              // Source IP address
      "DstIP": String,              // Destination IP address
      "AttackType": Integer,        // Attack type numeric ID
      "AttackTypeName": String,     // Attack type name (may not always be present)
      "AttackApp": String,          // Attack application name
      "Direction": String,          // Traffic direction ("in" or "out")
      "VulLevel": Integer,          // Vulnerability level: 1=low, 2=medium, 3=high
      "RuleResult": Integer,        // Handling result: 1=observe, 2=block
      "RuleSource": String,         // Rule source identifier
      "FirstTime": Long,            // First occurrence time (Unix timestamp in seconds)
      "LastTime": Long,             // Last occurrence time (Unix timestamp in seconds)
      "IPLocationInfo": {           // Geo-location of source IP
        "CountryName": String,      // Country name
        "CityName": String          // City name
      },
      "ResourcePrivateIPList": [    // Array of targeted private resources
        {
          "ResourceInstanceName": String,  // Resource instance name
          "ResourcePrivateIP": String,     // Private IP address
          "ResourceInstanceId": String,    // Resource instance ID
          "RegionNo": String               // Region ID
        }
      ],
      "ResourceType": String,       // Resource type of the target
      "Tag": String                 // Tag information
    }
  ]
}
```

**Pagination**: When `TotalCount` exceeds `PageSize`, increment `CurrentPage` to fetch additional pages.

---

## 3. Attack Rankings

### DescribeRiskEventTopAttackAsset

**Description**: Query the ranking of most attacked assets, showing which resources received the most attack attempts and how many were blocked.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| StartTime | Long | Yes | Start time for the query (Unix timestamp in seconds) |
| EndTime | Long | Yes | End time for the query (Unix timestamp in seconds) |

**Key Response Fields**:

```
{
  "RequestId": String,              // Request ID
  "Assets": [                       // Array of top attacked assets
    {
      "Ip": String,                 // Asset IP address
      "ResourceInstanceName": String, // Resource instance name
      "ResourceInstanceId": String,   // Resource instance ID
      "ResourceType": String,         // Resource type (e.g., "EcsEIP")
      "RegionNo": String,             // Region ID
      "AttackCnt": Integer,           // Total attack count
      "DropCnt": Integer              // Blocked/dropped count
    }
  ]
}
```

---

### DescribeRiskEventTopAttackType

**Description**: Query the ranking of attack types by frequency, showing the distribution of different attack categories (e.g., Web attacks, command execution, DoS). Requires the `Direction` parameter.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| StartTime | Long | Yes | Start time for the query (Unix timestamp in seconds) |
| EndTime | Long | Yes | End time for the query (Unix timestamp in seconds) |
| Direction | String | Yes | Traffic direction: "in" (inbound) or "out" (outbound) |

**Key Response Fields**:

```
{
  "RequestId": String,              // Request ID
  "TotalAttackCnt": Integer,        // Summary: total attack count across all types
  "TotalProtectCnt": Integer,       // Summary: total protected/blocked count across all types
  "TopAttackTypeList": [            // Array of top attack types (NOTE: not "TypeList")
    {
      "AttackType": Integer,        // Attack type numeric ID
      "AttackCnt": Integer,         // Attack count for this type
      "ProtectCnt": Integer         // Protected/blocked count (NOTE: not "DropCnt")
    }
  ]
}
```

**Attack Type ID Mapping**:

| ID | Attack Type |
|----|-------------|
| 1 | Abnormal Connection |
| 2 | Command Execution |
| 3 | Information Leak |
| 4 | Information Probing |
| 5 | DoS Attack |
| 6 | Overflow Attack |
| 7 | Web Attack |
| 8 | Other |

---

### DescribeRiskEventTopAttackApp

**Description**: Query the ranking of attacked applications, showing which application-layer targets received the most attacks.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| StartTime | Long | Yes | Start time for the query (Unix timestamp in seconds) |
| EndTime | Long | Yes | End time for the query (Unix timestamp in seconds) |

**Key Response Fields**:

```
{
  "RequestId": String,              // Request ID
  "AttackApps": [                   // Array of top attacked apps (NOTE: not "AppList")
    {
      "App": String,                // Application name (NOTE: not "AttackApp")
      "AttackCnt": Integer,         // Attack count
      "DropCnt": Integer            // Blocked/dropped count
    }
  ]
}
```

---

## 4. IPS Configuration

### DescribeDefaultIPSConfig

**Description**: Query the current IPS protection configuration, including run mode (observe/block), rule switches for basic rules, virtual patches, threat intelligence, and AI engine.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| (none required) | — | — | No required parameters; only the global `--region` flag is needed |

**Key Response Fields**:

```
{
  "RequestId": String,              // Request ID
  "RunMode": Integer,               // IPS run mode: 0=observe mode, 1=block mode
  "BasicRules": Integer,            // Basic protection rules: 0=disabled, 1=enabled
  "PatchRules": Integer,            // Virtual patch rules: 0=disabled, 1=enabled
  "CtiRules": Integer,              // Threat intelligence rules: 0=disabled, 1=enabled
  "AiRules": Integer,               // AI engine rules: 0=disabled, 1=enabled
  "RuleClass": Integer,             // Rule class mode
  "MaxSdl": Integer                 // Maximum SDL configuration value
}
```

**Run Mode Values**:
- `0` — Observe mode: IPS detects and logs threats but does NOT block them
- `1` — Block mode: IPS actively blocks detected threats

---

### DescribeSignatureLibVersion

**Description**: Query the IPS rule library version information, including the IPS rule library and threat intelligence library versions and their last update times.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| (none required) | — | — | No required parameters; only the global `--region` flag is needed |

**Key Response Fields**:

```
{
  "RequestId": String,              // Request ID
  "TotalCount": Integer,            // Total number of rule libraries
  "Version": [                      // Array of rule library versions (NOTE: this is an array, not an object)
    {
      "Type": String,               // Library type: "ips" (IPS rule library) or "intelligence" (threat intelligence library)
      "Version": String,            // Version identifier (e.g., "IPS-2603-01")
      "UpdateTime": Long            // Last update time (Unix timestamp in seconds)
    }
  ]
}
```
