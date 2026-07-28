# aliyun CLI Pitfalls

Common gotchas when calling `aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} cms describe-metric-list` and related APIs. Ordered by likelihood of hitting them.

## 1. `--dimensions` must be a stringified JSON array

Wrong:
```bash
--dimensions '{"instanceId":"xxx"}'        # ❌ missing outer []
--dimensions instanceId=xxx                # ❌ not key=value form
```

Right:
```bash
--dimensions '[{"instanceId":"rmq-cn-xxx"}]'                       # single resource
--dimensions '[{"instanceId":"a"},{"instanceId":"b"}]'             # batch
--dimensions '[{"instanceId":"a","groupId":"GID_x"}]'              # group dimension
--dimensions '[{"instanceId":"a","groupId":"GID_x","topic":"T_y"}]' # fine-grained
```

## 2. `userId` is not required

Although `describe-metric-meta-list` returns `userId` in the dimensions list, you **must not** pass it when calling `describe-metric-list`. The CLI infers `userId` from the current AccessKey automatically.

## 3. Namespace must be `acs_rocketmq`

Using `acs_rocketmq5` does not error out — it silently returns empty `Datapoints`. Always verify with this namespace name first.

## 4. `--period` is in seconds, not minutes

`--period 60` = 1-minute resolution; `--period 300` = 5-minute. Retention varies:
- `< 60s` → 7 days
- `= 60s` → 31 days
- `≥ 300s` → 91 days

This skill uses 60 by default.

## 5. Time format (⚠️ IMPORTANT: naive strings are interpreted per region timezone, NOT UTC!)

| Format | How CMS interprets | Recommended |
|--------|------------------|-------------|
| `'2026-06-02 15:20:00'` (no TZ) | **The region's timezone** (cn-hangzhou → Beijing Time) | Easy to misuse |
| `'2026-06-02T07:20:00Z'` (with Z) | UTC | ✅ Recommended |

**Trap**: Generating a UTC string with `date -u '+%Y-%m-%d %H:%M:%S'` (without `Z`) makes CMS interpret it as Beijing Time, shifting the query window by 8 hours and returning all zeros.

**Correct pattern** — always use ISO-8601 with `Z`:

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ'      # supported by both GNU date and BSD date
--start-time '2026-06-02T07:20:00Z' --end-time '2026-06-02T08:00:00Z'
```

## 6. Pagination

Responses with a non-empty `NextToken` indicate more data. Loop:

```bash
NEXT=""
while :; do
  RES=$(aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} cms describe-metric-list ... ${NEXT:+--next-token "$NEXT"})
  echo "$RES" | jq -r '.Datapoints | fromjson | .[]'
  NEXT=$(echo "$RES" | jq -r '.NextToken // empty')
  [ -z "$NEXT" ] && break
done
```

`--length` defaults to 1000. Increasing it reduces page count.

## 7. Account-wide 50 QPS cap

CMS `describe-metric-list` is shared at 50 QPS per AliCloud account. Batch inspection must serialize calls + sleep (this skill uses ~30 QPS ceiling). Throttling errors should be exponentially backed off ≤ 3 retries.

## 8. 4.x / 5.x instance ID prefixes differ

- 4.x: `MQ_INST_<uid>_BX...`
- 5.x: `rmq-cn-...`

Use these prefixes to auto-detect version and route to `aliyun ons` vs `aliyun rocketmq` management APIs.

## 9. `Datapoints` is a JSON string, parse twice

The CLI returns `Datapoints` as a string field, not an array, so:

```bash
aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} cms describe-metric-list ... | jq -r '.Datapoints | fromjson'
```

Each point includes: `timestamp` (ms epoch), one of `Sum` / `Maximum` / `Value` / `Average` (depending on the metric's `Statistics`), `instanceId`, plus the other dimensions.

## 10. Fine-grained (PerGidTopic) metrics need both groupId and topic

Omitting either yields empty results. Use:

```bash
--dimensions '[{"instanceId":"...","groupId":"GID_x","topic":"T_y"}]'
```

## 11. 5.0-only metrics return empty on 4.x instances

`InstanceSendApiCallTps`, `InstanceReceiveApiCallTps`, `InstanceSendTpsUtilization`, `InstanceReceiveTpsUtilization`, `InstanceInternetFlowoutBandwidth`, `InstanceStorageSize` produce empty `Datapoints` on 4.x — not an error. The renderer shows N/A and skips scoring.

## 12. Management API: `ons` vs `rocketmq` argument flavors

- 4.x: `aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} ons ons-group-list --instance-id xxx --region cn-x`,
        `aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} ons ons-topic-list --instance-id xxx --region cn-x`
- 5.x: `aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} rocketmq list-consumer-groups --instance-id xxx --region cn-x`,
        `aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} rocketmq list-topics --instance-id xxx --region cn-x`

Both flavors use kebab-case parameters (`--instance-id`, `--region`), but be aware some plugin commands reject `--region-id` and require plain `--region`. Always check `aliyun <product> <command> --help`.

## 13. 5.x `list-consumer-groups --page-size` upper bound is 100 (not 200)

Although the help text says `10~200`, the actual maximum is `100`. Setting 200 produces `InvalidpageSize`.

## 14. Ghost instances in CMS

CMS retains 31 days of datapoints for deleted instances. Querying without `--dimensions` may return instance IDs that fail `get-instance` with `Instance.NotFound`. The skill probes via `get-instance` / `ons-instance-base-info` before pulling metrics and skips ghosts automatically.
