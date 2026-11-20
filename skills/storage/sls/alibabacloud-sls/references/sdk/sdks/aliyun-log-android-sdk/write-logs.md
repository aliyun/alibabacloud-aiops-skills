# Write Logs — aliyun-log-android-sdk

## Overview

The Android SDK is a **Producer** — it buffers logs and sends them asynchronously in the background with auto-batching, LZ4 compression, automatic retry, and optional breakpoint resume (local binlog persistence for at-least-once delivery).

- Docs: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-android
- GitHub README: https://github.com/aliyun/aliyun-log-android-sdk/blob/master/README.md

## Basic Usage Example

```java
import com.aliyun.sls.android.producer.*;

// Keep config + client as long-lived singletons (one-to-one).
LogProducerConfig config = new LogProducerConfig(context, endpoint, project, logstore);
config.setAccessKeyId(System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"));
config.setAccessKeySecret(System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"));

// Batching knobs (defaults are usually fine)
config.setPacketLogBytes(1024 * 1024);  // max packet size
config.setPacketLogCount(1024);          // max logs per packet
config.setPacketTimeout(3000);           // flush timeout (ms)

// Optional: breakpoint resume — logs persist to a local binlog file;
// deleted only after confirmed upload (at-least-once delivery).
config.setPersistent(1);
config.setPersistentFilePath(context.getFilesDir() + "/sls_log");
config.setMaxBufferLimit(64 * 1024 * 1024);

LogProducerClient client = new LogProducerClient(config);

// Write a log
Log log = new Log();
log.putContent("level", "INFO");
log.putContent("message", "App launched");
LogProducerResult result = client.addLog(log);
// addLog(log, 1) — flush immediately instead of waiting for batch trigger
```

## Callback

```java
LogProducerClient client = new LogProducerClient(config, new LogProducerCallback() {
    @Override
    public void onCall(int resultCode, String reqId, String errorMessage,
                       int logBytes, int compressedBytes) {
        if (resultCode != LogProducerResult.LOG_PRODUCER_OK) {
            // handle send failure
        }
    }
});
```

## STS Token Auth

On mobile, prefer STS tokens over embedding a static AccessKey in the app:

```java
LogProducerConfig config = new LogProducerConfig(context, endpoint, project, logstore,
    accessKeyId, accessKeySecret, securityToken);
// Refresh before expiry:
config.resetSecurityToken(newAccessKeyId, newAccessKeySecret, newSecurityToken);
```

## Notes

- Initialize once (singleton) — duplicate initialization is the most common cause of duplicate logs.
- Logs are sent asynchronously to avoid blocking the UI thread.
- With `setPersistent(1)`, logs survive app restarts and network outages (at-least-once). Each config must have a unique `setPersistentFilePath`.
- Dynamic reconfiguration (endpoint/project/logstore) is supported since v2.6.0+.
- The underlying engine is the [C Producer SDK](../aliyun-log-c-sdk/index.md) (`persistent` branch).
