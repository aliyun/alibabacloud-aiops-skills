# Moved — see [guest-diagnostics.md](disk-pl-change-guide__guest-diagnostics.md)

Module M4 now lives in
[guest-diagnostics.md](disk-pl-change-guide__guest-diagnostics.md). That module is the single
source for the in-guest boundary: the five allowlisted non-mutating listing
commands that `scripts/axes/disk_pl_change_guide/disk_pl_advisor.py --mode guest` can dispatch after an
explicit per-command confirmation, the announce-before-dispatch template, the
refusal table, the customer-run attribution commands, the reading rules, and
the DEGRADED contract.

This file holds no knowledge of its own and is kept only so older links keep
resolving. Nothing here overrides that module.
