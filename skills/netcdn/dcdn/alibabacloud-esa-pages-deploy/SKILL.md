---
name: alibabacloud-esa-pages-deploy
description: Deploy HTML pages, static directories, or custom edge functions to Alibaba Cloud ESA edge nodes. Manage Edge KV for distributed key-value storage. Use when deploying web pages, static sites, frontend builds, serverless edge functions, or edge data storage to ESA Functions & Pages.
---

Category: service

# ESA Functions & Pages — Edge Deployment & KV Storage

Deploy to Alibaba Cloud ESA edge nodes via JavaScript SDK. **Provides free global CDN acceleration and edge security protection**, enabling your static assets to be served from the nearest edge node for improved performance and security.

- **Functions & Pages** — Deploy edge functions and static content (same API, Pages is simplified pattern)
- **Edge KV** — Distributed key-value storage accessible from edge functions
- **Free CDN** — Global edge node acceleration, serve static assets from the nearest location
- **Security Protection** — Built-in DDoS protection, WAF, and other edge security capabilities

## Three Deployment Patterns

| Pattern              | Use Case                         | Code Type       | Size Limit           |
| -------------------- | -------------------------------- | --------------- | -------------------- |
| **HTML Page**        | Quick prototypes, single pages   | Auto-wrapped JS | **< 5MB** (ER limit) |
| **Static Directory** | Frontend builds (React/Vue/etc.) | Assets          | **< 25MB** per file  |
| **Custom Function**  | API endpoints, dynamic logic     | Custom JS       | **< 5MB**            |

## Prerequisites

> **Important**: Enable ESA Functions & Pages first at [ESA Console](https://esa.console.aliyun.com/edge/pages/list) before using this skill, or use `OpenErService` API to enable programmatically.

```bash
npm install @alicloud/esa20240910@2.43.0 @alicloud/openapi-client@0.4.15 @alicloud/credentials@2.4.4
```

### Enable Edge Routine Service via API

If the user hasn't enabled the Edge Routine service, call `OpenErService` to enable it:

```javascript
// Check if service is enabled
const status = await client.getErService(
  new $Esa20240910.GetErServiceRequest({}),
);
if (status.body?.status !== "online") {
  // Enable the service
  await client.openErService(new $Esa20240910.OpenErServiceRequest({}));
}
```

## SDK Quickstart

```javascript
import Esa20240910, * as $Esa20240910 from "@alicloud/esa20240910";
import * as $OpenApi from "@alicloud/openapi-client";
import Credential from "@alicloud/credentials";

function createClient() {
  const credential = new Credential();
  const config = new $OpenApi.Config({
    credential,
    endpoint: "esa.cn-hangzhou.aliyuncs.com",
    userAgent: "AlibabaCloud-Agent-Skills",
  });
  return new Esa20240910(config);
}
```

## Unified Deployment Flow

All deployments follow the same pattern:

```
1. CreateRoutine(name)              → Create function (skip if exists)
2. Upload code/assets to OSS        → Via staging upload or assets API
3. Commit & Publish                 → Deploy to staging → production
4. GetRoutine(name)                 → Get access URL (defaultRelatedRecord)
```

### HTML Page Flow

```
CreateRoutine → GetRoutineStagingCodeUploadInfo → Upload wrapped JS
→ CommitRoutineStagingCode → PublishRoutineCodeVersion(staging/production)
```

### Static Directory Flow

```
CreateRoutine → CreateRoutineWithAssetsCodeVersion → Upload zip
→ Poll GetRoutineCodeVersionInfo → CreateRoutineCodeDeployment(staging/production)
```

## Code Format

All deployments ultimately run as Edge Routine code:

```javascript
export default {
  async fetch(request) {
    return new Response("Hello", {
      headers: { "content-type": "text/html;charset=UTF-8" },
    });
  },
};
```

For HTML pages, your HTML is automatically wrapped into this format.

## Zip Package Structure

| Type              | Structure                       |
| ----------------- | ------------------------------- |
| **JS_ONLY**       | `routine/index.js`              |
| **ASSETS_ONLY**   | `assets/*` (static files)       |
| **JS_AND_ASSETS** | `routine/index.js` + `assets/*` |

## API Summary

### Edge Routine Service

- **Service Management**: `OpenErService`, `GetErService`

### Functions & Pages

- **Function Management**: `CreateRoutine`, `GetRoutine`, `ListUserRoutines`
- **Code Version**: `GetRoutineStagingCodeUploadInfo`, `CommitRoutineStagingCode`, `PublishRoutineCodeVersion`
- **Assets Deployment**: `CreateRoutineWithAssetsCodeVersion`, `GetRoutineCodeVersionInfo`, `CreateRoutineCodeDeployment`
- **Routes**: `CreateRoutineRoute`, `ListRoutineRoutes`

### Edge KV

- **Namespace**: `CreateKvNamespace`, `GetKvNamespace`, `GetKvAccount`
- **Key Operations**: `PutKv`, `GetKv`, `ListKvs`
- **Batch Operations**: `BatchPutKv`
- **High Capacity**: `PutKvWithHighCapacity`, `BatchPutKvWithHighCapacity`

## Utility Scripts

Pre-made scripts for common operations. Install dependencies first:

```bash
npm install @alicloud/esa20240910@2.43.0 @alicloud/openapi-client@0.4.15 @alicloud/credentials@2.4.4 @alicloud/tea-util@1.4.9 jszip@3.10.1
```

| Script                | Usage                                                 | Description             |
| --------------------- | ----------------------------------------------------- | ----------------------- |
| `deploy-html.mjs`     | `node scripts/deploy-html.mjs <name> <html-file>`     | Deploy HTML page        |
| `deploy-folder.mjs`   | `node scripts/deploy-folder.mjs <name> <folder>`      | Deploy static directory |
| `deploy-function.mjs` | `node scripts/deploy-function.mjs <name> <code-file>` | Deploy custom function  |
| `manage.mjs`          | `node scripts/manage.mjs list\|get`                   | Manage routines         |

**Examples:**

```bash
# Deploy HTML page
node scripts/deploy-html.mjs my-page index.html

# Deploy React/Vue build
node scripts/deploy-folder.mjs my-app ./dist

# Deploy custom function
node scripts/deploy-function.mjs my-api handler.js

# List all routines
node scripts/manage.mjs list

# Get routine details
node scripts/manage.mjs get my-page
```

## Key Notes

- **Function name**: lowercase letters/numbers/hyphens, start with letter, length ≥ 2
- **Same name**: Reuses existing function, deploys new version
- **Environments**: staging → production (both by default)
- **Access URL**: `defaultRelatedRecord` from `GetRoutine`
- **Size limits**: Functions < 5MB, Assets single file < 25MB, KV value < 2MB (25MB high capacity)

## Credentials

The SDK uses [Alibaba Cloud default credential chain](https://www.alibabacloud.com/help/en/sdk/developer-reference/v2-manage-access-credentials). No explicit AK/SK configuration needed.

> **Note**: ESA endpoint is fixed (`esa.cn-hangzhou.aliyuncs.com`), no region needed.

## Reference

- **Functions & Pages API**: `references/pages-api.md`
- **Edge KV API**: `references/kv-api.md`
