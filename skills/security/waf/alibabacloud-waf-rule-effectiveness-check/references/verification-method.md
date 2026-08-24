# Verification Method: WAF custom rule effectiveness check

Step-by-step verification method and pass criteria. Every command must carry
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-effectiveness-check/{session-id}`,
with `sleep 0.3` between calls for throttling.

## Step 0: Environment and credentials

```bash
aliyun version          # >= 3.3.3
aliyun configure list   # a valid profile exists (AK / STS / OAuth)
```

**Pass criteria**: version is sufficient and a valid credential exists. If either fails, STOP — do not
continue the investigation.

## Step 1: Instance and protection object (Phase 1)

```bash
aliyun waf-openapi describe-instance --biz-region-id <region>
aliyun waf-openapi describe-defense-resource --biz-region-id <region> --resource <matched_host>
```

**Verification points**:
- `InstanceId` (required by later commands) and `Details.DefenseObjectInTemplateMaxCount` are returned;
- `Resource` is non-empty → the protection object exists; `Resource.ResourceStatus == "active"` → ready;
- `initializing` → wait and retry, not a misconfiguration; `init_failed` → guide recreation / a ticket.

## Step 2: Locate the rule and confirm scope (Phase 2)

```bash
aliyun waf-openapi describe-defense-rules --biz-region-id <region> --instance-id <instance_id> \
  --query '{"ruleId": <rule_id>}'
```

**Verification points**:
- `Rules` is non-empty → the rule exists;
- `Rules[0].DefenseOrigin == "custom"` → in scope; `system` → say so plainly and stop;
- Record `Status` / `TemplateId` / `DefenseScene` / `Config`;
- `DefenseScene` ∈ {cc, antiscan_highfreq, antiscan_dirscan, antiscan_scantools}, or `custom_acl` with rate
  limiting enabled in Config → a statistical rule, so add the Phase 4.2 checklist.

## Step 3: The effectiveness quad (Phase 3)

```bash
# Element ②: binding (single first, then group)
aliyun waf-openapi describe-template-resources --biz-region-id <region> --instance-id <instance_id> \
  --template-id <template_id> --resource-type single --max-results 500
# Element ③: template status
aliyun waf-openapi describe-defense-template --biz-region-id <region> --instance-id <instance_id> \
  --template-id <template_id>
```

**Verification points**:
- ① `Status == 1`;
- ② `<matched_host>` ∈ `Resources(single)`, or `Resource.ResourceGroup` ∈ `Resources(group)`;
- ③ `Template.TemplateStatus == 1`;
- ④ The action field in the rule `Config` is block, not observe/monitor (e.g. `monitor`) — when the action
  cannot be parsed, mark it "not retrieved" and review manually; **never treat that as a block pass**;
- Auxiliary gates: `ResourceStatus == active`; the domain is not inside the default protection object group;
  the binding count has not reached `DefenseObjectInTemplateMaxCount` (use
  `describe-template-resource-count --template-ids <tid>` for the current count when needed).

**Conclusion rule**: if the customer reports "no hits at all", check ② → ① → ③ → ④; if they report "hits but
no block", check ④ first. **The first failing item is the root cause**, and the conclusion must cite actual
field values. Once observe mode holds it is the root cause — do not fall back to binding or timing
explanations.

## Step 4: Final check with the script

```bash
SKILL_SESSION_ID={session-id} python3 scripts/check_rule_effectiveness.py \
  --rule-id <rule_id> --resource <matched_host> --json
```

**Pass criteria**:
- exit code `0` → the quad and the auxiliary gates all pass; the rule is effective for the object and blocks;
- exit code `1` → `first_failure` in the JSON names the first broken link (observe mode included) and matches
  the manual conclusion;
- exit code `2` → query failure, or the rule / protection object does not exist, or it is out of scope;
  human intervention needed;
- when `notes` contains `element 4 (action) undetermined`, element ④ is **not verified** — review the action
  manually and never count it as a pass.

## Overall success criteria

| Result | Ruling |
|--------|--------|
| Quad + auxiliary gates all pass | The rule is effective and blocks; if the missed block persists, run the Phase 4 checklists / SLS corroboration and do not invent a root cause |
| Element ④ fails (observe mode) | Conclude "observe-mode misreading" directly; if the customer reported a status code, also tell them it comes from the origin |
| Any other element fails | Emit the checklist verdict: first broken link + temporary / permanent fix |
| Query failure / out of scope | Mark it "not retrieved" with its impact; emit no "effective / not effective" verdict |
| Quad passes but logs show no hit | Contradictory evidence: escalate with a ticket plus the ruled-out items; rationalized convergence is forbidden |
