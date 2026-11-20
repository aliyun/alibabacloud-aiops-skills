# aliyun-log-c-sdk

## Summary

Pure-C log Producer for Alibaba Cloud SLS. Minimal dependencies and low resource usage for embedded / smart devices and high-throughput Linux servers. Async, aggregates by timeout/count/size, lz4 compression, thread-pool sending, context query; data is sent directly over the network (no disk spooling on the default branch).

- Package: source build (no package manager)
- Language / Platform: C, embedded Linux / servers (Windows / macOS / mobile via the `live` branch)

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-c-sdk

## Official Docs

- Guide: https://help.aliyun.com/zh/sls/developer-reference/log-service-sdk-for-c

## Install

```bash
git clone https://github.com/aliyun/aliyun-log-c-sdk.git
```

> Build steps depend on the branch/platform — follow the repo's build docs. Pin a specific commit or tag for production rather than tracking `master`.

## Quick Start

```c
#include "log_producer_config.h"
#include "log_producer_client.h"

log_producer_config *config = create_log_producer_config();
log_producer_config_set_endpoint(config, "cn-hangzhou.log.aliyuncs.com");
log_producer_config_set_project(config, "your_project");
log_producer_config_set_logstore(config, "your_logstore");
log_producer_config_set_access_id(config, getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"));
log_producer_config_set_access_key(config, getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"));

log_producer *producer = create_log_producer(config, NULL);
log_producer_client *client = get_log_producer_client(producer, NULL);
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Producer (high-perf, auto-batch + auto-retry) | [write-logs](write-logs.md) |

## Notes

- Branch selection (non-obvious, pick before building):
  - `master` — strongest performance; Linux servers / embedded Linux (recommended default).
  - `live` — same features as master plus broadest platform support (Windows, macOS, Android, iOS).
  - `bricks` — extreme-minimal (<10 KB footprint), very limited features; for RTOS / tightly constrained devices.
  - `persistent` — adds local cache (single-thread send); used by the Android/iOS native layer — prefer the official mobile SDKs instead.
