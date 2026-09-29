# RAM Policy (read-only, credential-light)

The core diagnosis — fetching the parameter spec from the **public** OpenAPI metadata endpoint and diffing the
customer's parameters — requires **no Alibaba Cloud credentials and no RAM permissions at all**.

Credentials are needed only for the *optional* live reproduction of a **read** action (`describe-*`) or a
`--cli-dry-run` that resolves an endpoint. This skill never performs a write action, so no `Create*` /
`Modify*` / `Delete*` permission should ever be granted.

## Least-privilege policy (only if a live read reproduction is requested)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-waf:DescribeInstance",
        "yundun-waf:DescribeInstanceInfo",
        "yundun-waf:DescribeDomains",
        "yundun-waf:DescribeDefenseRules",
        "yundun-waf:DescribeDefenseTemplates",
        "yundun-waf:DescribeDefenseResource"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- The action set is intentionally limited to `Describe*` reads across both versions
  (`DescribeInstance` = WAF 3.0 / `DescribeInstanceInfo` = WAF 2.0). Grant only the specific read action that
  matches the customer's failing call if a tighter policy is preferred.
- If RAM policy validation does not recognize the `yundun-waf:` prefix, the equivalent `waf:` prefix can be
  used (e.g. `waf:DescribeInstance`).
- Diagnosing a `Create*` / `Modify*` parameter error does **not** require permission to call that write action:
  the spec is read from public metadata and the fix is validated with `--cli-dry-run`, so no write permission
  is ever needed.
- Never grant this skill any write permission; a corrected write call is handed to the customer to run
  themselves after confirmation.
