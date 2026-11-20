# alibabacloud-sls-nodejs-sdk (OpenAPI)

## Summary

Alibaba Cloud OpenAPI SDK for SLS (Node.js / TypeScript). Auto-generated from API metadata — full, consistent API coverage for resource management (Project, Logstore, index, machine group, dashboard, alert, etc.) and log query. This is the newer OpenAPI evolution direction; for basic log writing, use the dedicated Node.js SDK.

- Package: `@alicloud/sls20201230` (npm)
- Language / Platform: Node.js / TypeScript

## Repository

- GitHub: https://github.com/aliyun/alibabacloud-typescript-sdk (mono-repo, `sls-20201230` module)

## Official Docs

- OpenAPI overview: https://help.aliyun.com/zh/sls/developer-reference/api-overview
- API list: https://next.api.aliyun.com/document/Sls/2020-12-30/overview
- Per-API doc: `https://next.api.aliyun.com/document/Sls/2020-12-30/<ApiName>` (e.g. `CreateProject`, `GetLogsV2`)
- Online debugging & sample code: `https://next.api.aliyun.com/api/Sls/2020-12-30/<ApiName>?sdkStyle=dara&tab=DEMO&lang=NODEJS`

## Install

```bash
npm install @alicloud/sls20201230 @alicloud/credentials
```

## Quick Start

```typescript
import Client, { GetLogsV2Request } from '@alicloud/sls20201230';
import Credential, { Config as CredentialConfig } from '@alicloud/credentials';
import { $OpenApiUtil } from '@alicloud/openapi-core';

const credentialConfig = new CredentialConfig({
    type: 'access_key',
    accessKeyId: process.env.ALIBABA_CLOUD_ACCESS_KEY_ID,
    accessKeySecret: process.env.ALIBABA_CLOUD_ACCESS_KEY_SECRET,
});
const credential = new Credential(credentialConfig);

const config = new $OpenApiUtil.Config({ credential });
config.endpoint = 'cn-hangzhou.log.aliyuncs.com';
const client = new Client(config);

const now = Math.floor(Date.now() / 1000);
const request = new GetLogsV2Request({
    query: '*',
    line: 100,
    offset: 0,
    from: now - 3600,
    to: now,
});
const response = await client.getLogsV2('your_project', 'your_logstore', request);
console.log(JSON.stringify(response.body, null, 2));
```

## Capability

| Capability | Ref |
| --- | --- |
| Query logs (`getLogsV2`) | inline |
| Manage resources | inline |

## Notes

- For basic log writing (`postLogStoreLogs`), use [aliyun-log-nodejs-sdk](../aliyun-log-nodejs-sdk/index.md).
- Compared to `aliyun-log-nodejs-sdk`, this OpenAPI SDK has broader resource-management API coverage and is the recommended path for new resource-management integrations.
