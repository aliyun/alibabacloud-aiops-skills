# Write Logs

Recommend SDKs for writing / ingesting logs into Alibaba Cloud SLS.

## SDK Routing by Situation

| Situation | Recommended ref |
| --- | --- |
| Java high-throughput service | [aliyun-log-java-producer index](../sdks/aliyun-log-java-producer/index.md), then [write-logs](../sdks/aliyun-log-java-producer/write-logs.md) |
| Java general API usage | [aliyun-log-java-sdk index](../sdks/aliyun-log-java-sdk/index.md), then [write-logs](../sdks/aliyun-log-java-sdk/write-logs.md) |
| Java Log4j application | [aliyun-log-log4j-appender index](../sdks/aliyun-log-log4j-appender/index.md), then [write-logs](../sdks/aliyun-log-log4j-appender/write-logs.md) |
| Java Log4j2 application | [aliyun-log-log4j2-appender index](../sdks/aliyun-log-log4j2-appender/index.md), then [write-logs](../sdks/aliyun-log-log4j2-appender/write-logs.md) |
| Java Logback application | [aliyun-log-logback-appender index](../sdks/aliyun-log-logback-appender/index.md), then [write-logs](../sdks/aliyun-log-logback-appender/write-logs.md) |
| Go service | [aliyun-log-go-sdk index](../sdks/aliyun-log-go-sdk/index.md), then [write-logs](../sdks/aliyun-log-go-sdk/write-logs.md) |
| Python script or service | [aliyun-log-python-sdk index](../sdks/aliyun-log-python-sdk/index.md), then [write-logs](../sdks/aliyun-log-python-sdk/write-logs.md) |
| PHP application | [aliyun-log-php-sdk index](../sdks/aliyun-log-php-sdk/index.md) |
| Node.js application | [aliyun-log-nodejs-sdk index](../sdks/aliyun-log-nodejs-sdk/index.md) |
| .NET application | [aliyun-log-dotnetcore-sdk index](../sdks/aliyun-log-dotnetcore-sdk/index.md) |
| C++ application | [aliyun-log-cpp-sdk index](../sdks/aliyun-log-cpp-sdk/index.md) |
| Rust application | [aliyun-log-rust-sdk index](../sdks/aliyun-log-rust-sdk/index.md) |
| iOS app | [aliyun-log-ios-sdk index](../sdks/aliyun-log-ios-sdk/index.md), then [write-logs](../sdks/aliyun-log-ios-sdk/write-logs.md) |
| Android app | [aliyun-log-android-sdk index](../sdks/aliyun-log-android-sdk/index.md), then [write-logs](../sdks/aliyun-log-android-sdk/write-logs.md) |
| C / embedded Linux producer | [aliyun-log-c-sdk index](../sdks/aliyun-log-c-sdk/index.md), then [write-logs](../sdks/aliyun-log-c-sdk/write-logs.md) |

## Selection Guidance

- For Java high-throughput production services, prefer `aliyun-log-java-producer` over the basic Java SDK write API.
- For Java applications that already use a logging framework (Log4j, Log4j2, Logback), prefer the matching Appender to avoid code changes.
- For Go services, the `aliyun-log-go-sdk` includes a built-in Producer Library for efficient batched writes.
- For mobile apps (iOS / Android), use the dedicated mobile Producer SDKs.
- For embedded Linux or resource-constrained environments, use `aliyun-log-c-sdk`.
