# RAM Permissions

This Skill requires the following RAM permissions:

## Core Diagnostic (kubectl read-only, no RAM needed)

The core diagnostic flow uses only `kubectl get/describe` read operations against the ACK cluster.
No additional RAM permissions are required.

## Multi-Cluster Connection (cluster_connect.sh)

When using `cluster_connect.sh` to fetch kubeconfig for multiple ACK clusters,
the following read-only RAM permissions are required:

`cs:DescribeClusters` — List all ACK clusters under the account
`cs:DescribeClusterDetail` — Get cluster detail information
`cs:DescribeClusterUserKubeconfig` — Get cluster kubeconfig file

## Recommended Custom Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cs:DescribeClusters",
        "cs:DescribeClusterDetail",
        "cs:DescribeClusterUserKubeconfig"
      ],
      "Resource": "*"
    }
  ]
}
```

> Note: All actions listed above are read-only operations. No write permissions are required or declared.
