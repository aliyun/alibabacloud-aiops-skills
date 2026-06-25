---
name: quickbi-smartq-dashboard
description: >
  Generate a dedicated query skill based on a QuickBI dashboard.
  Use when the user provides a dashboard URL and wants to create a query skill.
  Trigger keywords: generate skill, dashboard to Skill.
---

# QuickBI Dashboard Skill Generator

Retrieve QuickBI dashboard data through OpenAPI, discover its chart components, field configurations, query controls, and layout relationships, extract the analytical approach, and generate a SKILL.md file that can be used for data queries.

## Scope

**Does:**
- Accept a QuickBI dashboard URL or data portal URL and parse out the pageId
- Call OpenAPI to retrieve the complete dashboard JSON structure
- Parse chart components, query controls, datasets, and field configurations
- Analyze layout patterns and match an appropriate analysis framework (L1-L4 Pyramid or a specialized framework)
- Generate a complete query skill SKILL.md file and install it into the skill center

**Does NOT:**
- Does NOT perform actual data queries (queries are handled by the generated child skill)
- Does NOT support dashboards outside the QuickBI platform
- Does NOT handle dashboards that require special permissions (an error will be surfaced during the pre-validation stage)
- **Does NOT attempt any alternative solution when `fetch_dashboard_data` fails** (MUST terminate the flow; workarounds are prohibited)

## Trigger Scenarios

Use this skill when the user makes requests like the following:
- "Help me turn this QuickBI dashboard into a query Skill"
- "Help me convert this QuickBI dashboard into a query Skill"
- "Generate a query skill for this dashboard: {URL}"
- "Generate a skill for this dashboard: {URL}"
- The user provides a dashboard URL similar to `https://bi.aliyun.com/dashboard/view/pc.htm?pageId=XXXXXXX` and wants to create query capability
- The user provides a data portal page URL (e.g., `https://bi.aliyun.com/product/view.htm?module=dashboard&productId=xxx&menuId=yyy`) and wants to create query capability

### Supported URL Formats

| URL Type | Path Characteristic | Key Parameter | Handling Method |
|----------|---------|---------|----------|
| **Dashboard page** | `/dashboard/view/pc.htm` | `pageId` | Extract pageId directly |
| **Data portal page** | `/product/view.htm` | `productId`, `menuId` | Retrieve the associated pageId via OpenAPI |

## Phase 1: Input Collection and Validation

### Step 1.0: Get User Input

Extract from the user message:

1. **Page URL** (required): QuickBI dashboard link or data portal link
2. **Skill name** (optional): the generated skill directory name (kebab-case format)
   - If the user specified a skill name, use it directly (a skill with the same name will be automatically overwritten in Phase 2, no pre-check needed)
   - If not specified, it will be derived automatically after discovering the dashboard title in Phase 2

---

## Phase 2: Dashboard Data Retrieval and Parsing

### Step 2.1: One-Stop Dashboard Data Retrieval

> **⚠️ Mandatory Constraint**: You MUST use the encapsulated script; splitting the execution manually is prohibited.

Use `scripts/fetch_dashboard_data.py` to complete the following in one step: configuration loading → URL parsing → pre-validation → JSON retrieval → structure parsing → dataset name retrieval.

**[Mandatory Rule] Terminate immediately on failure; any workaround is prohibited**:

> ⛔ **Absolutely prohibited**: When `fetch_dashboard_data` returns failure, **do NOT attempt any alternative solution**, including but not limited to:
> - ❌ Directly calling low-level APIs (such as `get_dashboard_json`)
> - ❌ Skipping the pre-validation step
> - ❌ Trying "other methods" to obtain data
> - ❌ Continuing with any subsequent step
>
> **The ONLY correct behavior**: Output the error message → terminate the flow → wait for the user to correct it and trigger again

- If retrieval fails (`result["success"] == False`), **the entire flow MUST be terminated immediately**
- **The failure reason is already described in `result["error"]`**; display it to the user directly
- **Do NOT try to "intelligently" work around the error** — pre-validation failure means prerequisites are not satisfied; workarounds will only cause all subsequent steps to fail

```python
from dashboard.fetch_dashboard_data import fetch_dashboard_data

# One-stop retrieval (automatically handles: configuration loading, URL parsing, pre-validation, JSON retrieval, parsing, dataset names)
result = fetch_dashboard_data(user_input_url)

if not result["success"]:
    print(f"Retrieval failed: {result['error']}")
    # ⛔ MUST terminate immediately! Trying any other method or continuing any subsequent step is prohibited
    return  # The flow ends here; wait for the user to correct the issue and trigger again

# Extract results
dashboardData = result["dashboardData"]      # Parsed dashboard structure
datasetNameMap = result["datasetNameMap"]    # cubeId -> cubeName mapping
page_id = result["pageId"]                   # Dashboard pageId
dashboard_url = result["dashboardUrl"]       # Standard dashboard preview URL (used for skill generation)

print(f"Retrieved successfully: {dashboardData['basicInfo']['name']}")
```

**Script location**: [scripts/fetch_dashboard_data.py](scripts/fetch_dashboard_data.py)

**MUST output after execution** (one-line summary only; **do NOT expand into tables** — the full dataset list, field mapping, etc. will be written into SKILL.md exactly once in Phase 3.2):

```markdown
✅ Step 2.1 retrieved "{dashboardData.basicInfo.name}" | pageId=`{page_id}` | charts=N / datasets=M / tabs=K / gmtModified={dashboardData.basicInfo.gmtModified}
```

> ⛔ **Critical constraint** (even when the input is a data portal URL): everywhere pageId is needed in Phase 3, you **MUST use `result["pageId"]`**; do NOT use the `productId` from the user-input URL (portal ID ≠ dashboard pageId).

**Returned data structure**: `dashboardData` contains `basicInfo`, `queryControls`, `chartComponents`, `tabComponents`, `richTextComponents`, `layoutAnalysis`, `fieldMapping`, and other fields. For the full definition, see [reference.md - dashboardData Data Structure](./reference.md#dashboarddata-data-structure).

### Step 2.2: Data Validation and Supplementation

**Purpose**: Validate the completeness of the parsing result and supplement information if necessary.

#### 2.2.1 Tab Structure Validation

If `dashboardData.tabComponents.length > 0`:

1. List all Tabs and their titles
2. Confirm the chart components included under each Tab
3. Record the ownership relationship between Tabs and charts

#### 2.2.2 Chart Title Validation

1. Check whether `dashboardData.chartComponents[].componentName` is meaningful
2. If it is empty or not meaningful, infer the theme based on measure/dimension fields
3. Record the adjusted chart titles

#### 2.2.3 Rich Text Content Extraction

1. Extract plain text from `dashboardData.richTextComponents[].textContent`
2. Use it to understand the business background and usage instructions of the dashboard

### Step 2.3: Extract Analytical Approach and Match Analysis Framework

> **[Mandatory Step]** Complete all substeps 2.3.1-2.3.4 and the mandatory output (2.3.2-OUTPUT). All content MUST be inferred based on `dashboardData`; do NOT fabricate information.

#### 2.3.1 Data Extraction

Extract from `dashboardData.chartComponents`:

**Dataset List**: Collect all charts' `sourceId`, deduplicate, and build a list:

| Dataset ID | Associated Charts | Available Dimensions | Available Measures |
|----------|---------|---------|----------|
| {sourceId} | {list of chart names} | {dimension fields} | {measure fields (aggregation method)} |

**Metric System**: Traverse `chartComponents[].measures` and deduplicate by `caption`.

**Dimension System**: Traverse `chartComponents[].dimensions` and classify by `itemType`:
- `datetime` → Time dimensions | `geographic` → Geographic dimensions | `dimension` → Categorical dimensions

#### 2.3.2 Analysis Framework Matching and Output

Match the most suitable analysis framework by combining **metric semantics + layout pattern + linkage relationships**.

**Framework Matching Rules**: See [reference.md - Analysis Framework Matching Rules](reference.md#analysis-framework-matching-rules)

Common frameworks: DuPont Analysis, AARRR Pirate Model, RFM Customer Analysis, Funnel Analysis, Goal Achievement Analysis, Period-over-Period & Year-over-Year Analysis, etc. When no match is found, use **L1-L4 Pyramid** (Overview → Trend → Breakdown → Detail).

**Matching Reasoning Process**:

1. List all metric names from `uniqueMeasures`
2. List all dimension names from `uniqueDimensions` (classified by datetime/geographic/dimension)
3. Identify the layout pattern (Metric Matrix / Detail-Oriented / Comparative Analysis / Focused Analysis)
4. Analyze linkage relationships (shared filters) and drill-down direction (`drillFields` dimension types)
5. Synthesize the above information to match the best analysis framework, and record the matching basis

**[Mandatory] Output format**: Output the "Analysis Framework Matching Result", including extracted real fields (measures/dimensions), layout pattern, framework matching (name/confidence/basis), and level preview. See [reference.md - Analysis Framework Output Template](reference.md#analysis-framework-output-template)

#### 2.3.3 Layout Pattern Analysis and Dashboard Type Inference

Infer the dashboard's overall analysis pattern based on `tileLayout` positional information. See [reference.md - Layout Pattern Analysis Rules](reference.md#layout-pattern-analysis-rules)

**Layout Pattern Types**: Metric Matrix, Core Chart, Detail-Oriented, Comparative Analysis, Focused Analysis.

#### 2.3.4 Business Logic Inference

Infer calculation relationships based on metric combinations. For inference rules, see [reference.md - Business Logic Inference Rules](reference.md#business-logic-inference-rules)

### Step 2.4: Infer the Intent Routing Matrix

> **Core Goal**: Establish an accurate mapping from user question → target chart → dataset ID

Extract intent by user query pattern and match target level (L1 metric card / L2 trend chart / L3 grouped chart / L4 detail table, etc.). For complete rules, see [reference.md - Intent Routing Rules](reference.md#intent-routing-rules)

### Step 2.5: Exploration Completion Confirmation

> **[Pre-check] Confirm that Step 2.1 and Step 2.3.2 have already output the analysis framework matching result**

> ⚠️ **Design change note**: This step only outputs a **short confirmation**. Do **NOT** repeat the chart list, field mapping, intent routing or any other details from `dashboardData` here. All details will be written into SKILL.md exactly once in Phase 3.2 (re-emitting the same content here is the main reason skill generation used to take 15-25 minutes).

**[Mandatory] Output** (keep within 10 lines): chart component count N (Phase 3.2 MUST output N rows), dataset count M, query control count K, matched framework name, business background keywords. Do **NOT** repeat chart list, field mapping, intent routing or other details — these will be written directly into SKILL.md in Phase 3.2.

---

## Phase 3: Skill File Generation

Based on the exploration results, assemble and write the SKILL.md and config.yaml files.

> ⚠️ **Key Variable Confirmation**: Before generating the skill file, confirm the source of the following values:
> - **pageId** = `result["pageId"]` (Step 2.1 script return value) — **NOT** the `productId` in the user-input URL
> - **dashboard_url** = `result["dashboardUrl"]` (Step 2.1 script return value, already contains the correct pageId)
> - **skill_generated_at** = `dashboardData.basicInfo.gmtModified`
>
> The `productId` in a data portal URL is a portal ID and is completely different from the dashboard `pageId`; mixing them is prohibited.

### Step 3.1: Determine the Skill Name

If the user provided a skill name, use it directly. Otherwise, generate one using the format `qbi-{title-kebab}-{first 8 chars of pageId}`.

### Step 3.2: Assemble SKILL.md Content

Generate the skill file according to the following template. **{placeholders}** indicate content populated from the exploration results.

#### 3.2.1-3.2.7 Content Template

> **[MUST execute] Read the template file**
>
> Use the `read_file` tool to read the file `./templates/output_skill_template.md` and obtain the full template for the following content:
> - **YAML Frontmatter + skill metadata** (3.2.1): name/description format, SKILL_METADATA comment block
> - **Title and description** (3.2.2): skill title and one-line description
> - **Prerequisites** (3.2.4): configuration guidance flow (consistent logic with this skill's prerequisites)
> - **Dashboard Knowledge Base** (3.2.5): basic information, business context (conditional output), dataset list, query controls, chart component complete list, intent routing matrix, field mapping
> - **Dashboard Analytical Approach** (3.2.6, simplified): metric relationships, linkage and drill-down paths
> - **Workflow** (3.2.7): question understanding → decomposition → build query → call SmartQ → summarize results → error handling
>
> Generate the corresponding content according to the template format and fill it with real data extracted from `dashboardData`.

**Key Requirements**:
- description MUST retain the `INSTEAD OF generic quickbi-smartq-chat` priority declaration
- Metrics and dimensions MUST come from `dashboardData`; do NOT fabricate them

### Step 3.3: Generate skill files

Phase 2 automatically completes the following:
- Creates the complete skill directory structure
- Copies runtime scripts with adjusted import paths
- Splices fragments and replaces all placeholders
- Generates config.yaml
- Validates no placeholder residuals

After Phase 2 succeeds, the output directory is a ready-to-install skill package.

### Step 3.4: Skill is already in place (no separate install step)

Pass the **skill center target path** directly as `--output-dir` (e.g. `<skill_center_root>/qbi-dashboard-<first 8 chars of pageId>`). Phase 2 handles "target exists → auto-rename to `.bak.<timestamp>` backup" internally. When Phase 2 returns `success: true`, the skill is already installed; **do NOT run any extra `cp` / `mv` / `rm`**. Backup directories will accumulate over re-generations and may be cleaned up by the user periodically.
---

## Examples

### Example 1: Generate a Query Skill from a Dashboard URL

**Input:** User provides a dashboard URL and requests generating a query skill

**Output:** Pre-validation passes → Parse dashboard components → Output analysis framework matching → Generate `skills/qbi-xxx-{first 8 chars of pageId}/SKILL.md` → Install into the skill center

### Example 2: Generate a Query Skill from a Data Portal URL

**Input:** User provides a data portal URL (with productId/menuId)

**Output:** First resolve the associated dashboard pageId via OpenAPI, then follow the same flow as Example 1

---

## Important Notes

1. **Intent Routing Accuracy**: The intent routing matrix determines whether a user question can be correctly matched to a dataset and needs to be inferred carefully
2. **Analysis Framework MUST Be Output**: Step 2.3.2 is a mandatory step; the analysis framework matching result MUST be output before summarizing the exploration results

---

## Appendix

See [reference document](module-dashboard-reference.md) for tool functions, API error codes, and other detailed references.
