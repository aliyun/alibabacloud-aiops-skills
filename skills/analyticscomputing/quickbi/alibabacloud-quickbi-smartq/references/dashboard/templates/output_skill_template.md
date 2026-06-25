# Phase 2 Dynamic Field Format Reference

> Format examples for each field in `next_step.stdin_schema.dynamic_sections`. The LLM only needs to generate the following fields; all other sections are concatenated automatically by the script.

## 1. frontmatter_yaml

```yaml
---
name: {skill-name}
description: >
  **Dedicated query skill** for the QuickBI "{dashboard title}" dashboard.
  Use this skill INSTEAD OF generic quickbi-smartq-chat when the user asks about:
  {5-8 core measure fields, comma-separated}.
  Trigger keywords: {dashboard title/abbreviation}, {3-5 business topic keywords}.
---
```

> **Note**: Select 5-8 metrics users ask about most often for core measures; select 3-5 topic terms unique to this dashboard for business topics; `INSTEAD OF generic quickbi-smartq-chat` MUST be retained.

## 2. metadata_comment

```markdown
<!-- SKILL_METADATA
dashboard_page_id: {pageId}
skill_generated_at: {gmtModified value at generation time}
dashboard_name: {dashboard title}
generator_skill: quickbi-smartq-chat
-->
```

> **Note**: `skill_generated_at` directly uses `dashboardData.basicInfo.gmtModified`; `generator_skill` is always `quickbi-smartq-chat`.

## 3. title_and_desc

```markdown
# {dashboard title} - Data Query

A dedicated query skill for the "{dashboard title}" dashboard, supporting natural-language queries (both English and Chinese) for dashboard-related data.
```

## 4. basic_info_table

```markdown
| Attribute | Value |
|-----------|-------|
| Name | {title} |
| URL | `{url}` |
| pageId | `{pageId}` |
```

> **Note**: Both pageId and URL come from the script return values (`result["pageId"]` / `result["dashboardUrl"]`), not from the raw URL provided by the user.

## 5. business_context

> **Note**: Only generate this section when the dashboard has statistical caliber definitions, filter rules, or charts with complexFilter; otherwise output an empty string.

- **Business topic**: business domain inferred from the dashboard title
- **Core metrics**: key metrics extracted from chart titles and measure fields
- **Analysis dimensions**: key dimensions extracted from dimension fields
- **Statistical caliber**: metric definitions identified from rich text; if none, write "No special description"
- **Filter conditions**: extracted from rich text + `chart_summary[].filters[].complexFilter`; if none, write "None"

## 6. intent_routing_matrix

```markdown
| EN Keywords | CN Keywords | Target Chart | Component ID | Dataset ID | Analysis Theme | Analysis Level | Routing Explanation |
|-------------|-------------|--------------|--------------|------------|----------------|----------------|---------------------|
| {keyword1}, {keyword2} | {keyword1_cn}, {keyword2_cn} | {chart name} | `{componentId}` | `{sourceId}` | {theme} | L1/L2/L3/L4 | {explanation} |
```

**Routing rules** (priority descending): measure field names → dimension field names → chart type features → analysis themes → all dataset IDs (fallback when matching fails)

> **Note**: Keywords MUST include both English and Chinese to support bilingual user queries.

## 7. analysis_insights

**Metric relationships** — infer calculation relationships from field names (supports attribution analysis; only output clearly inferable ones):

```markdown
- Profit = Sales Amount − Cost
- Gross Margin = Profit / Sales Amount × 100%
- Average Order Value = Sales Amount / Order Count
```

**Linkage and drill-down paths**:

```markdown
| Source Level | Source Chart | Interaction | Target Level | Target Chart | Analytical Use |
|--------------|--------------|-------------|--------------|--------------|----------------|
| L1 | {KPI card} | Click / filter | L2 | {trend chart} | Drill down from overview to trend |
| L2 | {trend chart} | Click time point | L3 | {distribution chart} | Drill down from trend to dimensions |
| L3 | {distribution chart} | Click dimension value | L4 | {detail table} | Drill down from dimensions to details |
```

## 8. chart_filter_conditions

Array type; generate a filter condition description for each chart (with or without `complexFilter`) in chart order. Use `"none"` when there are no filter conditions:

```json
["order_status = completed AND region IN (East, South)", "none", "time >= 2024-01-01"]
```
