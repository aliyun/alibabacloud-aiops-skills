# RAM Policies

This document describes the RAM permissions required by the `alibabacloud-oos-chatops-agent` skill.

## Required Permissions

| Action | Service | Description |
|--------|---------|-------------|
| `oos:Chat` | OOS (Operation Orchestration Service) | Send chat messages to OOS ChatOps Agent |

## Minimal RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oos:Chat"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- The `oos:Chat` permission is the only permission directly required by this skill.
- The OOS ChatOps Agent itself may internally call other Alibaba Cloud APIs (e.g., `ecs:DescribeInstances`) to fulfill user queries. Those permissions are handled by the OOS service's own service-linked role, not by the caller's identity.
- If the OOS Agent reports permission errors for specific resource operations, the user may need to grant additional permissions to the OOS service role — not to the skill's calling identity.
