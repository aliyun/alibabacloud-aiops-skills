# Acceptance Criteria: alibabacloud-waf-rule-effectiveness-check

**Scenario**: static effectiveness check for WAF 3.0 custom rules
**Purpose**: skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — the product subcommand must be `waf-openapi`

The plugin is named `aliyun-cli-waf-openapi`; there is no `waf` product subcommand.

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou
```

#### ❌ INCORRECT
```bash
aliyun waf describe-instance --region cn-hangzhou
```
`'waf' is not a valid product` — wrong product name, the command fails outright.

## 2. Command — the commands this skill is allowed to use (all read-only)

`describe-instance` / `describe-defense-resource` / `describe-defense-resources` /
`describe-defense-rules` / `describe-defense-template` / `describe-template-resources` /
`describe-template-resource-count`

#### ❌ INCORRECT
Any `modify-*` / `create-*` / `delete-*` command — this skill is read-only and delivers write actions as
console paths only.

## 3. Parameters — plugin mode uses lowercase-hyphen parameters

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-defense-rules --biz-region-id cn-hangzhou \
  --instance-id waf_xxx --query '{"ruleId": 123456}'
```

#### ❌ INCORRECT
```bash
aliyun waf-openapi describe-defense-rules --RegionId cn-hangzhou \
  --InstanceId waf_xxx --Query '{"ruleId": 123456}'
```
PascalCase belongs to the legacy API style; plugin mode does not recognize it and reports an unknown flag.

## 4. Error-prone parameters

#### Region parameter
- ✅ `--biz-region-id cn-hangzhou` (maps to the API's RegionId; only `cn-hangzhou` / `ap-southeast-1`)
- ❌ Using the global `--region` in place of WAF's RegionId parameter

#### Binding count lookup
- ✅ `describe-template-resource-count --template-ids <tid>` (**plural**, comma-separated for multiple IDs)
- ❌ `describe-template-resource-count --template-id <tid>` (the parameter does not exist)

#### Paging for template-bound objects
- ✅ `describe-template-resources ... --max-results 500 --next-token <token>`
- ❌ Using `--page-size` / `--page-number` with `describe-template-resources` (unsupported by that command)

#### resource-type enum
- ✅ `--resource-type single` (protection object) / `group` (object group) / `asset` (protected asset)
- ❌ Any other value

## 5. Observability — every API command must carry `--user-agent`

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-effectiveness-check/<session-id>
```
The script receives the session ID via
`SKILL_SESSION_ID=<session-id> python3 scripts/check_rule_effectiveness.py ...`.

#### ❌ INCORRECT
- Omitting `--user-agent`
- Using `aliyun configure ai-mode` (deprecated)
- Using `export ALIBABA_CLOUD_USER_AGENT=...` (deprecated; does not survive across separate bash invocations)

## 6. Credential safety

- ✅ Use `aliyun configure list` only, to check credential status
- ❌ Reading / printing AK/SK, asking the user to paste AK/SK into the conversation, or writing literal
  credentials with `aliyun configure set`

## 7. Parameter confirmation

- ✅ Confirm `rule_id` / `rule_name`, `matched_host`, and `region` with the user before executing
- ❌ Assuming a default region, or inventing a protection object name and going straight to an
  "effective / not effective" verdict

---

# Correct Script Patterns

## 1. Invocation
```bash
SKILL_SESSION_ID=<session-id> python3 scripts/check_rule_effectiveness.py \
  --rule-id <rule_id> --resource <matched_host>
```
Exit codes: `0`=the whole quad passes; `1`=a broken link exists or the rule is in observe mode (the first
break is reported); `2`=query failure / rule or object not found / out of scope.

## 2. Scope ruling
For rules with `DefenseOrigin != custom` the script must refuse the check with exit code 2 (built-in and
whitelist rules are out of scope) and must not force a verdict.

## 3. Ruling on the action element (element ④)

#### ✅ CORRECT
- Action is an observe/monitor-style value (e.g. `monitor`) → element ④ fails and the verdict is stated
  directly as "observe-mode misreading"
- The action cannot be parsed from `Config` → emit `element 4 (action) undetermined` as a note for manual
  review

#### ❌ INCORRECT
- Treating "the action could not be parsed" as "the action is block" and passing it
- Having confirmed observe mode, still attributing the root cause to binding / timing / config rollout
  (**rationalized convergence**, forbidden)
- Reading `xx_action=block` as "it blocked" when the log shows `xx_test=true`

## 4. Conclusion discipline

#### ✅ CORRECT
- Query failure / empty result → mark it "not retrieved" and state the impact on the conclusion
- Rule identifier missing → reverse-look-up first; if it cannot be located, output "known facts +
  preliminary judgement + missing inputs + advice"
- Quad passes but logs show no hit → rule it contradictory evidence and escalate with the ruled-out items
- The status code the customer sees comes from the origin (`status == upstream_status`) → explain and point
  them at the origin

#### ❌ INCORRECT
- Inferring "the rule / binding does not exist" from an empty result and closing the case
- Replying with just "please provide the rule ID" and stopping (**stalling**)
- Taking the customer's "I configured the rule" at face value without verification
- Hard-coding a root cause when evidence is insufficient, or taking origin-side responsibility onto WAF

## 5. Output language

- ✅ The report to the customer is written in the customer's language (Chinese for domestic tickets), and
  console navigation paths keep their original Chinese console wording, e.g.:

  ```
  WAF 3.0 控制台 → 防护配置 → 模板 Y → 防护对象 → 添加 Z
  ```
- ❌ Replying in English to a Chinese-speaking customer, or translating console menu names so the customer
  cannot find them in the UI
