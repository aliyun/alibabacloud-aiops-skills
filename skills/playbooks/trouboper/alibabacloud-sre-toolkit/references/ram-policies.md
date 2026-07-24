# RAM Policies

This document lists the RAM permissions required by the **alibabacloud-sre-toolkit** Skill. The **diagnostic/inspection workflow** is **read-only** -- no cloud resource write operations are performed during diagnosis. All remediation steps are output as text for manual execution by the user. The onboarding configuration phase (first-time setup) includes two **user-triggered** write actions (`CreateDigitalEmployee` / `DeleteDigitalEmployee`), which are clearly separated from the diagnostic workflow below.

## STAROps Related Permissions

STAROps is the primary diagnostic engine for this Skill. The following permissions are required for session creation and streaming queries:

| Action | Purpose | Invocation Method |
|--------|---------|-------------------|
| `starops:CreateThread` | Create diagnostic session Thread (reuse Thread context) | Via `scripts/starops_manager.py create-thread` |
| `starops:CreateChat` | Initiate SSE streaming diagnostic query | Via `scripts/starops_manager.py chat` |
| `starops:ListDigitalEmployees` | Enumerate digital employees under the account during onboarding (read-only/List) | Via `scripts/starops_manager.py list-employees` |
| `starops:GetDigitalEmployee` | Get single digital employee details for auxiliary confirmation (read-only/Get) | Via `scripts/starops_manager.py get-employee` |
| **[WARNING]** `starops:CreateDigitalEmployee` | Create STAROps digital employee -- **onboarding-only, user-triggered write action** (not part of diagnostic workflow) | Via `scripts/starops_manager.py create-employee` |
| **[WARNING]** `starops:DeleteDigitalEmployee` | Delete STAROps digital employee -- **onboarding-only, user-triggered write action** (not part of diagnostic workflow) | Via `scripts/starops_manager.py delete-employee` |
| `sts:GetCallerIdentity` | Resolve account UID from selected profile credentials during onboarding (read-only) | Via `aliyun` CLI |

> STAROps product info: Product `StarOps`, API Version `2026-04-28`, Endpoint `starops.cn-beijing.aliyuncs.com` (see [starops-api.md](starops-api.md)).

## Read-Only Diagnostic API Permissions

> **[WARNING] Permission Holder**: The permissions below are for the **STAROps digital employee's RAM role** (managed by the STAROps service), **not** for the user's own RAM identity. The user's identity only needs the STAROps permissions listed above (`starops:CreateThread` / `starops:CreateChat` / etc.) plus `sts:GetCallerIdentity`. Users do **NOT** need to grant these cloud product permissions to their own RAM identity.

During diagnosis, STAROps digital employees read the status, metrics, and configuration of target cloud resources. The following table lists the **minimum specific permissions** for common diagnostic scenarios (health inspection, incident response, capacity planning, security audit). All permissions are strictly **read-only**:

| Service | Minimum Permissions | Description |
|---------|-------------------|-------------|
| ECS | `ecs:DescribeInstances`, `ecs:DescribeInstanceStatus`, `ecs:DescribeDisks`, `ecs:DescribeSecurityGroups`, `ecs:DescribeNetworkInterfaces` | Instance, disk, and network interface status |
| RDS | `rds:DescribeDBInstances`, `rds:DescribeDBInstanceAttribute`, `rds:DescribeDBInstancePerformance`, `rds:DescribeSlowLogs`, `rds:DescribeParameters` | Database instance health, performance, and parameters |
| SLB | `slb:DescribeLoadBalancers`, `slb:DescribeLoadBalancerAttribute`, `slb:DescribeListeners`, `slb:DescribeHealthStatus` | Classic load balancer status and backend health |
| ALB | `alb:ListLoadBalancers`, `alb:GetLoadBalancerAttribute`, `alb:ListListeners`, `alb:GetListenerAttribute` | Application load balancer status and configuration |
| VPC | `vpc:DescribeVpcs`, `vpc:DescribeVSwitches`, `vpc:DescribeRouteTables`, `vpc:DescribeRouteTableList`, `vpc:DescribeEipAddresses` | Network topology and routing |
| CMS | `cms:DescribeMetricList`, `cms:DescribeMetricLast`, `cms:DescribeAlertRules`, `cms:DescribeSystemEventAttribute`, `cms:GetMetricData` | Monitoring metrics and alert rules |
| SLS | `log:GetProject`, `log:ListProject`, `log:GetLogStore`, `log:GetLogs`, `log:ListLogStores` | Log project access and queries |

> **[Resource Scoping Recommendation]**: For production environments, scope these permissions to specific resources via the `Resource` field in the RAM policy (e.g., `"Resource": "acs:ecs:cn-beijing:*:instance/i-bp1xxx"`) instead of `"Resource": "*"`. This further enforces least-privilege access.
>
> **[Extending for specialized scenarios]**: The above list covers common diagnostic scenarios. If a specialized diagnostic requires additional cloud product APIs not listed here, add only the specific read-only permissions needed (following the `Describe*` / `List*` / `Get*` naming pattern). Refer to [Alibaba Cloud OpenAPI Explorer](https://api.alibabacloud.com/) for the exact API names per product. **Never grant write operation permissions (e.g., `Create*` / `Delete*` / `Modify*` / `Update*`)**.

---

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
