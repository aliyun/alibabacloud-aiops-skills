# Write Logs — aliyun-log-ios-sdk

## Overview

The iOS SDK is a **Producer** — it buffers logs and sends them asynchronously in the background with auto-batching, LZ4 compression, automatic retry, and optional offline caching (local binlog persistence for at-least-once delivery).

- Docs: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-ios
- GitHub README: https://github.com/aliyun/aliyun-log-ios-sdk/blob/master/README.md

## Swift Example

```swift
import AliyunLogProducer

let config = LogProducerConfig(
    endpoint: "cn-hangzhou.log.aliyuncs.com",
    project: "your_project",
    logstore: "your_logstore",
    accessKeyID: accessKeyID,
    accessKeySecret: accessKeySecret)

// Batching knobs (defaults are usually fine)
config.setPacketLogBytes(1024 * 1024)
config.setPacketLogCount(1024)
config.setPacketTimeout(3000)

// Optional: offline caching — at-least-once delivery
config.setPersistent(1)
config.setPersistentFilePath(NSHomeDirectory() + "/Documents/sls_log")
config.setMaxBufferLimit(64 * 1024 * 1024)

let client = LogProducerClient(logProducerConfig: config)

let log = Log()
log.putContent("level", value: "INFO")
log.putContent("message", value: "App launched")
client?.add(log)
// add(log, flush: 1) — flush immediately instead of waiting for batch trigger
```

## Objective-C Example

```objc
LogProducerConfig *config = [[LogProducerConfig alloc]
    initWithEndpoint:@"cn-hangzhou.log.aliyuncs.com"
    project:@"your_project"
    logstore:@"your_logstore"
    accessKeyID:accessKeyID
    accessKeySecret:accessKeySecret];

LogProducerClient *client = [[LogProducerClient alloc]
    initWithLogProducerConfig:config callback:nil];

Log *log = [Log log];
[log putContent:@"level" value:@"INFO"];
[log putContent:@"message" value:@"App launched"];
[client AddLog:log];
```

## STS Token Auth

On mobile, prefer STS tokens over embedding a static AccessKey in the app:

```swift
let config = LogProducerConfig(
    endpoint: endpoint, project: project, logstore: logstore,
    accessKeyID: id, accessKeySecret: secret, securityToken: token)
// Refresh before expiry:
config.resetSecurityToken(newID, accessKeySecret: newSecret, securityToken: newToken)
```

## Notes

- Initialize once (singleton) — keep `LogProducerConfig` + `LogProducerClient` as long-lived properties, paired one-to-one.
- Logs are sent asynchronously to avoid blocking the main thread.
- With `setPersistent(1)`, logs survive app restarts and network outages (at-least-once). Each config must have a unique `setPersistentFilePath`.
- The underlying engine is the [C Producer SDK](../aliyun-log-c-sdk/index.md) (`persistent` branch).
