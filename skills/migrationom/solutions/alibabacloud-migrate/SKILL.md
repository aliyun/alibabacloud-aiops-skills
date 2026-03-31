---
name: alibabacloud-migrate
description: |
  Assess and migrate workloads from AWS to Alibaba Cloud. Follows a 4-phase methodology:
  Phase 1 (source architecture assessment), Phase 2 (migration plan generation), Phase 3
  (infrastructure deployment as empty shells via Terraform), Phase 4 (data and application
  migration + cutover). Covers EC2→ECS (AMI export + ImportImage), RDS→ApsaraDB (DTS),
  S3→OSS, Lambda→Function Compute FCv3, and network/DNS migration. Uses Terraform (default) for
  infrastructure provisioning and Alibaba Cloud CLI for migration-specific operations (DTS, data transfer).
  Triggers: "migrate from AWS", "AWS to Alibaba Cloud", "migrate EC2 to ECS", "migrate S3 to OSS",
  "migrate RDS to ApsaraDB", "migrate Lambda to Function Compute", "migrate Lambda to FCv3",
  "cloud migration assessment", "cross-cloud migration", "AWS migration", "ImportImage", "database migration DTS".
---

# AWS to Alibaba Cloud Migration

> This skill handles **assessment, planning, and execution** of workload migration from AWS to Alibaba Cloud.
> **Default approach**: Terraform for infrastructure provisioning; CLI for migration-specific operations (DTS, data transfer, ImportImage).

## Architecture

```
AWS (Source)              Alibaba Cloud (Target)         Tool
────────────              ─────────────────────          ────
VPC / Networking     ──→  VPC / VSwitch / SG             Terraform
EC2 Instances        ──→  ECS                            CLI (AMI export→OSS→ImportImage) + Terraform
RDS / Aurora         ──→  ApsaraDB RDS / PolarDB         CLI (DTS full+incremental) + Terraform
S3 Buckets           ──→  OSS                            CLI (ossutil/DataOnline) + Terraform
Lambda               ──→  Function Compute (FC 3.0)      Terraform + code refactor
API Gateway          ──→  API Gateway                    Terraform (OpenAPI import)
EventBridge          ──→  EventBridge                    Terraform (rule+target)
Step Functions       ──→  Serverless Workflow             Flow definition rewrite
SQS / SNS            ──→  MNS Queue / Topic              Code changes (SDK)
ECS (Container) / EKS ─→  ACK (Kubernetes)               Velero + Terraform
ECR                  ──→  ACR                            docker pull/push
DynamoDB             ──→  Tablestore                     DTS/DataX + schema rewrite
ElastiCache          ──→  Tair (Redis/Memcached)         CLI (DTS) + Terraform
MSK (Kafka)          ──→  Message Queue for Kafka         Broker config migration
Redshift             ──→  MaxCompute / AnalyticDB        DataX + SQL adaptation
Route53              ──→  Alibaba Cloud DNS              Terraform (zone+records)
CloudFront           ──→  CDN                            Terraform (origin+SSL)
ELB / ALB / NLB      ──→  SLB / ALB / NLB               Terraform
VPN Gateway          ──→  VPN Gateway                    Terraform (IPsec)
Direct Connect       ──→  Express Connect                Physical circuit setup
IAM                  ──→  RAM                            Policy syntax rewrite
Cognito              ──→  IDaaS                          User pool migration
WAF                  ──→  WAF                            Terraform (rule migration)
CloudWatch           ──→  CloudMonitor + SLS             Metric/log remapping
```

## Installation

**Step 1 — Aliyun CLI** (requires >= 3.3.1; see [references/cli-installation-guide.md](references/cli-installation-guide.md))

**Step 2 — Terraform Runtime Detection** — Run once, record result as `TERRAFORM_MODE`:

```bash
terraform version 2>/dev/null && echo "TERRAFORM_MODE=local" || echo "TERRAFORM_MODE=online"
```

- **`TERRAFORM_MODE=local`**: Use `terraform` CLI directly for all operations.
- **`TERRAFORM_MODE=online`**: Prompt user to install Terraform (`brew install terraform` / https://developer.hashicorp.com/terraform/install), or use `terraform_runtime_online.sh` as fallback. See `## Terraform Online Runtime`.

**Step 3 — Set Terraform User-Agent** — Required for all Terraform operations (both local and online modes):

```hcl
provider "alicloud" {
  region               = var.region
  configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-migrate"
}
```

## Authentication

> **CRITICAL Security Rules — NEVER violate:**
> - NEVER read, echo, or print AK/SK values
> - NEVER ask for AK/SK in conversation or command line
> - NEVER use `aliyun configure set` with literal credential values

### AWS Credentials (Phase 1 prerequisite)

```bash
aws sts get-caller-identity  # Must return AccountId before starting Phase 1.
```

> **[STOP — AWS Source Access Required for Phase 1]** Before running any scan, confirm one of the following is available:
> 1. **AWS credentials configured** — `aws sts get-caller-identity` returns a valid `AccountId`. If not, ask the user to configure credentials, then re-run the check.
> 2. **Complete AWS resource inventory provided manually** — User supplies a full description of all resources (VPC, subnets, SGs, EC2, RDS, S3, Lambda, API Gateway, EventBridge, IAM roles, etc.) that substitutes the scan output.
>
> **Do NOT start Phase 1 scans or produce any output until one of the above conditions is confirmed.**

### Alibaba Cloud Credentials (Phase 3 prerequisite)

```bash
aliyun configure list  # Must show a valid profile (AK, STS, or OAuth). STOP if none found.
```

> **[STOP — Alibaba Cloud Credentials Required for Phase 3]** If no valid profile:
> 1. Inform the user that Alibaba Cloud credentials are required before infrastructure deployment.
> 2. Suggest: obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak), configure via `aliyun configure` in a terminal **outside this session**, then return.
> 3. **Do NOT proceed to Phase 3 (Terraform apply) without verified credentials.** Phase 1-2 (assessment and planning) can proceed with AWS credentials only.

## CLI operation idempotency (DTS, ImportImage, SMC, etc.)

Terraform state and `STATE_ID` (online runtime) prevent duplicate *Terraform-managed* resources, but **Alibaba creation APIs** for DTS tasks, image import, SMC jobs, and similar may still create **new** records if invoked repeatedly with different client tokens or names.

**Agent / operator rules:**

1. **Describe / list before create:** Query existing tasks, jobs, or imports by name prefix or tags; if a matching **Succeeded** or **Running** resource exists, reuse its ID instead of creating another.
2. **Stable identifiers:** Prefer `ClientToken` / unique job names derived from a deterministic key (e.g., source server id + target region), documented in the migration runbook.
3. **Retries:** On timeout or ambiguous error, **do not** blindly re-run “create”; poll status first, then either wait, cancel, or resume per product documentation.
4. **User confirmation:** Before second creation of the same logical migration object, surface the duplicate risk and require explicit approval.

## Interaction Mode

> **[MANDATORY FIRST STEP — STOP]** Present the mode choice below and **wait for user response** before ANY other action. Do NOT read files, run scans, or begin assessment until the user has chosen a mode. This is a blocking gate.

Present this choice and wait for response:

```
Before starting the migration, choose the agent work mode:

A) Interactive mode (recommended)
   Agent asks before every significant decision. Full control over every migration detail.
   Best for: first-time migrations, complex environments, learning the process.

B) Autonomous mode
   Agent handles all low-risk decisions automatically (naming, sizing, transfer path, etc.).
   Only confirms at mandatory checkpoints: Phase 1/2 architecture review, DNS cutover,
   source decommission, instance type > ecs.g6.2xlarge.
   Each checkpoint presents [Recommended] option with reasoning; user can accept or override.
   Best for: experienced users, repeat migrations with known patterns.

Choose mode (A/B, default A — press Enter to confirm A):
```

**Interactive mode — agent confirms before acting:**

All significant decisions are presented to the user with context and a [Recommended] option. The user can accept, override, or ask for more information before proceeding. This includes:
- Resource naming, VPC CIDR, VSwitch layout
- Disk type, image format, instance type sizing
- Data transfer path selection
- Phase checkpoints (same as autonomous mode)

**Autonomous mode defaults** (all shown in Phase 2 summary; user can override):
naming `<project>-<resource>` · VPC `10.0.0.0/16` · disk `cloud_essd` · image `VHD` · instance type closest match · transfer path Option B (HK relay ECS)

**Autonomous mode — always confirm** (present [Recommended] + reasoning):
Phase 1 architecture review · Phase 2 plan review · DNS cutover (4.6) · source decommission (4.8) · instance type > ecs.g6.2xlarge

## Parameter Confirmation

> Parameters are confirmed at the **end of Phase 2** — autonomous mode as a single summary block; interactive mode one-by-one. See [references/parameter-reference.md](references/parameter-reference.md) for the full parameter table with agent defaults.

## Output Isolation

> All generated migration files MUST go in `<project-name>-alicloud/` directory (created in working directory). NEVER modify user's existing source files. If no project name provided, ask before creating the directory.

## Destructive Action Policy

> **NEVER** delete, stop, or modify AWS source resources until ALL of the following are met:
> 1. Target resources verified working — see [references/verification-method.md](references/verification-method.md)
> 2. Data integrity confirmed (checksums, row counts, object counts match)
> 3. DNS cutover complete and traffic flowing to Alibaba Cloud
> 4. 24-hour observation period passed
> 5. User explicitly approves decommissioning (Phase 4.8)

## Migration Status Tracking

> **MANDATORY**: Create `migration-status.md` from [references/migration-status-template.md](references/migration-status-template.md) at the start of Phase 1. Update after every operation: ⬜ Not Started → 🔄 In Progress → ✅ Completed / ❌ Failed. Record STATE_IDs and error details. All items in current phase must show ✅ before advancing to the next phase.

## RAM Permissions

See [references/ram-policies.md](references/ram-policies.md) for the complete per-service permission list and the recommended custom least-privilege policy.

> **[MUST]** On any permission error: read `references/ram-policies.md`, use `ram-permission-diagnose` skill, and wait for user to confirm permissions are granted before continuing.

## Terraform Online Runtime (TERRAFORM_MODE=online only)

> Skip this section when `TERRAFORM_MODE=local`. Full usage guide: [references/terraform-online-runtime.md](references/terraform-online-runtime.md)

**Rules (online mode only):**
- Consolidate all HCL into a **single** `main.tf` (IaCService requirement)
- **STATE_ID** is the deployment identity. Only the **first** apply of a new deployment runs **without** `--state-id`. After a run reaches **Applied**, **in-place updates** must use **plan → apply(plan)** (IaCService rejects `apply main.tf --state-id` on an already-Applied job).

```bash
export TF="$SKILL_DIR/scripts/terraform_runtime_online.sh"
apply_output=$($TF apply main.tf)
STATE_ID=$(echo "$apply_output" | grep '^STATE_ID=' | cut -d= -f2)
echo "STATE_ID=$STATE_ID" >> terraform_state_ids.env
# In-place change after Applied: plan then apply the plan state (same ID typically echoed twice)
plan_output=$($TF plan main.tf "$STATE_ID")
PLAN_SID=$(echo "$plan_output" | grep '^STATE_ID=' | cut -d= -f2)
$TF apply --state-id "$PLAN_SID"
# Destroy: $TF destroy "$STATE_ID"
```

**Multi-STATE_ID (production):** Use separate HCL files per resource layer (`network-main.tf`, `compute-main.tf`, etc.) and apply each independently for independent lifecycle management.

## Core Workflow

Four phases, executed **strictly sequentially**. Each phase ends with a **[CHECKPOINT — STOP]** gate. These are hard barriers — the agent MUST stop, present the checkpoint output, and wait for the user to explicitly confirm before any Phase N+1 action. Merging phases, skipping checkpoints, or proceeding without user confirmation is a critical violation.

```
Phase 1: Source Assessment  →  Phase 2: Migration Plan  →  Phase 3: Infra Deploy  →  Phase 4: Data Migration
  [STOP: Confirm AWS state]     [STOP: Confirm plan]        [STOP: Confirm infra]     [STOP: DNS cutover]
```

> **Anti-pattern — NEVER do this:** Combine multiple phases in a single response, generate Terraform code before Phase 1 checkpoint is confirmed, or execute `terraform apply` before Phase 2 plan is approved.

---

### Phase 1: Source Architecture Assessment

**Goal**: Fully understand the AWS current state. Identify migration complexity and risks. No design or planning in this phase.

1. **Discover AWS resources** — Two steps, **both mandatory**, per [references/aws-discovery-commands.md](references/aws-discovery-commands.md):
   - **Step 1 broad scan** (~30–60s): `scripts/aws-scan-region.sh <region>` — one list/describe per service, outputs `inventory.md`
   - **Step 2 deep scan** (must run after Step 1): `scripts/aws-scan-enrich.sh <region> <scan-output-dir>` — loops over each main resource for per-resource detail, outputs `inventory-deep.md`

   > **[PAUSE — AWS access unavailable: ask user before proceeding]**
   >
   > **Trigger conditions** (any one is sufficient):
   > - AWS CLI is not installed or not found on PATH
   > - Scan scripts return credential errors (`NoCredentialProviders`, `InvalidClientTokenId`, `ExpiredTokenException`, `AuthFailure`, etc.)
   > - API connectivity failures (network unreachable, timeout on all services)
   > - All service categories in `inventory.md` show "(no resources, no access, or timeout)"
   >
   > **Required action — pause the task, present the two options below, and wait for the user's reply before doing anything else:**
   >
   > > "AWS access is not available (AWS CLI missing / credentials not configured / API unreachable). I cannot proceed without real resource data. Please choose:
   > >
   > > **Option A** — Configure AWS credentials and re-run the scan scripts:
   > > `aws configure` (or set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_DEFAULT_REGION`), then re-run `aws-scan-region.sh` and `aws-scan-enrich.sh`.
   > >
   > > **Option B** — Provide a complete AWS resource inventory manually (VPC, subnets, SGs, EC2, RDS, S3, Lambda, API Gateway, EventBridge, IAM roles, etc.) and I will continue from there.
   > >
   > > Which option would you like to proceed with?"
   >
   > **Unconditional prohibitions — no exceptions, no rationalisations:**
   > - **Do NOT fabricate** any AWS resource, architecture, topology, or configuration — not even as "representative", "typical", "simulated", "example", or "for evaluation purposes".
   > - **Do NOT create any output files** (`inventory.md`, `inventory-deep.md`, `migration-assessment-report.md`, `main.tf`, `migration-status.md`, runbooks, etc.) based on invented data.
   > - **Do NOT advance to Phase 2, 3, or 4** under any circumstances until real resource data is confirmed.
   > - Being a test, evaluation, or demo environment is **not** a valid reason to bypass this rule.

   > **[STOP — Both scans required]** Do NOT proceed to Phase 1 step 2 (dependency mapping) until **both** `inventory.md` and `inventory-deep.md` have been generated and read. If Step 1 returns resources but Step 2 is skipped, the assessment will miss critical migration details (triggers, policies, listener configs, DNS records, etc.). If the user cannot run the scripts, they must manually provide equivalent information for each resource category below.

   **[MUST]** The deep scan (Step 2) reveals details invisible in broad scan — do not skip:
   - **Lambda** `get-policy` per function (push triggers NOT returned by `list-event-source-mappings`)
   - **API Gateway** REST `get-resources`+`get-stages`; HTTP v2 routes+stages
   - **Step Functions** state machine definitions · **EventBridge** `list-targets-by-rule` on every bus
   - **SNS** per-topic subscriptions · **SQS** per-queue attributes (DLQ, encryption, FIFO)
   - **S3** per-bucket lifecycle+policy · **DynamoDB** per-table capacity/GSI/streams · **EFS** mount targets+access points
   - **ECS** per-cluster services · **EKS** per-cluster details+addons · **ElastiCache** replication groups+parameters
   - **ELB v2** per-LB listeners+target groups · **Route53** per-zone record sets · **CloudFront** per-distribution config
   - **RDS** subnet groups+parameter groups · **IAM** inline policies · **MSK** broker config · **Cognito** user pool config

   **[MUST]** VPC topology (broad scan — verify completeness): subnets, route tables, SG rules, NACLs, endpoints, peering, prefix lists, VPN, Direct Connect

2. **Map dependencies and data flows** — Service call chains, data origins/destinations, external integrations, migration ordering constraints.

3. **Risk and complexity assessment** — Rate each dimension High/Medium/Low: data volume, downtime tolerance (RTO/RPO), compliance requirements, custom AMI/OS compatibility, Lambda→FCv3 code refactor scope, security group complexity.

4. **Generate assessment report (Phase 1 sections)** — Create `migration-assessment-report.md` using [references/assessment-report-template.md](references/assessment-report-template.md). Complete: Executive Summary, Resource Inventory, Integration & Dependency Mapping, Risk Assessment. Remaining sections completed in Phase 2.

5. **Initialize status tracker** — Create `migration-status.md` from [references/migration-status-template.md](references/migration-status-template.md). Populate all discovered resources, set all statuses to ⬜.

6. **[CHECKPOINT — Phase 1 end]** Output the following three items **directly in the conversation** (do not write to a file):
   - **Structured resource inventory** — one table per category, one row per discovered resource. Do not omit any category that has resources. Format:

     ```
     AWS <region> Resource Discovery Results

     ## 1. VPC & Networking
     ┌──────────────────┬──────────────────────────┬──────────────────────────────────────────────┐
     │   Resource Type  │       Resource ID         │                    Details                   │
     ├──────────────────┼──────────────────────────┼──────────────────────────────────────────────┤
     │ VPC              │ vpc-xxxxxxxxxxxxxxxxx     │ CIDR x.x.x.x/x, state available, default/custom │
     │ Subnet           │ subnet-xxxxxxxxxxxxxxx   │ AZ, CIDR, public/private                     │
     │ Security Group   │ sg-xxxxxxxxxxxxxxxxx     │ inbound rules summary / outbound rules summary │
     │ NAT Gateway      │ nat-xxxxxxxxxxxxxxxxx    │ public IP, associated subnet                 │
     │ Route Table      │ rtb-xxxxxxxxxxxxxxxxx    │ key route entries                            │
     └──────────────────┴──────────────────────────┴──────────────────────────────────────────────┘

     ## 2. Compute
     ┌──────────────────┬──────────────────────────┬──────────────────────────────────────────────┐
     │ EC2 Instance     │ i-xxxxxxxxxxxxxxxxx       │ type, OS, state, private IP                  │
     │ Lambda Function  │ <function-name>           │ runtime, memory, timeout, triggers (deep scan) │
     └──────────────────┴──────────────────────────┴──────────────────────────────────────────────┘

     ## 3. Storage
     ## 4. Database
     ## 5. ... (only include categories with discovered resources)
     ```

   - **Architecture topology** (ASCII, not Mermaid):

     ```
     ┌──────────────────── AWS ─────────────────────────┐
     │  Region: <region>   VPC: <cidr>                   │
     │  EC2: <type> <OS> ──▶ RDS: <engine> <ver>         │
     │  S3: <N> buckets   Lambda: <N>   SQS: <N>         │
     │  Route53: <domain> → CloudFront → EC2              │
     └──────────────────────────────────────────────────┘
     ```

   - **Risk assessment**:

     | Risk Dimension | Rating | Notes |
     |----------------|--------|-------|
     | Data volume | H/M/L | |
     | Downtime tolerance (RTO/RPO) | H/M/L | |
     | Code refactor scope | H/M/L | |
     | Compliance requirements | H/M/L | |

   > **Is the above AWS current state and risk assessment accurate? Confirm to proceed to Phase 2.**
   > **[DO NOT proceed to Phase 2 until the user explicitly confirms]**

---

### Phase 2: Migration Plan Generation

**Goal**: Map AWS services to Alibaba Cloud equivalents, design target architecture, confirm all parameters, and produce a complete migration plan.

1. **Service mapping** — Use [references/service-mapping.md](references/service-mapping.md). For missing mappings follow the "Adding a New Mapping" procedure in that file. Record the planned Alibaba Cloud resource type for every AWS resource — these names will be validated against [references/terraform-providers/alicloud.md](references/terraform-providers/alicloud.md) at the Phase 3 pre-HCL gate (existence, deprecation, usage example).

2. **Target architecture design** — Region (proximity to source), VPC/VSwitch CIDRs, ECS/RDS sizing, OSS bucket policies, FCv3 RAM role + trigger mapping, CDN config, CloudWatch→Cloud Monitor mapping, IAM→RAM mapping.

3. **Data migration strategy** — Confirm tool per resource type and S3→OSS transfer path:

   | Option | Method | Speed | Est. time (2.5 GB) |
   |--------|--------|-------|-------------------|
   | A | Local relay | ~1–2 MB/s | ~30–45 min |
   | **B ← Recommended** | **HK relay ECS** | **~50–100 MB/s** | **~1–3 min, <¥1** |
   | C | Alibaba Cloud Online Migration | ~20–50 MB/s | ~3–8 min |

   Autonomous: default to B, notify user. Interactive: present table and wait for choice.

4. **Downtime window planning** — Maintenance windows, AMI export timing, DTS cutover window after sync lag stabilizes.

5. **Cost estimation** — Monthly cost for all target resources (ECS + RDS + OSS + FCv3) and data transfer costs during migration; compare to AWS baseline.

6. **Rollback plan** — DNS rollback (keep AWS endpoints running), DTS bidirectional sync (database fallback), Terraform destroy per STATE_ID (per-layer infrastructure rollback).

7. **Complete assessment report (Phase 2 sections)** — Add to `migration-assessment-report.md`: Service Mapping, Network Topology (target state), IAM & Security Mapping, Monitoring Mapping, Data Migration Strategy, Cost Estimation, Migration Plan, Rollback Plan, Next Steps + sign-off.

8. **[CHECKPOINT — Phase 2 end]** Render target architecture + migration plan + parameter summary **directly in the conversation**. Wait for explicit confirmation before Phase 3.

   ```
   ┌──────────────── Alibaba Cloud ───────────────────┐
   │  Region: <region>   VPC: <cidr>                   │
   │  ECS: <type> (via ImportImage) ──▶ ApsaraDB <eng> │
   │  OSS: <N> buckets   FCv3: <N> functions            │
   │  Alibaba Cloud DNS: <domain> → CDN → ECS          │
   └──────────────────────────────────────────────────┘
   ```

   | Phase | Content | Tool | Est. Time |
   |-------|---------|------|-----------|
   | ✅ 1 | Source assessment | — | Done |
   | ✅ 2 | Migration plan | — | Done |
   | ⬜ 3 | Infrastructure deploy (empty shells) | Terraform | ~10–20 min |
   | ⬜ 4 | Data migration + cutover | CLI + DTS + Terraform | ~varies |

   Autonomous mode: include parameter summary (see [references/parameter-reference.md](references/parameter-reference.md) for full defaults table).

   > **Is the above target architecture and plan accurate? Confirm to proceed to Phase 3.**
   > **[DO NOT proceed to Phase 3 until the user explicitly confirms]**

---

### Phase 3: Infrastructure Deployment

**Goal**: Deploy all target resources on Alibaba Cloud as empty shells. No data migration in this phase. Verify all infrastructure is ready before Phase 4.

> **[MUST — Pre-HCL gate]** Before writing **any** Terraform resource block, look up **every** planned resource type in [references/terraform-providers/alicloud.md](references/terraform-providers/alicloud.md) and confirm **all three** of the following:
>
> 1. **Exists** — the resource name is listed in `alicloud.md` (do not invent or guess resource names).
> 2. **Not deprecated** — the entry has no ⚠️ deprecated marker. If deprecated, switch to the replacement resource name listed there (e.g., use `alicloud_fcv3_function` not `alicloud_fc_function`).
> 3. **Usage example reviewed** — read the example block in `alicloud.md` for each resource to confirm required arguments, argument names, and value formats before writing HCL.
>
> **Violation of this gate** (writing HCL without checking) is a critical error — deprecated resources cause silent apply failures and the resulting infrastructure cannot be used for migration.

**Step 1 — Network layer first (required before all other layers):**

```bash
$TF apply network-main.tf    # → NETWORK_STATE_ID
echo "NETWORK_STATE_ID=$NETWORK_STATE_ID" >> terraform_state_ids.env
```

HCL template: [references/migration-guides/network-migration.md](references/migration-guides/network-migration.md)

**Step 2 — Remaining layers in parallel (after network is ready):**

```bash
$TF apply compute-main.tf    # → COMPUTE_STATE_ID    (ECS instance — no data; image imported in Phase 4)
$TF apply database-main.tf   # → DATABASE_STATE_ID   (ApsaraDB RDS — empty DB; data migrated via DTS in Phase 4)
$TF apply storage-main.tf    # → STORAGE_STATE_ID    (OSS bucket — empty; data transferred in Phase 4)
$TF apply serverless-main.tf # → SERVERLESS_STATE_ID (FCv3 RAM Role + empty function; code deployed in Phase 4)
```

HCL templates: [server](references/migration-guides/server-migration-importimage.md) · [database](references/migration-guides/database-migration-dts.md) · [storage](references/migration-guides/storage-migration-oss.md) · [serverless](references/migration-guides/serverless-migration-fc.md)

> **[MUST] FCv3 RAM Role**: Create a RAM Role trusting `fc.aliyuncs.com` with least-privilege policies for services the function accesses (OSS, SLS, etc.). Set ARN as `role` on `alicloud_fcv3_function` — without this, the function cannot authenticate to other Alibaba Cloud services at runtime.

**[CHECKPOINT — Phase 3 end]** Verify all infra is ready: VPC/SG applied, ECS defined, RDS connectable (empty), OSS accessible, FCv3 role + function ready. All items in `migration-status.md` show ✅. Present resource list and estimated ongoing cost.

> **Is all target infrastructure ready? Confirm to proceed to Phase 4.**
> **[DO NOT proceed to Phase 4 until the user explicitly confirms]**

---

### Phase 4: Application and Data Migration

**Goal**: Migrate actual data and applications to Phase 3 infrastructure, complete cutover, and verify. Execute in dependency order; update `migration-status.md` after each sub-step.

**4.1 Server migration (AMI export + ImportImage)**
Export EC2 AMI → S3 → transfer to OSS → ImportImage → attach to Phase 3 ECS instance and start. No agent installation required on source server. See [references/migration-guides/server-migration-importimage.md](references/migration-guides/server-migration-importimage.md).

**4.2 Database migration (DTS full + incremental sync)**
Start DTS job against Phase 3 ApsaraDB instance: full migration + continuous incremental sync. Cut over during maintenance window once sync lag falls below acceptable threshold. See [references/migration-guides/database-migration-dts.md](references/migration-guides/database-migration-dts.md).

**4.3 Storage migration (S3 → OSS)**
Transfer all S3 objects to Phase 3 OSS bucket using the transfer path confirmed in Phase 2. Verify object count and total size match after transfer. See [references/migration-guides/storage-migration-oss.md](references/migration-guides/storage-migration-oss.md).

**4.4 Serverless deployment (Lambda → FCv3)**
Export Lambda code, adapt handler signatures, deploy to Phase 3 FCv3 functions. Configure triggers (API GW / EventBridge / SQS→MNS). Terraform resources: `alicloud_fcv3_function`, `alicloud_fcv3_trigger`. See [references/migration-guides/serverless-migration-fc.md](references/migration-guides/serverless-migration-fc.md).

**4.5 Pre-cutover validation**
Before DNS cutover, verify all workloads on Alibaba Cloud (see [references/verification-method.md](references/verification-method.md)):
- [ ] ECS: application running from imported image
- [ ] RDS: row counts match, DTS sync lag < threshold
- [ ] OSS: object count matches source S3 (checksum spot-check)
- [ ] FCv3: functions invocable, output correct
- [ ] End-to-end functional and performance tests pass

**4.6 [MUST CONFIRM] DNS cutover**
Migrate Route53 → Alibaba Cloud DNS; CloudFront → Alibaba Cloud CDN (Terraform). See [references/migration-guides/network-migration.md](references/migration-guides/network-migration.md).

> **This will immediately affect live traffic. Confirm DNS cutover?**
> Lower TTL to 60s beforehand. Keep AWS endpoints running for instant DNS rollback.

**4.7 Post-migration observation (minimum 24 hours)**
Monitor: traffic routing, error rates, response times, DB write operations. Stop DTS sync after confirming data consistency.

**4.8 [MUST CONFIRM] Source resource decommission**
Decommission AWS resources only after observation period and user confirms. **Irreversible.**

> **Observation period complete. Confirm decommission of AWS source resources?**
> Retain RDS snapshots and EC2 AMI for at least 30 days as final backup.

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed steps.

- [ ] VPC/VSwitch/SG created (Terraform state = `Applied`)
- [ ] ECS image imported (`DescribeImages` status = `Available`)
- [ ] ECS instance running from imported image
- [ ] RDS accessible; DTS sync lag < threshold
- [ ] OSS bucket: object count and size match source
- [ ] FCv3 functions deployed and invocable
- [ ] DNS resolving correctly; CDN active

## Cleanup

```bash
# Destroy Terraform-managed infra (load STATE_IDs from terraform_state_ids.env)
$TF destroy "$NETWORK_STATE_ID"
$TF destroy "$COMPUTE_STATE_ID"
$TF destroy "$DATABASE_STATE_ID"
$TF destroy "$STORAGE_STATE_ID"
$TF destroy "$SERVERLESS_STATE_ID"

# Delete imported ECS image and OSS staging file (not Terraform-managed)
aliyun ecs DeleteImage --RegionId <region> --ImageId <image-id> --Force true --user-agent AlibabaCloud-Agent-Skills
ossutil rm oss://<oss-bucket>/migrated-image.vhd

# Release DTS job (not Terraform-managed)
aliyun dts DeleteMigrationJob --MigrationJobId <job-id> --user-agent AlibabaCloud-Agent-Skills
```

> **WARNING**: Only clean up migration-related intermediate resources. Do NOT destroy target ECS/RDS/OSS unless decommissioning.

## Best Practices

1. **Never add `terraform {}` / `required_providers` block** — Provider is pre-initialized; this block causes `Failed to load plugin schemas`. Start HCL with `provider "alicloud" { region = var.region; configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-migrate" }` directly. See `references/acceptance-criteria.md §4`.
2. **Save and reuse every STATE_ID** — Record immediately after every apply. Always pass `--state-id` for any subsequent operation on existing infrastructure.
3. **Single `main.tf` (online mode only)** — Required by IaCService. Local mode can split HCL files freely.
4. **Consult error remediation first** — Check [references/error-remediation.md](references/error-remediation.md) before ad-hoc debugging.

## References

All references are linked inline throughout this document. Key directories:
- `references/migration-guides/` — Per-service migration workflows (server, database, storage, serverless, network)
- `references/terraform-providers/` — Alicloud and AWS Terraform resource catalogs
- `references/source-mappings/` — Raw source mapping documents
