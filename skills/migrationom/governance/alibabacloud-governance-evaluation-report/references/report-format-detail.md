# Report Format: Individual Check-Item Analysis

**Use cases**:

- The user asks about one specific check item, such as an MFA check or a check
  identified by ID.
- The user asks how to remediate a check item, such as MFA enforcement or
  exposure of high-risk ports.
- The user asks for the non-compliant resources associated with a check item.

**Data sources**:

- Check-item details: JSON output from `detail --id <metric-id>` or
  `detail --keyword <keyword>`.
- Non-compliant resources: JSON output from `resources --id <metric-id>`,
  retrieved only when needed.

---

## Format Template

### Check-Item Details Without a Resource List

```markdown
## Check-Item Details: {DisplayName}

| Attribute | Value |
| --- | --- |
| Check Item ID | `{Id}` |
| Pillar | {CategoryCN} |
| Priority | {RecommendationLevelCN} |
| Current Status | {Risk mapped to High / Medium / Low / Compliant} |
| Compliance Rate | {Compliance*100:.0f}% |
| Non-Compliant Resources | {NonCompliant, if available, otherwise "N/A"} |
| Potential Score Increase | +{PotentialScoreIncrease:.1f} {if available, otherwise omit this row} |

### Check Description

{Description: the full description of what this check item evaluates.}

### Current Risk Analysis

{Agent analyzes:
- Why this check item is in its current risk state
- What the compliance rate means in practical terms
- Potential impact of non-compliance on security, cost, or stability
}

### Remediation

{Parse the Remediation array and present each remediation option.
For each remediation:}

#### Option {N}: {RemediationType mapped to "Manual Remediation", "Assisted Analysis", or "Quick Remediation"}

{For each entry in Steps:}

**{Classification, if present}**

{Description: what this step does.}

{If Suggestion is present:}
> Recommendation: {Suggestion}

{If CostDescription is present:}
> Cost: {CostDescription}

{If Notice is present:}
> Notice: {Notice}

{If Guidance is present, for each guidance entry:}

**{Title}**

{Content}

{If ButtonRef is present:}
[{ButtonName}]({ButtonRef})

{End of steps.}
{Repeat for each remediation option.}
```

### Check-Item Details With a Resource List

When the user explicitly asks for non-compliant resources, or when listing
specific resources materially improves the explanation, append the resource
section below to the preceding report.

Call `resources --id <metric-id>` to retrieve the resource data.

```markdown
### Non-Compliant Resources

Total: {TotalCount} non-compliant resources

| Resource ID | Resource Name | Resource Type | Region | Key Properties |
| --- | --- | --- | --- | --- |
| {ResourceId} | {ResourceName, or "-"} | {ResourceType} | {RegionId} | {Agent: select the one or two most relevant values from Properties} |
| ... | ... | ... | ... | ... |

{If TotalCount is greater than the displayed count:}
> Showing the first {N} of {TotalCount} resources. Increase `--max-results` to
> retrieve more.

### Remediation Advice

{Agent generates advice based on the actual non-compliant resources:
- Group similar resources when applicable, such as five RAM users without MFA
- Provide concrete next steps
- Highlight resources that need priority attention, such as a root account or
  production resources
}

---

### Related Check Items

{Agent uses pillar data already cached from the same overview or pillar query
and selects two to five related check items in the same Category or topic.
Include only risky items where Risk is not "None". Omit this section when no
related risky items exist.}

Other risky items in the {CategoryCN} pillar:

| Check Item | Risk Level | Compliance Rate |
| --- | --- | --- |
| {DisplayName} | {RiskCN} | {Compliance*100:.0f}% |
| ... | ... | ... |

---

To explore further, you can ask:

- For a related item: "**Show details for {a related DisplayName}.**"
- For affected resources: "**Which resources are non-compliant for {current DisplayName}?**" {only if the resource list was not already shown}
- For the complete pillar: "**Analyze all checks in the {CategoryCN} pillar.**"
```

---

## Formatting Rules

- Write the final report in the user's language. Localize headings and fixed
  labels when appropriate, while keeping API field values and command
  parameters exact.
- **Do not use emoji**; maintain a professional tone throughout.
- Use a vertical key-value table for check-item attributes.
- Map `Risk` values as follows: `Error` to high risk, `Warning` to medium risk,
  `Suggestion` to low risk, and `None` to compliant.
- Present the API's `Remediation` data faithfully and do not invent steps.
- Preserve console URLs from `ButtonRef` as Markdown links.
- In the Key Properties column, select the one or two `Properties` values that
  best explain the issue, such as `MFAEnabled: false`.
- When more than 20 resources exist, show the first 20 and state the total.
- When `detail --keyword` returns multiple matches, show the match list and ask
  the user to select one instead of expanding every item.

## Follow-up Guidance Rules

- Always end the report with follow-up guidance that helps the user continue
  exploring.
- Base guidance on actual report data and insert real check-item and pillar
  names into suggested questions.
- Offer two or three directions as a list and bold the suggested questions.
- Adapt directions to the context:
  - If no resource list is shown, offer to list non-compliant resources.
  - If resources are already shown, offer a pillar-level analysis or a return
    to the overview.
  - If related risky items exist, prioritize a specific related item.
- In Related Check Items, select risky items from the same pillar, excluding
  the current item. Prefer topically related or higher-risk items and omit the
  section when none exist.
- Do not use emoji.
