# Effectiveness Chain and Common Root Causes (custom rules)

## The WAF 3.0 binding chain

In WAF 3.0 a rule is not attached to a protection object directly; it is bound indirectly through a
"protection template":

```
Protection rule (Rule, DefenseOrigin=custom)
    └── belongs to → Protection template (Template, scoped by scene: custom_acl / cc / antiscan / ip_blacklist / ...)
                    └── bound to → Protection object (Resource, domain / cloud product instance) or Object group (Group)
```

Therefore the necessary and sufficient condition for "a custom rule is in effect for a protection object" is
that **all three elements hold at once**:

1. Rule `Status = 1` (enabled);
2. The protection object (or the object group it belongs to) is in the binding list of the rule's template;
3. Template `TemplateStatus = 1` (enabled).

If any one fails, the rule has **no effect at all** for that object — not "partial effect", not
"intermittent effect".

## The fourth element: disposal action (in effect ≠ blocking)

The three elements answer "is the rule in effect", but **being in effect is not the same as blocking**:

- Action is **block**: match → the request is blocked;
- Action is **observe/monitor**: match → logged, **but the request is allowed through**.

So the **top root cause for "the rule clearly matched but the request was not blocked" is observe mode**, not
the binding chain. Two classes of evidence:

- **Configuration side (authoritative)**: the action field in the rule `Config` is an observe/monitor-style
  value (e.g. `monitor`) rather than `block`;
- **Log side (corroboration)**: when a plugin-level `xx_test` field in the SLS WAF log
  (`acl_test` / `cc_test` / `antiscan_test`, etc.) is `true`, the paired `xx_action` is
  **recorded as `block` by default**, but that **does not mean the request was blocked**;
  only when `xx_test = false` is `xx_action` the real disposal action.
- **Supporting signals**: `final_action` / `final_plugin` empty → no actual disposal;
  `status == upstream_status` → the status code is passed through from the origin.

Once observe mode is confirmed, **that IS the root cause**. Do not go looking for binding / timing /
config-rollout explanations (rationalized convergence).

## Why element ② is the top root cause

The usual console workflow is "create the template → write the rule → bind the protection object", and the
last step is the easiest to forget: the template and rule are both created and enabled, so the customer
assumes they are done — but the template's protection object list is empty.
This is the highest-frequency cause in tickets, and it presents as "the configuration looks completely
correct, there is simply not a single hit record".

## Auxiliary gates

- **ResourceStatus**: a newly created protection object goes through initialization (seconds to tens of
  seconds); binding a template fails during the `initializing` window, and `init_failed` requires recreation
  or a ticket. A binding failure immediately after creation is normal — do not call it a misconfiguration.
- **Binding quota**: the number of protection objects each template can bind is capped by instance edition
  (typical values: Basic 10 / Standard 100 / Advanced 200 / Enterprise 500). The authoritative value is
  `Details.DefenseObjectInTemplateMaxCount` from `DescribeInstance`. Exceeding it presents as "cannot bind".
- **Default protection object group**: if a domain sits inside the default protection object group, a rule
  configured for that **single object** will not take effect; the object must be moved out of the default
  group first. This is an invisible gate that is easily mistaken for "it is bound but does not work".

## Scope: custom rules only

- `DefenseOrigin = custom`: user-defined rules (custom ACL, CC / rate limiting, scan protection, IP
  blacklist, etc.) — in scope for this skill.
- `DefenseOrigin = system`: built-in rules (core web protection, etc.) — effectiveness additionally depends on
  per-rule toggles inside the template, out of scope here.
- Whitelist rules — their semantics and investigation path form their own system (checkbox options, allow
  precedence, etc.); handled by the dedicated whitelist skill and not covered here.

## Extra dimensions of statistical rules (CC / rate limiting / scan protection)

Statistical rules are not "match the condition, take the action" but "take the action only once the count
within the statistical window crosses the threshold".
Therefore, when they do not fire, the cause is **usually that the count within the window never reached the
threshold, not a broken configuration chain** — review the window and threshold first, then these two:

- **Counting subject**: IP or session (`acw_tc` cookie). Behind a shared NAT egress, counting by IP causes
  collateral damage to legitimate users; the session dimension depends on the tracking cookie and is
  unavailable when the protection object has `AcwCookieStatus = 0`.
- **Blacklist scope**: for the blacklist generated on trigger, `effect: service` applies to the whole
  protection object (wide ban scope) and `effect: rule` applies only within the rule's match conditions
  (precise). "The ban scope is too wide" is usually the former.

The action element applies to statistical rules too: in observe mode a CC / rate-limit rule records hits but
bans nothing.

## Non-configuration causes of missed blocks

Not every "should have blocked but did not" is a broken rule. Rule these out first:

1. **Observe/monitor mode** — the rule matches but does not block (most common, see above);
2. **The block / status code actually comes from the origin** — the WAF log shows no block record at all while
   the customer sees 4xx/5xx, or `status == upstream_status`;
3. **Preceding-rule short-circuit / priority** — the request was handled by a higher-priority rule first, so
   later rules never ran;
4. **Whitelist early allow** — the request matched a whitelist and was allowed through, so blocking rules
   never matched;
5. **Timing** — the sample request predates the rule's configuration or rollout completion time; expected;
6. The request never reached the detection engine (e.g. 3xx forced redirect requests bypass the engine);
7. The request body exceeded the inspection range (ALB service-mode onboarding inspects at most 8KB of body);
8. Onboarding-mode capability differences — some modes support body length and regex conditions differently
   from central WAF, so the configuration saves but has no effect;
9. The attack is outside web application layer protection (non-HTTP protocols, pure client-side, behaviour
   inside an encrypted payload);
10. Match conditions written wrong (misused multi-value operator, URL vs URL-Path field mapping, consecutive
    `/` collapsed by the engine);
11. IP geolocation database bias — rules with a region condition depend on the IP geolocation database, and
    misclassification causes false blocks or misses;
12. It did block but was misread — WAF security protection returns **405** on a block, and customers often
    read 405 as "not blocked".

## Difference from "block reason lookup"

- This skill: a **configuration-state** static check — no packets sent, no single request inspected; it
  answers "why is (or is not) the custom rule in effect".
- Block reason lookup: a **traffic-state** single-request trace — it reconstructs the match chain in the logs
  from a trace_id and answers "why was this request blocked".

The two take different inputs and rely on different evidence; do not mix them.
