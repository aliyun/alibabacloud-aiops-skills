# RAM permissions and failure handling

This Skill uses the `aliyun-cli-emas-appmonitor` plugin to call the EMAS AppMonitor OpenAPI (`regionId=cn-shanghai`, `product=emas-appmonitor`, `version=2019-06-11`). Below is the **minimum set of RAM actions required to call the 4 core APIs**.

> **RamCode**: EMAS AppMonitor's RAM code is `emasha` (not `emas-appmonitor`). The action prefix for custom policies is `emasha:`. EMAS AppMonitor does **not** support resource-level authorization, so `Resource` must be `"*"`.

## Required actions

| CLI subcommand | RAM action | Purpose |
| --- | --- | --- |
| `aliyun emas-appmonitor get-issues` | `emasha:ViewIssues` | Fetch aggregated error list |
| `aliyun emas-appmonitor get-issue` | `emasha:ViewIssue` | Fetch details of a single aggregated error |
| `aliyun emas-appmonitor get-errors` | `emasha:ViewErrors` | Fetch sample list under an aggregated error |
| `aliyun emas-appmonitor get-error` | `emasha:ViewError` | Fetch full details of a single sample |

## Recommended policy

Read-only permission policy. `Resource` is fixed to `"*"` because EMAS AppMonitor does not support resource-level authorization:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "emasha:ViewIssues",
        "emasha:ViewIssue",
        "emasha:ViewErrors",
        "emasha:ViewError"
      ],
      "Resource": "*"
    }
  ]
}
```

Or attach the official system policy directly:

| System policy | Scope |
| --- | --- |
| `AliyunEMASAppMonitorReadOnlyAccess` | `emasha:View*` + `Resource:"*"` (sufficient for this Skill) |
| `AliyunEMASAppMonitorFullAccess` | `emasha:*` + `Resource:"*"` (grants write access too — not needed here) |

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this Skill
> 2. Invoke the `ram-permission-diagnose` skill to guide the user through requesting the needed permissions
> 3. Pause and wait for the user to confirm the required permissions have been granted before continuing

## Common permission errors

| Symptom | Explanation | Action |
| --- | --- | --- |
| `Code: NoPermission` | The current profile lacks the action | Attach the policy above and retry |
| `Code: Forbidden.RAM` | The RAM sub-user is disabled or the policy has not taken effect | In the RAM console, confirm the policy is attached and the user is enabled |
| HTTP 403 + `SignatureDoesNotMatch` | Wrong AK/SK | Check the profile with `aliyun configure list`; re-run `aliyun configure` if needed (do NOT expose AK/SK in the conversation) |
| `InvalidAccessKeyId.NotFound` | AK is deleted / disabled | Issue a new AK in the RAM console |

## Related resources

- EMAS console: https://emas.console.aliyun.com/
- RAM console: https://ram.console.aliyun.com/
- Official read-only system policy: https://help.aliyun.com/zh/ram/developer-reference/aliyunemasappmonitorreadonlyaccess
- Official full-access system policy: https://help.aliyun.com/zh/ram/developer-reference/aliyunemasappmonitorfullaccess
- AppMonitor RamCode (action prefix for custom policies): `emasha`
