# aliyun-log-consumer-java

## Summary

Java LogHub Consumer Library (Consumer Group) for Alibaba Cloud SLS. Handles shard assignment, load balancing across consumers, failover, heartbeat, and checkpoint so you only implement per-shard processing logic. Consumption latency is typically seconds.

- Package: `com.aliyun.openservices:loghub-client-lib`
- Language / Platform: Java

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-consumer-java
- Consumer Group concepts: [consumer-group-concepts](../../scenarios/consumer-group-concepts.md)

## Official Docs

- Consume via Consumer Group: https://help.aliyun.com/zh/sls/developer-reference/use-consumer-groups-to-consume-data
- Manage consumer groups (Java): https://help.aliyun.com/zh/sls/developer-reference/use-log-service-sdk-for-java-to-manage-consumer-groups

## Install

### Maven

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>loghub-client-lib</artifactId>
  <version>0.6.50</version>
</dependency>
<dependency>
  <groupId>com.google.protobuf</groupId>
  <artifactId>protobuf-java</artifactId>
  <version>2.5.0</version>
</dependency>
```

> Check latest version: [Maven Central](https://central.sonatype.com/artifact/com.aliyun.openservices/loghub-client-lib)

## Quick Start

```java
LogHubConfig config = new LogHubConfig(
    "consumerGroupX", "consumer_1",
    "cn-hangzhou.log.aliyuncs.com", "your_project", "your_logstore",
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
    LogHubConfig.ConsumePosition.BEGIN_CURSOR);

ClientWorker worker = new ClientWorker(new SampleLogHubProcessorFactory(), config);
new Thread(worker).start();
// worker.shutdown(); on exit
```

## Capability

| Capability | Ref |
| --- | --- |
| Consume logs | [consume-logs](consume-logs.md) |

## Notes

- The classic library requires `protobuf-java 2.5.0` alongside `loghub-client-lib`. The newer path bundles the consumer in `aliyun-log` (the Java SDK) and supports SPL consumption via `config.setQuery(...)`.
- Checkpoint auto-saves ~every 60s; call `saveCheckPoint(true)` for an immediate server-side save. A worker crash can cause minor duplicate consumption since the last checkpoint (at-least-once).
- Consumer names must be unique within a group; a Logstore allows at most 30 consumer groups.
- If you encounter dependency conflicts (e.g. protobuf version mismatch), use the `jar-with-dependencies` classifier:

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>loghub-client-lib</artifactId>
  <version>0.6.50</version>
  <classifier>jar-with-dependencies</classifier>
</dependency>
```
