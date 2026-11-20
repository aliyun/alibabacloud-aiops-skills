# aliyun-log-dotnetcore-sdk

## Summary

.NET SDK for Alibaba Cloud SLS. Wraps the SLS REST API behind an async, thread-safe `ILogServiceClient`: write (`PostLogStoreLogsAsync`), query (`GetLogsAsync`), and manage Project / Logstore / index.

- Package: `aliyun-log-dotnetcore-sdk` (NuGet)
- Language / Platform: C# / .NET

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-dotnetcore-sdk

## Official Docs

- Overview: https://help.aliyun.com/zh/sls/developer-reference/overview-of-log-service-sdk-for-dotnet-core
- Install: https://help.aliyun.com/zh/sls/developer-reference/install-log-service-sdk-for-dotnet-core
- Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-dotnet-core

## Install

```bash
dotnet add package aliyun-log-dotnetcore-sdk
```

> Or `Install-Package aliyun-log-dotnetcore-sdk` via the NuGet Package Manager. Feature dependencies (WebApi.Client, Json.Net, Google.Protobuf, lz4net, Zlib) resolve automatically.

## Quick Start

```csharp
using Aliyun.Api.LogService;

ILogServiceClient client = LogServiceClientBuilders.HttpBuilder
    .Endpoint("cn-hangzhou.log.aliyuncs.com", "your_project")
    .Credential(
        Environment.GetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_ID"),
        Environment.GetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_SECRET"))
    .Build();
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Basic / batch (`PostLogStoreLogsAsync`) | inline |
| Query logs (`GetLogsAsync`) | inline |
| Manage resources | inline |

## Notes

- Supported platforms: .NET Core 2.0, .NET Framework 4.6.1/4.6.2 (via .NET Core 1.x/2.0 SDK), Mono 5.4, Xamarin (iOS/Mac/Android), UWP 10.0.16299.
