# RAM Policies — alibabacloud-pai-dsw-manage

RAM permissions required for all PAI DSW APIs used by this skill.

## Permission List

| Action | API | Access Level | Resource | Notes |
|---|---|---|---|---|
| `paidsw:CreateInstance` | CreateInstance | Write | `*` | ⚠️ No official authorization docs — contact Alibaba Cloud if permission errors occur |
| `paidsw:UpdatePostPaidInstance` | UpdateInstance | Write | `*` | |
| `paidsw:GetInstance` | GetInstance | Read | `*` | |
| `paidsw:ListInstances` | ListInstances | List | `*` | |
| `paidsw:ListEcsSpecs` | ListEcsSpecs | Read | `*` | |
| `paidsw:StartInstance` | StartInstance | Write | `*` | |
| `paidsw:StopInstance` | StopInstance | Write | `*` | |

## Minimum-Privilege Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "paidsw:CreateInstance",
        "paidsw:UpdatePostPaidInstance",
        "paidsw:GetInstance",
        "paidsw:ListInstances",
        "paidsw:ListEcsSpecs",
        "paidsw:StartInstance",
        "paidsw:StopInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

1. **CreateInstance authorization undocumented** — The official docs state "no authorization info available." The inferred Action is `paidsw:CreateInstance`. If permission is denied:
   - Try `paidsw:CreateInstance` first.
   - Contact Alibaba Cloud support to confirm the canonical Action name.
   - This cannot be auto-verified — confirm manually in the RAM console.

2. **Workspace operations** (e.g., resolving `WorkspaceId`) require additional permissions:
   - `aiworkspace:ListWorkspaces`
   - `aiworkspace:GetWorkspace`

3. **Dataset mounting** requires additional permissions:
   - `paidataset:ListDatasets`
   - `paidataset:GetDataset`

   **Note**: Dataset mounting is optional and requires **explicit user confirmation**. Do NOT assume or auto-generate dataset configurations.

## Links

- [RAM Console](https://ram.console.aliyun.com/)
- [PAI DSW API Overview](https://help.aliyun.com/zh/pai/developer-reference/api-pai-dsw-2022-01-01-overview)
