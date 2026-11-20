---
name: alibabacloud-ecs-compliance-cert-guide
description: |
  Read-only guide for ECS compliance and security-qualification evidence: maps MLPS 2.0 (Dengbao) control areas to official ECS capability docs, separates platform and customer duties for certificates, and builds a cross-region read-only self-audit inventory.
  Use when a customer prepares a classified-protection assessment or asks for compliance certificates and proof documents.
  Triggers: "Dengbao requirements", "MLPS 2.0 assessment", "level 3 protection compliance", "security qualification materials", "compliance certificate", "proof documents", "cryptographic assessment", "NoPermission", "ImplicitDeny".
  Do NOT use: disk or inode full -> alibabacloud-ecs-diagnose; expansion not applied -> alibabacloud-ecs-disk-expand-diagnosis; start/stop stuck -> alibabacloud-ecs-instance-state-diagnosis; slow disk IO -> alibabacloud-ecs-disk-io-diagnosis; remediation -> console guidance.
metadata:
  openclaw:
    requires:
      # No environment variable is required: the skill runs on the aliyun CLI
      # default credential chain alone.
      env: []
      # Both binaries evidenced in the shipped code must be installed.
      bins: [aliyun, python3]
---

# ECS Compliance and Security-Qualification Evidence Guide

Help a customer prepare evidence for a classified-protection (MLPS 2.0, "Dengbao") assessment or a general security-compliance review on Alibaba Cloud ECS. Three capabilities, all strictly read-only:

1. **S1 - Control mapping**: translate the control areas the customer cites (operations audit, log retention, secure area boundary, host baseline, cryptography assessment) into the platform capabilities and official ECS documentation listed in [references/compliance-cert-guide__mlps-mapping.md](references/compliance-cert-guide__mlps-mapping.md).
2. **S2 - Materials guidance**: explain which compliance certificate / security-qualification materials the platform publishes, which report the customer must obtain from an accredited assessment body, and which items need a human or commercial channel (see [references/compliance-cert-guide__compliance-materials.md](references/compliance-cert-guide__compliance-materials.md)). Official download-channel links for this tier are NOT yet verified: until they are, S2 answers stay in DEGRADED mode and never invent a link.
3. **S3 - Read-only self-audit inventory**: list the customer's instances, states and bound security groups across the regions they name, using the two whitelisted read APIs, and render a pre-assessment self-audit checklist that separates observed facts (script output) from manual console checks.

The customer rarely states the technical need; match the symptom sentence or error string, then route with the decision tree below.

## Data Flows and External Calls

The shipped code contacts exactly one destination family: the Alibaba Cloud ECS OpenAPI (product `ecs`, API version `2014-05-26`) through the `aliyun` CLI as a subprocess. Per call it sends: the action name, the region ID, pagination parameters, an optional instance-ID filter, and the per-run `--user-agent` observability label `AlibabaCloud-Agent-Skills/alibabacloud-ecs-compliance-cert-guide/<session-id>` (a random 32-hex identifier, not an account identifier). Authentication is attached by the aliyun CLI from its own default credential chain; the scripts never read, print, or forward any access key, secret key, or STS token. Only the two whitelisted read actions in Absolute Rule 2 are ever invoked; nothing is created, changed, deleted, or executed inside the customer's account. The knowledge mode (`--topic`) performs no network calls at all.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command or script that calls a mutating OpenAPI action - any action whose name starts with `Create*`, `Delete*`, `Modify*`, `Update*`, `Put*`, `Attach*`, `Detach*`, `Release*`, `Reset*`, `Revoke*`, `Start*`, `Stop*`, `Reboot*`, `Replace*`, `Import*`, `Export*`, `Add*`, `Remove*`, `Join*`, `Leave*`, `Authorize*` - including "commands for the user to run manually" produced through this skill. This skill is read-only. If the user asks to harden a security group, enable a product, delete resources, or clean disks, output manual guidance only and hand off per Rule 7.
2. **API WHITELIST:** The only permitted OpenAPI actions are the read queries `ecs:DescribeInstances` (instance inventory and bound security groups) and `ecs:DescribeInstanceStatus` (running state) - product `ecs`, version `2014-05-26`, reached only through `scripts/`. `ecs:DescribeAvailableResource` is deliberately NOT authorized for this skill and must never be called. Any action outside the whitelist is prohibited even if it is a read query.
3. **NO GUEST EXECUTION:** This skill never runs commands inside an ECS instance. There is no Cloud Assistant / workbench execution channel here, not even for "read-only in-guest diagnostics". In-guest evidence (password policy, audit switches, log retention inside the OS) is a manual customer task; mark it as such in the checklist.
4. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. Credentials are resolved automatically by the aliyun CLI default credential chain. Never ask the user for an AK/SK pair; on missing credentials, tell the user to run `aliyun configure` themselves.
5. **NO FABRICATION:** Every conclusion must come from script output or the embedded reference knowledge. If a query fails or returns empty, record it and state the limitation - never invent instance counts, certificate names, standards clauses, or document URLs. Only URLs present in `references/` may be cited; the S2 official-channel URLs are pending human verification and MUST NOT be invented (report that gap as DEGRADED).
6. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <Code>: <Message>` to stderr and continue with the remaining regions - never silently skip a step and never abort the whole run on one failure. A permission failure must name the missing action and point to [references/ram-policies.md](references/ram-policies.md) using the error literals `NoPermission` / `ImplicitDeny`.
7. **SCOPE BOUNDARY + HANDOFF:** This skill covers only compliance-evidence guidance and the read-only self-audit inventory. When the conversation shows an out-of-scope symptom - disk or inode full, expansion not applied, instance stuck starting/stopping, slow disk IO, actual remediation inside a cloud product, legal-grade stamped originals - stop diagnosing and emit the matching handoff sentence from [references/compliance-cert-guide__handoff-matrix.md](references/compliance-cert-guide__handoff-matrix.md). Cleanup, deletion, configuration changes and refunds are never executed here.

## Trigger Conditions

Use this skill when the customer's own wording matches one of the phrases the `description` advertises (natural-English renderings of the Dengbao tier triggers):

- "Dengbao requirements" / "MLPS 2.0 assessment" / "level 3 protection compliance"
- "security qualification materials" / "compliance certificate" / "proof documents"
- "cryptographic assessment"
- an asset query that fails with `NoPermission` or `ImplicitDeny` while the customer is collecting compliance evidence

Generic words such as "permission", "security" or "compliance" alone MUST NOT trigger this skill; they count only in combination with the assessment / qualification / proof-document context above.

## Execution Principle

All cloud evidence MUST be gathered by running `scripts/axes/compliance_cert_guide/compliance_inventory.py` (single entry). The Agent is prohibited from assembling its own `aliyun` CLI commands or importing anything to bypass the script - the script embeds the API whitelist, pagination, retry, error degradation, and the observability guarantees. Knowledge answers come from the script's `--topic` mode or the `references/` files, never from model memory. If a script fails, relay its `STATUS`/`NEXT_ACTION`; do not improvise replacements.

## Observability

All OpenAPI calls (invoked through the aliyun CLI by the script) include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-ecs-compliance-cert-guide`.
- **session-id**: a 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached via `--user-agent` to every CLI call of that run, so all calls of one diagnosis can be correlated. The shared layer in `scripts/axes/compliance_cert_guide/_cli.py` implements this automatically.

## Prerequisites

1. **aliyun CLI >= 3.3.3** (required) - the only execution backend (built-in API metadata mode for `ecs`, PascalCase actions and parameters). Check with `aliyun version`; upgrade with `aliyun aliyun-cli update` or reinstall via the official installer (`curl -fsSL https://aliyuncli.alicdn.com/install.sh | bash`). Older 3.x builds lack the plugin-mode sub-commands this skill calls and MUST be upgraded before use.
2. **Python 3.9+** - standard library only; see `scripts/requirements.txt` (no third-party dependencies).
3. **Credentials** - resolved automatically by the aliyun CLI default credential chain; if the identity call path fails with a credential error, the script exits `STATUS: FAIL` and tells the user to configure `aliyun configure`. Never request raw keys.

## User Confirmation

Every action here is a whitelisted read query, so no per-call confirmation is required before running the script - but scope discipline is mandatory:

1. The region list is customer-supplied; never widen it to "scan all regions" on your own. Ask once for the regions (and optionally the instance IDs) if the customer did not name them.
2. Restate the read-only scope before the first inventory run (which regions, which filter).
3. Any request that would change cloud state, execute commands in an instance, or promise an official stamped document is refused with the handoff sentence (Absolute Rule 7), not confirmed and executed.

## Orchestration

```
Customer wording
  |- out-of-scope symptom (disk/inode, expand, start-stop, IO, remediation, legal docs)
  |     -> references/compliance-cert-guide__handoff-matrix.md: emit handoff sentence, stop
  |- S1 control mapping ("what does Dengbao check on ECS?", "level 3 requirements")
  |     -> python3 scripts/axes/compliance_cert_guide/compliance_inventory.py --topic mlps-control-map
  |        -> relay mapping rows + cite only URLs listed there + responsibility boundary
  |- S2 materials ("give me the compliance certificate / proof documents")
  |     -> python3 scripts/axes/compliance_cert_guide/compliance_inventory.py --topic material-scope
  |        -> responsibilities + channel status; official channels pending -> DEGRADED wording
  |- S3 self-audit ("inventory my instances before the assessment")
        -> python3 scripts/axes/compliance_cert_guide/compliance_inventory.py --regions <r1[,r2...]> [--instance-ids ...]
           -> read-only inventory table + manual checklist; report ends with STATUS/NEXT_ACTION
```

## Execution Flow

### Step 1: Classify and confirm scope

Route the request to S1, S2, S3, or handoff using the tree above. For S3 collect the region list (required) and an optional instance-ID filter; ask once if missing - never guess or scan unlisted regions.

### Step 2 (S1/S2): Knowledge answers from embedded references

```bash
cd $SKILL_DIR && python3 scripts/axes/compliance_cert_guide/compliance_inventory.py --list-topics
cd $SKILL_DIR && python3 scripts/axes/compliance_cert_guide/compliance_inventory.py --topic <key>
```

Relay the topic output; the document URLs it prints are the only citable links. If the customer needs a control item outside the embedded map, say so explicitly and mark it pending human verification instead of improvising a mapping.

### Step 3 (S2): Materials responsibility split

Run `--topic material-scope`. State: platform-published qualification evidence vs. customer-obtained assessment report vs. legal-channel items; then state that the official download-channel links for this tier are not yet verified (DEGRADED) and guide the customer to the console / official help-site search and to a support ticket for stamped or paper originals. Never name a file the customer "should find" there.

### Step 4 (S3): Read-only cross-region inventory

```bash
cd $SKILL_DIR && python3 scripts/axes/compliance_cert_guide/compliance_inventory.py --regions cn-hangzhou,cn-beijing [--instance-ids i-xxx,i-yyy] [--json]
```

The script calls `DescribeInstances` (NextToken pagination) and `DescribeInstanceStatus` (page-number pagination) per named region, degrades failed regions with `[WARN]` instead of aborting, and prints the inventory table plus the manual checklist. Empty region = valid finding ("no instances reported"), never an error.

### Step 5: Assemble the report

Separate three layers: observed facts (script fields), manual check items (embedded checklist), and guidance with citations (references). Permission gaps are reported with the missing action and the minimal policy pointer. Close with the script's `Summary` and its `STATUS` line.

### Step 6: Boundary check before answering

Scan the draft for any accidental promise to execute a change, fabricate a document channel, or run in-guest commands; replace it with the handoff or manual-guidance wording.

## Input Parameters

| Parameter | Required | Description |
|---|---|---|
| `--regions` | yes (inventory mode) | Comma-separated region IDs supplied by the customer, e.g. `cn-hangzhou,cn-shanghai`; the script loops one region at a time |
| `--instance-ids` | no | Comma-separated `i-*` IDs to narrow the inventory (passed as the API `InstanceIds` filter) |
| `--profile` | no | Optional aliyun CLI credential profile name |
| `--json` | no | Machine-readable report for the Agent to relay |
| `--list-topics` / `--topic` | no | Knowledge mode (S1/S2/handoff/checklist topics); performs no API calls |

No parameter is auto-filled silently: regions must come from the customer, and every filter used is echoed in the report header.

## Module Index

| Module | File | Responsibility |
|---|---|---|
| M1: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only policy for the two whitelisted actions; grant steps; permission-error table |
| M2: Control mapping | [references/compliance-cert-guide__mlps-mapping.md](references/compliance-cert-guide__mlps-mapping.md) | MLPS/Dengbao control areas vs. platform capabilities vs. official ECS docs; responsibility boundary; doc list |
| M3: Materials | [references/compliance-cert-guide__compliance-materials.md](references/compliance-cert-guide__compliance-materials.md) | Who provides which certificate/qualification material; pending-channel DEGRADED protocol |
| M4: Self-audit | [references/compliance-cert-guide__self-audit-checklist.md](references/compliance-cert-guide__self-audit-checklist.md) | Per-instance manual checklist items behind each automated observation |
| M5: Handoff | [references/compliance-cert-guide__handoff-matrix.md](references/compliance-cert-guide__handoff-matrix.md) | Out-of-scope symptom recognition and the exact handoff sentences |

## Available Scripts

| Script | Purpose |
|---|---|
| `scripts/axes/compliance_cert_guide/compliance_inventory.py` | Single entry: S3 read-only cross-region inventory (argparse, pagination, retry, degradation) and S1/S2 knowledge topics; emits `STATUS:` / `NEXT_ACTION:` |
| `scripts/axes/compliance_cert_guide/_cli.py` | Shared aliyun-CLI layer: API whitelist guard, per-run session-id + `--user-agent` on every call, transient retry with backoff, per-call timeout, credential masking |
| `scripts/axes/compliance_cert_guide/_constants.py` | Embedded constants and knowledge data (MUST 1.1.2: no data files in `scripts/`) |

### Exit codes (contract)

- `0` - the run produced a conclusion: `STATUS: OK`, or `STATUS: DEGRADED` when part of the evidence was unavailable (failed regions are recorded and still reported).
- `1` - no usable conclusion: `STATUS: FAIL` (missing required input, credential failure, or every region failed). `NEXT_ACTION` states what to ask for or fix; never treat exit 1 as a successful audit.
- `2` - argparse usage error only (unknown option). A diagnosed condition never exits with 2.

## Error Handling

| Error literal | Meaning | Action |
|---|---|---|
| `NoPermission` / `ImplicitDeny` | RAM policy missing one of the two read actions | Script prints the missing action and the pointer to M1; guide the grant, retry later |
| Credential-resolution failure from the CLI | No configured default-chain credential | Tell the user to run `aliyun configure`; never collect keys here |
| `InvalidParameter` | Bad region ID or instance-ID format | Fixed client-side before any call; relay the script message |
| `Throttling.User` / `InternalError` / `ServiceUnavailable` | Transient service failure | Retried with backoff (3 attempts); then degraded with `[WARN]` and kept in `errors[]` |
| Empty instance list | Region genuinely has no matching instances | Report as a valid empty finding; check the region list with the customer |

## Important Notes

- A platform-level qualification does NOT mean the customer's own system is compliant: assessment of the customer's business system, its controls and its evidence is always the customer's task through an accredited assessment body (shared-responsibility split in M2).
- Security-group rule detail (ports, sources) is NOT collected here: the rule-listing API is outside this skill's whitelist, so the checklist asks for a console review of each listed group ID instead.
- OS-level compliance facts (password policy, audit logs, patch state) are in-guest and out of scope (Absolute Rule 3); they appear only as manual check items.
- The S2 official-channel links are pending human verification in this release; the skill's own answer must say so verbatim.
- Results reflect only the account behind the current default-chain credential; state this in every report.

## Examples

**Example 1 - S1 mapping**

> User: "We must pass the Dengbao level 3 assessment - what does ECS need to show for the audit controls?"

```bash
cd $SKILL_DIR && python3 scripts/axes/compliance_cert_guide/compliance_inventory.py --topic mlps-control-map
```

Relay the control-area rows, cite only the URLs the topic output lists, and state which parts remain manual customer work.

**Example 2 - S2 materials request**

> User: "Please send us your compliance certificate and the security qualification proof documents for our audit."

```bash
cd $SKILL_DIR && python3 scripts/axes/compliance_cert_guide/compliance_inventory.py --topic material-scope
```

Explain the three buckets (platform-published evidence, assessment-body report, legal channel), and because the official download channels for this tier are pending verification, deliver the DEGRADED wording from M3 verbatim instead of naming links.

**Example 3 - S3 pre-assessment inventory**

> User: "List all our ECS instances with their security groups in cn-hangzhou and cn-beijing before our assessment next week."

```bash
cd $SKILL_DIR && python3 scripts/axes/compliance_cert_guide/compliance_inventory.py --regions cn-hangzhou,cn-beijing
```

Report the table per region (IDs, status, zone, type, network, security groups, public exposure) plus the manual checklist; declare that rule-level review and in-guest items are manual console work; end with the script's `Summary` and `STATUS`.

## Final Answer Contract

The final answer to the customer MUST:
1. Lead with the script's `Summary` relayed faithfully, including the `STATUS` outcome (`OK` / `DEGRADED` / `FAIL`).
2. Quote only fields actually returned by the two whitelisted queries; no invented instance data, certificate names, or standards clauses.
3. Declare the region list and any `--instance-ids` filter used (nothing is auto-filled silently).
4. Cite only document URLs that appear in the script output or `references/`; if `STATUS: DEGRADED` or the S2 channel note applies, state the pending-verification limitation verbatim.
5. Keep suggestions as manual guidance only (this skill changes nothing and executes nothing in the guest); for any out-of-scope or legal-channel request, end with the M5 handoff sentence instead of a fix list.
6. State the account-scope note: results reflect only the account behind the current credential.
