# 相关命令

## 命令总览

| 命令 | OpenAPI Action | 用途 | 类型 |
|------|----------------|------|------|
| `get-table-columns` | `GetTableColumns` | 查询资产表字段，定位字段候选 GUID 与字段元数据 | 读 |
| `get-users` | `GetUsers` | 按用户 ID 批量获取用户信息，授权前确认对象 | 读 |
| `list-resource-permissions` | `ListResourcePermissions` | 分页获取权限授权记录 | 读 |
| `grant-resource-permission` | `GrantResourcePermission` | 通过资源点对用户授权 | 写 |
| `check-resource-permission` | `CheckResourcePermission` | 校验用户是否有指定资源权限点 | 读 |
| `list-resource-permission-operation-log` | `ListResourcePermissionOperationLog` | 分页获取权限操作日志 | 读 |
| `revoke-resource-permission` | `RevokeResourcePermission` | 回收用户资源授权 | 写 |

## 字段级权限核心参数

| 参数 | 命令 | 类型 | 说明 |
|---|---|---|---|
| `--resource-type` | grant/revoke/check | string | 字段权限常用 `PHYSICAL_FIELD` / `LOGICAL_FIELD` / `LABEL_FIELD` / `REALTIME_LOGICAL_FIELD` / `REALTIME_MIRROR_FIELD` |
| `--resource-list` | grant/revoke/check | list(object) | 每个元素必须传 JSON 对象，如 `--resource-list '{"ResourceId":"field_resource_id"}'`；字段 `Guid` 需核对为权限 API 可识别的 `ResourceId` |
| `--operate-list` | grant/revoke | list(string) | 授权/回收操作列表，字段查看通常为 `SELECT` |
| `--operate` | check | string | 单个操作类型，如 `SELECT` |
| `--user-id-list` | grant | list(string) | 待授权用户 ID，CLI 原生 list 格式：`--user-id-list 300001 300002` |
| `--user-id` | revoke/check | string | 单个用户 ID |
| `--effective-end` | grant | string | 有效期时间戳，毫秒 |
| `--tab-type` | list | string | 表/字段权限使用 `TABLE`；数据源权限使用 `DATASOURCE` |
| `--search-text` | list | string | 搜索关键词，建议分别尝试表名、字段名、账号名 |

## 正确参数示例

### 定位字段

```bash
aliyun dataphin-public get-table-columns --tenant-id "$TENANT_ID" \
  --catalog "<业务板块或项目空间名称>" \
  --table-name "<表名>" \
  --user-agent "$UA" --format json
```

### 查询授权记录

```bash
aliyun dataphin-public list-resource-permissions --tenant-id "$TENANT_ID" \
  --tab-type TABLE --search-text "<表名或字段名>" \
  --page 1 --page-size 10 \
  --user-agent "$UA" --format json
```

### 授予字段 SELECT 权限

```bash
aliyun dataphin-public grant-resource-permission --tenant-id "$TENANT_ID" \
  --resource-type PHYSICAL_FIELD \
  --resource-list '{"ResourceId":"<字段资源ID或GUID>"}' \
  --user-id-list "<用户ID>" \
  --operate-list SELECT \
  --effective-end "<毫秒时间戳>" \
  --reason "<授权原因>" \
  --user-agent "$UA" --format json
```

### 校验字段权限

```bash
aliyun dataphin-public check-resource-permission --tenant-id "$TENANT_ID" \
  --resource-type PHYSICAL_FIELD \
  --resource-list '{"ResourceId":"<字段资源ID或GUID>"}' \
  --user-id "<用户ID>" \
  --operate SELECT \
  --user-agent "$UA" --format json
```

### 回收字段权限

```bash
aliyun dataphin-public revoke-resource-permission --tenant-id "$TENANT_ID" \
  --resource-type PHYSICAL_FIELD \
  --resource-list '{"ResourceId":"<字段资源ID或GUID>"}' \
  --user-id "<用户ID>" \
  --operate-list SELECT \
  --reason "<回收原因>" \
  --user-agent "$UA" --format json
```

## 参数陷阱

| 陷阱 | 错误示例 | 正确示例 |
|---|---|---|
| `--resource-list` 传裸字符串 | `--resource-list field_guid` | `--resource-list '{"ResourceId":"field_guid"}'` |
| `--resource-list` 传 JSON 字符串元素 | `--resource-list '"field_guid"'` | `--resource-list '{"ResourceId":"field_guid"}'` |
| 把字段权限当表级权限 | `--resource-type PHYSICAL_TABLE` | `--resource-type PHYSICAL_FIELD` |
| 查询字段权限用错页签 | `--tab-type DATASOURCE` | `--tab-type TABLE` |
| 未确认用户身份 | 直接授权用户 ID | 先 `get-users --user-id-list <id>` 确认 |

## 业务边界

- 公共 OpenAPI 的字段级授权/回收通过 `GrantResourcePermission` / `RevokeResourcePermission` 实现，不直接暴露页面内部 `grantByResource` 请求体。
- `get-table-columns` 用于定位字段候选元数据；真实授权/校验使用的 `ResourceId` 必须以 `list-resource-permissions`、已知授权记录或 `check-resource-permission` 可识别结果为准。
- 授权成功后，运行时查询是否立刻可见可能受缓存同步、引擎侧鉴权、跨项目权限、审批链路影响。
- 字段级权限不同于行级权限：字段权限控制列可见性，行级权限按字段值过滤数据行；不要混用 `manage-row-level-permission` 的规则表达式。
