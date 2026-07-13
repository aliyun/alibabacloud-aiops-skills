# Elasticsearch Plugin Management

> Routing entry: [../SKILL.md](../SKILL.md)
>
> This document covers **Plugin management** (system plugins, user custom plugins) for an existing Elasticsearch instance.
> Global conventions (Authentication, Observability, common CLI args, idempotency, RAM rules) are defined in `SKILL.md` and apply to every command below.

## Table of Contents

- [1. ListPlugins](#1-listplugins)
- [2. ListUserPlugin](#2-listuserplugin)
- [3. InstallSystemPlugin](#3-installsystemplugin)
- [4. UninstallPlugin](#4-uninstallplugin)
- [5. PluginAnalysis](#5-pluginanalysis)
- [6. InstallUserPlugins](#6-installuserplugins)
- [Common Conventions](#common-conventions)
- [Official Documentation](#official-documentation)

---

## Common Conventions

> The following short rules apply to every API in this document. Full text lives in `SKILL.md`.

| Item | Rule |
|---|---|
| Common CLI args | **`--user-agent` applies ONLY to business API commands** (e.g. `aliyun elasticsearch ...`); such commands MUST pass `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}` (see `SKILL.md#observability` for `SESSION_ID` generation rule). **System / tool commands** (`aliyun configure`, `aliyun version`, `aliyun plugin update`, `aliyun help`, etc.) **MUST NOT** carry `--user-agent` — they do not support the flag. Each business command also appends `--connect-timeout 3 --read-timeout 10` (write op: `--read-timeout 30`). |
| Region | `--region` is REQUIRED and MUST be explicitly provided by the user. Do NOT guess. |
| InstanceId | `--instance-id` is REQUIRED and MUST be explicitly provided by the user. |

---

### 1. ListPlugins

List the system (built-in) plugins installed on a specified Elasticsearch instance.

- **API**: `ListPlugins`
- **HTTP**: `GET /openapi/instances/{InstanceId}/plugins`
- **Read-only**: Yes — no `clientToken` needed.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `name` | Query | No | Filter by plugin name (e.g. `analysis-ik`) |
| `page` | Query | No | Page number (default 1) |
| `size` | Query | No | Page size (default 10) |
| `source` | Query | No | Plugin source type. Only `SYSTEM` is supported. |

**CLI Example**

```bash
aliyun elasticsearch list-plugins --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result[]` | Array of plugin objects |
| `Result[].name` | Plugin name (e.g. `analysis-ik`, `aliyun-qos`) |
| `Result[].state` | Plugin state: `INSTALLED` / `UNINSTALLED` / `INSTALLING` / `UNINSTALLING` / `UPGRADING` / `FAILED` / `UNKNOWN` |
| `Result[].source` | Source type: `SYSTEM` |
| `Result[].description` | Plugin description |
| `Result[].specificationUrl` | Plugin documentation URL (may be null) |
| `Headers.X-Total-Count` | Total number of plugins |
| `RequestId` | Request ID |

---

### 2. ListUserPlugin

List the user-uploaded custom plugins for a specified Elasticsearch instance.

- **API**: `ListUserPlugin`
- **HTTP**: `GET /openapi/instances/{InstanceId}/userPlugins`
- **Read-only**: Yes — no `clientToken` needed.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `name` | Query | No | Filter by plugin name |
| `page` | Query | No | Page number (default 1) |
| `size` | Query | No | Page size (default 50) |

**CLI Example**

```bash
aliyun elasticsearch list-user-plugin --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Example**

```json
{
  "RequestId": "019F3AAB-191D-15F7-AAB7-72DA2D1585BD",
  "Headers": {
    "X-Total-Count": 1,
    "totalCount": 1
  },
  "Result": [
    {
      "bingoPlugins": [
        {
          "elasticsearchVersion": "8.15.1",
          "pluginType": "CUSTOM_PLUGIN",
          "imageBuiltin": false,
          "name": "analysis-icu",
          "description": "The ICU Analysis plugin integrates the Lucene ICU module...",
          "state": "UNINSTALLED",
          "source": "USER",
          "version": "8.15.1",
          "fileVersion": "CAEQmQIYgYDAvZTW6vkZ..."
        }
      ],
      "name": "analysis-icu",
      "state": "UNINSTALLED",
      "source": "USER",
      "version": ""
    }
  ]
}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result[]` | Array of user plugin groups |
| `Result[].name` | Plugin name |
| `Result[].state` | Plugin state: `INSTALLED` / `UNINSTALLED` / `INSTALLING` / `UNINSTALLING` / `UPGRADING` / `FAILED` / `UNKNOWN` |
| `Result[].source` | Source type: `USER` |
| `Result[].version` | Plugin version (may be empty) |
| `Result[].bingoPlugins[]` | **Detailed plugin metadata array** — use these objects as the request body for `InstallUserPlugins` |
| `Result[].bingoPlugins[].elasticsearchVersion` | Target ES version |
| `Result[].bingoPlugins[].pluginType` | `CUSTOM_PLUGIN` |
| `Result[].bingoPlugins[].imageBuiltin` | `false` for custom plugins |
| `Result[].bingoPlugins[].name` | Plugin name |
| `Result[].bingoPlugins[].description` | Plugin description |
| `Result[].bingoPlugins[].state` | `UNINSTALLED` / `INSTALLED` |
| `Result[].bingoPlugins[].source` | `USER` |
| `Result[].bingoPlugins[].version` | Plugin version |
| `Result[].bingoPlugins[].fileVersion` | File version identifier (required for install) |
| `Headers.X-Total-Count` | Total number of user plugins |
| `RequestId` | Request ID |

---

### 3. InstallSystemPlugin

Install one or more system (built-in) plugins on a specified Elasticsearch instance.

- **API**: `InstallSystemPlugin`
- **HTTP**: `POST /openapi/instances/{InstanceId}/plugins/system/actions/install`
- **Idempotent**: Yes — `clientToken` recommended.

> **Important Behaviors**
> - The instance must be in `active` status before calling this API.
> - Plugin installation may trigger a cluster restart depending on the plugin type. Perform during off-peak hours.
> - **[MUST] Confirmation gate**: Because this operation may trigger a cluster restart, you **MUST** first present the target instance ID, the plugin(s) to install, and the restart risk to the user, and obtain **explicit confirmation** before executing. Do NOT auto-execute. If the user has not clearly confirmed, **STOP and ASK**.
> - **Prerequisite**: Call `ListPlugins` first to query available system plugins. Only plugins with `state=UNINSTALLED` and `source=SYSTEM` can be installed.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `clientToken` | Query | No | Idempotency token (max 64 ASCII chars) |

**Request Body**

JSON array of plugin names to install:

```json
["aliyun-sql", "codec-compression"]
```

**CLI Example**

```bash
aliyun elasticsearch install-system-plugin --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '["analysis-aliws"]' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | List of plugin names that were requested for installation |
| `RequestId` | Request ID |

---

### 4. UninstallPlugin

Uninstall one or more system plugins from a specified Elasticsearch instance.

- **API**: `UninstallPlugin`
- **HTTP**: `POST /openapi/instances/{InstanceId}/plugins/actions/uninstall`
- **Idempotent**: Yes — `clientToken` recommended.

> **Important Behaviors**
> - The instance must be in `active` status before calling this API.
> - Plugin uninstallation triggers a cluster restart. Perform during off-peak hours.
> - **[MUST] Confirmation gate**: Because this operation triggers a cluster restart, you **MUST** first present the target instance ID, the plugin(s) to uninstall, and the restart risk to the user, and obtain **explicit confirmation** before executing. Do NOT auto-execute. If the user has not clearly confirmed, **STOP and ASK**.
> - **Prerequisite**: Call `ListPlugins` first to query installed system plugins. Only plugins with `state=INSTALLED` and `source=SYSTEM` can be uninstalled.
> - Use `force=true` only on new-architecture instances (i.e. `DescribeInstance` returns `Result.archType = "Public"`) to cancel an in-progress installation.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `clientToken` | Query | No | Idempotency token (max 64 ASCII chars) |
| `force` | Query | No | Force uninstall (cancel in-progress install on new-arch instances where `DescribeInstance` returns `Result.archType = "Public"`). Default: `false` |

**Request Body**

JSON array of plugin names to uninstall:

```json
["aliyun-sql", "codec-compression"]
```

**CLI Example**

```bash
aliyun elasticsearch uninstall-plugin --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '["aliyun-sql"]' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | List of plugin names that were requested for uninstallation |
| `RequestId` | Request ID |

---

### 5. PluginAnalysis

Upload custom plugin(s) from OSS to the instance's plugin library. After upload, the plugin is in "pending install" state. Supports `dryRun=true` for validation without actually uploading.

- **API**: `PluginAnalysis`
- **HTTP**: `POST /openapi/instances/{InstanceId}/plugins/actions/analysis`
- **Write**: Yes — no `clientToken` supported by this API.

> **Architecture Requirement**
> - **Only cloud-native (v3) instances** support this API (`DescribeInstance` returns `Result.archType = "Public"`).
> - v2 (basic control) instances do **NOT** support custom plugin upload/install — this feature is under internal upgrade and suspended. If urgently needed, contact support via ticket.

> **Important Behaviors**
> - The instance must be in `active` status before calling this API.
> - This is a **prerequisite step** before `InstallUserPlugins`. The workflow is:
>   1. Call `PluginAnalysis` (dryRun defaults to `true`) to **validate** the plugin (compatibility, naming, size).
>   2. Call `PluginAnalysis` with `dryRun=false` to **upload** the plugin to the library.
>   3. Call `InstallUserPlugins` to **install** the uploaded plugin (triggers cluster restart).
> - Plugin file requirements:
>   - Filename: uppercase/lowercase letters, numbers, hyphen (`-`) or dot (`.`), length 8–128, suffix `.zip`
>   - `plugin-descriptor.properties` must be at the ZIP root
>   - Single file ≤ 100 MB; max 50 plugins per instance
>   - Plugin name must not conflict with existing custom plugins. If the name conflicts with a system plugin, the custom plugin will override the system one upon installation.
> - Upload does NOT auto-install. Must call `InstallUserPlugins` separately.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `dryRun` | Query | No | Default `true` (validate only, no upload). Set to `false` to actually upload to library. |

**Request Body**

JSON array of objects. Each object has `name` (display name in library) and `ossObject` pointing to the OSS location:

```json
[
  {
    "name": "analysis-icu-8.15.1.zip",
    "ossObject": {
      "bucketName": "my-plugin-bucket",
      "key": "plugin/analysis-icu-8.15.1.zip"
    }
  }
]
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Plugin zip file name |
| `ossObject.bucketName` | string | Yes | OSS bucket name (must be in the same region as the ES instance) |
| `ossObject.key` | string | Yes | OSS object key (path within bucket) |

**CLI Examples**

```bash
# Step 1: Dry-run validation (default behavior, dryRun defaults to true)
aliyun elasticsearch plugin-analysis --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '[{"name":"analysis-icu-8.15.1.zip","ossObject":{"bucketName":"my-plugin-bucket","key":"plugin/analysis-icu-8.15.1.zip"}}]' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Step 2: Upload to plugin library (must explicitly set dryRun=false)
aliyun elasticsearch plugin-analysis --instance-id es-cn-xxxxx --dry-run false \
  --region cn-hangzhou \
  --body '[{"name":"analysis-icu-8.15.1.zip","ossObject":{"bucketName":"my-plugin-bucket","key":"plugin/analysis-icu-8.15.1.zip"}}]' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | Upload result or validation result |
| `RequestId` | Request ID |

---

### 6. InstallUserPlugins

Install user-uploaded custom plugins (previously uploaded via `PluginAnalysis`) on a specified instance.

- **API**: `InstallUserPlugins`
- **HTTP**: `POST /openapi/instances/{InstanceId}/plugins/user/actions/install`
- **Write**: Yes — no `clientToken` supported by this API.

> **Architecture Requirement**
> - **Only cloud-native (v3) instances** support this API (`DescribeInstance` returns `Result.archType = "Public"`).
> - v2 (basic control) instances do **NOT** support custom plugin upload/install — this feature is under internal upgrade and suspended. If urgently needed, contact support via ticket.

> **Important Behaviors**
> - **Prerequisite**: The plugin must have been uploaded to the library via `PluginAnalysis` first (see [Section 5](#5-pluginanalysis)).
> - The instance must be in `active` status before calling this API. Returns `InstanceActivating` error if the instance is still activating.
> - Installation triggers a cluster restart. Operate during off-peak hours.
> - **[MUST] Confirmation gate**: Because this operation triggers a cluster restart, you **MUST** first present the target instance ID, the plugin(s) to install, and the restart risk to the user, and obtain **explicit confirmation** before executing. Do NOT auto-execute. If the user has not clearly confirmed, **STOP and ASK**.
> - If the custom plugin name conflicts with a system built-in plugin, the installation will **automatically override** the system plugin with the custom one.
> - On cloud-native (v3) instances, you can cancel an in-progress installation.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |

**Request Body**

JSON array of plugin metadata objects. These fields come from `ListUserPlugin` response → `Result[].bingoPlugins[]` (where state=`UNINSTALLED`):

```json
[
  {
    "elasticsearchVersion": "8.15.1",
    "pluginType": "CUSTOM_PLUGIN",
    "imageBuiltin": false,
    "name": "analysis-icu",
    "description": "The ICU Analysis plugin integrates the Lucene ICU module into Elasticsearch, adding ICU-related analysis components.",
    "state": "UNINSTALLED",
    "source": "USER",
    "version": "8.15.1",
    "fileVersion": "CAEQmQIYgYDAvZTW6vkZIiBkMmNlZWVmOTUwNWY0MWZhYmU1YWYwMTA2YTIxMDYxZA--"
  }
]
```

| Field | Type | Required | Description |
|---|---|---|---|
| `elasticsearchVersion` | string | Yes | Target ES version (must match instance version) |
| `pluginType` | string | Yes | Plugin type: `CUSTOM_PLUGIN` |
| `imageBuiltin` | bool | Yes | Whether built into image. Custom plugins are `false` |
| `name` | string | Yes | Plugin name (without `.zip` suffix) |
| `description` | string | Yes | Plugin description |
| `state` | string | Yes | Must be `UNINSTALLED` (only uninstalled plugins can be installed) |
| `source` | string | Yes | Source type: `USER` |
| `version` | string | Yes | Plugin version |
| `fileVersion` | string | Yes | File version identifier (from upload response / ListUserPlugin) |

**CLI Example**

```bash
# Install the uploaded plugin (triggers restart)
# Body = ListUserPlugin → Result[].bingoPlugins[] (where state=UNINSTALLED)
aliyun elasticsearch install-user-plugins --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '[{"elasticsearchVersion":"8.15.1","pluginType":"CUSTOM_PLUGIN","imageBuiltin":false,"name":"analysis-icu","description":"The ICU Analysis plugin","state":"UNINSTALLED","source":"USER","version":"8.15.1","fileVersion":"CAEQmQIYgYDA..."}]' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Complete Workflow Example**

```bash
# === Upload & Install Custom Plugin (3-step workflow) ===

# 1. Dry-run: validate plugin compatibility (dryRun defaults to true, no need to specify)
aliyun elasticsearch plugin-analysis --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '[{"name":"analysis-icu-8.15.1.zip","ossObject":{"bucketName":"my-plugin-bucket","key":"plugin/analysis-icu-8.15.1.zip"}}]' \
  --connect-timeout 3 --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# 2. Upload: push plugin to library (must set dryRun=false)
aliyun elasticsearch plugin-analysis --instance-id es-cn-xxxxx --dry-run false \
  --region cn-hangzhou \
  --body '[{"name":"analysis-icu-8.15.1.zip","ossObject":{"bucketName":"my-plugin-bucket","key":"plugin/analysis-icu-8.15.1.zip"}}]' \
  --connect-timeout 3 --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# 3. Install: install the uploaded plugin (triggers cluster restart)
# Body = ListUserPlugin → Result[].bingoPlugins[] (where state=UNINSTALLED)
aliyun elasticsearch install-user-plugins --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '[{"elasticsearchVersion":"8.15.1","pluginType":"CUSTOM_PLUGIN","imageBuiltin":false,"name":"analysis-icu","description":"The ICU Analysis plugin","state":"UNINSTALLED","source":"USER","version":"8.15.1","fileVersion":"CAEQmQIYgYDA..."}]' \
  --connect-timeout 3 --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | List of plugin file names that were requested for installation |
| `RequestId` | Request ID |

---

## Official Documentation

- [ListPlugins](https://help.aliyun.com/zh/es/developer-reference/api-listplugins)
- [ListUserPlugin](https://next.api.aliyun.com/document/elasticsearch/2017-06-13/ListUserPlugin)
- [InstallSystemPlugin](https://help.aliyun.com/zh/es/developer-reference/api-installsystemplugin)
- [UninstallPlugin](https://help.aliyun.com/zh/es/developer-reference/api-uninstallplugin)
- [PluginAnalysis](https://next.api.aliyun.com/document/elasticsearch/2017-06-13/PluginAnalysis)
- [InstallUserPlugins](https://help.aliyun.com/zh/es/developer-reference/api-installuserplugins)
- [Upload & Install Custom Plugin (User Guide)](https://help.aliyun.com/zh/es/user-guide/upload-and-install-a-custom-plug-in)
