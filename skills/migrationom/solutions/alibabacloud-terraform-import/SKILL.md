---
name: alibabacloud-terraform-import
description: This skill should be used when the user asks to "导入阿里云资源到 Terraform", "terraform import 阿里云", "将现有云资源纳入 Terraform 管理", "阿里云资源迁移 Terraform", "生成 terraform state", "import alicloud resources", "阿里云 IaC 迁移", "阿里云 Terraform 导入", or needs to manage existing Alibaba Cloud resources with Terraform. Guides users step-by-step through environment check, authentication, resource discovery, HCL generation, state import, validation, and dependency graph. Supports both one-time migration and incremental sync.
version: 0.1.0
---

# Alibaba Cloud Resource Terraform Import Wizard

Step-by-step guide to import existing resources under an Alibaba Cloud account into local Terraform management. Automatically performs environment checks, resource discovery, HCL generation, state import, etc. Users only need to confirm at key decision points.

Two modes are supported:
- **One-time migration**: Complete Phase 1-9 end to end
- **Incremental sync**: When a Terraform working directory already exists, jump directly to incremental sync mode

## Resource Support Scope

- **Theoretical scope**: Any resource in the alicloud provider that has a Read method (i.e., can read state from the cloud). Most resources can be imported directly via the `terraform import` command or `import` blocks (Terraform 1.5+); a few resources without an Importer can be imported by manually constructing tfstate, but this requires exact matching of the provider's state structure and carries some risk. Check support status at `https://registry.terraform.io/providers/aliyun/alicloud/latest/docs`.
- **Pre-built resources**: ~50 common resource types (networking, compute, storage, databases, load balancing, DNS, RAM, ACK, FC) with verified API discovery commands, HCL templates, and import ID formats in `references/`
- **Beyond pre-built scope**: Will look up provider docs on the fly to provide commands and templates; accuracy depends on documentation content; users should verify before executing

---

## Command Format Requirements

**All aliyun CLI commands must use plugin mode (lowercase-hyphenated format). CamelCase command names and parameter names are prohibited.** Violating this rule will cause parameter errors or call failures.

**Example (correct plugin-mode format):**
```bash
aliyun vpc describe-vpcs --biz-region-id cn-shanghai --page-size 50
```

**Parameter conversion rules:**
- **Region**: Prefer `--biz-region-id` (business parameter, corresponds to the API's RegionId); `--region` (framework parameter, controls endpoint region) should only be used when the API's RegionId is optional
- **Pagination**: `--page-size` (not PageSize)
- **Others**: Convert CamelCase parameter names to lowercase-hyphenated (VpcId -> `--vpc-id`, InstanceIds -> `--instance-ids`). Use `aliyun <product> <command> --help` to confirm
- **OSS**: Use `aliyun ossutil ls oss://` exclusively

---

## Phase 1: Environment Check

Run the following commands to detect the environment:

```bash
echo "=== aliyun CLI ===" && aliyun --version 2>&1 || echo "NOT_INSTALLED"
echo "=== terraform ===" && terraform --version 2>&1 || echo "NOT_INSTALLED"
echo "=== python3 ===" && python3 --version 2>&1 || echo "NOT_INSTALLED"
echo "=== OS ===" && uname -s 2>&1
```

Automatically handle missing tools based on output:
- aliyun CLI missing (macOS): Run `brew install aliyun-cli`
- aliyun CLI missing (Linux): Run `curl -sSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz && sudo mv aliyun /usr/local/bin/`
- terraform missing (macOS): Run `brew tap hashicorp/tap && brew install hashicorp/tap/terraform`
- terraform missing (Linux): Direct user to https://developer.hashicorp.com/terraform/install for manual installation (requires root)

Once all tools are ready, proceed to Phase 2.

**Configure aliyun CLI AI-Mode:**

All aliyun CLI commands must have AI-Mode configured so Alibaba Cloud can identify AI invocation scenarios and provide optimized support. Before executing any aliyun CLI command, run:

```bash
# Enable AI-Mode (required)
aliyun configure ai-mode enable

# Set User-Agent identifier (required)
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-terraform-import"

# Update plugins to latest version (recommended)
aliyun plugin update
```

All subsequent aliyun CLI commands will automatically carry AI-Mode and User-Agent identifiers. See the "Command Format Requirements" section above for command formatting rules.

**Disable AI-Mode (when the session ends or if needed):**
```bash
aliyun configure ai-mode disable
```

---

## Phase 2: Authentication Configuration

This Skill relies on the Alibaba Cloud default credential chain for authentication, supporting the following methods (by priority):
1. Environment variables (ALICLOUD_ACCESS_KEY / ALICLOUD_SECRET_KEY) — **highest priority**
2. aliyun CLI configuration file (~/.aliyun/config.json)
3. ECS RAM role (only when running on ECS)

**Important**: The Terraform alicloud provider and aliyun CLI each read credentials independently, both prioritizing environment variables. When environment variables and CLI profile point to different accounts, environment variables take precedence.

**Verify authentication:**

Verify identity via the default credential chain (without explicitly passing AK/SK):

```bash
aliyun sts get-caller-identity 2>&1
```

Analyze the output:
- Confirm AccountId and UserId, record Region
- **If the credential source is unexpected** (e.g., environment variables and CLI profile point to different accounts), inform the user of the credential conflict and suggest unifying credential configuration before retrying

If an error occurs, prompt the user to:
- Check whether credentials are configured (via `aliyun configure` or environment variables)
- Check permissions (requires ReadOnlyAccess or corresponding resource Describe permissions)
- Refer to `references/ram-policies.md` for required permissions
---

## Phase 3: Working Directory Initialization

Ask the user for the following information:
- Target working directory path (default `~/alicloud-terraform`)
- Target Region (confirm if already inferred from Phase 2, otherwise ask)
- Whether a Terraform working directory already exists (skip this Phase if so)

After user confirmation, automatically complete the following:

1. Create working directory and `.import/` subdirectory (for storing intermediate artifacts)
2. Generate `provider.tf` in the target directory (refer to `examples/provider.tf`), replacing the region default with the user-confirmed Region. The provider block must include `configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-terraform-import"` for UA tracking
3. Run `terraform init` in the target directory
4. Analyze init output, confirm provider download succeeded
5. **(Optional enhancement)** Run `terraform providers schema -json`, extract fields ending in `_id` or `_ids` from all resources to build a **reference field whitelist** for Phase 6. If schema output is too large causing parse timeout, skip this step; Phase 6 will fall back to static dependency rules for reference resolution
6. **(Optional enhancement)** Call `iacservice list-resource-types` (paginate to get all), replace the `ALIYUN` prefix in the `resourceType` field with `ACS` to build a `terraformResourceType <-> ResourceCode` bidirectional mapping table, written to `.import/resource-type-mapping.json` for use in Phase 4/5/6. If the call fails or insufficient permissions, fall back to the static mapping table in `references/resource-hub-api.md`. **Skipping this step does not affect the core import flow**, only affects ResourceCenter API resource type conversion
7. Inform user that initialization is complete, proceed to Phase 4

---

## Phase 4: Resource Discovery

**Step 0 — Query ResourceCenter Supported Resource Types (execute first)**

Run `aliyun resourcecenter list-resource-types` to get the list of resource types supported by API A (search-resources) and API B (list-resource-relationships), cache for use in this Phase and Phase 5. See `references/resource-hub-api.md` for details.

If the call fails or insufficient permissions, skip Step 0 and use native product APIs for resource discovery throughout.

**Step 1 — Discover Resources**

For each target resource type, choose discovery method by the following priority:
1. If the resource type is in API A's support list -> Use API A (search-resources) for batch query, see `references/resource-hub-api.md`
2. Otherwise -> Fall back to native product API commands in `references/api-commands.md`

If the user needs to discover resource types not in `references/api-commands.md`:
- First check provider docs (`https://registry.terraform.io/providers/aliyun/alicloud/latest/docs`) to determine support:
  - Has `Import` section -> Supports `terraform import`, proceed normally
  - No `Import` section but provider supports the resource -> Can import via manual tfstate construction; inform user of risks before proceeding
  - Provider does not support the resource at all -> Clearly inform that import is not possible
- After confirming support, check aliyun CLI docs (`https://help.aliyun.com/document_detail/110244.html`) or corresponding product API docs for discovery commands

Execute the appropriate commands, collect output, and generate a resource discovery report summarizing counts and ID lists by type.

**Empty discovery results handling:**

If a resource type (e.g., NAT Gateway) returns empty results but the user expects them to exist, proactively investigate:
- Confirm whether the resource is in a different Region
- Confirm whether the current credentials have Describe permission for that resource
- Confirm whether the resource has been released (can check audit logs)
- Inform user that discovery results don't match expectations, ask for confirmation before continuing

---

## Phase 5: Select Import Scope and Depth

Present the resource discovery report and ask the user:
- Import all or select specific resource types?
- Filter by VPC scope?
- Filter by Tag?
- **Import depth strategy**:
  1. Import only discovered resources (no related resource queries, depth=0)
  2. Import one level of related resources (depth=1)
  3. Import complete dependency tree (depth=unlimited, recommended)

**Build Resource Dependency Graph (based on depth strategy)**

Based on the user's chosen depth strategy:

**Depth=0 (import only discovered resources):**
- Skip API B calls
- Directly use static dependency rules from `references/dependency-rules.md` to sort Phase 4 discovered resources
- Generate import order

**Depth=1 (import one level of related resources):**
- For each resource discovered in Phase 4, if its type is in API B's support list -> Call API B (list-resource-relationships) to get directly related resources
- Do not recursively call API B for returned related resources
- Merge discovered resources and one-level related resources, topologically sort the resource graph, generate import order

**Depth=unlimited (import complete dependency tree, recommended):**
- From Phase 4 discovered resources, identify root resources with no parent dependencies (VPC, OSS Bucket, DNS domains, RAM users, etc.)
- For each root resource, if its type is in API B's support list -> Call API B to get related resources
- Recursively call API B for related resources until no new resources appear (new resource set == empty set)
- For resource types not supported by API B -> Fall back to static dependency rules in `references/dependency-rules.md`
- Merge all relationship trees, topologically sort the resource graph, generate import order

**Fallback static import order (when API B is unavailable):**
```
Layer 0: VPC, OSS Bucket (no dependencies)
Layer 1: VSwitch, Security Group, EIP (depend on VPC)
Layer 2: NAT Gateway, SLB (depend on VPC + VSwitch)
Layer 3: ECS Instance (depends on VSwitch + Security Group)
Layer 4: Disk (depends on ECS)
Layer 5: RDS, Redis, MongoDB (depend on VSwitch)
Layer 6: DNS Record (depends on Domain)
```

For detailed dependency rules, refer to `references/dependency-rules.md`.

---

## Phase 6: Generate Terraform HCL Code

Process resources in batches by type. For each resource type:

1. Execute detail retrieval commands (JSON format)
2. Parse JSON, generate corresponding .tf files and write to working directory

One file per resource type, filename format: `<product>_<resource_type>.tf`:

```
vpc_vpcs.tf
vpc_vswitches.tf
vpc_security_groups.tf
vpc_eips.tf
vpc_nat_gateways.tf
ecs_instances.tf
ecs_disks.tf
oss_buckets.tf
rds_instances.tf
kvstore_instances.tf
dds_instances.tf
slb_load_balancers.tf
alidns_domains.tf
alidns_records.tf
```

Refer to `references/terraform-patterns.md` for HCL code templates and `examples/` for examples.

**Cross-Resource Reference Resolution (three-layer strategy)**

When generating HCL for each resource, determine for each field value whether to replace with a terraform resource address, using the following priority:

1. **API B relationship first**: If the resource was discovered via API B (list-resource-relationships), its parent or related resources are already determined. Combined with the reference field whitelist extracted in Phase 3, find type-matching `_id` fields in the current resource and directly replace with the corresponding terraform resource address. The relationship is definitive, no guessing needed.

2. **Whitelist + mapping table dual-match fallback**: For resources not covered by API B, if the field name is in the Phase 3 reference field whitelist and the field value has a corresponding entry in the resource ID mapping table, replace with terraform resource address.

3. **dependency-rules.md static rules fallback**: For edge cases not covered by the above two layers (composite IDs, reference fields not ending in `_id`, etc.), refer to static rules in `references/dependency-rules.md`.

**Resource ID Mapping Table**

After generating each resource block, immediately append a record to the mapping table:

```
<cloud resource ID>  ->  <terraform resource address>
# Example:
vpc-bp1xxx   ->  alicloud_vpc.vpc_prod_main
vsw-bp1aaa   ->  alicloud_vswitch.vsw_prod_a
sg-bp1xxx    ->  alicloud_security_group.sg_web
```

Write the mapping table to `.import/id-mapping.json` for use in subsequent phases.

**Other key principles:**
- Resource names use `<type>_<name>` format (e.g., `alicloud_vpc.vpc_prod_main`)
- Password/secret fields use variables (`var.db_password`)
- Preserve original tags

---

## Phase 7: Import State

Based on the topological sort generated in Phase 5, generate the complete list of `terraform import` commands, present to user for confirmation, then execute in batches.

**Batch 1 — Network foundation:**
```bash
terraform import alicloud_vpc.vpc_<name> <vpc-id>
terraform import alicloud_vswitch.vsw_<name> <vsw-id>
terraform import alicloud_security_group.sg_<name> <sg-id>
```

**Batch 2 — Network ancillary:**
```bash
terraform import alicloud_nat_gateway.nat_<name> <nat-id>
terraform import alicloud_eip_address.eip_<name> <eip-id>
```

**Batch 3 — Compute:**
```bash
terraform import alicloud_instance.ecs_<name> <instance-id>
terraform import alicloud_disk.disk_<name> <disk-id>
```

**Batch 4 — Storage:**
```bash
terraform import alicloud_oss_bucket.bucket_<name> <bucket-name>
```

**Batch 5 — Database:**
```bash
terraform import alicloud_db_instance.rds_<name> <db-id>
terraform import alicloud_kvstore_instance.redis_<name> <redis-id>
terraform import alicloud_mongodb_instance.mongo_<name> <mongo-id>
```

**Batch 6 — Load Balancing:**
```bash
terraform import alicloud_slb_load_balancer.slb_<name> <slb-id>
```

**Batch 7 — DNS:**
```bash
terraform import alicloud_dns_domain.domain_<name> <domain-name>
```

After each batch, analyze output and handle common errors:
- `ResourceNotFound`: Resource ID is incorrect, re-verify
- `PermissionDenied`: Need Describe permission for the corresponding resource
- `already managed`: Resource already in state, skip
- ID format error: Refer to import format in `references/resource-types.md`

---

## Phase 8: Validation

Execute the following commands to validate import results:

```bash
# List all resources in state
terraform state list 2>&1

# Run plan, target is No changes
terraform plan -refresh=true 2>&1
```

Analyze plan output:
- `No changes` -> Validation passed, proceed to Phase 9
- Has diff -> Analyze the cause, refer to common diff fix patterns in `references/terraform-patterns.md`, provide fix recommendations and inform user, execute fix after user confirmation

Common diff causes:
- Tag format mismatch (need to adjust tags syntax in HCL)
- Password fields cannot be read from API (use `ignore_changes` to ignore)
- Computed field differences (add `lifecycle { ignore_changes = [...] }`)
- Default value differences (explicitly set values matching the cloud)

---

## Phase 9: Resource Relationship Graph

Execute the following commands to generate a resource relationship graph:

```bash
# Export state JSON
terraform show -json > .import/tf_state.json 2>&1

# Extract dependencies
python3 -c "
import json, sys
with open('.import/tf_state.json') as f:
    state = json.load(f)
resources = state.get('values', {}).get('root_module', {}).get('resources', [])
print(f'Total resources: {len(resources)}')
for r in resources:
    deps = r.get('depends_on', [])
    if deps:
        for d in deps:
            print(f'  {d} --> {r[\"address\"]}')
" 2>&1
```

Based on output, generate a text-format resource relationship graph (tree structure) showing:
- Network layer -> Compute layer -> Data layer dependency chains
- Security group cross-cutting references
- Load balancer backend binding relationships

Refer to `examples/dependency-graph.txt` for example format.

---

## Incremental Sync Mode

Use this mode when a Terraform working directory already exists. Automatically detects three types of changes:

**1. Detect new resources (exist in cloud, not in state):**

Execute the following commands to compare state and cloud ID lists:
```bash
# ECS example
terraform state list | grep alicloud_instance
aliyun ecs describe-instances --biz-region-id $REGION --page-size 100 \
  --output cols=InstanceId rows=Instances.Instance 2>&1
```

Compare the two lists, find the difference set, generate HCL + import commands for new resources, inform user for confirmation before executing.

**2. Detect deleted resources (exist in state, not in cloud):**

Run existence checks for each resource in state; if API returns empty, execute:
```bash
terraform state rm alicloud_instance.<name>
```

**3. Detect configuration drift:**

Execute the following command to detect drift:
```bash
terraform plan -refresh=true 2>&1
```

For detailed incremental sync procedures, refer to `references/incremental-sync.md`.

---

## References

- `references/resource-types.md` — Complete resource type mapping table (20+ resource types)
- `references/terraform-patterns.md` — HCL code templates + common diff fixes
- `references/state-management.md` — terraform state command reference
- `references/api-commands.md` — aliyun CLI command quick reference (native product API fallback path)
- `references/dependency-rules.md` — Resource dependency layers and import order (API B fallback path)
- `references/resource-hub-api.md` — ResourceCenter API guide (list-resource-types / search-resources / list-resource-relationships)
- `references/incremental-sync.md` — Detailed incremental sync procedures
