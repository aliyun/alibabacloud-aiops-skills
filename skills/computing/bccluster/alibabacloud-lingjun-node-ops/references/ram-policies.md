# RAM Policies - Least-Privilege Sets

> 4 permission sets keyed to feature areas. Combine as needed; in production, **never** grant the union of all four to a single role.

## Set 1: Read-Only (mandatory baseline for every user)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:DescribeRegions",
        "eflo:ListClusters",
        "eflo:DescribeCluster",
        "eflo:ListClusterNodes",
        "eflo:ListClusterHyperNodes",
        "eflo:DescribeNode",
        "eflo:DescribeHyperNode",
        "eflo:ListNodeGroups",
        "eflo:DescribeNodeGroup",
        "eflo:ListMachineTypes",
        "eflo:DescribeNodeType",
        "eflo:ListImages",
        "eflo:DescribeTask",
        "eflo:ListTagResources",
        "eflo:DescribeInvocations"
      ],
      "Resource": "*"
    }
  ]
}
```

## Set 2: Power Operations (F1-F3)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:StopNodes",
        "eflo:RebootNodes",
        "eflo:ReimageNodes",
        "eflo:DescribeTask"
      ],
      "Resource": "*"
    }
  ]
}
```

## Set 3: Lifecycle Operations (F4-F8)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:ChangeNodeTypes",
        "eflo:ReportNodeStatus",
        "eflo:ApproveOperation",
        "eflo:RunCommand",
        "eflo:StopInvocation",
        "eflo:UpdateNodeGroup",
        "eflo:DescribeTask",
        "eflo:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bss:RenewInstance",
        "bss:QueryOrders"
      ],
      "Resource": "*"
    }
  ]
}
```

## Set 4: Tag & Resource Group (F9)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:TagResources",
        "eflo:UntagResources",
        "eflo:ListTagResources",
        "eflo:ChangeResourceGroup"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ram:ListResourceGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

## Common 403 errors -> policy mapping

| Error message | Missing action | Set |
|---|---|---|
| `NoPermission: eflo:StopNodes` | `eflo:StopNodes` | 2 |
| `NoPermission: eflo:ReimageNodes` | `eflo:ReimageNodes` | 2 |
| `NoPermission: eflo:ChangeNodeTypes` | `eflo:ChangeNodeTypes` | 3 |
| `Forbidden.RAM` on `RenewInstance` | `bss:RenewInstance` | 3 |
| `NoPermission: eflo:RunCommand` | `eflo:RunCommand` | 3 |
| `NoPermission: eflo:TagResources` | `eflo:TagResources` | 4 |
| `NoPermission: eflo:ChangeResourceGroup` | `eflo:ChangeResourceGroup` | 4 |

When any 403 surfaces, the Agent should:

1. Look up the missing action in the table above.
2. Show the **smallest** policy set the user must add (typically Set 1 + the relevant feature set).
3. Route to the `alibabacloud-ram-permission-diagnose` skill for deeper diagnosis.
