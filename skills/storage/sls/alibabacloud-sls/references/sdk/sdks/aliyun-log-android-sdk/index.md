# aliyun-log-android-sdk

## Summary

Android client-side log Producer for Alibaba Cloud SLS. Wraps the log-collection APIs so Android apps can batch, compress, cache, and upload logs asynchronously. Companion libraries add crash / block / network-quality / Trace collection.

- Package: `io.github.aliyun-sls:aliyun-log-android-sdk` (aar)
- Language / Platform: Android 4.0+ (API 14+), Java / Kotlin

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-android-sdk

## Official Docs

- Overview: https://help.aliyun.com/zh/sls/developer-reference/overview-of-log-service-sdk-for-android
- Install: https://help.aliyun.com/zh/sls/developer-reference/install-log-service-sdk-for-android
- Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-android

## Install

### Gradle (module `build.gradle`)

```groovy
implementation 'io.github.aliyun-sls:aliyun-log-android-sdk:2.7.13@aar'
```

> Check latest version: [Maven Central](https://central.sonatype.com/artifact/io.github.aliyun-sls/aliyun-log-android-sdk)

## Quick Start

```java
LogProducerConfig config = new LogProducerConfig(
    context, "cn-hangzhou.log.aliyuncs.com", "your_project", "your_logstore");
config.setAccessKeyId(System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"));
config.setAccessKeySecret(System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"));

LogProducerClient client = new LogProducerClient(config);
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Producer (high-perf, auto-batch + auto-retry) | [write-logs](write-logs.md) |

## Notes

- Auth on mobile: prefer STS tokens (`resetSecurityToken`) or the mobile log direct-transfer service; avoid shipping a static AccessKey in the app.
- Breakpoint resume (`setPersistent`) persists logs to a local binlog for at-least-once delivery; give each config a unique `setPersistentFilePath`.
- Initialize once (singleton); duplicate initialization is the most common cause of duplicate logs.
- Companion libraries (`sls-android-core`, `-crashreporter`, `-blockdetection`, `-network-diagnosis`, `-trace`) enable mobile APM / RUM — see the Overview doc.
