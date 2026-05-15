# Phase 2: Resource Mapping

**Input**: `.migration-report/input-resources.json` (from Phase 1)  
**Output**: `.migration-report/alibabacloud-mapped-resources.json`

Map each source resource to Alibaba Cloud equivalent, including property transformation.

---

## Input Validation (Entry Gate)

Before proceeding, verify `input-resources.json` satisfies:

- Top level: `source_platform`, `source_regions`, `input_mode`, `resources` all present
- Each resource has: `id`, `type`, `category`, `region`, `discovery_method`, `source_file`, `properties`, `dependencies`
- `discovery_method` is one of: `from_hcl`, `from_state`, `from_description`, `inferred`
- `dependencies` is an array; referenced IDs exist in resources list or start with `module.`
- Unresolved `var.` references are allowed only when the referenced variable is recorded in top-level `variables`
- Data source `id` starts with `data.`

If any condition fails, return to Phase 1 to fix.

---

## Step 1: Load Input & Mapping Index

Read `.migration-report/input-resources.json` → Identify `source_platform` → Open mapping index:
- **AWS**: [AWS → Alibaba Cloud](../mappings/aws/index.md)
- **Azure**: [Azure → Alibaba Cloud](../mappings/azure/index.md)

---

## Step 2: Map Resources

For each resource:

1. **Look up mapping**: `source_platform` + `type` → Find alicloud equivalent(s) from mapping index or provider docs

   **If resource not in mapping index**: Search provider docs to understand the resource, then find the Alibaba Cloud equivalent.

   | Platform | Terraform Provider Docs |
   |----------|------------------------|
   | AWS | https://registry.terraform.io/providers/hashicorp/aws/latest/docs |
   | Azure | https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs |
   | Alibaba Cloud | https://registry.terraform.io/providers/aliyun/alicloud/latest/docs |

   **1:N mapping**: One source resource may map to multiple target resources (e.g., `aws_db_instance` → `alicloud_db_instance` + `alicloud_db_connection`). List all in `target_resources[]`.

2. **Select target region**: If user has not specified, ask. If already specified, use directly.

3. **Determine resource name**: Reuse the source resource's name part. E.g., `aws_vpc.main` → `alicloud_vpc.main`, `aws_eks_cluster.this` → `alicloud_cs_managed_kubernetes.this`. For 1:N splits, append suffix (e.g., `alicloud_db_instance.main`, `alicloud_db_connection.main_conn`).

4. **Transform properties**: Map source attributes to target attributes based on provider documentation and `references/mappings/` (e.g., `instance_type: t3.medium` → `instance_type: ecs.g6.large`, `engine_version: "8.0"` → `engine_version: "8.0"`).

   `target_resources[].properties` is the contract Phase 4 uses to generate Terraform. It must contain the concrete Terraform arguments needed to avoid ambiguous or deprecated generation. Do not leave service selection to Phase 4 if the mapping docs already decide it.

   Required property rules:
   - Include type-driving attributes when mapping docs require them, such as `address_type`, `zone_mappings`, `vswitch_ids`, `assume_role_policy_document`, `engine`, and `engine_version`.
   - Preserve `count`/`for_each` when the target supports the same repeated-resource structure.
   - Never place deprecated arguments or wrong service generations in `target_resources`; fix them in Phase 2.

5. **Map dependencies**: Replace source resource references with corresponding target references using the determined names.

6. **Propagate `discovery_method`**: Copy from source resource unchanged. For `inferred` or `from_description` resources, add note in `notes` field.

7. **Map `state_backend`** (if exists): Map backend type and config fields to OSS:

   | Source Backend | Target Backend |
   |---------------|---------------|
   | `s3` | `oss` |
   | `azurerm` | `oss` |

   | Source Field | Target Field |
   |-------------|-------------|
   | `bucket` | `bucket` |
   | `key` | `prefix` |
   | `region` | `region` (use target region) |
   | `dynamodb_table` | (drop — OSS has built-in locking) |

8. **Propagate `variables`** (if exists): Copy top-level `variables` from `input-resources.json` to `alibabacloud-mapped-resources.json` unchanged. Preserve `var.<name>` references in mapped target properties when the original source property used an unresolved variable. Do not resolve, default, or rewrite sensitive variables during mapping.

**Mapping-specific required/forbidden properties live in `references/mappings/`; check those tables before writing `target_resources[]`.**

---

## Step 3: Generate Output

Write `.migration-report/alibabacloud-mapped-resources.json`:

```json
{
  "migration_id": "aws-eks-to-alibabacloud-20260325",
  "source_platform": "aws",
  "target_platform": "alibabacloud",
  "source_region": "ap-southeast-1",
  "target_region": "ap-southeast-1",
  "mapping_completed_at": "2026-03-25T01:00:00Z",
  "variables": {
    "db_password": {
      "sensitive": true,
      "has_default": false,
      "reason": "source variable is sensitive"
    }
  },
  "resource_mappings": [{
    "source_resource": { /* Full resource from Phase 1 */ },
    "target_resources": [{
      "id": "alicloud_vpc.main",
      "type": "alicloud_vpc",
      "category": "networking",
      "properties": { "cidr_block": "10.0.0.0/16" },
      "dependencies": []
    }],
    "notes": ""
  }]
}
```

### Example

**Input (Phase 1):**
```json
{
  "source_platform": "aws",
  "source_regions": ["ap-southeast-1"],
  "variables": {},
  "resources": [
    {
      "id": "aws_vpc.main",
      "type": "aws_vpc",
      "category": "networking",
      "region": "ap-southeast-1",
      "discovery_method": "from_hcl",
      "source_file": "main.tf",
      "properties": { "cidr_block": "10.0.0.0/16" },
      "dependencies": []
    },
    {
      "id": "aws_eks_cluster.this",
      "type": "aws_eks_cluster",
      "category": "compute",
      "region": "ap-southeast-1",
      "discovery_method": "from_hcl",
      "source_file": "eks.tf",
      "properties": { "version": "1.28" },
      "dependencies": ["aws_vpc.main"]
    }
  ]
}
```

**Output:**
```json
{
  "migration_id": "aws-eks-to-alibabacloud-20260325",
  "source_platform": "aws",
  "target_platform": "alibabacloud",
  "source_region": "ap-southeast-1",
  "target_region": "ap-southeast-1",
  "mapping_completed_at": "2026-03-25T01:00:00Z",
  "variables": {},
  "resource_mappings": [
    {
      "source_resource": {
        "id": "aws_vpc.main",
        "type": "aws_vpc",
        "category": "networking",
        "region": "ap-southeast-1",
        "discovery_method": "from_hcl",
        "source_file": "main.tf",
        "properties": { "cidr_block": "10.0.0.0/16" },
        "dependencies": []
      },
      "target_resources": [{
        "id": "alicloud_vpc.main",
        "type": "alicloud_vpc",
        "category": "networking",
        "properties": { "cidr_block": "10.0.0.0/16" },
        "dependencies": []
      }],
      "notes": ""
    },
    {
      "source_resource": {
        "id": "aws_eks_cluster.this",
        "type": "aws_eks_cluster",
        "category": "compute",
        "region": "ap-southeast-1",
        "discovery_method": "from_hcl",
        "source_file": "eks.tf",
        "properties": { "version": "1.28" },
        "dependencies": ["aws_vpc.main"]
      },
      "target_resources": [{
        "id": "alicloud_cs_managed_kubernetes.this",
        "type": "alicloud_cs_managed_kubernetes",
        "category": "compute",
        "properties": {
          "version": "1.28",
          "vswitch_ids": [
            "alicloud_vswitch.private_a.id",
            "alicloud_vswitch.private_b.id"
          ]
        },
        "dependencies": [
          "alicloud_vpc.main",
          "alicloud_vswitch.private_a",
          "alicloud_vswitch.private_b"
        ]
      }],
      "notes": "AWS EKS → Alibaba Cloud ACK. Architecture change: workloads need redeployment."
    }
  ]
}
```
