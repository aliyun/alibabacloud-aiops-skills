# RAM Permissions Required: DataHub Resource Management

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| DataHub | dhs:ListProjects | * | List all projects in a region |
| DataHub | dhs:CreateProject | * | Create a DataHub project |
| DataHub | dhs:GetProject | * | Query project information |
| DataHub | dhs:UpdateProject | * | Update project description |
| DataHub | dhs:DeleteProject | * | Delete a project |
| DataHub | dhs:ListTopics | * | List all topics in a project |
| DataHub | dhs:CreateTopic | * | Create a topic |
| DataHub | dhs:GetTopic | * | Query topic information |
| DataHub | dhs:UpdateTopic | * | Update topic description |
| DataHub | dhs:DeleteTopic | * | Delete a topic |
| DataHub | dhs:ListSubscriptions | * | List subscriptions under a topic |
| DataHub | dhs:CreateSubscription | * | Create a subscription |
| DataHub | dhs:GetSubscription | * | Query subscription information |
| DataHub | dhs:DeleteSubscription | * | Delete a subscription |

## RAM Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dhs:ListProjects",
        "dhs:CreateProject",
        "dhs:GetProject",
        "dhs:UpdateProject",
        "dhs:DeleteProject",
        "dhs:ListTopics",
        "dhs:CreateTopic",
        "dhs:GetTopic",
        "dhs:UpdateTopic",
        "dhs:DeleteTopic",
        "dhs:ListSubscriptions",
        "dhs:CreateSubscription",
        "dhs:GetSubscription",
        "dhs:DeleteSubscription"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- The above policy grants full DataHub resource lifecycle management permissions.
- For production use, consider restricting `Resource` to specific project ARNs.
- Read-only operations (`List*`, `Get*`) can be separated into a read-only policy for monitoring purposes.
