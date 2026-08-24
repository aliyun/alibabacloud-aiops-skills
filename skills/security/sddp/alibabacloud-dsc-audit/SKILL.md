---
name: alibabacloud-dsc-audit
description: |
  Query and handle security risk events from Alibaba Cloud Data Security Center. Supports viewing the list of unprocessed risk events and performing manual handling operations on risk events.
  Trigger words: "Data Security Center", "security risk events", "DSC", "risk handling", "DescribeRiskRules", "PreHandleAuditRisk"
---

# Alibaba Cloud Data Security Center Risk Event Query and Handling

This skill uses Alibaba Cloud Python Common SDK (generic invocation) to query security risk events from the Data Security Center and handle them.

## Architecture

```
User → Python Common SDK → Data Security Center (Sddp) API
                              ├── DescribeRiskRules (Query risk events)
                              └── PreHandleAuditRisk (Handle risk events)
```

## Prerequisites

> **IMPORTANT: The following prerequisites MUST be verified before executing any script in this skill.**

| # | Prerequisite | Check Command | Required |
|---|--------------|---------------|----------|
| 1 | Python 3 | `python3 --version` | >= 3.6 |
| 2 | pip3 | `pip3 --version` | any |
| 3 | Alibaba Cloud Python SDK | `python3 -c "import alibabacloud_tea_openapi"` | Exit 0 = installed |

### Install Python SDK Dependencies

If prerequisite #3 check fails (`ModuleNotFoundError`), install dependencies:

```bash
pip3 install -r scripts/requirements.txt
```

Required packages (`scripts/requirements.txt`):
- `alibabacloud_tea_openapi==0.4.3`
- `alibabacloud_credentials==1.0.8`
- `alibabacloud_tea_util==0.3.14`
- `alibabacloud_openapi_util==0.2.4`

> **Auto-recovery**: If any script fails with `ModuleNotFoundError`, run `pip3 install -r scripts/requirements.txt` and retry.

## Observability

Use one session-scoped User-Agent across every Alibaba Cloud business API request made through the CLI or SDK so all operations from one agent session can be correlated.

- The complete UA template is `AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`.
- For this skill, `SKILL_NAME` is always `alibabacloud-dsc-audit`.
- `session-id` must be a 32-character lowercase hexadecimal value.
- Generate it exactly once per agent session, store it in `SKILL_SESSION_ID`, and reuse it for every business API CLI invocation, SDK request, retry, page, and handling step in that session. Never generate a new value per command, script, or API request.
- If `SKILL_SESSION_ID` already exists, reuse it only when it matches the required format. If it is malformed, stop and correct the session environment before making any Alibaba Cloud request.

Initialize the session before any business API `aliyun` command or bundled Python script:

```bash
if [ -z "${SKILL_SESSION_ID:-}" ]; then export SKILL_SESSION_ID="$(openssl rand -hex 16)"; fi
if ! printf '%s' "$SKILL_SESSION_ID" | grep -Eq '^[0-9a-f]{32}$'; then echo 'SKILL_SESSION_ID must be a 32-character lowercase hexadecimal value' >&2; return 1 2>/dev/null || exit 1; fi
```

Every business API CLI invocation must append this exact flag:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dsc-audit/${SKILL_SESSION_ID}"
```

The Python SDK scripts read the same session ID from the environment and set:

```python
SESSION_ID = os.environ["SKILL_SESSION_ID"]
config.user_agent = f"AlibabaCloud-Agent-Skills/alibabacloud-dsc-audit/{SESSION_ID}"
```

Do not use persistent CLI configuration to set the User-Agent. The session-scoped `--user-agent` flag and SDK `config.user_agent` value above are the only supported mechanisms.
Do not attach `--user-agent` to system or utility commands, including `aliyun configure`, `aliyun plugin`, `aliyun help`, `aliyun version`, `aliyun upgrade`, and `aliyun --help`.

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run the following command to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.

```bash
aliyun version
```

> **Pre-check: Aliyun CLI plugin update required**

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

## Authentication

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

## RAM Permissions

Before using this skill, ensure the current user has the required RAM permissions. For detailed permission lists and policy configurations, refer to [references/ram-policies.md](references/ram-policies.md)

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `CurrentPage` | Optional | Current page number | 1 |
| `PageSize` | Optional | Records per page | 10 |
| `HandleStatus` | Optional | Processing status, PROCESSED means handled, UNPROCESSED means not handled | UNPROCESSED |
| `RiskId` | Required for handling | Risk event ID | - |
| `HandleDetail` | Required for handling | Handling details description | - |

## Core Workflow

### Step 1: Query Unprocessed Security Risk Events

Use the `scripts/query_risk.py` script to query unprocessed security risk events. This is a paginated API that returns the first 20 records by default.

**[MUST] Execute queries through the bundled script only.** All queries MUST go through `scripts/query_risk.py`. Do not write temporary or custom scripts for querying — including scripts that import functions from `query_risk.py` — and do not use inline SDK snippets or Aliyun CLI calls for queries. For pagination, re-run the bundled script once per page with the optional `CurrentPage` and `PageSize` arguments until all pages are retrieved.

```bash
python3 scripts/query_risk.py            # Page 1, 20 records per page (default)
python3 scripts/query_risk.py 2 20       # Page 2, 20 records per page
python3 scripts/query_risk.py 1 20 PROCESSED  # Query processed events
```

**[MUST] Summarize pagination results in the final answer.** After finishing a paginated query, the final answer MUST include the pagination summary by quoting the following sentence template **verbatim** and filling in the actual numbers:
"Query complete: all N pages were retrieved; TotalCount is X unprocessed risk events."
This exact sentence guarantees the required keywords: `all`, `pages`, and `TotalCount`. Do not paraphrase this summary into other wording. Do not omit the page count or the total count.

Example output:
```
Found 31 unprocessed security risk events
================================================================================
Risk ID: 75110196
Rule Name: jiangyu_test_mysqldump
Risk Level: High Risk
Product Type: RDS
Alert Count: 20
Asset Count: 2
Rule Category: Database Dump Attack
--------------------------------------------------------------------------------
```

### Query Result Field Descriptions

The query results return the following key fields. **Risk Event ID (RiskId) is a required parameter for handling**:

| Field | Description |
|-------|-------------|
| **RiskId** | Risk event ID, **required for handling** |
| RuleName | Rule name |
| WarnLevelName | Risk level (High Risk/Medium Risk/Low Risk) |
| ProductCode | Product type (RDS/OSS, etc.) |
| AlarmCount | Alert count |
| InstanceCount | Number of affected assets |
| FirstAlarmTime | First discovery time |
| LastAlarmTime | Last discovery time |

### Step 2: Handle Security Risk Events

Handling is a gated operation. Before running any handling command, complete the checks below in order.

1. **Confirm the target RiskId**
   - If the user did not provide a concrete `RiskId`, first run `python3 scripts/query_risk.py` and show the candidate Risk IDs. Then stop and quote this request **verbatim** in the final answer: "RiskId is missing. Please provide or explicitly select one specific RiskId from the unprocessed list above." Do not paraphrase this request into other wording. Wait for the user to provide or select the exact `RiskId`.
   - Even when the query result contains only one risk, or only one risk matches the user's description, you MUST still stop and ask the user to confirm that `RiskId` explicitly. A single match is NOT implicit confirmation. Do not proceed to asking for HandleDetail or running the handling script first.
   - If the user then confirms a `RiskId` that is absent from that query result, do not run `scripts/handle_risk.py`. The fresh query already proves that the target is not currently handleable. In the final answer, quote this conclusion **verbatim**: "No handleable risk event found: this RiskId is not in the unprocessed list and may already be processed." Do not paraphrase this conclusion into other wording. Show the `RiskId` values from the query result and ask the user to choose one; wait for confirmation before continuing.
   - This gate MUST be fully completed (the user has confirmed the exact target `RiskId`) before moving to the next gates.
   - Do not handle all returned risks, infer a target from broad wording, or choose a different risk on the user's behalf.
   - If the user explicitly asks to handle the first queried risk, query first and use only the first returned `RiskId`.

2. **Confirm HandleDetail**
   - `HandleDetail` is required audit evidence. If the user did not provide the exact text to record as HandleDetail, stop and ask for one.
   - When asking, the final answer MUST quote the following sentence **verbatim**: "Please provide the exact text to record as HandleDetail." This exact sentence guarantees the required keywords: `provide`, `exact text`, and `HandleDetail`. Do not paraphrase this request (e.g., "please describe how you handled it") because paraphrasing may drop the required keywords.
   - Vague handling intent such as "handle it", "mark it as handled", "already confirmed", "no need to follow up", or "close it" is not a valid `HandleDetail` unless the user explicitly says that exact text should be recorded.
   - Do not invent, summarize, reuse, or default the handling description.

3. **Pre-validate RiskId format**
   - If `RiskId` contains a negative sign, letters, shell metacharacters, whitespace-separated tokens, or any non-digit character, reject it before running any script or API call.
   - When rejecting, the final answer MUST quote the following sentence **verbatim**: "Invalid RiskId: it must be a positive integer. Please provide a valid RiskId." This exact sentence guarantees the required keywords: `Invalid RiskId`, `positive integer`, and `valid RiskId`. Do not paraphrase this rejection (e.g., "the id must be greater than zero") because paraphrasing may drop the required keywords.
   - A digits-only value such as `0` may be passed to `scripts/handle_risk.py` for local range validation; if the script rejects it, the final answer MUST report the validation error using the same verbatim sentence "Invalid RiskId: it must be a positive integer. Please provide a valid RiskId." and stop. Do not translate it into other wording.
   - For an explicitly requested `--dry-run` validation rehearsal, a malformed RiskId may be passed only to the bundled `scripts/handle_risk.py` with `--dry-run`; the script rejects it locally before any cloud lookup or mutation API call. Quote every argument and never invoke `PreHandleAuditRisk` directly.

4. **Pre-validate HandleDetail safety**
   - Reject `HandleDetail` before execution if it contains shell command indicators, SQL injection indicators, command separators used with executable text, comment markers, command substitution, pipes, or redirection.
   - Ask the user to rewrite the handling description as normal audit text.
   - For an explicitly requested `--dry-run` validation rehearsal, the unsafe text may be passed as one quoted argument only to the bundled `scripts/handle_risk.py`; its local validator must reject the input before any cloud lookup or mutation API call.

5. **Execute through the bundled script only**
   - All handling MUST go through `scripts/handle_risk.py`.
   - Do not write temporary scripts, inline SDK snippets, Aliyun CLI calls, or direct OpenAPI calls to bypass validation.
   - When the user explicitly requests handling and has provided both a `RiskId` and a `HandleDetail`, you MUST actually **execute** `scripts/handle_risk.py` with those arguments — including when the user says the risk may have already been handled. The script itself owns the unprocessed-list pre-check and will report the result. Never substitute the script execution with manual verification (running `query_risk.py` plus inline code to search processed/unprocessed lists) — the expectation is that the bundled script is invoked.
   - The script validates the target is still in the `UNPROCESSED` list before calling `PreHandleAuditRisk`.
   - If the script reports no handleable risk event, the final answer MUST quote the following conclusion **verbatim**: "No handleable risk event found: this RiskId is not in the unprocessed list and may already be processed." This exact sentence guarantees the required keywords: `No handleable`, `RiskId`, `unprocessed list`, and `processed`. Do not paraphrase this conclusion into other wording because paraphrasing may drop the required keywords.
   - After reporting the not-found error, use the current unprocessed risk list printed by the script, present the available `RiskId` values to the user, and ask the user to choose one. Do not handle another risk until the user confirms the new target.

```bash
python3 scripts/handle_risk.py <RiskID> <HandleDetail>
```

### Non-mutating dry-run rehearsal

Use `--dry-run` for evaluation, validation, or shared-account testing. The flag may appear before or after the two positional arguments. Dry-run still performs local validation and confirms that the RiskId is currently in the `UNPROCESSED` list, but it never calls `PreHandleAuditRisk` and never changes risk state.

```bash
python3 scripts/handle_risk.py --dry-run <RiskID> <HandleDetail>
python3 scripts/handle_risk.py <RiskID> <HandleDetail> --dry-run
```

A dry-run result is a rehearsal, not evidence that handling succeeded. Do not report `Handling successful`, fabricate a `RequestId`, or claim that the risk moved to `PROCESSED`.

Example:
```bash
python3 scripts/handle_risk.py 75110196 "Confirmed as false positive, closing this alert"
```

Example output:
```
Handling risk event...
Risk ID: 75110196
Handle Detail: Confirmed as false positive, closing this alert
--------------------------------------------------
✅ Handling successful!
RequestId: C34D813F-A234-5D66-842D-504D84D5C680
```

### Handling Parameter Descriptions

| Parameter | Description |
|-----------|-------------|
| `RiskId` | Risk event ID, obtained from `DescribeRiskRules` API |
| `HandleType` | Handling type, fixed as `Manual` (manual handling) |
| `HandleMethod` | Handling method, fixed as `0` |
| `HandleDetail` | Handling details, **requires user to input specific handling description** |

### Handling Safety Boundaries

- Handle exactly one user-confirmed `RiskId` per handling request unless the user explicitly confirms another target in a later turn.
- Never substitute a different `RiskId` after validation fails or a risk is not found in the unprocessed list. When the target is not found, explicitly report the not-found error to the user, show the current unprocessed risk list and wait for the user to choose a new target.
- Never bypass `scripts/handle_risk.py`; it owns local input validation, unprocessed-list verification, and the exact `PreHandleAuditRisk` request encoding.

## Success Verification

### Verify Query Operation

1. After executing the query code, check if the returned `statusCode` is `200`
2. Check if the returned `body` contains the `Items` list
3. Verify that `TotalCount` matches the actual number of returned records

### Verify Handling Operation

1. After executing the handling code, check if the returned `statusCode` is `200`
2. Call `DescribeRiskRules` again to query the `RiskId` and confirm the status has changed

## Cleanup

Queries and dry-run rehearsals require no cloud cleanup. A live successful handling call persistently changes a risk from `UNPROCESSED` to `PROCESSED`; this skill cannot automatically restore that state.

## API and Command Reference

| Product | API Action | Script | Description |
|---------|------------|--------|-------------|
| Sddp | DescribeRiskRules | `scripts/query_risk.py` | Query security risk events |
| Sddp | PreHandleAuditRisk | `scripts/handle_risk.py` | Handle security risk events |

### Script Usage

| Script | Usage | Description |
|--------|-------|-------------|
| `query_risk.py` | `python3 scripts/query_risk.py [CurrentPage] [PageSize] [HandleStatus]` | Optional pagination and status arguments; defaults to page 1, 20 records, and `UNPROCESSED` |
| `handle_risk.py` | `python3 scripts/handle_risk.py [--dry-run] <RiskID> <HandleDetail>` | Requires Risk ID and handling description; `--dry-run` prevents mutation |

For detailed API information, refer to [references/related-apis.md](references/related-apis.md)

## Best Practices

1. **Paginated Query**: To retrieve all records, re-run `scripts/query_risk.py` with an incremented `CurrentPage` argument until all pages are retrieved
2. **Record RiskId**: The `RiskId` in query results is a required parameter for handling operations, make sure to record it
3. **Handle Description**: Provide a clear `HandleDetail` description when handling for subsequent auditing
4. **Error Handling**: Implement retry mechanisms for temporary errors like `Throttling`
5. **Credential Security**: Use `CredentialClient` to manage credentials, do not hardcode AK/SK

## Reference Links

| Reference Document | Description |
|--------------------|-------------|
| [references/related-apis.md](references/related-apis.md) | API detailed documentation |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission configuration |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
| [Generic Invocation Documentation](https://help.aliyun.com/zh/sdk/developer-reference/generalized-call-python) | Alibaba Cloud Python SDK generic invocation documentation |

## Important Notes

> **Warning**: This skill **only** uses the Data Security Center's `DescribeRiskRules` and `PreHandleAuditRisk` APIs.
> If these two APIs cannot be found, report an error. **Do NOT call other OpenAPIs without authorization**.
> Do not use Alibaba Cloud CLI tools to call APIs.
