---
name: alibabacloud-ecs-high-frequency-issues
description: |
  Ticket-grade non-mutating ECS diagnosis: unreachable website/instance, slowness/crash, billing/renewal/arrears/refund/trial expiry, snapshot/image/spot charges, access blocked, login failure (password/key/RDP/SSH/VNC/Cloud Assistant), start-stop-reboot, disk mount/expand/IOPS, data recovery, SSL, bandwidth, DDoS/CC, intrusion, image lifecycle, ICP filing, cross-account transfer.
  Use when a customer describes an ECS problem in ticket language (ids may be missing), or asks ECS rules/policy only.
  Do NOT use for DR design, Cloud-Assistant-gated live diagnosis (alibabacloud-ecs-diagnose), invoices, non-ECS.
  Triggers: "unexpected or snapshot-size charges", "rule added still blocked", "RDP failure", "stuck stopping", "disk invisible after expand", "snapshot before C-drive expand", "snapshot rollback error", "upload entry missing", "where to see username/password", "RAM permission denied", "burstable CPU throttled", "snapshot cleanup", "trial expired: auto-stop? still billed?".
---

# alibabacloud-ecs-high-frequency-issues

Merged ECS support skill (55 areas, customer-symptom family). Each area keeps its
original full spec; this file is the router and the shared contract layer.

## Execution Principle (MANDATORY, applies to every area)
- MANDATORY ENTRY SCRIPT: every area answer MUST be produced by running
  `python3 scripts/ticket-support.py --area <area> -- <args>`. Never answer a
  matched area from general knowledge or by pasting the area reference, and never
  hand-craft the area's queries outside the entry script. If the script raises,
  report the real error and still deliver the area's degraded checklist.
- MANDATORY CONCLUSION: the delivered answer text itself MUST open with the
  `PRIMARY-CAUSE:` verdict line (rule 3d), carry read evidence, and close with the
  customer-side next step (manual / console); writing `outputs/*.md` never discharges
  this, and guest reads not run MUST be declared UNVERIFIED. ORDER: write every file
  (`outputs/`, `ran_scripts/`) and mark every todo completed BEFORE the block, then stop -
  the block is the LAST message of the run and no tool call may follow it. Delivery is not
  a todo item: never track it in the todo list, because a `todo_write` after the block
  forces one more turn, which becomes a wrap-up. Anything sent after the block (wrap-up,
  file list, summary, any language) becomes the reply and drops the verdict, so a correct
  block sent earlier still fails.
- MANDATORY CUSTOMER QUESTION: pass the customer's own words on every dispatch via
  `--customer-question "<verbatim question>"` after the `--`. The dispatcher consumes
  it and never forwards it to the area, so it is safe on all 55 areas. The document leg
  ranks the frozen official anchors in `references/doc-anchors.json` against exactly
  that text (through `scripts/_doc_refs.py`, no runtime search), so a dispatch without
  it cites nothing - not a smaller answer, no citation at all. Rule 4b then governs
  what the answer may promise from that citation.
- Query-only boundary by default: never create/modify/delete cloud resources
  unless the area is listed as GATED below and the customer explicitly confirms
  the exact action.
- ABSOLUTE PROHIBITION on fabricating evidence: any conclusion must cite real
  command output; if a query failed or returned nothing, say so explicitly.
  Claiming "verified/executed" without trace = violation.
- ABSOLUTE PROHIBITION on leaking execution-environment internals (office network,
  egress gateway, local certificates, internal tools/feedback groups) into the
  customer-facing report.
- Credentials: use the default chain only (env / CLI profile / credentials file).
  Never print or hardcode AK/SK. ABSOLUTE PROHIBITION on reading
  `~/.aliyun/config.json`, `~/.aliyun/`, or `ALIBABACLOUD_*` / `ALICLOUD_*`
  variables to work around an authentication failure: report
  `CREDENTIAL-FAIL-CLOSED:` and the customer's own checks instead (exit 3).

## Guest Consent and Credential Fail-Closed (MANDATORY, applies to every area)

**In-guest reads are OFF by default.** Cloud Assistant `RunCommand` executes inside the
customer's instance. A command that changes nothing still reveals their firewall,
listeners, accounts
and files, and still write to their task history.

- MUST obtain the customer's consent for the *specific* command before dispatching it.
  Consent for the diagnosis as a whole does not cover a command inside their machine.
- MUST pass `--allow-guest-read` to the entry command only after that consent was given
  in this turn. The dispatcher strips every guest-activation flag otherwise and prints
  `CONSENT-REQUIRED: <area> / refused flags`; the area's own `--confirm` token is a second
  gate on top of this one, never a substitute.
- MUST NOT re-run with `--allow-guest-read` on your own initiative. If consent is missing,
  name the exact command and ask in the answer, never skip silently; a generic "continue"
  reply is NOT consent. Declined or unanswered => tier UNVERIFIED, hand them the command.
- MUST NOT describe a layer as clean because its guest read did not run.

**Credential failure is fail-closed.** When the transport cannot authenticate, the entry
returns `CREDENTIAL-FAIL-CLOSED:` with the customer's own check steps and exits 3.

- ABSOLUTE PROHIBITION: never read `~/.aliyun/config.json`, `~/.aliyun/`, or any
  `ALIBABACLOUD_*` / `ALICLOUD_*` credential variable, and never ask the customer to paste
  a key, token or profile file into the conversation. `_guardrails.py` refuses to spawn a
  command that carries those paths or names.
- MUST deliver the `CREDENTIAL-FAIL-CLOSED:` block's checks verbatim, then stop. Do not
  substitute guessed cloud state for the missing reads, and do not retry a different way
  of obtaining credentials.
- MUST NOT claim "no issue found" when the evidence was unreadable. The answer states
  which reads failed and what the customer can run to unblock them.

**A named target that is not visible is its own outcome.** When the run reads the pinned
instance and the read returns it absent under the current credential and region
(`DescribeInstances` returned nothing for that id, `InvalidInstanceId`, or
`InvalidRegionId`), the absence is a confirmed determination, not an unverified gap: the
first line states `PRIMARY-CAUSE: ... (target-not-found)` with the absence as evidence,
the answer offers the readable candidate instances to choose from, and the entry exits 4.
Exit 4 is distinct from exit 3 (credential fail-closed) and from a clean diagnosis (exit 0);
a target absence never impersonates the credential-closed code.

## Action Authority (MANDATORY, applies to every area)

What this skill may do on the customer's behalf is fixed by
`references/action-classes.json` and explained in
[references/action-authority-matrix.md](references/action-authority-matrix.md). On any
conflict the JSON wins. Two hard rules:

- **High-risk actions are guidance only.** A restart, and anything that interrupts a
  running service, destroys or replaces data or a system disk, changes a paid spec that
  needs a restart, or cannot be undone, is NEVER executed for the customer. ABSOLUTE
  PROHIBITION on dispatching a guide-only action (RebootInstance, StopInstance,
  ReInitDisk, ReplaceSystemDisk, DeleteInstance, DeleteSnapshot, ModifyInstanceSpec,
  ModifyInstanceNetworkSpec, ReleaseEipAddress, RedeployInstance, InstallCloudAssistant,
  refund/unsubscribe). The dispatcher refuses it before any leg runs (exit 2) and the
  answer carries a guidance block: explain the effect, the prerequisites, and where the
  customer performs it themselves. Never name an internal switch in that block.
- **Configuration changes need per-operation consent and disclosure.** A consent-write
  action (for example CreateSnapshot) may run only after the customer agrees to that one
  operation in this turn, and the answer MUST state its effect and its cost (a snapshot
  bills by capacity used until deleted) and how it is undone. MANDATORY: one agreement
  authorises exactly one operation; never carry a prior agreement forward, and never
  claim the effect was achieved unless this run read it back.

`guest-config-change` (in-guest swap/sysctl/systemctl) and `security-group-write` are
`not-built`: ABSOLUTE PROHIBITION on implementing or dispatching them this round - that is
a capability project, not a gap fix. In-guest reads (`RunCommand`) still require the
per-command consent above even though the dispatched command only inspects the guest
and mutates nothing.

## Area Index (Module Index)

**Selecting an area from a Chinese question (MANDATORY).** The `Triggers:` on each area
card are English. When the customer's first question is Chinese, also match it against
[references/trigger-lexicon.json](references/trigger-lexicon.json): per-area Chinese
trigger terms measured over the same 37,750-ticket corpus, each admitted only when it
fires in at least 20 first questions and at most half of those belong to other areas.
It covers the 41 areas whose Chinese vocabulary is discriminative; the other 14 share
words with sibling areas and must be chosen by meaning, using the cross-area table in
`references/routing-table.json`. The lexicon only helps pick `--area`; it never
authorises a dispatch or a write, and a lexical match is a hint, not a confirmed cause.

**Routing a free question before the area is known.** Run
`python3 scripts/ticket-support.py --route-question "<customer question>"` to get a
`ROUTE-SUGGESTION:` block ranking candidate `--area` slugs from that lexicon. It is a
suggestion-only hint and NEVER dispatches; confirm the area by meaning, then run that area
normally with `--area`. With no lexical signal it prints `no lexical signal` (exit 1)
and you choose by meaning plus the cross-area table. Do not paste the suggestion
block into a customer answer.

**Boundary rules when two areas both look plausible.** Measured on a stratified entry-routing
benchmark (326 tickets, first informative customer turn): these rules put first-question area
selection at 84.0% on questions that carry enough information, +2.0pp over the same sample
without the last rule. Pick the ENTRY area, not the area the root cause will land in; when the
question cannot determine the area, ask one clarifying question instead of guessing.

Each rule below resolves a measured confusion:
1. "why am I still being charged", "I released it but the balance keeps dropping", "which resource costs this" -> billing-attribution-bill-check. Use arrears-trial-billing-stop ONLY when the question is about overdue payment stopping/releasing resources or a trial ending.
2. Any performance, utilisation, capacity or benchmark question -> resource-bottleneck, even when it mentions a panel, a disk or a website ("is this memory usage normal", "fio cannot reach the disk throughput limit", "too many auto-start services"). UNLESS the ask is to CHANGE a disk's category/performance level or to EXTEND capacity: "can this IO be raised" -> disk-pl-change-guide; "extend the disk" -> disk-expand-diagnosis.
3. Price, feasibility or billing-period questions about changing spec -> spec-change-purchase ONLY on money wording: price, refund, cost of the change, billing period. Whether a change is possible, how to perform it, or a change that is blocked or unavailable ("cannot upgrade in this region", "can I raise memory/CPU", "can this plan be upgraded", "why can't I change two at once") -> instance-modify-diagnosis.
4. Burstable/credit behaviour, CPU performance limits, hyper-threading support -> burstable-instance-guide, not instance-modify-diagnosis.
5. Port 8888, "bt.cn", Baota/BT panel wording -> bt-panel-diagnosis, even if the symptom is "cannot open the URL". UNLESS the object of the question is not the panel itself: "the panel does not show the extended disk capacity" -> disk-expand-diagnosis.
6. A named website/URL/API that cannot be reached, including "the instance cannot reach the internet" phrased as access failure -> web-inaccessible-slow. Use network-quality-bandwidth ONLY when the complaint is speed/latency/packet loss with the service still reachable, OR when the customer reports ping/traceroute to the instance itself failing or a regional network incident.
7. SSH specifically (port 22, key, sshd, "only my IP works") -> ssh-connection. Use access-block-layered ONLY when the customer names security-group rules, a firewall policy or an explicit block as the object of the question.
8. Windows remote desktop (mstsc, RDP, 3389) -> windows-rdp. Use remote-connection-entry ONLY when the connection method is not yet known.
9. OS version upgrade / replacing the operating system / image choice -> custom-image-lifecycle, not instance-modify-diagnosis. UNLESS the ask is about leftover files after an upgrade ("can I delete Windows.old") or about repartitioning/reinstalling only one volume: then the disk area owns it.
10. A cross-border or overseas endpoint that is slow while a same-region peer is fine -> cross-border-link-diagnosis, not network-quality-bandwidth.
11. Recovering a database's own data files, or database connectivity/availability -> db-on-ecs-diagnosis. Use data-recovery-assessment ONLY for generic file/disk loss.
12. A pending maintenance/operational event, or instance state questions -> instance-state-diagnosis. Use instance-start-stop-anomaly ONLY when a start/stop action itself failed.
13. A multi-product deployment quote or a request for a human/account manager -> service-escalation-guide, not spec-change-purchase.
14. Whether a disk keeps data when the instance fails, or how a disk attaches -> disk-attach-os-visibility, not data-recovery-assessment.
15. "Is there a short-term server" / which billing mode suits me -> billing-mode-selection, not preemptible-instance-guide.
16. A channel request that NAMES a topic ("human agent: ECS upgrade", "transfer me, the server expired") is routed by the TOPIC, never by the channel wording. service-escalation-guide only when the whole message carries no technical topic ("how do I reach a human", "after-sales service").

Entry command for every area (keep the `scripts/` prefix verbatim):
`python3 scripts/ticket-support.py --area <area> -- <args>`

Full spec for every area: `references/areas/<area>.md` (one card per area, named exactly
as the slug below). The mode shown is the area's default authority; the gated-action list
under the table governs confirmation for state-changing actions in every area it names,
including areas whose default mode is query-only.

**query-only areas (37):**
   `web-inaccessible-slow`, `renewal-pricing-discount`, `billing-attribution-bill-check`, `access-block-layered`,
   `expiry-release-retention`, `attack-blackhole-diagnosis`, `login-credential-repair`, `instance-state-diagnosis`,
   `arrears-trial-billing-stop`, `unsubscribe-refund`, `billing-mode-selection`, `console-channel-diagnosis`,
   `remote-connection-entry`, `public-ip-guide`, `bandwidth-modify-guide`, `instance-modify-diagnosis`,
   `spec-change-purchase`, `network-quality-bandwidth`, `ssh-connection`, `icp-filing-guide`, `data-recovery-assessment`,
   `intranet-egress`, `console-resource-lookup`, `cross-border-link-diagnosis`, `vpc-connectivity-check`,
   `instance-relocation-guide`, `sas-alert-vulnerability`, `disk-expand-diagnosis`, `unexpected-reboot-diagnosis`,
   `service-escalation-guide`, `stop-mode-billing-guide`, `smtp-block-diagnosis`, `ddh-capacity-guide`,
   `punishment-appeal-guide`, `preemptible-instance-guide`, `slb-backend-diagnosis`, `burstable-instance-guide`

**gated areas (18)** - state-changing actions require explicit customer confirmation:
   `resource-bottleneck`, `web-service-runtime-config`, `instance-start-stop-anomaly`,
   `bt-panel-diagnosis`, `snapshot-billing-cleanup`, `file-transfer-diagnosis`,
   `host-intrusion-cleanup`, `disk-attach-os-visibility`, `db-on-ecs-diagnosis`,
   `custom-image-lifecycle`, `windows-rdp`, `cloud-assistant-diagnosis`, `image-billing-cleanup`,
   `hbr-backup-diagnosis`, `ssl-cert-deployment`, `ram-policy-diagnosis`,
   `linux-permission-repair`, `disk-pl-change-guide`

Gated areas in this package: resource-bottleneck, web-service-runtime-config, instance-start-stop-anomaly, bt-panel-diagnosis, snapshot-billing-cleanup, file-transfer-diagnosis, host-intrusion-cleanup, disk-attach-os-visibility, db-on-ecs-diagnosis, custom-image-lifecycle, windows-rdp, cloud-assistant-diagnosis, image-billing-cleanup, hbr-backup-diagnosis, ssl-cert-deployment, ram-policy-diagnosis, linux-permission-repair, disk-pl-change-guide, access-block-layered, console-channel-diagnosis, disk-expand-diagnosis, intranet-egress, unexpected-reboot-diagnosis, web-inaccessible-slow. The gate covers state-changing actions ONLY: those MUST stop and ask for explicit customer confirmation (the area's confirmation flag: `--user-confirmed` / `--confirmation-scope`, or `--confirm` where the area defines it) before running; without confirmation, do not mutate anything. Read-style in-guest probes also travel through Cloud Assistant RunCommand. They are NOT query-only from the customer's side: the command still executes inside their machine and leaves a task record there. ABSOLUTE PROHIBITION: never dispatch one without the customer's consent for that exact command in this turn. Ask first, then pass `--allow-guest-read` to the entry command. Without it the dispatcher strips the area's guest flags, prints `CONSENT-REQUIRED:` naming the command it refused, and the cloud-side (Describe/Get) reads still run — so a missing consent degrades the answer instead of blocking it.

When the customer issue matches an area, run that area entry command and follow the
area spec in `references/areas/<area>.md`. Do not mix areas in one report.

## Trigger Conditions
See description (customer wording kept verbatim from the merged intake analysis).

## Input Parameters
Per area: region id / instance id / uid as required by the area spec; if missing, ask the customer once, never guess.

### Parameter provenance (MANDATORY)
Every parameter that reaches the report carries its source, in one of three states:
- **customer-provided**: quote the value as given.
- **defaulted**: the area fell back to its documented default. When the call carried no region
  flag the dispatcher declares it on the internal stream already in customer words
  ("Region: cn-hangzhou (the area default, not supplied by you)") - copy that wording. Never
  present it as the customer's region, and never write the machine key behind it.
- **derived**: read from the environment at run time (account UID from `sts GetCallerIdentity`,
  resource attributes from `Describe*`). Name the source, e.g. "account ****6705, derived from
  the current credentials".

Stating a defaulted or derived value as if the customer had supplied it is a report defect.

### Confirmation flag names (MANDATORY)
`--allow-guest-read` is the central consent switch only; each area also has its own switch and
the two are not interchangeable. Names in use: `--confirm` (some areas require the value to echo
the target id verbatim), `--user-confirmed`, `--user-confirmation`, `--customer-confirmed`,
`--confirmed`, `--confirmation`, `--confirmation-scope`, `--approval-quote`,
`--acknowledge-approval`, `--confirm-cost`, `--snapshot-confirmed`, `--confirm-irreversible`,
`--guest-confirmed-by`. Areas that define more than one switch (console-channel-diagnosis,
db-on-ecs-diagnosis, disk-expand-diagnosis, intranet-egress, snapshot-billing-cleanup,
ssh-connection, ssl-cert-deployment, unexpected-reboot-diagnosis) need all of their switches;
passing only `--allow-guest-read` leaves the guest layer UNVERIFIED. Read the switch name and
value form from the area spec's Parameters section before running.

## Execution Flow
1. Classify the symptom into one area via the table above. **Customer self-diagnosis never routes (MANDATORY)**: a customer's speculated cause ("suspected disk IO error / maybe a virus / must be the network") is NOT an area-selection input - route by the objective reproducible phenomenon instead (e.g. "VNC freezes" -> console-channel). When an objective channel/startup/availability symptom coexists with a customer guess, the symptom's own area takes precedence; customers mistaking a symptom for the cause is the most common misrouting pattern in real tickets. **Compound billing intent lands on the mechanism area (MANDATORY)**: when a stop/downtime state coexists with a billing question ("instance is stopped yet keeps charging", "want to stop it AND stop the charges"), route to the mechanism area (stop-mode-billing-guide) - never to the generic stop-charges area (arrears-trial-billing-stop); the generic area is only for a pure "how do I stop all billing" with no instance-state element, because the mechanism area supersedes it and the generic answer silently omits the stop-mode prerequisites (which resources keep charging after StopInstance, NoCharges eligibility).
2. Run the area entry command in query-only mode.
3. Gated area: stop, present the exact write action, wait for explicit `--confirm`.
4. Deliver the report in the area spec's format. Delivery IS the answer, not a tracked task: never put it in a todo list (close the list at the last read instead), and let the answer block be the last message of the run - no tool call and no message may follow it.
5. Which steps that scenario runs, and what its answer is allowed to claim, follows the flow
   class bound to that `(area, scenario)` pair in
   [diagnosis-flow-templates](references/diagnosis-flow-templates.md). That file is a design
   contract for report shape; it adds no call, no gate and no parameter of its own.
6. **Cross-area hand-off is decided by the table, not by improvisation (MANDATORY).** The
   dispatcher reads `references/routing-table.json`, matches the customer's own words (passed
   with `--customer-question`) and appends a three-line `Continue with:` block naming the area,
   what that area settles, and what happens next. The agent half - the exact switch,
   `--area <target>` plus its sub-command - is printed on the run log as `HANDOFF-SWITCH:` and
   must never be pasted into the customer answer, because a ticket customer cannot run this
   script. ABSOLUTE PROHIBITION: do not invent another hand-off target, another sub-command, or a
   skill name that is not in that table; do not re-state the block in your own words; and do not
   add a hand-off when the dispatcher withheld it (the run log says `HANDOFF: not evaluated (...)`
   with the reason - credential failure, missing toolchain, or a rejected argument shape). The
   measured ticket basis for every row, and the admission test
   `ecs-suite-v2/tools/check_routing_table.py` re-derives, are in
   [references/routing-detail.md](references/routing-detail.md).

## Observability
Every CLI/API call attaches the User-Agent template
`AlibabaCloud-Agent-Skills/{skill}/{session-id}`, where session-id is a 32-character hex string
generated once per run and reused across all calls in that run (each area's `_cli.py` under
scripts/areas/). `{skill}` is pinned to the published package name
`alibabacloud-ecs-high-frequency-issues` and a `skill-version/{version}` segment derived from
`references/manifest.json` is appended on the wire, giving
`AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<session-id> skill-version/<version>`.
The runtime document leg (`scripts/_doc_refs.py`) carries this same real-name, versioned,
per-session User-Agent when it re-reads an official page.

## Boundary (Do NOT use for)
- Do NOT use for instance health or login failures (alibabacloud-ecs-diagnose), outbound, or disk IO ceiling / provisioned IOPS.
- Do NOT use for VPC route tables, EIP or cross-border link quality (alibabacloud-ecs-vpc-publicnetwork-troubleshoot); nor disk capacity, inode exhaustion, instance state, disk IO, network path, billing, ICP filing, security cleanup or extension installs (alibabacloud-ecs-install-extension).
- Do NOT use for services failing inside a running instance or guest middleware faults (alibabacloud-ecs-linux-os-troubleshooting), SSH/RDP login, disk capacity or inode cleanup, disk IO performance, or partition expansion.

### Published skills named above (catalogue-verified 2026-11-11)

Each name was resolved against the published skill catalogue, so a handoff that names it
reaches a skill the customer can actually install. What each one owns:
[references/published-handoff-skills.md](references/published-handoff-skills.md).

## Degraded output when the customer's resources are not visible (MANDATORY)

Empty, NotFound or Forbidden under the current credentials does NOT mean the problem does not exist: tickets are
resolved by the support engineer's checklist, not by the account view. Never stop at "query failed" and never ask the
customer to restate the issue. Still deliver, for the stated symptom: (1) the layered check order the customer can run
in their own account, with the exact aliyun CLI command shapes from the area reference; (2) the ranked high-frequency
root causes for that symptom drawn from real tickets; (3) which finding confirms which cause, and the escalation
condition when all checks pass. MANDATORY: the worked root-cause list and the full wording of this rule are in
[references/degraded-output-playbook.md](references/degraded-output-playbook.md). Never change customer resources,
never fabricate readings, never claim a specific cause without evidence - rank probabilities and say what evidence
would confirm each. The ban is symmetric over NEGATIVE exclusions: "not a quota problem", "not an inventory issue",
"unrelated to billing" are claims too, and a factor may be eliminated ONLY by a read that covers it. Factors living in
internal backends invisible to this leg (risk-control verdict, quota approval records, off-ticket conversations) MUST
NEVER be excluded nor confirmed - split them into separate conditional determinations that each name the
customer-visible channel they belong to ("if the block reason is a quota ceiling -> the offline business/SA channel;
if it is a violation flag -> the appeal path"). Ruling out an invisible factor is a defect even when the remaining
direction is correct. Probe results describe ONLY the resources visible under the current credentials: if the
customer's own domain/instance is not among them, never assert it is healthy, deployed or reachable - mark it
UNVERIFIED and put it in the layered checklist instead.

## Out-of-scope handling (Discovery leg, MANDATORY when no area matches)
1. First try the area table above. ABSOLUTE PROHIBITION: do NOT run this leg for
   symptoms that match any area, and never use it to escape a failed diagnosis.
2. When no area matched, the exit is decided by the shape of the question - by this
   rule, not by picking from a menu. Measured routing discipline: offering "search the
   help docs" as one candidate among others makes it get chosen ~86% of the time,
   including for symptoms an area owns, so it must never appear in a candidate list.
   2a. **Knowledge/policy consult** (the customer asks what the rule IS - billing or
       refund scope, expiry and retention, snapshot/backup charging, charge-type
       conversion, campaign eligibility, a spec-family or quota limit - and no fault is
       being diagnosed): dispatch the area that owns that TOPIC FAMILY, per the area
       table, and pass the customer's question verbatim through the dispatcher's own
       `--customer-question` argument:

       `python3 scripts/ticket-support.py --area <area> --no-guest-baseline -- --customer-question "<the customer's question, verbatim>" <that area's own consult mode>`

       `--customer-question` is consumed by the dispatcher and never forwarded to the
       area, so it is safe on every area, including those that accept no free-text
       argument of their own. The document leg then ranks the frozen official anchors
       against that question and prints the `Doc check: ` block (rule 4b), which is the
       answer's source. One dispatch only (rule 3f). Without a question the leg cites
       nothing at all - there is nothing to rank against - so omitting the argument is
       not a shortcut, it silently disables the citation.
       ABSOLUTE PROHIBITION: never answer an anchored policy question from memory, and
       never run your own web/help-center search to find a page - the anchor set is
       frozen at build time precisely so the cited URL is one that was verified against
       the official body, and a URL found at answer time was not.
   2b. **Capability gap** (the symptom belongs to another product or to work this
       skill does not do): the hand-off ladder alone decides whether another skill
       is ever named, and it runs local first, then the catalogue:
       `python3 scripts/ticket-support.py --skill-handoff-check --target area:<slug>|<published-code> --keywords "<generic symptom words>"`
       Rungs: an `area:<slug>` target is a check this package already ships, so stay
       here and name it in words (the token is internal, never deliver it);
       otherwise use what is already installed; otherwise offer the catalogue's
       answer as a card of at most 2 candidates, downloading staying the customer's
       decision; no match or no answer degrades - say so, keep answering in scope.
       ABSOLUTE PROHIBITION: never name a skill the ladder did not return - the
       codes inherited from the single-skill packages this one was assembled from
       answer 404 against the catalogue, so such a sentence reads as an answer and
       sends the customer to a skill they cannot install.
       MANDATORY: the query carries generic symptom words only - no id, IP, domain,
       path or credential - because that query leaves this machine over the network.
3. ABSOLUTE PROHIBITION on installing anything yourself: never download, write or
   execute external skill code - installing is a platform action the customer takes
   after their own confirmation.
4. When neither 2a nor 2b applies - a knowledge question whose topic family no area
   owns - say that plainly and mark the determination UNVERIFIED. Do not fill the gap
   with a recalled rule, a guessed URL, or a confident-sounding number: an answer that
   cannot be anchored is worse than a named limit, because the customer acts on it.
## Incomplete customer info never blocks the executable checks (MANDATORY ORDER)
1. Run the dispatcher pipeline first, always. ABSOLUTE PROHIBITION: never reply to a
   diagnosable symptom by requesting information only - not "please provide the exact
   error", not "please confirm the instance ID", before executing the pipeline once.
2. When the deciding detail is missing (error string, time window, affected scope), do
   not gate on it: execute every leg that is computable from what the customer already
   said - identity pre-check, region default cn-hangzhou, instance/disk/bill listings,
   security-group and DNS resolution, blackhole and arrears state - and label each
   result CONFIRMED / EXCLUDED / UNKNOWN with its evidence.
3. Ask targeted follow-up questions only as a supplement appended to that partial
   report, never as a substitute for running it.

## Final report spine and ranking law (ABSOLUTE)

Every rule below binds every delivered report. MANDATORY: read
[references/report-spine-detail.md](references/report-spine-detail.md) before composing a
report - full wording, ticket evidence and worked verdict-line/citation examples.

1. Read trace: one line per fact actually read this session, in customer language ("read
   the security group ingress rules -> 0 rules"), never a command, script path, exit code
   or internal status word; copy the tool's facts, not its plumbing. Zero read facts with
   no explicit reason is a defect. ABSOLUTE PROHIBITION: never paste `scripts/...`, a
   `python3 ...` line, `STATUS:`, `DEGRADED`, `VERDICT-JSON`, `DOC-CHECK:`, `DOC-REF`,
   `[EVIDENCE]`, `[FINDING]` or a session id into the answer. `Doc check: ` is the
   customer-facing form of the document leg; the `DOC-*` lines are its internal record.
2. Ranking law: an anomaly a check READ (service stopped, no listener, DROP rule,
   PasswordAuthentication no, stale fstab line, disk full, agent offline, instance
   Stopped, missing SG rule) IS the #1 confirmed root cause, stated as the conclusion.
   Hypotheses without a read rank strictly below every read-confirmed finding; naming an
   unverified cause as #1 while a read-verified anomaly sits unranked is a defect.
3. When in-guest reads could not run (agent offline, Forbidden, cross-account
   invisibility): say so in the first line, list each skipped read with its reason, mark
   the layer UNVERIFIED, deliver the customer-side checklist. Never dress an unmeasured
   guess up as a confirmed finding.
3b. The routed area never limits the read set: `df -h`, `free -h`, `cat /etc/fstab`,
   `findmnt`, `sshd -T` (plus `iptables -S` for any reachability/blocking symptom and the
   EIP/association read for any public-IP symptom) MUST be obtained whenever the ticket
   targets one running instance whose Cloud Assistant agent answers - even when the chosen
   area does not emit them: use its guest-read option or call the instance-state area for
   the same instance id. The dispatcher collects this baseline for every `--area` call
   carrying both `--instance-id` and `--region-id` and prints it above the area result
   under `tier-1 guest baseline`; the area delivers those non-mutating reads only with the
   explicit `--guest-baseline` opt-in. Cite them; a `[WARN]` baseline means the tier-1
   facts are absent and the report must say so. **Cloud-side-only round exception:** only
   when the customer or contract explicitly forbids in-guest commands, call the dispatcher
   with `--no-guest-baseline` and pass neither `--guest-command` nor `--guest-baseline` to
   any area; declare the guest tier UNVERIFIED per rule 3 and list the readings you would
   have taken. Dispatching silently, or describing an unexecuted read as done, is a
   contract violation - worse than an honest UNVERIFIED line.
3c. A `MUST-LEAD:` line from any area script is binding report order (ABSOLUTE
   PROHIBITION): computed from guest read-back (a system filesystem >=95%, `MemAvailable`
   <=10% of total, `PasswordAuthentication no` in the effective sshd config), never a
   guess, so that anomaly MUST be the first line of the conclusion with its measured
   numbers verbatim. Never rank a security-group, DNS, upstream-service or fail2ban
   hypothesis above it, never conclude `UNDETERMINED`/`need more information` while it is
   unaddressed, never omit it. An unexecuted read must never be described as done.
3d. The answer MUST open with one machine-parseable verdict line as its first non-empty
   line - no heading, table, preamble or rule above it: `PRIMARY-CAUSE: <the single leading cause> | EVIDENCE: <the read
   that confirms it>` or, when nothing was confirmed, `PRIMARY-CAUSE: unverified | not read: <each layer this run did
   not read, with its reason in plain words>`. This binds the delivered answer text: writing a report file never discharges it, and a run whose reads did not land
   still owes this line plus the customer-side checklist in that answer. The grader parses this line verbatim: a cause no
   executed check confirms, or a missing `MUST-LEAD:` anomaly, is a defect even if the body is right. Never present a
   speculative hypothesis as confirmed. Copy, do not compose: the dispatcher (`scripts/ticket-support.py`) prints it as
   the FIRST line of its answer block - copy it verbatim and add NO prefix of your own (never `REPORT-LEAD:` or any other
   label). Three changes are permitted and each is MANDATORY when its condition holds: (a) replace `unverified` with a
   cause whose confirming read appears in the tool output; (b) when rule 4 applies, replace `unverified` with that
   determination, citing the rule instead of a read and appending `; official page <url>` whenever this run's `Doc check:
   ` block printed a URL - copied verbatim from that block, never recalled or assembled from a product name; when the
   block reads `Doc check: skipped`, omit the segment and never supply a URL to fill the gap; (c) when the run's reads
   returned the pinned target ABSENT under the current credential and region (DescribeInstances returned nothing,
   InvalidInstanceId, InvalidRegionId), that absence is a read outcome and MUST take the line as a target-not-found
   determination, without speculating another-account / released / wrong-region absent a further read. Forms (b) and (c)
   are mandatory: leaving `unverified` there states less than the run established. If the dispatcher printed no verdict
   line, compose it from the reads and rule-4 knowledge you hold. Never rewrite the line to drop a mandated anomaly. The
   layered-access area appends `EXCLUDED by live read: <layers>`; all were read and allow the flow: never name them as
   root cause anywhere in the report, and never re-rank a HIT read above against them.
3e. Identifier hygiene (ABSOLUTE PROHIBITION): never print a raw 16-digit account UID, a
   Cloud Assistant InvokeId (`t-...`) or a 32-hex session id. Both boundaries already mask
   them (dispatcher on the child stream, each area's CLI layer on its own stdout/stderr, so
   a directly invoked area is covered) as `****6705`, `t-****1m9s`, `****8299`. Copy the
   masked form verbatim; never reconstruct the original or ask the customer for it. If a
   trace id is genuinely needed, point at the internal verdict record in the run log instead.
3f. Read budget: a how-to/consult question gets exactly ONE dispatch - the area's consult
   intent when it has one (`--intent consult` on public-ip-guide), otherwise a single
   triage call. Never chain `triage -> verify -> ip-missing` and never add `--scan-regions`
   for such a question; a second call is a defect, not thoroughness.
3g. A withheld layer must reach the conclusion: when the tool prints `WITHHELD-LEAD:`, the
   verdict you copy must keep that `not read:` segment on the first line, not only in the
   body, so a reader of the conclusion alone cannot infer more than the run established.
3h. Answer surface (ABSOLUTE PROHIBITION): exactly two parts - line 1 the verdict line,
   everything after it the customer's content. Nothing may precede it, no message may follow it, and none of these may appear in the
   answer, in any language: process narration ("let me check the entry script first", "the pipeline has run",
   "Done.", "Diagnosis complete") or a saved-file list (`outputs/`, `ran_scripts/`); a compliance recital - never
   say what you did NOT do (no change made, no write API, no in-guest command, no credential read), nor name an unpassed flag, a credential path or the script's defaults/routing/exit codes; a
   tool/command inventory ("Executed checks" tables listing `python3 ...`, `scripts/areas/...`, exit codes, `STATUS:
   OK/DEGRADED/FAIL`); internal markers or machine fields (`[EVIDENCE]`, `[FINDING]`, `[RISK]`, `[HUMAN STEP]`,
   `VERDICT-JSON`, `REPORT-LEAD`, `MUST-LEAD`, `DOC-CHECK`, `DOC-REF`, `ACTION-CLASS`, `SOURCES:`, `INSTANCE-OFFER`, `[WARN]`, the bare word `DEGRADED` or its lowercase telling of the same fact, an area slug such as `web-inaccessible-slow`, an internal status/attribution code such as `NO_PUBLIC_PATH` / `NO-EVIDENCE` / `EXCLUDED`, or a raw API `field=value` dump) or a raw session id - and the same words are banned in their translated shapes: a heading or label that renders one of these keys in the reader's own language counts as that key, because the grader reads it as the same marker, so head a part for what the reader gets from it instead; a rejected call shape's own
   error text (`usage: ...`, `the following arguments are required`, `<entry-script>.py: error:`) - quote the
   dispatcher's one line naming the missing argument instead; a raw UID or InvokeId (3e). The dispatcher already returns
   the answer in that shape and size: stdout opens with the verdict line and is capped at 8 lines / 600 characters of
   report body, plus the remedy block a refusal or credential failure owes and the document citations; everything folded
   stays in the internal run-log file the dispatcher names. Reuse that block as delivered - do not rebuild the report from the raw log or re-inflate it by
   pasting the log back in, and never tee, redirect or copy that log into `outputs/` or `ran_scripts/` nor read it back
   into the conversation: a saved run record is this block plus your own account of what you ran, naming the check and its
   target rather than the command line (no entry-script path, no interpreter, no flags). Every artifact you save is held to this same vocabulary, the area spec's `STATUS:` / `NEXT_ACTION:` report scaffolding included, its file name included (never an area slug); the saved report is the block verbatim and the run record adds only the check and its target - no section about the run's own conduct, and no mechanism narration (`hash-match`, `anchor`, `relevance floor`, parameter or flag names). A fenced block, a table or a template inside a saved file is deliverable text under the same rule: no package path, interpreter, option name or raw error body anywhere in it, and no line inside it announcing that a report or record was saved. Neither the ticket text nor the instructions you were given are source text for the answer - a machinery word handed to you as an instruction is honoured in the reader's words, never quoted back. Set `ECS_ANSWER_DETAIL=investigation` when the reader asked to see the investigation: the
   block then carries the per-read trace (up to 16 lines / 1400 characters) and closes with `What this answer rests on:
   …`, naming only sources this run actually printed, so a source missing there is a real gap. Any other value falls back
   to the short form.
4. Platform-policy facts need no read: when deterministic platform knowledge answers the
   question - bandwidth-to-throughput conversion (1 Mbps ~= 128 KB/s; a measured 0.92 Mbps
   download on a 1 Mbps order IS the spec ceiling working as designed), fixed-bandwidth vs
   pay-by-traffic behavior, SLA scope, burstable CPU/bandwidth credits, spec-family limits
   - state it as a confirmed determination with the concrete numbers, then the remediation
   (raise bandwidth / change charge type / request quota). A checklist or a hedged "maybe
   normal" without that determination is incomplete, and the determination MUST take the
   verdict line (3d form (b)). The lifecycle/commercial families are rule-4 knowledge even
   when the account-side read is unavailable: a trial instance IS pay-as-you-go whose free
   grant is only a deduction entitlement, so expiry keeps metering with no auto-stop and no
   auto-release - only releasing the resource stops the charge; stopping an instance stops
   the compute meter but not attached cloud disks, snapshots or the public IP it holds; a
   discount/eligibility ruling turns on the order's validity window and new-purchase-only
   scope, so an expired campaign cannot be re-priced in place and must be released and
   re-bought; arrears blocks new purchases until settled but does not retroactively delete
   the resource.
4b. A rule-4 determination must carry its official source whenever this run found one
   (copy, do not compose): the dispatcher prints a `Doc check: ` line in the answer block - `completed` (each cited page
   compared against the live official body), `degraded` (part of the basis is weaker than a live match, and the header
   says which: not re-read online, not re-read because the budget went to higher-ranked citations so it rests on a dated
   snapshot, or changed since verification so the citation is withheld), or `skipped` (no citable document, including
   when documents are registered for the area but none is about the question asked). Below it are the adjudicated
   customer wording and the official URLs. Copy that block unchanged - wording, numbers, URLs and the header's reason.
   The quoted official wording stays in its original language; translating it would put a promise in the report that no
   document makes. The doc block beats your recollection: never publish a day count, amount, retention period, deadline
   or eligibility scope it does not carry, and never print a help-center URL it did not print. When it holds a conflict
   it prints the pre-adjudicated range and both sources - keep the range; narrowing it to one figure is a defect even
   though both URLs are real. On `degraded` keep the stated reason with the citation and never re-supply a withheld
   citation from memory; on `skipped` state the determination as rule knowledge and manufacture no citation. A
   `DOC-REF-SCOPE-LIMIT:` line in the internal record bounds what you may do with that citation: it is an instruction to
   you, so it stays out of the answer (3h), but treating it as decorative is a defect. Both shapes bind - adjudicated for
   a FACT but not the ACT around it means state the fact and route the act to the handoff table's path; only one section
   of a large page adjudicated means do not extend the citation to the rest of that page. Never turn a scope-limited
   citation into procedure the limit excludes or widen it to its whole source page. `Doc check: ` and the URLs are
   customer-facing; `DOC-CHECK:` and `DOC-REF*:` stay out of the answer.

## Area root-cause intel (curated from resolved tickets)

MANDATORY: before composing the report for the routed area, read its entry in
[references/area-root-cause-intel.md](references/area-root-cause-intel.md). Those
entries are ranking rules adjudicated against resolved tickets: where an entry names
a PRIMARY cause it leads the conclusion and the verdict line (rules 2 / 3c / 3d), and
where it records a layer EXCLUDED by a read that layer must not be named as root cause.
The ticket ids and batch labels in that file are maintainer provenance and never
appear in a customer answer (rule 3h).

## Important Notes
- Relative paths only; all assets live in this package.
- All network/API/subprocess calls carry timeouts.
