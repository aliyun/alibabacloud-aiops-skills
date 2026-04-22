# RAM 权限策略说明

本 Skill 通过 aliyun CLI 调用阿里云云安全中心 (SAS) 和安全令牌服务 (STS)，运行账号（RAM 用户或 RAM 角色）须被授予以下最小权限。

> **注意**：云安全中心 (SAS) 的 RAM 授权粒度为 **SERVICE 级别**，不支持资源级授权，`Resource` 必须设置为 `"*"`。

---

## 所需 RAM Action

### 安全令牌服务 (STS)

| Action | 调用脚本 | 用途 |
|--------|----------|------|
| `sts:GetCallerIdentity` | `accounts.py`、`baseline.py`、`vuln.py` | 获取当前凭证的主账号 ID，用于判断是否省略 `--ResourceDirectoryAccountId` 参数 |

### 云安全中心 (SAS)

RAM Code：`yundun-sas`（同义别名：`threatdetection`、`yundun-aegis`）

| Action | 调用脚本 | 访问级别 | 用途 |
|--------|----------|----------|------|
| `yundun-sas:ListAccountsInResourceDirectory` | `accounts.py` | 读取 | 从资源目录拉取所有成员账号列表 |
| `yundun-sas:DescribeMonitorAccounts` | `accounts.py` | 读取 | 查询已纳入 SAS 监控的成员账号列表，用于过滤 |
| `yundun-sas:ExportRecord` | `baseline.py` | 写入 | 发起基线检测结果导出任务（baselineCspm / exportHcWarning） |
| `yundun-sas:DescribeExportInfo` | `baseline.py` | 读取 | 轮询基线导出任务状态，获取下载链接 |
| `yundun-sas:ExportVul` | `vuln.py` | 写入 | 发起漏洞导出任务（cve / sys / app / emg） |
| `yundun-sas:DescribeVulExportInfo` | `vuln.py` | 读取 | 轮询漏洞导出任务状态，获取下载链接 |

---

## 最小权限策略示例

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

## 多账号访问说明

本工具设计用于**资源目录主账号**（Master Account）下运行，通过 `--ResourceDirectoryAccountId` 参数代入成员账号进行操作。

- 运行凭证须属于资源目录的**管理账号**或已被授权的 RAM 角色
- 成员账号侧无需额外配置，SAS 多账号管理的权限由主账号统一管控
- 若凭证属于成员账号（非主账号），`--ResourceDirectoryAccountId` 参数会被自动省略，仅导出该账号自身的数据

---

## 授权说明

- **读取操作**（`Describe*`、`GetCallerIdentity`）：不修改任何资源，风险低
- **写入操作**（`ExportRecord`、`ExportVul`）：在服务端触发导出任务，不修改用户资产或配置，风险低
- 由于 SAS 不支持资源级授权，所有 `yundun-sas` Action 的 Resource 均须设为 `"*"`

---

## 参考文档

- [云安全中心 RAM 鉴权](https://www.alibabacloud.com/help/en/security-center/developer-reference/api-sas-2018-12-03-ram)
- [STS GetCallerIdentity](https://www.alibabacloud.com/help/en/resource-access-management/latest/getcalleridentity)
- [RAM 自定义策略](https://help.aliyun.com/zh/ram/user-guide/create-a-custom-policy)
