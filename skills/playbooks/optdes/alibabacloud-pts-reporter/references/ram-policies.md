# RAM Policies — alibabacloud-pts-reporter

> Read-only permission set required by the PTS report analyzer. All actions are
> **Get / List** — no mutation. Scope is strictly limited to PTS report data;
> no ECS / CloudMonitor permissions are required because this skill does NOT
> perform instance-level diagnostics.

---

## Minimum Required Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pts:GetPtsReportDetails",
        "pts:GetPtsSceneRunningData",
        "pts:GetPtsSceneBaseLine",
        "pts:GetJMeterReportDetails",
        "pts:GetPtsScene",
        "pts:ListPtsScene"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Action-to-Workflow Mapping

| Workflow Step | API Action | RAM Action |
|---------------|-----------|------------|
| Read past PTS native report | `GetPtsReportDetails` | `pts:GetPtsReportDetails` |
| Read past JMeter report | `GetJMeterReportDetails` | `pts:GetJMeterReportDetails` |
| Read scene baseline | `GetPtsSceneBaseLine` | `pts:GetPtsSceneBaseLine` |
| Read scene running data (if still alive) | `GetPtsSceneRunningData` | `pts:GetPtsSceneRunningData` |
| Read scene metadata | `GetPtsScene` | `pts:GetPtsScene` |
| List scenes for context lookup | `ListPtsScene` | `pts:ListPtsScene` |

---

## Why NO Mutation Permissions Here

This analyzer is strictly read-only. If the user wants to act on a finding
(re-run a scenario, adjust PTS concurrency, resize an instance), those
operations belong to other skills:

- **Re-run / modify PTS scenario** → `alibabacloud-pts-task`
- **Resize ECS instance** → `alicloud-compute-ecs`
- **Instance-level resource diagnosis (CPU/Memory/Disk/Network)** → corresponding cloud-product diagnostic skill (out of scope here)

Keeping mutation and instance-level read permissions out of this skill's RAM
footprint is intentional — it allows least-privilege deployment for
report-analysis-only roles.
