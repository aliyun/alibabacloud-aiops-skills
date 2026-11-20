# alibabacloud-sls-java-sdk (OpenAPI)

## Summary

Alibaba Cloud OpenAPI SDK for SLS (Java). Auto-generated from API metadata — full, consistent API coverage for resource management (Project, Logstore, index, machine group, dashboard, alert, etc.) and log query. This is the newer OpenAPI evolution direction; for log writing and consumption, use the dedicated SDKs listed below.

- Package: `com.aliyun:sls20201230`
- Language / Platform: Java

## Repository

- GitHub: https://github.com/aliyun/alibabacloud-java-sdk (mono-repo, `sls-20201230` module)

## Official Docs

- OpenAPI overview: https://help.aliyun.com/zh/sls/developer-reference/api-overview
- API list: https://next.api.aliyun.com/document/Sls/2020-12-30/overview
- Per-API doc: `https://next.api.aliyun.com/document/Sls/2020-12-30/<ApiName>` (e.g. `CreateProject`, `GetLogsV2`)
- Online debugging & sample code: `https://next.api.aliyun.com/api/Sls/2020-12-30/<ApiName>?sdkStyle=dara&tab=DEMO&lang=JAVA`

## Install

### Maven

```xml
<dependency>
  <groupId>com.aliyun</groupId>
  <artifactId>sls20201230</artifactId>
  <version>5.16.0</version>
</dependency>
<dependency>
  <groupId>com.aliyun</groupId>
  <artifactId>credentials-java</artifactId>
  <version>0.3.12</version>
</dependency>
```

> Check latest version: [Maven Central](https://central.sonatype.com/artifact/com.aliyun/sls20201230)

## Quick Start

```java
import com.aliyun.sls20201230.Client;
import com.aliyun.sls20201230.models.GetLogsV2Request;
import com.aliyun.sls20201230.models.GetLogsV2Response;
import com.aliyun.teaopenapi.models.Config;

com.aliyun.credentials.models.Config credentialConfig = new com.aliyun.credentials.models.Config();
credentialConfig.setType("access_key");
credentialConfig.setAccessKeyId(System.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"));
credentialConfig.setAccessKeySecret(System.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"));
com.aliyun.credentials.Client credential = new com.aliyun.credentials.Client(credentialConfig);

Config config = new Config().setCredential(credential);
config.endpoint = "cn-hangzhou.log.aliyuncs.com";
Client client = new Client(config);

int now = (int) (System.currentTimeMillis() / 1000);
GetLogsV2Request request = new GetLogsV2Request()
    .setFrom(now - 3600)
    .setTo(now)
    .setQuery("*")
    .setLine(100L)
    .setOffset(0L);

GetLogsV2Response response = client.getLogsV2("your_project", "your_logstore", request);
```

## Capability

| Capability | Ref |
| --- | --- |
| Query logs (`GetLogsV2`) | inline |
| Manage resources | inline |

## Notes

- For log writing, use [aliyun-log-java-producer](../aliyun-log-java-producer/index.md) (high-throughput) or [aliyun-log-java-sdk](../aliyun-log-java-sdk/index.md) (basic `PutLogs`). For log consumption, use [aliyun-log-consumer-java](../aliyun-log-consumer-java/index.md).
- Compared to `aliyun-log-java-sdk`, this OpenAPI SDK has broader resource-management API coverage and is the recommended path for new resource-management integrations.
