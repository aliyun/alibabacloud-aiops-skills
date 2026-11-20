# Consume Logs — aliyun-log-consumer-java

## Overview

Use the Java Consumer Library for Consumer Group-based consumption. It automatically handles shard assignment, heartbeat, checkpoint persistence, and load balancing across multiple consumers.

- Docs: https://help.aliyun.com/zh/sls/developer-reference/use-consumer-groups-to-consume-data
- Consumer Group concepts: [consumer-group-concepts](../../scenarios/consumer-group-concepts.md)

## Consumer Worker Example

```java
import com.aliyun.openservices.loghub.client.ClientWorker;
import com.aliyun.openservices.loghub.client.config.LogHubConfig;
import com.aliyun.openservices.loghub.client.interfaces.ILogHubProcessor;
import com.aliyun.openservices.loghub.client.interfaces.ILogHubProcessorFactory;
import com.aliyun.openservices.loghub.client.interfaces.ILogHubCheckPointTracker;
import com.aliyun.openservices.log.common.LogGroupData;

import java.util.List;

LogHubConfig config = new LogHubConfig(
    "my-consumer-group",
    "consumer-1",               // unique within the consumer group
    "cn-hangzhou.log.aliyuncs.com",
    "your_project", "your_logstore",
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
    LogHubConfig.ConsumePosition.BEGIN_CURSOR);

ClientWorker worker = new ClientWorker(new SampleProcessorFactory(), config);
Thread thread = new Thread(worker);
thread.start();

// Graceful shutdown — call worker.shutdown() on exit, then wait for async
// tasks to finish (the library recommends ~30s for safe cleanup).
Runtime.getRuntime().addShutdownHook(new Thread(() -> {
    worker.shutdown();
    try { Thread.sleep(30_000); } catch (InterruptedException ignored) {}
}));
```

## Processor Implementation

```java
class SampleProcessor implements ILogHubProcessor {
    private int shardId;

    @Override
    public void initialize(int shardId) {
        this.shardId = shardId;
    }

    @Override
    public String process(List<LogGroupData> logGroups, ILogHubCheckPointTracker tracker) {
        for (LogGroupData data : logGroups) {
            System.out.println("Shard " + shardId + ": " + data.GetAllLogs().size() + " logs");
        }

        // false — save to local memory (fast).
        // Framework auto-flushes local checkpoints to server every ~60s
        // (autoCommitEnabled=true, autoCommitIntervalMs=60000 by default).
        tracker.saveCheckPoint(false);
        return null;
    }

    @Override
    public void shutdown(ILogHubCheckPointTracker tracker) {
        // Final checkpoint save on shutdown — flush to server
        tracker.saveCheckPoint(true);
    }
}

class SampleProcessorFactory implements ILogHubProcessorFactory {
    @Override
    public ILogHubProcessor generatorProcessor() {
        // Return a new instance each time. Each processor handles one shard,
        // and shards are processed concurrently — sharing an instance requires
        // thread-safe fields.
        return new SampleProcessor();
    }
}
```

## Notes

- Checkpoint: `saveCheckPoint(false)` saves to local memory (fast); the framework calls `flushCheckpointIfNeeded()` after every `process()` and auto-flushes to the server every ~60s (`autoCommitEnabled=true`, `autoCommitIntervalMs=60000` by default). Use `true` only in `shutdown()` to guarantee the final checkpoint is persisted.
- On crash between auto-commits, the next consumer restarts from the last persisted checkpoint (at-least-once delivery; minor duplicate consumption possible within the 60s interval).
- `ConsumePosition.BEGIN_CURSOR` / `END_CURSOR` / `SPECIAL_TIMER_CURSOR` — the start position is **only effective on first consumer group creation**; subsequent restarts resume from the last saved checkpoint.
- `config.setQuery("* | where status = '500'")` enables optional server-side SPL filtering.
- Consumer names must be unique within a consumer group; use IP + PID or a persistent UUID.
- Call `worker.shutdown()` on exit, then allow ~30s for async cleanup before the process terminates.
