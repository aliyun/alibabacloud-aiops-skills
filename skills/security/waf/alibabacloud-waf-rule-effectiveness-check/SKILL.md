---
name: alibabacloud-waf-rule-effectiveness-check
description: |
  Diagnose why a configured Alibaba Cloud WAF 3.0 custom protection rule (custom ACL, CC / rate limiting,
  scan protection, IP blacklist) is not working: name the first broken link in the chain and hand back the
  console fix path. Read-only checks of configuration state only; never sends test traffic.
  Use it when a customer says a rule has no effect at all, a rule matches in the logs but nothing is blocked,
  an attack that should have been blocked got through, a rule worked yesterday but not today, or a CC or
  rate-limiting rule does not trigger or bans far too widely.
  Not for: explaining why one specific request was blocked or looking it up by trace_id, whitelist rule
  effectiveness itself, live attack sample validation, built-in rule toggles, config export, or reports.
  Triggers: "规则不生效", "规则配了但不生效", "自定义规则不生效", "预期拦未拦", "该拦的没拦住",
  "漏拦截", "规则命中但没拦", "规则昨天还好今天失效", "CC不触发", "误封面过大", "规则为什么没生效",
  "WAF rule not effective", "rule not taking effect", "rule hit but not blocked"
---

# WAF Custom Rule Effectiveness Check

Answers one precise question: **is this custom rule currently in effect for this protection object, and if
not, which link is broken.** Statically checks the configuration chain; sends no test traffic.
WAF 3.0 only (waf-openapi 2021-10-01). Use when the customer reports "I configured the rule but it does not
work / it should have been blocked but was not / CC does not trigger or the ban scope is too wide".
Scope: user-defined rules with `DefenseOrigin = custom` (custom_acl / cc / rate limiting / scan / blacklist).

## ❗ Hard Constraints (highest priority in this document)

> **Interaction stance — confirm first, query second.** Asking the customer for a required input that is
> missing or ambiguous, and then waiting for the answer, is *correct* behaviour in this skill — never a
> failure to act. Guessing an input, or querying around the gap, is the failure.

1. **Never take the customer's "I configured it" at face value** — saying it was configured does not mean the
   rule exists, is enabled, and is bound. Verify all platform-side state with read-only APIs (Phase 1→3).
2. **When the disposal action is observe/monitor mode, that IS the root cause** — do not demote it to a
   "side note", and do not switch to hunting for binding / timing / config-rollout explanations instead.
   Having observe-mode evidence in hand yet picking a self-consistent but wrong explanation is
   **rationalized convergence and is explicitly forbidden** (see Phase 3, element ④).
3. **A failed or empty query is NOT proof of absence** — mark it "not retrieved" and state how that limits the
   conclusion. Never infer "the rule / binding does not exist" and close the case on that basis.
4. **No `region` or no `matched_host` → call nothing at all.** Both are prerequisites for every query in this
   skill. When either is missing, ask the customer and **WAIT for the answer**: not one API call, not even
   `describe-instance`, and never guess a region from the domain name. This gate covers **all** APIs, not only
   the template-level ones, and no other instruction in this document overrides it.
5. **Multiple domains or rules failing at once points away from a single-rule misconfiguration** — do not
   diagnose them one by one as configuration errors; state the consistency of the symptom and guide the
   customer to open a ticket so the platform-side rollout can be checked.
6. **Contradictory evidence must be escalated honestly** — if the quad and the action element all pass but the
   logs show no hit at all, that is an evidence conflict: open a ticket with the ruled-out items attached.
   **Do not hard-code a root cause to force closure.**
7. **When the status code the customer sees comes from the origin, say so and point them at the origin** —
   do not take on WAF-side responsibility (criteria in Phase 4.1).
8. **Read-only throughout** — any write action (enable, bind, change action) is delivered as a console path
   only, for the customer to execute after confirmation.
9. **A missing rule identifier, or "rule not found", is not a finished diagnosis** — **with `region` and
   `matched_host` already in hand**, do not stall on "please provide the rule ID" and do not stop at "the rule
   does not exist". Enumerate the candidate templates (list rules by scene or name keyword to collect their
   `TemplateId`s), then still check the object binding, the template status and the binding quota on those
   candidates, so the customer learns whether the object is bound to any enabled template. **Zero-result
   lookups only; never overrides constraint 4; several candidates is constraint 11 — confirm first.**
10. **Answer in the customer's language** — a Chinese-language ticket gets a fully Chinese report, including
    the checklist table headers and the verdict wording; only console menu names keep their original Chinese.
    Never hand a Chinese-speaking customer an English report.
11. **Template-level calls are gated** — `DescribeTemplateResources`, `DescribeDefenseTemplate` and
    `DescribeTemplateResourceCount`. Calling them is **forbidden** until both hold: (a) the rule's
    `DefenseOrigin` is `custom` — for a built-in (`system`) rule report "built-in rule, out of scope" and stop,
    do not touch the template APIs at all; (b) the customer has confirmed **which** rule, whenever the rule was
    reached through a name keyword instead of an exact ID — list the matches with `RuleId` / `RuleName` /
    `TemplateId` and wait for the pick, **even if only one rule matched**. **This outranks any
    evidence-collection instruction below.**

## Architecture

```
Customer report: custom rule not effective / expected block missed / CC not triggering or over-banning
│
├── Phase 1: DescribeInstance (InstanceId / Edition / quota) + DescribeDefenseResource (existence / status)
│
├── Phase 2: DescribeDefenseRules → confirm DefenseOrigin=custom; detect statistical rules (CC / rate / scan)
│
├── Phase 3 (core): Check the effectiveness quad element by element
│   ├── ① rule Status=1
│   ├── ② object (or its object group) bound to the rule's template   ← top root cause
│   ├── ③ template TemplateStatus=1
│   └── ④ disposal action is block, not observe/monitor               ← top root cause for missed blocks
│   └── Auxiliary gates: ResourceStatus=active / default object group / binding quota
│
├── Phase 4: missed-block checklist (observe mode, origin pass-through, priority, timing)
│           or statistical-rule checklist (window and threshold, counting subject, blacklist scope)
│
├── Phase 5: Reverse corroboration with SLS logs (optional)
│
└── Phase 6: Emit the checklist verdict (first broken link + temporary / permanent fix)
```

## Scope Boundaries (division of labour with other WAF skills)

| How the customer asks | Which skill |
|-----------------------|-------------|
| "Why was this request blocked?" | A block-reason lookup skill (trace_id → matched rule → rule detail) |
| **"Why is the custom rule I configured not taking effect?"** | **This skill** |
| "I allow-listed it and it is still blocked" | The dedicated whitelist skill (whitelist effectiveness **itself** is out of scope here; but "whitelist early allow made my blocking rule miss" is a cause this skill rules out) |
| "Can my protection rules really block attacks?" (wants real samples sent) | An active validation skill |
| "Export all my protection configuration" / "Give me an attack and protection report" | A configuration export skill / a reporting skill |

> One ticket may need both this skill and a block-reason lookup skill: **use this skill first**, then let the
> other analyse the request by trace_id (different leads: rule_id vs trace_id) — do not mix them.

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **Preferred (no remote script execution):** download `https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz`
>   (macOS: `aliyun-cli-macosx-latest-{amd64|arm64}.tgz`), `tar tzf` to inspect, `tar xzf`, `sudo mv aliyun /usr/local/bin/`.
> - **Alternative:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Update (CLI >= 3.3.5):** `aliyun upgrade`. Full instructions: `references/cli-installation-guide.md`.

**Pre-check: Aliyun CLI plugin update required**

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
> The WAF 3.0 commands live in the `waf-openapi` plugin: `aliyun plugin install --names aliyun-cli-waf-openapi`.

**Pre-check: Python 3.8+ required**

> The bundled `scripts/check_rule_effectiveness.py` requires Python 3.8+. No additional pip packages needed.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> Run `aliyun configure list` and check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Policy

This skill is **strictly read-only** and needs WAF read permissions only.
Full policy JSON: [references/ram-policies.md](references/ram-policies.md).

| Action | Purpose |
|--------|---------|
| `yundun-waf:DescribeInstance` | Instance ID / edition / per-template binding quota |
| `yundun-waf:DescribeDefenseRules` | Rule detail: Status, DefenseOrigin, DefenseScene, TemplateId, Config |
| `yundun-waf:DescribeDefenseTemplate` | Template TemplateStatus, DefenseScene |
| `yundun-waf:DescribeTemplateResources` | Protection objects / object groups bound to the template (element ②) |
| `yundun-waf:DescribeDefenseResource` | Object existence, ResourceStatus, owning object group |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-effectiveness-check/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-effectiveness-check/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

**Script / Terraform execution:** When running Python SDK scripts or Terraform commands or bash scripts, inject the session-id via inline environment variable so the code can read it at runtime:

```bash
# Python SDK script
SKILL_SESSION_ID={session-id} python3 scripts/check_rule_effectiveness.py --rule-id <rule_id> --resource <matched_host>
```

Scripts read `SKILL_SESSION_ID` from the environment (default to empty string if absent).

## Inputs and Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Never assume or silently default a parameter the customer did not
> provide. When the required inputs below (rule identifier, protection object, region) are already present in
> the request, treat them as confirmed and **start the read-only checks straight away — do not ask again**.
> Ask only for a required input that is genuinely missing or ambiguous.

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| `rule_id` / `rule_name` | Required (either one) | ID of the custom protection rule under check, or a name keyword (fuzzy match) | None |
| `matched_host` | Required | Protection object name (usually the object for a domain, e.g. `www.example.com-waf`) | None |
| `region` | Required | Region of the WAF instance: `cn-hangzhou` (Chinese mainland) or `ap-southeast-1` (outside the Chinese mainland) | Read it from the customer's wording (e.g. Chinese mainland / Singapore); ask only when absent |
| Symptom | Optional | Expected block missed / CC not triggering / ban scope too wide — decides which Phase 4 checklist to run | None |
| Expected vs actual behaviour | Optional | What the customer wanted the rule to achieve and what they actually observed (including the status code) | None |
| Configuration time | Optional | When the rule was configured and whether it ever worked — the key input for the timing check (Phase 4.1) | None |
| Time the failure started | Optional | For "it suddenly stopped working", record the approximate time to assess change / rollout impact | None |

### When the rule identifier is missing

With `region` and `matched_host` in hand but no `rule_id` / rule name, **do not simply demand it and stop** —
reverse-look-up from the object's template first:

```bash
# Infer candidate rules from the template that the protection object is bound to
# (get template_id first, then list the rules of that template)
aliyun waf-openapi describe-defense-rules --biz-region-id <region> --instance-id <instance_id> \
  --query '{"templateId": <template_id>}'
```

If that still turns up nothing, output known facts + preliminary judgement (which class of root cause the
symptom suggests) + missing inputs + advice — do not stop at a bare "please provide the rule ID".

> **This section assumes `region` and `matched_host` are already known.** If either is missing, constraint 4
> applies instead — ask and wait, issue no API call, and **never fall back to "let me at least check the
> rule's own state"**. When the object name is merely uncertain but present, page through
> `aliyun waf-openapi describe-defense-resources` to compare, or filter by name keyword.

## Workflow

> **[MUST] Three gates, in order, before **any** API call — they outrank the evidence set below; when a gate
> closes, answer the customer instead of querying:** (a) `region` or `matched_host` missing → ask and **wait**,
> zero API calls, not even `describe-instance` (constraint 4); (b) `DefenseOrigin ≠ custom` → report "built-in
> rule, out of scope" and stop, no template-level call (constraint 11); (c) the rule was reached through a
> **name keyword** rather than an exact ID → list the matches and let the customer confirm which one, **even if
> only one matched** (constraint 11).
> **[MUST] Baseline evidence set** — once all three gates pass, work through `describe-instance`,
> `describe-defense-resource`, `describe-defense-rules`, `describe-template-resources` (`--resource-type single`
> **then** `group`), `describe-defense-template`, `describe-template-resource-count` before the verdict, even
> when the first broken link looks obvious.

### Phase 1: Identify the instance and the protection object

```bash
aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou
# Key fields: InstanceId, Details.Edition, Details.DefenseObjectInTemplateMaxCount
aliyun waf-openapi describe-defense-resource --biz-region-id cn-hangzhou --resource <matched_host>
# Key fields: Resource.ResourceStatus (initializing / active / init_failed), Resource.ResourceGroup
```

- `ResourceStatus = initializing`: a newly created object is still initializing (seconds to tens of seconds);
  binding a template may fail during this window. Wait and retry — **do not call it a misconfiguration**.
- `ResourceStatus = init_failed`: initialization failed; guide the customer to recreate it in onboarding
  management or open a ticket.
- Object does not exist: the customer gave the wrong object name. Align on the name first (wildcard and
  multi-domain setups are frequently mismatched).

### Phase 2: Locate the rule and classify it

```bash
# Exact lookup by rule ID (custom protection rule)
aliyun waf-openapi describe-defense-rules --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --query '{"ruleId": <rule_id>}'

# Fuzzy lookup by name
aliyun waf-openapi describe-defense-rules --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --query '{"nameLike": "<rule name keyword>"}'
```

**If you reached the rule through `nameLike` (a name keyword) instead of an exact `ruleId`, stop here and
report the matches** — list `RuleId` / `RuleName` / `TemplateId` for every hit, **even when only one matched**,
and wait for the customer to confirm which rule they mean. Phase 3 must not start before that (constraint 11).

Read `DefenseOrigin` from the returned `Rules[]` to pick the path:
- `DefenseOrigin = custom` → **user-defined rule** (custom ACL / CC / rate limiting / scan protection /
  IP blacklist, etc.) → continue with Phase 3 → 4 **once the rule under check is confirmed**.
- `DefenseOrigin = system` → **built-in rule**, out of scope: say plainly that this skill only checks custom
  rules, that built-in rules also depend on per-rule toggles inside the template, and point them at built-in
  rule docs or a dedicated skill. **No template-level calls (constraint 11); do not force a verdict.**
- Rule not found (**zero** results): re-check the ID / name, hand whitelist rules to the whitelist skill, and
  enumerate candidates via `defenseScene` / `nameLike` to collect `TemplateId`s for the Phase 3 template
  checks (constraint 9). **Several candidates rather than zero → constraint 11: list them and wait.**

**Statistical rule detection** — any of these `DefenseScene` values qualifies:
`antiscan_highfreq` (high-frequency triggering) / `antiscan_dirscan` (directory scanning) /
`antiscan_scantools` (scanning tools) / `cc` (CC protection) / `custom_acl` with rate limiting enabled in
`Config`. Statistical rules additionally go through Phase 4.2.

Record: `RuleId`, `RuleName`, `Status`, `TemplateId`, `DefenseScene`, `Config` (a JSON string holding the
**disposal action**, match conditions, rate-limit settings, and blacklist scope — element ④ and the
statistical checklist both parse it).

### Phase 3 (core): Check the effectiveness quad element by element

Elements ①②③ decide whether the rule is **in effect** (all three must hold; if any fails the rule has no
effect at all). Element ④ decides whether an effective rule actually **blocks the request** — in
observe/monitor mode the rule matches and is logged, but the request is allowed through.

| # | Element | How to check | How to word the failure |
|---|---------|--------------|-------------------------|
| ① | Rule status is **enabled** | `Status` from the rule lookup (1=enabled, 0=disabled) | "Rule X is currently disabled" |
| ② | The object is **bound** to the template containing the rule | Run `describe-template-resources --template-id <tid>` **twice — `--resource-type single` and `--resource-type group`, both are required evidence**: does `Resources` contain `matched_host`, or the object's `ResourceGroup`? | "Template Y is not bound to protection object Z, so the rule has no effect" |
| ③ | The template status is **enabled** | `TemplateStatus` from `describe-defense-template --template-id <tid>` (1=enabled, 0=disabled) | "Template Y is disabled" |
| ④ | The disposal action is **block**, not observe/monitor | Parse the action field (e.g. `action`) out of the rule `Config`; log-side corroboration below | "Rule X is in observe mode: it matches but does not block the request" |

```bash
# Element ②: run twice — --resource-type single, then group (both are required, never only one)
aliyun waf-openapi describe-template-resources --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --template-id <template_id> --resource-type single

# Element ③: template status
aliyun waf-openapi describe-defense-template --biz-region-id cn-hangzhou --instance-id <instance_id> \
  --template-id <template_id>
```

> **Element ② is the top root cause for "the rule has no effect at all"**, especially "template and rule are
> both set up but no protection object was ever bound"; **element ④ is the top root cause for "the rule
> matched but nothing was blocked"**.
> Suggested order: if the customer reports "nothing happens at all / no hit records", go ② → ① → ③ → ④;
> if they report "the logs show hits but the request was not blocked", check ④ first.
> The output must name the exact template that is missing the exact object, or the exact action of the exact
> rule — never stop at "please check your configuration".

#### ⚠ Observe-mode ruling (element ④)

A rule in observe/monitor mode **matches and is logged, but does not block the request**. Two classes of
evidence:

| Evidence source | Criterion |
|-----------------|-----------|
| Configuration side (authoritative) | The action field in the rule `Config` is an observe/monitor-style value (e.g. `monitor`) rather than `block` |
| Log side (corroboration) | When a plugin-level `xx_test` field in the SLS WAF log (e.g. `acl_test` / `cc_test` / `antiscan_test`) is `true`, the paired `xx_action` is **recorded as `block` by default**, but that **does not mean the request was blocked** — it was allowed through. Only when `xx_test = false` is `xx_action` the real disposal action |
| Supporting signals | `final_action` / `final_plugin` empty → no actual disposal took place; `status == upstream_status` → the status code is passed through from the origin |

**Hard constraint**: once observe mode is confirmed (action is monitor, or the log shows `xx_test=true`, or
`final_action` is empty while `status == upstream_status`), **that IS the root cause** — state the verdict as
"observe-mode misreading" directly. Do not demote it to a "side note", and **do not go looking for binding /
timing / config-rollout explanations** (none of those are the root cause in observe mode).
If the customer also reported a specific status code, state that the code comes from the origin and point
them at the origin.

**Branches**:
- Rule does not exist → complete the baseline evidence set on the candidate templates first (constraint 9),
  then go to Phase 6; the verdict is that the configuration was never saved or has been deleted.
- Action is observe/monitor → **go to Phase 6** once the baseline evidence set is collected; the verdict is
  "observe-mode misreading".
- Action is block and ①②③ all pass → continue with the Phase 4 checklists.

**Auxiliary gates**:
- A newly created protection object goes through initialization; a template can only be bound once
  `ResourceStatus` becomes `active` (already checked in Phase 1).
- **Default protection object group**: if the domain sits inside the default protection object group, a rule
  configured for that **single object** will not take effect. The object must first be moved out of the
  default group before it can carry its own rules (compare `Resource.ResourceGroup` against the template's
  group binding list).
- Template binding count is capped by edition: compare `describe-template-resource-count` against the
  `Details.DefenseObjectInTemplateMaxCount` returned by `DescribeInstance` (**the source of truth**, not
  memorized edition numbers). At the cap, binding fails; trim bindings or open a ticket for an assessment.

### Phase 4: Symptom-specific checks

Pick the checklist that matches the symptom. Full tables:
[references/symptom-checklists.md](references/symptom-checklists.md).

- **Expected block missed (4.1)** — element ④ (observe mode) is ruled out first, then the non-configuration
  causes: origin status-code pass-through (`status == upstream_status`), preceding-rule short-circuit and
  priority, whitelist early allow, config rollout timing, 3xx forced redirects bypassing the engine, the ALB
  service-mode 8KB body inspection limit, onboarding-mode capability differences, out-of-scope attack types,
  unmatchable match conditions, IP geolocation bias, and a 405 block being misread as "not blocked".
- **CC / rate-limit anomaly (4.2)** — statistical rules act only once the count within the statistical window
  crosses the threshold, so a non-firing rule is **usually a count that never reached the threshold, not a
  broken configuration chain**. Review the window and threshold first, then the counting subject (IP vs
  session `acw_tc`, unavailable when `AcwCookieStatus=0`) and the blacklist scope
  (`effect: service` vs `effect: rule`).

### Phase 5: Reverse corroboration with SLS logs (optional)

When the customer has WAF log service enabled, corroborate against their own SLS WAF logs (filter by
`matched_host` + `final_rule_id` / `rule_id`). Interpretation table:
[references/symptom-checklists.md](references/symptom-checklists.md).

Key readings: hits with `xx_test=true` → observe mode; no block record while the customer sees 4xx/5xx, or
`status == upstream_status` → origin pass-through; hits for other rules only → preceding-rule short-circuit or
whitelist early allow; the quad passes yet no hit exists → contradictory evidence, escalate.

> If the logs cannot be retrieved or log service is not enabled, mark it "not retrieved" and state which
> rulings therefore cannot be closed. **Never use that as "no hit".**

### Phase 6: Output

Always emit one checklist verdict plus a single root-cause sentence the customer can act on:

```
**Verdict**: {rule X is currently not effective for protection object Z; broken at "element ② object not bound to template"}
**Checklist**:
  ① Rule status: pass / fail (actual value)
  ② Object binding: pass / fail (template Y is not bound to Z)
  ③ Template status: pass / fail (actual value)
  ④ Disposal action: block / observe mode (actual value) / not retrieved
  ⑤ Statistical window and threshold / blacklist scope: pass / fail / not applicable
**Actions**: {<=3 items, temporary + permanent per the table below, with the console path}
```

**Output language**: respond in the customer's language (Chinese for domestic tickets). Keep console
navigation paths in their original Chinese console wording, e.g.
"WAF 3.0 控制台 → 防护配置 → 模板 Y → 防护对象 → 添加 Z", so the customer can find them in the UI.

Hard constraints: at most 15 lines total; every ruling must cite the field value actually retrieved, and
anything unavailable is written as "not retrieved" with its impact stated; never paste raw API JSON in bulk;
**the first failing link is the root cause — do not enumerate every possibility**; if everything passes yet
the problem persists, say so honestly and open a ticket instead of inventing a root cause.

## Remediation Table

Map the located root cause to a temporary fix (what the customer can do now) plus a permanent fix, and deliver
the console path. Full table with all 19 root causes:
[references/remediation-table.md](references/remediation-table.md).

**Ticket / escalation criteria**: the quad and checklists all pass yet the logs show no hit (contradictory
evidence), or multiple domains / rules fail at once with no configuration cause — open a ticket with the
ruled-out items attached. **Do not rationalize it into a customer configuration problem.**

## Fallback Logic

- Rule identifier missing while `region` + `matched_host` are in hand: reverse-look-up first; if still nothing,
  output known facts + judgement + missing inputs rather than a bare "please provide the rule ID". **This never
  licenses a query while `region` / `matched_host` are still missing (constraint 4).**
- Query failed or returned empty: mark it "not retrieved", state the impact; never infer "does not exist".
- Root cause fits no row in the remediation table: treat it as a contradiction signal (data, tool result,
  multiple sources or logs disagreeing with the configuration) and trigger the ticket flow.
- Platform-side problem suspected but unconfirmable: open a ticket with the ruled-out customer-side factors.

## One-Shot Check Script

```bash
# Inject the session-level session-id (see Observability), then check the effectiveness quad for one custom
# rule against one protection object (read-only)
SKILL_SESSION_ID={session-id} python3 scripts/check_rule_effectiveness.py --rule-id <rule_id> --resource <matched_host>

# Fuzzy match by rule name
SKILL_SESSION_ID={session-id} python3 scripts/check_rule_effectiveness.py --rule-name "<name keyword>" --resource <matched_host>

# JSON output for programmatic use
SKILL_SESSION_ID={session-id} python3 scripts/check_rule_effectiveness.py --rule-id <rule_id> --resource <matched_host> --json
```

Exit codes:
- `0`: the quad and the auxiliary gates all pass (the rule is effective for the object and will block)
- `1`: a broken link exists, or the rule is in observe mode (the first break is reported)
- `2`: query failure, or the rule / protection object does not exist (human intervention needed)

> Script output is evidence, not judgement: when the action field cannot be determined the script emits the
> raw value as a note for manual review. **Never read "action could not be parsed" as "the action is block".**

## Rate Limiting

WAF openapi throttling limit: **5 calls/second per uid**.
- Insert `sleep 0.3` (300ms) between every `aliyun` API command
- On throttling error (`Throttling.User` / HTTP 429): exponential backoff (2s → 4s → 8s), stop after 3 failures

## Security Constraints

- Read-only investigation. Write actions such as enabling a rule or binding a template are delivered as
  console paths only, for the customer to execute after confirmation;
  **NEVER** call `Modify*` / `Create*` / `Delete*` WAF APIs.
- Access resources in the customer's own account only; never query across accounts.
- Change advice follows least impact: adjust match conditions only within the necessary scope, never suggest
  disabling an entire rule group, and keep a record of changes so they can be rolled back.

## Cleanup

No persistent cloud resources are created. Delete any temporary report file the investigation produced
(e.g. `effectiveness_report.json`).

## Best Practices

1. Never accept "I configured it" at face value; verify with read-only APIs first.
2. Never conclude without `matched_host` — and never *query* without it either: ask and wait (constraint 4).
3. "No hits at all" → check ② → ① → ③ → ④; "hits but no block" → check ④ first. First failure is the verdict.
4. Once observe mode holds it is the root cause — **stop looking for binding / timing / rollout explanations**.
5. Confirm `DefenseOrigin = custom` first; built-in and whitelist rule effectiveness are out of scope.
6. `DescribeTemplateResources` is the source of truth for bindings; never miss the object-group and
   default-group indirect paths.
7. Base quota rulings on the live `DescribeInstance` response, not memorized edition numbers.
8. Mark failed / empty queries "not retrieved" with their impact; never read them as "does not exist".
9. Cite actual field values; if the quad passes yet the problem persists, escalate with the ruled-out items.
10. Read-only throughout; deliver write actions as console paths and wait for customer confirmation.

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/scenario-description.md](references/scenario-description.md) | Scenario workflow and information sources |
| [references/related-commands.md](references/related-commands.md) | WAF 3.0 CLI commands and key response fields |
| [references/ram-policies.md](references/ram-policies.md) | Read-only RAM policy JSON |
| [references/effectiveness-chain-basics.md](references/effectiveness-chain-basics.md) | Effectiveness chain and common root causes |
| [references/symptom-checklists.md](references/symptom-checklists.md) | Phase 4 / 5 detail: missed-block and statistical checklists, log readings |
| [references/remediation-table.md](references/remediation-table.md) | Root cause → temporary / permanent fix, with console paths |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification method and criteria |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria: correct / incorrect patterns |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and upgrade guide |
