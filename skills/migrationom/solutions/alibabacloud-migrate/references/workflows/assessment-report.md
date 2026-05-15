# Phase 3: Assessment & Approval

**Input**: `.migration-report/alibabacloud-mapped-resources.json`  
**Output**: `.migration-report/assessment-report.md` + **User approval**

Generate a mapping assessment report for user review, then wait for approval before proceeding.

---

## Input Validation (Entry Gate)

Before proceeding, verify `alibabacloud-mapped-resources.json` satisfies:

- Top level: `migration_id`, `source_platform`, `target_platform`, `source_region`, `target_region`, `resource_mappings` all present
- Each mapping has: `source_resource` (full Phase 1 resource), `target_resources` (array), `notes`
- `source_resource` includes `discovery_method`
- `target_resources` is non-empty array; each has `id`, `type`, `category`, `properties`, `dependencies`

If any condition fails, return to Phase 2 to fix.

---

## Step 1: Generate Assessment Report

Write `.migration-report/assessment-report.md` with the following structure:

### Report Structure

```markdown
# Migration Assessment Report

## Summary

Source: {platform} ({source_region}) → Target: Alibaba Cloud ({target_region})
Resources: {N} source → {M} target | {K} need confirmation

## Resource Mapping

### {Category} ({source_count} → {target_count})
| # | Source | → Target | Notes |
|---|--------|----------|-------|
| 1 | source_type.name | target_type.name | |
| 2 | ⚠️ source_type.name | target_type.name | inferred, need confirmation |

(repeat for each category)

## ⚠️ Requires Your Attention

| Resource | Issue |
|----------|-------|
| ... | ... |
```

### Rules

- **Resource Mapping table must list ALL resources** — no omissions, no "... and N more"
- Group by category, show `(source_count → target_count)` per group
- Mark resources with `discovery_method: "inferred"` or `"from_description"` with `⚠️`
- For 1:N splits, list all targets comma-separated in one row
- Resources with no standalone target equivalent: show `—` in Target column with explanation in Notes
- **"Requires Your Attention" section** collects all items where:
  - `notes` is non-empty (architecture changes, manual steps, splits)
  - `discovery_method` is `inferred` or `from_description` (need user confirmation)

---

## Step 2: User Approval (HITL Gate)

**Default behavior** — pause for user confirmation:

1. After generating the report, **STOP execution**
2. Output the approval prompt below
3. Wait for explicit user approval before moving to Phase 4
4. On approval, write `.migration-report/migration-state.json` with `approval_status: "approved"` and `current_phase: "phase3-approved"`

**Approval prompt**:
```
📊 Migration assessment complete — see `.migration-report/assessment-report.md`

Key findings:
- [N] source resources → [M] target resources
- ⚠️ [K] items need your attention: [brief list]

Approve and proceed to generate Terraform code? Reply "approved" or describe changes needed.
```

**Exception**: If the user has explicitly requested to skip confirmation (e.g., "无需确认直接生成", "不用审批"), skip only the approval wait, not the assessment artifact. Still generate `assessment-report.md`, then set `approval_status: "approved"` and `current_phase: "phase3-approved"` in `.migration-report/migration-state.json` before proceeding to Phase 4.

### Required Approval State

Before Phase 4 starts, `.migration-report/migration-state.json` must contain:

```json
{
  "current_phase": "phase3-approved",
  "approval_status": "approved",
  "approval_source": "user_reply | initial_prompt",
  "user_confirmations": [
    {
      "source": "user_reply | initial_prompt",
      "intent": "approved | pre-approved",
      "confirmed_at": "<timestamp>"
    }
  ]
}
```

`current_phase` alone is not enough. Phase 4 must refuse to start unless `approval_status` is exactly `"approved"`.
