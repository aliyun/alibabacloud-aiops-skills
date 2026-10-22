# Service prerequisites and self-checks

Before API examples, initialize and reuse the manifest-derived `USER_AGENT` as
described in [SKILL.md](../SKILL.md#observability).

Check only the capabilities in the confirmed scope. A score-only request does not
require a WAF or billing preflight. Reuse responses within the same account/session.

| Capability | Prerequisite / evidence | Missing prerequisite |
|---|---|---|
| Basic SAS overview queries | SAS read permission; validate actual API response | Permission/query error, not a blanket paid-edition rejection |
| Paid SAS feature statistics | DescribeVersionConfig: Version, IsPostpay, IsTrialVersion, PostPayModuleSwitch; actual feature API availability | Confirmed unopened/unsupported: not applicable with reason; missing evidence: unknown |
| Service dates / billing configuration | DescribeVersionConfig; fields validated independently | Missing fields stay unknown; preserve valid fields |
| WAF protection statistics | WAF 3.0 (API 2021-10-01), WAF read permission, instance in the selected WAF region | WAF 2.0: unsupported; confirmed no instance: not applicable; failed discovery: error |
| Bill details | bss:QueryBill, selected account/site and month | Denied query: unavailable; no automatic policy attachment |

## Self-check commands

After credentials and relevant parameters are confirmed, run only the needed check:

```bash
# SAS feature/service configuration, reusable for Modules 2 and 5
aliyun sas describe-version-config --user-agent "$USER_AGENT"
# WAF 3.0 instance discovery; choose the confirmed WAF service region
aliyun waf-openapi describe-instance --region "$WAF_REGION" --user-agent "$USER_AGENT"
```

Interpret configuration with `python3 scripts/overview_response.py billing < response.json`.
The current API documents Version 1 as free, 3 enterprise, 5 advanced, 6 anti-virus,
7 ultimate, 8 multi-account, and 10 value-added plan. These labels do not establish
entitlement to every feature. PostPayStatus 2 indicates overdue; a switch value of
1 alone must not be presented as proof of a healthy, authorized service. Trials and
subscription/pay-as-you-go coexistence must be preserved. Confirm capability-level
access from the specific API; do not invent a minimum edition without its contract.

Distinguish four outcomes: valid result (including zero), confirmed unavailable
service, permission/query error, and unknown configuration. Continue independent
requested modules; explicitly label partial coverage. Never turn an empty response
or error into a recommendation to buy a paid edition.

Source: [DescribeVersionConfig](https://help.aliyun.com/zh/security-center/developer-reference/api-sas-2018-12-03-describeversionconfig), checked 2026-10-18.
