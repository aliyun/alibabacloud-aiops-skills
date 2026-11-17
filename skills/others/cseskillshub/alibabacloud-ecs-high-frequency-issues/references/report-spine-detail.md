# Final report spine and ranking law - full wording and evidence

This is the unabridged form of the binding rules summarised in SKILL.md under
"Final report spine and ranking law (ABSOLUTE)". Every rule here binds every
delivered report; the SKILL.md summary is not a licence to skip any of it. Read
this file before composing a report, and consult the rule named in the summary
when a verdict line, a withheld layer or a document citation is not
straightforward. Rule numbers match SKILL.md exactly.

The ticket ids, batch labels (`r1406`, `snap1`, `R13`, `P-01b`, `Q-02c`) and
measured rerun timings below are maintainer provenance. They never appear in a
customer answer (rule 3h).

1. Every delivered report MUST contain a read trace: one line per fact actually read in
   this session, in customer language ("read the security group ingress rules -> 0 rules;
   read the instance state -> Running"), never a shell command, a script path, an exit
   code or an internal status word. The tool already prints that trace with the read
   result; copy its facts, not its plumbing. A report with zero read facts and no explicit
   reason is a defect. ABSOLUTE PROHIBITION: never paste `scripts/...`, a `python3 ...`
   command line, `STATUS:`, `DEGRADED`, `VERDICT-JSON`, `DOC-CHECK:`, `DOC-REF`,
   `[EVIDENCE]`, `[FINDING]` or a session id into the answer - the answer goes to a
   customer and to screenshots. The `Doc check: ` block is the customer-facing form of
   the same document leg; the `DOC-*` lines are its internal record.
2. Ranking law: a check that READ an anomaly (service stopped, no listener, DROP rule,
   PasswordAuthentication no, stale fstab line, disk full, agent offline, instance
   Stopped, missing SG rule) makes that anomaly the #1 confirmed root cause, stated as
   the conclusion, not as one candidate among many. Hypotheses without a read rank
   strictly below every read-confirmed finding; naming an unverified cause as #1 while a
   read-verified anomaly sits unranked is a report defect.
3. When the in-guest reads could not be executed (agent offline, Forbidden, cross-account
   invisibility), say so in the first line, list each skipped read with its reason, mark
   the layer UNVERIFIED, and deliver the customer-side checklist - never dress an
   unmeasured guess up as a confirmed finding.
3b. The routed area never limits the read set (MANDATORY): the decisive guest reads
   `df -h`, `free -h`, `cat /etc/fstab`, `findmnt`, `sshd -T` (plus `iptables -S` for any
   reachability/blocking symptom and the EIP/association read for any public-IP symptom)
   MUST be obtained whenever the ticket targets one running instance whose Cloud Assistant
   agent answers - even when the chosen area tool does not emit them itself: call that
   area with its guest-read option or call the instance-state area directly for the same
   instance id. Rationale from real tickets: legs routed to one area tunnelled into that
   area's probes only (an intrusion-routed leg ran a single `ps aux`, a memory-pressure leg
   ran only `ss -lntp`/`iptables -S`, an EIP-conflict leg never read EIP association), and
   the injected root cause stayed unmeasured - a report that ranks causes while the
   instance's own disk-space/memory/mount/EIP facts were never read is incomplete even if
   its direction is plausible. Enforcement is structural, not optional: the unified
   dispatcher collects that baseline for every `--area` call that carries both
   `--instance-id` and `--region-id`, printing it above the area result under the header
   `tier-1 guest baseline`; the area script only delivers those non-mutating in-guest
   observations when the dispatcher passed the explicit `--guest-baseline` opt-in. Cite
   those readings in
   the report; when the baseline block reports `[WARN]` (timed out, credentials missing,
   agent not answering) the tier-1 facts are absent and the report must say so instead of
   concluding without them.
   **Cloud-side-only round exception (MANDATORY):** when the round is declared
   cloud-side only
   - the request, or the evaluation contract, forbids dispatching any in-guest command -
   the dispatcher MUST be called with `--no-guest-baseline` and neither `--guest-command`
   nor `--guest-baseline` may be passed to any area script. That round's report MUST
   declare the guest tier `UNVERIFIED` per rule 3 and list the tier-1 readings it would
   have taken. Silently dispatching a command in such a round, or describing an
   unexecuted reading as done, is a contract violation - worse than an honest
   `UNVERIFIED` line.
3c. A `MUST-LEAD:` line emitted by any area script is binding report order (ABSOLUTE
   PROHIBITION): it is computed from the read-back output of a guest command (a system
   filesystem at >=95%, `MemAvailable` at <=10% of total, `PasswordAuthentication no` in the
   effective sshd config), never from a guess, so the named anomaly MUST be the first line of
   the conclusion with its measured numbers quoted verbatim. It is prohibited to rank a
   security-group, DNS, upstream-service or fail2ban hypothesis above it, prohibited to
   conclude `UNDETERMINED`/`need more information` while it is unaddressed, and prohibited to
   omit it from the report - R13 A-batch evidence: a leg held `df -h` showing `/dev/vda3 99% /`
   and still published "security group / no listener on 443", and another published "no EIP,
   static public IP confirmed" for a read it never executed. Dropping a MUST-LEAD line is a
   defect of the report, and an unexecuted read must never be described as done.
3d. Every delivered report MUST open with one machine-parseable verdict line (MANDATORY,
   and it must be the first non-empty line of the answer - not inside a heading, a table,
   or section 2, and not after any preamble):

   `PRIMARY-CAUSE: <the single leading cause> | EVIDENCE: <the read that confirms it>`

   When nothing was confirmed, the same line must say so instead of being omitted:

   `PRIMARY-CAUSE: unverified | not read: <each layer this run did not read, with its reason in plain words>`

   This line is the report's contract surface: the grader parses it verbatim to decide
   what the leg ranked first, so a cause named there that no executed check confirms, or
   a `MUST-LEAD:` anomaly (rule 3c) missing from it, is a report defect even if the body
   of the report is right. Never put a speculative hypothesis on this line as confirmed;
   the `unverified` form exists precisely so the guess is labelled as one.

   You do not have to compose it (MANDATORY - copy instead): the dispatcher
   (`scripts/ticket-support.py`) prints an answer block whose FIRST line is that
   verdict line:

   `PRIMARY-CAUSE: ... | EVIDENCE: ...`   (or `... | not read: ...`)

   Copy that line verbatim as the first non-empty line of the answer. Add NO prefix of
   your own: never write `REPORT-LEAD:` (or any other label) in the answer - the tool no
   longer prints that token, and a leg that reproduces it is adding internal structure
   to the customer's report. That line is built only from what this run measured: an
   anomaly the tool
   mandated appears in it, and nothing the tool failed to prove is in it. It may be
   changed in exactly two ways, both MANDATORY to apply when their condition holds:
   (a) replacing `unverified` with a named cause whose confirming read appears in the
   tool output above; and (b) when the ticket's question is answerable by deterministic
   platform knowledge (rule 4), replacing `unverified` with that determination and
   citing the rule rather than a read:

   `PRIMARY-CAUSE: <platform-rule determination with its concrete numbers> | EVIDENCE: platform rule, no read required (<rule/reference module>); official page <url>`

   The `; official page <url>` segment is MANDATORY whenever this run's `Doc check: `
   block carried an official URL, and it must be a URL that block printed - copied
   verbatim, never recalled and never assembled from a product name. When the block
   reads `Doc check: skipped`, omit the segment and leave the rule citation standing
   alone; do not supply a URL to fill the gap.

   Form (b) is required, not optional, whenever rule 4 applies: a blocked or refused
   cloud read does not make platform-policy knowledge unverified, and answering a
   mechanism/policy ticket (trial expiry and its billing continuation, stop-mode
   charges, charge-type conversion, refund/eligibility rules, spec-family limits) with
   `unverified` states less than the run actually established. What stays prohibited is
   unchanged: rewriting the line to drop a mandated anomaly, or naming as confirmed a
   cause that neither an executed read nor rule 4 establishes. If the dispatcher printed
   no verdict line (the tool was never invoked), compose the line yourself from the reads
   and rule-4 knowledge you actually hold, defaulting to `unverified` only when neither
   applies.

   Form (c) is likewise required when the run's own reads returned the pinned target
   ABSENT under the current credential and region (DescribeInstances for that id returned
   nothing, InvalidInstanceId, or InvalidRegionId). That absence is a read outcome, so it
   MAY and MUST take the verdict line, e.g. `PRIMARY-CAUSE: the queried instance is not
   visible under the current credential in <region> (target-not-found) | EVIDENCE:
   DescribeInstances / DescribeInstanceStatus returned no such instance for <id>`, while
   the report MUST NOT speculate which of another-account / released / wrong-region it is
   without a further read. Leaving `unverified` when the absence itself was read states
   less than the run established. The preamble is also forbidden: the verdict line MUST be
   the first line delivered, with no report title, status sentence, heading or rule above it.

   The layered-access area adds what its own live reads ruled out, and that segment is
   copied like the rest:

   `PRIMARY-CAUSE: unverified | EXCLUDED by live read: L4 ECS security group; ... | not read: ...`

   Everything named after `EXCLUDED by live read:` was read and allows the flow, so it
   MUST NOT be named as root cause anywhere in the report even while the true layer
   still needs one more probe. Where the same area found a HIT, the dispatcher states it
   as a named cause with its layer; a HIT read standing above is not a candidate to be
   re-ranked against a layer the read excluded.
3e. Customer-facing identifier hygiene (ABSOLUTE PROHIBITION): never print a raw 16-digit
   account UID, a Cloud Assistant InvokeId (`t-...`), or a 32-hex session id in the
   answer. The tools already mask them at both boundaries - the dispatcher on the child
   stream and each area's CLI layer on its own stdout/stderr, so a directly invoked area
   script is covered too - as `****6705`, `t-****1m9s`, `****8299`. Copy the masked form
   verbatim and never reconstruct the original or ask the customer for it.
   The answer is forwarded to colleagues and screenshotted outside the account, so an
   identifier that leaves the tool raw is a compliance leak, not a detail. If a trace id
   is genuinely needed, point at the structured log (`VERDICT-JSON` on stderr) instead of
   pasting it into the report.
3f. Read budget and convergence (MANDATORY): a how-to/consult question ("how do I view the
   public IP?", "how do I call this API?") gets exactly ONE dispatch. Use the area's
   consult intent when it has one (`--intent consult` on public-ip-guide), otherwise a
   single triage call. Do NOT chain `triage -> verify -> ip-missing` and do NOT add
   `--scan-regions` for such a question: the chain buys no evidence, only minutes (measured
   159 s / 444 s / 118 s for three runs of the same how-to question, identical conclusion).
   Dispatching a second call for the same consult question is a defect, not thoroughness.
3g. A withheld layer must reach the conclusion (MANDATORY): when the tool withheld or could
   not run a layer it prints `WITHHELD-LEAD:`. The verdict you copy must keep that
   `not read:` segment - the unread layer belongs on the first line, not only in the body,
   because a reader of the conclusion alone would otherwise infer more than the run
   established.
3h. Answer surface (ABSOLUTE PROHIBITION - measured 2026-10-27): the delivered answer has
   exactly two parts - line 1 is the verdict line, everything after it is the customer's
   content. Nothing may precede the verdict line, and none of the following may appear
   anywhere in the answer, in any language:
   - process narration ("let me check the entry script first", "I will run the identity
     pre-check now", "the pipeline has run", "now let me look at the root-cause notes");
   - a tool/command inventory ("Executed checks" tables listing `python3 ...`,
     `scripts/areas/...`, exit codes, `STATUS: OK/DEGRADED/FAIL`);
   - internal markers or machine fields (`[EVIDENCE]`, `[FINDING]`, `[RISK]`,
     `[HUMAN STEP]`, `VERDICT-JSON`, `REPORT-LEAD`, `MUST-LEAD`, `DOC-CHECK`,
     `DOC-REF`), or a raw session id;
   - a rejected call shape's own error text (`usage: ...`, `the following arguments
     are required`, `<entry-script>.py: error:`): the dispatcher replaces it with
     one line naming the missing argument, so quote that line instead;
   - a raw 16-digit UID or an InvokeId (see 3e).
   The dispatcher already returns the answer material in that shape and in that size:
   its stdout opens with the verdict line, continues with the customer's content, and is
   capped at 8 lines / 600 characters of report body, plus the remedy block a refusal or
   a credential failure owes and the document citations. Everything it folded stays on
   stderr. Reuse that block as delivered; do not rebuild the report out of the raw
   execution log on stderr, and do not re-inflate it by pasting the log back in. If you
   must summarise which facts were read, use customer language ("read the security group
   ingress rules -> 0 rules"), not the command that produced them.
   Set `ECS_ANSWER_DETAIL=investigation` before the call when the reader asked to see the
   investigation itself: the same block then carries the per-read trace (up to 16 lines /
   1400 characters) instead of the one-line summary, and closes with one line naming which
   evidence sources this run actually printed (`What this answer rests on: …`) - it never
   names a source the run did not print, so a source missing there is a real gap. Any
   other value falls back to the short form and says so on stderr.
   Rationale: P-01b / Q-02c reruns (2026-10-27) had zero identifier leaks but still opened
   with a "let me check the entry script" narration above the verdict and carried an
   "Executed checks" table quoting `scripts/areas/...` and `STATUS: DEGRADED`; that is
   internal state presented as the customer's report.
4. Platform-policy facts need no read (MANDATORY): when the ticket's question is answerable
   by deterministic platform knowledge - bandwidth-to-throughput conversion (1 Mbps ~= 128
   KB/s; a measured 0.92 Mbps download on a 1 Mbps order IS the spec ceiling working as
   designed, state it as the confirmed conclusion), fixed-bandwidth vs pay-by-traffic
   behavior, SLA scope, burstable instance CPU/bandwidth credits, spec-family limits - the
   report MUST state that fact as a confirmed determination with the concrete numbers and
   then give the remediation (raise bandwidth / change charge type / request quota).
   A checklist or a hedged "maybe normal" WITHOUT such a determination is an incomplete
   report for these tickets. The same determination MUST take the verdict line itself
   (rule 3d form (b)) rather than leaving `unverified` there, and the deterministic
   lifecycle/commercial families count as rule-4 knowledge even though the account-side
   read is unavailable: a trial instance IS a pay-as-you-go instance whose free grant is
   only a deduction entitlement, so expiry continues metering with no auto-stop and no
   auto-release - only releasing the resource stops the charge; stopping an instance
   stops the compute meter but not the attached cloud disks, snapshots or the public IP
   it holds; a discount/eligibility ruling is decided by the order's validity window and
   by new-purchase-only scope, so an expired campaign cannot be re-priced in place and
   must be released and re-bought; arrears blocks new purchases until settled while it
   does not retroactively delete the resource.
4b. A rule-4 determination must carry its official source whenever this run found one
   (MANDATORY - copy, do not compose): the dispatcher runs a document leg on every
   dispatch and prints, inside the answer block, a line starting `Doc check: ` -
   `completed` (each cited page was compared against the live official body),
   `degraded` (part of the basis is weaker than a live match, and the header itself
   says which: a body could not be re-read online, or was not re-read at all because
   this run's read budget went to the higher-ranked citations first, so that citation
   rests on a dated snapshot; or a page has changed since it was last verified, so that
   citation is withheld rather than quoted), or `skipped` (this run has no citable
   document - which includes the case where documents are registered for this area but
   not one of them is about the question that was asked).
   Below that header it prints the adjudicated customer wording and the official URLs.
   Copy that block into the answer: its wording, its numbers, its URLs and the reason
   the header gives, unchanged. The quoted official wording stays in its original
   language - it is copied verbatim from the China-site page, and translating it would
   put a promise in the customer's report that no document makes.
   - Where the doc block and your own recollection of the rule disagree, the doc block
     wins. ABSOLUTE PROHIBITION: never publish a day count, amount, retention period,
     deadline or eligibility scope that the doc block does not carry, and never print a
     help-center URL that the block did not print. Recalled policy is exactly the
     surface this leg exists to replace - two official pages currently state the refund
     arrival window differently (about 2 business days vs 2-3), so a single remembered
     number is a promise no document makes.
   - When the leg holds a conflict it prints the pre-adjudicated range wording and both
     sources. Keep the range. Narrowing it to one figure, or picking the source that
     suits the customer's hope, is a defect even though both URLs are real.
   - When the header reads `degraded`, keep the reason it states with the citation: the
     customer is entitled to know which part of the basis was not re-verified live today,
     and a withheld citation must never be re-supplied from memory. When it reads
     `skipped`, state the determination as rule knowledge with no document behind it and
     do not manufacture a citation.
   - MANDATORY: when the internal record carries a `DOC-REF-SCOPE-LIMIT:` line for a
     citation, that line bounds what you may do with the citation. It is an instruction to
     you rather than customer text, so it stays out of the answer (rule 3h) - but treating
     it as decorative is a defect. Two shapes occur and both bind. A limit saying the page
     was adjudicated for a FACT but not for the ACT around it (a data-disk impact fact
     quoted from the replace-the-operating-system page, where this area owes no replacement
     procedure) means: state the fact, and route the act to the path the handoff table
     names. A limit saying only one section of a large page was adjudicated means: do not
     extend the citation to anything else on that page. ABSOLUTE PROHIBITION: never turn a
     scope-limited citation into procedure the limit excludes, and never widen it to cover
     the rest of its source page.
   - The `Doc check: ` header and the URLs are customer-facing content. `DOC-CHECK:` and
     `DOC-REF*:` lines are the internal record of the same leg and stay out of the
     answer (rule 3h).
