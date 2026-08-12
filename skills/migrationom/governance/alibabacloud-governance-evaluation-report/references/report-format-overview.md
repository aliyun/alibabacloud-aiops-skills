# Report Format: Overall Overview

**Use case**: The user asks about the account's overall health, maturity score,
or a comprehensive report without specifying a pillar or check item.

**Data source**: JSON output from `overview` mode.

**Design principle**: The overview is the entry point of the analysis funnel. It
must provide a **quick diagnosis, focus attention, and guide deeper analysis**
instead of enumerating every risk item.

---

## Format Template

```markdown
## Governance Evaluation Report

**Latest evaluation time**: {EvaluationTime, format: YYYY-MM-DD HH:MM:SS}

**Overall summary**: The current governance maturity score is
{TotalScore*100:.1f}.
{Agent summarizes the overall condition in one or two sentences, identifies
which pillars contain most issues, and states what needs attention first.}

### Risk Distribution by Pillar

| Pillar | High Risk | Medium Risk | Recommendations | Summary |
| --- | --- | --- | --- | --- |
| Security | {Error} | {Warning} | {Suggestion} | {Agent: one-sentence summary} |
| Reliability | {Error} | {Warning} | {Suggestion} | {Agent: one-sentence summary} |
| Cost | {Error} | {Warning} | {Suggestion} | {Agent: one-sentence summary} |
| Operational Efficiency | {Error} | {Warning} | {Suggestion} | {Agent: one-sentence summary} |
| Performance | {Error} | {Warning} | {Suggestion} | {Agent: one-sentence summary} |

### Priority Risk Items

{Agent selects the most critical risk items to highlight.
Selection criteria are defined in the "Item Count Rules" section below.
Group selected items by logical topic or domain, such as identity and access,
network security, or data protection.}

#### {Group Name}

| Risk Item | Risk Level | Pillar | Description |
| --- | --- | --- | --- |
| {DisplayName} | High | {CategoryCN} | {Agent: brief explanation of risk and impact} |
| ... | ... | ... | ... |

{Repeat for each group.}

{After listing the selected items, summarize omitted items:}
> The table shows the highest-priority risks. Another {remaining_error}
> high-risk items, {warning_count} medium-risk items, and {suggestion_count}
> recommendations are not listed. Ask for a pillar-level analysis to explore
> them.

{If there are no high-risk items, state "There are currently no high-risk
items." and omit the grouping.}

### Governance Recommendations

{Agent generates two or three focused, actionable recommendations.
Each recommendation must have a title and directly reference risk items shown
above.}

#### 1. {Recommendation title}

{Specific actionable content that references relevant risk items and includes
a concrete next step, such as reviewing the Security pillar in detail or
prioritizing remediation for {DisplayName}.}

#### 2. {Recommendation title}

{...}

#### 3. {Recommendation title}

{...}

---

To explore further, you can ask:

- For details about a pillar: "**Analyze the {pillar with most risks} pillar.**"
- For remediation of a risk item: "**How do I remediate {a high-risk DisplayName from the report}?**"
- For affected resources: "**Which resources have {a risk topic from the report}?**"
```

---

## Item Count Rules

The overview must remain focused. Apply these rules when selecting priority
risk items:

- **Five or fewer high-risk items**: show all of them.
- **Six to ten high-risk items**: show all of them, but keep each description
  to one sentence.
- **More than ten high-risk items**: show the top ten by
  `RecommendationLevel` (`Critical`, `High`, `Medium`, then `Suggestion`) and
  summarize the rest numerically.
- **Medium-risk items and recommendations**: do not list them individually in
  the priority section; include their counts in the pillar table and summary.
- If there are no high-risk items but medium-risk items exist, show the top
  three to five medium-risk items as priority items.

## Formatting Rules

- Write the final report in the user's language. Localize headings and fixed
  labels when appropriate, while keeping field names and command values exact.
- **Do not use emoji**; maintain a professional tone throughout.
- Enter plain numbers in the risk-distribution table without prefixes.
- In the Summary column, describe the actual result of each pillar in one
  sentence. State that the pillar is fully compliant when applicable.
- Group priority risk items by logical topic, including across pillars when
  related items belong together.
- Give each governance recommendation a heading. Provide two or three
  recommendations, each tied to specific risks instead of generic advice.
- Use a blockquote for the omitted-item summary and provide accurate counts.

## Follow-up Guidance Rules

- Always end the report with follow-up guidance that helps the user continue
  the analysis.
- Base guidance on actual report data rather than generic examples.
- Fill guidance prompts with real pillar names, risk-item names, and topics
  selected from the report.
- Offer two or three directions as a list and bold the suggested questions.
- Prefer directing the user to the pillar with the most risks or the most
  severe risk item.
- Do not use emoji.
