# Evidence, degradation, and privacy

Three contracts, each learned from a failure mode in this tier's tickets: every
conclusion is bound to a reading that is in the report; a blocked evidence path
produces an explicit DEGRADED result rather than a guess; and no credential ever
leaves the machine that holds it.

## 1. Evidence traceability

- Every finding cites the API field or guest output line that produced it, plus the
  rule id (R1-R9) and the caliber (mean or max, host-view or in-guest, percent or
  absolute, window start/end). See `scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py`
  `evaluate()` and `render_text()`.
- **No resource may be mentioned that a call did not return.** Not an instance, not
  a disk, not a snapshot, not an installed agent, not a log file. Ticket T-50C39C59
  is the lesson: an answer that confidently described things which did not exist
  sent the customer on a wasted operation. Rule R8 enforces this: if a customer
  names a resource that is absent from the returned inventory, the run stops on an
  existence mismatch.
- Every parameter the report used is echoed back in the report's "collected
  parameters" section, and values the script filled in automatically are marked as
  such. A reader can therefore tell which inputs the customer gave and which the
  tool assumed.
- Declared API versions and the exact action list are printed at the top of each
  report, so a reviewer can compare the run against `related_apis.yaml` and
  `references/ram-policies.md` without re-deriving it.
- A run is traceable to an account: the `sts:GetCallerIdentity` result is rendered
  as `account:uid-****<last4>` (`sts_token.py::uid_traceability_label`) — enough to
  attribute the report, never enough to be a credential.

## 2. The four real evidence-blocking causes, and the DEGRADED branch for each

These are the four ways a diagnosis in this tier actually fails to get its
evidence, ordered by how often they occur in the corpus. Each has a named branch.
Silence and guessing are both worse than a DEGRADED report.

### (a) The customer does not authorise in-guest inspection
Tickets T-6143D71E, T-1D5C74FB, T-570E51B9. In several tickets the whole
interaction ended at this gate: "either authorise on-machine access, or the
investigation stops".

**Branch.** Report the cloud-side findings that *were* obtained (instance shape,
disks, metrics, co-peaks), state precisely which question needs the guest —
process-level CPU/memory ranking, `kswapd` presence, historical replay — and stop
there. Never characterise an unverified in-guest cause as likely. Never treat
silence as consent: a confirmation quote is required per run, and placeholder text
is rejected by `guest_evidence.py::is_valid_confirmation`.

### (b) Wrong or expired credentials
Tickets T-441637A1 (three separate occurrences), T-69AEDFA2, T-3EA06F17.

**Branch.** The identity check is the first call of every run, and
`--check-auth-only` runs it alone. A failure reports `InvalidCredential`,
`NoPermission` or `ImplicitDeny` with the guidance in
`sts_token.py::identity_guidance_lines`: refresh the local chain with
`aliyun sts get-caller-identity`, confirm the RAM principal belongs to the account that owns the
instance, and see `references/ram-policies.md` for the exact actions. The run
**never** asks the customer to paste an AccessKey or token, and never reads,
prints or passes key material. A mismatch between the credential's account and the
instance's owner is an R8 finding, not a warning to proceed past.

### (c) CloudMonitor agent and/or `atop` were not installed
Tickets T-D25A9845, T-36BC7559, T-6143D71E, T-BF2F77A0. Without the agent the OS
memory metric has no data, so "was it memory?" is unanswerable from the cloud side;
without `atop` there is no per-process history for a past minute.

**Branch.** Emit the R6 gap with the metric name that returned nothing, name the
missing collector, and say what it would have proven. An empty series is never read
as `0%` and never read as `normal`. Point at Template 6 of
`references/resource-bottleneck__human-actions.md` so the next incident is diagnosable, and use the
guest-side fallbacks that do not need an agent (`free -m`, `vmstat 1 3`,
`top -bn1`, gated).

### (d) The instance is frozen — SSH, RDP *and* console VNC all fail
Tickets T-570E51B9, T-1BBB1704.

**Branch.** This is itself a finding, and the strongest one available: a
connectivity failure on every path while the cloud-side readings show memory
pressure plus pinned disk IO is the R1 chain at its terminal step. Report it as
DEGRADED with the diagnosis explicitly incomplete, state that no in-guest evidence
can be collected while the agent cannot answer, and move to the recovery sequence
in `references/resource-bottleneck__human-actions.md` (snapshot, then the three-risk reboot notice).
Do **not** conclude "nothing wrong inside" from a command that never ran.

`STATUS` is set by `determine_status()` and is honest about this: `OK` when the
evidenced areas answered the question, `DEGRADED` when a branch above applied,
`FAIL` when nothing usable was obtained. `NEXT_ACTION` is always printed and names
the single next step, including the manual one.

## 3. Credentials and privacy

- **Nothing secret is ever echoed.** Not by this skill, and the operator is told to
  refuse it too. Ticket T-7E06B86C is the reason a prohibition is written down
  rather than assumed: an engineer pasted the instance root password into the
  chat. If a customer supplies a password, key, token or the VNC credential in
  conversation, do not repeat it, do not quote it "for confirmation", do not
  include it in the ticket record — state that it was exposed in the conversation,
  and advise rotating it.
- **Masking is applied on the way out, not on request.** `_cli.mask_credentials()`
  runs over every error string, every stderr fragment, and every decoded guest
  output before it reaches the report or the terminal; the patterns and the
  replacement (`***`) are in `_constants.py::SENSITIVE_KEY_PATTERNS` /
  `MASKED_VALUE`. It covers `AccessKeyId`, `SecurityToken`, `Signature` and
  password-shaped keys. Guest output is masked *before* it is parsed, so a secret
  cannot travel into a finding's quoted line either.
- **Key material is never a parameter of this package.** There is no key, token or
  profile argument anywhere in the call path; the aliyun CLI default credential
  chain is used and nothing else. A failure therefore points at
  `aliyun sts get-caller-identity`, not at a request for the customer's secret.
- **`.gitignore` blocks the paths where secrets could accidentally land**: `.env`,
  `.env.*`, `*.pem`, `*.key`, `.sts_cache.json`, plus report outputs
  (`report*.json`, `report*.md`), so a generated capture is never committed.
- **Report files are create-only.** `write_report_file()` opens with mode `x` and
  refuses an existing path: it will not overwrite a file, which also means a second
  run cannot silently splice new guest output into an earlier customer's capture.
- **Only the data the diagnosis needs is requested.** No bulk export of instance
  lists across regions, no customer identity lookups, no log collection beyond the
  single whitelisted command whose text the customer approved.
- Full captured output stays on the terminal of the operator who ran it; the report
  truncates with an explicit marker (`OUTPUT_SNIPPET_MARKER`) rather than silently
  shortening, so the reader knows a longer capture exists.

## 4. Facts versus advice

The report states resource-side facts. It does not recommend a spec, a family, a
price, or a refund route; those are commercial decisions belonging to the customer
and to billing (`references/resource-bottleneck__escalation-map.md`). Where the customer asks "should I
upgrade?", the answer this skill gives is the saturated area, its caliber, its
window, and the process-level attribution that is still missing — and then the
question is handed to a human with those readings attached.

Where a fact is not available in this package, it is labelled as pending rather
than asserted. The open items inherited from the requirements document (section 8)
are recorded where they belong: `acs_ecs_dashboard` namespace and the CloudMonitor
`Period`/metric-name set in `references/resource-bottleneck__metric-catalog.md`; the excluded
`create-snapshot` console action in `references/resource-bottleneck__human-actions.md`; the network and security
handoff names in `references/resource-bottleneck__escalation-map.md`; the two candidate `atop` doc links
in `references/resource-bottleneck__human-actions.md`; and the absence of quotable error strings in
`references/resource-bottleneck__log-signatures.md`.
