# Elasticsearch Config Management

> Routing entry: [../SKILL.md](../SKILL.md)
>
> This document covers **Snapshot (backup) management** and **Dict (analyzer dictionary) management** for an existing Elasticsearch instance.
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
| Idempotency | All write APIs (`UpdateSnapshotSetting`, `CreateSnapshot`, `UpdateDict`, `UpdateHotIkDicts`, `UpdateSynonymsDicts`, `UpdateAliwsDict`) MUST pass `--client-token $(uuidgen)`. Use the SAME token when retrying after timeout. |
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

## Official Documentation

- [UpdateSnapshotSetting](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatesnapshotsetting)
- [DescribeSnapshotSetting](https://www.alibabacloud.com/help/zh/es/developer-reference/api-describesnapshotsetting)
- [CreateSnapshot](https://www.alibabacloud.com/help/zh/es/developer-reference/api-createsnapshot)
- [ListDicts](https://www.alibabacloud.com/help/zh/es/developer-reference/api-listdicts)
- [UpdateDict](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatedict)
- [UpdateHotIkDicts](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatehotikdicts)
- [UpdateSynonymsDicts](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatesynonymsdicts)
- [UpdateAliwsDict](https://www.alibabacloud.com/help/zh/es/developer-reference/api-updatealiwsdict)
