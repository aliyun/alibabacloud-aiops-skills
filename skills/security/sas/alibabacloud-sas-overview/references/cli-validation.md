# CLI validation record — 2026-10-18

CLI: 3.4.11. SAS plugin: 0.7.10; WAF plugin: 0.7.6. BSS plugin updated locally
from 0.7.5 to 0.9.5 during validation.

All 14 active API command/flag contracts were checked against complete help:
11 SAS commands (2018-12-03), 2 WAF commands (2021-10-01), and QueryBill
(2017-12-14). `--current-page`, `--page-size`, `--machine-types ecs`,
`--cal-type home_security_score`, WAF required `--instance-id`,
`--start-timestamp` (seconds) / `--interval` (multiple of 60), SAS chart times
(milliseconds), and BSS `--billing-cycle` (YYYY-MM) agree with the installed help.
`--user-agent` is accepted by the dispatcher but not listed in generated API help.
The local configure/plugin maintenance commands reject it, so they omit it.

## BSS plugin recovery and final result

The old BSS 0.7.5 package had no usable query-bill help. After updating to 0.9.5,
direct plugin help exposed the full contract. Initial regular-CLI checks still
returned only a banner/exit 255; those attempts were correctly treated as failures.
A final fresh run of `python3 scripts/check_cli_contract.py` through the regular
`aliyun` launcher returned checked_commands=14 and failures={} (exit 0), including
BSS. The reason for the transient post-update launcher failure was not established.

Both the cached-help check and the final regular-CLI check passed. Do not use exit
status alone in future checks: complete Usage/API Version/parameter output remains
required. No actual SAS/WAF/BSS cloud data was queried, and these checks do not
validate live permissions, account-specific endpoints or business-data correctness.
