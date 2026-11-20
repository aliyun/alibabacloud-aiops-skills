# Detailed operation logs

`internal-operation_log` records detailed SLS resource operations and data
reads/writes for the source Project. Use it to investigate who made a request,
what resource/API was involved, and the request's result and latency. It covers
console and client/SDK requests, excluding JDBC access.

## Locate and enable

Read [service logs](service-logs.md) for activation, shutdown and destination
discovery. Use the source Project's `logging get` response: the destination is
`loggingProject`, and the `operation_log` entry gives the Store. A shared
destination can contain multiple source Projects.

The Store remains a managed built-in resource: do not directly change its
configuration or indexes or delete it. Use the service-log module's supported
operations; see [managed Store safety rules](entry.md#safety-rules-for-managed-built-in-stores).

## Request evidence

| Fields | Use |
| --- | --- |
| `Project`, `LogStore`, `Method` | Source resource and API operation; `Project` uses a capital P |
| `RequestId`, `Status` | Correlate a request and inspect its response status |
| `CallerType`, `InvokerUid`, `SourceIP`, `UserAgent` | Caller type/account, origin and client |
| `Latency` | Request latency in **microseconds** |
| `NetOutFlow`, `NetworkOut` | Read bytes and the subset read through the public endpoint |

Do not confuse operation-log `Status` with an alert execution or task state.
Read only the identity fields needed for the investigation and follow the
[credential safety rules](../../SKILL.md#safety-rules).

## Read, write and resource operations

| Operation class | Additional evidence |
| --- | --- |
| Reads such as `GetLogs`, `PullLogs` and `GetHistograms` | `Query`, `BeginTime`, `EndTime`, `DataStatus`, `RequestLines`, `ResponseLines`, `Offset`, `Reverse` |
| Writes such as `PostLogStoreLogs` and `PutWebTracking` | `InFlow` (original bytes), `NetInflow` (compressed bytes), `InputLines`, `Shard` |
| Resource operations such as `CreateProject` or `DeleteProject` | Use `Method`, source resource, caller, time and request outcome to reconstruct changes |

Preserve exact field spelling; byte counters use different capitalization.
Interpret request/query windows according to the API rather than substituting
them for the log event timestamp. A successful read request can still have a
data-completeness status that needs separate interpretation.

Example source-Project filter in the discovered operation Store:

```text
Project: "example-project" and Method: "GetLogs"
```

Read [query and analysis](../query/entry.md) for indexes, time bounds and result
completeness. `operation_log` is a collection configuration type; do not assume
it must be used as a stored `__topic__` filter. Source:
[Service log types — detailed logs](https://help.aliyun.com/zh/sls/log-types).
