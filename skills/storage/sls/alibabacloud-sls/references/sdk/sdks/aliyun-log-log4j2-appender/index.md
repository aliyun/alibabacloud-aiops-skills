# aliyun-log-log4j2-appender

## Summary

Log4j2 Appender for Alibaba Cloud SLS. Sends an existing Log4j2 application's logs straight to a Logstore via configuration only — no code changes. Internally uses the Java Producer, so writes are async, batched, and retried.

- Package: `com.aliyun.openservices:aliyun-log-log4j2-appender`
- Language / Platform: Java / Log4j2

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-log4j2-appender

## Official Docs

- Collect Log4j logs (Appender config): https://help.aliyun.com/zh/sls/collect-log4j-logs

## Install

### Maven

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>aliyun-log-log4j2-appender</artifactId>
  <version>0.1.15</version>
</dependency>
<dependency>
  <groupId>com.google.protobuf</groupId>
  <artifactId>protobuf-java</artifactId>
  <version>2.5.0</version>
</dependency>
```

> Check latest version: [Maven Central](https://central.sonatype.com/artifact/com.aliyun.openservices/aliyun-log-log4j2-appender)

## Quick Start

```xml
<Appenders>
  <Loghub name="Loghub"
          project="your_project"
          logStore="your_logstore"
          endpoint="cn-hangzhou.log.aliyuncs.com"
          accessKeyId="${env:ALIBABA_CLOUD_ACCESS_KEY_ID}"
          accessKeySecret="${env:ALIBABA_CLOUD_ACCESS_KEY_SECRET}"
          topic="your_topic">
    <PatternLayout pattern="%d %-5level [%thread] %logger{0}: %msg"/>
  </Loghub>
</Appenders>
<Loggers>
  <Root level="warn"><AppenderRef ref="Loghub"/></Root>
</Loggers>
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Logging framework (appender) | [write-logs](write-logs.md) |

## Notes

- Optional appender params (`totalSizeInBytes`, `ioThreadCount`, `batchSizeThresholdInBytes`, `batchCountThreshold`, `lingerMs`, `retries`) map directly to the underlying Producer's tuning knobs.
