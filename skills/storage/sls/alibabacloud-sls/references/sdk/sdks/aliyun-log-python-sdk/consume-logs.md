# Consume Logs — aliyun-log-python-sdk

## Overview

Use `ConsumerWorker` with a `ConsumerProcessorBase` subclass for automatic shard assignment, heartbeat, checkpoint, and load balancing.

- Docs: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-python
- API reference: http://aliyun-log-python-sdk.readthedocs.io/api.html
- Consumer Group concepts: [consumer-group-concepts](../../scenarios/consumer-group-concepts.md)

## Consumer Group Example

```python
import os
from aliyun.log.consumer import *

class MyProcessor(ConsumerProcessorBase):
    def initialize(self, shard):
        self.shard = shard

    def process(self, log_groups, check_point_tracker):
        for log_group in log_groups.LogGroups:
            for log in log_group.Logs:
                print(dict([(c.Key, c.Value) for c in log.Contents]))
        # False — save to local memory (fast).
        # Framework auto-flushes local checkpoints to server every ~60s.
        check_point_tracker.save_check_point(False)
        return None

    def shutdown(self, check_point_tracker):
        # True — flush to server immediately on shutdown, prevent re-consumption.
        check_point_tracker.save_check_point(True)

option = LogHubConfig(
    os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
    os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
    "cn-hangzhou.log.aliyuncs.com",
    "your_project", "your_logstore",
    "my-consumer-group", "consumer-1",
    cursor_position=CursorPosition.BEGIN_CURSOR)

worker = ConsumerWorker(MyProcessor, option)
worker.start()

# Graceful shutdown on signal:
# worker.shutdown()
```

## Notes

- Checkpoint: `save_check_point(False)` saves locally (fast); the framework calls `flush_check()` after every `process()` and auto-flushes to the server every ~60s (`default_flush_check_point_interval`). Use `True` only in `shutdown()` to guarantee the final checkpoint is persisted.
- `CursorPosition.BEGIN_CURSOR` / `END_CURSOR` — the start position is only effective when the consumer group is first created.
