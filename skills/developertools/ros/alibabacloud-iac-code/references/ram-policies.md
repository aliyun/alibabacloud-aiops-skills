# RAM permissions

## Permission model

The packaged bridge and Runtime-cache commands do not call Alibaba Cloud APIs and require no RAM permission.
Infrastructure jobs run through the authenticated iac-code Runtime. Grant the Runtime credential only the exact
Alibaba Cloud actions needed by the user's approved task. Template generation, conversion, and offline validation
also require no cloud permission.

Do not attach a product-wide `FullAccess` policy or use an action wildcard. Read-only discovery should use exact
`Describe`, `List`, or `Get` actions. Create, update, and delete actions must be added only after the corresponding
plan and cleanup scope have been approved. Where an API supports resource-level authorization, scope `Resource` to
the target account, region, stack, or resource ARN rather than all resources.

## Common workflow actions

These are workflow-specific examples, not one policy to grant in full.

| Workflow | Read actions | Write actions when explicitly approved |
|---|---|---|
| Caller preflight | `sts:GetCallerIdentity` | None |
| ROS template and stack operations | `ros:ValidateTemplate`, `ros:GetTemplateParameterConstraints`, `ros:PreviewStack`, `ros:GetStack`, `ros:ListStackResources` | `ros:CreateStack`, `ros:UpdateStack`, `ros:DeleteStack` |
| VPC and vSwitch operations | `vpc:DescribeVpcs`, `vpc:DescribeVSwitches`, `vpc:DescribeVpcAttribute`, `vpc:DescribeVSwitchAttributes` | `vpc:CreateVpc`, `vpc:CreateVSwitch`, `vpc:DeleteVSwitch`, `vpc:DeleteVpc` |
| Security-group operations | `ecs:DescribeZones`, `ecs:DescribeSecurityGroups`, `ecs:DescribeSecurityGroupAttribute` | `ecs:CreateSecurityGroup`, `ecs:AuthorizeSecurityGroup`, `ecs:AuthorizeSecurityGroupEgress`, `ecs:DeleteSecurityGroup` |

Other resource types require their own exact product/action pairs. Never infer that the actions above authorize ECS
instances, databases, public IP addresses, gateways, load balancers, disks, or any other unrelated resource.

## Failure handling

If the Runtime returns `Forbidden`, `Forbidden.RAM`, `NoPermission`, or a similar authorization error, report the
exact denied action and request ID when available. Do not retry with broader credentials, print credentials, or
bypass the bridge with a direct CLI call. Ask for the narrow missing action only when continuing the approved task
requires it.
