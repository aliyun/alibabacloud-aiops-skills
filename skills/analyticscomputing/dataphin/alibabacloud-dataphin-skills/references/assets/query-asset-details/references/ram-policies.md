# RAM 策略

本 skill 涉及的最小 Dataphin OpenAPI 权限列表（纯只读）。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 最小权限

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataphin:GetAssetAttributes",
        "dataphin:GetCatalogAssetDetails"
      ],
      "Resource": "*"
    }
  ]
}
```

> 两者均为只读查询 Action，不涉及任何写权限。
