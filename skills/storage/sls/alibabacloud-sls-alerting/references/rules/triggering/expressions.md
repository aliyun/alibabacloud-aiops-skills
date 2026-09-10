# Evaluation expressions

Read for nontrivial trigger expressions. Start
with the [four trigger-mode mappings](trigger-conditions.md#four-trigger-modes);
this file is the next level for expression syntax.

Expressions evaluate query-result fields, not raw source fields absent from
the result. Prefer simple alphabetic SQL aliases such as `errorCount`.

| Need | Example |
| --- | --- |
| Numeric comparison | `errorCount >= 20` |
| Combined predicates | `errorCount > 0 && latency > 100` |
| Equality | `service == "checkout"` |
| Negation | `!(errorCount == 0)` |
| Substring test | `contains(service, 'check')` |
| Row-count predicate | `__count__ >= 5` in `countCondition` |

Use `==`, not SQL `=`. Expressions must produce a Boolean; arithmetic alone
does not trigger an alert. Parenthesize negative numbers, such as
`temperature < (-5)`. Numbers are evaluated as 64-bit floating point, so avoid
exact equality for imprecise computed values.

Unusual field names require brackets, for example `[5xx-rate(%)] > 5`.
Regular-expression operators are `=~` and `!~` with RE2 syntax; JSON encoding
adds another escaping layer. Evaluation expressions have a documented
1–128-character limit when nonempty; the trigger modes also intentionally use
empty strings.

Keep this syntax separate from policy DSL and notification-template syntax.
For multiple-query prefixes or additional operators, consult the
[official evaluation-expression reference](https://help.aliyun.com/zh/sls/syntax-of-evaluate-expressions)
instead of guessing.
