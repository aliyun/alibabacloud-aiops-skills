# Consume Logs

Recommend SDKs for consuming / reading logs from Alibaba Cloud SLS.

## SDK Routing by Situation

| Situation | Recommended ref |
| --- | --- |
| Java Consumer Group processing | [aliyun-log-consumer-java index](../sdks/aliyun-log-consumer-java/index.md), then [consume-logs](../sdks/aliyun-log-consumer-java/consume-logs.md) |
| Go Consumer Library | [aliyun-log-go-sdk index](../sdks/aliyun-log-go-sdk/index.md), then [consume-logs](../sdks/aliyun-log-go-sdk/consume-logs.md) |
| Python consumption or processing job | [aliyun-log-python-sdk index](../sdks/aliyun-log-python-sdk/index.md), then [consume-logs](../sdks/aliyun-log-python-sdk/consume-logs.md) |

## How Consumer Groups Work

See [consumer-group-concepts](consumer-group-concepts.md) for the underlying model: shard assignment, heartbeat, checkpoint, consumer naming, start position, and ordering.

## Selection Guidance

- For Java Consumer Group (multi-consumer, shard assignment, checkpoint, load balancing), prefer `aliyun-log-consumer-java`.
- For Go services, the `aliyun-log-go-sdk` includes a built-in Consumer Library with Consumer Group support.
- For Python data processing jobs or scripts, use `aliyun-log-python-sdk` which supports consumer group usage.
