# Tags & Resource Group APIs

PolarDB-X tag and resource-group management APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`. Resource type must be `PolarDBXInstance`. `--resource-id` and `--tag` are list-type parameters (repeat or pass multiple values).

---

## TagResources

Attach tags to resources.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region |
| `resource-id` | List | Resource ID(s), max 50 |
| `resource-type` | String | Must be `PolarDBXInstance` |
| `tag` | List | Tag list, max 20 (`key`/`value` pairs) |

### CLI example

```bash
aliyun polardbx tag-resources \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --resource-type PolarDBXInstance \
  --resource-id '["pxc-********"]' \
  --tag '[{"Key":"env","Value":"prod"}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:TagResources`

---

## UntagResources

Remove tags from resources.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region |
| `resource-id` | List | Resource ID(s), max 50 |
| `resource-type` | String | Must be `PolarDBXInstance` |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `tag-key` | List | Tag keys to remove, max 20 |
| `all` | Boolean | Remove all tags (only when `tag-key` is empty) |

### CLI example

```bash
aliyun polardbx untag-resources \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --resource-type PolarDBXInstance \
  --resource-id '["pxc-********"]' \
  --tag-key '["env"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:UntagResources`

---

## ListTagResources

Query the tag-to-resource relationships.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region |
| `resource-type` | String | Must be `PolarDBXInstance` |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `resource-id` | List | Filter by resource ID(s), max 50 |
| `tag` | List | Filter by tag list, max 20 |
| `next-token` | String | Pagination token |

### CLI example

```bash
aliyun polardbx list-tag-resources \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --resource-type PolarDBXInstance \
  --resource-id '["pxc-********"]' \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ListTagResources`

---

## DescribeTags

Query tag information.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance name |
| `tag-key` | String | Tag key filter |

### CLI example

```bash
aliyun polardbx describe-tags \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeTags`

---

## ChangeResourceGroup

Move an instance to another resource group.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `new-resource-group-id` | String | New resource group ID |
| `resource-id` | String | Resource ID (instance) |
| `resource-type` | String | Only `PolarDB-X 2.0` instance is supported |

### CLI example

```bash
aliyun polardbx change-resource-group \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --resource-id pxc-******** \
  --resource-type INSTANCE \
  --new-resource-group-id rg-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ChangeResourceGroup`

---

## UpdateCustinsParam

Update an instance tag/parameter (name/value pair).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `name` | String | Name |
| `value` | String | Value |

### CLI example

```bash
aliyun polardbx update-custins-param \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --name <name> \
  --value <value> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:UpdateCustinsParam`
