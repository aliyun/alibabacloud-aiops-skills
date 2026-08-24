# CLI Commands and Key Fields (WAF 3.0 / waf-openapi 2021-10-01)

> The product subcommand is `waf-openapi` (plugin `aliyun-cli-waf-openapi`); all parameters use the
> lowercase-hyphen style.
> Every command must carry `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-effectiveness-check/{session-id}`
> (see the Observability section in SKILL.md).
> For instances outside the Chinese mainland, use `--biz-region-id ap-southeast-1`.
> This skill only checks custom protection rules (`DefenseOrigin = custom`); whitelist rules and built-in
> rules are out of scope.

## Instance

```bash
# Instance ID / edition / per-template protection object quota
aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou
```

**Key response fields**:
- `InstanceId`: required parameter for every subsequent call
- `Details.Edition`: edition (default_version, etc.)
- `Details.DefenseObjectInTemplateMaxCount`: per-template protection object quota (authoritative value for
  the edition cap)

## Protection object

```bash
# A single protection object (existence / initialization state / owning object group)
aliyun waf-openapi describe-defense-resource --biz-region-id cn-hangzhou --resource <matched_host>

# Page through protection objects (to compare when the name does not line up)
aliyun waf-openapi describe-defense-resources --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --page-size 50 --page-number 1
```

**Key response fields** (`describe-defense-resource` → `Resource`):
- `ResourceStatus`: `initializing` / `active` / `init_failed`
- `ResourceGroup`: owning protection object group (the indirect binding path for element ②)
- `AcwCookieStatus`: tracking cookie (acw_tc) switch — prerequisite for session-dimension counting
- `XffStatus` / `CustomHeaders`: client IP resolution configuration (used when investigating NAT false bans)

## Protection rules (custom)

```bash
# Exact lookup by ID (--query takes a JSON string)
aliyun waf-openapi describe-defense-rules --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --query '{"ruleId": <rule_id>}'

# Fuzzy lookup by name / lookup by template
aliyun waf-openapi describe-defense-rules --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --query '{"nameLike": "<keyword>"}'
aliyun waf-openapi describe-defense-rules --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --query '{"templateId": <template_id>}'
```

**Key response fields** (`Rules[]`):
- `RuleId` / `RuleName`
- `Status`: 1=enabled, 0=disabled (element ①)
- `TemplateId`: the rule's template (entry point for elements ② and ③)
- `DefenseOrigin`: `custom`=user-defined (in scope), `system`=built-in (out of scope)
- `DefenseScene`: `custom_acl` / `cc` / `antiscan_highfreq` / `antiscan_dirscan` / `antiscan_scantools` /
  `ip_blacklist` and other custom scenes
- `Config`: a JSON string holding the **disposal action** (element ④), match conditions, operators,
  rate-limit settings (`ccStatus`), and blacklist scope (`effect`)

## Protection template

```bash
# Template status (element ③)
aliyun waf-openapi describe-defense-template --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --template-id <template_id>

# Protection objects bound to the template (element ②, direct binding; page with --max-results / --next-token)
aliyun waf-openapi describe-template-resources --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --template-id <template_id> --resource-type single --max-results 500

# Protection object groups bound to the template (element ②, indirect binding)
aliyun waf-openapi describe-template-resources --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --template-id <template_id> --resource-type group

# Current binding count (for the quota ruling; note the parameter is --template-ids, comma-separated)
aliyun waf-openapi describe-template-resource-count --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --template-ids <template_id>
```

**Key response fields**:
- `describe-defense-template` → `Template.TemplateStatus`: 1=enabled, 0=disabled; `Template.DefenseScene`
- `describe-template-resources` → `Resources[]`: the list of bound protection object / object group names;
  follow `NextToken` to page

## Ruling cheat sheet

| Ruling | Source of truth |
|--------|-----------------|
| In scope: custom rule | `Rules[0].DefenseOrigin == "custom"` (system and whitelist are out of scope) |
| Element ① rule enabled | `Rules[0].Status == 1` |
| Element ② bound | `<matched_host>` ∈ `Resources(single)`, or `Resource.ResourceGroup` ∈ `Resources(group)` |
| Element ③ template enabled | `Template.TemplateStatus == 1` |
| Element ④ action is block | The action field in `Rules[0].Config` is not an observe/monitor value; if it cannot be parsed, mark it "not retrieved" — never treat that as a pass |
| Gate: initialization complete | `Resource.ResourceStatus == "active"` |
| Gate: not in the default object group | `Resource.ResourceGroup` is not the default protection object group |
| Gate: quota not exhausted | binding count < `Details.DefenseObjectInTemplateMaxCount` |
| Statistical rule | `DefenseScene` ∈ {cc, antiscan_highfreq, antiscan_dirscan, antiscan_scantools}, or custom_acl with rate limiting enabled in Config |
