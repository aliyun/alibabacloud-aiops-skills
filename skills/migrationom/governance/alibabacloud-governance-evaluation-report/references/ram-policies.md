# RAM Policies

## Required Permissions

The following RAM permissions are required to use the Governance Center evaluation features.

### Minimum Required Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "governance:ListEvaluationMetadata",
        "governance:ListEvaluationResults",
        "governance:ListEvaluationMetricDetails"
      ],
      "Resource": "*"
    }
  ]
}
```

## System Policy

Alternatively, attach the system policy:

- **AliyunGovernanceReadOnlyAccess** - Read-only access to Governance Center

## Permission Details

| API Action | Permission | Description |
|------------|------------|-------------|
| ListEvaluationMetadata | `governance:ListEvaluationMetadata` | Query check item definitions |
| ListEvaluationResults | `governance:ListEvaluationResults` | Query evaluation results |
| ListEvaluationMetricDetails | `governance:ListEvaluationMetricDetails` | Query non-compliant resource details |
