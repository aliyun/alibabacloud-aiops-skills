# RAM Policies for alibabacloud-lingjun-node-diagnose

> This skill depends only on `eflo:*`; it does not involve BSS / ECS.

---

## Four permission policies (split by responsibility)

### Policy A: LingjunDiagnose-ReadOnly (read-only locator)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:ListClusters",
        "eflo:DescribeCluster",
        "eflo:ListClusterNodes",
        "eflo:ListClusterHyperNodes",
        "eflo:DescribeNode",
        "eflo:DescribeHyperNode",
        "eflo:DescribeRegions",
        "eflo:ListSyslogs"
      ],
      "Resource": "*"
    }
  ]
}
```

Applies to: viewing resource information only, extracting hardware counters, capturing system logs.

---

### Policy B: LingjunDiagnose-Submit (diagnostic read + submit)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:CreateDiagnosticTask",
        "eflo:DescribeDiagnosticResult",
        "eflo:ListDiagnosticResults"
      ],
      "Resource": "*"
    }
  ]
}
```

Applies to: submitting diagnostics, querying diagnostic results, browsing diagnostic history.

---

### Policy C: LingjunDiagnose-Repair (repair mutating)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:RebootNodes",
        "eflo:ReimageNodes",
        "eflo:StopNodes",
        "eflo:ReportNodeStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

Applies to: executing repairs (reboot / reimage / stop / hardware fault declaration).

---

### Policy D: LingjunDiagnose-FaultReport (fault report tracking)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:DescribeFaultReport",
        "eflo:ListFaultReports",
        "eflo:StopNodeDiagnostic",
        "eflo:ApproveOperation"
      ],
      "Resource": "*"
    }
  ]
}
```

Applies to: tracking the deep-diagnosis progress after a fault report (two read-only actions), stopping a fault diagnosis (`StopNodeDiagnostic`, mutating), and approving a platform-raised maintenance proposal (`ApproveOperation`, mutating). If only querying is needed without termination/approval, `eflo:StopNodeDiagnostic` / `eflo:ApproveOperation` can be removed.

---

## Least-privilege combinations for roles vs users

| Use case | Recommended policies |
|---|---|
| AI engineer monitoring node health, read-only | A |
| Troubleshooting engineer, can submit diagnostics and read results | A + B |
| SRE / operations, full handling authority | A + B + C |
| Track / stop deep diagnosis after a fault report | A + C + D (fault-report submission depends on `ReportNodeStatus` in C) |

---

## Permission failure troubleshooting

`NoPermission` / `Forbidden` / HTTP 403 -> stop the flow immediately, match the missing action against the table above, pass `RequestId` + the missing action to the user, and suggest routing to the `ram-permission-diagnose` skill so the user can complete the policy themselves.
