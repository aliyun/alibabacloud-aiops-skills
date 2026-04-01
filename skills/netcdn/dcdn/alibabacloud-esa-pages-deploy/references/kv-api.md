# Edge KV — Edge Key-Value Storage Reference

ESA Edge KV is a distributed edge key-value storage service, readable and writable in Edge Routine, also manageable via OpenAPI. Suitable for edge configuration distribution, feature flags, A/B testing, and caching.

## Core Concepts

- **Namespace**: Isolation container for KV data, each account can create multiple namespaces
- **Key**: Key name, max 512 characters, cannot contain spaces or backslashes
- **Value**: Standard API max 2MB, high capacity API max 25MB
- **TTL**: Optional expiration time via `Expiration` (Unix timestamp) or `ExpirationTtl` (seconds)

## Limits

| Limit                                | Value          |
| ------------------------------------ | -------------- |
| Max Key length                       | 512 characters |
| Single Value (PutKv)                 | 2 MB           |
| Single Value (PutKvWithHighCapacity) | 25 MB          |
| Batch request body                   | 100 MB         |
| Single Namespace capacity            | 1 GB           |

## JavaScript SDK Usage

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

### Namespace Management

```javascript
// Create namespace
async function createNamespace(namespace, description = "") {
  const client = createClient();
  return await client.createKvNamespace(
    new $Esa20240910.CreateKvNamespaceRequest({ namespace, description }),
  );
}

// Delete namespace
async function deleteNamespace(namespace) {
  const client = createClient();
  return await client.deleteKvNamespace(
    new $Esa20240910.DeleteKvNamespaceRequest({ namespace }),
  );
}

// List all namespaces
async function listNamespaces() {
  const client = createClient();
  const resp = await client.getKvAccount(
    new $Esa20240910.GetKvAccountRequest({}),
  );
  return resp.body;
}

// Get namespace info
async function getNamespace(namespace) {
  const client = createClient();
  return await client.getKvNamespace(
    new $Esa20240910.GetKvNamespaceRequest({ namespace }),
  );
}
```

### Key-Value Operations

```javascript
// Write key-value pair
async function putKv(namespace, key, value, ttl = null) {
  const client = createClient();
  const request = new $Esa20240910.PutKvRequest({ namespace, key, value });
  if (ttl) request.expirationTtl = ttl;
  return await client.putKv(request);
}

// Read key's value
async function getKv(namespace, key) {
  const client = createClient();
  return await client.getKv(new $Esa20240910.GetKvRequest({ namespace, key }));
}

// Delete key
async function deleteKv(namespace, key) {
  const client = createClient();
  return await client.deleteKv(
    new $Esa20240910.DeleteKvRequest({ namespace, key }),
  );
}

// Get key with TTL info
async function getKvDetail(namespace, key) {
  const client = createClient();
  return await client.getKvDetail(
    new $Esa20240910.GetKvDetailRequest({ namespace, key }),
  );
}

// List keys
async function listKvs(namespace, prefix = null, pageSize = 100) {
  const client = createClient();
  const request = new $Esa20240910.ListKvsRequest({ namespace, pageSize });
  if (prefix) request.prefix = prefix;
  return await client.listKvs(request);
}
```

### Batch Operations

```javascript
// Batch write
async function batchPutKv(namespace, items) {
  // items: [{ Key: "k1", Value: "v1", ExpirationTtl: 3600 }, ...]
  const client = createClient();
  const request = new $Esa20240910.BatchPutKvRequest({ namespace });
  request.body = JSON.stringify(items);
  return await client.batchPutKv(request);
}

// Batch delete
async function batchDeleteKv(namespace, keys) {
  // keys: ["key1", "key2", ...]
  const client = createClient();
  const request = new $Esa20240910.BatchDeleteKvRequest({ namespace });
  request.body = JSON.stringify(keys);
  return await client.batchDeleteKv(request);
}
```

## Using KV in Edge Routine

Access KV storage directly in your Edge Routine code:

```javascript
export default {
  async fetch(request) {
    // Create KV instance (must specify namespace)
    const kv = new EdgeKV({ namespace: "my-namespace" });

    // Write
    await kv.put("key1", "value1");

    // Write with TTL (seconds)
    await kv.put("temp-key", "temp-value", { expirationTtl: 3600 });

    // Read
    const value = await kv.get("key1");

    // Read as specific type
    const jsonValue = await kv.get("config", { type: "json" });

    // Delete
    await kv.delete("key1");

    // List keys with prefix
    const keys = await kv.list({ prefix: "user:" });

    return new Response(JSON.stringify({ value, keys }), {
      headers: { "content-type": "application/json" },
    });
  },
};
```

### EdgeKV API in Edge Routine

| Method                         | Description                                                        |
| ------------------------------ | ------------------------------------------------------------------ |
| `kv.get(key, options?)`        | Read value. Options: `{ type: "text" \| "json" \| "arrayBuffer" }` |
| `kv.put(key, value, options?)` | Write value. Options: `{ expirationTtl: seconds }`                 |
| `kv.delete(key)`               | Delete key                                                         |
| `kv.list(options?)`            | List keys. Options: `{ prefix: string, limit: number }`            |

## Common Workflows

### 1. Initialize KV Storage

```
CreateKvNamespace → PutKv / BatchPutKv → ListKvs (verify)
```

### 2. Configuration Distribution

```javascript
// 1. Write config via OpenAPI
await putKv(
  "config",
  "feature-flags",
  JSON.stringify({
    newFeature: true,
    maxRetries: 3,
  }),
);

// 2. Read in Edge Routine
export default {
  async fetch(request) {
    const kv = new EdgeKV({ namespace: "config" });
    const flags = await kv.get("feature-flags", { type: "json" });

    if (flags.newFeature) {
      // New feature logic
    }
    return new Response("OK");
  },
};
```

### 3. Edge Caching

```javascript
export default {
  async fetch(request) {
    const kv = new EdgeKV({ namespace: "cache" });
    const url = new URL(request.url);
    const cacheKey = `page:${url.pathname}`;

    // Try cache first
    let content = await kv.get(cacheKey);
    if (content) {
      return new Response(content, {
        headers: { "x-cache": "HIT" },
      });
    }

    // Fetch from origin
    const response = await fetch(request);
    content = await response.text();

    // Cache for 1 hour
    await kv.put(cacheKey, content, { expirationTtl: 3600 });

    return new Response(content, {
      headers: { "x-cache": "MISS" },
    });
  },
};
```

## Common Error Codes

| HTTP | Error Code                  | Description              |
| ---- | --------------------------- | ------------------------ |
| 400  | InvalidNameSpace.Malformed  | Invalid namespace name   |
| 400  | InvalidKey.Malformed        | Invalid key name         |
| 400  | InvalidKey.ExceedsMaximum   | Key > 512 bytes          |
| 400  | InvalidValue.ExceedsMaximum | Value > 2MB (or 25MB)    |
| 404  | InvalidNameSpace.NotFound   | Namespace not found      |
| 404  | InvalidKey.NotFound         | Key not found            |
| 406  | InvalidNameSpace.Duplicate  | Namespace already exists |
| 406  | InvalidNameSpace.QuotaFull  | Namespace quota exceeded |
| 403  | InvalidKey.ExceedsCapacity  | Namespace capacity full  |
| 429  | TooQuickRequests            | Rate limit exceeded      |
