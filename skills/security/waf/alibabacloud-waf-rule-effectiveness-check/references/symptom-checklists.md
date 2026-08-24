# Symptom Checklists and Log Corroboration (Phase 4 / Phase 5 detail)

Detailed tables for Phase 4 and Phase 5 of SKILL.md. Load this when the quad in Phase 3 has passed yet the
symptom persists.

## 4.1 Missed-block checklist ("it should have been blocked but was not")

Once element ④ (observe mode) is ruled out, work through these non-configuration causes so that a working
rule is not misjudged as broken:

| Check | Notes |
|-------|-------|
| Does the block actually come from the origin | Either criterion settles it: the WAF log shows **no block record at all** while the customer sees 4xx/5xx; or `status == upstream_status` (the status code is passed through from the origin). Both point to: WAF is not broken, WAF simply did not block this request — explain that to the customer and point them at the origin. **Do not take on WAF-side responsibility** |
| Preceding-rule short-circuit / priority | The request was handled by a higher-priority rule first, so later rules never ran. If the log does not record this rule but does record others, this is the cause |
| Whitelist early allow | The request matched a whitelist and was allowed through, so blocking rules never matched (whitelist effectiveness **itself** goes to the dedicated skill, but as a cause here it must be ruled out) |
| Timing of config vs request | Configuring or editing a rule has a rollout delay. If the sample request predates the rule's configuration or rollout completion time, that is expected, not a failure. For "it worked yesterday but not today", align the failure onset with the most recent configuration change |
| Did the request reach the detection engine at all | Requests with a 3xx forced redirect (log `status`) bypass the engine, so no policy applies |
| Is the request body beyond the inspection range | ALB service-mode onboarding inspects at most 8KB of the body; anything beyond that is not inspected |
| Onboarding-mode capability differences | Some onboarding modes support body length and regex conditions differently from central WAF: **the configuration saves but has no effect** |
| Is the attack type within scope | Anything outside web application layer protection (pure client-side issues, non-HTTP protocols, behaviour inside an encrypted payload) will not match |
| Can the match conditions really match that request | Multi-value cases must use a multi-value operator such as "equals any of"; several parallel "equals" conditions are mutually exclusive. Do not mix up the field mapping: **URL** in a rule maps to log `request_uri` (query included), **URL-Path** maps to `request_path` (query excluded); the engine collapses consecutive `/` in the URI |
| IP geolocation database bias | Rules with a region condition depend on the IP geolocation database; classifying a domestic IP as overseas causes false blocks, and the reverse causes misses |
| Did the block happen but get misread | WAF security protection returns **405** when it blocks; the customer may read 405 as "not blocked" |

> Reverse corroboration: check in the logs whether the attacked request's `matched_host` **is exactly** the
> protection object you checked (wildcard and multi-domain setups are frequently mismatched).

## 4.2 Statistical rules (CC / rate limiting / scan protection)

Statistical rules are not "match the condition, take the action" but "**take the action only once the count
within the statistical window crosses the threshold**". Therefore, when they do not fire, the cause is
**usually that the count within the window never reached the threshold, not a broken configuration chain**.
Review the window and threshold first, then the rest (all settings live in the rule `Config` JSON):

| Symptom | What to check |
|---------|---------------|
| Threshold reached but nothing triggers | **Check the statistical window and count threshold combination first** (too long a window or too high a threshold means it is never actually reached); then check whether the counting subject is IP or session (a session subject actually counts `acw_tc`, and the session dimension is unavailable when the object has `AcwCookieStatus=0`) |
| Ban scope too wide after triggering | The scope of the generated blacklist is set by configuration: `effect: service` → applies to the **whole protection object**; `effect: rule` → applies only within the **rule's match conditions** |
| Many legitimate users banned | With IP as the counting subject, a shared NAT egress causes collateral damage — switch to the session dimension. If the client IP resolution itself is in doubt, run a real-IP diagnosis first (`XffStatus` / custom header configuration) |

> Element ④ applies to statistical rules too: in observe mode a CC / rate-limit rule records hits but bans nothing.

## Phase 5: Reverse corroboration with SLS logs (optional)

When the customer has WAF log service enabled, corroborate against their own SLS WAF logs
(filter by `matched_host` + `final_rule_id` / `rule_id`):

| Log finding | What it points to |
|-------------|-------------------|
| Hit records exist but `xx_test=true` | Observe mode (element ④) — even `xx_action=block` does not mean it blocked |
| Hit records exist with `xx_test=false` and `final_action=block` | It did block; go back to the "405 misread" item in 4.1 |
| No block record at all while the customer sees 4xx/5xx; or `status == upstream_status` | The status code is passed through from the origin; point them at the origin |
| No hit for this rule but hits for other rules (`matched_rules`-style fields) | Preceding-rule short-circuit / whitelist early allow (see 4.1) |
| The quad all passes yet the logs show no hit | **Contradictory evidence** — record it honestly and escalate with a ticket plus the ruled-out items; do not hard-code a root cause |

> If the logs cannot be retrieved or log service is not enabled, mark it "not retrieved" and state which
> rulings therefore cannot be closed. **Never use that as "no hit".**
