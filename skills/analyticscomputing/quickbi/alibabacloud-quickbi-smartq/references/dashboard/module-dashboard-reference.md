# QuickBI Dashboard Skill Generator - Reference Document

> This document contains detailed reference content for SKILL.md, for in-depth understanding and use.

## Analysis Framework Matching Rules

### Framework Matching Rules Table

Match the most suitable analysis framework by combining **metric semantics + layout pattern + linkage relationships**.

| Matching Rule (based on real field names) | Analysis Framework | Applicable Scenario | Core Formula / Method |
|---------------------------|---------|---------|--------------|
| Contains "sales amount/revenue" + "cost" + "profit" + "gross margin/profit rate" | **DuPont Analysis** | Financial metric decomposition, profitability analysis | ROE = Profit Rate × Asset Turnover Ratio × Equity Multiplier |
| Contains "acquisition/new users" + "activation" + "retention" + "conversion" + "revenue/payment" | **AARRR Pirate Model** | Internet product growth funnel analysis | Optimization of conversion rates at each stage |
| Contains "most recent purchase time" + "purchase frequency" + "spending amount" | **RFM Customer Analysis** | Customer value segmentation, precision marketing | R×F×M scoring matrix |
| Contains "product/goods" dimension + "market share/growth rate" | **Boston Matrix** | Product portfolio strategy analysis | Star / Cash Cow / Question Mark / Dog classification |
| Contains "step/stage/phase" dimension + "conversion rate/churn rate" | **Funnel Analysis** | Process optimization, locate the dropout stage | Conversion rate at each stage = next step / previous step |
| Contains "target value/planned value" + "actual value/completed value" | **Goal Achievement Analysis** | KPI completion monitoring | Achievement rate = actual value / target value × 100% |
| Contains "same period/year-over-year" + "current period/this period" | **Period-over-Period & Year-over-Year Analysis** | Time-based comparison trend analysis | YoY = (current period − same period) / same period × 100% |
| Contains "budget" + "actual/execution" | **Budget vs. Actual Analysis** | Budget execution monitoring | Budget execution rate = actual / budget × 100% |
| Contains "inventory/stock" + "turnover/sell-through" | **Inventory Analysis** | Inventory health monitoring | Turnover rate = cost of sales / average inventory |
| Contains "average order value" + "customer count/user count" + "sales amount" | **Customer Value Analysis** | Customer contribution analysis | Sales Amount = Customer Count × Average Order Value |
| Contains "impression/display" + "click" + "conversion/transaction" | **Marketing Funnel Analysis** | Advertising effectiveness analysis | CTR / CVR and other conversion metrics |
| Contains "workforce/headcount" + "output/efficiency" | **Workforce Efficiency Analysis** | Human resource efficiency analysis | Per-capita output = total output / headcount |
| None of the above match | **L1-L4 Pyramid** | General hierarchical analysis framework | Overview → Trend → Breakdown → Detail |

---

## Layout Pattern Analysis Rules

### Layout Pattern Identification

Infer the dashboard's overall analysis pattern based on `tileLayout` positional information.

| Layout Characteristic | Layout Pattern | Typical Feature | Inferred Dashboard Type |
|---------|---------|---------|----------------|
| First row has multiple indicator-card type components | **Metric Matrix** | Dense metric card array at the top | Monitoring dashboard (emphasizing L1 overview) |
| Contains line/bar trend charts | **Core Chart** | Focus layout with primary and secondary emphasis | Analytical dashboard (emphasizing L2/L3) |
| Bottom has a common-table | **Detail-Oriented** | Detail table at the bottom | Operational dashboard (emphasizing L4 traceability) |
| Multiple components of the same type in the same row | **Comparative Analysis** | Parallel layout facilitating comparison | Multi-dimensional comparative analysis |
| Few components (≤4) | **Focused Analysis** | Few but focused core charts | Thematic analysis dashboard |

### Relationship Between Layout Patterns and Analysis Frameworks

| Layout Pattern | Preferred Analysis Framework | Confidence Improvement Basis |
|---------|--------------|---------------|
| Metric Matrix | Goal Achievement Analysis, Period-over-Period & Year-over-Year Analysis | Multiple metrics side by side → focus on metric comparison |
| Core Chart | Trend Analysis, Funnel Analysis | Large chart as the main focus → focus on process changes |
| Detail-Oriented | L1-L4 Pyramid | Has detail table → requires traceability capability |
| Comparative Analysis | DuPont Analysis, Customer Value Analysis | Side-by-side layout → focus on dimension comparison |

---

## Hierarchical Classification Rules

### L1-L4 Level Determination

| Level | Type Characteristic | Position Characteristic |
|-----|---------|----------|
| **L1** | indicator-card/kpi/gauge | y ≤ 20 (top) |
| **L2** | line/area/indicator-trend | 20 < y < 50, contains a datetime dimension |
| **L3** | bar/pie/ranking-list | 30 < y < 70, contains categorical dimensions |
| **L4** | common-table | y > 50 (bottom) |

### Analysis Theme Inference (Based on Chart Type)

| Chart Type | Analysis Theme Pattern |
|---------|-------------|
| indicator-card/kpi | "{measure} metric display" |
| line/area | "{measure} temporal trend" |
| pie | "{dimension} distribution/share" |
| bar | "{dimension} comparative analysis" |
| ranking-list | "{dimension} ranking" |
| common-table | "{topic} detail query" |

---

## Intent Routing Rules

### User Query Pattern Matching

| User Query Pattern | Extracted Intent | Match Target |
|-------------|-----------|----------|
| "How much is XX / How many XX" | Query a single metric | L1 metric card |
| "How much is XX / What is XX" | Query a single metric | L1 metric card |
| "XX trend / movement / change" | Trend analysis | L2 line chart / trend chart |
| "XX trend / movement / change" | Trend analysis | L2 line chart / trend chart |
| "XX ranking / TOP / highest / lowest" | Ranking analysis | L3 ranking list |
| "XX ranking / TOP / highest / lowest" | Ranking analysis | L3 ranking list |
| "XX distribution / share / composition" | Structure analysis | L3 pie chart / bar chart |
| "XX distribution / share / composition" | Structure analysis | L3 pie chart / bar chart |
| "Each XX's YY" | Dimension breakdown | L3 grouped chart |
| "YY by each XX" | Dimension breakdown | L3 grouped chart |
| "XX detail / details / list" | Detail query | L4 detail table |
| "XX details / list" | Detail query | L4 detail table |
| "Why did XX decrease / increase" | Attribution analysis | L1→L2→L3 combined |
| "Why did XX decrease / increase" | Attribution analysis | L1->L2->L3 combined |

---

## Business Logic Inference Rules

### Inference Formulas for Metric Combinations

| Metric Combination | Inference Formula |
|---------|----------|
| Sales Amount + Cost + Profit | Profit = Sales Amount − Cost |
| Sales Amount + Sales Volume | Average Order Value = Sales Amount / Sales Volume |
| Target Value + Actual Value | Achievement Rate = Actual / Target × 100% |
| Current Period + Same Period | YoY Growth Rate = (Current Period − Same Period) / Same Period × 100% |
| Current Period + Previous Period | PoP Growth Rate = (Current Period − Previous Period) / Previous Period × 100% |

---

## Utility Function Reference

### quickbi_openapi.py Function List

| Function Name | Purpose | Usage Stage |
|--------|------|----------|
| `load_config(config_path=None)` | Load configuration (priority: environment variables > working-directory level > global > package default) | Step 1.0, Step 2.1 |
| `is_dataportal_url(url)` | Determine whether it is a data portal URL | Step 1.0 |
| `extract_dataportal_ids(url)` | Extract productId and menuId from a data portal URL | Step 1.0 |
| `get_dataportal_page_id(...)` | Retrieve the dashboard pageId associated with a data portal via OpenAPI | Step 1.0 |
| `extract_page_id(url)` | Extract pageId from the dashboard URL | Step 1.0 |
| `validate_and_prepare_dashboard(...)` | Dashboard pre-validation and preprocessing | Step 1.0 |
| `get_dashboard_json(...)` | Get the complete dashboard JSON data | Step 2.1 |
| `query_openapi(...)` | Call the SmartQ query API | Generated skill query stage |
| `get_dashboard_update_time(...)` | Query dashboard update time | Generated skill startup validation |

### get_dashboard_json.js Function List

| Function Name | Purpose |
|--------|------|
| `parseDashboardJson(json)` | Parse the raw dashboard JSON and extract component structure and field mapping |
| `findFieldInfoFromSchema(pathId, fields)` | Find field caption and name from dataset schema |
| `buildFieldMappingEntry(col, fieldSettingMap, schemaFields)` | Build a field mapping entry (chart display name → dataset original name) |
| `analyzeLayout(charts)` | Analyze chart layout based on tileLayout |

### config_loader.py Function List

| Function Name | Purpose |
|--------|------|
| `load_config()` | Four-layer configuration loading (priority: environment variables > working-directory level > global > package default) |
| `persist_to_global_config(key, value)` | Write to global configuration `~/.qbi/config.yaml` |

---

## Error Code Reference

### Pre-validation API Error Codes

| Error Code | Meaning | Handling Recommendation |
|--------|------|----------|
| `AE0510000005` | User is not in the organization | Check whether user_token is correct |
| `AE0510150002` | No dashboard access permission | Check whether the user has access permission for the dashboard |
| `AE0510200000` | No dataset management or authorization permission | Check whether there are dataset management and SmartQ configuration permissions |
| `AE0581030022` | SmartQ functionality has not been purchased | Confirm that the SmartQ feature has been purchased |
| `OE10010106` | API not authorized | Check the api_key/api_secret configuration |
| `CONNECTION_ERROR` | Network connection failed | Check the network and server_domain configuration |

### Data Portal API Error Codes

| Error Code | Meaning | Handling Recommendation |
|--------|------|----------|
| `NO_PAGE_ID` | The data portal menu is not linked to a dashboard | Check whether the portal menu is correctly configured with a dashboard page |
| `CONNECTION_ERROR` | Network connection failed | Check the network and server_domain configuration |

---

## dashboardData Data Structure

Complete data structure returned after Step 2.2 parsing:

```typescript
{
  success: boolean;
  basicInfo: {
    name: string;           // Dashboard name
    pageId: string;         // Page ID
    workspaceId: string;    // Workspace ID
    gmtModified: number;    // Last modified time (millisecond timestamp), used for skill_generated_at
  };
  queryControls: Array<{    // Query controls list
    componentId: string;
    internalId: string;
    needManualQuery: boolean;
    fields: Array<{
      labelName: string;
      componentType: string;  // datetime / enumSelect
      relatedGraphIds: string[];
    }>;
  }>;
  chartComponents: Array<{  // Chart components list
    componentId: string;
    componentName: string;
    sourceId: string;       // Dataset ID - key for SmartQ calls
    componentType:string
    dimensions: Array<{caption: string; pathId: string}>;
    measures: Array<{caption: string; aggregateType: string}>;
    defaultFilters: Array<{
      key: string;              // Field key
      caption: string;          // Field name
      complexFilter: object | null;   // Filter configuration (conditions & values)
      aggregator: string | null;      // Aggregation type
      itemType: string;         // dimension / measure / datetime / geographic
      colType: string | null;   // Column type
    }>;
    drillFields: Array<{caption: string}>;
    tabInfo: object | null; // Tab ownership relationship
  }>;
  tabComponents: Array<{    // Tab components list
    componentId: string;
    tabs: Array<{id: string; title: string}>;
  }>;
  richTextComponents: Array<{textContent: string}>;
  layoutAnalysis: {rows: Array};  // Layout analysis
  fieldMapping: {             // Field mapping (grouped by dataset, only fields where caption !== originalCaption)
    [sourceId: string]: {     // Key is the dataset ID (only datasets with mapped fields are included)
      datasetName: string | null;  // Dataset name
      fields: Array<{
        caption: string;           // Chart display name (the name shown to users)
        originalCaption: string;   // Original field title saved in chart JSON (col.caption), unaffected by dataset-level aliases
        pathId: string | null;     // Field path ID
        itemType: string | null;   // Field type: dimension / measure / datetime / geographic
        charts: Array<{componentId: string; componentName: string}>;  // Charts in which this field appears (with chart ID and name)
      }>;
    };
  };
}
```

### fieldMapping Field Description

`fieldMapping` establishes a mapping from chart display name → dataset original name, used for precise field matching during SmartQ queries. **Only fields where `caption !== originalCaption` are included** (identical fields need no mapping and are filtered at the data layer); only datasets with mapped fields are included (datasets where all field names are identical will not appear in fieldMapping).

**Mapping Layers**:

| Layer | Field | Meaning | When It Has a Value |
|------|------|------|----------|
| Chart display name | `caption` | The field name displayed on the chart, combining alias and dataset title | Always has a value |
| Dataset original name | `originalCaption` | Original field title saved in chart JSON (col.caption), unaffected by dataset-level aliases | Always has a value |

> Note: Fields where `originalCaption` is `null` are filtered at the data layer and will not appear in fieldMapping.

**Typical Scenarios**:
- User set alias "Sales Amount" in chart, but original title in chart JSON is "Sales Revenue" → `caption="Sales Amount"`, `originalCaption="Sales Revenue"` (different, shown in mapping)
- Dataset-level alias changed to "Sales Amount", but chart JSON still has "Sales Revenue" → `caption="Sales Amount"` (from schema), `originalCaption="Sales Revenue"` (from col.caption) (different, shown in mapping)
- User asks about "Region", and dataset original name is also "Region" → `caption="Region"`, `originalCaption="Region"` (identical, filtered at data layer, not in fieldMapping)
- Chart JSON has no caption → `originalCaption=null` (filtered at data layer, not in fieldMapping)
