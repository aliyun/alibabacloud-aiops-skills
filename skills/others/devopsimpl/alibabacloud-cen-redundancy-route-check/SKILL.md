---
name: alibabacloud-cen-redundancy-route-check
description: |
  Alicloud Service Scenario-Based Skill. Use for read-only auditing of Alibaba Cloud CEN dedicated-line/VPN down-cloud (cloud-to-IDC) route redundancy: detect missing VBR/VPN paths, Route Maps that break redundancy, conflicting routes, and policy-based routes that need manual confirmation. Covers dual-VBR ECMP, dual-VBR active/standby, VBR+VPN active/standby, CEN 1.0 and CEN 2.0 (Transit Router).
  Triggers: "CEN redundancy route check", "verify dual dedicated-line redundancy", "missing down-cloud route", "pre-failover route audit", "check CEN dedicated-line redundant routes", and equivalent requests in other languages.
---

# Alibaba Cloud CEN Dedicated Line / VPN Redundancy Route Check

## 1. Scenario Description

Read-only inspection of the down-cloud direction (VPC/CEN → IDC). The skill verifies whether active/standby or equal-cost paths have complete configuration evidence, and reports missing paths, Route Map impact, conflicting routes, and uncovered scope.

**Architecture:** `IDC → Physical dedicated line / VPN → VBR / VPN Attachment → CEN Transit Router → VPC`

Supported scenarios:

- Dual-VBR equal-cost (ECMP) load balancing
- Dual-VBR active/standby
- VBR + VPN active/standby
- CEN 1.0 regional routes and CEN 2.0 TR system/custom route tables
- Same-region and cross-region VPC down-cloud paths

This skill only reads configuration and status. It never performs failover, never modifies routes, and a configuration check never replaces a real failover drill.

## 2. Installation

**Mandatory preflight: detect and bootstrap Aliyun CLI before any other skill step**

> [MUST] Run this local environment check before parameter confirmation, credential inspection, or any cloud API invocation:
>
> ```bash
> if ! command -v aliyun >/dev/null 2>&1; then
>   case "$(uname -s)" in
>     Darwin|Linux)
>       /bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
>       ;;
>     *)
>       echo "Aliyun CLI is not installed and automatic installation is unsupported on this platform." >&2
>       exit 1
>       ;;
>   esac
> fi
> command -v aliyun >/dev/null 2>&1 && aliyun version
> ```
>
> - If `aliyun` is absent, automatically run the official setup script on macOS/Linux, then verify that the command is available.
> - The verified version MUST be >= 3.3.3. For an installed version below 3.3.3 or a major upgrade, run the official setup script and verify again. For routine updates on CLI >= 3.3.5, prefer `aliyun upgrade`.
> - If download, installation, command discovery, or version verification fails, STOP before authentication or cloud API calls and report the failing step. Never continue with a missing or unsupported CLI.
> - On Windows, STOP and direct the user to the official installer; do not invent an installation command.
> - This bootstrap changes only the local tool environment. It MUST NOT configure credentials or modify cloud resources.
> - See `references/cli-installation-guide.md` for full installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
> [MUST] if either required plugin is still unavailable, run `aliyun plugin install --names aliyun-cli-cbn aliyun-cli-vpc`, verify both plugins, and STOP if installation fails.

Required plugins: `aliyun-cli-cbn` and `aliyun-cli-vpc`.

## 3. Environment Variables

This skill requires no environment variables. AK/SK MUST NOT be passed through environment variables by this skill.

Names such as `$CEN_ID`, `$VBR_ID`, `$REGION_ID`, `$IDC_CIDR`, `$TRANSIT_ROUTER_ID`, `$VPC_ID`, and `$VPC_ROUTE_TABLE_ID` in this document are placeholders for user-confirmed or API-returned values. Do NOT export or assign them as shell variables; substitute the literal value into each command before execution (see 7.0).

Never write real credentials into commands, scripts, reports, or the repository.

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## 5. RAM Policy

The minimum read-only Actions are listed in [references/ram-policies.md](references/ram-policies.md). Prefer granting specific Actions; if organizational policy requires system policies, an administrator may evaluate `AliyunCENReadOnlyAccess` and `AliyunVPCReadOnlyAccess`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

| Parameter Name | Required/Optional | Description | Default Value |
|---|---|---|---|
| `CEN_ID` | Conditionally required | CEN instance ID; provide at least one of `CEN_ID` and `VBR_ID` | None |
| `VBR_ID` | Conditionally required | VBR to focus on; provide at least one of `CEN_ID` and `VBR_ID` | None |
| `REGION_ID` | Required | Region of the VBR/TR; confirm every related region for cross-region scenarios | None |
| `IDC_CIDR` | Required | Target IDC CIDR block(s) in the down-cloud direction; multiple values allowed | None |
| `VPN_ATTACHMENT_ID` | Optional | VPN Attachment ID for VBR+VPN mode | None |
| `EXPECTED_MODE` | Required | `dual-vbr-ecmp`, `dual-vbr-active-standby`, or `vbr-vpn-active-standby` | None |
| `PROFILE` | Optional | Configured Aliyun CLI profile | Current profile, still requires confirmation |

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

If only a VBR ID is provided, enumerate CEN instances within the scope confirmed by the user, then locate the owning CEN through its attached child instances. Never blindly scan across accounts or regions.

Values stated explicitly in the user's request (CEN ID, VBR ID, region, IDC CIDR, expected mode) count as user-confirmed; do not ask for them again. Ask for all missing parameters together in one message, never one at a time. If no reply can be obtained (for example in a non-interactive run), do not wait, loop, or re-ask: continue with the read-only workflow, use the region derived from the CEN/VBR topology, treat every prefix whose next hop is a VBR or VPN as a candidate IDC CIDR, report the observed redundancy mode per prefix, and list the unconfirmed parameters under "Parameters to confirm" in the report.

## Observability (MUST follow for every aliyun command)

Before any cloud API invocation, read `references/manifest.json` from this skill's root and use only its top-level non-empty string `version` as `{skill-version}`. If the file is missing, invalid, or the field is absent/empty/not a string, STOP and report the error. NEVER invent, guess, or reuse a version from another skill.

Bind version and session to the current skill name and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. When switching skills or returning to this skill, reread this skill's manifest; never cross-skill reuse either value.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

Markdown examples may omit the flag for brevity. The Agent MUST append the exact flag below to every actual execution, including commands generated or extended at runtime; do not repeat UA boilerplate in every example block.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cen-redundancy-route-check/{session-id} skill-version/{skill-version}"
```

The entire UA value MUST be double-quoted because it contains a space. Do not skip, alter, or omit it on any `aliyun` API command.

**Script / Terraform execution:** Pass both scoped values inline as environment variables. In the template below, `{session-id}` and `{skill-version}` are placeholders only: before execution the Agent MUST substitute `{session-id}` with this skill's generated 32-character lowercase hex session ID and `{skill-version}` with the `version` read from `references/manifest.json`. NEVER execute the template with literal `{session-id}` / `{skill-version}` text, and NEVER substitute example or empty values.

```bash
# Template — replace both placeholders with the actual runtime values before running
# Python SDK script
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/deploy.py

# Terraform
TF_VAR_session_id={session-id} TF_VAR_skill_version={skill-version} terraform apply
```

Before running, verify the substituted command contains no `{` or `}` characters in either value and that the session ID matches `^[0-9a-f]{32}$`; otherwise STOP and report the error.

Scripts and Terraform configs MUST require both values (fail if unset or empty) and construct the same UA product.
Generated Terraform providers MUST set `configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-cen-redundancy-route-check/${var.session_id} skill-version/${var.skill_version}"`; here `${var.session_id}` and `${var.skill_version}` are Terraform interpolations resolved from the injected `TF_VAR_*` values, not placeholders for the Agent to edit.

## 7. Core Workflow

Every List/Describe query MUST traverse all `PageNumber` or `NextToken` pages and deduplicate by resource ID. The commands below show only the first request; every actual execution MUST append the `--user-agent` flag defined in Observability.

### 7.0 Execution Rules and Mandatory Query Checklist

- **One literal command per call:** run every cloud API call as a single standalone `aliyun` command with all values written literally, e.g. `--cen-id cen-abc123 --biz-region-id eu-central-1`. NEVER use shell variables, `for`/`while` loops, functions, `xargs`, scripts, heredocs, command substitution, or `&&`/`;` chaining to build or batch cloud API calls. Piping a single command's output into a local JSON viewer is allowed.
- **Never skip a checklist step:** run every applicable step below even when earlier evidence already looks conclusive or the user did not mention that resource type. An empty result is evidence; record it instead of skipping the query.
- **Never run interactive commands** (for example `aliyun configure` without subcommand arguments). Stop pagination when `NextToken` is empty or repeats.

CEN 2.0 region (has an `Enterprise` TR):

| # | Command | Mandatory parameters |
|---|---|---|
| 1 | `cbn describe-cens` | `--filter` with the literal `CenId` (omit only when the CEN ID is unknown and must be discovered) |
| 2 | `cbn describe-cen-attached-child-instances` | `--cen-id` |
| 3 | `cbn list-transit-routers` | `--cen-id` |
| 4–7 | `cbn list-transit-router-peer-attachments`, `-vpc-attachments`, `-vbr-attachments`, `-vpn-attachments` (all four, always) | `--cen-id`, `--transit-router-id`, `--biz-region-id` |
| 8 | `cbn list-transit-router-route-tables` | `--transit-router-id` |
| 9 | `cbn list-transit-router-route-entries` (every route table) | `--transit-router-route-table-id` |
| 10 | `vpc describe-route-table-list` (every in-scope VPC) | `--biz-region-id`, `--vpc-id` |
| 11 | `vpc describe-route-entry-list` (every VPC route table × every IDC CIDR) | `--biz-region-id`, `--route-table-id`, `--destination-cidr-block` |
| 12 | `cbn describe-cen-route-maps` | `--cen-id`, `--cen-region-id` |
| 13 | `cbn describe-route-conflict` (every VPC route table × every IDC CIDR) | `--child-instance-id`, `--child-instance-type VPC`, `--child-instance-region-id`, `--child-instance-route-table-id`, `--destination-cidr-block` |

CEN 1.0 region (only a `Basic` TR or no TR): run steps 1–3, then `cbn describe-cen-region-domain-route-entries` (`--cen-id`, `--cen-region-id`), then steps 10–13 for every VPC child instance attached to the CEN in that region (taken from step 2). NEVER run steps 4–9 (any `list-transit-router-*-attachments`, `list-transit-router-route-tables`, or `list-transit-router-route-entries`) against a CEN 1.0 region or its Basic TR.

If no VPC is in scope, report steps 10, 11, and 13 as "Not applicable: no VPC attached in the inspected region"; never silently omit them.

### 7.1 Confirm CEN and Topology

```bash
aliyun cbn describe-cens \
  --filter "[{\"Key\":\"CenId\",\"Value\":[\"$CEN_ID\"]}]" --page-size 50
aliyun cbn describe-cen-attached-child-instances \
  --cen-id "$CEN_ID" --page-size 50
aliyun cbn list-transit-routers \
  --cen-id "$CEN_ID" --page-size 50
```

Decision rules (decide per region, never for the whole CEN at once):

- Group the returned TRs by their `RegionId` and record each TR's `Type`. A single CEN can have Enterprise TRs in some regions and Basic or no TRs in others.
- Target region has an `Enterprise` TR: inspect that region with the CEN 2.0 workflow.
- Target region has only a `Basic` TR or no TR: enter the CEN 1.0 workflow for that region only if the CEN query, attachment query, TR query, pagination, and permissions all succeeded, and the target VBR is attached to the CEN in that region. Basic TRs expose no TR route tables or attachments to inspect.
- Any critical query failed or returned incomplete scope: mark the version of the affected region as "Unable to confirm".
- TRs in other regions never switch the target region to the CEN 2.0 workflow; they are only followed when Peer Attachments link them to the target region.
- A TR whose `Type` is missing or unrecognized: mark the version of that region as "Unable to confirm".

### 7.2 Enumerate CEN 2.0 Attachments

For each Enterprise TR in a region identified as CEN 2.0:

```bash
aliyun cbn list-transit-router-peer-attachments \
  --cen-id "$CEN_ID" --transit-router-id "$TRANSIT_ROUTER_ID" \
  --biz-region-id "$REGION_ID" --max-results 100
aliyun cbn list-transit-router-vpc-attachments \
  --cen-id "$CEN_ID" --transit-router-id "$TRANSIT_ROUTER_ID" \
  --biz-region-id "$REGION_ID" --max-results 100
aliyun cbn list-transit-router-vbr-attachments \
  --cen-id "$CEN_ID" --transit-router-id "$TRANSIT_ROUTER_ID" \
  --biz-region-id "$REGION_ID" --max-results 100
aliyun cbn list-transit-router-vpn-attachments \
  --cen-id "$CEN_ID" --transit-router-id "$TRANSIT_ROUTER_ID" \
  --biz-region-id "$REGION_ID" --max-results 100
```

Continue with the returned `NextToken` until it is empty. Record attachment status, resource ID, TR ID, region, and peer information.

For each Peer Attachment, also record the peer region, peer TR ID, and `AutoPublishRouteEnabled`. To state whether the IDC CIDR reaches the peer region, run steps 8–9 against the peer TR as well; if `AutoPublishRouteEnabled` is `false` or the prefix is absent there, report the cross-region Peer as "IDC CIDR not propagated" rather than omitting it.

### 7.3 Inspect TR Route Tables

```bash
aliyun cbn list-transit-router-route-tables \
  --transit-router-id "$TRANSIT_ROUTER_ID" --max-results 100
aliyun cbn list-transit-router-route-entries \
  --transit-router-route-table-id "$TR_ROUTE_TABLE_ID" \
  --transit-router-route-entry-status All --max-results 100
```

Traverse system and custom route tables, filter `IDC_CIDR` and its more-specific prefixes, and record route status, type, origin, next-hop attachment, next-hop resource type, and resource ID. Never omit `Rejected`, `Prohibited`, `Standby`, or `Candidate` routes.

### 7.4 Inspect Same-Region and Cross-Region VPC Routes

For the VPC and region of each VPC Attachment:

```bash
aliyun vpc describe-route-table-list \
  --biz-region-id "$VPC_REGION_ID" --vpc-id "$VPC_ID" --page-size 50
aliyun vpc describe-route-entry-list \
  --biz-region-id "$VPC_REGION_ID" --route-table-id "$VPC_ROUTE_TABLE_ID" \
  --destination-cidr-block "$IDC_CIDR" --max-result 100
```

In a CEN 1.0 region, the VPCs to inspect are the VPC child instances returned by `describe-cen-attached-child-instances` for that region. Always pass `--destination-cidr-block` with each literal IDC CIDR; if more-specific prefixes must be checked, run an additional query without the filter after the filtered one.

Both system and custom route tables MUST be inspected. When the next hop is `Attachment`, `VpnGateway`, `RouterInterface`, or another related type, combine it with TR-side evidence to confirm the full path. Never conclude redundancy is healthy from VPC-side routes alone.

### 7.5 Inspect CEN 1.0 Regional Routes

Run only for regions confirmed in 7.1 to have a Basic TR or no TR:

```bash
aliyun cbn describe-cen-region-domain-route-entries \
  --cen-id "$CEN_ID" --cen-region-id "$REGION_ID" \
  --status All --page-size 500
```

Traverse every related CEN 1.0 region and aggregate Active/Candidate/Rejected/Prohibited routes and next hops per IDC prefix.

### 7.6 Inspect Route Maps and Route Conflicts

```bash
aliyun cbn describe-cen-route-maps \
  --cen-id "$CEN_ID" --cen-region-id "$REGION_ID" --page-size 50
aliyun cbn describe-route-conflict \
  --child-instance-id "$VPC_ID" --child-instance-type VPC \
  --child-instance-region-id "$VPC_REGION_ID" \
  --child-instance-route-table-id "$VPC_ROUTE_TABLE_ID" \
  --destination-cidr-block "$IDC_CIDR" --page-size 50
```

Determine whether `Deny` actions, attribute changes, direction, or priority filter standby paths or break the ECMP/active-standby relationship. `describe-route-conflict` is mandatory in both CEN 1.0 and CEN 2.0 for every in-scope VPC route table and IDC CIDR; collect its required parameters from steps 2 and 10 first, and record an empty result as "No conflict reported".

### 7.7 Determine Redundancy

| Expected Mode | Healthy Evidence | Missing/Abnormal Evidence |
|---|---|---|
| `dual-vbr-ecmp` | The same IDC prefix has at least 2 valid, expected, equal-cost VBR paths | Only one VBR, unequal attributes, or a path is Rejected/Prohibited |
| `dual-vbr-active-standby` | The primary path is valid, and a provable Standby/Candidate or policy-backed standby VBR path exists | No standby path evidence, or a Route Map filters the standby route |
| `vbr-vpn-active-standby` | Both the VBR primary path and the VPN standby path have complete topology and route evidence | VPN Attachment/route is missing or unavailable |

The VPC `DescribeRouteEntryList` API cannot fully prove PBR matching on source address, protocol, or port, nor its failover behavior. If existing API evidence is insufficient, mark PBR as "Manual confirmation required"; never report "No PBR found".

### 7.8 Output Report

Write the report in the language of the user's request, following this structure:

```markdown
# CEN Redundancy Route Check Report

## Basic Information
- CEN / VBR / Region / IDC CIDR: ...
- CEN version per region: <region>: 1.0 / 2.0 / Unable to confirm
- Expected mode: ...
- Query completeness: Complete / Partially failed

## Topology Coverage
| Attachment Type | Count | Status | Resource IDs / Peer Region | Route Evidence for IDC CIDR |
|---|---|---|---|---|
| VPC | ... | ... | ... | ... |
| VBR | ... | ... | ... | ... |
| VPN | ... | ... | ... | ... |
| Peer (cross-region) | ... | ... | ... | ... |

## Route Table Check
| Scope | Route Table | Destination CIDR | Next Hop | Route Status | Redundancy Verdict |
|---|---|---|---|---|---|

## Route Maps and Conflicting Routes
| Policy/Conflict | Direction | Match Conditions | Action | Impact |
|---|---|---|---|---|

## Query Errors and Uncovered Scope
- API/permission/pagination errors: ...
- Resources not inspected and why: ...
- PBR items requiring manual confirmation: ...

## Conclusion and Recommendations
- Topology verdict per attachment type: VPC: ...; VBR: ...; VPN: ...; Peer (cross-region, <peer region>): ...
- Healthy items: ...
- Missing redundant paths: ...
- Unable-to-confirm items: ...
- Recommended failover verification: ...
```

If any critical query failed, the overall conclusion MUST NOT be "All healthy".

The Topology Coverage table MUST contain one row for each of VPC, VBR, VPN, and Peer, even when the count is 0 (write "0 / None found"; in a CEN 1.0 region write "Not applicable: CEN 1.0" for VPN and Peer). The Conclusion MUST repeat a one-line verdict for every attachment type by name, including the cross-region Peer and its peer region, and whether the IDC CIDR is propagated across it. When the report is written in a language other than English, keep the type names `VPC`, `VBR`, `VPN`, `Peer` as-is and write the cross-region item as "cross-region Peer" translated into that language, keeping `Peer` literal.

**Final reply rule:** the final chat reply to the user IS the report. Output the complete report above directly in the final reply, in the same language as the user's request (for example, a Chinese request gets a Chinese reply, even if commands, logs, or intermediate notes were in English). Saving the report to a file is optional and never replaces it; NEVER end with only a short summary, a status table, or a file path. For a non-English reply, translate the section headings Basic Information / Topology Coverage / Route Table Check / Route Maps and Conflicting Routes / Query Errors and Uncovered Scope / Conclusion and Recommendations into the user's language; keep resource IDs, CIDRs, route statuses (`Active`, `Standby`, ...) and `Route Map` literal, and state the route-conflict result ("No route conflicts found" or the conflicts found) and the redundancy verdict explicitly in that language. If any parameter is still unconfirmed, the final reply MUST also repeat the one-message parameter question and the "Parameters to confirm" list, translated into the user's language.

## 8. Success Verification Method

Verify according to [references/verification-method.md](references/verification-method.md): all target regions, TRs, attachments, TR route tables, and VPC route tables are covered; pagination is complete; every IDC prefix has redundancy evidence matching the expected mode; all failures and unknowns are included in the report.

## 9. Cleanup

This skill only runs read-only queries and never creates or modifies cloud resources, so no cloud cleanup is needed. If the user asked to save intermediate query results to local files, obtain user consent before deleting them after the report is delivered.

## 10. Best Practices

1. Use the user-confirmed IDC CIDR as the primary key; never infer direction from route names.
2. Inspect both Active and non-Active routes to avoid missing standby, conflicting, and policy-prohibited states.
3. Cross-validate TR and VPC sides; single-side evidence is never an end-to-end redundancy verdict.
4. For empty lists, verify permissions, region, pagination, and filters before concluding a resource does not exist.
5. Even after the configuration check passes, run a real link failover drill through the change-management process.

## 11. Reference Links

| Reference | Description |
|---|---|
| [references/reference.md](references/reference.md) | Detailed inspection algorithm |
| [references/related-commands.md](references/related-commands.md) | Related CLI commands |
| [references/ram-policies.md](references/ram-policies.md) | Minimum RAM permissions |
| [references/verification-method.md](references/verification-method.md) | Success verification method |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [references/manifest.json](references/manifest.json) | Skill version manifest |
