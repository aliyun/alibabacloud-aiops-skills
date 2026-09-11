# Related APIs - SLS Alerting

Use this catalog for official API definitions. For commands and their handling,
follow the relevant management operation:

- [Alert rules](rules/manage-alert-rules.md): find, inspect, enable, disable, delete, create, update, and temporarily mute/unmute.
- [Notification resources](notifications/manage-notifications.md): choose the resource by purpose.
- [ResourceRecord API operations](notifications/api/resource-records.md): shared record encoding and CRUD.
- [Alert history](diagnosis/diagnose.md#start-with-the-incident): query execution and trigger evidence.

## Command List

All commands below use `aliyun sls` and API version `2020-12-30`.

| CLI Command | API Action | Description | Documentation |
| --- | --- | --- | --- |
| `list-alerts` | ListAlerts | List rules in a Project | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-listalerts) |
| `get-alert` | GetAlert | Read one rule | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getalert) |
| `create-alert` | CreateAlert | Create a rule | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createalert) |
| `update-alert` | UpdateAlert | Replace a rule's configuration | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-updatealert) |
| `enable-alert` | EnableAlert | Enable evaluation | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-enablealert) |
| `disable-alert` | DisableAlert | Disable evaluation | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-disablealert) |
| `delete-alert` | DeleteAlert | Delete one rule | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-deletealert) |
| `list-resource-record` | ListResourceRecord | List records with offset/size pagination | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-listresourcerecord) |
| `get-resource-record` | GetResourceRecord | Read one record | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getresourcerecord) |
| `create-resource-record` | CreateResourceRecord | Create one record | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createresourcerecord) |
| `update-resource-record` | UpdateResourceRecord | Replace one existing record | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-updateresourcerecord) |
| `delete-resource-record` | DeleteResourceRecord | Delete exact record IDs | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-deleteresourcerecord) |
| `get-project` | GetProject | Resolve Project metadata | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getproject) |
| `get-logs-v2` | GetLogsV2 | Validate a query or inspect alert history | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogsv2) |
