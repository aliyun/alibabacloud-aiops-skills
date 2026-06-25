## Workflow

### Step 1: Understand the User Question

Refer to the "Dashboard Knowledge Base", "Analytical Approach", and "Analysis Path" sections to understand the user question. **You MUST output the understanding result**:

1. **Parse the user question**: extract keywords (metrics, dimensions, time range, filter conditions). The user may ask in Chinese or English — match both EN and CN columns of the intent routing matrix.

2. **Combine with the knowledge base**:
   - Cross-reference the "Chart Components" table to identify the involved charts and datasets
   - Cross-reference the "Analytical Approach" to match the applicable scenario
   - Cross-reference the "Business Logic" to understand metric relationships

3. **[Required output] Understanding result** (output in the user's language): user intent, matched analysis scenario, involved metrics, involved dimensions

### Step 2: Categorize and Decompose the Question

Based on Step 1, categorize the question and emit an analysis plan:

#### Categorization Rules

| Type | Criteria | Handling |
|------|----------|----------|
| **Simple question** | The question matches a specific chart name | No decomposition; query the dimensions+metrics of that chart directly |
| **Composite question** | Requires multi-dimensional analysis or attribution | Decompose into 2-3 sub-questions |

#### Sub-question Decomposition Rules (composite questions only)

1. **Three elements**: every sub-question must specify `dimension` + `metric` + `purpose`
2. **Single-table principle**: each sub-question should let SmartQ return a single table, avoiding multi-dimensional crosses
3. **Query order**: arrange in L1→L2→L3 logical order (overview → dimension drill-down → detail lookup)
4. **Dynamic supplementation**: append more questions based on query results (count is not fixed)
5. **Ratio handling**: if the question involves a ratio (e.g., growth rate, conversion rate), try a direct query first; if SmartQ cannot recognize it or the result is abnormal, decompose into base metrics (numerator/denominator) and compute manually

#### Output Format (shown to the user, use the user's language)

Output an analysis plan table containing: user question, analysis level, sub-question list (with dimension, metric, purpose)

### Step 3: Build the Query

**Query-construction constraints**:
1. **Filter conditions**: chart filter fields in the table are in "dataset original names". Append the matched chart filter (pseudo-code) to the query as unambiguous natural language.

**Do NOT append when**:
- The user question already contains the exact same filter
- The filter clearly conflicts with the user question

> **Example** (assuming the chart filter is `region = 'East China'`):
> - **Duplicate → do NOT append**: user asks "What is the sales of East China?" — already covered, appending would duplicate
> - **Conflict → do NOT append**: user asks "What is the sales of North China?" — conflicts with the filter; honor the user's intent
> - **Normal → append**: user asks "What is the sales?" — region not mentioned, append the filter

2. **Field replacement**: refer to the "Field Mapping" table; when a field appears in the mapping, use the "dataset original name" instead of the "chart display name". Fields not in the mapping table are already consistent — use them as-is.
> **Example**: mapping lists "Sales Amount -> Net Sales"; user asks "Sales Amount trend" -> build the query as "Net Sales trend".

Build the query based on the question category:

- **Simple question**: output the query (field names use dataset original names) + dataset ID
- **Complex question**: output a sub-question list table, with sub-questions (field names use dataset original names), dataset ID, and analysis purpose

**Fallback**: if no specific chart matches, collect all chart components' `Dataset ID`s, deduplicate, and pass them as the multi-dataset input parameter.

### Step 4: Call SmartQ

Use the query built in Step 3 and call the `query_openapi` function in the bundled `scripts/quickbi_openapi.py`:

```python
import sys, os
sys.path.insert(0, os.path.join('__SKILL_DIR__', 'scripts'))
from quickbi_openapi import query_openapi
from config_loader import load_config

# Load config (priority: env > workspace > global > package default)
config = load_config()

# Simple question: single call
result = query_openapi(
    endpoint=config["server_domain"],
    access_key_id=config["api_key"],
    access_key_secret=config["api_secret"],
    question=query_question,
    user_id=config["user_token"],
    cube_id=dataset_id  # single dataset ID, or multiple IDs comma-separated
)

# Complex question: loop over each sub-question
results = []
for sub_question in sub_questions:
    result = query_openapi(
        endpoint=config["server_domain"],
        access_key_id=config["api_key"],
        access_key_secret=config["api_secret"],
        question=sub_question["question"],
        user_id=config["user_token"],
        cube_id=sub_question["cube_id"]
    )
    results.append({"sub_question": sub_question, "result": result})
    # Decide dynamically whether to append more queries based on the result
    # e.g., when an outlier is found, append a third question for deeper analysis
```

**Multi-call rules**:
- Each sub-question makes one independent call to `query_openapi`, capped at **3 calls** (minimalism principle)
- Execute in the order produced in Step 1
- **Dynamic supplementation**: if earlier results show an anomaly (e.g., a dimension value too high or too low), append the next question for deeper analysis

**Important constraints**:
- **When data is returned normally, do NOT try other methods**: when the API returns data normally (including empty or all-zero data), display it directly
- **Only fall back to the browser on errors**: only when the API returns errors (interface failure, network failure, permission issues) attempt to open the dashboard
- **Do NOT inject personal judgment**: do not judge data plausibility; show the raw API result

### Step 5: Summarize and Display the Result

Display the result based on the question category. **Use the user's language**. Include smart summary and result table. For complex questions, also provide a comprehensive analysis of all sub-question results to answer the user's original question.

**Source link notes**:
- Get the URL from "Dashboard Knowledge Base - Basic Information - URL"
- If the question matched a specific chart component, append `&componentId={componentId}&highlight=true` to the URL

## Error Handling

| Scenario | Detection | Strategy |
|------|---------|----------|
| Failed to understand the question | No valid keywords extracted | Ask the user (in their language) what data they want to query |
| Failed intent match | No chart component matched | Fall back to using all dataset IDs |
| API call failed | Returns error code | Use the error code to prompt the user in their language (permissions, instance expiration, etc.) |
| Some sub-questions failed | Some API calls failed | Show successful results and annotate failed sub-questions |

**Note**: data successfully returned by the API (including empty or all-zero data) should be shown directly; do not re-query or "correct" it.

**Error message language**: all user-facing error messages MUST follow the detected language. Use locale-matching wording when asking for clarification or reporting errors.
