---
name: alibabacloud-migration-mas-product-mapping
description: 多厂商云产品映射 Skill，支持 AWS、腾讯云、华为云、Azure 到阿里云的全量映射，涵盖产品名称映射、实例规格映射、用量换算和阿里云实时询价。当用户需要将其他云资源迁移到阿里云、需要规格对照表、需要估算阿里云成本、或执行产品询价时使用。
metadata: {"supported_vendors": ["aws", "tencent", "huawei", "azure"], "output_format": "markdown-table", "pricing_service": true}
---

# Cloud Product Mapping Skill (Multi-Vendor + Instance-Level Spec Mapping + Real-Time Pricing)

Map source cloud vendor (AWS / Tencent Cloud / Huawei Cloud / Azure) resources to Alibaba Cloud with precision, outputting a complete comparison table of product names, instance specs, usage, and reference prices.

## When to Use

- User has resource inventory/bills/survey reports from other cloud vendors and needs mapping to Alibaba Cloud products and specs
- Before migration planning, need to estimate costs on the Alibaba Cloud side
- User specifies source cloud vendor and needs product mapping relationships and migration order

## Supported Vendors

| Vendor | Identifier | Mapping Data | Spec Mapping | Product Mapping | Instance Spec Mapping | Real-Time Pricing |
|--------|-----------|--------------|--------------|-----------------|----------------------|-------------------|
| AWS | aws | references/mappings/aws.md | references/aws-spec.md | 78 products | Full | 33 products |
| Tencent Cloud | tencent | references/mappings/tencent.md | references/tencent-spec.md | 85 products | Full | 33 products |
| Huawei Cloud | huawei | references/mappings/huawei.md | references/huawei-spec.md | 83 products | Full | 33 products |
| Azure | azure | references/mappings/azure.md | references/azure-spec.md | 78 products | Full | 33 products |

Cross-vendor common rules (Database / Redis / MongoDB / FC / Disk): references/common-spec.md
Alibaba Cloud Pricing API Index (33 products): references/pricing-api.md

## Prerequisites

### Runtime Environment

- Python: >= 3.9 (scripts use f-strings, type annotations, `dict | None` syntax)
- OS: macOS / Linux / Windows (verified on macOS 15 / Ubuntu 22)
- Disk: >= 200 MB for Python dependencies and intermediate results

### Dependency Installation

```bash
cd .qoder/skills/product-mapping/scripts
pip install -r requirements.txt
```

Main dependencies:

| Dependency | Purpose |
|-----------|---------|
| flask | Pricing service HTTP framework |
| requests | Calling pricing service and external APIs |
| xlrd / openpyxl | Read/write Excel (.xls / .xlsx) |
| aliyun-python-sdk-core / aliyun-python-sdk-bssopenapi / aliyun-python-sdk-ecs / aliyun-python-sdk-rds / aliyun-python-sdk-r-kvstore / aliyunsdkpolardb | Alibaba Cloud product SDKs |

### Alibaba Cloud Credentials

**This Skill relies on the Alibaba Cloud default credential chain for authentication. NEVER explicitly handle AK/SK credentials.**

The pricing service uses the [default credential provider chain](https://help.aliyun.com/document_detail/378659.html) which resolves credentials in the following order:

1. Environment variables (`ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`) — set by the runtime environment automatically
2. OIDC Role ARN
3. ECS RAM Role (Instance metadata)
4. Credential file (`~/.alibabacloud/credentials`)

No manual credential configuration is needed. The runtime environment provides credentials automatically.

**Mandatory Rules**:

- When user request **includes price estimation, cost comparison, or real-time pricing**, start the pricing service normally
- The pricing service resolves credentials automatically via the default credential chain
- If credentials are not available in the environment, the service will return appropriate error responses
- **MUST** still send standard requests to local pricing service (e.g., `POST /api/pricing/batch`) to record call traces in `api.json`
- Only when user explicitly says "mapping only, no pricing" can pricing be fully skipped, with report annotated "Pricing not enabled"

**Prohibited**: Hardcoding AccessKey in scripts; explicitly reading/exporting AK/SK in Skill instructions; using root account AccessKey.

## Required Permissions

For detailed RAM permission policies and API permission reference, see [references/ram-policies.md](references/ram-policies.md).

## Input Format

Supports any one or more of the following formats:

**Format 1 - Plain Text**:
```
  "3 台 EC2 m5.xlarge，2 个 RDS MySQL db.r5.large（500GB），1 个 S3 桶约 2TB"
  "4 台腾讯云 CVM S5.LARGE8，1 个 CDB MySQL 4C8G"
```

**Format 2 - JSON**:
```json
  [
    {"vendor": "aws",     "service": "EC2", "type": "m5.xlarge",  "count": 3},
    {"vendor": "tencent", "service": "CVM", "type": "S5.LARGE8",  "count": 4}
  ]
```

**Format 3 - Excel Survey / Cloud Vendor Bill CSV**

When vendor is not specified, auto-detect from product names in context (EC2/S3 → AWS, CVM/COS → Tencent Cloud, ECS/OBS → Huawei Cloud, VM/Blob → Azure).

## Execution Steps

### 1. Confirm Source Cloud Vendor

Confirm which source cloud vendor (AWS / Tencent Cloud / Huawei Cloud / Azure) the user wants to map. If unclear, prompt user to choose directly; do not assume defaults.

### 2. Confirm Alibaba Cloud Target Region

**Must confirm with user before pricing; different regions have significant price differences.**

- Extract region info from source data (e.g., AWS ap-southeast-1 = Singapore)
- Show source region to user and ask for Alibaba Cloud target region
- Common Alibaba Cloud regions: cn-beijing, cn-shanghai, cn-hangzhou, cn-shenzhen, ap-southeast-1 (Singapore), ap-southeast-5 (Jakarta)
- Do NOT default to cn-beijing; must be explicitly specified by user
- Pass confirmed region as `--region` parameter to `excel_mapping.py` and pricing service
- **Post-execution validation**: After script completes, must verify the "target region" field in output file matches the `--region` value exactly; if mismatch (e.g., falls back to cn-beijing), prompt user to check script parameter parsing or force override `ALIBABA_CLOUD_REGION_ID`

### 3. Product Name Mapping

Load corresponding product mapping table from references/mappings/ based on source vendor. Table structure: Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity.

For source products not in the mapping library, match by category to similar Alibaba Cloud products and annotate with "AI Recommended, please verify manually".

### 4. Instance Spec Mapping

Load spec mapping detail table by source vendor:

- AWS → references/aws-spec.md (EC2 instance families, ARM Graviton, Intel/AMD, spec size conversion)
- Tencent Cloud → references/tencent-spec.md (CVM all generations, CDB MySQL, TDSQL-C, Redis, MongoDB)
- Huawei Cloud → references/huawei-spec.md (ECS including Kunpeng ARM, RDS, GaussDB, DCS Redis, DDS)
- Azure → references/azure-spec.md (VM all series, Database for MySQL/PG, Cache for Redis, Cosmos DB)
- Cross-vendor common rules → references/common-spec.md (RDS / Redis / MongoDB / FC / Disk / Others)

#### 4.1 Spec Family Normalization Rules

| CPU:Memory Ratio | Alibaba Cloud Spec Family | Category |
|-----------------|--------------------------|----------|
| 1:2 | ecs.c7 / ecs.c8i / ecs.c8a / ecs.c8y | Compute-optimized |
| 1:4 | ecs.g7 / ecs.g8i / ecs.g8a / ecs.g8y | General-purpose (default) |
| 1:8 | ecs.r7 / ecs.r8i / ecs.r8a / ecs.r8y | Memory-optimized |
| 1:16+ | ecs.re7 | High-memory (SAP HANA) |

- **ARM instances**: Map uniformly to Yitian ARM series (c8y / g8y / r8y)
- **GPU instances**: T4 inference → ecs.gn7i, V100 training → ecs.gn6v, A100 → ecs.gn7e, H100 → ecs.gn8
- **Bare metal**: ebmg7 / ebmc7 / ebmr7 / ebmgn7e

#### 4.2 Spec Family Auto-Fallback

When mapped spec family is unavailable in target region, fall back in this priority:

1. Same-generation substitute (e.g., g8i → g7)
2. Same-ratio substitute (e.g., g7 → c7 when 1:2 fits)
3. General-purpose fallback (ecs.g7)
4. Special: ecs.t6-c1m2 only available at large size; xlarge+ must fall back to ecs.c8y.xlarge

#### 4.3 Disk Configuration (Required Reading)

- System disk: ESSD PL0 uniformly, minimum 20GB
- Data disk >= 20GB → ESSD PL1; < 20GB → must downgrade to ESSD PL0 (PL1 minimum is 20GB, otherwise API error)
- ECS pricing must include both system disk and data disk

### 5. Alibaba Cloud Real-Time Pricing

#### 5.0 Pre-Pricing Service Start (Mandatory)

Before calling any pricing API, must perform:

1. Start `pricing_service.py` — it resolves credentials automatically via the default credential chain
2. **MUST** call `/api/pricing/batch` or corresponding product pricing endpoints
3. **MUST NOT** skip API calls under any circumstances
4. **If credential chain resolution fails**:
   - The pricing service will return 401/403 or preset reference prices
   - Caller handles per Section 5.3 error table
   - Inform user: "Credential chain resolution failed, pricing API returned error; ensure the runtime environment provides valid credentials"
4. **Only when user explicitly replies "no pricing" or "mapping only"** can pricing be skipped, with report annotated "Pricing not enabled"

#### 5.1 Start Pricing Service

```bash
cd .qoder/skills/product-mapping/scripts
pip install -r requirements.txt
# macOS note: AirPlay occupies port 5000, recommend port 5001
PRICING_PORT=5001 python pricing_service.py
```

Service exposes pricing capabilities for 33 products (see references/pricing-api.md).

#### 5.2 Batch Pricing (Recommended)

POST multiple products at once to /api/pricing/batch to significantly reduce latency. Full examples in references/pricing-api.md.

#### 5.3 Response Handling and Error Processing

All pricing service responses are unified JSON. Caller must implement the following; otherwise cost estimates will be inaccurate:

| HTTP Status | Meaning | Action |
|------------|---------|--------|
| 200 + price | Pricing success | Write to report |
| 200 + price=null, warning | Spec exists but no quote | Annotate "Reference price missing", fall back to mapping table reference price |
| 400 invalid_param | Parameter error (e.g., PL1 + <20GB) | Validate and retry, auto-downgrade PL1→PL0 |
| 404 spec_not_found | Spec does not exist / deprecated | Fall back by CPU:memory ratio |
| 429 rate_limited | API rate limiting | Exponential backoff (1s/2s/4s, max 3 retries) |
| 5xx / timeout | Upstream exception | Retry once per item; annotate "Pricing failed" on failure |
| Credential missing / 403 | AccessKey not configured or insufficient permissions | **Must stop execution and prompt user**, no silent fallback |

**Mandatory Requirements**:

- Timeout: HTTP client timeout 30 seconds (PolarDB DescribeClassList is slow in large regions)
- Retry: 429 / 5xx / timeout use exponential backoff, max 3 retries
- Fallback: All failed pricing items must be annotated "Pricing failed / Reference price missing, please verify manually" in report; silent discard prohibited
- **Credential missing is NOT a fallback scenario**: When AccessKey not configured, must interrupt and prompt user

#### 5.4 Pricing Coverage

| Vendor | Mapped Products | API Real-Time Pricing | Free/No Pricing Needed | Effective Coverage |
|--------|----------------|----------------------|----------------------|-------------------|
| AWS | 78 | 41 | 13 | 69.2% |
| Azure | 78 | 37 | 14 | 65.4% |
| Tencent Cloud | 85 | 39 | 14 | 62.4% |
| Huawei Cloud | 83 | 38 | 13 | 61.4% |

Detailed list with product_code/parameters for each product: references/pricing-api.md

### 6. Output Complete Mapping Report

#### 6.1 Resource Mapping Summary Table

| # | Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Migration Complexity | Notes |

#### 6.2 Cost Comparison Estimate

| Resource Type | Source Spec x Qty | Alibaba Cloud Spec x Qty | Source Monthly Cost (ref) | Alibaba Cloud Monthly Cost (ref) | Savings % |

#### 6.3 Cost Summary

```
┌──────────────────────────────────────┐
│ Alibaba Cloud Monthly Cost Estimate  │
├──────────────────────────────────────┤
│ Compute: ECS             ¥ xxx       │
│ Database: RDS/PolarDB    ¥ xxx       │
│ Cache: Redis/Tair        ¥ xxx       │
│ Storage: OSS+Disk+NAS    ¥ xxx       │
│ Network: SLB+CDN+EIP     ¥ xxx       │
│ Other: Kafka/FC/SLS etc  ¥ xxx       │
├──────────────────────────────────────┤
│ Monthly Total:           ¥ xxxxx     │
│ Annual Est.(85%):        ¥ xxxxx     │
│ 3-Year Est.(50%):        ¥ xxxxx     │
└──────────────────────────────────────┘
```

### 7. Output Migration Priority Recommendations

Ordered by risk from low to high:

1. **Batch 1 (Low Risk)**: Network infrastructure (VPC, Subnet, Security Group, NAT, Load Balancer, CDN, DNS)
2. **Batch 2 (Low Risk)**: Object storage (S3/COS/OBS/Blob → OSS)
3. **Batch 3 (Low Risk)**: Security & Identity (IAM → RAM, KMS, WAF, DDoS, Certificates)
4. **Batch 4 (Medium Risk)**: Compute instances (EC2/CVM/ECS/VM → ECS), using SMC whole-machine migration
5. **Batch 5 (Medium Risk)**: Databases (RDS/Aurora/TDSQL-C/GaussDB/Azure SQL → RDS/PolarDB), via DTS sync
6. **Batch 6 (Medium Risk)**: Cache & Search (Redis / Elasticsearch)
7. **Batch 7 (High Risk)**: Message queues (Kafka / RocketMQ / RabbitMQ / Service Bus)
8. **Batch 8 (High Risk)**: Containers & Serverless (EKS/TKE/CCE/AKS → ACK, Lambda/SCF/FunctionGraph/Functions → FC)
9. **Batch 9 (High Risk)**: Big Data & AI (EMR / Redshift / Synapse → MaxCompute / EMR, SageMaker → PAI)

## Excel Batch Processing Mode

Read resource survey Excel via script, auto-complete product mapping, spec mapping, real-time pricing, and output results to Excel.

```bash
cd .qoder/skills/product-mapping/scripts
pip install -r requirements.txt
PRICING_PORT=5001 python pricing_service.py &
python excel_mapping.py <input.xls> --output result.xlsx --pricing-url http://localhost:5001 --region <user-specified-region>
```

Input: Excel file with each Sheet representing one AWS product (EC2 / S3 / ElasticCache / DocumentDB / AuroraDB / NAT / Load Balancer / EIP / Lambda / Athena / EventBridge / SNS / CloudWatchLog / Other).

Output: *_mapping_result.xlsx with 10 Sheets (Product Mapping Summary, EC2 Spec Details, Database Details, Cache Details, Storage Details, Network Details, Other Services, Cost Summary, Migration Priority, Coverage Report).

**Practical Tips**: ECS deduplicates pricing by (spec, system disk, data disk, PL) tuple; system disk minimum 20GB; data disk < 20GB downgrade to PL0; t6 burst xlarge+ falls back to ecs.c8y; recommended port 5001.

**Credential Requirement**: The pricing service resolves credentials automatically via the default credential chain. Always start `pricing_service.py` and call `/api/pricing/batch`; do not skip API calls. If 401/403 returned, annotate per Section 5.3 error table.

## Mapping Rules

- Prefer Alibaba Cloud official migration tools (SMC / DTS / Online Migration Service)
- When no official tool available, recommend mature open-source solutions (redis-shake, MirrorMaker, etc.)
- Specs matched at equal or slightly higher performance to avoid degradation
- Aurora / TDSQL-C / GaussDB users strongly recommended PolarDB (architecture compatible)
- ARM instances uniformly map to Yitian ARM series (c8y / g8y / r8y)
- Complexity assessment: Low=config migration, Medium=data+config migration, High=requires app refactoring
- Uncertain mappings must be annotated "AI Recommended, please verify manually"

## Observability

### User-Agent Template

All HTTP requests made by `pricing_service.py` to Alibaba Cloud OpenAPI MUST include a User-Agent header following this template:

```
AlibabaCloud-Agent-Skills/alibabacloud-migration-mas-product-mapping/{session-id}
```

### Session-ID Generation Rules

- Generate one UUID v4 per Skill invocation as the `session-id`
- The same `session-id` MUST be used across all API calls within a single user interaction
- Format: lowercase UUID without hyphens (32 hex characters), e.g., `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`
- The session-id MUST be passed as an environment variable `SKILL_SESSION_ID` when starting `pricing_service.py`

```bash
export SKILL_SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex)")
PRICING_PORT=5001 SKILL_SESSION_ID=$SKILL_SESSION_ID python pricing_service.py
```

## Disclaimers

### Pricing Disclaimer

- All Alibaba Cloud prices output by this Skill are public reference prices, not contract prices.
- Actual prices are affected by: business discounts, enterprise negotiation, tiered billing, long-term commitment discounts, exchange rate fluctuations, vouchers, and promotional offers.
- Real-time API prices from BSS / ECS / RDS / Redis / PolarDB are based on Alibaba Cloud official pricing at the time of call; results are not commercial commitments.
- Some products (PolarDB-X, ClickHouse, Lindorm, GDB, Tablestore, etc.) use estimation logic rather than real-time API pricing, with lower accuracy.
- **Mandatory**: All reports must append at the end: "Prices in this report are for reference only; final pricing is subject to the contract signed with Alibaba Cloud sales."

### Competitor Spec Mapping Disclaimer

- Source vendor (AWS / Tencent Cloud / Huawei Cloud / Azure) spec mappings are based on public technical docs and market research, not official recommendations from source vendors.
- Different CPU generations, memory ratios, and network performance may differ between sides; performance equivalence does not guarantee 100% consistency.
- Deprecated, newly released, or region-restricted instance families may not be covered by the mapping library; results will be annotated "AI Recommended, please verify manually".
- ARM instances (Graviton / Kunpeng / Ampere) mapped to Alibaba Cloud Yitian ARM require user testing for app compatibility (some natively compiled apps may need rebuilding).
- GPU instance models (T4 / V100 / A100 / H100) are strictly matched; cross-model mapping is prohibited due to large performance differences.

### Data Source Declaration

- Vendor spec info: Referenced from each vendor's official documentation (as of 2025 Q1)
- Alibaba Cloud pricing: Obtained via Alibaba Cloud OpenAPI in real-time or referenced from Alibaba Cloud official public pricing
- Mapping rules: Based on practical experience from Alibaba Cloud migration team

## Directory Structure

```
.qoder/skills/product-mapping/
├── SKILL.md                      # This file (entry point and workflow)
├── references/                   # Spec mapping details and pricing API index
│   ├── mappings/                 # Product-level mapping data
│   │   ├── aws.md
│   │   ├── tencent.md
│   │   ├── huawei.md
│   │   └── azure.md
│   ├── aws-spec.md
│   ├── tencent-spec.md
│   ├── huawei-spec.md
│   ├── azure-spec.md
│   ├── common-spec.md            # Cross-vendor common rules (RDS/Redis/MongoDB/FC/Disk/Others)
│   └── pricing-api.md            # Pricing API index + error handling
├── scripts/                      # Python pricing service and Excel batch processing
│   ├── requirements.txt
│   ├── pricing_service.py        # Flask pricing service (port 5001)
│   ├── excel_mapping.py          # Excel batch processing entry point
│   ├── azure_mapping.py
│   ├── huawei_mapping.py
│   ├── price_comparison.py
│   ├── tc_price_comparison.py
│   └── hw_price_comparison.py
└── evals/                        # Evaluation test cases
```
