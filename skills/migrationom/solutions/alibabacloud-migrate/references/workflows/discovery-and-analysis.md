# Phase 1: Discovery and Analysis

**Input**: Terraform files (`.tf`, `.tfvars`, `.tfstate`) **OR explicitly confirmed** natural language description
**Output**: `.migration-report/input-resources.json`

Extract and structure all source infrastructure resources for migration planning.

---

## Step 1: Identify Input Source

Try Terraform files first. Do not fall back to natural language unless the user explicitly confirms description mode.

| Priority | What to do | Discovery Method |
|----------|-----------|------------------|
| 1 | `Glob` for `**/*.tf` and check user-provided path hints — if found, parse them | `from_hcl` / `from_state` |
| 2 | If no files are found, STOP Phase 1 and ask the user to provide an accurate path or explicitly confirm natural language description mode | none |
| 3 | Only after explicit confirmation, parse the user's infrastructure description | `from_description` |

✅ `.tf`, `.tfstate`, `.tfvars` | ❌ CloudFormation, ARM templates

---

## Step 2: Detect Source Platform

**AWS**: `provider "aws"`, resource prefix `aws_*`  
**Azure**: `provider "azurerm"`, resource prefix `azurerm_*`

**If both detected**: STOP and ask user:
> "Detected AWS ([count]) and Azure ([count]) resources. To reduce risk, migrate one platform at a time. Which first: AWS or Azure?"

Wait for selection, then parse only that platform's resources.

---

## Step 3: Parse Natural Language (explicit confirmation only)

When no `.tf` files exist and the user explicitly confirms description mode, parse the user's description to infer: `source_platform`, `source_regions`, resource `type`/`name`/`category`/`region`/`properties`/`dependencies`. Document assumptions in `resource.notes`.

Example: "AWS VPC in us-east-1 with 3 EC2 instances (t3.medium)" →
`aws_vpc.main`, `aws_instance.web_1..3` (all with `discovery_method: "from_description"`, `source_file: "user_description"`)

**Skip this step if `.tf` files are available.** If no `.tf` files are available and the user has not explicitly confirmed description mode, do not generate `input-resources.json`; stop with: "未找到源 Terraform 文件，请提供准确路径或确认是否使用自然语言描述模式".

---

## Step 4: Extract and Analyze Resources

Scan all `.tf` and `.tfstate` files, extract every resource definition with complete configuration.

**Workflow**: Scan & Extract → Classify → Categorize → Preserve Dynamic Structure → Resolve Modules → Merge

### 4.1 Scan and Extract Resources

Scan all sources, for each resource extract the following fields:

| Field | Description | Resolution |
|---|---|---|
| `id` | Resource identifier | `aws_instance.web`, `data.aws_iam_policy_document.x` |
| `type` | Resource type | `aws_instance`, `aws_vpc` |
| `discovery_method` | How the resource was found | See table below |
| `source_file` | File path where defined | `main.tf`, `modules/vpc/main.tf` |
| `region` | From provider config | Explicit `provider = aws.alias` → alias region; else default provider region |
| `properties` | Resolved attribute values | Priority: `.tfstate` attrs → `.tfvars` → non-sensitive variable defaults → preserve `var.<name>` |
| `dependencies` | Resource IDs this depends on | See dependency detection below |

#### Discovery Method

Every extracted resource must have a `discovery_method` tag. Downstream phases use it to decide handling:

| `discovery_method` | Source | Reliability | Downstream handling |
|---|---|---|---|
| `from_hcl` | Parsed from `.tf` files | Confirmed | Map directly |
| `from_state` | Extracted from `.tfstate` | Confirmed | Map directly |
| `from_description` | User natural language description | Needs confirmation | Add comment in generated code |
| `inferred` | Inferred (remote module, reference to undefined resource, etc.) | Needs confirmation | Add comment in generated code |

#### Source Formats

| Source | ID Format | Discovery Method |
|--------|-----------|------------------|
| `.tf` files | `aws_instance.web`, `module.vpc.aws_vpc.main` | `from_hcl` |
| `.tfstate` files | `{type}.{name}` from resources array | `from_state` |

`.tfstate` uses JSON v4 format:

```json
{
  "resources": [{
    "mode": "managed",
    "type": "aws_instance",
    "name": "web",
    "instances": [{
      "index_key": 0,
      "attributes": { "id": "i-0abcd", "instance_type": "t3.medium" },
      "dependencies": ["aws_subnet.public"]
    }]
  }]
}
```

- `instances[]` is an array — `count = 3` → 3 instances
- State attribute names may differ from HCL (e.g., `vpc_security_group_ids` vs `security_groups`)

#### Backend Configuration

Extract `terraform { backend {} }` block, record as `state_backend`:

```json
"state_backend": {
  "source_type": "s3",
  "source_config": { "bucket": "my-tf-state", "key": "prod/terraform.tfstate", "region": "us-east-1" },
  "target_type": "oss",
  "target_config": { "bucket": "my-tf-state-alicloud", "prefix": "prod/terraform.tfstate", "region": "<target_region>" }
}
```

Backend mapping: `s3` → `oss`, `azurerm` → `oss`

#### Variable Handling

Record source variables referenced by resources in a top-level `variables` object. This object is required when any resource property preserves a `var.<name>` reference.

Rules:

1. Resolve variables from `.tfvars` or defaults when a concrete value is available and safe to copy.
2. If a concrete value cannot be resolved, preserve resource properties as `var.<name>` and record the variable in `variables`.
3. If the source variable declares `sensitive = true`, record `sensitive: true` and propagate that flag to target Terraform variables.
4. If the source variable has no default, record `has_default: false`; missing values are not a discovery failure.
5. Do not invent placeholder values or ask for missing variable values during discovery.

Example:

```json
"variables": {
  "sql_password": {
    "sensitive": true,
    "has_default": false,
    "reason": "source variable is sensitive"
  },
  "instance_count": {
    "sensitive": false,
    "has_default": true,
    "default": 3
  }
}
```

#### Dependency Detection

Additive — check all patterns:

| Pattern | Example |
|---|---|
| Direct reference | `vpc_id = aws_vpc.main.id` |
| List/Map reference | `subnets = [aws_subnet.a.id]` |
| Explicit depends_on | `depends_on = [aws_s3_bucket.logs]` |
| Module output | `subnet_id = module.network.subnet_id` |
| For_each indexed | `aws_subnet.subnet[each.key].id` |
| Data source | `data.aws_iam_policy_document.x.json` |

**NOT dependencies**: literal strings (`"web-server"`), ARN strings (`"arn:aws:..."`), variable references (`var.xxx`).

---

### 4.2 Classify Resource Types

| Block | Example | Migration Action |
|---|---|---|
| Managed Resource | `resource "aws_instance" "web"` | **MIGRATE** → alicloud equivalent |
| Data Source | `data "aws_partition" "current"` | **EXTRACT SEMANTICS** — not a migration target |
| Policy Document | `data "aws_iam_policy_document" "..."` | **EXTRACT SEMANTICS** → build equivalent RAM policy |

Data sources use `data.` prefix in ID, their `category` inferred from usage context.

---

### 4.3 Categorize by Domain

| Category | Example Resources |
|----------|------------------|
| compute | EC2, Lambda, ECS, Fargate, EKS |
| networking | VPC, Subnet, SG, ELB/ALB/NLB, NAT Gateway, Route53, CloudFront |
| storage | S3, EBS, EFS |
| database | RDS, Aurora, DynamoDB, ElastiCache |
| messaging | SQS, SNS, EventBridge, Kinesis |
| security | IAM, KMS, Secrets Manager |
| monitoring | CloudWatch, CloudTrail |
| other | Everything else |

---

### 4.4 Preserve Dynamic Resources (Count / For_Each)

```hcl
resource "aws_instance" "web" { count = 3 }
→ aws_instance.web with properties.count = 3

resource "aws_s3_bucket" "b" { for_each = toset(["logs","assets"]) }
→ aws_s3_bucket.b with properties.for_each = "toset([...])"
```

**Rules**:
1. Preserve the original resource ID (`type.name`) and record `count` or `for_each` in `properties`.
2. Preserve expressions that depend on `each.key`, `each.value`, or `count.index` in `properties`; do not expand them into synthetic resource IDs during HCL discovery.
3. Resolve non-sensitive variable defaults when available. If a variable is sensitive or has no default, preserve the reference as `var.<name>` and include the variable declaration in generated target Terraform.
4. Only expand into concrete instances when reading `.tfstate`, because state contains the realized instance addresses and values.

---

### 4.5 Resolve Module Blocks

**Local modules**: Recurse into path, extract resources with `module.<name>.` prefix.

```hcl
module "vpc" { source = "./modules/vpc" }
→ Recurse ./modules/vpc, prefix IDs with module.vpc.
```

**Remote modules** (Registry / Git): Cannot read source, apply inference by priority:

| Priority | Source | Strategy |
|---|---|---|
| 1 | `.tfstate` | Extract `module.<name>.*` resources from state → `discovery_method: "from_state"` |
| 2 | Output references | `module.vpc.vpc_id` → infer contains `aws_vpc` → `discovery_method: "inferred"` |
| 3 | Registry name | `terraform-aws-modules/vpc/aws` → infer VPC related resources → `discovery_method: "inferred"` |
| 4 | None | Record module block only, `notes: "remote module - resources not resolved"` |

**Exception — utility modules** (e.g., `hashicorp/subnets/cidr`): Modules that only perform computation (CIDR calculation, naming, etc.) and do NOT create any provider-specific resources do not need mapping. Skip them in resource extraction — they can be reused directly or replaced with built-in functions (e.g., `cidrsubnet()`) in Phase 4.

---

### 4.6 Merge & Deduplicate

`.tf` ∪ `.tfstate` → no duplicates. When both exist for same resource, `.tfstate` values take priority.

---

## Step 5: Generate Output

Write a single JSON object to `.migration-report/input-resources.json`. All fields except `notes` and `state_backend` are mandatory; include `state_backend` when a source backend block exists:

```json
{
  "source_platform": "aws",
  "source_regions": ["us-east-1"],
  "input_mode": "files | description | hybrid",
  "variables": {
    "db_password": {
      "sensitive": true,
      "has_default": false,
      "reason": "source variable is sensitive"
    }
  },
  "state_backend": {
    "source_type": "s3",
    "source_config": { "bucket": "my-tf-state", "key": "prod/terraform.tfstate", "region": "us-east-1" },
    "target_type": "oss",
    "target_config": { "bucket": "my-tf-state-alicloud", "prefix": "prod/terraform.tfstate", "region": "<target_region>" }
  },
  "resources": [{
    "id": "aws_instance.web",
    "type": "aws_instance",
    "category": "compute",
    "region": "us-east-1",
    "discovery_method": "from_hcl | from_state | from_description | inferred",
    "source_file": "main.tf | user_description",
    "properties": {"instance_type": "t3.medium"},
    "dependencies": ["aws_vpc.main"],
    "notes": ""
  }]
}
```

For description mode: `discovery_method: "from_description"`, `source_file: "user_description"`, document inference assumptions in `notes`.
