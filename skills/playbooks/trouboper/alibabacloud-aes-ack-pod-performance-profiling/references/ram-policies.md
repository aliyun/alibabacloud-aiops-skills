# RAM Policies: alibabacloud-aes-ack-pod-performance-profiling

This document lists all APIs and their corresponding RAM permissions used by the SysOM ACK Pod diagnosis skill.

---

## SysOM Permissions

| API | RAM Action | Description |
|-----|-----------|-------------|
| InitialSysom | `sysom:InitialSysom` | Initialize SysOM role authorization |
| InvokeDiagnosis | `sysom:InvokeDiagnosis` | Invoke intelligent diagnosis |
| GetDiagnosisResult | `sysom:GetDiagnosisResult` | Get diagnosis result |

## CS (Container Service) Permissions

| API | RAM Action | Description |
|-----|-----------|-------------|
| DescribeClusterDetail | `cs:DescribeClusterDetail` | Get ACK cluster details (region, state, name) |
| CreateClusterVpcEndpointConnection | `cs:CreateClusterVpcEndpointConnection` | Create VPC endpoint connection for private cluster API server access (used by `scripts/create-cluster-vpc-endpoint-connection.py`) |

---

## Minimum Permission Policy Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sysom:InitialSysom",
        "sysom:InvokeDiagnosis",
        "sysom:GetDiagnosisResult",
        "sysom:CreateClusterVpcEndpointConnection",
        "sysom:AuthDiagnosis"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cs:DescribeClusterDetail",
        "cs:CreateClusterVpcEndpointConnection",
        "cs:DescribeClusterNodes",
        "cs:DescribeClusterEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "cms:QueryMetricList",
      "Resource": "*"
    }
  ]
}
```

## Permission Tiers

| Phase | Required Permissions | Description |
|-------|---------------------|-------------|
| Diagnosis | `sysom:InitialSysom`, `sysom:InvokeDiagnosis`, `sysom:GetDiagnosisResult`, `cs:DescribeClusterDetail`, `cs:CreateClusterVpcEndpointConnection` | Minimum permissions for ACK Pod diagnosis |
