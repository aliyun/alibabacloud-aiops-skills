---
name: alibabacloud-migrate
description: >
  Migrate cloud resources from AWS/Azure to Alibaba Cloud. Use when users want to
  "move to Alibaba Cloud", ask what Alibaba Cloud services replace their AWS/Azure setup,
  or need ready-to-deploy Alibaba Cloud Terraform code. Outputs: migration assessment
  report, modular Terraform code, step-by-step migration guide. Code generation only —
  no deployment, data migration, or DNS cutover.
---

# Cloud Migration to Alibaba Cloud

**Supported sources**: AWS (Terraform/natural language), Azure (Terraform/natural language)  
**Output**: Terraform only (modular, production-ready), migration assessment report, step-by-step migration guide  
**Not covered**: CloudFormation/ARM templates, runtime configuration


## Output Structure

The migration process generates a complete `.migration-report/` directory with all deliverables:

```
.migration-report/
├── migration-state.json          # Migration progress tracker (for resuming work)
├── input-resources.json          # Parsed source infrastructure (from Phase 1)
├── assessment-report.md          # Comprehensive migration analysis
├── migration-guide.md            # Step-by-step guide with verification & scripts
└── terraform/                    # Production-ready Terraform code
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── versions.tf
    ├── terraform.tfvars.example
    ├── README.md
    └── modules/                  # Reusable modules (dynamically generated)
        └── <module_name>/
            ├── main.tf
            ├── variables.tf
            ├── outputs.tf
            └── versions.tf
```

**Note**: Modules are dynamically generated based on actual resources (e.g., network, compute, storage, database).

### Migration State Tracking

The `migration-state.json` file tracks progress through each phase:

```json
{
  "migration_id": "migration-20240320-1234",
  "started_at": "2024-03-20T10:00:00Z",
  "updated_at": "2024-03-20T10:30:00Z",
  "source_platform": "aws",
  "current_phase": "phase2-resource-mapping",
  "completed_phases": [
    {
      "phase": "phase1-discovery-and-analysis",
      "completed_at": "2024-03-20T10:15:00Z"
    }
  ],
  "source_files": ["terraform/main.tf", "terraform/variables.tf"],
  "resource_count": 45,
  "resource_summary": { "compute": 12, "networking": 18, "storage": 8, "database": 5, "other": 2 },
  "user_confirmations": []
}
```

**Purpose**: Resume interrupted migrations. Always check this file first to continue from the last completed phase. Phase 3 includes `approval_status` field (values: `approved` | `rejected` | `pending`). Phase 4 includes `validation_status` field (values: `passed` | `skipped` | `failed`).

## Migration Phases

**⚠️ CRITICAL**: Phases **MUST** be executed in sequential order. Each phase depends on the previous phase's output. **Never skip or reorder phases.**

**Pre-approval flag**: During Phase 1, detect whether the initial user prompt contains a pre-approval signal such as "直接生成不需要确认", "不用审批", "auto-approve", or "skip approval". Record this intent in `migration-state.json.user_confirmations`. This skips only the Phase 3 approval wait; Phase 3 must still generate `assessment-report.md` and set `approval_status: "approved"` before Phase 4.

| Phase | Input → Output | Reference |
|-------|----------------|-----------|
| **1. Discovery** | **Terraform files OR natural language description** → `input-resources.json` | [discovery-and-analysis.md](references/workflows/discovery-and-analysis.md) |
| **2. Mapping** | `input-resources.json` → `alibabacloud-mapped-resources.json` | [resource-mapping.md](references/workflows/resource-mapping.md) |
| **3. Assessment & Approval** | Mapped resources → `assessment-report.md` + **User approval required** | [assessment-report.md](references/workflows/assessment-report.md) |
| **4. Terraform** | Mapped resources + approval → `terraform/` directory<br>**⚠️ CRITICAL: Code MUST be generated in `.migration-report/terraform/`**<br>**⚠️ CRITICAL: MUST run `terraform validate`, or record `validation_status: "skipped"` when Terraform CLI/provider download is unavailable** | [code-migration.md](references/workflows/code-migration.md) |
| **5. Migration Guide** | Assessment + Terraform → `migration-guide.md` | [migration-guide.md](references/workflows/migration-guide.md) |

### Phase 1 Discovery & Output Contract

Files first. Natural language description mode is allowed only after the user explicitly confirms it. Output: `.migration-report/input-resources.json` (missing any required field = Phase 1 incomplete).

**File discovery strategy**: Scan the workspace for `.tf` files using glob or directory listing. Check the user's prompt for path hints. If no `.tf` files are found after scanning, **STOP Phase 1 immediately** and output: "未找到源 Terraform 文件，请提供准确路径或确认是否使用自然语言描述模式". **NEVER set `input_mode` to `description` or continue generating `input-resources.json` without explicit user confirmation.**

| Level | Required Fields | Constraints |
|-------|----------------|-------------|
| Top-level | `source_platform`, `source_regions`, `input_mode`, `resources` | `input_mode` ∈ {files, description, hybrid}; files → `from_hcl`/`from_state`, description → `from_description`, hybrid → per-resource |
| Each resource | `id`, `type`, `category`, `region`, `discovery_method`, `source_file`, `properties`, `dependencies` | `discovery_method` ∈ {from_hcl, from_state, from_description, inferred}; `dependencies` is array, IDs must exist in resources or start with `module.`; data source `id` starts with `data.`; preserve original `count`/`for_each` structure instead of expanding it unless `.tfstate` contains concrete instances |
| If backend exists | `state_backend` | Contains `source_type`, `source_config`, `target_type`, `target_config` |
| If variables are referenced | `variables` | Record referenced variables. Unresolved values stay as `var.<name>`; propagate `sensitive = true` only when declared by source. |

### Phase 3: User Approval Gate

**🚨 HARD BLOCK — cannot be bypassed:**

1. Generate `assessment-report.md`
2. **STOP and output** a summary with an explicit approval question (see [assessment-report.md](references/workflows/assessment-report.md) for format)
3. **DO NOT** write `approval_status: "approved"` to `migration-state.json` yourself. Only the user's explicit reply counts.
4. Phase 4 must verify `migration-state.json` has `approval_status: "approved"` before starting. If missing or `"pending"`, refuse and re-prompt.

**⚠️ Exception — User pre-approval in initial prompt:**

If the user's **initial migration request** contains pre-approval signals (explicit phrases like "直接生成不需要确认", "直接帮我生成不需要再问我确认", "auto-approve", "skip approval", or any equivalent instruction to bypass the approval gate), the Agent MUST:

1. Detect this intent during Phase 1 or before Phase 3
2. **Still generate** `assessment-report.md` in Phase 3 — skip only the approval wait, not the assessment artifact
3. Write `approval_status: "approved"` and `current_phase: "phase3-approved"` to `migration-state.json` with a record:
   ```json
   "user_confirmations": [
     {
       "source": "initial_prompt",
       "intent": "pre-approved",
       "confirmed_at": "<timestamp>"
     }
   ]
   ```
4. Mark in the output: "📊 Assessment complete — automatically proceeding per your pre-approval."
5. Proceed directly to Phase 4

**Rationale**: The approval gate exists to prevent unintended code generation. When the user explicitly opts out in their first message, respecting that intent is the correct behavior. The assessment report is still generated for audit and Phase 5 reference.

**Violation**: Proceeding without real user approval OR without detected pre-approval invalidates the migration.

### Phase 4 Special Requirements

**🚨 CANNOT SKIP**: Read `references/workflows/code-migration.md`; Phase 4 is NOT complete until these checks pass:

1. **Entry gate** — Phase 1-3 artifacts exist and `.migration-report/migration-state.json` has `approval_status: "approved"`.
2. **Resource gate** — Resource types come from `references/mappings/` and are checked against `references/mappings/alicloud-provider-deprecations.md` plus the provider catalog/public deprecation source when available.
3. **Output contract** — Terraform files are under `.migration-report/terraform/`, preserve source layout, and include `main.tf`, `variables.tf`, `outputs.tf`, and `versions.tf`.
4. **Provider contract** — `versions.tf` contains:
   ```hcl
   configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-migrate"
   ```
   `variables.tf` declares `variable "region" { default = "<target_region>" }`; provider and resources use `var.region`.
5. **Generation contract** — Required OSS backend, source trace comments, unresolved variables, and credential hygiene follow the Phase 4 workflow.
6. **Post-generation checks** — Generated artifacts contain no deprecated/wrong resources, invalid topology, undeclared variables, placeholders, or inline credentials.
7. **Validation** — Run `terraform init && terraform validate` in `.migration-report/terraform/`; must return `Success!`
   - **Environment unavailable**: If `terraform` is not installed, provider download times out, or registry/network access is unavailable, mark `validation_status: "skipped"` in `migration-state.json`, write the reason, and continue to Phase 5. **NEVER mark as `"passed"` without actually running validate.**
   - On pass or environment-unavailable skip, update `migration-state.json`; on validation failure, fix and re-run before Phase 5.

### Phase 5 Validation Status Handling

Phase 5 may run when Phase 4 has `validation_status: "passed"` or `"skipped"`.

- If `"passed"`: write normal deployment steps.
- If `"skipped"`: generate `migration-guide.md` and include a visible validation note: `Terraform validation: SKIPPED (<reason from migration-state.json>)`. The guide must tell the user to run `terraform init -backend=false && terraform validate` before deployment.
- If `"failed"` or missing: return to Phase 4 and fix validation first.

## Execution Rules

**For each phase**:
1. Check `migration-state.json` to resume from last completed phase
2. Read the phase-specific reference document
3. Verify all prerequisite files exist
4. Execute phase following reference doc step-by-step
5. Update `migration-state.json` with completion status
6. Verify no placeholders (TODO/FIXME/TBD) before proceeding

**⚠️ Stop on any error** - ask user for guidance before continuing.


## References

All references are linked inline throughout this document. Key directories:
- `references/workflows/` — Per-phase workflow documents (discovery → mapping → assessment → terraform → guide)
- `references/mappings/` — Service mapping documents (AWS/Azure → Alibaba Cloud)
