# Remediation Table (root cause → temporary / permanent fix)

Map the located root cause to a row. Temporary fixes are what the customer can do right now; permanent fixes
address the cause. **All write actions are executed by the customer** — this skill only supplies the console
path.

Console navigation paths keep their original Chinese console wording so the customer can find them in the UI.

| Root cause | Temporary fix | Permanent fix |
|------------|---------------|---------------|
| Rule does not exist / was never saved | Reconfigure in the console and confirm it saved | Investigate the error raised during configuration |
| Rule disabled (element ①) | Console: enable rule X under template Y (path P-1 below) | Add a rule-toggle check to post-release regression |
| Object not bound to the template (element ②) | Console: add object Z to template Y (path P-2 below) | Map out template-to-object bindings and fix the configuration order |
| Template disabled (element ③) | Enable template Y | Clean up duplicate / retired templates to prevent misuse |
| Rule in observe/monitor mode (element ④) | Explain that the rule does not block requests and that `xx_action=block` in the log is only a default hit marker; if the customer reported a status code, **also tell them it comes from the origin and point them there** | Switch the action to block if blocking is genuinely required; explain the difference between observe and block |
| Domain inside the default protection object group | Move the object out of the default group, then give it its own rule | Design a layered strategy for object groups vs single-object rules |
| Protection object not finished initializing | Retry the binding once `ResourceStatus` becomes `active` | Add an initialization wait step to the onboarding runbook |
| Template binding count at quota | Trim the bindings on that template or split into a new one | Open a ticket to assess edition / quota |
| Preceding-rule short-circuit | Adjust rule priority order | Rework the rule priority design |
| Whitelist early allow | Narrow the whitelist match conditions | Separate the scopes of whitelist and blocking rules |
| Onboarding-mode capability limit | Explain the limit and offer a workable alternative condition | Open a ticket requesting the capability |
| IP geolocation database bias | Allow-list the misclassified address ranges | Open a ticket to have the geolocation data corrected |
| Match conditions written wrong | Switch to a multi-value operator / fix the URL vs URL-Path field | Validate match behaviour against the logs after configuring |
| Block happened but was misread (405) | Corroborate with log `status` and `final_action`, then explain | Document the block response signature to prevent future misreads |
| Block comes from the origin | No WAF-side action needed | Explain and point the customer at the origin; **do not take on WAF-side responsibility** |
| Count within the window never reached the threshold | Shorten the statistical window or lower the threshold | Re-baseline the threshold against real business QPS |
| Ban scope too wide / false bans | Switch to `effect: rule` or the session dimension | Review the client IP resolution configuration (XffStatus) |
| Quad passes but logs show no hit (contradiction) | No customer-side action; **open a ticket with the ruled-out items**, do not invent a root cause | Product team investigates the rollout path |
| Multiple domains / rules failing at once | No customer-side action; state the consistency of the symptom and **open a ticket to check platform-side rollout** | Product team investigates the config rollout / sync path |

Console navigation paths keep their original Chinese console wording so the customer can find them
in the UI:

```
P-1 控制台 → 防护配置 → 模板 Y → enable rule X
P-2 控制台 → 防护配置 → 模板 Y → 防护对象 → 添加 Z
```

## Ticket / escalation criteria

When the quad and the checklists all pass yet the logs show no hit (contradictory evidence), or when multiple
domains / rules fail at once and no configuration cause can be found, guide the customer to open a ticket with
the list of ruled-out items attached. **Do not rationalize it into a customer configuration problem.**
