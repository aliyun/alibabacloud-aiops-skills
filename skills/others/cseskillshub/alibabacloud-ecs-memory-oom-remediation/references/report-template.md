# Report template

Field order is fixed for every run. A field whose evidence did not come back is written
as `Unknown / not collected`; it is never left blank and never filled from an
assumption.

Delivery: the entry script prints this report as a ```text code block followed by a ```json
code block; both are the deliverable and must be quoted **verbatim in the final chat reply**
(see the *Final Answer Delivery Contract* in SKILL.md), together with every guidance/warning
line the run emitted. Saving them to a file or summarising them does not count as delivery;
keep the literal `STATUS:`, `NEXT_ACTION:`, precondition names and verdicts, and
evidence-source labels. The script also prints a `=== FINAL ANSWER DELIVERY (MANDATORY) ===`
directive after the JSON block; obey it literally and paste both code blocks into the reply.

```text
=== ECS MEMORY OOM REMEDIATION REPORT ===
Region: <region id> | Instance: <instance id>
Account scope: queries see account <account id> only
Instance spec: <instance type> (<vcpu> vCPU, <memory> MiB) | OS type: <os> | status: <state>
PRIMARY-CAUSE: <token-dense main finding + the recommended action; kept at the top so it
survives a summary>

[Routing]
- Symptom branch: <oom | iops | hang | cpu | root-cause | unknown>
- Memory-pressure evidence: <PASS | UNKNOWN> (<named signals, or why none>)

[Swap preconditions]
- linux_instance: <PASS | FAIL | UNKNOWN>
- memory_at_most_8gib: <PASS | FAIL | UNKNOWN>
- memory_pressure_evidence: <PASS | FAIL | UNKNOWN>
- disk_free_at_least_5gib_after_change: <PASS | FAIL | UNKNOWN>
- system_disk_is_not_basic_cloud_disk: <PASS | FAIL | UNKNOWN>
- swap_plugin_available_in_guest: <PASS | FAIL | UNKNOWN>

[Recommendation]
- Recommended action: <one lane>
- Reason: <which precondition decided it>
- Risk or limit: <the Swap trade-off, or the limit of the advice given>

[Node.js runtime]
- one line per node process, or "no node process in the snapshot"

[In-guest evidence]
- Swap state / disk I/O utilisation / free space on the root filesystem /
  rotational flags / top resident-size processes / atop availability, active
  file, last sample timestamp and rotation state

[Verification after remediation]   (after a confirmed change, or with --verify)
- per compared key: before=<value> after=<value> -> <EASED | WORSENED | STILL PRESENT |
  CONFIGURED | REMOVED | UNCHANGED | UNVERIFIED | NO BASELINE> (<one-line reason>)

[Degradations]
- every refused, failed or empty read, in the order it happened

STATUS: <OK | DEGRADED | INPUT-NOT-FOUND | FAILED>
NEXT_ACTION: <what the customer or the agent does next>
```

A JSON block with the session id, account scope, symptom branch, whether guest reads
ran, whether a Swap change was requested, and the degradation list is appended after
the text report.

## Marking rules

- Each conclusion carries its evidence source: cloud read, in-guest collector, atop
  history replay, or not collected.
- `CONSENT-REQUIRED:` means the in-guest read was refused for lack of a consent token;
  the cloud-side part of the report is still valid.
- `SWAP-CHANGE-BLOCKED:` names the unmet preconditions and is followed by guidance,
  never by a change. An unconfirmed request never reaches this code path at all: the
  report simply recommends guidance and delivers nothing.
- `SWAP-CHANGE-ALREADY-CONFIGURED:` means the customer confirmed an `enable`, but the
  guest reading already shows Swap with room left, so nothing was delivered and the next
  step is the memory holder, the runtime limit or the spec.
- `OS-TYPE-LIMIT:` means the guest is not Linux, so the frozen shell collector was not
  dispatched and every guest-derived field stays unverified.
- `SWAP-CHANGE-AGENT-UNREACHABLE:` means the customer did confirm, but the Cloud
  Assistant status read reports the agent as `offline` or `unresponsive`, so the change
  was not delivered. A change nobody could confirm is not a configuration either:
  the report never calls the Swap state applied in this case.
- `Cloud Assistant agent:` carries the freshness evidence, e.g.
  `online (last heartbeat 2026-11-11T08:55:00Z, 300 s ago)`, `unresponsive`, `offline`,
  `unknown (no status row came back)`.
- `unresponsive` is decided by the heartbeat, at a threshold of 900 seconds. Measured on a
  live instance: a running agent refreshed `LastHeartbeatTime` roughly every 60 seconds,
  and after the agent service was stopped `CloudAssistantStatus` kept reporting `true` for
  at least 19 minutes while the heartbeat stayed frozen. The flag alone therefore cannot be
  trusted as proof of answerability, and an old heartbeat blocks the dispatch.
- `CREDENTIAL-FAIL-CLOSED:` means nothing was read at all; no other section may appear.
- `PERMISSION-GAP:` names the refused read and states that a refused or empty result
  is not evidence that the instance is healthy or absent.
- A CloudMonitor reading the API refused is written as `UNKNOWN (<error code>)`, and the
  memory-pressure line then says the reading could not be read. It is never written as
  "no datapoint": a refused read and an empty read are different facts, and only the
  second one may be described as missing data.
- `ENVIRONMENT-DEPENDENCY:` means the CLI product plugin is missing in this
  environment; the install hint is given and no cloud state is claimed.
- A Swap recommendation is always accompanied by the statement that upgrading the
  instance spec is the real fix.
