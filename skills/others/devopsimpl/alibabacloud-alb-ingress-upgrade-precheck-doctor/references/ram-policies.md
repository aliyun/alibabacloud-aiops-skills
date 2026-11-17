# RAM Permission Policies

Minimum read-only permissions required for this Skill to perform diagnosis. Every action below maps to a
command the Skill actually runs; nothing else is required.

## Policy Document

Replace `<region>`, `<account-id>` and `<cluster-id>` with your own values to scope the policy to the
cluster being diagnosed (wildcards are shown as the loosest acceptable form).

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cs:DescribeClusterAddonsVersion"
      ],
      "Resource": "acs:cs:<region>:<account-id>:cluster/<cluster-id>"
    },
    {
      "Effect": "Allow",
      "Action": [
        "alb:GetLoadBalancerAttribute",
        "alb:ListListeners",
        "alb:GetListenerAttribute",
        "alb:ListRules",
        "alb:ListLoadBalancers"
      ],
      "Resource": "acs:alb:<region>:<account-id>:loadbalancer/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "alb:ListAclEntries",
        "alb:ListAcls"
      ],
      "Resource": "acs:alb:<region>:<account-id>:acl/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "alb:ListServerGroupServers",
        "alb:ListServerGroups"
      ],
      "Resource": "acs:alb:<region>:<account-id>:servergroup/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "log:GetLogStore",
        "log:GetLogStoreLogs"
      ],
      "Resource": "acs:log:<region>:<account-id>:project/k8s-log-<cluster-id>/logstore/alb-<cluster-id>"
    }
  ]
}
```

The Skill requires the user to provide the cluster ID; account-wide cluster discovery permissions are not needed.

## Permission Details

| Service | Action | Resource scope | Used by |
|---------|--------|----------------|---------|
| CS | `cs:DescribeClusterAddonsVersion` | the diagnosed cluster | `aliyun cs describe-cluster-addons-version` (Controller version) |
| ALB | `alb:GetLoadBalancerAttribute` | load balancers | `aliyun alb get-load-balancer-attribute` |
| ALB | `alb:ListListeners` | load balancers | `aliyun alb list-listeners` |
| ALB | `alb:GetListenerAttribute` | owning load balancers | `aliyun alb get-listener-attribute` |
| ALB | `alb:ListRules` | owning load balancers | `aliyun alb list-rules` |
| ALB | `alb:ListAclEntries` | ACLs | `aliyun alb list-acl-entries` |
| ALB | `alb:ListServerGroupServers` | server groups | `aliyun alb list-server-group-servers` |
| ALB | `alb:ListLoadBalancers` / `alb:ListAcls` / `alb:ListServerGroups` | loadbalancer / acl / servergroup ARN patterns in the target region and account | `aliyun alb list-load-balancers` / `list-acls` / `list-server-groups` |
| SLS | `log:GetLogStore` | `k8s-log-<cluster-id>/alb-<cluster-id>` only | `aliyun sls get-log-store` (verify the DryRun logstore exists) |
| SLS | `log:GetLogStoreLogs` | `k8s-log-<cluster-id>/alb-<cluster-id>` only | `aliyun sls get-logs` |

## Handling Permission Errors

When a command returns `Forbidden.RAM`, `Forbidden`, `NoPermission`, `Unauthorized`, `NotAuthorized`
or `AccessDenied` (HTTP 401/403):

1. Treat it as missing read-only permission, not as a configuration drift finding.
2. In the final reply (not only in the collected script output), name the failed API and the exact action from the
   table above (for example `aliyun sls get-logs`
   denied -> `log:GetLogStoreLogs` on `k8s-log-<cluster-id>/alb-<cluster-id>`), and give the user the
   matching statement from the policy document so an account administrator can grant it.
3. Continue the diagnosis with the data that was readable, and state which conclusion is incomplete.
4. Never call RAM/STS APIs, attach policies, switch profiles or credentials, or retry with broader
   permissions; granting access is done by the user.

## Notes

- All permissions are **read-only** (Describe/List/Get). The Skill never calls create/update/delete APIs and never modifies Kubernetes resources, so no write permission is needed.
- ALB listener and forwarding-rule APIs authorize against the owning load balancer ARN, not a listener ARN. List APIs require the resource-type pattern shown above; specify the target region and account, and replace `loadbalancer/*`, `acl/*` or `servergroup/*` with known IDs wherever the API supports it.
- CS enhanced authentication documents `cs:DescribeClusterAddonsVersion` for the component-version API; its API reference also lists the legacy permission `cs:Queryk8sComponentsUpdateVersion`. If the deployed endpoint reports the latter as the denied action, replace the CS action with that exact read-only permission on the same cluster; do not grant `cs:*` or add unrelated permissions.
- SLS GetLogs maps to the RAM action `log:GetLogStoreLogs`, not `log:GetLogs`.
- References: [ALB authorization](https://help.aliyun.com/zh/slb/application-load-balancer/developer-reference/api-alb-2020-06-16-ram), [CS enhanced authentication](https://help.aliyun.com/en/ack/product-overview/ack-api-enhances-user-authentication), [CS component-version API](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-describeclusteraddonsversion), [SLS GetLogs authorization](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogs).
- The SLS statement is optional if the cluster does not deliver ALB component logs to SLS.
- Prefer a RAM role / STS profile over a long-lived AccessKey; see [cli-installation-guide.md](cli-installation-guide.md).
