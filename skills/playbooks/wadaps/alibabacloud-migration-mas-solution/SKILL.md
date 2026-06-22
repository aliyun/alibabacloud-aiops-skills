---
name: alibabacloud-migration-mas-solution
description: 生成从友商云（AWS、Azure、华为云、腾讯云）迁移到阿里云的迁移方案。当用户提供友商云产品列表时，给出产品映射和详细迁移方案。适用于用户提到"迁云"、"迁移方案"、"云迁移"、"从XX云迁移到阿里云"等场景。
---

# Cloud Migration Solution Generator

## When to Use

**Scenarios where this Skill SHOULD be used:**

- User explicitly mentions "cloud migration", "migration plan", "migrate from XX cloud to Alibaba Cloud", etc.
- User provides a list of source cloud products / resource inventory / architecture diagram and needs a complete migration plan document
- User requests deliverable-grade documentation (MD + Word) including product mapping, migration steps, risk assessment, and reverse sync
- User involves **cross-cloud migration** (AWS / Azure / Huawei Cloud / Tencent Cloud → Alibaba Cloud)
- User involves **Alibaba Cloud cross-account / cross-site migration** (e.g., Hologres, MaxCompute, DataWorks internal migration)

**Scenarios where this Skill SHOULD NOT be used (use product-mapping or other approaches):**

- User only needs a **specification comparison table** or **cost estimate**, not a full migration plan → Use `product-mapping` Skill
- User only needs **pricing for a single Alibaba Cloud product** → Use `product-mapping` Skill
- User asks about **Alibaba Cloud product features / configuration / best practices** without migration context → Answer directly or search documentation
- User already has a complete plan and only needs **format conversion** (e.g., MD → Word) → Call `md_to_docx.py` directly
- User discusses **application architecture refactoring** rather than cloud resource migration → General technical discussion
- User needs an **O&M operations manual** rather than a one-time migration plan → Not applicable

---

## 1. Workflow

```
Collect Info → Review Mapping Table → Search Official Docs Online → Generate Markdown Plan → Convert to Word → Deliver to User
```

### Step 1: Collect Information

Confirm the following required information with the user:

- **Source cloud provider**: AWS / Azure / Huawei Cloud / Tencent Cloud
- **Cloud product list**: Product names and specifications currently in use
- **Business scenario (optional)**: Helps recommend more accurate Alibaba Cloud products

> If the user does not specify the source cloud provider, ask proactively. If only product names are provided without specifications, handle as a general scenario.

### Step 2: Review Product Mapping Table

Based on the source cloud provider, read the corresponding mapping file to get product mapping relationships and migration methods:

| Source Cloud | Mapping File |
|-------------|-------------|
| AWS | [references/aws-product-mapping.md](references/aws-product-mapping.md) |
| Azure | [references/azure-product-mapping.md](references/azure-product-mapping.md) |
| Huawei Cloud | [references/huawei-product-mapping.md](references/huawei-product-mapping.md) |
| Tencent Cloud | [references/tencent-product-mapping.md](references/tencent-product-mapping.md) |

> Each mapping table contains two parts — **Cloud Product Mapping** + **Self-hosted Middleware Migration**. When the user's products involve self-hosted middleware (MySQL, Redis, Kafka, Nginx, etc.), also refer to the self-hosted section for migration methods.

### Step 3: Search Alibaba Cloud Official Documentation Online (Mandatory)

Before generating the "Per-Product Migration Plan", you **MUST** search Alibaba Cloud official documentation online to ensure migration step accuracy.

#### 3.1 Requirements

- **Must search online**: Use available web search tools (e.g., `search_web`, `web_search`, `web_fetch`, etc.) to search Alibaba Cloud official migration documentation
- **Must retrieve document content**: Use available content fetching tools (e.g., `fetch_content`, `web_fetch`, etc.) to read `help.aliyun.com` official documentation
- **Never fabricate from memory**: All migration steps must come from actually retrieved official documentation
- **Must cite official links**: The "Reference Documentation" in the output must include real links from the `help.aliyun.com` domain

#### 3.2 Search Steps (Execute Per Product)

For **each** migration product/tool the user involves, repeat the following:

1. **Search official documentation**
   - Use available search tools to find Alibaba Cloud official migration documentation
   - Search keyword format: `Alibaba Cloud <tool/product name> <migration scenario> official documentation`
   - Examples:
     - `Alibaba Cloud DTS MySQL migration official documentation`
     - `Alibaba Cloud Redis-Shake migration guide`
     - `Alibaba Cloud SMC Server Migration`
     - `Alibaba Cloud Online Migration Service OSS`

2. **Select `help.aliyun.com` links**
   - Prioritize official documentation from the `help.aliyun.com` domain
   - Retrieve at least 1 official document per product

3. **Read document content**
   - Use available content fetching tools to read the document page
   - Extract: prerequisites, operation steps, important notes, data verification methods

4. **Integrate document content into the plan**
   - Reference the retrieved official documentation in the "Migration Steps"
   - Attach actually read `help.aliyun.com` links in the "Reference Documentation"

#### 3.3 Execution Verification

- [ ] Online search performed for each migration product
- [ ] Official `help.aliyun.com` documentation retrieved for each migration product
- [ ] "Migration Steps" content derived from actually retrieved document body
- [ ] "Reference Documentation" links include `help.aliyun.com` domain

> If any item is not satisfied, you must go back and re-execute search and retrieval. Do not proceed with plan generation.

#### 3.4 Common Search Keyword Quick Reference

| Migration Tool | Search Keywords |
|---------------|----------------|
| DTS | `Alibaba Cloud DTS data migration <source database type>` |
| SMC | `Alibaba Cloud SMC Server Migration Center` |
| Redis-Shake | `Alibaba Cloud Redis-Shake data sync` |
| Online Migration Service | `Alibaba Cloud Online Migration Service OSS object storage migration` |
| Logstash/Snapshot | `Alibaba Cloud Elasticsearch data migration snapshot restore` |
| MirrorMaker | `Kafka MirrorMaker migration Alibaba Cloud` |
| ACK Deployment | `Alibaba Cloud ACK Container Service application deployment` |
| PolarDB | `Alibaba Cloud PolarDB data migration DTS` |

### Step 4: Generate Markdown Plan

Generate plan content following the "Plan Template" structure below, save as a `.md` file (suggested filename: `<customer_name>_migration_plan.md`).

### Step 5: Convert to Word Document

```bash
timeout 60 uv run --with python-docx==1.2.0 python3 scripts/md_to_docx.py <plan.md> <plan.docx>
```

Conversion tool features (precise formatting via python-docx):

- Dual Chinese/English fonts (Microsoft YaHei + Calibri), A4 page, 1.5x line spacing
- Hierarchical heading styles (dark blue, bold, graduated font sizes)
- Professional table formatting: dark blue header + white text + zebra rows + borders
- Supports bold, ordered/unordered lists, blockquotes, horizontal rules
- Uses `uv run --with python-docx==1.2.0` for automatic dependency management, no manual installation needed

Provide the generated `.docx` file path to the user.

---

## 2. Plan Template

```markdown
# [Customer/Project Name] Cloud Migration Plan

## 1. Migration Overview

Briefly describe migration background, source cloud platform, target cloud platform (Alibaba Cloud), and number of products involved.

## 2. Product Mapping Summary

| No. | Source Cloud Product | Source Product Description | Alibaba Cloud Product | Alibaba Cloud Product Description | Migration Method |
|-----|---------------------|---------------------------|----------------------|----------------------------------|-----------------|
| 1   | XXX                 | ...                       | XXX                  | ...                              | ...             |

## 3. Per-Product Migration Plan

### 3.1 [Product Name]

#### Product Mapping
- **Source product**: Product name and brief description
- **Alibaba Cloud product**: Counterpart product name and brief description

#### Migration Plan
- **Migration method**: Describe the migration approach (online migration/offline migration/tool migration/reconfiguration, etc.)
- **Migration tool**: Recommended migration tool or service
- **Migration steps** (must be based on official documentation retrieved via `fetch_content`):
  1. Prerequisites (permissions, network, version requirements, etc.)
  2. Specific operation steps
  3. Data verification and cutover
- **Application modification** (if needed): Clearly identify whether application code, configuration files, or connection strings need modification, and list specific modification points
- **Reference documentation**: Attach actual `help.aliyun.com` official documentation links retrieved via `fetch_content`

#### Important Notes
- Compatibility notes (version, parameter, feature differences)
- Data consistency assurance (verification methods)
- Business interruption assessment (downtime window, rollback plan)

(Repeat 3.x structure for each product)

## 4. Migration Risks and Mitigation

| Risk Item | Risk Description | Impact Level | Mitigation Measures |
|-----------|-----------------|--------------|---------------------|
| ...       | ...             | High/Med/Low | ...                 |

## 5. Data Reverse Sync Plan

During cutover, to ensure data consistency between source and Alibaba Cloud for rollback purposes, provide a data reverse synchronization plan.
```

---

## 3. Writing Principles

- **Accurate mapping**: Product mapping must strictly follow the mapping table. If Alibaba Cloud has no exact counterpart, explain differences and provide alternatives
- **Feasible plan**: Migration steps must be specific and actionable; recommended tools and methods must actually exist
- **Risk disclosure**: Explain compatibility issues, data loss risks, and business interruption impact
- **Tool-first**: Prioritize migration tools noted in the mapping table (SMC, DTS, Redis-Shake and other official Alibaba Cloud tools)
- **Best practices**: Provide recommendations based on Alibaba Cloud official documentation
- **Documentation-driven (mandatory)**: Each product migration plan must execute Step 3 online documentation search; migration steps must come from actual `help.aliyun.com` document content, never fabricated from memory; must include real reference links
- **Application modification marking**: If migration involves application changes (code/config/connection string changes), a dedicated "Application Modification" subsection must be added in the "Migration Plan" section, clearly listing all modification points with examples
