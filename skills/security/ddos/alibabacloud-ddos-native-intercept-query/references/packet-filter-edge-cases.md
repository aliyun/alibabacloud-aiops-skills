# Edge Cases Where packet_filter Intercepts Do Not Match PortRuleList

Reference for troubleshooting `InterceptModule = packet_filter` intercepts when the IP-specific Mitigation Policy `PortRuleList` does not align with intercept records.

## When to Read This Document

Consult this document only when you actually encounter **any** of the following situations during troubleshooting. There is no need to preload it for routine investigation:

- (a) The current IP-specific Mitigation Policy's `PortRuleList` is empty
- (b) `PortRuleList` contains rules, but the protocol/port in the intercept record **does not fall within the coverage of any rule** (rules exist but none match)
- (c) The number of `PortRuleList` rules is clearly disproportionate to the intercept distribution (e.g., there is only 1 UDP rule, but TCP ports also show a large number of `packet_filter` intercepts)

**Do not** immediately conclude "system anomaly", "data mismatch", or "module misclassification". This is normal behavior, and there are two possible explanations.

## 1. Port Blocking Originating from the Default Policy (Not Visible in Custom Policies)

Port blocking rules deployed by the default policy **do not** appear in the user's console "Port Blocking" list, **nor do they** appear in the custom policy `PortRuleList` returned by `ListPolicy`, but they **do** generate intercept records under the `packet_filter` module. There are two sources, both attributed to the "default policy" layer:

- **(1.1) Built-in port blocking in default policy templates**: All default policy templates (including the three level-based templates `normal`/`strict`/`loose`, as well as business scenario templates such as `game_tcp`/`game_udp`/`office_network`/`gf_origin_protect_eip_*`) **may include** a fixed set of built-in port blocking rules. As long as the IP is bound to a default policy, these rules remain in effect. For the specific rules built into each template, refer to `default-policy-details.md` in the same directory.
- **(1.2) Temporary port blocking deployed by AI Intelligent Protection**: When AI Intelligent Protection is enabled in the default policy (`EnableIntelligence=true`), it automatically deploys port blocking rules upon detecting an attack, which automatically expire after the attack ends.

Key point: Both types of rules **coexist** with the user's custom `PortRuleList` and are not mutually exclusive. Even if the user's `PortRuleList` already contains custom rules, as long as the protocol/port in the intercept record **falls outside the coverage of the user's custom rules** and still belongs to the `packet_filter` module, the source is the default policy — this is not a bug or a data mismatch. **There is no need to strictly distinguish between 1.1 and 1.2** (roughly: intercepts concentrated during attack bursts lean toward temporary deployment; intercepts evenly distributed across the window lean toward built-in template rules). When conflicts arise, simply explain to the user: "This intercept originates from the default policy and does not conflict with your custom rules." There is no need to further investigate whether it is template-built-in or AI-deployed.

## 2. Historically Deleted Port Blocking Rules

The user previously configured port blocking rules in a custom policy but later deleted them in the console. When querying intercept records for a historical time window, the intercept records generated at that time still exist in the intercept records table with the module `packet_filter`, but the corresponding rule can no longer be found in the current policy. It is normal that the rule cannot be found in this situation.

## Decision Path

When encountering this type of situation during troubleshooting, follow the decision path below and clearly inform the user:

- Custom policy `PortRuleList` is empty / does not match the intercept records -> The source is the **default policy** (template-built-in or AI-deployed), and it **does not conflict** with the user's custom rules nor is it a bug; there is no need to precisely distinguish between 1.1 / 1.2
- The user recalls deleting port blocking rules -> Residual intercept records from historical rules; can be ignored
- The user's custom `PortRuleList` **contains** rules but the intercept record hits a **different port** -> Do not force-attribute it to that rule; explain it as "originating from the default policy"
- None of the above situations **affect the current protection configuration**; if the user suspects a false positive, further investigation can be done by correlating intercept timestamps with business logs
