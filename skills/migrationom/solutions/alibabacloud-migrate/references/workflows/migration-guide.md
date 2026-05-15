# Phase 5: Generate Migration Guide

**Input**: `.migration-report/alibabacloud-mapped-resources.json`, `.migration-report/terraform/`  
**Output**: `.migration-report/migration-guide.md`

Generate a deployment guide for the Terraform code produced in Phase 4.

---

## Input Validation (Entry Gate)

Before proceeding, verify:

- `.migration-report/terraform/` exists with `.tf` files
- Phase 4 `validation_status` is `"passed"` or `"skipped"` in `.migration-report/migration-state.json`
- `versions.tf` contains `configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-migrate"`

If Phase 4 `validation_status` is `"failed"` or missing, return to Phase 4 and complete the validate → fix loop before proceeding.

If Phase 4 `validation_status` is `"skipped"`, continue and write a visible note near the top of `migration-guide.md`:

```markdown
> Terraform validation: SKIPPED ({validation_skip_reason})
>
> Run `terraform init -backend=false && terraform validate` in `.migration-report/terraform/` before deployment.
```

---

## Guide Structure

### 1. Code Architecture

Describe the generated Terraform code structure:

- File organization and what each file contains
- Resource dependencies (which resources depend on which)
- Variables that need to be filled in
- Outputs provided

**Example**:
```markdown
## Code Architecture

### File Structure
```
.migration-report/terraform/
├── versions.tf    — Provider config (alicloud, region variable)
├── variables.tf   — 8 variables (region, vpc_cidr, db_password, ...)
├── vpc.tf         — VPC + 3 VSwitches + NAT Gateway
├── ecs.tf         — 2 ECS instances + Security Group
├── rds.tf         — RDS MySQL instance + DB connection
└── outputs.tf     — VPC ID, ECS IPs, RDS endpoint
```

### Resource Dependencies
```
alicloud_vpc.main
  └── alicloud_vswitch.public_a, .private_a
        ├── alicloud_instance.web (public)
        └── alicloud_db_instance.main (private)
```

### Variables to Configure
| Variable | Description | Example |
|----------|-------------|---------|
| region | Target region | cn-hangzhou |
| vpc_cidr | VPC CIDR block | 10.0.0.0/16 |
| db_password | RDS root password | (sensitive) |
```

### 2. Deployment Steps

Concrete steps to deploy the generated code:

```markdown
## Deployment Steps

### Step 1: Configure Variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with actual values

### Step 2: Initialize
terraform init

### Step 3: Review Plan
terraform plan
# Review the planned changes

### Step 4: Apply
terraform apply
# Type "yes" to confirm
```

If Phase 4 validation was skipped, insert an extra validation step before `terraform plan`:

```markdown
### Step 3: Validate
terraform init -backend=false
terraform validate
```

### 3. Notes

- Resources marked with `# NOTE: This resource was inferred` — verify these exist as expected
- Architecture differences from source (extracted from mapping `notes`)
- Any manual steps needed post-apply (e.g., data migration, DNS updates)

---

## Generation Rules

1. **Use actual file names and resource names** from `.migration-report/terraform/`
2. **List all variables** that need user input — don't leave them guessing
3. **Only include sections relevant to the generated code** — no generic cloud migration advice
4. **Keep it actionable** — every section should tell the user what to do
5. **Preserve validation status** — if validation was skipped, the guide must state `Terraform validation: SKIPPED` and include the exact skip reason from `migration-state.json`
6. **No credential examples** — if authentication is mentioned, tell users to configure provider credentials outside Terraform with `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and optional `ALIBABA_CLOUD_SECURITY_TOKEN`; do not include assignments, sample values, deprecated `ALICLOUD_*` names, or `terraform.tfvars` credential variables.
