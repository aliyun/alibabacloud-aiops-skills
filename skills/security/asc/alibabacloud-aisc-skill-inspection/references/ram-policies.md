# RAM Permissions

This Skill requires the following AISC (Agent Security Center) OpenAPI permissions:

| API | Operation | RAM Action | Description |
|-----|-----------|-----------|-------------|
| CreateSkillFileCheck | Submit check | `aisc:CreateSkillFileCheck` | Batch submit Skill file security check tasks |
| ListSubTasks | Query results | `aisc:ListSubTasks` | Retrieve sub-task detection results |

## Minimal Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "aisc:CreateSkillFileCheck",
        "aisc:ListSubTasks"
      ],
      "Resource": "*"
    }
  ]
}
```

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
