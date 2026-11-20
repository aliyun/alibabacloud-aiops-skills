# Collection statistics: `logtail_profile`

Use to diagnose file reading, parsing and sending progress in the documented
Logtail profile schema. Its reporting interval is ten minutes. Records describe
either one file or a Logstore summary.

| Field | Meaning |
| --- | --- |
| `project`, `LogStore`, `source_ip` | Source resource and collector |
| `config_name` | Full configuration identity, such as `##1.0##project-name$config-name` |
| `file_name` | File path, or `logstore_statistics` for a Logstore summary |
| `file_size`, `read_offset`, `last_read_time` | File size/position in bytes and last read timestamp |
| `succeed_lines`, `parse_failures`, `regex_match_failures`, `time_format_failures` | Successful and failed parsing/processing counts |
| `total_bytes`, `send_failures` | Bytes read and sending-failure count |

For `file_name: logstore_statistics`, sending-specific fields include
`send_network_error`, `send_quota_error`, `send_discard_error`,
`send_queue_size`, `send_block_flag` and `sender_valid_flag`. File device/inode
fields do not carry useful file identity for summary records.

Example filter:

```text
__topic__: logtail_profile and project: "example-project" and LogStore: "example-logstore"
```

Separate file records from summary records before aggregation to avoid counting
the same activity twice. Do not equate `read_avg_delay` with seconds: the
documented field describes a file-position gap. Collector major versions use
different pipeline telemetry; check [version routing](../../loongcollector/sls-lens-contracts.md)
before choosing this topic for a modern LoongCollector investigation.

Source: [Service log types — Logtail collection logs](https://help.aliyun.com/zh/sls/log-types).
