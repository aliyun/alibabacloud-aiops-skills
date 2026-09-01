# Windows Online Diagnostic Execution Workflow

This file carries the complete execution workflow for Windows ECS **online diagnostics**, defining all execution details after entering online diagnostics.

**User scenario**: Windows instance has successfully booted into the operating system, and the user reports a fault phenomenon or requests troubleshooting or status check of a Windows instance. Coverage includes:

- Network issues: ping, DNS, DHCP, firewall, SMB
- RDP/Remote Desktop: connection failure, authentication, black screen, sluggishness
- Storage/disk, system activation, Windows Update, performance issues
- User accounts/permissions, drivers, application crashes, security/certificates/TLS, scheduled tasks
- Vague descriptions such as "check the system" or "the system has issues"

This file is self-contained: the problem domain routing table, fallback mechanism, and PowerShell collection script rules are all defined inline in this file.

---

## Table of Contents

- General Execution Constraints
  - User Presentation Rules
  - Collection Channel Rules
  - Collection Fallback Chain
- Diagnostic Execution Workflow
  - Problem Understanding
  - Path Planning
  - Step-by-Step Execution
  - Debug Event Log Deep-Dive Mechanism (Universal Fallback)
  - Causal Chain Analysis
  - Evidence Review
  - Fix Plan
- Online Problem Domain Routing Table
  - 1. Startup Issues (Management Side)
  - 2. Crash/Hang or Lifecycle Abnormality
  - 3. Usage Issues
  - 4. Performance Issues
  - 5. Instance Configuration Not Taking Effect
  - 6. Management Channel Issues
  - 7. Other Issues
- Fallback Mechanism (Sole Authority)
- Output Format Templates
  - Evidence Review Template
  - Causal Chain Example
  - Diagnostic Conclusion Output Template
  - Platform-Side Root Cause Output Template
  - Check Item Summary Template
- PowerShell Collection Script Rules
  - 0. Pre-Execution Self-Check Checklist
  - 1. Cmdlet Selection
  - 2. Output Style
  - 3. Variable Naming to Avoid Built-in Identifiers
  - 4. GUI Dialog Command Handling
  - 5. Suppress Progress Stream for Remote Execution
  - 6. Pitfall of Colon After Variable Name in String Interpolation
  - 7. foreach Statement Cannot Directly Connect to Pipeline
  - 8. cmd Tool Error Handling Using $LASTEXITCODE
  - 9. Version String Parsing
  - 10. UTF-8 BOM Compatibility
  - 11. User Command Display Gating (MUST Validate Before Display)
  - 12. Command Transmission Mode (Direct Execution Channel)
  - 13. Remote Execution Channel Rules
  - High-Frequency Pitfalls

## General Execution Constraints

### User Presentation Rules

**Language first**: per SKILL.md principle 11, every user-facing sentence is written in the language the user is using. All phrasing templates and output templates in this file are given in English only because the skill files must stay ASCII -- they define structure and meaning, not literal output. When the user speaks another language (e.g., Chinese), translate the phrasing into that language (e.g., "Result: Normal / Abnormal" becomes a Chinese normal/abnormal phrasing); never present the English template text verbatim to a non-English user.

The following phrasing templates correspond one-to-one with internal diagnostic stages/actions; when presenting progress, diagnostic paths, current steps, and other information to the user, MUST use the natural language phrasing from this table, and MUST NOT present the corresponding internal marker text.

**Diagnostic stage recommended phrasing templates** (user-facing, unified style):

When loading domain diagnostic files, express as "Checking + that domain's diagnostic function" (using the domain's diagnostic function in natural language description, without mentioning file names), e.g., networking-dns -> "Checking DNS configuration", rdp-service -> "Checking Remote Desktop service configuration"; when multiple files from the same domain are checked in parallel, merge into one overall description. Non-trivial stages/tags refer to the table below:

| Internal Stage / Action | User-Facing Phrasing (Example) |
|------|------|
| Event log pre-diagnosis | "Collecting and preliminarily analyzing key alerts in event logs" |
| Platform-side triage | "Checking platform-side configuration and events (public network entry, bandwidth, security group rules, maintenance events) to rule out factors outside the operating system" |
| Platform-side root cause | "The cause lies outside the operating system (platform configuration / platform event); remediation needs to be done on the console or via API" |
| Debug log deep-dive | "Guiding to enable component debug logs, waiting to collect more detailed diagnostic information after reproduction" |
| Skip a step (fallback) | "The above checks found no issues, continuing with additional check items" |
| Speculative diagnosis annotation | "Did not precisely match a preset scenario; will diagnose along the closest path, may need to adjust based on intermediate results" |
| Dynamic planning annotation | "No preset scenario matched; will dynamically compose a diagnostic path based on the phenomenon" |
| Direct root cause | "Found an issue that directly caused this fault" |
| Contributing root cause | "Found an aggravating / indirectly impacting issue" |
| Unrelated (other findings) | "Found an item not directly related to this fault but recommended for attention" |
| Critical severity | "Severe issue, will affect functional availability" |
| Warning severity | "Issue requiring attention, may affect stability" |
| Info severity | "Informational item for reference" |

**Note**: The above table is for reference only; phrasing may be adjusted as appropriate when used. The principle is to express "what is being done", without presenting internal identifiers like "calling X.md / Step Y".

### Collection Channel Rules

Before executing any data collection, MUST first follow the PowerShell Collection Script Rules section below in this file based on the current collection channel, then write/call collection according to its rules:

- **Direct execution channel** (PowerShell command execution on local instance) -> PowerShell Collection Script Rules section below, Section 12 Command Transmission Mode (Direct Execution Channel)
- **Remote execution channel** (PowerShell command execution via `aliyun ecs run-command` on remote instance) -> PowerShell Collection Script Rules section below, Section 13 Remote Execution Channel Rules + [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md)

**Pre-execution self-check (MUST)**:

- **Direct execution channel**: After writing the script and **before** executing, MUST scan the script text item by item against the "Pre-Execution Self-Check Checklist" in the PowerShell Collection Script Rules section below; fix any matched signals before executing
- **Remote execution channel**: Same self-check as direct execution channel, PLUS verify: (1) script does not reference local files on the agent machine, (2) script does not require interactive input, (3) script output stays small -- Cloud Assistant truncates oversized output (see [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section Output Size Management)

The value of this step is to catch script errors before execution: PowerShell execution failures not only waste a round-trip, but the error output can easily be mistaken for a real abnormality of the target system, leading diagnostic conclusions astray.

### Collection Fallback Chain

When the PowerShell command channel is unavailable (channel-level failures), MUST switch collection means level by level according to the fallback chain below.

**Fallback chain by mode (MUST degrade level by level in order)**:

- **Local mode**: Command line (PowerShell direct execution via `powershell.exe`) -> display commands for user manual execution
- **Remote mode**: Remote command line (`aliyun ecs run-command`) -> display commands for user manual execution

**Fallback determination strategy**:

- **Channel-layer failure** (Cloud Assistant unreachable, network error, instance not found, Cloud Assistant agent not running) -> Enter fallback: degrade to next level
- **RAM authorization failure is NOT a channel-layer failure and never enters this fallback chain**: an `AccessDenied` / `Forbidden.RAM` / `Forbidden` error means the CLI identity lacks a RAM Action, and no other API, channel, or manual-execution path can substitute for a permission the identity does not hold -- probing other APIs to find one that works hides the authorization gap from the user. Route it exclusively to the Authorization Flow on AccessDenied declared with this skill's RAM permissions: state the missing Action, request the grant, END the turn. This applies to prerequisite gate calls (e.g. `describe-instances`) and to every later call (`run-command`, polling, monitor-data) alike
- **Script-layer failure** (cmdlet not found, permission denied, path not found, syntax error with non-zero exit code and clear error output) -> This is a script issue, not a channel issue; fix the script and retry on the same channel
- **Timeout failure** (command execution exceeded timeout) -> Increase timeout and retry once; if still times out, break script into smaller chunks or fallback to next level

**User manual execution rules**: When the PowerShell command channel is unavailable, display the commands to the user for manual execution, and after obtaining the user's manual execution results, continue the diagnostic workflow.

**Collection script merging principle**: After entering the fallback flow, MUST merge multiple related collection items in the current diagnostic stage into one script output that can be executed as a whole for the user as much as possible, reducing the number of manual executions. When merging, maintain clear separator markers between each collection item's output (such as comment line `# --- <item-name> ---`), for easy segment-by-segment parsing after pasting back. Only split into multiple outputs when there are strong dependencies between collection items (subsequent commands need to be dynamically determined based on prior results).

**User command display gating (mandatory)**: Commands output for user manual execution MUST be validated item by item against the User Command Display Gate rules in the PowerShell Collection Script Rules section below before display (pure ASCII, placeholder compliance, no local path dependency, can be copied and executed as a whole); fix any non-compliant item before displaying. Pure ASCII is a hard requirement: the user's terminal encoding environment is uncontrollable (GBK/UTF-8), and non-ASCII characters are prone to garbled text after copy-paste, which may cause PowerShell parsing failure.

---

## Diagnostic Execution Workflow

### Problem Understanding

1. Extract core phenomena: Collect error codes, prompt messages, command outputs, abnormal screenshots, and other observed facts from the user's text descriptions and attached images, uniformly incorporating them as equally prioritized inputs into the "core phenomena" set; during path planning, use this for problem domain matching
2. **When information is insufficient, MUST first ask the user for clarification** (specific phenomena, error prompts, operation timing, etc.), and only enter the path planning stage after collecting sufficient information
3. **Target instance identity is part of "sufficient information"** (remote execution channel): if the user has not given an instance ID / region, ask for it BEFORE the first cloud command and end the turn until answered -- the gate defined in SKILL.md Section Remote Execution Prerequisites. Enumerating instances to guess the target, or adopting an ID surfaced by environment variables / local files / history, is prohibited: the only legitimate sources are the user's own words or a candidate list the user explicitly confirmed

> All subsequent analysis MUST revolve around the "core phenomena"; items in the "core phenomena" set MUST be explicitly referenced in the "evidence" field of the final diagnostic conclusion, not just used for internal reasoning.

### Path Planning

1. **Problem classification (sole classification point in the entire workflow, secondary classification outside this step is prohibited)**: Use the Online Problem Domain Routing Table section below, combine the problem's core phenomena and ambiguity resolution conclusions to determine the problem domain and unified diagnostic sequence; classification results are only used as internal context (one primary problem domain, at most two parallel candidate domains when necessary), not presented to the user; fuzzy matching -> diagnostic path annotated as "speculative diagnosis". If subsequent evidence (such as event log pre-diagnosis) indicates classification needs adjustment, MUST return to this step for re-classification, and adjusted results MUST still fall within the problem domains defined in the routing table
2. **Platform-side triage (remote execution channel only)**: Immediately after classification, before entering the domain sequence, run the L2 platform triage defined in [platform-evidence.md](references/online/platform-evidence.md) Section L2: consult the per-domain mapping using the L1 platform context snapshot captured at channel prerequisites, execute at most 1-2 additional read-only platform calls, and state the triage outcome to the user (what platform-side factor was checked and what it ruled in or out). If the platform facts fully explain all user symptoms under that file's exit gates, conclude a platform-side root cause there and skip the GuestOS deep-dive (reporting any incidental in-guest anomalies as separate findings); otherwise proceed with the planned domain sequence. In direct execution channel mode, skip this step entirely
3. **Event log pre-diagnosis**:
   - Collect key event logs within the user-reported time period (System, Application, Security)
   - Filter Error/Critical level events, extract Event ID and source
   - Refine the priority of diagnostic steps within the classified domain based on event log characteristics (step selection basis), without changing the classification result
   - Note: Only collection and pre-analysis, no specific diagnostic steps executed
4. **Dynamic planning** (only when classification does not match any problem domain, or the classified sequence completes without finding a root cause):
   - First load [system-health-check.md](references/online/system-health-check.md) to execute global baseline health check, then combine the user's problem description + baseline check results to select relevant problem domain files from the routing table and fallback mechanism sections below
   - Compose a diagnostic sequence, and explain to the user: "This is a dynamically planned diagnostic path, not a preset scenario"; layered fallback rules see the Fallback Mechanism section below
5. Output: Ordered list of problem domain files (typically 2-5, avoid too many) + planning rationale

### Step-by-Step Execution

Load and execute problem domain files one by one according to the diagnostic sequence.

**Single problem domain file execution rules**:
1. **Select relevant step subset**: Filter based on the "step selection guidance" in the problem domain file, combined with the "core phenomena" set + event log pre-diagnosis results; when the problem domain file does not provide guidance or matching is uncertain, conservatively include; missed items are covered by the "subset fallback rule"
2. **Strict step-by-step execution**: Each step must complete the full flow of "data collection -> analysis and determination -> normal/abnormal conclusion" before proceeding to the next step, and MUST present a brief Check Item Summary to the user before proceeding to the next step; bulk collection of data for multiple steps followed by centralized analysis is prohibited
   - Each abnormal determination MUST have corresponding collected data as evidence
   - Each step MUST give a clear normal/abnormal dichotomous conclusion
   - Discovered abnormalities MUST be linked to specific root causes
   - **Baseline batching exception (remote channel only)**: the 7 steps of [system-health-check.md](references/online/system-health-check.md) are read-only with no inter-step data dependencies; over the remote execution channel they MAY be merged into 2-3 `run-command` invocations (separated by `# --- Step N ---` segment markers in the output) to save round trips. Per-step analysis discipline above still applies unchanged -- each step gets its own determination and Check Item Summary from its output segment, and total output MUST stay within Cloud Assistant size limits (split further if it would not). Domain diagnostic sequences (which contain conditional steps) are NOT covered by this exception
3. **Subset fallback rule**: If the selected steps find no issues, continue executing all remaining steps in that problem domain file
4. **Escalation trigger rule**: When all Steps in the domain are executed (including subset fallback) without finding a root cause, first go through rule 6's Debug log deep-dive fallback; if not applicable or still no clues after deep-dive, then enter [system-health-check.md](references/online/system-health-check.md) global baseline health check
5. **Cross-reference handling**:
   - When encountering a cross-reference -> prioritize the jump target, then return to the main sequence after completion
   - When the same problem domain file is referenced multiple times, it only needs to be executed once; subsequent references directly reuse existing results
6. **Debug log deep-dive fallback**: When all Steps in the domain are executed (including subset fallback) without confirming a root cause, **before** escalating to global baseline health check, MUST first evaluate applicability per the "Debug event log deep-dive mechanism" below; if applicable, guide the user to enable debug logs and reproduce, then collect and re-analyze; if not applicable, user refuses, or still no clues after deep-dive, then enter the escalation flow
7. **Platform-side evidence (remote execution channel only)**: When the remote execution channel is active, platform-side data is governed by [platform-evidence.md](references/online/platform-evidence.md) at three levels: the **L1 context snapshot** is captured once at channel prerequisites and reused throughout; **L2 platform triage** runs as Path Planning step 2 before the domain sequence (and may conclude a platform-side root cause under that file's exit gates); during the sequence itself, use only **L3 cross-validation** -- for the matched problem domain group, fetch platform-side data (instance/disk monitoring metrics, system events, console screenshot) as auxiliary evidence that corroborates or bounds in-instance findings but never replaces intra-instance collection and never changes domain classification. Label the evidence source (platform-side vs in-instance) in the Evidence Review. If mid-sequence in-instance evidence points to a platform-level cause not caught by triage, apply the same L2 exit gates before concluding. In direct execution channel mode, skip this rule entirely

> Collection commands MUST use the commands given in the problem domain file's "Diagnostic Steps"; only placeholder replacement and parameter adaptation to the current environment are allowed; generating collection scripts based solely on step descriptions is prohibited.

**Sequence control logic**:
- **Early termination**: Discovered root cause fully explains all user symptoms -> terminate subsequent problem domain files
- **Continue execution**: Only partially explains symptoms -> continue executing subsequent problem domain files
- **Direction correction**: During execution, the problem direction is found to differ from initial planning -> return to path planning stage, re-plan based on new clues

### Debug Event Log Deep-Dive Mechanism (Universal Fallback)

Regular log channels (System / Application / Operational / Admin) only record key events; many components' Debug/Analytic channels are disabled by default; after the normal diagnostic path is completed, the fault scene may not have left any logs available for determination. In this case, enabling debug logs for the target component, reproducing the fault once, then collecting and re-analyzing often yields details invisible on the regular path. This mechanism applies to **all problem domains** and is the universal deep-dive method between per-domain diagnosis and global baseline check.

**Trigger conditions**: All Steps in the current problem domain have been executed (including subset fallback) without confirming a root cause, and the fault can be actively reproduced by the user (or is a periodic natural recurrence).

**Execution flow**:

1. **Select debug channel**: Prioritize using debug channels already defined in the current problem domain file (such as [rdp-session-disconnect.md](references/online/rdp-session-disconnect.md) Step 5's three RDP Debug channel groups); when the domain file does not define them, select the corresponding component's Debug/Analytic ETW channel based on the fault domain (e.g., for the network domain, determine channels by network component providers); skip this mechanism when specific channels cannot be determined
2. **Enable and reproduce**: MUST attach the complete enable command (`wevtutil sl <channel> /e:true /q:true`), execution instructions (admin PowerShell), and reproduction guidance to the user in the same response; execute after obtaining user consent; after enabling, ask the user to reproduce the fault once and record the reproduction time. Enabling debug logs is a system state modification operation; MUST first obtain user permission, and MUST NOT execute automatically
3. **Re-collect and analyze**: Narrow the window based on the user's reproduction time, collect Error/Warning level events from the debug channel, and re-determine according to the domain file's analysis approach; when new clues appear, return to "Step-by-Step Execution" to continue diagnosis; the evidence for the determination conclusion MUST reference debug channel events
4. **Cleanup and close**: After diagnosis is complete (regardless of whether a conclusion was reached), MUST attach the corresponding close command (`/e:false`) to avoid debug logs occupying disk long-term; user refuses or does not respond -> skip this mechanism, note in the conclusion "Debug logs were not enabled; deep-level details not covered"

**Inapplicable scenarios**: Fault cannot be reproduced and is not periodic; offline diagnostics (system disk mount/offline environment has no runtime log channels); current domain has no known debug channels and cannot be reasonably inferred.

### Causal Chain Analysis

1. Aggregate findings from all problem domain files
2. Build a causal chain (distinguishing direct causes and indirect causes)
3. Rank by relevance to the user's problem: **relation (Direct > Contributing > Unrelated) x severity (Critical > Warning > Info) dual-dimension sorting**; Unrelated issues are listed separately as "other findings", not mixed into the main fix plan
4. When no findings: execute global baseline health check [system-health-check.md](references/online/system-health-check.md), route to relevant domain files for in-depth diagnosis based on baseline scan results; still no findings -> truthfully inform the user, provide recommended diagnostic directions
5. **Causal edge evidence triple (mandatory)**: Every edge in the causal chain ("A caused B") must carry all three of: (1) the collection command plus the output excerpt it produced, (2) the documented judgment it matched (the "Abnormal: X -> Root cause: Y" pattern in the problem domain file), and (3) a time-window check -- the timestamps of the cause-side evidence must precede or overlap the symptom's occurrence window (event log times, service start time, config last-write time, etc.). An edge missing any of the three MUST be downgraded to a speculative hypothesis in the Evidence Review and never presented as a conclusion
6. **Co-occurrence is not causation (red line)**: Linking an observed anomaly A to the user's symptom B merely because they co-occurred in the same session, or because they sound topically related, is prohibited. A causal claim requires all of: temporal precedence or overlap, the same object on both sides (same adapter / service / disk / account / task), and a causal mechanism documented in the reference files. When any of these cannot be established, report A and B as separate observations and state what additional data would connect them
7. **Differential diagnosis checklist**: Before asserting a root cause, list the alternative candidate causes for the symptom (drawn from the problem domain file's sub-scenario routing and related domains) that were examined, and the specific collected data that excluded each. A root cause asserted without its ruled-out alternatives is incomplete -- return to collection for the unexamined candidates instead of asserting with confidence

### Evidence Review

Before presenting the diagnostic conclusion and fix plan, perform a consolidated review of the entire diagnostic process. Individual step summaries show per-check results, but the causal chain analysis may introduce inferences that go beyond what the data directly proves. This review catches those gaps before they reach the user -- a conclusion that sounds authoritative but rests on an unsupported assumption is worse than an honest "I don't have enough data to confirm this yet".

**Relationship to Check Item Summary**: The per-step Check Item Summary is a progress checkpoint -- it shows what each single step collected and concluded, helping the user track diagnostic progress in real time. The Evidence Review is a cross-step verification gate -- it consolidates all judgments from the causal chain and verifies each one against collected data before any fix is proposed. They serve different purposes and are not redundant: one tracks progress during diagnosis, the other validates conclusions before action.

**Review process**:

1. **Enumerate collection actions**: List every data collection command executed during this session, with a brief summary of what was returned (key values, counts, status). This gives both you and the user a complete picture of what was actually checked, and makes it easy to spot collection gaps.

2. **Map evidence to judgments**: For each conclusion in the causal chain, cite the specific data point that supports it:
   - A registry value, event log entry, service status, configuration item, or command output that directly confirms the finding -> labeled **Confirmed**
   - If the conclusion is an inference (e.g., "likely caused by X because Y and Z were observed, but X itself was not directly measured") -> labeled **Speculative**, with an explanation of what was observed and what additional data would confirm it
   - When platform-side data was fetched (remote execution channel, per Step-by-Step Execution rule 7), cross-check related judgments against it and label each evidence item's source (**platform-side** vs **in-instance**); a genuine discrepancy between the two views is itself a diagnostic clue and MUST be presented honestly
   - For each causal edge ("A caused B"), verify the **evidence triple**: the collection command + output excerpt, the matched documented judgment, and time-window consistency (cause-side timestamps precede or overlap the symptom window). An edge missing any element keeps only its directly-observed endpoints as Confirmed findings -- the causal link itself is downgraded to Speculative
   - **Co-occurrence is not causation**: two abnormalities observed in the same session remain separate findings until temporal, same-object, and documented-mechanism linkage is shown; do not merge them into one story without that linkage
   - Include the **differential diagnosis**: for each asserted root cause, list the alternative candidates examined and the data that excluded each; alternatives not yet examined are collection gaps, not grounds for confidence

3. **Identify unsupported judgments**: Any judgment that cannot cite specific collected data must not be presented as a conclusion. Instead, downgrade it to a **hypothesis pending verification** and:
   - Label it as "Hypothesis -- inference based on: {what was observed}"
   - List the missing data items needed to confirm or refute it
   - Provide the specific collection commands the user can run to obtain that data
   - Present these separately from evidence-backed conclusions so the user can clearly distinguish between proven findings and unverified hypotheses

4. **Present to user**: Output the evidence review using the template below before entering the fix plan. This gives the user the opportunity to spot gaps, correct misunderstandings, or provide additional context before fixes are proposed.

> The goal is transparency: the user should be able to trace every conclusion back to a specific piece of collected data, and clearly see where inference fills the gaps. When the user can see the evidence trail, they can make informed decisions about whether to proceed with a fix or collect more data first.

### Fix Plan

**Trigger conditions (mandatory)**:
- Once "Evidence Review" is completed, the fix plan MUST be presented in the same response -- the full plan, risk notes, AND the confirmation question together. MUST NOT stop after only describing the root cause in text
- "No delay" means plan PRESENTATION must not be deferred: do not say "let me check with you first... I will generate the script later", and do not wait for the user to ask before providing the plan. It does NOT relax the confirmation gate of output rule 3 -- asking the confirmation question immediately is mandatory, and executing the fix still requires the user's explicit confirmation reply in a later turn
- Fix scripts MUST be **directly copyable and executable complete PowerShell one-click scripts** -- prepared for the turn after confirmation, not for immediate dispatch in the plan turn

**Fix reference loading contract (mandatory)**:
- Before outputting a fix plan, MUST first load the fix reference for the problem domain where the root cause is located: when the problem domain file's "Fix recommendations" section is a single-line pointer, MUST load the corresponding fix file under `references/online/fixes/`; when it is an inline fix section, directly output based on that section's content. **This load MUST happen within the same turn as the fix plan output**: if the fix reference was only read earlier in the session (e.g. during path planning or early domain loading), re-read it NOW before presenting the plan -- by the time the root cause is confirmed, an early read sits deep in the context, and the confirmation gate and exact command blocks it carries must be fresh at the decision point before any fix wording is produced
- When the root cause comes from a cross-domain parameterized reference, MUST load the fix reference of the referenced party (fix authority), and the referencing party does not duplicate fix content
- Outputting fix scripts from memory without loading fix references is prohibited; when the fix reference has no fix matching the root cause, truthfully inform the user and seek their opinion, and self-created fix commands are prohibited

**Output rules**:
1. Each root cause provides an executable fix script, MUST include verification method and expected result
2. Present in priority order
3. **Display complete fix content to the user, wait for explicit confirmation -- automatically executing any fix command is prohibited. After presenting the plan (including risk notes and confirmation request), END the current turn; execution may start only after the user's explicit confirmation reply in a later turn -- presenting the plan and executing the fix in the same turn is prohibited. The user's original "please fix / troubleshoot and repair" request is NOT confirmation (see SKILL.md Principle 6); do not rationalize same-turn execution with phrasings like "proceeding since the repair was explicitly requested" or "approved by the task directive". The plan message MUST end with a confirmation question (e.g. "Shall I proceed with this fix?"), and the same turn MUST NOT write the fix script, send the fix command, or bundle "save and run" steps -- a turn containing both a plan and any fix action violates this rule no matter what authorization wording it uses**
4. Same-issue aggregation: multiple modifications for the same root cause are merged into one script
5. Different-issue separation: fixes for different root causes are strictly separated, confirmed one by one
6. Operations involving system modifications MUST annotate risk notes
7. **Multi-option fix presentation**: When a root cause has multiple fix options, MUST present all and annotate "applicable conditions", sorted by risk from low to high (primary -> alternative), and let the user choose which to execute
8. **Post-execution fix summary (mandatory)**: After a fix is executed and verified, the summary presented to the user MUST be a self-contained record of the whole troubleshooting run, containing: (a) the key diagnostic/collection commands executed, each quoted verbatim by its command name (e.g. `Get-NetTCPConnection -LocalPort 443 -State Listen`, `Get-NetFirewallRule -Direction Inbound`) together with a one-line finding each; (b) the executed fix command quoted verbatim -- the full statement including the cmdlet name (e.g. `New-NetFirewallRule -DisplayName ... -Action Allow ...`), NOT only the created object's name or its parameter values; (c) the verification result; (d) the rollback command. A purely prose description ("added an inbound allow rule for 443") without the concrete command text is insufficient
9. **Fix impact standard fields (required)**: Each fix plan's risk notes section MUST include the following three items:
   - **Session impact**: Whether it disconnects existing TCP/RDP sessions; if no impact, explicitly annotate "No impact on existing sessions"
   - **Persistence scope**: "Survives reboot" / "Current session only" / "Written to registry"
   - **Rollback command**: A one-line copyable reversible operation

**Turn-boundary examples** (how the confirmation gate looks in practice):

Bad -- plan and execution in one turn (prohibited, even with authorization wording):

```
Fix plan (approved by the task directive "identify the cause and fix it"):
- Delete the blocking WFP filter {GUID} ...
- Risk: minimal ... Rollback: ...
[then, same turn] Saving the fix script and running it: <run-command call>
```

Good -- present the plan, ask, and stop; execute only after the user replies:

```
Fix plan:
- Delete the blocking WFP filter {GUID} ...
- Risk: minimal ... Rollback: ...
Shall I proceed with this fix?
[END OF TURN -- no fix script written, no command sent]
(user replies: yes, proceed)
[next turn] Write and send the fix command, poll, verify
```

**High-risk operation constraints**:
- **Conservative modification**: Modifying system configurations (firewall, registry, service parameters, etc.) MUST only add or modify target items; wholesale overwriting of existing configurations is prohibited
- **Session impact reminder**: Operations that may affect currently active sessions, such as restarting services or modifying network configurations, MUST remind the user of potential impacts
- **Back up critical configurations first**: Before modifying the registry or core system configurations, MUST recommend the user back up relevant items first
- **Caution with sensitive objects**: When operating on system permissions, credentials, certificates, and other sensitive objects, MUST indicate permission impacts and irreversible risks

**Platform-side root cause handling**:

When the root cause is platform-side (per the L2 platform triage exit gates in [platform-evidence.md](references/online/platform-evidence.md)), the fix plan differs from GuestOS root causes in three ways:

1. **No GuestOS fix script**: the remediation happens outside the instance (associate an EIP / allocate public bandwidth, adjust a security-group rule, handle a platform event, etc.). Present it as concrete console/API guidance the user can act on -- this skill never executes platform write operations itself
2. **Verification**: state the observable platform state the user should confirm afterwards (e.g., "outbound bandwidth > 0 and public IP shown in instance detail"), plus any in-guest re-check command worth running once the platform change is in place
3. **Incidental in-guest anomalies**: configuration anomalies already observed inside the guest (e.g., DHCP disabled on an adapter, a stale static route) are listed separately with their own fix plan and confirmation request -- present them as "found during diagnosis, independent of the platform root cause; fix is optional". They MUST NOT be silently dropped just because the primary root cause lies elsewhere

---

## Online Problem Domain Routing Table

Problem classification in online mode MUST be based on this table.

**Classification criterion (sole rigid constraint)**: All problems within a problem domain MUST be diagnosable using **the same unified diagnostic sequence**. Domains are the organizational unit of diagnostic sequences; sub-scenarios are branches within a sequence.

**Grouping boundary criterion (whether operations can complete)**: Operations can complete but slowly (slow boot, slow shutdown, overall sluggishness) -> Performance issue group; Operations cannot complete or system is unresponsive (crash, Hang/Frozen, stuck shutdown) -> Crash/Hang or lifecycle abnormality group.

### 1. Startup Issues (Management Side)

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Instance stuck in "Starting" state | `GuestOS.UnexpectedlySlowStarting` | Management-side boundary determination (non-GuestOS primary cause): standardized image determination -> ISO download/ISO stage logs | Stuck at Starting, ISO stage timeout |

> **Why "Running" and "cannot boot" are not contradictory**: console instance status reflects the virtualization-layer lifecycle, not the operating system. "Running" only means the instance has at least *begun attempting* to boot the OS; underlying hardware or software faults, system misconfiguration, or file corruption can all stop the GuestOS from booting while the platform status remains Running, which is why users report "cannot boot / cannot connect / business down" instead of a status anomaly. In this situation the console VNC output is the direct evidence of where boot stopped. Conversely, an instance remaining in "Starting" for an abnormally long time indicates a platform-side startup anomaly (non-GuestOS primary cause), handled per the row above.

### 2. Crash/Hang or Lifecycle Abnormality

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| System crash (BSOD) | `GuestOS.Crash` | Crash event query and crash configuration diagnosis, dump collection: [system-crash.md](references/online/system-crash.md) (BugCheck crash event query -> Crash Dump configuration diagnosis -> generated dump collection and crash platform analysis; BugCheck Code points to driver -> [cloud-driver.md](references/online/cloud-driver.md)) | BugCheck BSOD, auto-restart after crash (system has recovered to running) |
| System Hang (frozen) | `GuestOS.Hang` | Online only does historical Hang event query and configuration check (reuse [system-crash.md](references/online/system-crash.md)); when instance is currently still Frozen, guide user to manually trigger NMI core collection per offline scenario ([crash-hang.md](references/offline/crash-hang.md)) | Dead screen, no response (recovered after forced restart / still Frozen) |
| GuestOS shutdown or restart abnormality | `GuestOS.SystemShutdownFailed` | Cloud Assistant delivery chain check (guest-shutdown log) -> ACPI shutdown event (User32/1074) -> VNC status confirmation -> ClearPageFileAtShutdown and update-in-progress check; performance timing breakdown within instance reuses [performance-lifecycle.md](references/online/performance-lifecycle.md), management channel component check reuses [system-management.md](references/online/system-management.md) | Stuck shutdown (cannot complete), stuck in "Shutting down", abnormal auto-restart |

> Crash / Hang scenarios on the online side only do historical event query and information collection, with no real-time analysis capability; NMI core on-site collection when instance is currently still Frozen (user manual operation) and in-depth analysis of inability to boot or repeated BSOD after crash / Hang are outside this online capability boundary.

### 3. Usage Issues

#### Login and Remote Access

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Cannot connect to instance via RDP | `GuestOS.RDPConnectingFailed` | Port reachability (3389) -> [rdp-service.md](references/online/rdp-service.md) -> [rdp-auth.md](references/online/rdp-auth.md) -> [rdp-certificate.md](references/online/rdp-certificate.md) -> [rdp-licensing.md](references/online/rdp-licensing.md); session disconnect during use specialized -> [rdp-session-disconnect.md](references/online/rdp-session-disconnect.md) | Connection timeout, refused, authentication failure, certificate warning, RDS licensing error, connection crash, session disconnect during use |
| Cannot connect to instance via VNC | `GuestOS.VNCLoginFailed` | [vnc-login-failed.md](references/online/vnc-login-failed.md): VNC output check -> memory 100% render failure determination -> GPU/bare-metal spec determination | VNC black screen, white screen disconnect, no response |

**Session-Layer Stage Pre-Probe** (stage definitions in SKILL.md "Boot/Session Stage Determination"): for session-layer symptoms only -- black screen / logon failure sub-scenarios of `GuestOS.VNCLoginFailed`, `GuestOS.DesktopAppAbnormal`, and `GuestOS.RDPConnectingFailed` -- run this real-time probe BEFORE entering the domain file to locate P3/P4/P5 (do not run it for network/performance/storage symptoms; it is routing noise there):

```powershell
$ErrorActionPreference = 'Stop'
# --- Section 1: session-critical processes ---
try {
    'winlogon', 'csrss', 'explorer', 'LogonUI', 'dwm' | ForEach-Object {
        $p = Get-Process -Name $_ -ErrorAction SilentlyContinue
        Write-Host ('{0}={1}' -f $_, ($(if ($p) { $p.Count } else { 0 })))
    }
} catch { Write-Host ('ERROR s1 proc: ' + $_.Exception.Message) }

# --- Section 2: recent logon success (4624) -> P5 reached ---
try {
    $l = Get-WinEvent -LogName Security -MaxEvents 500 -ErrorAction Stop |
        Where-Object { $_.Id -eq 4624 } | Select-Object -First 3 TimeCreated, Id
    if ($l) { $l | Format-List } else { Write-Host 'NO-4624' }
} catch { Write-Host ('ERROR s2 logon: ' + $_.Exception.Message) }

# --- Section 3: service start failures -> P3 ---
try {
    Get-WinEvent -LogName System -MaxEvents 300 -ErrorAction Stop |
        Where-Object { @(7000, 7001, 7023, 7026) -contains $_.Id } |
        Select-Object -First 10 TimeCreated, Id, ProviderName | Format-List
} catch { Write-Host ('ERROR s3 svc: ' + $_.Exception.Message) }
```

Probe semantics: winlogon/csrss absent -> P3; LogonUI/dwm abnormal (with 4624 absent) -> P4; 4624 present but explorer absent -> P5. Stage -> online domain mapping: P3 -> [system-management.md](references/online/system-management.md) (management channel / service chain); P4 -> [vnc-login-failed.md](references/online/vnc-login-failed.md) / [rdp-session-disconnect.md](references/online/rdp-session-disconnect.md); P5 -> [desktop-shell.md](references/online/desktop-shell.md) / [cloud-vminit.md](references/online/cloud-vminit.md).

#### Network Connectivity

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Cannot connect to network from inside instance | `GuestOS.InsideNetworkAccessFailed` | [networking-tcpip.md](references/online/networking-tcpip.md) (Step 6 raw ping error-text triage) -> [networking-firewall.md](references/online/networking-firewall.md) (Steps 3-5 config + Step 7 WFP) -> [networking-dns.md](references/online/networking-dns.md) -> [networking-dhcp.md](references/online/networking-dhcp.md) -> [cloud-metaserver.md](references/online/cloud-metaserver.md) | No internet access, some external targets unreachable, intermittent disconnection, ping failure, DNS resolution failure, 169.254 address, metadata unreachable, NIC red X, firewall blocking specific ports, general failure |
| Cannot connect to instance business service from outside | `GuestOS.OutsideNetworkAccessFailed` | Port listening check (netstat) -> firewall rules -> business service status | Business port telnet failure, website inaccessible |
| Shared folder (SMB) access failure | `GuestOS.SMBAccessFailed` | [storage-smb.md](references/online/storage-smb.md) -> [networking-firewall.md](references/online/networking-firewall.md) (port 445) | Share access denied, DFS failure, network discovery failure |

#### Disk and Storage

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Disk partition table, partition, and file system corruption or not as expected | `GuestOS.CorruptDiskStorage` | [storage-disk.md](references/online/storage-disk.md) -> [storage-hardware.md](references/online/storage-hardware.md) -> chkdsk/fsutil/ACL check | Disk not visible, offline, file system corruption, data inaccessible |
| Disk mount or unmount failure | `GuestOS.AttachOrDetachDiskFailed` | Driver version (viostor known bug, [cloud-driver.md](references/online/cloud-driver.md)) -> Device Manager disk controller and storage events ([storage-hardware.md](references/online/storage-hardware.md): rescan / Kernel-PnP Event 225 unmount occupancy) -> [device-driver.md](references/online/device-driver.md) | Not visible after online mount, unmount failure still visible, 2008 requires manual rescan |
| Data disk incorrectly reset | `GuestOS.IncorrectDiskResetting` | viostor version determination (<58017 known bug, [cloud-driver.md](references/online/cloud-driver.md)) -> user operation restoration confirmation -> storage event recheck ([storage-hardware.md](references/online/storage-hardware.md)) -> driver upgrade recommendation | Reset wrong drive letter |
| Backup failure (VSS) | `GuestOS.VSSBackupFailed` | [storage-vss.md](references/online/storage-vss.md) -> backup software events | VSS error, snapshot failure, restore point abnormality |

#### System Maintenance and Licensing

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Instance not properly activated | `GuestOS.SystemActivateFailed` | [system-activation.md](references/online/system-activation.md) -> KMS reachability ([cloud-metaserver.md](references/online/cloud-metaserver.md)/firewall) -> SPP events/Tokens.dat | Unactivated watermark, activation failure |
| Instance update abnormality | `GuestOS.SystemUpdateFailed` | [system-update.md](references/online/system-update.md) -> CBS log and component store error redirect to [system-cbs.md](references/online/system-cbs.md) -> update server reachability | Download/install failure, BSOD after update |
| IIS/.NET/Windows feature installation failure | `GuestOS.SystemFeatureInstallFailed` | [system-cbs.md](references/online/system-cbs.md) (component service and pending status -> CBS/DISM log error -> feature installation status -> component store health) | IIS and other role installation failure, .NET installation or enable failure, DISM feature enable error 0x800f0xxx |
| Instance internal time abnormality | `GuestOS.UnexpectedSystemTime` | [system-time.md](references/online/system-time.md) -> metadata time source ([cloud-metaserver.md](references/online/cloud-metaserver.md)) | Inaccurate time, time jump, timezone error |

#### Identity and Encryption

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Identity and access abnormality | `GuestOS.IdentityAccessFailed` | [identity-account.md](references/online/identity-account.md) -> [identity-permission.md](references/online/identity-permission.md) -> [identity-ad.md](references/online/identity-ad.md) -> [identity-auth.md](references/online/identity-auth.md) -> [identity-user-profiles.md](references/online/identity-user-profiles.md) | Account lockout, domain login failure, trust relationship failure, Kerberos/NTLM authentication abnormality, permission denied, temporary profile loading |
| BitLocker encryption lockout (online branch) | `GuestOS.BitLockerLocked` | [security-bitlocker.md](references/online/security-bitlocker.md) | Recovery key needed, recovery mode popup while system running |

#### Security and Device

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Device and driver abnormality | `GuestOS.DeviceDriverAbnormal` | [device-driver.md](references/online/device-driver.md) -> [cloud-driver.md](references/online/cloud-driver.md) -> [storage-hardware.md](references/online/storage-hardware.md) | Yellow exclamation mark, driver installation failure, NIC disappeared, device unavailable after migration |
| Program hijacked or unable to start (security) | `GuestOS.MalwareOrIFEOHijack` | [security-malware.md](references/online/security-malware.md) | No response on double-click, file not found |
| HTTPS/TLS certificate error | `GuestOS.TLSCertificateError` | [security-certificates.md](references/online/security-certificates.md) | HTTPS failure, incomplete certificate chain |
| Desktop and application abnormality | `GuestOS.DesktopAppAbnormal` | [desktop-shell.md](references/online/desktop-shell.md) -> [desktop-app.md](references/online/desktop-app.md) -> [desktop-printing.md](references/online/desktop-printing.md) | Black screen with no desktop after login, application startup failure, print failure |

### 4. Performance Issues

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Abnormally high CPU usage | `GuestOS.CPUUtilizationTooMuch` | PowerShell collection of CPU usage trend -> Top-N process identification -> [performance-slow.md](references/online/performance-slow.md) (power plan/BCD limitation/mitigation strategy) | CPU maxed out, process sluggishness |
| Abnormally high memory usage (OOM) | `GuestOS.OutOfMemory` | PowerShell Top-N memory-consuming process identification -> memory exhaustion event (Event 2004) -> page file and hardware reserved memory check | Memory maxed out, process killed |
| Network packet loss | `GuestOS.NetworkPacketDrop` | Packet loss direction determination ([networking-tcpip.md](references/online/networking-tcpip.md) Step 10 interface counter before/after comparison: increment before/after reproduction to determine send/receive direction) -> CIPU fragmentation limit -> CPU maxed out/core binding -> NIC filter driver (Step 9 MTU/RSS config + Step 2 third-party protocol binding) -> if no results [networking-firewall.md](references/online/networking-firewall.md) Step 7 WFP real event location | Unstable connection, request loss |
| High network retransmission rate | `GuestOS.NetworkRetransmissionTooMuch` | Retransmission metric collection -> peer/link quality -> TCP configuration and congestion | Massive retransmission |
| High network latency | `GuestOS.NetworkPacketIOLatencyTooHigh` | RTT baseline comparison -> link/routing -> NIC driver and interrupt | Business timeout, network sluggishness |
| Network performance not meeting expectations | `GuestOS.UnexpectedlyNetworkIOPerformance` | Instance spec network SLA comparison -> BPS/PPS measurement -> driver version ([cloud-driver.md](references/online/cloud-driver.md)) | Bandwidth not meeting SLA, slow download |
| Abnormally high disk IOPS | `GuestOS.DiskIOPSTooHigh` | Disk metric collection -> process-level IO identification -> fragmentation/index service | IO spike, system slowdown |
| Disk read/write performance not meeting expectations | `GuestOS.UnexpectedlyDiskIOPerformance` | Disk type/IOPS/throughput SLA comparison -> [storage-hardware.md](references/online/storage-hardware.md) (filter driver/Event 11/225) -> Cluster Size/MFT | IOPS not improving, slow read/write |
| System sluggishness or slow response | `GuestOS.SystemSlowPerformance` | [performance-slow.md](references/online/performance-slow.md) (CPU/memory/handle/page file/power plan/Minifilter) -> PowerShell Top-N process identification | Overall sluggishness, slow file opening |
| Abnormal instance boot or shutdown time | `GuestOS.UnexpectedlySlowLoading` | Boot/shutdown time breakdown ([performance-lifecycle.md](references/online/performance-lifecycle.md)) -> network shared drive mount check -> driver abnormality -> ClearPageFileAtShutdown and update-in-progress check (shutdown phase) -> event logs | Slow boot, long spinning before reaching desktop, slow shutdown (completes but takes too long) |

### 5. Instance Configuration Not Taking Effect

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Cannot reset user password in system | `GuestOS.ResetUserPasswordsFailed` | vminit log check ([cloud-vminit.md](references/online/cloud-vminit.md)) -> Cloud Assistant password change -> offline disk mount password change | Console/OpenAPI reset not taking effect, image password not taking effect |
| Cannot online expand cloud disk, partition, or file system | `GuestOS.ExtendingDiskStorageFailed` | Known issue determination (system/driver version requirements) -> [storage-disk.md](references/online/storage-disk.md) (disk/partition/file system expansion status check and extension) | Capacity unchanged after expansion |
| Cannot generate dump file after system crash | `GuestOS.DumpProductionFailed` | Crash Dump configuration check (CrashControl registry/page file dependency, [system-crash.md](references/online/system-crash.md)) -> disk space check -> determination of some BSODs unable to generate dump | No dump after BSOD, incomplete dump |
| user-data execution failure | `GuestOS.VminitUserDataExecutionFailed` | user-data understanding confirmation -> system disk replacement cache determination -> vminit userdata log ([cloud-vminit.md](references/online/cloud-vminit.md)) -> metaserver user-data content check | user-data not executed/errored |
| Custom DNS configuration not taking effect | `GuestOS.UnexpectedDNSConfiguration` | [networking-dns.md](references/online/networking-dns.md) -> vminit/DHCP overwrite check | DNS configuration reverted, resolution not as expected |
| hostname modification not taking effect | `GuestOS.HostnameModifyFailed` | hostname configuration check -> vminit overwrite check -> restart to take effect confirmation | Name change reverted |
| Group Policy not taking effect | `GuestOS.GroupPolicyNotApplied` | [system-gpo.md](references/online/system-gpo.md) -> gpupdate result | GPO not applied, login script not executed |
| Scheduled task not executing | `GuestOS.ScheduledTaskFailed` | [system-schtasks.md](references/online/system-schtasks.md) | Task not running, startup failure, invalid credentials |

### 6. Management Channel Issues

| Problem Domain | Unique Identifier | Unified Diagnostic Sequence | Covered Sub-scenarios |
| --- | --- | --- | --- |
| Management channel (WinRM/WMI/Cloud Assistant) abnormality | `GuestOS.ManagementChannelAbnormal` | [system-management.md](references/online/system-management.md) (PowerShell execution policy / WinRM / WMI repository / event log service / MMC) -> [cloud-vminit.md](references/online/cloud-vminit.md) (AliyunService service status) | PowerShell script blocked by execution policy, WinRM remote management failure, WMI repository corruption, event log service not starting, MMC cannot open console, Cloud Assistant command execution failure (OS-side component abnormality) |

> Problems in this group share a unified diagnostic sequence (in-instance management channel components -> cloud-side management agent); currently contains only a single domain.

### 7. Other Issues

Problems that cannot be classified into the six groups (startup/crash-Hang/usage/performance/configuration not taking effect/management channel) fall into this group, displaying information that can be automatically analyzed without customer authorization, with no targeted diagnostic sequence; record and directly seek expert support.

---

## Fallback Mechanism (Sole Authority)

When no defined domain is matched, or the preset sequence completes without finding a root cause, handle by the following levels:

1. **Debug event log deep-dive**: Preset sequence completes without finding root cause, and the fault can be reproduced by the user (or periodically recurs naturally) -> first enable Debug/Analytic log channels for relevant components, collect debug channel events after reproduction for analysis; if not applicable (cannot reproduce, no available debug channels) or still no clues after deep-dive, proceed to the next level
2. **Global baseline health check**: Problem cannot be classified into any defined domain, or preset sequence completes without finding root cause (including Debug log deep-dive with no results) -> load [system-health-check.md](references/online/system-health-check.md) to execute full-dimension baseline scan, route to corresponding domain file for in-depth diagnosis based on scan results; when completely unclassifiable, MUST explain to the user: "This is a dynamically planned diagnostic path, not a preset scenario"
3. **Capability boundary**: Root cause still not confirmed after baseline check and routing deep-dive, or all references are irrelevant -> truthfully record the diagnostic scope and all findings, inform the user that current diagnostic capability does not cover this scenario, provide recommended diagnostic directions and transfer to expert support

---

## Output Format Templates

### Evidence Review Template

Present this before the diagnostic conclusion:

> **Evidence Review**
>
> **Data Collected**:
>
> | # | Collection Action | Key Result |
> |---|-------------------|------------|
> | 1 | {command or check description} | {brief summary of what was returned} |
> | 2 | ... | ... |
>
> **Judgment Traceability**:
>
> | Judgment | Supporting Evidence | Confidence |
> |----------|---------------------|------------|
> | {conclusion from causal chain} | {specific data point that directly confirms it} | Confirmed |
> | {inferred conclusion} | {what was observed that led to this inference} | Hypothesis -- missing: {data items}; collect via: `{commands}` |
>
> **Unsupported Judgments**: {list any judgments downgraded to hypotheses, or "None -- all conclusions are evidence-backed"}

### Causal Chain Example

```
[User Problem] Cannot connect via Remote Desktop
    |
    |--- [Direct Cause] TermService service stopped
    |       `--- [Indirect Cause] Dependent service RpcSs abnormal
    |
    `--- [Direct Cause] Firewall blocking port 3389
            `--- [Indirect Cause] Public network profile in effect

--- Other Findings ---

    `--- [Other finding, for reference] Windows Firewall Private Profile is disabled
            `--- Note: Not directly related to the current RDP connection failure, but poses a security risk; user is advised to be aware
```

### Diagnostic Conclusion Output Template

> **Diagnostic Conclusion**
>
> **User Problem**: {Original problem description}
>
> Found {N} issues, ranked by fix priority:
>
> ---
>
> **Issue 1 (Direct cause, Critical, will affect functional availability): {root_cause}**
>
> **Evidence**: {Collected abnormal data -- MUST cite the concrete identifiers the collection actually returned: Event IDs (e.g., Application Error Event ID 1000/1001), exception/error codes (e.g., 0xc0000005), faulting module or service names, registry values, file paths, timestamps. A paraphrase without these identifiers is NOT acceptable evidence.}
>
> **Analysis**: {Why this issue directly caused the phenomenon the user observed}
>
> **Causal chain**: {User problem} <- {Direct cause} <- {Indirect cause (if any)}
>
> **Fix plan**:
> ```powershell
> {Fix script}
> ```
>
> **Fix impact**:
> - Session impact: {Whether it disconnects existing TCP/RDP sessions; if no impact, annotate "No impact on existing sessions"}
> - Persistence scope: {"Survives reboot" / "Current session only" / "Written to registry"}
> - Rollback command: {One-line copyable reversible operation}
>
> **Verification**:
> ```powershell
> {Verification command}
> ```
> Expected result: {Normal state}
>
> ---
>
> **Issue 2 (Indirect cause, Warning, may affect stability): {root_cause}**
> ...

**Final answer self-containment (required)**: the conclusion message actually shown to the user -- not only the saved report file -- MUST stand alone and restate two things: (1) the raw symptom error text as observed, quoted verbatim in the system's own language (e.g., ping returning "General failure" on English systems or its Chinese equivalent on Chinese systems, a BSOD stop code, an RDP error message) -- the exact error string is the user's anchor that ties your conclusion back to what they saw; (2) the root-cause category in concrete terms (e.g., an outbound firewall rule / WFP outbound filter blocking that specific target), naming the mechanism and the blocking direction. A terse closing reply that only says "fixed and verified" or buries these details exclusively in the report file fails this requirement.

### Platform-Side Root Cause Output Template

Use this variant when the conclusion comes from L2 platform triage (platform facts fully explain the symptoms). The structure mirrors the Diagnostic Conclusion Output Template, but the remediation is console/API guidance rather than a PowerShell script:

> **Diagnostic Conclusion**
>
> **User Problem**: {Original problem description}
>
> **Root cause (platform-side)**: {platform fact, e.g., no public IP assigned and outbound bandwidth = 0}
>
> **Evidence (platform-side)**: {API + exact field values, e.g., `DescribeInstances`: `PublicIpAddress=[]`, `InternetMaxBandwidthOut=0`}
>
> **Ruled out (in-instance)**: {what in-guest data was checked and what it excluded, e.g., DHCP service running, valid IP 192.168.0.35, gateway reachable -- the GuestOS network stack is functional}
>
> **Remediation (user-side, console/API)**: {concrete steps, e.g., associate an EIP or allocate public bandwidth via console/OpenAPI}
>
> **Verification**: {observable platform state after the change, plus any in-guest re-check command}
>
> **Incidental in-guest findings (optional fix)**: {anomalies observed inside the guest that are independent of the platform root cause, each with its own fix plan and confirmation request, or "None"}

### Check Item Summary Template

After completing each diagnostic step, present a brief summary to the user before proceeding:

> **Check Item: [Step Name]**
> - **Collection**: [key data collected, abbreviated]
> - **Analysis**: [one-sentence determination basis]
> - **Result**: Normal / Abnormal [if abnormal: brief description]

---

## PowerShell Collection Script Rules

### 0. Pre-Execution Self-Check Checklist

After writing the script and **before** executing, MUST scan the script text item by item against the table below; fix any matched signals according to the corresponding section before executing.

This step cannot be skipped: violations of these rules almost always manifest as PowerShell execution errors or garbled output, not as locally visible syntax errors. Waiting until the command fails to go back and check the rules first wastes an extra round-trip, and second, script-level errors are easily misread as target system "abnormalities", leading diagnostic conclusions astray. Scanning item by item takes only a few seconds, and the benefit far outweighs the cost.

| # | What to Search for in the Script | What to Do When Matched |
|---|---|---|
| 1 | `Get-WmiObject`, `net user`, `net localgroup`, `netstat`, `ipconfig`, `tasklist`, `sc query` | Replace with native cmdlets from the Section 1 mapping table; only keep and pass through raw output for those marked "no direct replacement" |
| 2 | Any pipeline outputting to the console | Confirm `Select-Object` is used to limit key fields; add per Section 2 if not limited |
| 3 | Pipeline from `Select-Object` / `ForEach-Object { [PSCustomObject]@{...} }` | Append `| Format-Table` or `| Format-List` at the end of the pipeline, see Section 2 |
| 4 | `Get-ItemProperty` | Confirm `PSPath` and other metadata fields are filtered, see Section 2 |
| 5 | Custom variable names | Compare against built-in keywords / automatic variables list in Section 3; rename if colliding |
| 6 | `slmgr`, `winver` | Change to `cscript //Nologo ...vbs` form, see Section 4 |
| 7 | `Get-WindowsFeature`, `Invoke-WebRequest`, `Invoke-RestMethod`, `Expand-Archive`, `Start-BitsTransfer`, `Copy-Item -ToSession/-FromSession` | Prepend `$ProgressPreference = 'SilentlyContinue'`, see Section 5 |
| 8 | `$variable:` in double-quoted strings | Rewrite as `${variable}:`, see Section 6 |
| 9 | Pipe `|` immediately after the closing brace of a `foreach (` statement | Use `ForEach-Object` instead, see Section 7 |
| 10 | exe calls like `reg`, `bcdedit`, `diskpart`, `dism`, `netsh` | Confirm using `$LASTEXITCODE` or stderr for error detection instead of `try/catch`, see Section 8 |
| 11 | `Substring(`, `CurrentVersion`, `ProductName` | Change to version number comparison or SKU branching, and null-check `CurrentVersion`, see Section 9 |
| 12 | `Set-Content`, `[System.IO.File]::WriteAllText` | Confirm the same file does not mix both methods, see Section 10 |
| 13 | Full command text intended for user manual execution | Pass through Section 11 display gating before display (pure ASCII + placeholder compliance + no local path dependency + can be copied and executed as a whole); fix any non-compliant item before display |
| 14 | The command payload itself about to be executed | **Local mode**: Multi-line scripts go through Base64 channel; inline single-line commands use single quotes, see Section 12. **Remote mode**: Deliver via `aliyun ecs run-command` -- plaintext by default (omit `--content-encoding`); Base64 with `--content-encoding Base64` only when quoting is impractical, see Section 13 |
| 15 | `-ErrorAction SilentlyContinue`, `2>$null`, `\| Out-Null`, `2>/dev/null` | Applies to BOTH Local and Remote mode payloads. Suppression is allowed only for state-table collection where absence of output is itself the finding; otherwise keep stderr, error text, and exit codes in the returned output (`$LASTEXITCODE` locally, `ExitCode` + `Output` remotely) and analyze them as potential root cause, see [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) (Output Size Management -> error preservation rule). The skill's bundled scripts (`scripts/*.ps1`) are stricter: zero `-ErrorAction SilentlyContinue`, every step guarded by Section 8 try/catch section guards |
| 16 | Double-quoted strings in native CLI invocations (`reg`, `netsh`, `bcdedit`, `dism`, `diskpart` arguments) | PowerShell 5.1 strips double quotes when passing arguments to native CLIs; rewrite the script to contain single-quoted strings only and retry on the same channel (script-layer error, not a target-system fault), see High-Frequency Pitfalls |
| 17 | The script being dispatched is a FIX script (modifies system state), via ANY channel | Before dispatching, verify ALL four conditions: (1) the complete plan with risk notes has already been presented to the user in an earlier message; (2) that message ended with an explicit confirmation question; (3) the user's confirmation arrived as a NEW message in a later turn; (4) the confirmation is not being inferred from the original task request ("troubleshoot and fix" is not confirmation). Any condition unmet -> do NOT dispatch; present the plan, end the turn, and wait. See Fix Plan output rule 3 and SKILL.md Principle 6 |

### 1. Cmdlet Selection

- `Get-WmiObject` is deprecated on some systems; prefer `Get-CimInstance`
- Prefer PowerShell native cmdlets over cmd tools to avoid dependence on cmd's text output format (field names vary with system language)

#### cmd -> PowerShell Replacement Mapping Table

| cmd Command | PowerShell Replacement |
|-----------|-------------------|
| `net user` | `Get-LocalUser` / `Get-CimInstance Win32_UserAccount` |
| `net localgroup` | `Get-LocalGroupMember` / `Get-CimInstance Win32_GroupUser` |
| `netstat` | `Get-NetTCPConnection` / `Get-NetUDPEndpoint` |
| `ipconfig` | `Get-NetIPConfiguration` / `Get-NetIPAddress` |
| `tasklist` | `Get-Process` / `Get-CimInstance Win32_Process` |
| `sc query` | `Get-Service` / `Get-CimInstance Win32_Service` |
| `net accounts` | No direct replacement, pass through raw output |
| `netsh` | No direct replacement, pass through raw output |
| `fsutil` | No direct replacement, pass through raw output |
| `bcdedit` | No direct replacement, pass through raw output |

When there is no native replacement -> pass through raw output for LLM analysis; do not parse text fields in scripts.

### 2. Output Style

#### Command Output Format Simplification

When using commands to collect information, the output format MUST be as simple as possible to reduce the LLM's comprehension cost. Prefer using `Select-Object` to output only key fields, avoiding verbose full object output.

- Recommended: `Get-Service TermService | Select-Object Name, Status, StartType`
- Not recommended: `Get-Service TermService` (output includes many irrelevant fields)
- Recommended: `Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 Id, Name, CPU`
- Not recommended: `Get-Process | Sort-Object CPU -Descending | Select-Object -First 5` (output 20+ fields)

#### PowerShell Formatting Output Delay

Objects returned by `Select-Object` enter a delayed formatting queue; subsequent `Write-Host` output may reach the console before the table, causing output order confusion. When writing collection scripts, MUST append `| Format-Table` or `| Format-List` after `Select-Object` to force synchronous rendering, ensuring correct output order at the source.

#### Get-ItemProperty Output Filtering

`Get-ItemProperty` returns PowerShell metadata fields including `PSPath`, `PSParentPath`, `PSChildName`, `PSDrive`, `PSProvider` by default, which interfere with diagnostic output. MUST filter these fields using one of the following methods:

1. Pipe `| Select-Object <target properties>` to explicitly select needed properties (recommended, for scenarios with known property names)
   ```powershell
   Get-ItemProperty ... -Name ProxyEnable, ProxyServer | Select-Object ProxyEnable, ProxyServer
   ```
2. Pipe `| Select-Object -Property * -ExcludeProperty PSPath,PSParentPath,PSChildName,PSDrive,PSProvider` (for scenarios needing all registry values but excluding metadata)

Directly outputting the full result of `Get-ItemProperty` is prohibited.

### 3. Variable Naming to Avoid Built-in Identifiers

Custom variable names in PowerShell collection scripts MUST avoid using built-in keywords (such as `switch`, `foreach`, `function`, etc.) and automatic variables (such as `$_`, `$input`, `$args`, `$error`, `$host`, `$pwd`, `$foreach`, `$switch`, `$null`, `$true`, `$false`, etc.).

Misuse of built-in identifiers leads to abnormal script behavior or variable value overwriting, making troubleshooting difficult.

### 4. GUI Dialog Command Handling

Commands like `slmgr`, `winver` pop up graphical dialogs by default, causing hangs in non-interactive execution environments.

Must use the `cscript //Nologo` prefix to call the corresponding `.vbs` script, redirecting output to the console:

```powershell
# Wrong: will pop up dialog and hang
slmgr /dli

# Correct: console output
cscript //Nologo C:\windows\system32\slmgr.vbs /dli
```

### 5. Suppress Progress Stream for Remote Execution

When executing remotely, Progress streams generated by some cmdlets mix into CLIXML metadata, interfering with output parsing. When scripts use the following cmdlets, MUST prepend `$ProgressPreference = 'SilentlyContinue'`:

| cmdlet | Trigger Scenario |
|--------|----------|
| `Get-WindowsFeature` | Enumerating roles/features |
| `Invoke-WebRequest` / `Invoke-RestMethod` | Downloading content |
| `Expand-Archive` | Extracting files |
| `Start-BitsTransfer` | Transferring files |
| `Copy-Item -ToSession/-FromSession` | Cross-session copy |

### 6. Pitfall of Colon After Variable Name in String Interpolation

PowerShell interprets `$var:` in `"$var:"` as a drive-qualified variable reference (e.g., `$env:`, `$global:`), causing the variable value to not expand correctly.

When a variable name in a string is immediately followed by a colon, MUST wrap the variable name in curly braces:

```powershell
# Wrong - $name: parsed as drive reference
"$name: OK"

# Correct
"${name}: OK"
```

This rule also applies when the variable name is followed by other PowerShell special characters (such as `(`, `[`).

### 7. foreach Statement Cannot Directly Connect to Pipeline

`foreach ($x in $list) { ... }` is a **statement**, not an expression; appending `| Format-Table` / `| Where-Object` / `| Select-Object` and other pipeline operations after the closing brace will report "An empty pipe element is not allowed". MUST use the `ForEach-Object` cmdlet instead:

```powershell
# Wrong
foreach ($f in $files) {
    [PSCustomObject]@{ File = $f }
} | Format-Table

# Correct
$files | ForEach-Object { [PSCustomObject]@{ File = $_ } } | Format-Table
```

For any scenario requiring unified formatting of loop results, always use `ForEach-Object`.

### 8. cmd Tool Error Handling Using $LASTEXITCODE

cmd tools like `reg.exe` / `bcdedit.exe` / `diskpart.exe` / `dism.exe` / `netsh.exe` do not throw PowerShell exceptions; errors are indicated only by non-zero exit codes. `try/catch` cannot capture them; MUST check `$LASTEXITCODE` or capture stderr:

```powershell
# Wrong - try/catch is ineffective
try { netsh advfirewall show allprofiles } catch { Write-Host 'failed' }

# Correct - check exit code
$out = netsh advfirewall show allprofiles 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "netsh failed: $out" }
```

#### Section Guard: try/catch Keeps Collection Running

exe tools need `$LASTEXITCODE` (above); PowerShell cmdlet errors need the opposite -- a section-level `try/catch` guard. Collection steps are independent: one failing check must never abort the rest of the script. Bundled collection scripts (`scripts/*.ps1` under this directory) MUST follow this shape and contain NO `-ErrorAction SilentlyContinue` -- the error text is diagnostic evidence, and a swallowed error is a lost signal:

```powershell
$ErrorActionPreference = 'Stop'

# --- Step 1: Check Device Status and Error Codes ---
try {
    $allDevices = Get-CimInstance Win32_PnPEntity
    # ...collect and print...
} catch {
    Write-Host ("ERROR step1 pnp-devices: " + $_.Exception.Message)
}

# --- Step 2: runs even if Step 1 failed ---
try {
    $bcd = bcdedit /enum '{current}' 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step2 bcdedit: exit=$LASTEXITCODE $($bcd | Out-String)" }
    $testSigning = $bcd | Select-String 'testsigning'
    # ...
} catch {
    Write-Host ("ERROR step2 driver-signing: " + $_.Exception.Message)
}
```

Why `$ErrorActionPreference = 'Stop'` plus guards: with the default `Continue`, a failing cmdlet sprays untagged error text that is hard to attribute to a step; with `Stop` the error jumps to that section's catch, gets a `ERROR step<N> <tag>:` prefix, and the next section still runs. A terminating error without a guard would kill the script and lose every later section.

### 9. Version String Parsing

Registry `CurrentVersion` / `ProductName` and other string formats are inconsistent across versions (`"6.1"` vs `"10.0"`); **prohibited** from using `Substring(0, N)` or fixed indices, as it throws `ArgumentOutOfRangeException` on short strings. MUST use one of:

```powershell
# Approach A: version number comparison
if ([version]$cv.CurrentVersion -ge [version]'6.2') { ... }
# Approach B: product SKU branching
if ($cv.ProductName -match 'Server 2008 R2|Windows 7') { ... }
```

When `CurrentVersion` is not read, MUST first `if ($cv.CurrentVersion) { ... }`; otherwise `$null` will cause subsequent exceptions.

### 10. UTF-8 BOM Compatibility

Windows PowerShell 5.x `Set-Content -Encoding UTF8` writes **with BOM** (`UTF8` = UTF-8 with BOM, no `utf8NoBOM` option); PowerShell 7+ `-Encoding UTF8` writes **without BOM** (`utf8` = utf8NoBOM alias); requires `-Encoding UTF8BOM` to align with PS5; PS 7+ without specifying `-Encoding` also defaults to `utf8NoBOM`.

- `ConvertTo-Json | Set-Content -Encoding UTF8` can be read back normally by `Get-Content -Raw | ConvertFrom-Json` in both PS5/PS7 (`ConvertFrom-Json` tolerates BOM), no special handling needed
- Mixing `Set-Content` and `[System.IO.File]::WriteAllText` on the same file across scripts is prohibited; BOM will be written repeatedly
- Strictly no BOM: `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))` (`$false` = do not emit BOM)

### 11. User Command Display Gating (MUST Validate Before Display)

For any scenario that degrades to "display commands for user manual execution", commands MUST pass the following validation gating **before** being displayed to the user; fix any non-compliant item before display -- the user environment cannot tolerate errors like the direct execution channel; one non-compliant command will directly stall the diagnostic workflow:

1. **Pure ASCII**: The full command text (script comments, separator markers like `# --- <item-name> ---`, placeholders, and explanation text) MUST be ASCII characters; Chinese comments, Chinese prompts, and full-width symbols are prohibited. Reason: the user's terminal encoding environment is uncontrollable (GBK/UTF-8), and non-ASCII characters are prone to garbled text after copy-paste, which may cause PowerShell parsing failure
2. **Placeholder compliance**: Values needing user replacement MUST use `<placeholder>` notation and explain the replacement content outside the command; residual internal variables from diagnostic context or temporary values from prior collection are prohibited
3. **No local path dependency**: Commands MUST NOT reference diagnostic-side local temp files/paths (e.g., intermediate products under `.diag-tmp`); all inputs must come from the user's own environment or be inline in the command
4. **Can be copied and executed as a whole**: When merging multiple commands, maintain clear separator markers; individual commands MUST NOT depend on the previous command's shell state (each is self-contained)

```powershell
# bad - non-ASCII comments break in some terminals
# Check RDP service status
Get-Service TermService

# good - pure ASCII
# Check RDP service status
Get-Service TermService
```

### 12. Command Transmission Mode (Direct Execution Channel)

When calling `powershell.exe` via Bash to execute commands, the command delivery method directly affects execution results:

1. **Multi-line scripts MUST use Base64 encoding when calling powershell.exe directly**: Pass via `powershell.exe -EncodedCommand <Base64>`; passing multi-line scripts directly as command-line arguments is prohibited -- multi-line scripts passed directly as command-line arguments will be split by whitespace/newlines (reporting `too many arguments`), causing only fragments to execute. If passing a script file via the `-File` parameter, this restriction does not apply. If `[Convert]::ToBase64String` is unavailable in ConstrainedLanguage mode, MUST use the `-File` parameter to pass the script file (`-File` path is also not subject to Base64 restrictions).
2. **Inline single-line commands MUST wrap the full command text in single quotes**: When wrapped in double quotes, `$var`, `$_`, etc. will be expanded by Bash first; by the time it reaches the PowerShell process, the variable is already lost; when single quotes are needed inside the command, escape them as two single quotes (`''`).
3. After execution, MUST verify that the returned output matches the expected number of collection segments; when empty output or missing fragments are found, first troubleshoot the transmission layer before suspecting the target system.

### 13. Remote Execution Channel Rules

When the remote execution channel is active, PowerShell commands are sent to the target instance via Alibaba Cloud CLI's `aliyun ecs run-command` API and executed by the Cloud Assistant agent (AliyunService). This section defines only the decision rules; all how-to details (API semantics, execution pattern, error codes, timeout table, output limits) are consolidated in [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md).

#### 13.1 Prerequisites

Before the first remote command, verify the prerequisites per the SKILL.md "Execution Channel" section (aliyun CLI installed and configured, target instance ID and region ID known, target instance Running, target instance `OSType` = `windows` confirmed by the same `describe-instances` call -- the remote-channel implementation of the SKILL.md Windows-Only Gate). If the region is unknown, locate the instance per [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section Prerequisites -- never guess it from the instance ID prefix or any other part of the ID (prefixes do not reliably encode the region and reasoning from them has produced fabricated region names); use the CLI-default-region probe, ask the user, or run the full region sweep. `DescribeInstances` returns an empty result (not an error) when the instance is not in that region. If `OSType` is not `windows`, exit the diagnostic flow entirely per the Windows-Only Gate (state the verified facts and reason; no WORKFLOW-GUIDE entry, no commands, no channel fallbacks). If the instance is not Running (or cannot boot at all -- e.g., system disk released), this channel is unusable until the user starts or repairs the instance via console. Store the `RegionId` and `InstanceId` as session context for reuse across all remote commands in this session.

#### 13.2 Command Delivery Rules

- Default: pass the script as plaintext in `--command-content` and omit `--content-encoding` (server default `PlainText`); follow the Section 12 shell quoting rules
- Only when shell quoting is impractical: Base64-encode the script and MUST set `--content-encoding Base64`; never send Base64-encoded content with `PlainText` encoding
- `--type RunPowerShellScript` is required for Windows instances; flag spellings are kebab-case per [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section CLI Flag Reference
- When the shell running the aliyun CLI is Windows PowerShell, JSON array arguments (e.g. `--instance-ids '["i-..."]'`) lose their inner double quotes and the API rejects the malformed JSON -- use the 5.1 backslash-escape form, the raw form on PowerShell 7.3+, or a repeatable quote-free flag, per [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section Operator-Shell Quoting for JSON Arguments

#### 13.3 Execution Loop

Send (`RunCommand`) -> capture the invocation ID from the JSON response (the response carries BOTH `CommandId` prefix `c-` and `InvokeId` prefix `t-` -- poll with `InvokeId`/`InvocationId`, never `CommandId`) -> poll `DescribeInvocationResults` every ~5 seconds until a terminal status (`Success` / `Failed` / `Stopped` / `Timeout` / `Error`) -> also read `ExitCode` (0 = clean script exit) -> decode the Base64 `Output` field. The polling window MUST cover the full `--timeout` plus a buffer -- never stop after a fixed attempt count shorter than the command timeout.

#### 13.4 Fix Script Rules

Fix scripts run in TWO separate turns -- never one. Presenting the plan and sending the fix script inside the same turn is a rule violation regardless of wording that claims authorization (SKILL.md Principle 6).

- **Phase A -- present and stop (this turn)**: present the complete fix plan (script content, what it changes, risk notes) and ask the user to confirm, then END the turn. No `RunCommand` in this turn, not even a "prepared" or "staged" one.
- **Phase B -- execute only after confirmation (a later turn)**: start ONLY when the user's confirmation arrives as a new message after the plan. Then send the fix script through the Section 13.3 loop with a longer timeout (180-300 seconds), and afterwards send a verification command through the same loop to confirm the fix took effect.

If the user's reply is a question or a modification request, that is not confirmation: answer it and end the turn again.

#### 13.5 Failure Classification

Classify failures per the Collection Fallback Chain above: channel-layer failures degrade the channel; script-layer failures are fixed in the script and retried on the same channel; timeout failures get one timeout increase before chunking or degrading. API ErrorCode meanings and remedies: [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section Error Handling.

#### 13.6 Output Management Rules

Cloud Assistant truncates oversized command output (truncation observed at roughly 10+ KB; exact limit undocumented -- verify by observation). Keep every collection script's output small per the Section 2 output style rules: limit fields, limit rows, narrow time windows, execute one step at a time. Detailed strategies: [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section Output Size Management.

#### 13.7 Session Context

Maintain for the duration of the remote session: `RegionId` (region of the target instance), `InstanceId` (target instance ID), and the UA session-id -- generated once when the remote channel is entered (before the first CLI call, including prerequisite gates) and reused unchanged for every CLI call, per [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section Observability. Track internally and reference in all subsequent remote commands.

#### 13.8 Post-Execution Verification

After each remote command, MUST verify: (1) `InvocationStatus` is `Success` -- otherwise handle per [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section Error Handling; (2) output is non-empty when data was expected -- distinguish "the target system returned no data" (valid result) from "the command never reached the target" (channel error); (3) the decoded output matches the expected format defined in the diagnostic file's Analysis section.

### High-Frequency Pitfalls

This section lists **high-frequency mandatory contracts** that MUST be followed when executing Windows commands.

#### Staircase Handling for Non-existent Commands

When a cmd tool or PowerShell cmdlet reports "command/module not found", the environment likely does not support that tool; **retrying the original command is prohibited**; MUST handle by the following staircase:

1. **Try a semantically equivalent alternative tool**: Select another tool that can achieve the same collection goal
2. **Skip and record**: When all alternatives are unavailable, record "This check item was skipped due to tool unavailability" and continue executing subsequent steps

#### Mixing PowerShell and cmd Redirection Syntax

In PowerShell, discarding output MUST use `$null` instead of cmd's `nul`; using cmd redirection syntax like `>nul` / `2>nul` / `1>nul` will trigger `RedirectionFailed` errors.

#### Command Parameters with Curly Braces MUST Be Quoted

PowerShell treats bare `{...}` as a script block; when passed to native cmd/exe tools, it will not be passed as a literal string, causing the original command's parameter parsing to fail. Literals containing curly braces MUST be wrapped in **double quotes** or **single quotes**, e.g., `bcdedit /enum "{default}"`.

#### PowerShell 5.1 Strips Double Quotes in Native CLI Argument Passing

Windows Server images ship with PowerShell 5.1 by default; when passing arguments to native executables, embedded **double quotes are stripped** and never reach the target CLI. Symptom: a native CLI call (`reg`, `netsh`, `bcdedit`, `dism`, `diskpart`, ...) fails with parameter-parsing errors -- "The syntax of the command is incorrect", values split at spaces, flags reported as missing -- even though the command text looks correct. This is a **script-layer error**, not a target-system fault: do NOT reclassify it as target abnormality and do NOT switch channels. Fix: rewrite the script so it contains **single-quoted strings only**, then retry on the **same channel** (per Section 13.5 failure classification). When a value genuinely needs quoting for the target CLI, prefer restructure-into-single-quotes over embedded double quotes.

#### No Repeated Queries to the Same WMI Class Within the Same Code Block

Within the same PowerShell code block, multiple `Get-CimInstance` calls to the same CIM class (e.g., `Win32_PnPEntity`, `Win32_ComputerSystem`) MUST be merged into one query and stored in a variable; subsequent access is through in-memory filtering (`Where-Object`) or property access.

```powershell
# [FAIL] Prohibited: two network round-trips
$errors = Get-CimInstance Win32_PnPEntity | Where-Object { $_.ConfigManagerErrorCode -ne 0 }
$all    = Get-CimInstance Win32_PnPEntity
Write-Host "Total: $($all.Count)"

# [PASS] Correct: single query + variable reuse
$allDevices   = Get-CimInstance Win32_PnPEntity
$errorDevices = $allDevices | Where-Object { $_.ConfigManagerErrorCode -ne 0 }
Write-Host "Total: $($allDevices.Count)"
```

> Note: Different diagnostic steps (independent code blocks) may each query the same class since they need to be independently and optionally executable.
