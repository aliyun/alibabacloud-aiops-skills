# RAM Policy (read-only investigation)

This skill is read-only end to end and performs no write operations. Least-privilege policy:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-waf:DescribeInstance",
        "yundun-waf:DescribeDefenseRules",
        "yundun-waf:DescribeDefenseTemplate",
        "yundun-waf:DescribeTemplateResources",
        "yundun-waf:DescribeTemplateResourceCount",
        "yundun-waf:DescribeDefenseResource",
        "yundun-waf:DescribeDefenseResources"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- Each action maps one-to-one to a WAF 3.0 OpenAPI (waf-openapi 2021-10-01) call, all at list/get level:

  | API | Authorization action | Level |
  |-----|----------------------|-------|
  | DescribeInstance | yundun-waf:DescribeInstance | get |
  | DescribeDefenseRules | yundun-waf:DescribeDefenseRules | list |
  | DescribeDefenseTemplate | yundun-waf:DescribeDefenseTemplate | get |
  | DescribeTemplateResources | yundun-waf:DescribeTemplateResources | list |
  | DescribeTemplateResourceCount | yundun-waf:DescribeTemplateResourceCount | get |
  | DescribeDefenseResource | yundun-waf:DescribeDefenseResource | get |
  | DescribeDefenseResources | yundun-waf:DescribeDefenseResources | list |

- If RAM policy validation does not recognize the `yundun-waf:` prefix, the equivalent `waf:` prefix can be
  used instead (e.g. `waf:DescribeDefenseRules`).
- Reverse corroboration against the customer's own SLS WAF logs is performed by the customer in their log
  console; this skill requests no additional SLS permissions.
- No `Modify*` / `Create*` / `Delete*` permission should **ever** be granted to this skill.
