# RAM Permission Policies

This skill mainly relies on 14 explicit `eflo` actions (no wildcard grants), plus 4 read-only `vpc` / `ecs` actions used only by the create-cluster form's resource prefetch. It does **not** need any `bss` action.

## Permission Sets

The actions are grouped into **4 permission sets** by usage frequency:

| Permission Set | # Actions | Covered Workflows | Risk |
|---|---|---|---|
| **Read-Only** | 8 | All query scenarios | None |
| **Create-Form Prefetch (vpc/ecs read-only)** | 4 | VPC / vSwitch / security group / key pair dropdowns of the create-cluster form | None |
| **Cluster Lifecycle** | 3 | Cluster create (incl. task polling) / delete (synchronous) | High (includes `DeleteCluster`) |
| **Tagging & Resource Group** | 3 | Tag / untag / change resource group | Medium |

## Read-Only Policy (8 actions)

For: read-only agents / monitoring / patrol scripts.

```json
{
  "Version": "1",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "eflo:ListClusters",
      "eflo:DescribeCluster",
      "eflo:DescribeRegions",
      "eflo:ListClusterNodes",
      "eflo:ListMachineTypes",
      "eflo:DescribeNodeType",
      "eflo:ListImages",
      "eflo:ListTagResources"
    ],
    "Resource": "*"
  }]
}
```

## Create-Form Prefetch Policy (4 actions, vpc/ecs read-only)

For: resource dropdown prefetch of the create-cluster form (step 1: VPC / key pairs; step 2: vSwitches / security groups).

```json
{
  "Version": "1",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "vpc:DescribeVpcs",
      "vpc:DescribeVSwitches",
      "ecs:DescribeSecurityGroups",
      "ecs:DescribeKeyPairs"
    ],
    "Resource": "*"
  }]
}
```

## Cluster Lifecycle Policy (3 actions)

```json
{
  "Version": "1",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "eflo:CreateCluster",
      "eflo:DeleteCluster",
      "eflo:DescribeTask"
    ],
    "Resource": ["acs:eflo:*:*:cluster/*"]
  }]
}
```

⚠️ `DeleteCluster` is irreversible. For production accounts, tighten `Resource` to a concrete `cluster/{ClusterId}`.

## Tagging & Resource Group Policy (3 actions)

```json
{
  "Version": "1",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "eflo:TagResources",
      "eflo:UntagResources",
      "eflo:ChangeResourceGroup"
    ],
    "Resource": ["acs:eflo:*:*:cluster/*"]
  }]
}
```

## Full Access Policy (dev/test only)

Wildcard actions are forbidden by convention; enumerate all 14 `eflo` actions explicitly instead:

```json
{
  "Version": "1",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "eflo:ListClusters",
      "eflo:DescribeCluster",
      "eflo:DescribeRegions",
      "eflo:ListClusterNodes",
      "eflo:ListMachineTypes",
      "eflo:DescribeNodeType",
      "eflo:ListImages",
      "eflo:ListTagResources",
      "eflo:CreateCluster",
      "eflo:DeleteCluster",
      "eflo:DescribeTask",
      "eflo:TagResources",
      "eflo:UntagResources",
      "eflo:ChangeResourceGroup"
    ],
    "Resource": "*"
  }]
}
```

## ARN Templates

| Resource Type | ARN Template |
|---|---|
| Cluster (concrete) | `acs:eflo:{regionId}:{accountId}:cluster/{ClusterId}` |
| Cluster (wildcard) | `acs:eflo:{regionId}:{accountId}:cluster/*` |
| Global read-only (regions / machine-types / images) | `*` |

## Per-Action Detail

### Read-Only (8)

| Action | Resource ARN | Type |
|---|---|---|
| `eflo:ListClusters` | `acs:eflo:{region}:{acct}:cluster/*` | List |
| `eflo:DescribeCluster` | `acs:eflo:{region}:{acct}:cluster/{ClusterId}` | Read |
| `eflo:DescribeRegions` | `*` | Read |
| `eflo:ListClusterNodes` | `acs:eflo:{region}:{acct}:cluster/{ClusterId}` | List |
| `eflo:ListMachineTypes` | `*` | List |
| `eflo:DescribeNodeType` | `*` | Read |
| `eflo:ListImages` | `*` | List |
| `eflo:ListTagResources` | `acs:eflo:{region}:{acct}:*` | List |

### Cluster Lifecycle (3)

| Action | Resource ARN | Risk | Notes |
|---|---|---|---|
| `eflo:CreateCluster` | `acs:eflo:{region}:{acct}:cluster/*` | None | ⏳ Async, returns `TaskId` |
| `eflo:DeleteCluster` | `acs:eflo:{region}:{acct}:cluster/{ClusterId}` | **High** | ⚠️ Irreversible |
| `eflo:DescribeTask` | `*` | None | Poll task to terminal state |

### Tagging & Resource Group (3)

| Action | Resource ARN | Risk | Notes |
|---|---|---|---|
| `eflo:TagResources` | `acs:eflo:{region}:{acct}:cluster/{ClusterId}` | Low | Synchronous |
| `eflo:UntagResources` | `acs:eflo:{region}:{acct}:cluster/{ClusterId}` | Low | Synchronous; `--all` and `--tag-key` are mutually exclusive |
| `eflo:ChangeResourceGroup` | `acs:eflo:{region}:{acct}:cluster/{ClusterId}` | Medium | Synchronous; affects billing aggregation |

## Applying a Policy

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. **Permissions → Policies → Create Policy**, choose **Script** mode, and paste any JSON above
3. Name it (suggested `Lingjun-{ReadOnly|Lifecycle|NodeGroup}`) → submit
4. **Identities → Users / Roles** → **Add Permissions** on the target identity and pick the policy just created
5. Wait 1-2 minutes for propagation

## Permission Failure Troubleshooting

| Response | Meaning | Handling |
|---|---|---|
| `Forbidden` / `NoPermission` / HTTP 403 | Missing policy for that action | Add a policy per the [Per-Action Detail](#per-action-detail) table |
| `Forbidden.RAM` | RAM user disabled or policy not yet effective | Check user status in the RAM console |
| `InvalidAccount.PermissionDenied` | Parent-account / RAM-user relationship issue | Check the RAM user's parent account |

## Security Recommendations

1. **Least privilege**: never grant wildcard `eflo` actions in production; distribute the 3 scoped sets instead
2. **Tighten resources**: use a concrete `cluster/{ClusterId}` ARN for `DeleteCluster`
3. **Condition elements**: add `acs:SourceIp` / `acs:CurrentTime` constraints on high-risk actions
4. **MFA**: enable MFA for sub-accounts holding the Cluster Lifecycle set
5. **Audit**: enable ActionTrail and watch `DeleteCluster` / `ChangeResourceGroup`
6. **Environment isolation**: use separate sub-accounts for dev / staging / production

## 📖 References

- [Alibaba Cloud RAM docs](https://www.alibabacloud.com/help/ram)
- [RAM Policy syntax](https://www.alibabacloud.com/help/ram/policy-syntax-and-structure)
- [eflo-controller OpenAPI](https://api.aliyun.com/api/eflo-controller/2022-12-15)
