# RAM Policy Reference (ram-policies)

The RAM Action list, system policies, and custom policy examples for all Security Center (SAS) vulnerability module APIs used by this skill. Grant the corresponding permissions to the RAM user or RAM role before executing the matching aliyun CLI commands.

## 1. Authorization Prefix Rules and Exceptions

- RAM Action naming rule for SAS APIs: **the Action name matches the API name**, with the unified prefix `yundun-sas:` (e.g., API `DescribeVulList` → Action `yundun-sas:DescribeVulList`).
- **Exceptions (legacy APIs with the `yundun-aegis:` prefix)** — verified one by one against the "Authorization" section of the official API documentation:

| API | Officially Documented Action | Access Level | Verification |
|-----|------------------------------|--------------|--------------|
| OperateVuls | `yundun-aegis:OperateVuls` | none | Documentation explicitly states the yundun-aegis prefix |
| ModifyStartVulScan | `yundun-aegis:ModifyStartVulScan` | update | Documentation explicitly states the yundun-aegis prefix |
| DescribeVulNumStatistics | `yundun-aegis:DescribeVulNumStatistics` | get | Documentation explicitly states the yundun-aegis prefix |

- **APIs with "no authorization information exposed"** — the official documentation does not expose authorization information; the following uses the `yundun-sas:` prefix convention, **subject to actual RAM enforcement**:

| API | Action Given Here (Convention) | Note |
|-----|--------------------------------|------|
| ModifyOperateVul | `yundun-sas:ModifyOperateVul` | Documentation states "no authorization information exposed"; given by prefix convention |
| DescribeCloudCenterInstances | `yundun-sas:DescribeCloudCenterInstances` | Same as above |
| DescribeVersionConfig | `yundun-sas:DescribeVersionConfig` | Same as above |

- All remaining APIs are explicitly marked with the `yundun-sas:` prefix in the official documentation.

## 2. Read-Only Actions (19)

Read operations can be executed directly (state the intent in one sentence before execution). Granting the following Actions completes all read scenarios — vulnerability query, statistics, and status tracking.

| CLI Command | RAM Action | Access Level |
|-------------|-----------|--------------|
| describe-vul-list | `yundun-sas:DescribeVulList` | get |
| describe-grouped-vul | `yundun-sas:DescribeGroupedVul` | get |
| describe-cloud-center-instances | `yundun-sas:DescribeCloudCenterInstances` | (no authorization info exposed; subject to actual RAM enforcement) |
| describe-vul-details | `yundun-sas:DescribeVulDetails` | get |
| describe-can-fix-vul-list | `yundun-sas:DescribeCanFixVulList` | get |
| describe-uuids-by-vul-names | `yundun-sas:DescribeUuidsByVulNames` | get |
| describe-version-config | `yundun-sas:DescribeVersionConfig` | (no authorization info exposed; subject to actual RAM enforcement) |
| describe-fix-used-count | `yundun-sas:DescribeFixUsedCount` | get |
| check-trial-fix-count | `yundun-sas:CheckTrialFixCount` | get |
| describe-vul-fix-statistics | `yundun-sas:DescribeVulFixStatistics` | get |
| describe-vul-num-statistics | `yundun-aegis:DescribeVulNumStatistics` | get (yundun-aegis prefix) |
| describe-vul-config | `yundun-sas:DescribeVulConfig` | get |
| describe-vul-whitelist | `yundun-sas:DescribeVulWhitelist` | get |
| describe-emg-vul-item | `yundun-sas:DescribeEmgVulItem` | get |
| describe-vul-check-task-status-detail | `yundun-sas:DescribeVulCheckTaskStatusDetail` | get |
| describe-instance-reboot-status | `yundun-sas:DescribeInstanceRebootStatus` | get |
| describe-once-task | `yundun-sas:DescribeOnceTask` | get |
| describe-front-vul-patch-list | `yundun-sas:DescribeFrontVulPatchList` | get |
| list-vul-auto-repair-config | `yundun-sas:ListVulAutoRepairConfig` | get |

## 3. Write Operation Actions (11)

Write operations cover vulnerability repair, scan triggering, configuration changes, and whitelist/auto-repair configuration changes. Present the change list and obtain user confirmation before execution.

| CLI Command | RAM Action | Access Level |
|-------------|-----------|--------------|
| modify-operate-vul | `yundun-sas:ModifyOperateVul` | (no authorization info exposed; subject to actual RAM enforcement) |
| operate-vuls | `yundun-aegis:OperateVuls` | none (yundun-aegis prefix) |
| modify-start-vul-scan | `yundun-aegis:ModifyStartVulScan` | update (yundun-aegis prefix; full scans only) |
| modify-push-all-task | `yundun-sas:ModifyPushAllTask` | update |
| modify-vul-config | `yundun-sas:ModifyVulConfig` | update |
| modify-vul-target | `yundun-sas:ModifyVulTarget` | update |
| modify-create-vul-whitelist | `yundun-sas:ModifyCreateVulWhitelist` | update |
| delete-vul-whitelist | `yundun-sas:DeleteVulWhitelist` | delete |
| modify-emg-vul-submit | `yundun-sas:ModifyEmgVulSubmit` | update |
| create-vul-auto-repair-config | `yundun-sas:CreateVulAutoRepairConfig` | create |
| delete-vul-auto-repair-config | `yundun-sas:DeleteVulAutoRepairConfig` | delete |

## 4. System Policies

| System Policy | Applicable Scope |
|---------------|------------------|
| `AliyunYundunSASReadOnlyAccess` | Read-only scenarios: covers all read commands in Section 2 |
| `AliyunYundunSASFullAccess` | Grants full read/write access to Security Center (coarse-grained; includes capabilities beyond the vulnerability module; not recommended for least-privilege production use — prefer the custom policies below for vulnerability-module write operations) |

> System policy reference (official RAM documentation): https://help.aliyun.com/zh/ram/developer-reference/aliyunyundunsasfullaccess

## 5. Custom Policy JSON Examples

### 5.1 Full Policy (read + write, covering all 30 APIs of this skill)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sas:DescribeVulList",
        "yundun-sas:DescribeGroupedVul",
        "yundun-sas:DescribeCloudCenterInstances",
        "yundun-sas:DescribeVulDetails",
        "yundun-sas:DescribeCanFixVulList",
        "yundun-sas:DescribeUuidsByVulNames",
        "yundun-sas:DescribeVersionConfig",
        "yundun-sas:DescribeFixUsedCount",
        "yundun-sas:CheckTrialFixCount",
        "yundun-sas:DescribeVulFixStatistics",
        "yundun-sas:DescribeVulConfig",
        "yundun-sas:DescribeVulWhitelist",
        "yundun-sas:DescribeEmgVulItem",
        "yundun-sas:DescribeVulCheckTaskStatusDetail",
        "yundun-sas:DescribeInstanceRebootStatus",
        "yundun-sas:DescribeOnceTask",
        "yundun-sas:DescribeFrontVulPatchList",
        "yundun-sas:ListVulAutoRepairConfig",
        "yundun-sas:ModifyOperateVul",
        "yundun-sas:ModifyPushAllTask",
        "yundun-sas:ModifyVulConfig",
        "yundun-sas:ModifyVulTarget",
        "yundun-sas:ModifyCreateVulWhitelist",
        "yundun-sas:DeleteVulWhitelist",
        "yundun-sas:ModifyEmgVulSubmit",
        "yundun-sas:CreateVulAutoRepairConfig",
        "yundun-sas:DeleteVulAutoRepairConfig",
        "yundun-aegis:DescribeVulNumStatistics",
        "yundun-aegis:OperateVuls",
        "yundun-aegis:ModifyStartVulScan"
      ],
      "Resource": "*"
    }
  ]
}
```

### 5.2 Read-Only Policy (query only, no write operations)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sas:DescribeVulList",
        "yundun-sas:DescribeGroupedVul",
        "yundun-sas:DescribeCloudCenterInstances",
        "yundun-sas:DescribeVulDetails",
        "yundun-sas:DescribeCanFixVulList",
        "yundun-sas:DescribeUuidsByVulNames",
        "yundun-sas:DescribeVersionConfig",
        "yundun-sas:DescribeFixUsedCount",
        "yundun-sas:CheckTrialFixCount",
        "yundun-sas:DescribeVulFixStatistics",
        "yundun-sas:DescribeVulConfig",
        "yundun-sas:DescribeVulWhitelist",
        "yundun-sas:DescribeEmgVulItem",
        "yundun-sas:DescribeVulCheckTaskStatusDetail",
        "yundun-sas:DescribeInstanceRebootStatus",
        "yundun-sas:DescribeOnceTask",
        "yundun-sas:DescribeFrontVulPatchList",
        "yundun-sas:ListVulAutoRepairConfig",
        "yundun-aegis:DescribeVulNumStatistics"
      ],
      "Resource": "*"
    }
  ]
}
```

### 5.3 Fallback Notes

- All SAS vulnerability-related Actions are **account-level (all resources) authorizations**; `Resource: *` is sufficient. Some APIs (e.g., DescribeVulWhitelist) show resource-level ARNs in the documentation, but `*` works as well.
- If a command still returns a permission error (`NoPermission`/`Forbidden`) after granting the full policy above, it may be caused by prefix enforcement differences for legacy APIs: change/add the corresponding `yundun-aegis:` Action alongside the `yundun-sas:` one and retry — **subject to actual RAM enforcement**.
- Policy changes take effect immediately without restarting the CLI; if using STS temporary credentials, re-obtain the token.

## 6. Permission Failure Handling (consistent with SKILL.md, MUST strictly follow)

When any command returns a permission error (e.g., `NoPermission`, `caller has no permission`, `Forbidden`), follow these three steps:

1. **Read this file to locate the missing permission**: Find the RAM Action corresponding to the failed command in the tables above, and tell the user the missing Action name and prefix (yundun-sas / yundun-aegis).
2. **Guide the user to the ram-permission-diagnose skill**: Ask the user to run the ram-permission-diagnose skill (or self-authorize in the RAM console using the policy JSON in Section 5). Never perform any authorization operation on behalf of the user in the conversation.
3. **Pause and wait for user confirmation**: Explicitly state "Please let me know once the permissions are granted, and I will continue." Do not retry write operations before the user confirms authorization is complete; read retries must also be announced first.

> Security constraint: This skill must never read, echo, or request AccessKey/Secret values, and must never write credentials via plaintext `aliyun configure set`. Permission diagnosis is based solely on the error message and the list in this file — never touching credential content.
