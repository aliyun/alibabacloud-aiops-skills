# aliyun-log-log4j-appender

## Summary

Log4j 1.x Appender for Alibaba Cloud SLS. Sends an existing Log4j application's logs to a Logstore via configuration only — no code changes. For new work prefer Log4j2 or Logback and their appenders; this targets legacy Log4j 1.x apps.

- Package: `com.aliyun.openservices:aliyun-log-log4j-appender`
- Language / Platform: Java / Log4j 1.x

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-log4j-appender

## Official Docs

- Collect Log4j logs (Log4j2/Logback appender config; links to this repo for older Log4j): https://help.aliyun.com/zh/sls/collect-log4j-logs

## Install

### Maven

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>aliyun-log-log4j-appender</artifactId>
  <version>0.1.15</version>
</dependency>
```

> Check latest version: [Maven Central](https://central.sonatype.com/artifact/com.aliyun.openservices/aliyun-log-log4j-appender)

## Quick Start

```properties
log4j.rootLogger=WARN, loghub

log4j.appender.loghub=com.aliyun.openservices.log.log4j.LoghubAppender
log4j.appender.loghub.project=your_project
log4j.appender.loghub.logStore=your_logstore
log4j.appender.loghub.endpoint=cn-hangzhou.log.aliyuncs.com
log4j.appender.loghub.accessKeyId=${ALIBABA_CLOUD_ACCESS_KEY_ID}
log4j.appender.loghub.accessKeySecret=${ALIBABA_CLOUD_ACCESS_KEY_SECRET}
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Logging framework (appender) | [write-logs](write-logs.md) |

## Notes

- Legacy: Log4j 1.x is end-of-life. New apps should use [log4j2](../aliyun-log-log4j2-appender/index.md) or [logback](../aliyun-log-logback-appender/index.md).
