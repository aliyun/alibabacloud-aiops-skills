# Scenario 1: Vulnerability Query and Filtering

This scenario addresses queries like "what vulnerabilities do I have, which are most urgent, what is the situation on a specific server / for a specific CVE": filter the vulnerability list by combined dimensions of type, severity, status, and asset, and drill down into repair solutions and vulnerability details.

## Trigger Conditions

Example user phrasings (enter this scenario when any matches):

- "Show me the unfixed / high-severity vulnerabilities"
- "What vulnerabilities does this server (name/IP) have?"
- "Are we affected by CVE-2021-44228 (Log4Shell)?"
- "Which vulnerabilities failed to fix? Which are fixed but pending reboot?"
- "Give me a high-severity unfixed list / vulnerability count statistics"

## Prerequisites

1. CLI and credential checks, session-id generation: see SKILL.md (Observability section). All API commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>`.
2. All operations in this scenario are read operations — execute directly; state the query intent to the user in one sentence before execution.
3. Clarify the query scope: confirm the four dimensions — vulnerability type (Type), severity (Necessity), status (Status), asset (Uuids/Remark) — with the user first; never assume default values.

## Workflow

### Step 1: Confirm the filter intent

Intent: clarify what "type + severity + status + assets" the user wants to query, avoiding blind full pulls.

Confirm the four dimensions with the user (at minimum confirm Type — Type is a required query parameter):

| Dimension | Parameter | Values (contract enums) |
|-----------|-----------|-------------------------|
| Vulnerability type | `--type` | `cve`=Linux software, `sys`=Windows system, `emg`=emergency, `app`/`sca`=application (app and sca both appear under the console's "Application Vulnerabilities" tab), `cms`=Web-CMS (legacy type) |
| Repair urgency | `--necessity` | `asap`=high, `later`=medium, `nntf`=low |
| Handling status | `--status-list` | 1 unfixed, 2 fix failed, 4 fixing, 6 verifying, 7 fixed, 8 fixed-pending-reboot, 10 ignored, 20 expired, etc. |
| Handled or not | `--dealed` | `y` handled / `n` unhandled |

Result interpretation: if the user says "application vulnerabilities", query `app` and `sca` Types separately and merge; when presenting to the user, use the four-category classification "Linux software / Windows system / application / emergency vulnerabilities".

Vulnerability status (Status) full enum quick reference (use readable names when presenting): 1 unfixed, 2 fix failed, 3 rollback failed, 4 fixing, 5 rolling back, 6 verifying, 7 fixed, 8 fixed-pending-reboot, 9 rollback succeeded, 10 ignored, 11 rollback-pending-reboot, 12 vulnerability does not exist, 20 expired. See the vulnerability state machine table in references/scenario-recheck.md for state transition rules.

### Step 2: Asset location (when querying specific servers)

Intent: convert the server name/IP mentioned by the user into a Security Center asset Uuid (vulnerability queries filter by Uuid).

```bash
aliyun sas describe-cloud-center-instances --criteria '[{"name":"internetIp","value":"<public-ip>"}]' --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Criteria is a JSON array of search conditions, supporting instance ID, instance name, VPC ID, region, public IP, etc. (see references/api-reference.md for more condition names).

Result interpretation notes:
- Take the target asset's `Uuid` from the response (the asset identifier used by vulnerability APIs — not the ECS instance ID).
- Also check `ClientStatus` (online/offline/pause): scan results of offline assets may be stale — inform the user.
- Shortcut: the `--remark` parameter of `describe-vul-list` supports fuzzy filtering by asset name / public IP / private IP — for a single asset you can skip this step and use Remark directly.

### Step 3: Combined filtering with describe-vul-list

Intent: query the vulnerability list with the confirmed dimension combination (Type required, others stackable).

```bash
aliyun sas describe-vul-list --type cve --necessity asap --dealed n --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Common parameter combinations (see references/api-reference.md for the full parameter table): `--type` (required) + `--necessity` / `--status-list` / `--dealed` / `--uuids` / `--remark` + `--current-page` / `--page-size` pagination.

Result interpretation notes:
- Key response fields: `Name` (vulnerability name / CVE ID), `AliasName`, `Necessity`, `Status`, `VulRecords[].Uuid` / asset info, `FirstTs` (first detection time), `TotalCount`.
- Pagination note: NextToken pagination does not return TotalCount; prefer `--current-page`/`--page-size` mode when a total is needed.

### Step 4: User-facing table presentation

Intent: organize JSON results into a user-readable table rather than pasting raw responses.

Suggested columns: vulnerability name (with CVE ID) | severity (high/medium/low) | status (e.g., "unfixed / fix failed / fixed-pending-reboot") | affected asset (name or IP) | first detection time.

- Time conversion: APIs return millisecond Unix timestamps (e.g., `1737331200000`); convert to a readable local time before presenting, and explain that "first detection time" is when the vulnerability was first found by a scan.
- Present severity as "high/medium/low" (corresponding to asap/later/nntf); do not output raw enum values.
- For large result sets, give a summary first ("X total, Y high-severity"), then ask whether to expand details or group by asset.

### Step 5: Drill down into vulnerability details

Intent: drill down when the user follows up with "how to fix it, how severe, what does the official doc say".

```bash
aliyun sas describe-vul-list --type cve --name <vulnerability-name> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Repair solution: the response's `ExtendContentJson.RpmEntityList[].UpdateCmd` is the system-provided repair command (entry to the manual repair path, see references/scenario-repair.md).
- Vulnerability details (score / official repair solution / vulnerability database link) via `describe-vul-details` (parameters and response fields in references/api-reference.md): `Solution`=repair solution, `CvssScore`=CVSS score, `CveLink`=Alibaba Cloud Vulnerability Database link (https://avd.aliyun.com) — safe to give directly to the user.

### Step 6: Pagination traversal (when the list exceeds one page)

Intent: fetch all pages when the user wants the complete list (e.g., all high-severity unfixed) and a single page is insufficient.

- Start `--current-page` from 1, compute total pages from the returned `TotalCount` and `--page-size`, and fetch page by page.
- After each page, verify the count matches expectations before continuing; keep the call count within a reasonable range per scenario (see SKILL.md execution rules); for very large bulk needs, suggest the user switch to vulnerability report export (see boundaries).
- NextToken pagination does not return TotalCount — do not use it when a total must be presented.

## Common Query Recipe Table

| User Question | Command and Parameter Combination |
|---------------|-----------------------------------|
| Unfixed vulnerability list | `describe-vul-list --type <type> --dealed n`, or `--status-list 1` |
| High-severity unfixed list | `describe-vul-list --type <type> --necessity asap --dealed n` |
| All vulnerabilities on a specific asset | `describe-vul-list --type <type> --uuids <asset-uuid>`, or fuzzy query with `--remark <name/IP>` |
| Fix-failed list | `describe-vul-list --type <type> --status-list 2` (take ResultCode/ResultMessage, then go to references/scenario-errors.md) |
| Fixed-pending-reboot list | `describe-vul-list --type <type> --status-list 8` |
| Verifying list | `describe-vul-list --type <type> --status-list 6` |
| Vulnerability count statistics by type | `describe-grouped-vul` or `describe-vul-num-statistics` |
| Exact query by CVE ID | `describe-vul-list --type <type> --name <cve-id>` (also try `--alias-name <vulnerability-alias>`) |

> Append pagination parameters and `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>` to every command; see references/api-reference.md for full parameter descriptions.

Recipe usage notes:

- For "application vulnerabilities" recipes, run once for each of the `app` and `sca` Types and merge the presentation to avoid omissions.
- After finding results for the "fix-failed list", first take each record's `ResultCode`/`ResultMessage`, then interpret via the high-frequency error code table in references/scenario-errors.md — do not throw raw English error messages at the user.
- For "all vulnerabilities on specific assets" with multiple servers, pass multiple Uuids comma-separated (see api-reference.md for limits).

## Abnormal Query Result Handling

| Symptom | Possible Cause | Action |
|---------|----------------|--------|
| Empty list returned but the user insists vulnerabilities exist | Over-stacked filter conditions (e.g., Type+Necessity+Status simultaneously) | Re-query with only Type, then re-add conditions one by one to locate |
| No vulnerabilities found on some asset | Asset not connected to Security Center or Agent offline | Verify ClientStatus via describe-cloud-center-instances; if offline, point to the alibabacloud-sas-install-agent skill |
| First detection time is 0 or abnormally old | Data sync delay or historical record archival | Explain to the user that the latest scan prevails; status sync delays are normal (see references/scenario-recheck.md) |
| TotalCount inconsistent with actual count | Pagination mode difference (NextToken does not return TotalCount) | Switch to current-page/page-size mode to verify |

## User Communication Points

- Result explanation template: "Under the current filter conditions, X vulnerabilities were detected, of which Y are high-severity. Top priority to handle: `<vulnerability-name>` (affecting Z servers, first detected on `<date>`)." Numbers must come from actual API responses — never fabricate.
- No-result phrasing: "No vulnerability records were found under the current filter conditions", and suggest possible reasons: filter conditions too strict, asset not connected, Agent offline causing stale data (guide to the install-agent scenario), or the vulnerability type is genuinely clear.
- Guidance phrasing: when query results show many high-severity unfixed vulnerabilities, naturally transition to the repair scenario (see references/scenario-repair.md), but never initiate any write operation without confirmation.

## Notes and Boundaries

- **Read-only scenario**: this scenario never initiates write operations; if the user asks to "also fix/ignore/scan", switch to the corresponding scenario document and follow the write-operation confirmation flow.
- **Excel report export is out of scope**: when the user asks to "export Excel / generate a vulnerability report", point to the `alibabacloud-sas-vul-report` skill — this skill does not perform exports.
- **Statistics overview**: when the user asks for a "full-account vulnerability posture overview / dashboard-style analysis", point to the `alibabacloud-sas-overview` skill.
- The severity metric is primarily Necessity (asap/later/nntf); `describe-vul-details`'s VulLevel (serious/high/medium/low) is a different rating system — the two must not be mixed or cross-mapped.
- Free-edition (AuthVersion=1) assets support detection only, with no repair capability; query results remain visible, but repair guidance requires an edition upgrade first (see references/scenario-repair.md Step 2).
- `cms` (Web-CMS) is a legacy vulnerability type; if the user explicitly asks to query it, use `--type cms`, but explain it within the four-category classification.
- When querying by CVE ID: prefer `--name` (exact match on vulnerability name); if not found, try `--alias-name` (vulnerability alias); no results from both does not mean no risk — the software version path on the asset may differ; suggest cross-checking via asset-dimension queries.
- Do not promise "repair will definitely succeed" in query results; repair feasibility is determined in the repair scenario's pre-fix chain.

## Related Documents

- Command parameters and response fields: [references/api-reference.md](api-reference.md)
- Official documentation dynamic lookup: [references/doc-lookup.md](doc-lookup.md)
- Follow-up repair actions: [references/scenario-repair.md](scenario-repair.md)
- Repair failure troubleshooting: [references/scenario-errors.md](scenario-errors.md)
- Scenario entry and boundary overview: [../SKILL.md](../SKILL.md)
