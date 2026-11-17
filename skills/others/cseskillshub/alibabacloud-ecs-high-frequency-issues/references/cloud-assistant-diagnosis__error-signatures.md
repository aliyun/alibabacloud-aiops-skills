# Error signatures: console wording to category

The console localises its message text, so the customer's wording may arrive in
any locale; the tokens below are the English forms this scenario's cases produced
(plus one or two stable product tokens that survive localisation). The scripts
match these; this page explains what each means and what the first move is.
Every row's case ids are the support tickets the wording was actually observed
in - nothing here is invented.

| # | Customer-visible wording (English form) | Category | What it really means | First move | Cases |
| --- | --- | --- | --- | --- | --- |
| 1 | "The command execution has been timeout" | COMMAND_TIMEOUT | Three explanations survive: the agent never answered (missing/stopped), the guest is too saturated to run the task, or the script genuinely needs more than its timeout. The ownership and lifecycle checks come first. | triage gates (visibility, lifecycle), then history + failure-window monitor curves (customer), then whitelisted df_h / df_i probes with consent | T-D87E8F47, T-DE98E694, T-02E6175C |
| 2 | "CLIENT_RESTARTED" / task interrupted without an exit code | CLIENT_RESTARTED | The agent process restarted mid-task; a load spike is the usual trigger. The source case never closed the loop - the honest output is a load-side evidence list plus a persistent-monitoring suggestion, not a proven cause. | ask for monitor curves around the interrupt time (customer console action); degraded reading list if instance operations are declined | T-FA7FC9EE |
| 3 | Repeated health checks return an empty array | AGENT_NOT_READY | No agent is checking in. Strongly associated with a system-disk re-initialisation or OS reinstall that did not leave a working agent behind. | readiness steps (install/start, customer-run); re-init awareness from the case history is a candidate to test, confidence low | T-270E4605 |
| 4 | "is not recognized as an internal or external command" / "the system cannot find the file specified" / a Windows image-resource-type error for every command | GUEST_ENV_BROKEN | The channel works - commands reach the guest - but the guest's own execution environment is damaged. Not a Cloud Assistant defect; do not chase the agent. | reproduce interactively (customer session), then hand off to the instance-state / OS repair area with the snapshot-first warning | T-E172703F |
| 5 | "The operation is invalid due to a task conflict" style wording when force-restarting | TASK_CONFLICT | A concurrent operation (an expansion job in flight, a pending reset) blocks the lifecycle action. No Cloud Assistant causality. | list in-flight tasks in the console; lifecycle conflicts go to the instance-state area | T-D6F80375 |
| 6 | Password reset fails with a Cloud Assistant abnormal / needs-upgrade message | VERSION_UPGRADE or DEPENDENCY_FEATURE_BLOCKED | Online reset is carried by the agent; an old agent version could not reach the current service endpoint (the support engineer proved it by reading the agent's own log - a read outside this skill's whitelist). | upgrade guidance (customer-run) or the documented offline reset fallback: snapshot first, reboot expected | T-1A68E453, T-A0FC6112 |
| 7 | File backup alarm: "Cloud Assistant is not started" | AGENT_NOT_READY | The agent service is installed but stopped (or absent); file backup depends on it. Customers new to this scenario often do not know what the agent does - explain the dependency first. | readiness steps: Linux service start and Windows services-manager start are customer-run; verify via new history afterwards | T-BB00A07B |
| 8 | "The cloud assistant command for expanding the disk failed" / console expansion task failure | EXPAND_TASK_FAILED | Paid-for capacity but the partition and filesystem still carry the old size; or the dispatched command died on load, a missing partition tool, a broken resolver, or Windows simply not being covered by the auto path. | answer only why the task failed (history Output is decisive), then hand the growth itself to the disk-expand area, snapshot first | T-79753A0F, T-521F4C4C, T-478C2A19, T-99046C78, T-D6F80375 |
| 9 | Installer/package errors in the command Output (repository unavailable, "not supported" for a named OS release, no compatibility statement) | SOFTWARE_INSTALL_FAILED | The channel is healthy; the command content failed. In the source case the OS release ships a different container engine (moby, not docker-ce) and the database product had no published compatibility note. | read the fetched Output; software selection and installation are the customer's own action - no agent conclusion here | T-A9825E98 |
| 10 | "Commands appear that I never ran" + access-key leak alert | ACCESSKEY_ABUSE | A leaked key lets an external caller dispatch commands through the very channel being diagnosed. Channel integrity is not the bug; credential governance is. | run the invocations evidence list per affected region; then the manual security order: disable the key, snapshot, respond with a security team. This skill stops at evidence | T-2A028B99, T-9BEAB951 |
| 11 | "After installing Cloud Assistant the server blue-screens / cannot boot" | (timing claim, route carefully) GUEST_ENV_BROKEN at best | Source-case outcome: support proved a damaged system registry hive; the agent install was correlation, not established causation. Several repair paths failed before re-initialisation. | do not adopt the causation: state the evidence boundary, then hand to the instance-state area; snapshot-first; watch the retention-window lesson of the same case | T-75912401 |
| 12 | Workbench CLI cannot connect on a non-default port / session downgrades to another mode | not this scenario | A defect or behavior of the Workbench CLI tool itself; the Cloud Assistant channel was never the failing part. | hand off to the Workbench CLI skill; interim: native SSH client | T-27821D2C |

## How the scripts use this table

- `triage --error-text` matches row tokens (lower-case substrings) to a
  category; the category selects the candidate set and the `NEXT_ACTION`.
- When the wording matches nothing, the history rows speak: a record whose
  status or ErrorInfo contains "timeout" routes to row 1, "CLIENT_RESTARTED"
  to row 2, and Output containing installer text to row 9. Empty history plus a
  visible, Running instance routes to row 3 or 7.
- Rows 4, 5, 11 and 12 are **recognition rows**: the correct output is a
  boundary statement plus a hand-off (see `handoff-matrix.md`), not a repair
  attempt. Mis-claiming them is the failure mode this scenario was built to avoid.

## What is NOT an error signature here

No standard OpenAPI error-code table was supplied for this scenario's surface, so
this page quotes customer-visible wording only, each line traced to a ticket.
The literal `NoPermission` / `ImplicitDeny` pair in the scripts is the only
authorization code vocabulary this skill prints. If a customer pastes a raw
`Code:` line the table does not know, the report keeps it verbatim in the
inputs and classifies on history instead - it never maps a guessed meaning
onto an unknown code.
