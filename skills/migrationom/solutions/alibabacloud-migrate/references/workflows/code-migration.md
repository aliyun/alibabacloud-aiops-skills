# Phase 4: Generate Terraform Code

**Input**: `.migration-report/alibabacloud-mapped-resources.json`  
**Output**: `.migration-report/terraform/`

Generate production-ready Terraform configuration based on the mapped resources.

---

## Input Validation (Entry Gate)

Before proceeding, verify:

1. `.migration-report/input-resources.json` exists from Phase 1
2. `.migration-report/assessment-report.md` exists from Phase 3
3. `.migration-report/migration-state.json` exists with `approval_status: "approved"` and `current_phase: "phase3-approved"` or later
4. `.migration-report/alibabacloud-mapped-resources.json` satisfies:
   - Each mapping has: `source_resource`, `target_resources` (non-empty array), `notes`
   - Each `target_resource` has: `id`, `type`, `category`, `properties`, `dependencies`
   - `source_resource` includes `discovery_method`

If `approval_status` is missing, `"pending"`, or `"rejected"`, stop and return to Phase 3 for explicit approval. Do not treat `current_phase` alone as approval.

If other conditions are not met, report which phase needs to be completed first.

---

## Pre-HCL Gate

**Before writing any `resource` block**, verify each `target_resource.type` against mappings, the provider catalog, and provider docs.

### Provider Catalog

Use these sources in order:

1. `references/mappings/` for source-to-target selection and required companion resources.
2. `references/mappings/alicloud-provider-deprecations.md` for migration-specific deprecated resources and invalid aliases.
3. `../alibabacloud-terraform-deploy/references/alicloud-providers.md` or the published deprecated-resource source when available.

For every `target_resource.type`:

1. Confirm the type is selected by a mapping or `target_resources`.
2. Confirm the type is not listed as deprecated or invalid.
3. When the provider catalog is available, confirm an exact `resource` row exists.
4. If a replacement is listed, update the mapping/code to use it. If no replacement is listed, stop and remap.

If the provider catalog is unavailable, continue with `references/mappings/` plus provider docs, and record the missing catalog in `.migration-report/terraform/validation.log`.

### Provider Docs

**URL pattern**: strip the `alicloud_` prefix, then fetch:
`https://raw.githubusercontent.com/aliyun/terraform-provider-alicloud/master/website/docs/r/<stripped_name>.html.markdown`

**Example**: `alicloud_vpc` → strip → `vpc` → fetch `.../r/vpc.html.markdown`

### Checks

1. **Exists** — HTTP 200 (never guess resource names)
2. **Not deprecated** — Search for `**DEPRECATED:**` or `Deprecated since`. If found, use the replacement named in the warning.
3. **Schema reviewed** — Read `## Argument Reference` for required args

### Error Handling

| Scenario | Action |
|----------|--------|
| Missing from catalog or 404 Not Found | Report to user: "Resource `alicloud_XXX` does not exist in provider" |
| Deprecated | Switch to the replacement resource named in the warning |
| Network error | Retry once, then ask user to verify |

---

## Code Generation

### File Organization

```
.migration-report/terraform/
├── versions.tf        # Provider configuration
├── variables.tf       # Variable declarations
├── outputs.tf         # Output definitions
└── main.tf (or split by source structure)
```

**Structure rule**: If source project has multiple files (e.g., `vpc.tf`, `eks.tf`), generate corresponding target files (e.g., `vpc.tf`, `ack.tf`). If source is a single `main.tf`, generate a single `main.tf`.

### Generation Rules

**1. Provider configuration (REQUIRED in `versions.tf`)**:

Use the provider version constraint already established in this skill or mapping references. Do not block code generation on querying the latest registry version. Avoid fixed upper-bound guidance here; the generated `required_providers` block must include an `alicloud` version constraint, but the exact constraint should follow the current skill reference or project convention.

```hcl
terraform {
  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = ">= 1.200.0"
    }
  }
}

provider "alicloud" {
  region               = var.region
  configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-migrate"
}
```

`configuration_source` belongs only in the `provider "alicloud"` block. If `terraform init` reports `configuration_source` as an unsupported argument inside a `terraform` block, move it into the provider block; do not delete it.

**If `state_backend` exists in mapped resources**, also add the OSS backend block in `versions.tf`:

```hcl
terraform {
  backend "oss" {
    bucket = "my-tf-state-alicloud"
    prefix = "prod/terraform.tfstate"
    region = "<state_backend.target_config.region>"
  }
}
```

Use `state_backend.target_config` for backend values. Do not hardcode a sample region; the backend block cannot reference `var.region`.

After generation, inspect `versions.tf`; if `state_backend.target_type` is `oss`, the file itself must contain `backend "oss"` with concrete `bucket`, `prefix`, and `region` values. Writing this backend only in `migration-guide.md` is a Phase 4 failure.

**2. Migration comments** — link back to source:

```hcl
# Migrated from: aws_vpc.main (source: vpc.tf)
resource "alicloud_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
```

**3. Discovery method comments** — for `inferred` or `from_description` resources:

```hcl
# Migrated from: aws_launch_template.app (source: compute.tf)
# NOTE: This resource was inferred and may need verification
resource "alicloud_ecs_launch_template" "app" {
  ...
}
```

**4. Dependency handling**:

```hcl
# Direct reference
resource "alicloud_vswitch" "public" {
  vpc_id = alicloud_vpc.main.id
}

# Cross-module reference via output
module "compute" {
  vpc_id = module.network.vpc_id
}
```

**5. Credentials and variable handling**:

Never write Alibaba Cloud access keys, secret keys, Terraform credential variables, or literal credential-looking values into generated files or reports. Configure the provider without inline credentials. If authentication must be mentioned, name only the current environment variables: `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and `ALIBABA_CLOUD_SECURITY_TOKEN` for STS. Do not assign, read, or display credential values, and do not recommend deprecated `ALICLOUD_*` names.

For unresolved source variables preserved in `.migration-report/alibabacloud-mapped-resources.json.variables`, declare matching target variables:

```hcl
variable "db_password" {
  description = "Sensitive value migrated from source variable db_password"
  type        = string
  sensitive   = true
}
```

If `variables.<name>.sensitive` is `true`, set `sensitive = true`; otherwise keep normal Terraform variable semantics. Do not invent placeholder values.

---

## Post-Generation Hard Checks

Before validation, inspect generated `.tf` files and every generated text artifact (`README.md`, `migration-guide.md`, `assessment-report.md`, `terraform.tfvars.example`, execution logs) for:

1. Provider-doc and mapping compliance: no deprecated, unknown, or wrong resource types or attributes; required companion resources are present.
2. Topology compliance: HA targets use the required number of distinct zones/VSwitches.
3. Variable compliance: every `var.<name>` has a declaration; `sensitive` metadata from mapped resources is reflected.
4. Hygiene: no placeholders, inline credential assignments, Terraform credential variables, or literal AccessKey-like values such as `LTAI`.
5. Credential examples: no `access_key =`, `secret_key =`, `alicloud_access_key`, `alicloud_secret_key`, deprecated `ALICLOUD_*` guidance, shell export assignments, or sample AK/SK values in any generated artifact.

Scan the generated `.tf` declarations against `references/mappings/alicloud-provider-deprecations.md` and the provider catalog/public deprecated-resource source when available. Treat deprecated resources, invalid aliases, and catalog misses as Phase 4 failures.

If any check fails, fix the generated artifacts before continuing.

---

## Validation

### First run: fmt + init + validate

```bash
cd .migration-report/terraform/
terraform fmt -recursive
terraform init -backend=false
terraform validate -json
```

**If `terraform init` fails because the configuration is invalid** (unsupported argument, missing required argument, invalid reference), fix the generated `.tf` files and retry.

**If the validation environment is unavailable** (`terraform: command not found`, provider download timeout, registry/network unreachable, or provider installation canceled), do not mark validation as passed. Write `validation_status: "skipped"` and `validation_skip_reason` to `.migration-report/migration-state.json`, record the same reason in `.migration-report/terraform/validation.log`, and continue to Phase 5.

### Fix loop

On errors or `[DEPRECATED]` diagnostics, fix and retry:

```bash
terraform fmt -recursive && terraform validate -json
```

For each iteration:
1. Read the error/diagnostic
2. Fix the corresponding `.tf` file
3. Re-run fmt + validate

Exit when: **no errors AND no `[DEPRECATED]` diagnostics**.

| Common Error | Fix |
|-------------|-----|
| `Missing required argument` | Add missing attribute (check provider docs) |
| `Invalid reference` | Check resource name or dependency |
| `Duplicate resource` | Rename or merge |
| `Unsupported argument` | Use correct attribute name from provider docs; if `configuration_source` is under `terraform {}`, move it to `provider "alicloud"` |
| `[DEPRECATED]` diagnostic | Re-run Pre-HCL Gate for that resource, switch to replacement |

### Validation summary

After loop exits, print:

```
Files written:
<path/to/file1>
<path/to/file2>
...

Validation:
  - terraform fmt+validate: ok
  - OR: SKIPPED (Terraform CLI/provider download/network unavailable)
  - OR: FAILED (<diagnostic excerpt>)

Deprecation routing: <origin → new | None>
```

Update `migration-state.json`:

- On successful validate: `validation_status: "passed"` with `validated_at`.
- On missing Terraform CLI, provider download timeout, registry/network unreachable, or provider installation cancellation: `validation_status: "skipped"`, `validation_skip_reason`, and `validated_at`.
- On HCL configuration errors from init or validate: `validation_status: "failed"` with diagnostic summary until fixed.


---

## Completion

Proceed to Phase 5 only when `validation_status` is `"passed"` or `"skipped"`. If skipped, Phase 5 must include the skipped validation note and require the user to run `terraform init -backend=false && terraform validate` before deployment.
