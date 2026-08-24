# Scenario Description: WAF Custom Rule Effectiveness Check

The source-of-truth document for this skill's scenario. Records what problem the scenario solves, the
workflow it decomposes into, and where each piece of domain knowledge came from, so that later iterations can
trace every ruling back to its origin.

## 1. Problem Statement

A customer configures a WAF 3.0 custom protection rule (custom ACL, CC / rate limiting, scan protection, IP
blacklist, etc.) and then reports one of:

- "I configured the rule but it does not work" — no hit records at all;
- "It should have been blocked but was not" — the attack traffic went through;
- "The logs show the rule matched, but the request was not blocked";
- "It worked yesterday and stopped working today";
- "CC does not trigger" or "the ban scope is far too wide".

The skill answers exactly one question: **is this rule currently in effect for this protection object, and if
not, which link in the chain is broken.** It is a configuration-state static check — no test traffic is sent
and no single request is traced.

## 2. Architecture / Objects Involved

```
Protection rule (DefenseOrigin=custom)
    └── belongs to → Protection template (scoped by scene)
                    └── bound to → Protection object, or Protection object group
                                    └── carries → domain / cloud product instance traffic
```

Cloud objects touched: WAF instance (edition and quota), protection object (initialization state, owning
object group, tracking cookie and client-IP settings), protection template (status and bindings), protection
rule (status, scene, action, match conditions, rate-limit and blacklist settings). Optionally the customer's
own SLS WAF log project for reverse corroboration.

## 3. Workflow Decomposition

The scenario decomposes into six phases; each phase maps to read-only APIs only.

**Phase 1 — Identify the instance and the protection object**
1.1 Query the WAF instance for `InstanceId`, edition, and the per-template protection object quota
    (`DescribeInstance`).
1.2 Query the protection object for existence, `ResourceStatus`, owning object group, tracking cookie switch,
    and client-IP settings (`DescribeDefenseResource`).
1.3 If the object name does not line up, page through all protection objects to compare
    (`DescribeDefenseResources`).

**Phase 2 — Locate the rule and classify it**
2.1 Look the rule up exactly by ID, or fuzzily by name (`DescribeDefenseRules`).
2.2 Confirm `DefenseOrigin = custom`; built-in (`system`) rules and whitelist rules are out of scope.
2.3 Detect whether it is a statistical rule from `DefenseScene` plus the rate-limit switch in `Config`.
2.4 Record status, template ID, scene, and the disposal action parsed out of `Config`.

**Phase 3 — Check the effectiveness quad**
3.1 Element ① — the rule is enabled (`Status`).
3.2 Element ② — the protection object, or its object group, is bound to the rule's template
    (`DescribeTemplateResources`, `single` then `group`).
3.3 Element ③ — the template is enabled (`DescribeDefenseTemplate`).
3.4 Element ④ — the disposal action is block rather than observe/monitor (parsed from `Config`).
3.5 Auxiliary gates — object initialization complete; the domain is not inside the default protection object
    group; the binding count has not hit the quota (`DescribeTemplateResourceCount`).

**Phase 4 — Symptom-specific checks**
4.1 Missed block: rule out origin status-code pass-through, preceding-rule short-circuit and priority,
    whitelist early allow, config rollout timing, requests that bypass the engine, body inspection limits,
    onboarding-mode capability differences, out-of-scope attack types, wrong match conditions, and IP
    geolocation bias.
4.2 Statistical rules: review the statistical window and count threshold first, then the counting subject
    (IP vs session) and the blacklist scope (`effect`).

**Phase 5 — Reverse corroboration with SLS logs (optional)**
5.1 Filter the customer's own WAF logs by protection object and rule ID to confirm whether hits exist.
5.2 Interpret observe-mode fields, origin pass-through signals, and other-rule hits.

**Phase 6 — Emit the verdict**
6.1 Output the pass/fail checklist with the actual field value behind every ruling.
6.2 Name the first broken link as the root cause, and give the temporary plus permanent fix with the console
    path.

## 4. Ruling Model

- **Elements ①②③ decide effectiveness**: all three must hold. If any fails the rule has no effect at all for
  that object — not partial, not intermittent.
- **Element ④ decides blocking**: an effective rule in observe/monitor mode matches and is logged but allows
  the request through. This is the top root cause when the customer says "it matched but nothing was blocked",
  and once confirmed it is the root cause on its own.
- **The first failing link is the root cause**; do not enumerate every possibility.
- **Check order follows symptom**: "no hits at all" → ② → ① → ③ → ④; "hits but no block" → ④ first.

## 5. Information Sources

| Knowledge area | Source |
|----------------|--------|
| Rule → template → object binding model, field semantics (`Status`, `TemplateStatus`, `DefenseOrigin`, `DefenseScene`, `Config`, `ResourceStatus`, `ResourceGroup`, `AcwCookieStatus`, `XffStatus`) | Alibaba Cloud WAF 3.0 OpenAPI (waf-openapi 2021-10-01) responses; command and parameter shapes verified with `aliyun waf-openapi <action> --help` |
| CLI command form, parameter naming, enum values, paging style | Verified live against the `aliyun-cli-waf-openapi` plugin help output |
| Per-template protection object quota | `Details.DefenseObjectInTemplateMaxCount` from `DescribeInstance` — always the live value, never a memorized edition number |
| Observe/monitor mode semantics; SLS log `xx_test` / `xx_action` pairing; `final_action` / `final_plugin` / `status == upstream_status` signals | Internal WAF ticket-diagnosis practice for the same scenario (rule-ineffective diagnosis), cross-checked against the configuration-side action field which this skill treats as authoritative |
| Preceding-rule short-circuit, whitelist early allow, default protection object group, config rollout timing, onboarding-mode capability differences, IP geolocation bias | Same internal ticket-diagnosis practice; each retained here only as a cause to rule out, with a read-only way to check it |
| Missed-block causes: 3xx forced redirects bypassing the engine, ALB service-mode 8KB body inspection limit, URL vs URL-Path field mapping, consecutive `/` collapsing, 405 block response | Alibaba Cloud WAF product documentation and support practice |
| Statistical-rule behaviour: window-and-threshold precedence, IP vs session (`acw_tc`) counting, blacklist `effect: service` vs `effect: rule` | WAF CC protection / rate limiting configuration semantics in `Config`, plus support practice on over-banning cases |
| RAM action names and levels | Alibaba Cloud RAM authorization list for WAF |

## 6. Constraints Baked Into the Skill

- **Read-only**: no `Modify*` / `Create*` / `Delete*` API is ever called; write actions are delivered as
  console paths for the customer to execute.
- **No test traffic**: this is a configuration-state check, not active probing.
- **Evidence discipline**: never take the customer's word for the configuration; a failed or empty query is
  not proof of absence; contradictory evidence is escalated rather than rationalized into a customer
  configuration problem.
- **Region scope**: `cn-hangzhou` (Chinese mainland) or `ap-southeast-1` (outside the Chinese mainland),
  confirmed with the user rather than assumed.

## 7. Test Material

Trigger and behaviour scenarios live under `evals/scenarios/`. Customer questions there are kept in Chinese
on purpose, because they simulate real Chinese-language tickets and exercise trigger matching.
