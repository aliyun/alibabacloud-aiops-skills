# Related Commands: alibabacloud-aes-ack-pod-performance-profiling

This skill uses the `aliyun` CLI to call SysOM, CS, and STS APIs. All non-system commands **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling`. System commands (`configure`, `version`, `plugin`) **MUST NOT** use the `--user-agent` flag.

---

## Diagnosis Phase

| Product | API (plugin-mode) | API Version | CLI Command | Description |
|---------|-------------------|-------------|-------------|-------------|
| cs    | `describe-cluster-detail`             | 2015-12-15 | `aliyun cs GET /clusters/<cluster_id>` (ROA path form, plugin-mode compliant) | Get ACK cluster details (region, state, name) |
| cs    | `create-cluster-vpc-endpoint-connection`| 2015-12-15 | (SDK only) `.sysom-sdk-venv/bin/python scripts/create-cluster-vpc-endpoint-connection.py --region <region> --cluster-id <cluster_id> --dry-run false` | Create VPC endpoint connection for cluster (CLI does NOT support; SDK is mandatory) |
| sysom | `initial-sysom`                       | 2023-12-30 | `aliyun sysom initial-sysom --check-only false --source aes-skills` | Initialize SysOM role authorization |
| sysom | `invoke-diagnosis`                    | 2023-12-30 | `aliyun sysom invoke-diagnosis --service-name ocd --channel ecs --params '<JSON>'` | Invoke ACK Pod diagnosis (params must include `product: "ACK"`) |
| sysom | `get-diagnosis-result`                 | 2023-12-30 | `aliyun sysom get-diagnosis-result --task-id <task_id>` | Poll diagnosis result |
| sts   | `get-caller-identity`                  | 2015-04-01 | `aliyun sts get-caller-identity` | Obtain account UID for diagnosis target field |

## Fixed Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `--service-name` | `ocd` | Diagnosis type (intelligent diagnosis) |
| `--user-agent` | `AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling` | Must be appended to all non-system commands (cs, sysom, sts). Do NOT pass this flag to system commands `configure`, `version`, or `plugin`. |
| `product` (params) | `ACK` | Product type for ACK Pod diagnosis |
