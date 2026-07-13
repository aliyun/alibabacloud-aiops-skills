# Elasticsearch Config Management

> Routing entry: [../SKILL.md](../SKILL.md)
>
> This document covers **Snapshot (backup) management**, **Dict (analyzer dictionary) management**, **Kibana settings**, and **ES cluster YML configuration** for an existing Elasticsearch instance.
> Global conventions (Authentication, Observability, common CLI args, idempotency, RAM rules) are defined in `SKILL.md` and apply to every command below.

## Table of Contents

- [Snapshot Management](#snapshot-management)
  - [1. UpdateSnapshotSetting](#1-updatesnapshotsetting)
  - [2. DescribeSnapshotSetting](#2-describesnapshotsetting)
  - [3. CreateSnapshot](#3-createsnapshot)
- [Dict Management](#dict-management)
  - [4. ListDicts](#4-listdicts)
  - [5. UpdateDict](#5-updatedict)
  - [6. UpdateHotIkDicts](#6-updatehotikdicts)
  - [7. UpdateSynonymsDicts](#7-updatesynonymsdicts)
  - [8. UpdateAliwsDict](#8-updatealiwsdict)
- [Kibana Settings](#kibana-settings)
  - [9. DescribeKibanaSettings](#9-describekibanasettings)
  - [10. UpdateKibanaSettings](#10-updatekibanasettings)
- [ES Cluster YML Configuration](#es-cluster-yml-configuration)
  - [11. UpdateInstanceSettings](#11-updateinstancesettings)
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
| Idempotency | All write APIs (`UpdateSnapshotSetting`, `CreateSnapshot`, `UpdateDict`, `UpdateHotIkDicts`, `UpdateSynonymsDicts`, `UpdateAliwsDict`, `UpdateKibanaSettings`, `UpdateInstanceSettings`) MUST pass `--client-token $(uuidgen)`. Use the SAME token when retrying after timeout. |
| Pre-check | All write APIs require the instance to be in `active` status. Run `aliyun elasticsearch describe-instance --region <RegionId> --instance-id <InstanceId> --cli-query "Result.status"` first. |
| OSS dict files | For `sourceType=OSS`, the OSS bucket must be in the SAME region as the ES instance and PUBLICLY READABLE. Existing dict files NOT explicitly listed with `sourceType=ORIGIN` will be DELETED — every Update*Dict call MUST include the full final desired dict list. |

---

## Snapshot Management

### 1. UpdateSnapshotSetting

Update the automatic snapshot policy of the instance (cron + on/off).

- **API**: `UpdateSnapshotSetting`
- **HTTP**: `POST|PUT /openapi/instances/[InstanceId]/snapshot-setting`
- **Idempotent**: No (config-overwriting; safe to repeat)

**Pre-check**

- Instance status MUST be `active`.
- If `enable=true`, `quartzRegex` is REQUIRED.

**Required Parameters**

| Parameter | Location | Required | Description |
|---|---|---|---|
| `--region` | flag | Yes | Region of the instance, user-provided |
| `--instance-id` | flag | Yes | Instance ID, user-provided |
| `enable` | body | Yes | `true` to enable scheduled snapshot, `false` to disable |
| `quartzRegex` | body | Conditional | Quartz cron expression. Required when `enable=true`, e.g. `0 0 01 ? * * *` (01:00 daily) |

**CLI Template**

```bash
aliyun elasticsearch update-snapshot-setting \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --body '{"enable":true,"quartzRegex":"<cron>"}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example: enable daily snapshot at 01:00**

```bash
aliyun elasticsearch update-snapshot-setting \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --body '{"enable":true,"quartzRegex":"0 0 01 ? * * *"}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response (Result struct)**: `enable`, `quartzRegex`.

---

### 2. DescribeSnapshotSetting

Query the current automatic snapshot configuration.

- **API**: `DescribeSnapshotSetting`
- **HTTP**: `GET /openapi/instances/[InstanceId]/snapshot-setting`

**Required Parameters**

| Parameter | Location | Required | Description |
|---|---|---|---|
| `--region` | flag | Yes | Region of the instance |
| `--instance-id` | flag | Yes | Instance ID |

**CLI Template**

```bash
aliyun elasticsearch describe-snapshot-setting \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example**

```bash
aliyun elasticsearch describe-snapshot-setting \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result.{Enable:Enable,Cron:QuartzRegex}" \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response (Result struct)**

| Field | Type | Description |
|---|---|---|
| `Enable` | bool | Whether scheduled snapshot is enabled |
| `QuartzRegex` | string | Cron expression (Quartz) |

---

### 3. CreateSnapshot

Manually trigger a one-shot snapshot for the instance.

- **API**: `CreateSnapshot`
- **HTTP**: `POST /openapi/instances/[InstanceId]/snapshots`
- **Idempotent**: Yes — `clientToken` is REQUIRED.

**Pre-check**

- Instance status MUST be `active`.
- Automatic snapshot setting must already be configured (call `DescribeSnapshotSetting` first; if `Enable=false` and there is no OSS repo bound, configure via `UpdateSnapshotSetting` first).

**Required Parameters**

| Parameter | Location | Required | Description |
|---|---|---|---|
| `--region` | flag | Yes | Region of the instance |
| `--instance-id` | flag | Yes | Instance ID |
| `--client-token` | query | Yes | UUID, ≤64 ASCII chars; reuse same token on retry |

**CLI Template**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch create-snapshot \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch create-snapshot \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response**: `Result` is `true` (success) / `false` (failure).

---

## Dict Management

> **⚠️ MUST — Disambiguate the dict type BEFORE picking an API**
>
> The four analyzer dict families map to **different APIs** and have different update semantics:
>
> | Dict family | analyzer-type | Update API | Notes |
> |---|---|---|---|
> | IK main / stopword (cold) | `IK` | `UpdateDict` | Cold update — always restarts the cluster (run during off-peak hours) |
> | IK main / stopword (hot) | `IK_HOT` | `UpdateHotIkDicts` | Restart-free **only when file content changes**; any file-count or file-name change still restarts the cluster |
> | Synonyms | `SYNONYMS` | `UpdateSynonymsDicts` | `*.txt` files |
> | AliNLP / analysis-aliws | `ALIWS` | `UpdateAliwsDict` | File MUST be `aliws_ext_dict.txt`; nodes auto-load without cluster restart |
>
> If the user does NOT explicitly state which dict family they want to update (e.g. only says "更新词典" / "update dictionaries" without naming IK / IK_HOT / synonyms / AliWS), **STOP and ASK** the user to clarify. **Do NOT guess** the dict family from file names, prior conversation, or defaults — choosing the wrong API will silently overwrite or delete unrelated dicts due to full-list semantics.

> **CRITICAL — Full-list semantics**
>
> All `Update*Dict` APIs use **full-list overwrite** semantics on the request body:
> - The body MUST be a **JSON array** containing every dict file you want to keep AFTER the call.
> - Files in the array with `sourceType=OSS` are uploaded/replaced from OSS.
> - Existing files you want to keep MUST be re-listed with `sourceType=ORIGIN`.
> - Any pre-existing file NOT listed in this call will be **DELETED**.
>
> Workflow: call `ListDicts` first → build the full target list → submit it via `UpdateDict` / `UpdateHotIkDicts` / `UpdateSynonymsDicts` / `UpdateAliwsDict`.

### 4. ListDicts

Return the dict list for a given analyzer type, including a temporary public download URL (90s validity).

- **API**: `ListDicts`
- **HTTP**: `GET /openapi/instances/[InstanceId]/dicts`

**Required Parameters**

| Parameter | Location | Required | Description |
|---|---|---|---|
| `--region` | flag | Yes | Region of the instance |
| `--instance-id` | flag | Yes | Instance ID |
| `--analyzer-type` | query | Yes | One of `IK` (IK cold-update), `IK_HOT` (IK hot-update), `SYNONYMS`, `ALIWS` |
| `--name` | query | No | Filter by file name |

**CLI Template**

```bash
aliyun elasticsearch list-dicts \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --analyzer-type <IK|IK_HOT|SYNONYMS|ALIWS> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example: list IK hot-update dicts and project key fields**

```bash
aliyun elasticsearch list-dicts \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --analyzer-type IK_HOT \
  --cli-query "Result[].{Name:name,Type:type,Source:sourceType,Size:fileSize}" \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `name` | Dict file name |
| `type` | For IK / IK_HOT: `MAIN` (main dict) or `STOP` (stopword); for SYNONYMS: `SYNONYMS`; for ALIWS: `ALI_WS` |
| `sourceType` | `OSS` or `ORIGIN` |
| `fileSize` | File size (Byte) |
| `downloadUrl` | Pre-signed download URL, valid for 90s |

---

### 5. UpdateDict

Cold-update of the IK analyzer dicts (main / stopword). Triggers an instance restart-style change.

> **⚠️ Restart impact**: A cold-update operation will restart the cluster. To avoid impacting your business, please perform this operation during off-peak hours; once the restart completes, the new dicts take effect automatically.

- **API**: `UpdateDict`
- **HTTP**: `PUT /openapi/instances/[InstanceId]/dict`
- **Idempotent**: Yes — pass `clientToken`.

> **⚠️ CRITICAL — Full-list semantics**: This API performs a **full replacement**. The body MUST contain ALL dictionaries you want to keep. Any existing dictionary NOT included in the request body will be **permanently deleted**. To obtain the current cold-update dict list, call `DescribeInstance` and read `Result.dictList`. For dictionaries that already exist on the server and should be retained as-is, set `sourceType` to `ORIGIN` (no need to re-upload via OSS).

**Pre-check**

- Instance status MUST be `active`.
- For `sourceType=OSS`, the OSS object must exist and the bucket must be publicly readable.

**Required Parameters**

| Parameter | Location | Required | Description |
|---|---|---|---|
| `--region` | flag | Yes | Region of the instance |
| `--instance-id` | flag | Yes | Instance ID |
| `--client-token` | query | Yes (idempotency) | UUID |
| `--body` | body | Yes | JSON array of dict objects |

**Body Item Schema**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Dict file name (`*.dic`) |
| `type` | Yes | `MAIN` or `STOP` |
| `sourceType` | Yes | `OSS` (new upload) or `ORIGIN` (keep) |
| `ossObject.bucketName` | Required when `sourceType=OSS` | OSS bucket name |
| `ossObject.key` | Required when `sourceType=OSS` | Object key in the bucket |

**CLI Template**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch update-dict \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_ARRAY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example: add one custom MAIN dict from OSS while keeping system dicts**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch update-dict \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '[
    {"name":"my_main.dic","type":"MAIN","sourceType":"OSS","ossObject":{"bucketName":"my-bucket","key":"es/my_main.dic"}},
    {"name":"SYSTEM_MAIN.dic","type":"MAIN","sourceType":"ORIGIN"},
    {"name":"SYSTEM_STOPWORD.dic","type":"STOP","sourceType":"ORIGIN"}
  ]' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

---

### 6. UpdateHotIkDicts

Hot-update of the IK analyzer dicts (main / stopword).

> **⚠️ Restart conditions**: Hot-update is restart-free **only when only the file CONTENTS are changed** (the new full-list keeps the same set of entries — same count AND same names — as the existing list, with `sourceType=OSS` only re-uploading the file content). **If the dict file count OR any file name changes, the cluster will still be restarted**. To avoid impacting your business, please perform such operations during off-peak hours; once the restart completes, the new dicts take effect automatically. Always call `ListDicts --analyzer-type=IK_HOT` (or `DescribeInstance` → `Result.ikHotDicts`) first to confirm the current entries before constructing the body.

- **API**: `UpdateHotIkDicts`
- **HTTP**: `PUT /openapi/instances/{InstanceId}/ik-hot-dict`
- **Idempotent**: Yes — pass `clientToken`.

> **⚠️ CRITICAL — Full-list semantics**: This API performs a **full replacement**. The body MUST contain ALL dictionaries you want to keep. Any existing dictionary NOT included in the request body will be **permanently deleted**. To obtain the current hot IK dict list, call `DescribeInstance` and read `Result.ikHotDicts`.

**Pre-check**: same as `UpdateDict`. Body uses the same schema as `UpdateDict` (`type` ∈ `MAIN | STOP`).

> **`sourceType` values**: `OSS` = upload new dict file from OSS; `ORIGIN` = retain an existing dictionary already on the server (no re-upload needed). When performing a full-list update, existing dicts you want to **keep unchanged** MUST be listed with `"sourceType": "ORIGIN"`.

**CLI Template**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch update-hot-ik-dicts \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_ARRAY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example: hot-replace IK STOP dict**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch update-hot-ik-dicts \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '[
    {"name":"hot_stop.dic","type":"STOP","sourceType":"OSS","ossObject":{"bucketName":"my-bucket","key":"es/hot_stop.dic"}},
    {"name":"SYSTEM_MAIN.dic","type":"MAIN","sourceType":"ORIGIN"},
    {"name":"SYSTEM_STOPWORD.dic","type":"STOP","sourceType":"ORIGIN"}
  ]' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

---

### 7. UpdateSynonymsDicts

Update the synonym dictionary (`type` is fixed to `SYNONYMS`, file MUST be `*.txt`).

- **API**: `UpdateSynonymsDicts`
- **HTTP**: `PUT /openapi/instances/[InstanceId]/synonymsDict`
- **Idempotent**: Yes — pass `clientToken`.

> **⚠️ CRITICAL — Full-list semantics**: This API performs a **full replacement**. The body MUST contain ALL synonym dictionaries you want to keep. Any existing dictionary NOT included in the request body will be **permanently deleted**. To obtain the current synonyms dict list, call `DescribeInstance` and read `Result.synonymsDicts`.

**Body Item Schema** (per item; same full-list semantics)

| Field | Required | Description |
|---|---|---|
| `name` | Yes | TXT file name (`*.txt`) |
| `type` | Yes | Fixed `SYNONYMS` |
| `sourceType` | Yes | `OSS` (upload new from OSS) or `ORIGIN` (retain existing dict as-is, no re-upload) |
| `ossObject.bucketName` / `ossObject.key` | Required when `sourceType=OSS` | OSS location |

> **Note on `ORIGIN`**: For dictionaries that already exist on the server and should be kept unchanged, set `"sourceType": "ORIGIN"`. You do NOT need to provide `ossObject` for these items.

**CLI Template**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch update-synonyms-dicts \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_ARRAY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch update-synonyms-dicts \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '[
    {"name":"my_synonyms.txt","type":"SYNONYMS","sourceType":"OSS","ossObject":{"bucketName":"my-bucket","key":"es/my_synonyms.txt"}}
  ]' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

---

### 8. UpdateAliwsDict

Update the AliNLP analyzer dict (plugin `analysis-aliws`, `type` fixed to `ALI_WS`). The `analysis-aliws` plugin supports hot-updating the custom dictionary file `aliws_ext_dict.txt`. After upload, nodes will auto-load the dict file — takes effect WITHOUT cluster restart.

- **API**: `UpdateAliwsDict`
- **HTTP**: `PUT /openapi/instances/[InstanceId]/aliws-dict`
- **Idempotent**: Yes — pass `clientToken`.
- **Constraint**: Not supported on Elasticsearch 5.x.

> **ℹ️ Note**: After installing the `analysis-aliws` plugin, the system does NOT ship any built-in dict file — you MUST upload one manually before the plugin becomes effective.

**Dict File Requirements** (MUST be satisfied BEFORE upload to OSS):

| Item | Requirement |
|---|---|
| File name | MUST be exactly `aliws_ext_dict.txt` |
| Encoding | MUST be UTF-8 |
| Content | One word per line; NO leading/trailing whitespace on any line |
| Line ending | MUST be UNIX/Linux LF (`\n`). Files generated on Windows MUST be converted via `dos2unix` before upload |

> **⚠️ CRITICAL — Full-list semantics**: This API performs a **full replacement**. The body MUST contain ALL AliWS dictionaries you want to keep. Any existing dictionary NOT included in the request body will be **permanently deleted**. To obtain the current AliWS dict list, call `DescribeInstance` and read `Result.aliwsDicts`.

**Body Item Schema**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Dict file name |
| `type` | Yes | Fixed `ALI_WS` |
| `sourceType` | Yes | `OSS` (upload new from OSS) or `ORIGIN` (retain existing dict as-is, no re-upload) |
| `ossObject.bucketName` / `ossObject.key` | Required when `sourceType=OSS` | OSS location |

> **Note on `ORIGIN`**: For dictionaries that already exist on the server and should be kept unchanged, set `"sourceType": "ORIGIN"`. You do NOT need to provide `ossObject` for these items.

**CLI Template**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch update-aliws-dict \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_ARRAY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch update-aliws-dict \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '[
    {"name":"aliws_ext_dict.txt","type":"ALI_WS","sourceType":"OSS","ossObject":{"bucketName":"my-bucket","key":"es/aliws_ext_dict.txt"}}
  ]' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

---

## Error Handling

| Error | Likely Cause | Remediation |
|---|---|---|
| `InstanceNotFound` | Wrong region / instance ID / instance deleted | Verify `--region` and `--instance-id`; call `describe-instance` to confirm |
| Body parse error on `Update*Dict` | Body is not a JSON array, or missing required fields per item | Confirm body is `[ {...}, {...} ]` and every item has `name`/`type`/`sourceType` |
| OSS access denied | Bucket not public-read, or bucket region differs from ES instance region | Make bucket region-matched and publicly readable, or grant proper RAM access |
| Existing dict disappeared after update | Item not listed with `sourceType=ORIGIN` | Re-`ListDicts` and re-submit with the full target list |
| `UpdateAliwsDict` rejected | Instance ES version is 5.x | AliWS not supported on 5.x |

---

## Kibana Settings

### 9. DescribeKibanaSettings

Retrieve the current Kibana configuration for a specified Elasticsearch instance.

- **API**: `DescribeKibanaSettings`
- **HTTP**: `GET /openapi/instances/{InstanceId}/kibana-settings`
- **Read-only**: Yes — no `clientToken` needed.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |

**CLI Example**

```bash
aliyun elasticsearch describe-kibana-settings --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | Map of Kibana settings key-value pairs (e.g. `map.includeElasticMapsService`, `server.ssl.enabled`, etc.) |
| `RequestId` | Request ID |

---

### 10. UpdateKibanaSettings

Update the Kibana configuration for a specified Elasticsearch instance. Currently only supports changing the Kibana UI language.

- **API**: `UpdateKibanaSettings`
- **HTTP**: `POST /openapi/instances/{InstanceId}/actions/update-kibana-settings`
- **Idempotent**: Yes — `clientToken` recommended.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `clientToken` | Query | No | Idempotency token (max 64 ASCII chars) |
| `i18n.locale` | Body | No | Kibana language. Only two values allowed: `en` (English, default) or `zh-CN` (Chinese). |

**CLI Example**

```bash
aliyun elasticsearch update-kibana-settings --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '{"i18n.locale":"zh-CN"}' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | `true` if Kibana settings updated successfully, `false` otherwise |
| `RequestId` | Request ID |

---

## ES Cluster YML Configuration

### 11. UpdateInstanceSettings

Update the YML parameter configuration (`elasticsearch.yml`) of a specified Elasticsearch instance.

- **API**: `UpdateInstanceSettings`
- **HTTP**: `POST /openapi/instances/{InstanceId}/instance-settings`
- **Idempotent**: Yes — `clientToken` recommended.

> **Important Behaviors**
> - This API **triggers a rolling restart** of the cluster. Operate during low-traffic periods.
> - Instance must be in `active` status. Cannot be called when instance is in `activating`, `invalid`, or `inactive` state.
> - If an ongoing blue-green change exists (instance status = `activating`), only `normal` (in-place) update strategy is allowed.

> **CRITICAL — Full-replacement semantics**
> - `esConfig` is applied as the **complete, final** YML config set — it **fully replaces** the existing config. It is **NOT** an incremental patch: any existing key **NOT** present in the submitted `esConfig` will be **removed/reset**.
> - Therefore you **MUST NOT** submit only the single key you want to change. The correct workflow is:
>   1. Call `DescribeInstance` first and read the current full YML config from `Result.esConfig`.
>   2. Merge your change into that full map (add / modify / delete the target key).
>   3. Submit the **entire merged `esConfig`** in the request body.
> - If `DescribeInstance` returns no `esConfig` (empty/absent), the instance currently has no custom YML overrides — submit the full desired set explicitly.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `clientToken` | Query | No | Idempotency token (max 64 ASCII chars) |
| `updateStrategy` | Query | No | Change strategy: `normal` (in-place, default — rolling restart one-by-one, no data copy), `blue_green` (blue-green — adds new nodes, copies data, smooth but slow, IPs will change), `intelligent` (system auto-selects optimal strategy). |

**Request Body**

> The `esConfig` object MUST be the **full** desired config map (see Full-replacement semantics above), not just the changed key.

```json
{
  "esConfig": {
    "<yml_param_key>": "<value>"
  }
}
```

**Supported YML Parameters**

| Parameter | Default | Version | Description |
|---|---|---|---|
| `action.auto_create_index` | `false` | All | Allow auto-creation of indices when a new document arrives for a non-existent index. |
| `action.destructive_requires_name` | `true` | All | Require explicit index name when deleting (disallow wildcards). |
| `xpack.security.audit.enabled` | `false` | All | Enable audit logging. Logs take disk space and affect performance — use with caution. |
| `xpack.watcher.enabled` | `false` | All | Enable X-Pack Watcher. Remember to periodically clean `.watcher-history*` indices. |
| `http.cors.enabled` | `false` | All | Enable CORS access. |
| `http.cors.allow-origin` | `""` | All | Allowed origin domains (supports regex, e.g. `/https?:\/\/localhost(:[0-9]+)?/`). `*` allows all (not recommended). |
| `http.cors.max-age` | `1728000` | All | CORS preflight cache time in seconds (default 20 days). |
| `http.cors.allow-methods` | `OPTIONS,HEAD,GET,POST,PUT,DELETE` | All | Allowed HTTP methods. |
| `http.cors.allow-headers` | `X-Requested-With,Content-Type,Content-Length` | All | Allowed request headers. |
| `http.cors.allow-credentials` | `false` | All | Whether to return `Access-Control-Allow-Credentials`. |
| `reindex.remote.whitelist` | — | All | Remote reindex whitelist (host:port). |
| `thread_pool.bulk.queue_size` | `200` | 5.x, 6.x | Write queue size (use `thread_pool.write.queue_size` for 6.x+). |
| `thread_pool.write.queue_size` | `200` | 6.x, 7.x, 8.x | Write queue size. |
| `thread_pool.search.queue_size` | `1000` | All | Search queue size (max 1000 via API; contact support for higher). |
| `xpack.sql.enabled` | `true` | All | X-Pack SQL plugin. Set `false` to use a custom SQL plugin. |
| `xpack.security.audit.logfile.events.include` | `access_denied, anonymous_access_denied, authentication_failed, connection_denied, tampered_request, run_as_denied, run_as_granted` | 7.x, 8.x | Audit event types to include in log file. Add `access_granted` to capture successful requests (increases disk usage significantly). |
| `xpack.security.audit.index.bulk_size` | `1000` | 5.x, 6.x | Bulk size for audit index writes. |
| `xpack.security.audit.index.flush_interval` | `1s` | 5.x, 6.x | Flush interval for audit index buffer. |
| `xpack.security.audit.index.rollover` | `daily` | 5.x, 6.x | Audit index rollover frequency (hourly/daily/weekly/monthly). |
| `xpack.security.audit.index.events.include` | `access_denied, access_granted, anonymous_access_denied, authentication_failed, connection_denied, tampered_request, run_as_denied, run_as_granted` | 5.x, 6.x | Audit event types to write to index. |
| `xpack.security.audit.index.events.exclude` | — | 5.x, 6.x | Audit event types to exclude from index. |
| `xpack.security.audit.index.events.emit_request_body` | `false` | 5.x, 6.x | Include REST request body in audit events (security risk). |
| `xpack.security.audit.index.settings.index.number_of_shards` | `5` | 5.x, 6.x | Number of primary shards for the audit log index. Must be set together with `xpack.security.audit.enabled: true`. |
| `xpack.security.audit.index.settings.index.number_of_replicas` | `1` | 5.x, 6.x | Number of replicas for the audit log index. Must be set together with `xpack.security.audit.enabled: true`. |
| `xpack.security.authc.realms.ldap1` | — | 6.x+ | LDAP realm configuration. |
| `xpack.security.authc.realms.active_directory1` | — | 6.x+ | Active Directory realm configuration. |
| `xpack.security.authc.realms.pki1` | — | 6.x+ | PKI realm configuration. |
| `xpack.security.authc.realms.saml1` | — | 6.x+ | SAML realm configuration. |
| `xpack.security.authc.realms.kerberos1` | — | 6.x+ | Kerberos realm configuration. |
| `xpack.security.authc.token.enabled` | — | 6.x+ | Token-based authentication. |

**CLI Example**

```bash
# Step 1: Fetch the current FULL YML config (full-replacement semantics — you must resubmit all existing keys)
aliyun elasticsearch describe-instance --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --cli-query "Result.esConfig" \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Step 2: Merge your change into the full esConfig, then submit the ENTIRE map.
# Example: existing esConfig already had {"action.auto_create_index":"true"}; now also set thread_pool.write.queue_size=500
aliyun elasticsearch update-instance-settings --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '{"esConfig":{"action.auto_create_index":"true","thread_pool.write.queue_size":500}}' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | Full instance detail object (same structure as `DescribeInstance` response) |
| `RequestId` | Request ID |

---

## Official Documentation

- [UpdateSnapshotSetting](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatesnapshotsetting)
- [DescribeSnapshotSetting](https://www.alibabacloud.com/help/zh/es/developer-reference/api-describesnapshotsetting)
- [CreateSnapshot](https://www.alibabacloud.com/help/zh/es/developer-reference/api-createsnapshot)
- [ListDicts](https://www.alibabacloud.com/help/zh/es/developer-reference/api-listdicts)
- [UpdateDict](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatedict)
- [UpdateHotIkDicts](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatehotikdicts)
- [UpdateSynonymsDicts](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatesynonymsdicts)
- [UpdateAliwsDict](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatealiwsdict)
- [DescribeKibanaSettings](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/DescribeKibanaSettings)
- [UpdateKibanaSettings](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/UpdateKibanaSettings)
- [UpdateInstanceSettings](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/UpdateInstanceSettings)
