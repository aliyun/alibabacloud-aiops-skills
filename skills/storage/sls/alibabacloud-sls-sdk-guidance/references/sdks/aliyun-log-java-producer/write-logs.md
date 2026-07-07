# Write Logs — aliyun-log-java-producer

## Overview

The **Java Producer Library** is the recommended way to write logs at scale in Java. It buffers logs and **automatically batches** them into merged send requests, sends them **asynchronously on background I/O threads**, and **automatically retries** on retriable exceptions — all under a bounded memory budget.

- Docs: https://help.aliyun.com/zh/sls/developer-reference/use-aliyun-log-java-producer-to-write-log-data-to-log-service
- Sample app: https://github.com/aliyun/aliyun-log-producer-sample

## Producer Example

```java
import com.aliyun.openservices.aliyun.log.producer.LogProducer;
import com.aliyun.openservices.aliyun.log.producer.ProducerConfig;
import com.aliyun.openservices.aliyun.log.producer.ProjectConfig;
import com.aliyun.openservices.log.common.LogItem;

ProducerConfig producerConfig = new ProducerConfig();
LogProducer producer = new LogProducer(producerConfig);

producer.putProjectConfig(new ProjectConfig(
    "your_project", "cn-hangzhou.log.aliyuncs.com",
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")));

LogItem item = new LogItem();
item.PushBack("level", "INFO");
item.PushBack("message", "User login successful");

// send is async — returns immediately, logs are batched and sent on background threads
producer.send("your_project", "your_logstore", "", "", item);

// Must call close() on shutdown — blocks until all buffered logs are flushed.
// Use close(timeoutMs) for a bounded shutdown; unflushed logs may be lost.
producer.close();
```

## Async with Callback

```java
producer.send("your_project", "your_logstore", "", "", item,
    new Callback() {
        @Override public void onCompletion(Result result) {
            if (result.isSuccessful()) {
                System.out.println("Sent OK");
            } else {
                System.err.println("Failed: " + result.getErrorCode() + " " + result.getErrorMessage());
            }
        }
    });
```

## Notes

- Thread-safe: multiple threads share one `LogProducer` instance — one per application is enough.
- Auto-batch + auto-retry + async send: `send()` returns immediately; the producer internally merges data and batches requests.
- `topic` and `source` are batching dimensions — the producer groups logs by `(project, logstore, topic, source, shardHash)` before merging. `source` defaults to the local IP, which is usually fine. Avoid passing high-cardinality values (e.g. per-request ID); too many distinct combinations break batching and generate many small requests.
- Key tuning knobs on `ProducerConfig`: `totalSizeInBytes`, `ioThreadCount`, `batchSizeThresholdInBytes` / `batchCountThreshold`, `lingerMs`, `retries`.
- Always call `producer.close()` before exit, or buffered logs are lost.
- For lower-throughput / one-off writes, use `Client.PutLogs` from [aliyun-log-java-sdk](../aliyun-log-java-sdk/write-logs.md) instead.
