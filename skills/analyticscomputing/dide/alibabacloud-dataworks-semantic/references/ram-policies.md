# RAM Policies — DataWorks Semantic Analysis

Grant only the actions needed for the selected workflow. Never use `dataworks:*`.

## Read runs and results

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:ListSemanticJobs",
        "dataworks:ListSemanticJobRuns",
        "dataworks:GetSemanticJobDetail",
        "dataworks:GetSemanticJobLog",
        "dataworks:DownloadSemanticResults"
      ],
      "Resource": "*"
    }
  ]
}
```

## Create and run

Add only these actions when the operator must create or execute jobs:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:CreateSemanticJob",
        "dataworks:RunSemanticJob"
      ],
      "Resource": "*"
    }
  ]
}
```

## Stop a run

Add this action only when the operator must stop an active semantic run. Retain the read actions above so the Skill can resolve the exact executor and verify its final state.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:KillSemanticJob"
      ],
      "Resource": "*"
    }
  ]
}
```

The active identity must also have the required DataWorks workspace write permission for the supplied `ProjectId`. If workspace authorization denies the stop, report the permission failure.

The action names match the released `dataworks-public` 2024-05-18 operations. `Resource: "*"` is retained only because the semantic API has not published a resource-level ARN contract in the inspected CLI release; the action list itself contains no wildcard. Replace it with the documented ARN scope when DataWorks publishes resource-level authorization.

The Skill intentionally omits upload, update, delete, archive, publish, and result mutation actions. The single-file flow therefore requires an existing `FileId` or accessible URI.
