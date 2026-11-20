# aliyun-log-go-sdk

## Summary

Go SDK for Alibaba Cloud SLS — one module covering the API client, the **Producer** library (async batching + retry), and the **Consumer** library (Consumer Group). Handles resource management, write (`PutLogs`), query (`GetLogs`), and shard-based consumption.

- Package: `github.com/aliyun/aliyun-log-go-sdk`
- Language / Platform: Go

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-go-sdk
- Producer: [README](https://github.com/aliyun/aliyun-log-go-sdk/blob/master/producer/README.md) · [examples](https://github.com/aliyun/aliyun-log-go-sdk/tree/master/example/producer)
- Consumer: [README](https://github.com/aliyun/aliyun-log-go-sdk/blob/master/consumer/README.md) · [examples](https://github.com/aliyun/aliyun-log-go-sdk/tree/master/example/consumer)

## Official Docs

- Overview: https://help.aliyun.com/zh/sls/developer-reference/overview-14
- Install: https://help.aliyun.com/zh/sls/developer-reference/install-log-service-sdk-for-go
- Init credentials: https://help.aliyun.com/zh/sls/developer-reference/initialize-the-log-service-go-sdk
- Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-go

## Install

```bash
go get -u github.com/aliyun/aliyun-log-go-sdk
```

## Quick Start

```go
import (
    "os"
    sls "github.com/aliyun/aliyun-log-go-sdk"
)

provider := sls.NewStaticCredentialsProvider(
    os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"), "")
client := sls.CreateNormalInterfaceV2("cn-hangzhou.log.aliyuncs.com", provider)
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Producer (`producer` package, auto-batch + auto-retry) | [write-logs](write-logs.md) |
| Write — Basic / batch (`PutLogs`) | [write-logs](write-logs.md) |
| Consume logs (`consumer` package, Consumer Group) | [consume-logs](consume-logs.md) |
| Query logs (`GetLogsV2`) | [query-logs](query-logs.md) |
| Manage resources | inline |

## Notes

- For Go services this is the default choice: one dependency gives you API + Producer + Consumer, so most stacks need nothing else.
