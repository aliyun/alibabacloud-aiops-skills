# Write Logs — aliyun-log-java-sdk

## Overview

Use the Java SDK's `Client.PutLogs` for direct, synchronous batch writes. Each call sends one `PutLogsRequest` containing a list of `LogItem`s. For high-throughput production services, prefer [aliyun-log-java-producer](../aliyun-log-java-producer/write-logs.md) (async batching + auto-retry).

- Official Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-java

## Basic Write Example

```java
import com.aliyun.openservices.log.Client;
import com.aliyun.openservices.log.common.LogItem;
import com.aliyun.openservices.log.request.PutLogsRequest;

Client client = new Client(
    "cn-hangzhou.log.aliyuncs.com",
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"));

List<LogItem> logGroup = new ArrayList<>();
LogItem item = new LogItem();
item.PushBack("level", "INFO");
item.PushBack("message", "Application started");
logGroup.add(item);

PutLogsRequest request = new PutLogsRequest("your_project", "your_logstore", "", "", logGroup);
client.PutLogs(request);
```

## Notes

- `PutLogs` is synchronous — one HTTP request per call. For bulk writes, accumulate multiple `LogItem`s in a single request.
- `topic` and `source` parameters in `PutLogsRequest` help organize and filter logs in queries.
- For STS token authentication, use the `Client` constructor overload that accepts a security token.
- For high-throughput async writes with batching, retry, and bounded memory, use the [Java Producer Library](../aliyun-log-java-producer/write-logs.md).
