# Collector status: `logtail_status`

Use for heartbeat, collector version and resource-use evidence. The documented
Logtail reporting interval is one minute. A heartbeat shows that a collector
reported; it does not by itself establish successful collection or delivery.

| Field | Meaning |
| --- | --- |
| `project` | Project owning the collection configuration |
| `ip`, `hostname`, `instance_id`, `uuid`, `user_defined_id` | Collector/host identifiers; match the available identity |
| `version`, `os`, `os_detail` | Collector version and operating system |
| `cpu`, `memory` | Collector CPU load and process memory in MB |
| `os_cpu`, `load` | Host CPU use and system load |
| `detail_metric` | JSON object containing more collector metrics |

Useful `detail_metric` subfields include `config_count`, configuration fetch/
update timestamps, `last_read_event_time`, `last_send_time`, `reader_count`,
`process_lines_ps`, `send_lines_ps`, `send_net_bytes_ps`, `net_err_stat`,
`send_queue_full` and `sender_invalid`.

Example filter:

```text
__topic__: logtail_status and project: "example-project" and ip: "192.0.2.10"
```

Inspect the stored representation of `detail_metric` before extracting JSON
subfields; do not assume every subfield is independently indexed. Correlate a
missing heartbeat with host/process and machine-group evidence, and check
[collector contracts](../../loongcollector/sls-lens-contracts.md) for version-specific
diagnostics.

Source: [Service log types — Logtail status](https://help.aliyun.com/zh/sls/log-types).
