# Write Logs — aliyun-log-c-sdk

## Overview

The C Producer SDK writes logs to SLS asynchronously with auto-batching (by timeout / count / size), LZ4 compression, thread-pool sending, and configurable retry. Designed for embedded Linux and high-throughput servers.

- Docs: https://help.aliyun.com/zh/sls/developer-reference/log-service-sdk-for-c
- GitHub README: https://github.com/aliyun/aliyun-log-c-sdk/blob/master/README.md
- Sample: [`sample/log_producer_sample.c`](https://github.com/aliyun/aliyun-log-c-sdk/blob/master/sample/log_producer_sample.c)

## Build

```bash
git clone https://github.com/aliyun/aliyun-log-c-sdk.git
cd aliyun-log-c-sdk
cmake .
make
make install
```

> Custom curl path: `-DCURL_INCLUDE_DIR=... -DCURL_LIBRARY=...`. Pin a commit/tag for production.

## Producer Example

```c
#include "log_producer_config.h"
#include "log_producer_client.h"

int main() {
    log_producer_config *config = create_log_producer_config();
    log_producer_config_set_endpoint(config, "cn-hangzhou.log.aliyuncs.com");
    log_producer_config_set_project(config, "your_project");
    log_producer_config_set_logstore(config, "your_logstore");
    log_producer_config_set_access_id(config, getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"));
    log_producer_config_set_access_key(config, getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"));

    // Batching knobs
    log_producer_config_set_packet_log_bytes(config, 4 * 1024 * 1024);
    log_producer_config_set_packet_log_count(config, 4096);
    log_producer_config_set_packet_timeout(config, 3000);
    log_producer_config_set_send_thread_count(config, 4);

    log_producer *producer = create_log_producer(config, NULL);
    log_producer_client *client = get_log_producer_client(producer, NULL);

    // Write a log — variadic: key-count, key1, val1, key2, val2, ...
    log_producer_client_add_log(client, 2,
        "level", "INFO",
        "message", "Application started");

    // Cleanup — flushes any buffered logs before exit
    destroy_log_producer(producer);
    return 0;
}
```

## Notes

- The Producer handles batching, LZ4 compression, and retry automatically; each `add_log` call is non-blocking.
- `destroy_log_producer` flushes remaining buffered logs before shutdown. For reliable exit with persistent buffer see [`save_send_buffer.md`](https://github.com/aliyun/aliyun-log-c-sdk/blob/master/save_send_buffer.md) in the repo.
- Branch selection matters — see the [index](index.md) Notes section for the `master` / `live` / `bricks` / `persistent` matrix.
- Thread pool size (`send_thread_count`) defaults to 0; set ≥1 for multi-threaded send.
