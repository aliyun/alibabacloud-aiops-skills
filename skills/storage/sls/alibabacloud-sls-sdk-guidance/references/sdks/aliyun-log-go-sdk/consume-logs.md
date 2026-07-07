# Consume Logs — aliyun-log-go-sdk

## Overview

Use the Go SDK's **Consumer Library** for Consumer Group-based consumption. It automatically handles shard assignment, heartbeat, checkpoint persistence, and load balancing across multiple consumers.

- Docs: https://github.com/aliyun/aliyun-log-go-sdk/blob/master/consumer/README.md
- Runnable examples: https://github.com/aliyun/aliyun-log-go-sdk/tree/master/example/consumer
- Consumer Group concepts: [consumer-group-concepts](../../scenarios/consumer-group-concepts.md)

## Consumer Library Example

```go
package main

import (
    "fmt"
    "os"
    "os/signal"
    "syscall"

    sls "github.com/aliyun/aliyun-log-go-sdk"
    "github.com/aliyun/aliyun-log-go-sdk/consumer"
    "github.com/go-kit/kit/log/level"
)

func main() {
    option := consumer.LogHubConfig{
        Endpoint:          "cn-hangzhou.log.aliyuncs.com",
        AccessKeyID:       os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
        AccessKeySecret:   os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
        Project:           "your_project",
        Logstore:          "your_logstore",
        ConsumerGroupName: "my-consumer-group",
        ConsumerName:      "consumer-1",
        CursorPosition:    consumer.BEGIN_CURSOR,
    }

    consumerWorker := consumer.InitConsumerWorkerWithCheckpointTracker(option, process)

    ch := make(chan os.Signal, 1)
    signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
    consumerWorker.Start()
    if _, ok := <-ch; ok {
        level.Info(consumerWorker.Logger).Log("msg", "get stop signal, start to stop consumer worker", "consumer worker name", option.ConsumerName)
        // Recommended: stop gracefully on exit. StopAndWait triggers one final
        // checkpoint save to the server before returning.
        consumerWorker.StopAndWait()
    }
}

func process(shardId int, logGroupList *sls.LogGroupList, checkpointTracker consumer.CheckPointTracker) (string, error) {
    // Save the checkpoint after the batch is processed.
    //   false — save to local memory only (fast); a background task periodically
    //           flushes it to the server (force=true) on its own schedule.
    //   true  — send the checkpoint to the server immediately (slower).
    // false is recommended for most scenarios.
    defer checkpointTracker.SaveCheckPoint(false)

    for _, logGroup := range logGroupList.LogGroups {
        for _, log := range logGroup.Logs {
            for _, content := range log.Contents {
                fmt.Printf("%s: %s\n", *content.Key, *content.Value)
            }
        }
    }
    // Return "" to keep the current position; return a cursor to reset to it.
    return "", nil
}
```

## Notes

- The Consumer Library manages shard assignment, heartbeat, checkpoint, and load balancing automatically.
- Checkpoint: the background auto-commit periodically saves progress to the server, so `SaveCheckPoint(false)` in the callback is enough for most cases; use `true` only when you need an immediate server-side save.
- Graceful shutdown: always call `consumerWorker.StopAndWait()` on exit (e.g. on SIGINT/SIGTERM) — it flushes a final checkpoint so consumption resumes at the right position after restart.
- `CursorPosition` can be `BEGIN_CURSOR`, `END_CURSOR`, or a specific timestamp.
