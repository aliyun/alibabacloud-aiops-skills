# aliyun-log-java-producer

## Summary

High-performance Java Producer for Alibaba Cloud SLS. Thread-safe, async non-blocking `send` with in-memory batching, automatic retry, bounded resource usage, and ordered writes. Built for big-data / high-concurrency ingestion (Flink, Spark, Storm) where raw API/SDK writes can't keep up.

- Package: `com.aliyun.openservices:aliyun-log-producer`
- Language / Platform: Java

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-java-producer — [README](https://github.com/aliyun/aliyun-log-java-producer/blob/master/README.md)
- Sample app: https://github.com/aliyun/aliyun-log-producer-sample

## Official Docs

- Guide: https://help.aliyun.com/zh/sls/developer-reference/use-aliyun-log-java-producer-to-write-log-data-to-log-service

## Install

### Maven

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>aliyun-log-producer</artifactId>
  <version>0.3.25</version>
</dependency>
```

> Check latest version: [Maven Central](https://central.sonatype.com/artifact/com.aliyun.openservices/aliyun-log-producer)

## Quick Start

```java
Producer producer = new LogProducer(new ProducerConfig());
producer.putProjectConfig(new ProjectConfig(
    "your_project", "cn-hangzhou.log.aliyuncs.com",
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")));

LogItem item = new LogItem();
item.PushBack("status", "200");
producer.send("your_project", "your_logstore", item);

producer.close(); // flush buffered logs before exit
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Producer (high-perf, auto-batch + auto-retry) | [write-logs](write-logs.md) |

## Notes

- Must call `producer.close()` before the process exits, or buffered logs are lost (send is async on background threads).
- Key tuning knobs on `ProducerConfig`: `totalSizeInBytes`, `ioThreadCount`, `batchSizeThresholdInBytes`/`batchCountThreshold`, `lingerMs`, `retries`.
- If you encounter dependency conflicts (e.g. protobuf version mismatch), use the `jar-with-dependencies` classifier:

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>aliyun-log-producer</artifactId>
  <version>0.3.25</version>
  <classifier>jar-with-dependencies</classifier>
</dependency>
```
