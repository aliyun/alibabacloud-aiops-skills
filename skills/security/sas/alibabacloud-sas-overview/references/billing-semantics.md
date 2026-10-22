# Billing interpretation and FAQ

Requirements: 85558306 / 85558292. Contract checked against the official
[DescribeVersionConfig documentation](https://help.aliyun.com/zh/security-center/developer-reference/api-sas-2018-12-03-describeversionconfig)
and API metadata on 2026-10-18.

## Are subscription and pay-as-you-go mutually exclusive?

Not globally. The documented MergedVersion field explicitly covers simultaneous
subscription and pay-as-you-go host/container protection. Do not publish an
account-wide mutual-exclusion rule. Restrictions on a particular module require
that module's current product contract; this read-only overview does not change
billing or enable modules.

## How should the response be interpreted?

Use `python3 scripts/overview_response.py billing < response.json` on the full
DescribeVersionConfig response. Report these independent dimensions:

| Evidence | Interpretation |
|----------|----------------|
| IsPostpay true / false | Pay-as-you-go opened / not opened; not a subscription flag |
| IsPostpay missing or wrong type | Unknown; do not infer it from IsPaidUser |
| InstanceId, Version, ReleaseTime | Report purchased instance/version and expiry evidence separately; a historical expiry is not proof of an active subscription |
| PostPayModuleSwitch | Parse the JSON string. 1=enabled, 0=disabled; missing keys are unknown, not disabled. Preserve unfamiliar module codes |
| PostPayStatus 1 / 2 | Normal / suspended for overdue payment; do not call suspension a RAM problem |
| IsTrialVersion 0 / 1 | Non-trial / trial; do not treat a trial as a paid subscription |

IsPaidUser is not a supported discriminator in the current published response
schema. Old responses containing only that field need an explicit “billing mode
unknown” result, not the previous false=>postpay shortcut. Missing fields and
malformed switch JSON must remain visible as unknown/partial data.

## Why is a module unavailable?

Distinguish not opened, unsupported edition, expired/suspended service, missing
asset authorization, and an actual Forbidden/permission response. A disabled
module is not proof of missing RAM permission. A module switch is not a bill:
use QueryBill for actual amounts. Never infer “no charges” from an empty switch map.

## Validation

CORRECT: show subscription evidence and enabled POST_HOST simultaneously when
both are returned. Retain trial, suspended and unknown states independently.
INCORRECT: select exactly one billing mode from IsPaidUser, suppress module switches
for a subscription account, or turn malformed JSON into an empty map.

Run `python3 -m unittest discover -s tests -p test_billing.py`.

## Service dates

The current API defines OpenTime (service opening), PostPayOpenTime (pay-as-you-go
opening), and ReleaseTime (instance expiry), all in milliseconds. CreateTime is not
a documented field. Use `scripts/overview_response.py times` to validate dates and
calculate separate elapsed days. A missing date cannot prove a service is unopened;
show unknown with its reason, including for postpay users.
