# Mem0 (Memory Engine) APIs

PolarDB-X Mem0 memory-engine APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--db-instance-name`.

> **Security:** The Mem0 API key is a credential. NEVER echo or hardcode it. The public-connection API is FORBIDDEN by default (see bottom).

---

## CreateMem0

Enable the Mem0 memory engine on an instance.

> **[MUST] Secondary confirmation required.** Enabling Mem0 may change billing. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx create-mem0 \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateMem0`

---

## DeleteMem0

Disable the Mem0 memory engine.

> **[MUST] Secondary confirmation required.** Disabling Mem0 removes the memory engine. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx delete-mem0 \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DeleteMem0`

---

## DescribeMem0Info

Query the Mem0 memory-engine information.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx describe-mem0-info \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeMem0Info`

---

## DescribeMem0SecurityIps

Query the Mem0 IP whitelist.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx describe-mem0-security-ips \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeMem0SecurityIps`

---

## ModifyMem0SecurityIps

Modify the Mem0 IP whitelist.

> **[MUST] Do not open to the public internet.** Reject `0.0.0.0/0`; confirm the exact CIDR list with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `security-ip-list` | String | IP list, comma-separated |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `group-name` | String | Whitelist group name |
| `modify-mode` | String | Whitelist modify mode |

### CLI example

```bash
aliyun polardbx modify-mem0-security-ips \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --security-ip-list 192.168.0.0/24 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyMem0SecurityIps`

---

## ResetMem0AccountPassword

Reset the Mem0 API key.

> **[MUST] Secondary confirmation required.** Resetting the API key invalidates the old key. Confirm with the user; never echo the key.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `mem0-api-key` | String | API key (never echo) |

### CLI example

```bash
aliyun polardbx reset-mem0-account-password \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ResetMem0AccountPassword`

---

## CreateGatewayConsumerForPolarDBX

Create an AI gateway consumer for a PolarDB-X instance.

> Note: This action may require the latest `aliyun` CLI plugin. If the plugin reports an unknown command, update it (`aliyun plugin update`) or call the OpenAPI directly. Verify exact parameters via `aliyun polardbx <action> --help` after updating.

### RAM action

`polardbx:CreateGatewayConsumerForPolarDBX`

---

## Public-network connection APIs (FORBIDDEN)

`AllocateMem0PublicConnection` (`allocate-mem0-public-connection`) allocates a PUBLIC-network address for Mem0 and is **forbidden** by default. `ReleaseMem0PublicConnection` (`release-mem0-public-connection`) may be used only to remove an existing public endpoint. Only proceed if the user explicitly accepts the risk of public exposure.

RAM actions: `polardbx:AllocateMem0PublicConnection`, `polardbx:ReleaseMem0PublicConnection`
