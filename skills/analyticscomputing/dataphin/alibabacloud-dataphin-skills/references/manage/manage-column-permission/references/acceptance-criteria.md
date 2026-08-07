# 验收标准

## 功能验收

- [ ] 能通过 `get-table-columns` 定位目标表字段候选 GUID，并进一步确认权限 API 可识别的 `ResourceId`。
- [ ] 能通过 `get-users` 确认授权或回收对象的用户身份。
- [ ] 能通过 `list-resource-permissions --tab-type TABLE` 查询表/字段授权记录。
- [ ] 能通过 `grant-resource-permission` 为字段资源授予 `SELECT` 权限。
- [ ] 能通过 `check-resource-permission` 校验用户对字段资源是否拥有指定操作权限。
- [ ] 能通过 `list-resource-permission-operation-log --tab-type TABLE` 查询授权/回收操作日志。
- [ ] 能通过 `revoke-resource-permission` 回收字段资源权限。

## 参数验收

- [ ] 字段级权限使用字段资源类型：`PHYSICAL_FIELD` / `LOGICAL_FIELD` / `LABEL_FIELD` / `REALTIME_LOGICAL_FIELD` / `REALTIME_MIRROR_FIELD`。
- [ ] `--resource-list` 不传裸字符串或 JSON 字符串元素，必须传 JSON 对象元素，如 `--resource-list '{"ResourceId":"field_guid"}'`。
- [ ] `--user-id-list` 使用 CLI 原生 list 格式，支持多个用户 ID。
- [ ] `--operate-list` 使用 CLI 原生 list 格式；字段查看通常为 `SELECT`。
- [ ] `grant-resource-permission` 必填 `--effective-end`，且值为毫秒时间戳。
- [ ] 授权记录和操作日志查询使用 `--tab-type TABLE`。

## 安全验收

- [ ] grant/revoke 写操作前必须 HITL 二次确认字段、用户、操作类型、有效期和原因。
- [ ] 回收前说明可能影响的任务、消费链路、数据服务 API 或报表访问。
- [ ] 不把页面内部 REST 接口 `grantByResource` / `submitAuthRevoke` 作为外部 Skill 命令入口。
- [ ] 不把字段权限误写成行级权限规则；字段权限控制列可见性，行级权限控制行过滤。
- [ ] 所有 API 命令必须携带 `--user-agent AlibabaCloud-Agent-Skills/manage-column-permission/{session-id}`。

## 结果验收

- [ ] grant 后能通过 `check-resource-permission` 或授权记录查询确认权限存在。
- [ ] revoke 后能通过 `check-resource-permission` 或授权记录查询确认权限失效。
- [ ] 操作日志能追踪授权/回收动作。
- [ ] 明确说明运行时查询结果可能受缓存同步、引擎侧鉴权、跨项目权限和审批链路影响。
