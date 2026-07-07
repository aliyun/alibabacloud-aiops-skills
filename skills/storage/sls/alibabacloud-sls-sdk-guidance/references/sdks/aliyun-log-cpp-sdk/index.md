# aliyun-log-cpp-sdk

## Summary

C++ SDK for Alibaba Cloud SLS, **Linux only**. Wraps the SLS API via the `LOGClient` class: write logs (`PostLogStoreLogs`), read via cursor (`GetCursor` / `GetBatchLog`), manage Project/Logstore/machine groups, and call raw consumer-group primitives (heartbeat / checkpoint).

- Package: source build (no package manager)
- Language / Platform: C++11, Linux

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-cpp-sdk

## Official Docs

- Overview: https://help.aliyun.com/zh/sls/developer-reference/overview-of-log-service-sdk-for-cpp
- Install: https://help.aliyun.com/zh/sls/developer-reference/install-log-service-sdk-for-cpp
- Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-cpp

## Install

Install deps (`openssl`, `curl`, `protobuf 2.5.0`, `lz4`), then build the SDK and link against it. Compile produces `lib/libslssdk.a`, `lib/libsls_logs_pb.a`, `lib/liblz4.a`.

```bash
git clone https://github.com/aliyun/aliyun-log-cpp-sdk.git
cd aliyun-log-cpp-sdk && make
# link: g++ -o app app.o -O2 -L./lib/ -std=c++11 -lslssdk -llz4 -lcurl -lprotobuf
```

> `protobuf` and `protoc` versions must match (2.5.0). See the Install doc for full dependency steps. Pin a tag for production.

## Quick Start

```cpp
#include "client.h"
#include "common.h"
using namespace aliyun_log_sdk_v6;

LOGClient client("cn-hangzhou.log.aliyuncs.com",
                 getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
                 getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
                 LOG_REQUEST_TIMEOUT, "127.0.0.1", false);
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Basic / batch (`PostLogStoreLogs`) | inline |
| Manage resources (`LOGClient`) | inline |

## Notes

- Linux only; for embedded / RTOS lightweight collection use [aliyun-log-c-sdk](../aliyun-log-c-sdk/index.md).
