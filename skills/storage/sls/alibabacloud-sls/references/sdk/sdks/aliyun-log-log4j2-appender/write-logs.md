# Write Logs — aliyun-log-log4j2-appender

## Overview

Configure the Log4j2 Appender to send logs from an existing Log4j2 application directly to SLS — no code changes required. The appender internally uses the Java Producer for async batching and retry.

- Docs: https://help.aliyun.com/zh/sls/collect-log4j-logs
- GitHub README: https://github.com/aliyun/aliyun-log-log4j2-appender/blob/master/README.md
- Example: [`Log4j2AppenderExample.java`](https://github.com/aliyun/aliyun-log-log4j2-appender/blob/master/src/main/java/com/aliyun/openservices/log/log4j2/example/Log4j2AppenderExample.java)
- Sample config: [`log4j2-example.xml`](https://github.com/aliyun/aliyun-log-log4j2-appender/blob/master/src/main/resources/log4j2-example.xml)

## Configuration (log4j2.xml)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN">
  <Appenders>
    <Loghub name="Loghub"
            project="your_project"
            logStore="your_logstore"
            endpoint="cn-hangzhou.log.aliyuncs.com"
            accessKeyId="${env:ALIBABA_CLOUD_ACCESS_KEY_ID}"
            accessKeySecret="${env:ALIBABA_CLOUD_ACCESS_KEY_SECRET}"
            totalSizeInBytes="104857600"
            maxBlockMs="0"
            ioThreadCount="8"
            batchSizeThresholdInBytes="524288"
            batchCountThreshold="4096"
            lingerMs="2000"
            retries="10"
            baseRetryBackoffMs="100"
            maxRetryBackoffMs="50000"
            topic=""
            source=""
            timeFormat="yyyy-MM-dd'T'HH:mmZ"
            timeZone="UTC"
            ignoreExceptions="true">
      <PatternLayout pattern="%d %-5level [%thread] %logger{0}: %msg"/>
    </Loghub>
  </Appenders>
  <Loggers>
    <Root level="WARN">
      <AppenderRef ref="Loghub"/>
    </Root>
  </Loggers>
</Configuration>
```

## Usage

No code changes needed — logs written via the standard Log4j2 API are sent to SLS:

```java
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

Logger logger = LogManager.getLogger(MyClass.class);
logger.info("Application started");
```

## Log Fields

Each log record sent to SLS includes: `level`, `location`, `message`, `throwable` (if exception), `thread`, `time`, `log`, `__source__`, `__topic__`.

## Notes

- Set `maxBlockMs="0"` (recommended) to prevent the appender from blocking the logging thread when the buffer is full.
- `ignoreExceptions="true"` suppresses appender-internal errors; monitor via `StatusConsoleListener` during debugging.
- `timePrecision` supports `secs`, `ms`, or `ns` for sub-second timestamps.
- Do not hardcode AccessKey in production — use `${env:...}` lookups or a credential provider.
