# alibabacloud-sls-go-sdk (OpenAPI)

## Summary

Alibaba Cloud OpenAPI SDK for SLS (Go). Auto-generated from API metadata — full, consistent API coverage for resource management (Project, Logstore, index, machine group, dashboard, alert, etc.) and log query. This is the newer OpenAPI evolution direction; for log writing and consumption, use the dedicated Go SDK.

- Package: `github.com/alibabacloud-go/sls-20201230/v6`
- Language / Platform: Go

## Repository

- GitHub: https://github.com/alibabacloud-go/sls-20201230

## Official Docs

- OpenAPI overview: https://help.aliyun.com/zh/sls/developer-reference/api-overview
- API list: https://next.api.aliyun.com/document/Sls/2020-12-30/overview
- Per-API doc: `https://next.api.aliyun.com/document/Sls/2020-12-30/<ApiName>` (e.g. `CreateProject`, `GetLogsV2`)
- Online debugging & sample code: `https://next.api.aliyun.com/api/Sls/2020-12-30/<ApiName>?sdkStyle=dara&tab=DEMO&lang=GO`

## Install

```bash
go get github.com/alibabacloud-go/sls-20201230/v6
go get github.com/aliyun/credentials-go/credentials
```

## Quick Start

```go
import (
    "fmt"
    "os"
    "time"

    openapi "github.com/alibabacloud-go/darabonba-openapi/v2/client"
    sls "github.com/alibabacloud-go/sls-20201230/v6/client"
    "github.com/alibabacloud-go/tea/tea"
    credential "github.com/aliyun/credentials-go/credentials"
)

credentialConfig := new(credential.Config).
    SetType("access_key").
    SetAccessKeyId(os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")).
    SetAccessKeySecret(os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"))
cred, _ := credential.NewCredential(credentialConfig)

config := &openapi.Config{Credential: cred}
config.Endpoint = tea.String("cn-hangzhou.log.aliyuncs.com")
client, _ := sls.NewClient(config)

now := int32(time.Now().Unix())
request := &sls.GetLogsV2Request{
    From:   tea.Int32(now - 3600),
    To:     tea.Int32(now),
    Query:  tea.String("*"),
    Line:   tea.Int64(100),
    Offset: tea.Int64(0),
}
resp, _ := client.GetLogsV2(tea.String("your_project"), tea.String("your_logstore"), request)
fmt.Println(resp.Body)
```

## Capability

| Capability | Ref |
| --- | --- |
| Query logs (`GetLogsV2`) | inline |
| Manage resources | inline |

## Notes

- For log writing (Producer) and consumption (Consumer Group), use [aliyun-log-go-sdk](../aliyun-log-go-sdk/index.md) — it includes API client, Producer Library, and Consumer Library in one module.
- Compared to `aliyun-log-go-sdk`, this OpenAPI SDK has broader resource-management API coverage and is the recommended path for new resource-management integrations.
