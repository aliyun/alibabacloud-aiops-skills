# Write Logs — aliyun-log-log4j-appender

## Overview

Configure the Log4j 1.x Appender to send logs from an existing Log4j application directly to SLS — no code changes required. The appender internally uses the Java Producer for async batching and retry.

- Docs: https://help.aliyun.com/zh/sls/collect-log4j-logs
- GitHub README: https://github.com/aliyun/aliyun-log-log4j-appender/blob/master/README.md
- Example: [`Log4jAppenderExample.java`](https://github.com/aliyun/aliyun-log-log4j-appender/blob/master/src/main/java/com/aliyun/openservices/log/log4j/example/Log4jAppenderExample.java)
- Sample config: [`log4j-example.properties`](https://github.com/aliyun/aliyun-log-log4j-appender/blob/master/src/main/resources/log4j-example.properties)

## Configuration (log4j.properties)

```properties
log4j.rootLogger=WARN, loghub

log4j.appender.loghub=com.aliyun.openservices.log.log4j.LoghubAppender

# Required
log4j.appender.loghub.project=your_project
log4j.appender.loghub.logStore=your_logstore
log4j.appender.loghub.endpoint=cn-hangzhou.log.aliyuncs.com
log4j.appender.loghub.accessKeyId=${ALIBABA_CLOUD_ACCESS_KEY_ID}
log4j.appender.loghub.accessKeySecret=${ALIBABA_CLOUD_ACCESS_KEY_SECRET}

# Optional
log4j.appender.loghub.topic=
log4j.appender.loghub.source=

# Producer tuning (optional, defaults shown)
log4j.appender.loghub.totalSizeInBytes=104857600
log4j.appender.loghub.maxBlockMs=0
log4j.appender.loghub.ioThreadCount=8
log4j.appender.loghub.batchSizeThresholdInBytes=524288
log4j.appender.loghub.batchCountThreshold=4096
log4j.appender.loghub.lingerMs=2000
log4j.appender.loghub.retries=10
log4j.appender.loghub.baseRetryBackoffMs=100
log4j.appender.loghub.maxRetryBackoffMs=50000
```

## Configuration (log4j.xml)

```xml
<appender name="loghub" class="com.aliyun.openservices.log.log4j.LoghubAppender">
  <param name="project" value="your_project" />
  <param name="logStore" value="your_logstore" />
  <param name="endpoint" value="cn-hangzhou.log.aliyuncs.com" />
  <param name="accessKeyId" value="${ALIBABA_CLOUD_ACCESS_KEY_ID}" />
  <param name="accessKeySecret" value="${ALIBABA_CLOUD_ACCESS_KEY_SECRET}" />
</appender>
```

## Usage

No code changes needed — logs written via the standard Log4j API are sent to SLS:

```java
import org.apache.log4j.Logger;

Logger logger = Logger.getLogger(MyClass.class);
logger.info("Application started");
```

## Log Fields

Each log record sent to SLS includes: `level`, `location`, `message`, `throwable` (if exception), `thread`, `time`, `log`, `__source__`, `__topic__`.

## Notes

- Set `maxBlockMs=0` (recommended) to prevent the appender from blocking the logging thread when the buffer is full.
- Do not hardcode AccessKey in production — use environment variables or a credential provider.
- Legacy: Log4j 1.x is end-of-life. For new projects, use [log4j2](../aliyun-log-log4j2-appender/write-logs.md) or [logback](../aliyun-log-logback-appender/write-logs.md).
