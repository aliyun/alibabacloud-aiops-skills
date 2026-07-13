# RAM Policies — MSE Nacos Inspection

This skill performs read-only operations only and requires the following minimum RAM permissions.

## Custom Policy (Recommended)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mse:QueryClusterDetail",
        "mse:ListClusters"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "arms:ListPrometheusInstances",
        "arms:GetPrometheusInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Usage

| Action | Purpose |
|--------|--------|
| `mse:QueryClusterDetail` | Query MSE instance details (ClusterName, MseVersion, etc.), used in Mode A only |
| `mse:ListClusters` | List all MSE instances in a region by region, used in region-based inspection mode |
| `arms:ListPrometheusInstances` | List Prometheus instances to obtain cloud product Prometheus instance IDs |
| `arms:GetPrometheusInstance` | Get Prometheus HTTP API public and internal addresses |
