# RAM Policies: alibabacloud-cms-dataset

Required RAM permissions for CMS Dataset operations (API version 2024-03-30).

## Permission List

| API | RAM Action | Description |
| --- | --- | --- |
| ListDatasets | `cms:ListDatasets` | List datasets in a workspace |
| GetDataset | `cms:GetDataset` | Get dataset details and schema |
| CreateDataset | `cms:CreateDataset` | Create a new dataset |
| UpdateDataset | `cms:UpdateDataset` | Update dataset description |
| DeleteDataset | `cms:DeleteDataset` | Delete a dataset |
| ExecuteQuery | `cms:ExecuteQuery` | Execute a query against a dataset |

## Minimum Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:ListDatasets",
        "cms:GetDataset",
        "cms:CreateDataset",
        "cms:UpdateDataset",
        "cms:DeleteDataset",
        "cms:ExecuteQuery"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-Only Policy

For users who only need to list, inspect, and query datasets:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:ListDatasets",
        "cms:GetDataset",
        "cms:ExecuteQuery"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- All actions are scoped to the CMS service (`cms:*`).
- Resource-level authorization is supported. Replace `"*"` with specific workspace ARNs to restrict scope.
- Attach the policy to the RAM user or role used by the `aliyun` CLI profile.
