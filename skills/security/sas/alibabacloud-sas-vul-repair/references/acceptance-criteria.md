# Acceptance Criteria

Correct/incorrect pattern comparison table for this skill's execution behavior. Each item gives ✅ correct examples and ❌ incorrect examples with reasons, for execution self-checks and result acceptance. Any occurrence of an ❌ pattern fails acceptance — roll back, correct, and re-execute.

## 1. CLI Plugin Mode Naming

Commands must use aliyun CLI plugin mode: `aliyun sas <lowercase-hyphenated-command>`.

✅ **Correct examples:**

```bash
aliyun sas describe-vul-list --type cve --necessity asap --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
aliyun sas modify-operate-vul --type cve --operate-type vul_fix --info '[...]' --from sas --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

❌ **Incorrect examples:**

```bash
aliyun sas DescribeVulList --Type cve          # Wrong: commands and parameters must be lowercase-hyphenated (plugin mode)
aliyun DescribeVulList --Type cve              # Wrong: this is the traditional RPC API mode, not the plugin mode this skill mandates
aliyun sas Describe-Vul-List --type cve        # Wrong: the command name contains uppercase letters and incorrect hyphenation
```

Reason: this skill's execution vehicle is plugin mode; API names convert PascalCase → lowercase-hyphenated (DescribeVulList → describe-vul-list, parameter Type → `--type`). Mixing the two modes makes commands unavailable or behavior inconsistent.

## 2. JSON Format of modify-operate-vul's Info Parameter

Info must be a JSON array string, and each item must contain the complete fields `name`, `uuid`, `tag` (plus `isFront` in Windows scenarios).

✅ **Correct example:**

```bash
aliyun sas modify-operate-vul --type cve --operate-type vul_fix --info '[{"name":"oval:com.redhat.rhsa:def:20172836","uuid":"<server-uuid>","tag":"oval","isFront":0}]' --from sas --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

❌ **Incorrect examples:**

```bash
# Error 1: missing tag field
--info '[{"name":"oval:com.redhat.rhsa:def:20172836","uuid":"<server-uuid>"}]'
# Error 2: not a JSON array (single object)
--info '{"name":"oval:com.redhat.rhsa:def:20172836","uuid":"<server-uuid>","tag":"oval"}'
# Error 3: missing uuid (cannot locate the server)
--info '[{"name":"oval:com.redhat.rhsa:def:20172836","tag":"oval"}]'
# Error 4: tag value outside the enum (anything other than oval/system/cms, e.g., "cve")
--info '[{"name":"...","uuid":"...","tag":"cve"}]'
```

Reason: official documentation specifies Info as a JSON array; the `tag` field only takes `oval` (Linux software vulnerability) / `system` (Windows system vulnerability) / `cms` (Web-CMS vulnerability); `uuid` is the required field for locating the server. Missing fields or format errors cause handling failure. name and uuid must come from describe-vul-list's real response — never hand-assembled.

## 3. Targeted Scan Hard Gate

Targeted scans of **specified servers** can only use `modify-push-all-task` + `--uuids`; `modify-start-vul-scan` is exclusively for full scans.

✅ **Correct example (vulnerability scan of a specified server):**

```bash
aliyun sas modify-push-all-task --uuids <server-uuid> --tasks OVAL_ENTITY,SYSVUL --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

❌ **Incorrect example:**

```bash
# Wrong: using modify-start-vul-scan to scan specified servers
aliyun sas modify-start-vul-scan --uuids <server-uuid> --types cve --user-agent ...
```

Reason: `modify-start-vul-scan` corresponds to the console's "one-click scan" and **triggers a full-account scan** (even when carrying the Uuids parameter), producing scan load on all assets in the account — contradicting the "targeted scan of specified servers" intent. This wording is consistent with the alibabacloud-sas-install-agent skill (HARD GATE). `modify-start-vul-scan` is used only when the user explicitly requests a full scan and confirms.

## 4. --user-agent Observability

Every command calling a cloud API must carry a correctly formatted `--user-agent`.

✅ **Correct example:**

```bash
aliyun sas describe-vul-list --type cve --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

(`<session-id>` is the 32-char lowercase hex string generated at session start; it stays constant within the same session; local commands such as `aliyun configure list`, `aliyun plugin update`, `aliyun version` do not carry it.)

❌ **Incorrect examples:**

```bash
aliyun sas describe-vul-list --type cve          # Error 1: --user-agent omitted
aliyun sas describe-vul-list --type cve --user-agent my-tool   # Error 2: format does not follow the standard prefix
aliyun sas describe-vul-list --type cve --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/   # Error 3: missing session-id
export ALIYUN_USER_AGENT=...                     # Error 4: this skill does not inject UA via exported env vars (not persistent across shell invocations)
```

Reason: `AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/{session-id}` is this skill's invocation observability identifier for call tracking and auditing; this skill does not inject UA via exported env vars (not persistent across shell invocations) — every command explicitly carries `--user-agent`.

## 5. Write Operations Require Prior Confirmation

All write operations (repair, ignore, delete, scan trigger, configuration change, etc.) must first present the change list to the user and obtain explicit confirmation; execution before confirmation is forbidden.

✅ **Correct example (flow):**

```
① Present the change list:
   - Vulnerability: <vulnerability-alias> (<vulnerability-name>)
   - Asset: <instance-name> (UUID: <server-uuid>, IP: <public-ip>)
   - Action: repair (vul_fix); reboot expected not required / required (kernel class)
   - Suggestions: create a snapshot before repair; pay-as-you-go repair is counted only on success
② Ask: "Confirm executing the repair above?"
③ Execute the modify-operate-vul command only after the user confirms
```

❌ **Incorrect example:**

```
User says "fix this vulnerability for me" → immediately execute modify-operate-vul (no change list presented, no reboot/snapshot inquiry, no confirmation)
```

Reason: write operations directly affect the user's asset state (may trigger reboots and billing); you must first present "what changes, which machines are affected, whether a reboot is needed, whether billing applies" and then obtain confirmation; write-operation failures must also not be auto-retried without explanation.

## 6. Never Fabricate API Responses

All results stated to the user must come from real command responses; when there is no data, say so honestly.

✅ **Correct examples:**

```
- Query returns empty VulRecords → "No vulnerability records were found under the current filter conditions (cve + asap + unhandled). The filters can be adjusted (e.g., loosen severity or status) and re-queried."
- Vulnerability details have no UpdateCmd → "The API response for this vulnerability contains no repair command. The official repair suggestion (Solution) original text has been provided — it needs manual evaluation and execution on the server."
```

❌ **Incorrect examples:**

```
- After a query failure or timeout → fabricate "Found 3 high-severity vulnerabilities: CVE-2023-xxxx ..." (the API returned no data)
- Details API errors → output from memory "the repair command is yum update kernel"
- An error code is not in the knowledge table → guess "8009 means yum repository timeout" (official semantics is update process is running)
```

Reason: fabricated responses mislead user decisions and create handling risks. Correct approach: honestly state the query result/failure status; error codes not in the table are dynamically looked up on the official error code page per doc-lookup.md — if not found, explicitly state "there is currently no authoritative interpretation for this error code; submitting a ticket is recommended".

## 7. Repair Type Limitations

emg (emergency), app (application), and sca (software composition analysis) vulnerabilities do not support console repair (vul_fix) — manual repair guidance is mandatory.

✅ **Correct example:**

```
User requests repairing an sca vulnerability →
"This is an application vulnerability (sca type) and does not support console one-click repair.
The official repair suggestion has been obtained for you: the Cves[].Solution original text (upgrade <component> to <version>, or uninstall).
Please handle it on the server per the suggestion — I can then trigger re-verification to confirm."
(emg can additionally be offered modify-emg-vul-submit re-detection guidance)
```

❌ **Incorrect example:**

```bash
# Wrong: calling vul_fix on sca/emg/app type vulnerabilities
aliyun sas modify-operate-vul --type sca --operate-type vul_fix --info '[{"name":"...","uuid":"...","tag":"..."}]' --user-agent ...
```

Reason: official documentation explicitly states emg/app/sca do not support repair operations; OperateVuls only supports Type=cve; the free edition (AuthVersion=1) also has no repair capability. Out-of-bounds calls fail outright or mislead.

## 8. Terminology and Enum Consistency

The three severity systems are used per their respective APIs — mixing is forbidden; enums such as status and type must be stated strictly per the contract wording.

✅ **Correct examples:**

```
- Describing filter parameters: "Filter by repair urgency: necessity=asap (high, fix ASAP)"
- Describing details severity: "This vulnerability's severity level is VulLevel=serious, from the vulnerability details API"
- describe-uuids-by-vul-names scenario: "Filter affected machines by Level=high"
```

❌ **Incorrect examples:**

```
- "Please pass --necessity high to query high-severity vulnerabilities"   # Wrong: the Necessity enum is asap/later/nntf, not high/medium/low
- "Necessity=asap equals VulLevel=serious"                                # Wrong: the two systems have different semantics and cannot be equated
- "Vulnerability status Status=4 means fixed"                             # Wrong: 4=fixing, 7=fixed (status enum 1~12, 20 per the contract table)
```

Reason: Necessity (asap/later/nntf — the console's primary wording), VulLevel (serious/high/medium/low), and Level (high/medium/low) are three systems belonging to different APIs; mixing them leads to wrong parameters or wrong conclusions.

## 9. Credential Security

Only `aliyun configure list` is allowed for checking credential configuration status; never read, echo, or request AccessKey/Secret at any time.

✅ **Correct example:**

```bash
aliyun configure list
```

(--user-agent not needed: local commands do not call cloud APIs and need no UA. Only check whether the profile name/region/credential type is ready; if no valid credential exists, stop and guide the user to configure it outside the session.)

❌ **Incorrect examples:**

```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID            # Wrong: echoing the AK environment variable
cat ~/.aliyun/config.json                    # Wrong: reading a configuration file containing secrets
"Please send me your AccessKey Secret and I'll configure it for you"   # Wrong: requesting secrets in the conversation
aliyun configure set --access-key-id ... --access-key-secret ...   # Wrong: writing credentials in plaintext
```

Reason: credential leakage is the highest-level security risk. This skill's three NEVER rules: never read/echo AK/SK, never request AK/SK in conversation, never configure set in plaintext; credential checks rely solely on `aliyun configure list`'s non-sensitive output.

## Acceptance Checklist

| # | Acceptance Item | Pass Standard |
|---|--------|----------|
| 1 | Command format | All commands are `aliyun sas <lowercase-hyphenated-command>` — no PascalCase, no traditional mode |
| 2 | Info JSON | Repair/verify/ignore commands' Info is a JSON array containing name/uuid/tag (plus isFront for Windows) |
| 3 | Scan gate | Targeted scans use only modify-push-all-task + --uuids; modify-start-vul-scan is full-scan-only and confirmed first |
| 4 | user-agent | Every API command carries `AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>` |
| 5 | Pre-write confirmation | Every write operation has change-list presentation and user confirmation records; no auto-retry after failure |
| 6 | Real responses | All data stated to the user is traceable to specific command response fields |
| 7 | Type limitations | vul_fix never called on emg/app/sca; operate-vuls never called on non-cve |
| 8 | Terminology consistency | Necessity/VulLevel/Level, Status, Type and other enums used per contract wording — no mixing |
| 9 | Credential security | AK/SK never read/echoed/requested throughout; only aliyun configure list used for checks |
| 10 | Forbidden APIs | GetVulFixDetails / ModifyFixVul (nonexistent APIs) never appear throughout |
