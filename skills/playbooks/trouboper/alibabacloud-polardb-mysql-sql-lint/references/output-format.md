# Output Format Specification

All SQL diagnostic reports MUST follow this exact format structure. Do NOT omit any section.

## Standard Output Example

The script outputs an English report. The agent should present a user-friendly report (Chinese or English based on user language) by interpreting the script output. Below is the script output format:

```
SQL Diagnosis Report

[CRITICAL]

  1. Charset Issue (RULE-070)
     Suggestion: Change to CHARSET=utf8mb4

[WARNING]

  2. Leading Wildcard Issue (RULE-022)
     SQL: SELECT * FROM products WHERE title LIKE '%test%'
     Suggestion: Avoid LIKE '%xxx' as it prevents index usage. Consider full-text search

[DAS DIAGNOSIS]

  Cost Estimate: Very small cost
    Estimated rows: 15
    Estimated CPU: 3.77
    Estimated I/O: 2.00

  Tuning Advice:
    - Leading wildcard in LIKE pattern prevents B-Tree index usage. Consider full-text index or search engine.

[NOTICE]
  Suggestions are for reference only. Evaluate applicability based on your business scenario and data characteristics before deploying.
```

## Agent Report Guidelines

When presenting to the user, the agent should:

1. **Add context**: Include SQL statement, Instance ID, Database name at the top
2. **Three-part structure**: For each issue, provide Problem, Impact, and Suggestion
3. **Provide optimized SQL**: Rewrite the SQL based on suggestions when possible
4. **Mandatory disclaimer**: Always include a disclaimer that suggestions are for reference only
5. **Do NOT paste raw script output**: Transform it into a readable report

## JSON Report (via --output flag)

```json
{
  "assessment_id": "lint_20260506_143300",
  "timestamp": "2026-05-06T14:33:00",
  "instance_id": "pc-xxxxx",
  "summary": {
    "total_rules": 28,
    "passed": 26,
    "critical": 0,
    "warnings": 1,
    "suggestions": 1
  },
  "issues": [
    {
      "rule_id": "RULE-022",
      "severity": "warning",
      "category": "statement",
      "message": "Leading wildcard in LIKE pattern"
    }
  ],
  "das_results": [
    {
      "success": true,
      "primaryTag": "PLAN_COST_VERY_SMALL",
      "estimateCost": {"cpu": 3.77, "io": 2.0, "rows": 15.0},
      "tuningAdvices": [{"name": "LIKE_LEFT_WILD_CARD", "type": "INFORMATIONAL"}]
    }
  ]
}
```
