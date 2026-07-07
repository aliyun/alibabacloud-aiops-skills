# aliyun-log-nodejs-sdk

## Summary

Node.js SDK for Alibaba Cloud SLS. Wraps most SLS APIs behind a promise-based `Client`: write (`postLogStoreLogs`), query (`getLogs`, `getHistograms`), and manage Project / Logstore / index.

- Package: `@alicloud/log` (npm)
- Language / Platform: Node.js (JavaScript; no TypeScript typings)

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-nodejs-sdk

## Official Docs

- Overview: https://help.aliyun.com/zh/sls/developer-reference/overview-of-log-service-sdk-for-node-js
- Install: https://help.aliyun.com/zh/sls/developer-reference/install-log-service-sdk-for-node-js
- Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-node-js

## Install

```bash
npm install @alicloud/log
```

## Quick Start

```js
const Client = require('@alicloud/log')
const client = new Client({
  accessKeyId: process.env.ALIBABA_CLOUD_ACCESS_KEY_ID,
  accessKeySecret: process.env.ALIBABA_CLOUD_ACCESS_KEY_SECRET,
  endpoint: 'cn-hangzhou.log.aliyuncs.com',
})
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Basic / batch (`postLogStoreLogs`) | inline |
| Query logs (`getLogs`) | inline |
| Manage resources | inline |

## Notes

- JavaScript SDK — no official TypeScript typings.
