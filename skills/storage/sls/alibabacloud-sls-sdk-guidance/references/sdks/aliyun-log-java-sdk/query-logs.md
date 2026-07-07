# Query Logs — aliyun-log-java-sdk

## Overview

Use `Client.GetLogs` to run an index query over a time range — plain keyword/field search, or search plus SQL analysis (`... | select ...`).

## Docs

- Query syntax: https://help.aliyun.com/zh/sls/query-and-analyze-logs-in-index-mode
- Paged query: https://help.aliyun.com/zh/sls/paged-query
- Official Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-java

## Example

```java
import com.aliyun.openservices.log.Client;
import com.aliyun.openservices.log.request.GetLogsRequest;
import com.aliyun.openservices.log.response.GetLogsResponse;

Client client = new Client(
    "cn-hangzhou.log.aliyuncs.com",
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"));

int to = (int)(System.currentTimeMillis() / 1000);
int from = to - 3600;

GetLogsRequest request = new GetLogsRequest(
    "your_project", "your_logstore", from, to, "", "level: ERROR | select count(*) as cnt");
GetLogsResponse response = client.GetLogs(request);

System.out.println("Count: " + response.GetCount());
for (var log : response.GetLogs()) {
    System.out.println(log.GetLogItem().ToJsonString());
}
```

## Paged Query

A single `GetLogs` request returns at most `line` rows (default/max 100). For a plain **search** query,
page through results by advancing `offset`:

```java
int offset = 0;
int line = 100;
while (true) {
    GetLogsRequest req = new GetLogsRequest(
        "your_project", "your_logstore", from, to, "", "level: ERROR", line, offset, false);
    GetLogsResponse resp = client.GetLogs(req);
    for (var log : resp.GetLogs()) {
        System.out.println(log.GetLogItem().ToJsonString());
    }
    if (resp.GetCount() < line) {
        break; // last page
    }
    offset += line;
}
```

> `offset` / `line` paging applies to **search** queries. For **SQL analysis**
> queries, page inside the SQL with `LIMIT offset, count` — see the paged-query
> doc above.

## Notes

- `GetLogs` returns matches within `[from, to)` in Unix seconds.
- The `topic` parameter (5th arg) is typically `""` unless the Logstore uses topic-based partitioning.
- For `GetHistograms` (count distribution over time buckets without full log content), use `Client.GetHistograms`.
