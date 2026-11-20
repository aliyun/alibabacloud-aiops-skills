# aliyun-log-logback-appender

## Summary

Logback Appender for Alibaba Cloud SLS. Sends an existing Logback application's logs to a Logstore via configuration only — no code changes. Most common of the three appenders since Logback is the Spring Boot default. Internally uses the Java Producer (async, batched, retried).

- Package: `com.aliyun.openservices:aliyun-log-logback-appender`
- Language / Platform: Java / Logback

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-logback-appender

## Install

### Maven

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>aliyun-log-logback-appender</artifactId>
  <version>0.1.29</version>
</dependency>
```

> Check latest version: [Maven Central](https://central.sonatype.com/artifact/com.aliyun.openservices/aliyun-log-logback-appender)

## Quick Start

```xml
<appender name="loghub" class="com.aliyun.openservices.log.logback.LoghubAppender">
  <endpoint>cn-hangzhou.log.aliyuncs.com</endpoint>
  <project>your_project</project>
  <logStore>your_logstore</logStore>
  <accessKeyId>${ALIBABA_CLOUD_ACCESS_KEY_ID}</accessKeyId>
  <accessKeySecret>${ALIBABA_CLOUD_ACCESS_KEY_SECRET}</accessKeySecret>
  <topic>your_topic</topic>
</appender>
<root level="INFO">
  <appender-ref ref="loghub"/>
</root>
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Logging framework (appender) | [write-logs](write-logs.md) |

## Notes

- If you encounter dependency conflicts (e.g. protobuf version mismatch), use the `jar-with-dependencies` classifier:

```xml
<dependency>
  <groupId>com.aliyun.openservices</groupId>
  <artifactId>aliyun-log-logback-appender</artifactId>
  <version>0.1.29</version>
  <classifier>jar-with-dependencies</classifier>
</dependency>
```
