# RAM Policy Reference

This skill calls Alibaba Cloud Security Center (SAS) and Security Token Service (STS) through the aliyun CLI. The running account (RAM user or RAM role) must be granted the following minimum permissions.

> **Note**: SAS RAM authorization is enforced at the **service level** and does not support resource-level authorization. `Resource` must be set to `"*"`.

---

## Required RAM Actions

### Security Token Service (STS)

| Action | Script | Purpose |
|--------|--------|---------|
| `sts:GetCallerIdentity` | `accounts.py`, `baseline.py`, `vuln.py` | Get the master account ID of the current credentials, used to decide whether to omit the `--ResourceDirectoryAccountId` parameter |

### Security Center (SAS)

RAM code: `yundun-sas` (aliases: `threatdetection`, `yundun-aegis`)

| Action | Script | Access level | Purpose |
|--------|--------|--------------|---------|
| `yundun-sas:ListAccountsInResourceDirectory` | `accounts.py` | Read | List all member accounts from the resource directory |
| `yundun-sas:DescribeMonitorAccounts` | `accounts.py` | Read | List member accounts already monitored by SAS, used for filtering |
| `yundun-sas:ExportRecord` | `baseline.py` | Write | Start a baseline result export task (baselineCspm / exportHcWarning) |
| `yundun-sas:DescribeExportInfo` | `baseline.py` | Read | Poll baseline export task status and get the download link |
| `yundun-sas:ExportVul` | `vuln.py` | Write | Start a vulnerability export task (cve / sys / app / emg) |
| `yundun-sas:DescribeVulExportInfo` | `vuln.py` | Read | Poll vulnerability export task status and get the download link |

---

## Minimum Policy Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sas:ListAccountsInResourceDirectory",
        "yundun-sas:DescribeMonitorAccounts",
        "yundun-sas:ExportRecord",
        "yundun-sas:DescribeExportInfo",
        "yundun-sas:ExportVul",
        "yundun-sas:DescribeVulExportInfo"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Multi-Account Access

This tool is designed to run under the **resource directory master account** and operates on member accounts through the `--ResourceDirectoryAccountId` parameter.

- The running credentials must belong to the resource directory **management account** or to an authorized RAM role.
- No extra configuration is required on member accounts; SAS multi-account permissions are managed centrally by the master account.
- If the credentials belong to a member account (not the master account), the `--ResourceDirectoryAccountId` parameter is omitted automatically and only that account's own data is exported.

---

## Authorization Notes

- **Read operations** (`Describe*`, `GetCallerIdentity`): do not modify any resources; low risk.
- **Write operations** (`ExportRecord`, `ExportVul`): trigger export tasks on the server side without changing user assets or configurations; low risk.
- Because SAS does not support resource-level authorization, the `Resource` of every `yundun-sas` action must be set to `"*"`.

---

## References

- [Security Center RAM authorization](https://www.alibabacloud.com/help/en/security-center/developer-reference/api-sas-2018-12-03-ram)
- [STS GetCallerIdentity](https://www.alibabacloud.com/help/en/resource-access-management/latest/getcalleridentity)
- [Create a custom RAM policy](https://help.aliyun.com/zh/ram/user-guide/create-a-custom-policy)
