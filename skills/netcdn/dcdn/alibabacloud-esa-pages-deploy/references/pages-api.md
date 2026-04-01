# ESA Functions & Pages — Deployment Reference

All deployments use the same Edge Routine API. Pages is simply a convenience pattern for static content.

> **IMPORTANT — Use existing scripts first**: For common operations, always prefer the pre-made scripts in `scripts/` directory over writing custom code.

## SDK Import & Instantiation (ESM)

> **CRITICAL**: In ESM (`.mjs` files), SDK packages use CommonJS-style exports. You MUST use `.default` when instantiating default-exported classes.

```javascript
import Esa20240910 from "@alicloud/esa20240910";
import OpenApi from "@alicloud/openapi-client";
import Credential from "@alicloud/credentials";

function createClient() {
  // MUST use .default for Credential and Esa20240910 in ESM
  const credential = new Credential.default();
  const config = new OpenApi.Config({
    credential,
    endpoint: "esa.cn-hangzhou.aliyuncs.com",
    userAgent: "AlibabaCloud-Agent-Skills",
  });
  return new Esa20240910.default(config);
}
```

## Response Field Name Casing

> **CRITICAL**: The SDK has two calling styles with DIFFERENT response field name casing:
>
> - **High-level methods** (e.g., `client.getRoutine()`, `client.deleteRoutine()`) → response fields are **camelCase**: `resp.body.routineName`, `resp.body.defaultRelatedRecord`
> - **Low-level `callApi`** → response fields are **PascalCase**: `resp.body.RoutineName`, `resp.body.DefaultRelatedRecord`
>
> Mixing up casing will silently return `undefined` values.

## Deploy HTML Page

Wraps HTML into Edge Routine code automatically.

```javascript

async function deployHtml(name, html) {
  const client = createClient();

  // Wrap HTML as Edge Routine code
  const escapedHtml = html.replace(/`/g, "\\`").replace(/\$/g, "\\$");
  const code = `const html = \`${escapedHtml}\`;

export default {
  async fetch(request) {
    return new Response(html, {
      headers: { "content-type": "text/html;charset=UTF-8" },
    });
  },
};`;

  // 1. Create routine (skip if exists)
  try {
    await client.createRoutine(new $Esa20240910.CreateRoutineRequest({ name }));
  } catch (e) {
    if (!e.message?.includes("RoutineNameAlreadyExist")) throw e;
  }

  // 2. Get upload signature
  const uploadInfo = await client.getRoutineStagingCodeUploadInfo(
    new $Esa20240910.GetRoutineStagingCodeUploadInfoRequest({ name })
  );
  const oss = uploadInfo.body.ossPostConfig || uploadInfo.body.OssPostConfig;

  // 3. Upload code to OSS
  const formData = new FormData();
  formData.append("OSSAccessKeyId", oss.OSSAccessKeyId);
  formData.append("Signature", oss.Signature);
  formData.append("callback", oss.callback);
  formData.append("x:codedescription", oss["x:codeDescription"]);
  formData.append("policy", oss.policy);
  formData.append("key", oss.key);
  formData.append("file", new Blob([code], { type: "text/plain" }));
  await fetch(oss.Url, { method: "POST", body: formData });

  // 4. Commit code version
  const commit = await client.commitRoutineStagingCode(
    new $Esa20240910.CommitRoutineStagingCodeRequest({ name })
  );
  const version = commit.body.codeVersion;

  // 5. Deploy to staging and production
  for (const env of ["staging", "production"]) {
    await client.publishRoutineCodeVersion(
      new $Esa20240910.PublishRoutineCodeVersionRequest({
        name,
        env,
        codeVersion: version,
      })
    );
  }

  // 6. Get access URL
  const routine = await client.getRoutine(
    new $Esa20240910.GetRoutineRequest({ name })
  );
  const domain = routine.body.defaultRelatedRecord;
  return domain ? `https://${domain}` : null;
}

// Usage
const url = await deployHtml("my-page", "<html><body>Hello World</body></html>");
console.log(`Access URL: ${url}`);
```

## Deploy Static Directory

For frontend builds (React/Vue/Angular dist folders).

```javascript
import Esa20240910, * as $Esa20240910 from "@alicloud/esa20240910";
import * as $OpenApi from "@alicloud/openapi-client";
import * as $Util from "@alicloud/tea-util";
import Credential from "@alicloud/credentials";
import JSZip from "jszip";
import * as fs from "fs";
import * as path from "path";

async function deployFolder(name, folderPath, description = "") {
  const client = createClient();

  // 1. Create routine
  try {
    await client.createRoutine(
      new $Esa20240910.CreateRoutineRequest({ name, description })
    );
  } catch (e) {
    if (!e.message?.includes("RoutineNameAlreadyExist")) throw e;
  }

  // 2. Create assets code version
  const params = new $OpenApi.Params({
    action: "CreateRoutineWithAssetsCodeVersion",
    version: "2024-09-10",
    protocol: "https",
    method: "POST",
    authType: "AK",
    bodyType: "json",
    reqBodyType: "json",
    style: "RPC",
    pathname: "/",
  });
  const body = { Name: name, CodeDescription: description };
  const request = new $OpenApi.OpenApiRequest({ body });
  const runtime = new $Util.RuntimeOptions({});
  const result = await client.callApi(params, request, runtime);
  const ossConfig = result.body?.OssPostConfig || {};
  const codeVersion = result.body?.CodeVersion;

  // 3. Package and upload zip
  const zip = new JSZip();
  const addFiles = (dir, zipPath = "") => {
    for (const file of fs.readdirSync(dir)) {
      const fullPath = path.join(dir, file);
      const zipFilePath = zipPath ? `${zipPath}/${file}` : file;
      if (fs.statSync(fullPath).isDirectory()) {
        addFiles(fullPath, zipFilePath);
      } else {
        zip.file(`assets/${zipFilePath}`, fs.readFileSync(fullPath));
      }
    }
  };
  addFiles(folderPath);
  const zipBuffer = await zip.generateAsync({ type: "nodebuffer" });

  const formData = new FormData();
  formData.append("OSSAccessKeyId", ossConfig.OSSAccessKeyId);
  formData.append("Signature", ossConfig.Signature);
  formData.append("policy", ossConfig.Policy);
  formData.append("key", ossConfig.Key);
  if (ossConfig.XOssSecurityToken) {
    formData.append("x-oss-security-token", ossConfig.XOssSecurityToken);
  }
  formData.append("file", new Blob([zipBuffer]));
  await fetch(ossConfig.Url, { method: "POST", body: formData });

  // 4. Wait for build ready
  for (let i = 0; i < 300; i++) {
    const infoParams = new $OpenApi.Params({
      action: "GetRoutineCodeVersionInfo",
      version: "2024-09-10",
      protocol: "https",
      method: "GET",
      authType: "AK",
      bodyType: "json",
      reqBodyType: "json",
      style: "RPC",
      pathname: "/",
    });
    const info = await client.callApi(
      infoParams,
      new $OpenApi.OpenApiRequest({ query: { Name: name, CodeVersion: codeVersion } }),
      runtime
    );
    const status = (info.body?.Status || "").toLowerCase();
    if (status === "available") break;
    if (status && status !== "init") throw new Error(`Build failed: ${status}`);
    await new Promise((r) => setTimeout(r, 1000));
  }

  // 5. Deploy to staging and production
  for (const env of ["staging", "production"]) {
    const deployParams = new $OpenApi.Params({
      action: "CreateRoutineCodeDeployment",
      version: "2024-09-10",
      protocol: "https",
      method: "POST",
      authType: "AK",
      bodyType: "json",
      reqBodyType: "json",
      style: "RPC",
      pathname: "/",
    });
    await client.callApi(
      deployParams,
      new $OpenApi.OpenApiRequest({
        query: {
          Name: name,
          Env: env,
          Strategy: "percentage",
          CodeVersions: JSON.stringify([{ Percentage: 100, CodeVersion: codeVersion }]),
        },
      }),
      runtime
    );
  }

  // 6. Get access URL
  const routine = await client.getRoutine(
    new $Esa20240910.GetRoutineRequest({ name })
  );
  return routine.body.defaultRelatedRecord
    ? `https://${routine.body.defaultRelatedRecord}`
    : null;
}

// Usage
const url = await deployFolder("my-app", "./dist");
console.log(`Access URL: ${url}`);
```

## Deploy Custom Function

For API endpoints or dynamic logic.

```javascript
async function deployFunction(name, code) {
  const client = createClient();

  // 1. Create routine
  try {
    await client.createRoutine(new $Esa20240910.CreateRoutineRequest({ name }));
  } catch (e) {
    if (!e.message?.includes("RoutineNameAlreadyExist")) throw e;
  }

  // 2. Get upload signature
  const uploadInfo = await client.getRoutineStagingCodeUploadInfo(
    new $Esa20240910.GetRoutineStagingCodeUploadInfoRequest({ name })
  );
  const oss = uploadInfo.body.ossPostConfig || uploadInfo.body.OssPostConfig;

  // 3. Upload code
  const formData = new FormData();
  formData.append("OSSAccessKeyId", oss.OSSAccessKeyId);
  formData.append("Signature", oss.Signature);
  formData.append("callback", oss.callback);
  formData.append("x:codedescription", oss["x:codeDescription"]);
  formData.append("policy", oss.policy);
  formData.append("key", oss.key);
  formData.append("file", new Blob([code], { type: "text/plain" }));
  await fetch(oss.Url, { method: "POST", body: formData });

  // 4. Commit and deploy
  const commit = await client.commitRoutineStagingCode(
    new $Esa20240910.CommitRoutineStagingCodeRequest({ name })
  );
  const version = commit.body.codeVersion;

  for (const env of ["staging", "production"]) {
    await client.publishRoutineCodeVersion(
      new $Esa20240910.PublishRoutineCodeVersionRequest({
        name,
        env,
        codeVersion: version,
      })
    );
  }

  // 5. Get access URL
  const routine = await client.getRoutine(
    new $Esa20240910.GetRoutineRequest({ name })
  );
  return routine.body.defaultRelatedRecord
    ? `https://${routine.body.defaultRelatedRecord}`
    : null;
}

// Usage
const code = `
export default {
  async fetch(request) {
    const url = new URL(request.url);
    return new Response(JSON.stringify({ path: url.pathname }), {
      headers: { "content-type": "application/json" },
    });
  },
};
`;
const url = await deployFunction("my-api", code);
```

## Function Management

```javascript
import * as readline from "readline";
import TeaUtil from "@alicloud/tea-util";

// Confirmation helper for destructive operations
function confirmAction(message) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(`⚠️  ${message} (yes/no): `, (answer) => {
      rl.close();
      resolve(["yes", "y"].includes(answer.trim().toLowerCase()));
    });
  });
}

// List all functions
// WARNING: Do NOT use client.getRoutineUserInfo() — it may fail with ParameterNotExist.
// Use callApi with ListUserRoutines instead.
async function listFunctions() {
  const client = createClient();
  const params = new OpenApi.Params({
    action: "ListUserRoutines",
    version: "2024-09-10",
    protocol: "https",
    method: "GET",
    authType: "AK",
    bodyType: "json",
    reqBodyType: "json",
    style: "RPC",
    pathname: "/",
  });
  const runtime = new TeaUtil.RuntimeOptions({});
  const resp = await client.callApi(params, new OpenApi.OpenApiRequest({}), runtime);
  // callApi returns PascalCase field names!
  return resp.body.Routines || [];
}

// Get function details (high-level method — returns camelCase fields)
async function getFunction(name) {
  const client = createClient();
  return await client.getRoutine(new Esa20240910.GetRoutineRequest({ name }));
}

// Delete function (with pre-check and confirmation)
// Uses high-level methods — response fields are camelCase
async function deleteFunction(name) {
  const client = createClient();

  // Pre-check: verify the routine exists and show details
  const info = await client.getRoutine(new Esa20240910.GetRoutineRequest({ name }));
  console.log(`About to delete routine: ${name}`);
  if (info.body.codeVersions?.length) {
    console.log(`  Code versions: ${info.body.codeVersions.length}`);
  }
  if (info.body.defaultRelatedRecord) {
    console.log(`  Access URL: https://${info.body.defaultRelatedRecord}`);
  }

  // Require explicit confirmation before destructive operation
  const confirmed = await confirmAction(
    `This will permanently delete routine "${name}" and all its versions. Continue?`
  );
  if (!confirmed) {
    console.log("Delete aborted.");
    return;
  }

  return await client.deleteRoutine(new Esa20240910.DeleteRoutineRequest({ name }));
}
```

## Route Management

Bind custom domains to functions.

```javascript
// Create route
async function createRoute(siteId, routineName, routeName, rule) {
  const client = createClient();
  return await client.createRoutineRoute(
    new $Esa20240910.CreateRoutineRouteRequest({
      siteId,
      routineName,
      routeName,
      rule,
      routeEnable: "on",
      bypass: "off",
    })
  );
}

// List routes
async function listRoutes(routineName) {
  const client = createClient();
  return await client.listRoutineRoutes(
    new $Esa20240910.ListRoutineRoutesRequest({ routineName })
  );
}
```

## API Reference

| Category | APIs |
|----------|------|
| **Function** | `CreateRoutine`, `DeleteRoutine`, `GetRoutine`, `GetRoutineUserInfo`, `ListUserRoutines` |
| **Code Upload** | `GetRoutineStagingCodeUploadInfo`, `CommitRoutineStagingCode`, `PublishRoutineCodeVersion` |
| **Assets** | `CreateRoutineWithAssetsCodeVersion`, `GetRoutineCodeVersionInfo`, `CreateRoutineCodeDeployment` |
| **Routes** | `CreateRoutineRoute`, `UpdateRoutineRoute`, `DeleteRoutineRoute`, `ListRoutineRoutes` |
| **Records** | `CreateRoutineRelatedRecord`, `DeleteRoutineRelatedRecord`, `ListRoutineRelatedRecords` |

## Notes

1. **Function name**: lowercase letters/numbers/hyphens, start with letter, length ≥ 2
2. **Same name**: Reuses existing function, creates new version
3. **HTML escaping**: Backticks and `$` must be escaped in template strings
4. **Zip structure**: `assets/*` for static files, `routine/index.js` for code
5. **Build timeout**: Assets deployment may take up to 5 minutes for large projects

## Size Limits

| Type | Limit |
|------|-------|
| **Functions (Edge Routine)** | < 5MB |
| **Assets (single file)** | < 25MB |

> **Tip**: For large HTML content, use Static Directory deployment (assets mode) instead of HTML Page deployment to avoid the 5MB ER limit.
