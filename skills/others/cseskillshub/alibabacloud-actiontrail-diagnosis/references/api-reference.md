# LookupEvents API Reference

## API Overview

- **API name**: LookupEvents
- **API version**: 2020-07-06
- **Product**: ActionTrail
- **Description**: Retrieve detailed historical events
- **Endpoint format**: `actiontrail.{RegionId}.aliyuncs.com`

> Note: Do not call this API too frequently. For near-real-time event search, create a trail that delivers events to SLS and use its real-time consumption feature.

## Authorization

| Action | Access Level | Resource Type |
|--------|--------------|---------------|
| actiontrail:LookupEvents | get | All resources * |

## Request Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| NextToken | string | No | Pagination token; used to request the next page (all other parameters must stay identical to the previous request) |
| MaxResults | string | No | Maximum number of results to return, range 1-50 (**always set to 50 is recommended**) |
| StartTime | string | No | Start time, ISO8601 UTC format: YYYY-MM-DDThh:mm:ssZ |
| EndTime | string | No | End time, ISO8601 UTC format: YYYY-MM-DDThh:mm:ssZ |
| Direction | string | No | Sort direction: FORWARD (ascending) / BACKWARD (descending, default) |
| LookupAttribute | array | No | Search conditions, at most 1-2 AttributeItem entries |
| LookupAttribute.N.Key | string | No | Search key |
| LookupAttribute.N.Value | string | No | Search value |

### Time Parameter Notes

- StartTime and EndTime must be both set or both omitted
- When omitted: StartTime defaults to 7 days before the current time, EndTime defaults to the current time
- Maximum query range: 90 days (default retention period of management events)
- The time format must be UTC; e.g. Beijing time 2024-01-15 10:00:00 corresponds to `2024-01-15T02:00:00Z`

## Response Parameters

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| StartTime | string | Start time of the retrieved events |
| EndTime | string | End time of the retrieved events |
| NextToken | string | Next-page token; absent when there are no more results |
| Events | array | Event list |

### Event Object Fields

| Field | Description |
|-------|-------------|
| eventId | Unique event ID |
| eventVersion | Event version |
| eventName | Event name (API operation name) |
| eventSource | Event source identifier |
| eventType | Event type (ConsoleOperation / ApiCall, etc.) |
| eventTime | Event occurrence time (UTC) |
| acsRegion | Region where the event occurred |
| serviceName | Cloud service name |
| sourceIpAddress | Source IP of the request |
| userIdentity | Identity information of the operator |
| userIdentity.type | Identity type (root-account / ram-user / assumed-role / system) |
| userIdentity.principalId | Principal ID |
| userIdentity.accountId | Primary account ID |
| userIdentity.userName | User name |
| userIdentity.accessKeyId | AccessKey ID used |
| userIdentity.sessionContext | Role session information |
| requestParameters | Request parameters (JSON) |
| responseElements | Response content (JSON) |
| referencedResources | List of related resources |
| referencedResources.resourceType | Resource type |
| referencedResources.resourceName | Resource name / ID |
| additionalEventData | Additional data |
| additionalEventData.loginAccount | Login account |
| additionalEventData.mfaChecked | Whether MFA verification passed |
| errorCode | Error code (empty on success) |
| errorMessage | Error message |
| eventRW | Read/write type (Read / Write) |
| userAgent | User-Agent of the caller |

## Pagination Logic

```
1. First request: set the query conditions + MaxResults=50
2. Check the returned NextToken:
   - Present -> request the next page with the same parameters + NextToken
   - Absent  -> query finished
3. Merge the Events arrays from all pages
```

**Important**: All parameters of a pagination request (StartTime, EndTime, LookupAttribute, etc.) must be exactly identical to the first request.

## Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | IncompleteSignature | Signature mismatch |
| 400 | InvalidParameterCombination | End time must be later than start time |
| 400 | InvalidQueryParameter | Invalid query parameter |
| 400 | InvalidParameterEndTime | Invalid EndTime |
| 400 | InvalidParameterStartTime | Invalid StartTime |
| 403 | RAM authorization error (the `.RAM`-suffixed permission-denied code) | Insufficient RAM permission — grant `actiontrail:LookupEvents` |
| 429 | Throttling | Request rate limit exceeded |

## Debug URL

https://api.aliyun.com/api/Actiontrail/2020-07-06/LookupEvents
