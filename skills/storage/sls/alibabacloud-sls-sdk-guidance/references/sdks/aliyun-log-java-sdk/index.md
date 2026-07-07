# aliyun-log-java-sdk

## Summary

Java SDK for Alibaba Cloud SLS — a complete REST API wrapper over the `Client` class: Project / Logstore / Shard / index management, write (`PutLogs`), query (`GetLogs`, `GetHistograms`), cursor scan (`BatchGetLogs` / `PullLogs`). This is the general-purpose Java entry point; specialized write/consume paths have their own libraries.

- Package: `com.aliyun.openservices:aliyun-log`
- Language / Platform: Java (JRE 6.0+)

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-java-sdk

## Official Docs

- Overview: https://help.aliyun.com/zh/sls/developer-reference/overview-of-log-service-sdk-for-java
- Install: https://help.aliyun.com/zh/sls/developer-reference/install-log-service-sdk-for-java
- Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-java

## Install

### Maven

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>aliyun-log</artifactId>
  <version>0.6.126</version>
</dependency>
```

### Gradle

```groovy
implementation "com.aliyun.openservices:aliyun-log:0.6.126"
```

> Check latest version: [Maven Central](https://central.sonatype.com/artifact/com.aliyun.openservices/aliyun-log)

## Quick Start

```java
import com.aliyun.openservices.log.Client;

Client client = new Client("cn-hangzhou.log.aliyuncs.com",
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"));
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Producer (high-perf, auto-batch + auto-retry) | [aliyun-log-java-producer](../aliyun-log-java-producer/index.md) |
| Write — Logging framework (appender) | [log4j](../aliyun-log-log4j-appender/index.md) / [log4j2](../aliyun-log-log4j2-appender/index.md) / [logback](../aliyun-log-logback-appender/index.md) |
| Write — Basic / batch (`PutLogs`) | [write-logs](write-logs.md) |
| Consume logs | [aliyun-log-consumer-java](../aliyun-log-consumer-java/index.md) |
| Query logs (`GetLogs`) | [query-logs](query-logs.md) |
| Manage resources | inline |

## Notes

- Direct `PutLogs` is fine for low volume; for high-throughput application logging use [aliyun-log-java-producer](../aliyun-log-java-producer/index.md), or a logging-framework [appender](../../scenarios/write-logs.md) if the app already uses Log4j/Log4j2/Logback.
- Supports both permanent AccessKey and STS token authentication.
- If you encounter dependency conflicts (e.g. protobuf version mismatch), use the `jar-with-dependencies` classifier which bundles all transitive dependencies with relocated packages:

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>aliyun-log</artifactId>
  <version>0.6.126</version>
  <classifier>jar-with-dependencies</classifier>
</dependency>
```
