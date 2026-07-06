# groupbyattrs processor

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/groupbyattrsprocessor/README.md
>
> Re-groups records under Resources matching the named attribute values, so records with the same values share one Resource. Beta for traces, metrics, logs.

## Config

Single field `keys`:

```yaml
processors:
  groupbyattrs:
    keys:
      - foo
      - bar
```

## Behavior

- A record carrying any listed key is moved to a Resource that has matching values for those keys (a new Resource is created if none exists).
- New Resources inherit the original Resource's attributes plus the promoted keys.
- The promoted attributes are **removed** from the individual records (they live on the Resource now).
- Records with none of the keys keep their original Resource — duplicate Resources still get compacted.
- Records also merge under matching InstrumentationLibrary.
- Datapoints from identical metrics merge; metrics with different DataTypes (GAUGE vs SUM) stay separate.

## Compaction-only mode

Empty `keys` list = compact duplicate ResourceLogs/ResourceSpans/ResourceMetrics that share resource + scope attributes. Useful after fragmentation (e.g., from `groupbytrace` or many small ingest requests).

```yaml
processors:
  groupbyattrs:
```

## Recommended pairing

Often followed by `batch` to further reduce export fragmentation.

## Internal metrics

Per signal: `num_grouped_*`, `num_non_grouped_*`, `*_groups`.

## Typical use case for ES exporter

Promote `tenant_id` from each log record into the Resource so ES exporter's data-stream routing (`data_stream.dataset` etc.) and `groupbyattrs`-aware exporters can batch per tenant cleanly:

```yaml
processors:
  groupbyattrs:
    keys: [tenant_id]
  batch:
    send_batch_size: 1024
    timeout: 5s
```
