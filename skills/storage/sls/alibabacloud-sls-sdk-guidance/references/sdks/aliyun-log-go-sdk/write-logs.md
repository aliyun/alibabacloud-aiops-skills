# Write Logs — aliyun-log-go-sdk

## Overview

The **Producer Library** is the recommended way to write logs at scale. It buffers logs and **automatically batches** them into merged send requests, sends them **asynchronously on background worker threads** (your `SendLog` call returns immediately), and **automatically retries** failed requests with backoff — all under a bounded memory budget.

- Docs: https://github.com/aliyun/aliyun-log-go-sdk/blob/master/producer/README.md
- Runnable examples: https://github.com/aliyun/aliyun-log-go-sdk/tree/master/example/producer

## Producer Library Example

```go
package main

import (
    "os"
    "time"

    sls "github.com/aliyun/aliyun-log-go-sdk"
    "github.com/aliyun/aliyun-log-go-sdk/producer"
    "github.com/gogo/protobuf/proto"
)

func main() {
    project := "your_project"
    logstore := "your_logstore"

    config := producer.GetDefaultProducerConfig()
    config.Endpoint = "cn-hangzhou.log.aliyuncs.com"
    config.CredentialsProvider = sls.NewStaticCredentialsProvider(
        os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
        os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"), "")

    p, err := producer.NewProducer(config)
    if err != nil {
        panic(err)
    }
    p.Start() // launches background sender goroutines (async + auto-retry)

    // Call SafeClose when the producer is no longer needed / on shutdown.
    // It blocks until all buffered logs are flushed to the server, so logs
    // are not lost. (Use Close(seconds) for a bounded shutdown.)
    defer p.SafeClose()

    // Option A — GenerateLog helper: convenient, but proto-serializes each
    // field internally (lower efficiency). Fine for tests / low volume.
    log := producer.GenerateLog(uint32(time.Now().Unix()), map[string]string{
        "level":   "INFO",
        "message": "Application started",
    })
    p.SendLog(project, logstore, "topic", "source", log)

    // Option B — build the protobuf sls.Log directly: recommended for
    // high-throughput writes (avoids the GenerateLog serialization overhead).
    log2 := &sls.Log{
        Time: proto.Uint32(uint32(time.Now().Unix())),
        Contents: []*sls.LogContent{
            {Key: proto.String("level"), Value: proto.String("INFO")},
            {Key: proto.String("message"), Value: proto.String("hello")},
        },
    }
    p.SendLog(project, logstore, "topic", "source", log2)
}
```

`SendLog(project, logstore, topic, source, log)` only enqueues the log; delivery
happens asynchronously. To observe per-batch success/failure, use
`SendLogWithCallBack` with a `Callback` implementation (see the producer README).

## Basic Client Write

For simple one-off writes without the Producer, call `PutLogs` directly:

```go
client := &sls.Client{
    Endpoint:        "cn-hangzhou.log.aliyuncs.com",
    AccessKeyID:     os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    AccessKeySecret: os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
}

logs := &sls.LogGroup{
    Topic:  proto.String(""),
    Source: proto.String(""),
    Logs: []*sls.Log{
        {
            Time: proto.Uint32(uint32(time.Now().Unix())),
            Contents: []*sls.LogContent{
                {Key: proto.String("level"), Value: proto.String("INFO")},
                {Key: proto.String("message"), Value: proto.String("hello")},
            },
        },
    },
}
err := client.PutLogs(project, logstore, logs)
```

## Notes

- Producer = async batching + automatic retry + bounded memory; prefer it for any high-throughput service. `PutLogs` is synchronous and one request per call — use it only for occasional writes.
- Always `SafeClose()` (or `Close(seconds)`) before exit, otherwise buffered logs that haven't been flushed yet are lost.
- `topic` and `source` are batching dimensions — the producer groups logs by `(project, logstore, topic, source, shardHash)` before merging. `source` defaults to the local IP, which is usually fine. Avoid passing high-cardinality values (e.g. per-request ID); too many distinct combinations break batching and generate many small requests.
