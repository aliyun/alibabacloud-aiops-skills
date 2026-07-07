# alibabacloud-sls-dotnet-sdk (OpenAPI)

## Summary

Alibaba Cloud OpenAPI SDK for SLS (.NET). Auto-generated from API metadata — full, consistent API coverage for resource management (Project, Logstore, index, machine group, dashboard, alert, etc.) and log query. This is the newer OpenAPI evolution direction; for basic log writing, use the dedicated .NET SDK.

- Package: `AlibabaCloud.SDK.Sls20201230` (NuGet)
- Language / Platform: C# / .NET

## Repository

- GitHub: https://github.com/aliyun/alibabacloud-csharp-sdk (mono-repo, `sls-20201230` module)

## Official Docs

- OpenAPI overview: https://help.aliyun.com/zh/sls/developer-reference/api-overview
- API list: https://next.api.aliyun.com/document/Sls/2020-12-30/overview
- Per-API doc: `https://next.api.aliyun.com/document/Sls/2020-12-30/<ApiName>` (e.g. `CreateProject`, `GetLogsV2`)
- Online debugging & sample code: `https://next.api.aliyun.com/api/Sls/2020-12-30/<ApiName>?sdkStyle=dara&tab=DEMO&lang=CSHARP`

## Install

```bash
dotnet add package AlibabaCloud.SDK.Sls20201230
dotnet add package Aliyun.Credentials
```

## Quick Start

```csharp
using AlibabaCloud.SDK.Sls20201230;
using AlibabaCloud.SDK.Sls20201230.Models;
using AlibabaCloud.OpenApiClient.Models;

var credentialConfig = new Aliyun.Credentials.Models.Config
{
    Type = "access_key",
    AccessKeyId = Environment.GetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    AccessKeySecret = Environment.GetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
};
var credential = new Aliyun.Credentials.Client(credentialConfig);

var config = new Config
{
    Credential = credential,
};
config.Endpoint = "cn-hangzhou.log.aliyuncs.com";
var client = new Client(config);

int now = (int)DateTimeOffset.UtcNow.ToUnixTimeSeconds();
var request = new GetLogsV2Request
{
    From = now - 3600,
    To = now,
    Query = "*",
    Line = 100,
    Offset = 0,
};
var response = client.GetLogsV2("your_project", "your_logstore", request);
```

## Capability

| Capability | Ref |
| --- | --- |
| Query logs (`GetLogsV2`) | inline |
| Manage resources | inline |

## Notes

- **Do NOT use this SDK for writing logs.** For basic log writing (`PostLogStoreLogsAsync`), use [aliyun-log-dotnetcore-sdk](../aliyun-log-dotnetcore-sdk/index.md).
- Compared to `aliyun-log-dotnetcore-sdk`, this OpenAPI SDK has broader resource-management API coverage and is the recommended path for new resource-management integrations.
