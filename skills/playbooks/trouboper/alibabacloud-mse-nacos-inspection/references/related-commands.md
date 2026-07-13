# Related CLI Commands — MSE Nacos Inspection

## MSE Instance Management

| Command | Description | Mode |
|---------|-------------|------|
| `aliyun mse list-clusters --page-num <N> --page-size <N> --biz-region-id <regionId> --region <regionId>` | List all MSE instances in a specified region with pagination | Mode B |
| `aliyun mse query-cluster-detail --instance-id <instanceId> --region <regionId>` | Query details of a single MSE instance | Mode A |

## ARMS Prometheus Management

| Command | Description |
|---------|-------------|
| `aliyun arms list-prometheus-instances --biz-region-id <regionId> --cluster-type cloud-product-prometheus --show-global-view false --api-version 2019-08-08 --region <regionId>` | List cloud product Prometheus instances in a specified region |
| `aliyun arms get-prometheus-instance --biz-region-id <regionId> --cluster-id <clusterId> --api-version 2019-08-08 --region <regionId>` | Get Prometheus instance details (including HTTP API address) |

## Local Utility Commands (no --user-agent required)

| Command | Description |
|---------|-------------|
| `aliyun version` | Check CLI version |
| `aliyun configure list` | Check credential configuration status |
| `aliyun configure set --auto-plugin-install true` | Enable automatic plugin installation |
| `aliyun plugin update` | Update all plugins |
