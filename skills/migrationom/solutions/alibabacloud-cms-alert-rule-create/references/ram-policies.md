# RAM Permissions

Minimum permissions required by this skill. This is a **write-operation skill** that creates alert rules, contacts, and contact groups.

Only actions used in the alert creation workflow are listed.

## CMS 1.0 Alert Permissions

| Permission | Purpose | Used In |
|------------|---------|---------|
| `cms:DescribeProjectMeta` | List cloud product namespaces | Step 1/2 |
| `cms:DescribeMetricMetaList` | Query available metrics for namespace | Step 2 |
| `cms:DescribeContactGroupList` | Query existing contact groups | Step 4 |
| `cms:PutContact` | Create new alert contact | Step 4 |
| `cms:PutContactGroup` | Create new contact group | Step 4 |
| `cms:PutResourceMetricRule` | Create alert rule | Step 5 |
| `cms:DescribeMetricRuleList` | Verify rule creation | Step 6 |

## Instance Query Permissions (Optional)

Required only when listing cloud resource instances for CMS 1.0 alerts:

| Permission | Purpose | Used In |
|------------|---------|---------|
| `ecs:DescribeInstances` | List ECS instances | Step 1 |
| `rds:DescribeDBInstances` | List RDS instances | Step 1 |
| `slb:DescribeLoadBalancers` | List SLB instances | Step 1 |
