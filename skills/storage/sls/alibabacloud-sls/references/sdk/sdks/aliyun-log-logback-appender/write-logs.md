# Write Logs — aliyun-log-logback-appender

## Overview

Configure the Logback Appender to send logs from an existing Logback / Spring Boot application directly to SLS — no code changes required. The appender internally uses the Java Producer for async batching and retry.

- Docs: https://help.aliyun.com/zh/sls/collect-log4j-logs
- GitHub README: https://github.com/aliyun/aliyun-log-logback-appender/blob/master/README.md
- Example: [`LogbackAppenderExample.java`](https://github.com/aliyun/aliyun-log-logback-appender/blob/master/src/main/java/com/aliyun/openservices/log/logback/example/LogbackAppenderExample.java)
- Sample config: [`logback-example.xml`](https://github.com/aliyun/aliyun-log-logback-appender/blob/master/src/main/resources/logback-example.xml)

## Configuration (logback.xml)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <!-- Important: prevents data loss on process exit -->
  <shutdownHook class="ch.qos.logback.core.hook.DelayingShutdownHook"/>

  <appender name="loghub" class="com.aliyun.openservices.log.logback.LoghubAppender">
    <!-- Required -->
    <endpoint>cn-hangzhou.log.aliyuncs.com</endpoint>
    <project>your_project</project>
    <logStore>your_logstore</logStore>
    <accessKeyId>${ALIBABA_CLOUD_ACCESS_KEY_ID}</accessKeyId>
    <accessKeySecret>${ALIBABA_CLOUD_ACCESS_KEY_SECRET}</accessKeySecret>

    <!-- Optional -->
    <topic></topic>
    <source></source>

    <!-- Producer tuning (optional, defaults shown) -->
    <totalSizeInBytes>104857600</totalSizeInBytes>
    <maxBlockMs>0</maxBlockMs>
    <ioThreadCount>8</ioThreadCount>
    <batchSizeThresholdInBytes>524288</batchSizeThresholdInBytes>
    <batchCountThreshold>4096</batchCountThreshold>
    <lingerMs>2000</lingerMs>
    <retries>10</retries>
    <baseRetryBackoffMs>100</baseRetryBackoffMs>
    <maxRetryBackoffMs>50000</maxRetryBackoffMs>

    <encoder>
      <pattern>%d %-5level [%thread] %logger{0}: %msg</pattern>
    </encoder>
    <timeFormat>yyyy-MM-dd'T'HH:mmZ</timeFormat>
    <timeZone>UTC</timeZone>
  </appender>

  <root level="INFO">
    <appender-ref ref="loghub" />
  </root>
</configuration>
```

## Usage

No code changes needed — logs written via the standard SLF4J / Logback API are sent to SLS:

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

Logger logger = LoggerFactory.getLogger(MyClass.class);
logger.info("Application started");
```

## Spring Boot Integration

Logback is the default logging framework in Spring Boot. Add the dependency and include the SLS appender in `logback-spring.xml`:

```xml
<springProfile name="production">
  <root level="INFO">
    <appender-ref ref="loghub" />
  </root>
</springProfile>
```

## Log Fields

Each log record sent to SLS includes: `level`, `location`, `message`, `throwable` (if exception), `thread`, `time`, `log` (if encoder configured), `__source__`, `__topic__`.

## Advanced Config

| Parameter | Default | Notes |
| --- | --- | --- |
| `mdcFields` | — | MDC capture: `*` (all), `KEY1,KEY2` (specific), `KEY1=alias` (rename) |
| `includeLocation` | `true` | Set `false` for performance-sensitive workloads |
| `maxThrowable` | `500` | Max exception stack trace length |
| `timePrecision` | `s` | `s` (seconds) or `ms` (milliseconds) |

Custom `CredentialsProvider`: implement `CredentialsProvider` + `CredentialsProviderBuilder` and configure via `<credentialsProviderBuilder>` in XML — see the [GitHub README](https://github.com/aliyun/aliyun-log-logback-appender/blob/master/README.md).

## Notes

- **Add `DelayingShutdownHook`** — without it, buffered logs may be lost on process exit.
- Set `maxBlockMs=0` (recommended) to prevent the appender from blocking the logging thread.
- Do not hardcode AccessKey in production — use environment variables or a custom `CredentialsProvider`.
