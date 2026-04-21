# RAM Policies — DataWorks Data Governance Tag Management

## Permission Summary

| Product | RAM Action | Resource Scope | API | Description |
|---------|-----------|----------------|-----|-------------|
| DataWorks | dataworks:CreateDataAssetTag | * | CreateDataAssetTag | Create a data asset tag key |
| DataWorks | dataworks:UpdateDataAssetTag | * | UpdateDataAssetTag | Update a data asset tag key/values |
| DataWorks | dataworks:ListDataAssetTags | * | ListDataAssetTags | Query the data asset tag list |
| DataWorks | dataworks:TagDataAssets | * | TagDataAssets | Bind tags to data assets |
| DataWorks | dataworks:UnTagDataAssets | * | UnTagDataAssets | Unbind tags from data assets |
| DataWorks | dataworks:ListDataAssets | * | ListDataAssets | Query the data asset list |

## RAM Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:CreateDataAssetTag",
        "dataworks:UpdateDataAssetTag",
        "dataworks:ListDataAssetTags",
        "dataworks:ListDataAssets"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:TagDataAssets",
        "dataworks:UnTagDataAssets"
      ],
      "Resource": "*"
    }
  ]
}
```

## Minimal Policy (Read-Only)

Use this policy if only querying the tag list and data asset list is required:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:ListDataAssetTags",
        "dataworks:ListDataAssets"
      ],
      "Resource": "*"
    }
  ]
}
```

## Minimal Policy (Bind/Unbind Only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:ListDataAssetTags",
        "dataworks:ListDataAssets",
        "dataworks:TagDataAssets",
        "dataworks:UnTagDataAssets"
      ],
      "Resource": "*"
    }
  ]
}
```

## How to Apply

1. Log in to the [RAM Console](https://ram.console.aliyun.com/policies)
2. Create a custom policy and paste the JSON above
3. Attach the policy to the target RAM user or role
4. Permissions take effect immediately
