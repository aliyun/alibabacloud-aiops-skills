# Report Format: Pillar or Keyword Analysis

**Use cases**:

- The user asks for analysis by pillar, such as security or cost optimization.
- The user asks for analysis by keyword or topic, such as network security or
  database risks.
- The user specifies filters, such as high-priority security issues or
  reliability issues at medium risk or above.

**Data sources**:

- Pillar analysis: JSON output from `pillar -c <Category>`.
- Keyword analysis: when `detail --keyword <keyword>` returns multiple matches,
  retrieve each match with `detail --id`, or filter the `pillar` output by
  keyword.

**Design principle**: A pillar report is the second level of the analysis
funnel. The user has selected an area, so show the complete risk picture for
that area while controlling information density. Explain high risks in detail
and summarize low risks.

---

## Format Template

```markdown
## Governance Analysis: {CategoryCN} Pillar

> Adjust the title to the user's intent when appropriate, for example,
> "Network Security Analysis" or "Database Risk Analysis."

**Latest evaluation time**: {EvaluationTime, format: YYYY-MM-DD HH:MM:SS}

**Overall score**: {TotalScore*100:.1f}

**Analysis scope**: {CategoryCN} pillar, {MatchedCount} checks
{If filtered: "Filters: risky items only / high priority only / other filters"}

### Summary

{Agent summarizes:
- Overall compliance for the pillar or topic
- Risk distribution: N high, N medium, and N recommendations
- Areas where the main issues are concentrated
}

### High-Risk Items

{If there are no Error items, state "There are currently no high-risk items."}

| Check Item | Priority | Compliance Rate | Non-Compliant Resources | Description |
| --- | --- | --- | --- | --- |
| {DisplayName} | {RecommendationLevelCN} | {Compliance*100:.0f}% | {NonCompliant} | {Agent: brief explanation of risk and impact} |
| ... | ... | ... | ... | ... |

### Medium-Risk Items

{If there are no Warning items, state "There are currently no medium-risk
items."}

{See "Item Count Rules" for display limits.}

| Check Item | Priority | Compliance Rate | Non-Compliant Resources | Description |
| --- | --- | --- | --- | --- |
| {DisplayName} | {RecommendationLevelCN} | {Compliance*100:.0f}% | {NonCompliant} | {Agent: brief explanation} |
| ... | ... | ... | ... | ... |

{If truncated:}
> Showing the first {N} items. Another {remaining} medium-risk items are not
> listed. Ask for the complete list if needed.

### Recommended Improvements

{By default, show only the count and do not list individual items.}

There are {suggestion_count} recommended improvements, all at low risk. Ask for
details if needed.

{If the user explicitly asks for every item, list them in a table.}

### Governance Recommendations

{Agent generates targeted recommendations for this pillar or topic.
Each recommendation has a title and directly references risk items above.}

#### 1. {Recommendation title}

{Specific actionable content that references relevant risk items.
Include a concrete next step, such as prioritizing {DisplayName} and reviewing
its remediation guidance.}

#### 2. {Recommendation title}

{...}

{Provide two or three recommendations ordered by risk severity.}

---

To explore further, you can ask:

- For details and remediation: "**Show details and remediation for {a risky DisplayName from the report}.**"
- For affected resources: "**Which resources are non-compliant for {a risky DisplayName}?**"
- For another pillar: "**Analyze the {another pillar} pillar.**"
```

---

## Item Count Rules

- **High-risk items (`Error`)**: show every item. These are usually few and are
  the main reason the user opened the pillar report.
- **Medium-risk items (`Warning`)**:
  - Five or fewer: show every item.
  - More than five: show the top five by `RecommendationLevel` and summarize
    the remainder.
- **Recommended improvements (`Suggestion`)**: show only the count by default.
  Expand the list only when the user explicitly requests it.
- If the user specifies `--risk` or `--level`, show the filtered result without
  applying additional truncation.

## Formatting Rules

- Write the final report in the user's language. Localize headings and fixed
  labels when appropriate, while keeping field names and command values exact.
- **Do not use emoji**; maintain a professional tone throughout.
- Adjust the title to the analysis dimension:
  - For pillar analysis, use "Governance Analysis: {CategoryCN} Pillar."
  - For keyword analysis, use "{keyword} Check Analysis."
- Separate items by risk level in descending severity, and sort each section by
  priority.
- In the Compliance Rate column, calculate `Compliance * 100` and show an
  integer percentage.
- In the Non-Compliant Resources column, use `NonCompliant`, or `-` when absent.
- In the Description column, summarize the risk meaning using the check item's
  `Description` and actual result.
- Keep an empty risk-level section and state that it has no current items.
- Give each recommendation a heading and tie it to specific risk items.

## Follow-up Guidance Rules

- Always end the report with follow-up guidance that helps the user continue
  the analysis.
- Base guidance on actual report data and insert real check-item and pillar
  names into suggested questions.
- Offer two or three directions as a list and bold the suggested questions.
- For a pillar report, follow-up directions may include remediation for a
  specific item, affected resources, or comparison with another pillar.
- Do not use emoji.
