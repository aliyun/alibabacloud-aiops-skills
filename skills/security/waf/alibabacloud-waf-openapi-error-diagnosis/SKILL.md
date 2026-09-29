---
name: alibabacloud-waf-openapi-error-diagnosis
description: |
  Diagnose why an Alibaba Cloud WAF OpenAPI call failed: find which request parameter's name, format, value,
  or required-ness disagrees with the official spec, and return a corrected call in the same channel. Covers
  BOTH generations -- WAF 2.0 (version 2019-09-10) and WAF 3.0 (version 2021-10-01) -- across CLI, SDK, and
  raw RPC. Read-only: fetches the authoritative parameter spec and diffs the request; never runs a write
  action and needs no credentials for the core diff.
  Use when a call returns InvalidParameter / MissingParameter / a malformed-parameter error, when parameters
  filled per the docs still fail, when a CLI action is "not available in the current API version", or when
  asked which parameter is wrong.
  Not for: credential/signature, RAM denials, throttling, not-purchased, server 5xx, rule-not-effective, or
  why one request was blocked.
  Triggers: "WAF OpenAPI 报错", "InvalidParameter", "MissingParameter", "参数格式错误",
  "哪个参数错了", "not available in the current API version", "which parameter is wrong"
---

# WAF OpenAPI Error Diagnosis

Answers one precise question: **which request parameter of this WAF OpenAPI call is wrong — by name, format,
value, or required-ness — relative to the official spec, and what is the corrected call.** Works for both WAF
generations under the product code `waf-openapi`:

- **WAF 2.0** — api version `2019-09-10` (domain / CNAME onboarding: `CreateDomain`, `DescribeInstanceInfo`, ...)
- **WAF 3.0** — api version `2021-10-01` (object / template / rule: `CreateDefenseRule`, `DescribeInstance`, ...)

The authoritative parameter spec is **fetched at diagnosis time** from the public OpenAPI metadata endpoint (or
`aliyun ... --help`), never recalled from memory. The core diagnosis is read-only and credential-free.

## ❗ Hard Constraints (highest priority in this document)

> **Decision order is mandatory: classify → resolve blocking identity → diagnose.** Classify from the supplied
> error code before asking questions or running any tool. An out-of-scope code exits through the dedicated
> response contract below. For an in-scope parameter error, an unknown action or any omitted API version is a
> blocking gap: ask and WAIT without a version-specific spec/diff call. The sole pre-confirmation exception is
> an unversioned discovery call for a known cross-generation action; it may only discover candidate versions,
> after which the agent must present both choices and WAIT. Never diagnose against an unconfirmed version.

1. **Pin the version first — and never from the year.** WAF 3.0 is only `2021-10-01`; **WAF 2.0 spans six
   version strings** (`2016-03-10`, `2016-07-18`, `2017-09-30`, `2018-01-17`, `2019-09-10`, `2021-07-27`).
   ⚠️ `2021-07-27` is **WAF 2.0** despite looking like 3.0's `2021-10-01`. The version decides the action set,
   the parameter names, and the value formats, so diagnosing against the wrong version's spec yields a
   confident but wrong answer. Only `2019-09-10` (2.0) and `2021-10-01` (3.0) have **public** parameter docs;
   for the other 2.0 versions the spec source is empty — that is a **doc-coverage gap, not "action does not
   exist"**. **Always pass `--version` explicitly** to the diagnosis script once the version is known. If the
   API version is omitted, **ASK the customer to confirm it and WAIT**. For a known cross-generation action
   (`CreateDomain`, `ModifyDomain`, or `DescribeWafSourceIpSegment`), first run only the unversioned discovery
   command defined below, show both generations, and WAIT. Do not infer even a single-version action silently
   from its name (see `references/version-differences.md`).
2. **The official spec is the only source of truth.** Always fetch the spec for that exact action + version
   (metadata endpoint / `--help`) before declaring any parameter wrong. **Never assert a parameter's
   type/enum/required-ness from memory** — API metadata changes.
3. **Classify before any input collection or tool call.** Only **parameter-class** errors are in scope.
   Credential/signature, RAM permission, throttling, feature-not-purchased/edition, server-side 5xx, and
   transient-state errors are **out of scope**: do not fetch specs, diff params, run CLI, install plugins, or
   inspect the account. `Throttling*` gets a final routing answer without asking for action/version. `Forbidden*`
   / `NoPermission` gets one routing HITL that explicitly asks for both Action/API and version so the RAM skill
   can form least-privilege advice; then WAIT. Never mix these two contracts.
4. **Name the exact offender.** The output must identify the specific parameter and the specific constraint it
   violated (e.g. "`IsAccessProduct` must be integer `0`/`1`, you sent `true`"). Never stop at "some parameter
   is invalid" or "check your parameters".
5. **A well-formed value that references a nonexistent object is not a format bug.** If the shape is correct
   but the `InstanceId` / `TemplateId` / `Resource` does not exist in that region (`*NotExist` /
   `InvalidInstanceId.NotFound`), say so and point at verifying the ID/region — do not "reformat" it.
6. **Return the corrected call in the same channel and version** the customer used (CLI plugin / SDK / raw
   RPC). Change only what the diff flagged. Never silently switch channels; only change the version when the
   version itself was the root cause, and say so.
7. **Read-only and write-safe throughout.** Execute `--cli-dry-run` only when the customer explicitly asks
   for verification. A command that includes `--cli-dry-run` is local shape validation and is permitted — and
   required when requested — even for `Create*` / `Modify*` / `Delete*`. Never send the same write command
   without `--cli-dry-run`. If a live check is truly needed, only a verified-safe `describe-*` read may be sent.
8. **Never fabricate.** Placeholders stay for values the customer did not supply (InstanceId, domain, IPs).
   A failed/empty spec lookup is reported as "not retrieved" with its impact, never read as "the parameter is
   fine" or "the action does not exist".
9. **Never touch credentials.** Do not read, echo, or print AK/SK, and do not ask for them in chat; only
   `aliyun configure list` to check status.
10. **Answer in the customer's language.** A Chinese-language ticket gets a fully Chinese report (root cause +
    corrected call commentary); only CLI flags, parameter names, and error codes keep their original form.

## Architecture

```
Customer: "calling WAF OpenAPI fails with error <Code>"
│
├── Gate: Classify the supplied error code before questions or tools
│     ├── parameter-class (InvalidParameter / MissingParameter / *Invalid / malformed / wrong version) → in scope
│     └── auth / RAM / throttling / not-purchased / 5xx / transient → OUT of scope contract, then stop
│
├── Phase 1: Capture and explicitly confirm action + version; retain params and error evidence
│
├── Phase 3: Fetch the authoritative spec for that exact action + version (metadata endpoint / --help)
│
├── Phase 4 (core): Diff every sent parameter against the spec, across 10 dimensions
│     version · name/style · required · type · enum · format · region value · nested/array · cross-param · nonexistent-id
│
├── Phase 5: Locate the offender(s) → root cause; invoke --cli-dry-run only when explicitly requested
│
└── Phase 6: Emit the corrected call (same channel + version) + a one-line root cause
```

## Scope Boundaries (division of labour with other WAF skills)

| How the customer asks | Which skill |
|-----------------------|-------------|
| **"My WAF OpenAPI call errors — which parameter is wrong?"** | **This skill** |
| "Why is the custom rule I configured not taking effect?" | The rule-effectiveness skill |
| "Why was this request blocked / give me the block reason by trace_id?" | A block-reason lookup skill |
| "SignatureDoesNotMatch / my AK is rejected" | Credential setup (out of scope; route) |
| "Forbidden.RAM / no permission to call the API" | `ram-permission-diagnose` (out of scope; route) |
| "Throttling.User / rate limited" | Back off & retry (out of scope; route) |

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **Preferred (no remote script execution):** download `https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz`
>   (macOS: `aliyun-cli-macosx-latest-{amd64|arm64}.tgz`), `tar tzf` to inspect, `tar xzf`, `sudo mv aliyun /usr/local/bin/`.
> - **Alternative:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Update (CLI >= 3.3.5):** `aliyun upgrade`. Full instructions: `references/cli-installation-guide.md`.

**Pre-check: Aliyun CLI plugin update required**

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
> Both WAF versions live in the `waf-openapi` plugin: `aliyun plugin install --names aliyun-cli-waf-openapi`.
> The plugin **defaults to 2021-10-01 (WAF 3.0)**; a WAF 2.0 action needs `--api-version 2019-09-10`.

**Pre-check: Python 3.8+ required**

> The bundled `scripts/diagnose_openapi_error.py` requires Python 3.8+. No additional pip packages needed —
> it reads the public metadata endpoint with the standard library.

## Authentication

Enter this gate only when the customer explicitly requests an optional live `describe-*` read. Core metadata
lookup, parameter diff, and local `--cli-dry-run` validation do not require credentials and must not be blocked.

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

> **Credential-light note:** the *core* diagnosis — fetching the parameter spec from the public metadata
> endpoint and diffing the customer's parameters — needs **no credentials at all**. Credentials are required
> only for the optional live reproduction of a `describe-*` read action. Never block the diagnosis on missing
> credentials when the answer is already derivable from the spec + the error text.

## RAM Policy

This skill is **read-only** and, for the core diff, permission-free. Credentials/permissions matter only for an
optional live `describe-*` reproduction. Full policy JSON: [references/ram-policies.md](references/ram-policies.md).

| Action | Purpose |
|--------|---------|
| (none) | Spec lookup + diff run against **public** metadata; no RAM permission required |
| `yundun-waf:DescribeInstance` / `DescribeInstanceInfo` | Optional live read reproduction (WAF 3.0 / WAF 2.0) |
| `yundun-waf:DescribeDomains` / `DescribeDefenseRules` / `DescribeDefenseTemplates` | Optional live read reproduction of the failing read action |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Observability (MUST follow for every aliyun command and script)

Upon loading this skill, do BOTH once for the entire session, **before the first cloud call**:
1. Generate a random session ID (32-char lowercase hex string) — use it as `{session-id}`.
2. Read the skill version from `references/manifest.json` (the top-level `version` string field) — use it as
   `{skill-version}`. **Never hardcode the version; always read it from the manifest.**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (`configure`, `plugin`, `version`, `--help`, `--cli-dry-run`) do not reach the cloud API
and are excluded.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-openapi-error-diagnosis/{session-id} skill-version/{skill-version}"
```

Example (session-id `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`, manifest version `1.0.0`):
```bash
aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-openapi-error-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 skill-version/1.0.0"
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation. The UA value
contains a space, so it MUST be quoted.

**Script execution:** inject BOTH values via inline environment variables so the script constructs the same UA
at runtime. The script reads `SKILL_SESSION_ID` and `SKILL_VERSION` from the environment (and falls back to
reading `version` from `references/manifest.json` when `SKILL_VERSION` is absent):

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/diagnose_openapi_error.py --version <2021-10-01|2019-09-10> --action <Action>
```

> The script's spec lookup is a public, credential-free HTTP call to the metadata endpoint; it still sends the
> same `AlibabaCloud-Agent-Skills/.../{session-id} skill-version/{skill-version}` User-Agent for attribution.

## Inputs and Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Never assume or silently default an input the customer did not
> provide. When the failing call's version, action, channel, parameters, and error text are already present in
> the request, treat them as confirmed and **start the read-only diagnosis straight away — do not ask again**.
> Ask only for an input that is genuinely missing or ambiguous, then WAIT.

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| `action` | Required | The API action that failed (PascalCase or CLI kebab-case, e.g. `CreateDefenseRule` / `create-domain`) | None |
| `version` | Required | `2021-10-01` (WAF 3.0) or `2019-09-10` (WAF 2.0); if omitted, obtain explicit confirmation before version-specific diagnosis | None |
| `channel` | Required (inferable) | CLI plugin / SDK / raw RPC / portal — decides the parameter naming rules | Infer from how they pasted the call |
| `params` | Required, values may be redacted | Preserve supplied keys and redaction markers in the diff; a redacted value is non-blocking | None |
| `error_code` / `error_message` | Code required; message non-blocking | The exact code drives classification; a truncated/missing message must not delay diagnosis | None |
| `request_id` | Optional | For the OpenAPI diagnosis portal when the message is ambiguous | None |
| `region` | Optional | `cn-hangzhou` or `ap-southeast-1` — needed only for a live read reproduction | Read from the call |

## Workflow

> **[MUST] Apply the first matching gate and do not blend gates:**
> 1. **`Throttling*` → final route and STOP.** Make no tool call and ask for neither action nor version.
> 2. **`Forbidden*` / `NoPermission` → RAM routing HITL and STOP.** Make no tool call; in one sentence ask for
>    both the Action/API name and API version, solely for least-privilege RAM advice.
> 3. **Other out-of-scope code → final route and STOP.** Make no tool call and perform no parameter analysis.
> 4. **In-scope + action missing → ASK and WAIT.** Run no script.
> 5. **In-scope + version missing → ASK and WAIT.** Run no version-specific script. For `CreateDomain`,
>    `ModifyDomain`, or `DescribeWafSourceIpSegment`, first run only canonical discovery call #0 below, then show
>    both WAF choices and WAIT. For every other action, ask directly without a discovery/spec/diff call.
> 6. **In-scope + action/version known →** run canonical calls #1 and #2. A missing/truncated error message or a
>    redacted parameter value is non-blocking: preserve what was supplied, run both calls, and report the limit.

> **[MUST — observable two-command sequence after version confirmation]** On the current turn or a resumed HITL
> turn, invoke call #1 and call #2 as two separate command-tool actions, in that order. Call #2 fetching metadata
> internally does not satisfy call #1. Never jump directly from a version choice to call #2 or to the report.

> **[MUST — resumed WAF 3.0 `CreateDomain` dry-run path]** If the previous turn offered both WAF versions and the
> customer now selects WAF 3.0 / `2021-10-01` and requests dry-run validation, finish all four steps in this same
> turn: (1) standalone call #1 with `--version 2021-10-01 --action CreateDomain` and no `--params`; (2) call #2
> with the customer's JSON after `--params`; (3) one command-tool invocation beginning exactly
> `aliyun waf-openapi create-domain` and containing `--cli-dry-run`; (4) a final answer containing the literal
> strings `CreateDomain` and `dry-run` plus the actual dry-run outcome. Missing required values use quoted
> placeholders and must never cause step 1 or step 3 to be skipped.

### Phase 1: Capture the failing call

After applying the out-of-scope gates, collect `version`, `action`, `channel`, exact `params`, `error_code`,
`error_message`, and optional `request_id`. Parse pasted calls instead of asking again. For an in-scope error,
`action` and `version` are blocking; ask and WAIT as gate 4/5 requires. A missing/truncated message and redacted
values are non-blocking: do not ask the customer to reveal them and do not wait; continue with the supplied code,
keys, and redaction markers.

### Phase 2: Classify the error

Map `error_code` with [references/error-code-map.md](references/error-code-map.md):
- **Parameter-class (in scope):** `InvalidParameter[.Name]`, `MissingParameter[.Name]`, `InvalidParameter.Format`,
  `*.Malformed`, `10900`, `AclParamError`, `Defense.Control.InvalidParameter`, `Defense.Control.*Invalid`,
  `*NotEmpty`/`*IpEmpty`, `Cert*Error`, cross-param dependency codes, **and wrong-version errors**
  (`api not found` / "not available in the current API version"). → continue.
- **Out of scope:** `SignatureDoesNotMatch` / `InvalidAccessKeyId.*` (credential), `Forbidden*` / `NoPermission`
  (RAM), `Throttling*` (rate limit), `InvalidApi.NotPurchase` / `*NotSupport*` / `ComboError` (edition),
  `InternalError` / `11001` / `500` (server), `*InOperation` / `*TooFrequent` (transient). → use exactly one
  applicable contract below and stop.

For a Chinese ticket, keep these response contracts concise and preserve the listed terms:
```text
Throttling.User 属于限流、非参数、out-of-scope。请检查 API 调用频率、配额与并发，并采用退避重试。
Forbidden.RAM 属于 RAM 权限、非参数、out-of-scope；请提供 Action/接口名和 API version/版本，以便转交 ram-permission-diagnose 生成最小权限建议。
```
The throttling response is final: do not ask any question and do not mention spec lookup, parameter comparison,
or phases. The RAM response is the only out-of-scope branch that waits for Action and version; do not run any
command before or after that question in this skill.

### Phase 3: Fetch the authoritative spec (canonical calls #0 and #1)

**Call #0 — discovery, only for a known cross-generation action whose version was omitted:**
```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/diagnose_openapi_error.py --action <CreateDomain|ModifyDomain|DescribeWafSourceIpSegment>
```
Do not add `--version` or `--params`. After the script reports multiple versions, make no further call and reply:
```text
CreateDomain 同时存在于 WAF 2.0（2019-09-10）和 WAF 3.0（2021-10-01）。请选择版本：WAF 2.0 或 WAF 3.0。
```
Substitute the actual action, then WAIT. In this choice reply, do not discuss how a version might otherwise be
inferred or selected; state only the two choices and the request to choose. If the omitted-version action is not
one of the three listed above, run no discovery and reply instead:
```text
DescribeDomains 的 API version/版本号尚未提供。请确认版本：WAF 3.0（2021-10-01）或 WAF 2.0（2019-09-10）。
```
Substitute the actual action and WAIT.

**Call #1 — spec fetch after version confirmation.** Run this exact shape: literal env prefix, `--version`
before `--action`, relative script path, and no `--params` (the diff is separate call #2):
```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/diagnose_openapi_error.py --version <2021-10-01|2019-09-10> --action <Action>
```
- `{skill-version}` = the `version` read from `references/manifest.json`; both env vars must be present and
  non-empty. Keep `scripts/diagnose_openapi_error.py` relative (no `./`). Keep the flag order
  `--version … --action …`. Add `--channel cli` only **after** `--action <Action>` if you need CLI flag names.
- Equivalent raw sources: the metadata endpoint
  `https://api.aliyun.com/meta/v1/products/waf-openapi/versions/{version}/apis/{Action}/api.json`, or
  `aliyun waf-openapi <kebab-action> [--api-version 2019-09-10] --help`.

Read the exit-`2` messages — three distinct root causes, and **do not loop retrying versions**:
- **`api not found`** for the version the customer named → either a wrong version (confirm once against the
  other generation) **or a genuinely nonexistent / non-public action**. If the other generation also returns
  `api not found`, conclude **"action not found / NO public API docs"**, still run the Phase 4 diff call for
  the record, then fall back to the manual dimensions and report — never invent a spec.
- **`exists in MULTIPLE documented versions`** from call #0 → show both choices exactly as above and WAIT;
  make no version-specific call until the customer answers.
- **`version <v> has NO public API docs`** → a legacy WAF 2.0 version (e.g. `2021-07-27`); it is a
  **doc-coverage gap, not a missing action** → re-fetch with `--version 2019-09-10`.

### Phase 4 (core): Diff every parameter against the spec (canonical call #2 — WITH `--params`)

This is a **separate second call**. Same env prefix and `--version … --action …` order, with `--params`
**immediately after** `--action <Action>` (nothing between them):

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/diagnose_openapi_error.py --version <2021-10-01|2019-09-10> --action <Action> --params '<the customer's params as a JSON object, PascalCase API-level keys>'
```
A value such as `***`, `<redacted>`, or `[redacted]` is a **non-blocking redaction marker**. Keep that literal
marker in the JSON, run call #2 immediately, and do not request the secret value. The final report must identify
the redacted parameter and state that only its content/format could not be fully checked; all names, required
fields, non-redacted values, and error-code evidence were still checked.

If explicit-version call #1 exited `2` specifically for api-not-found/no-public-docs, still issue call #2 for
the record, then use the manual dimensions. **Never** issue call #2 after discovery call #0 or any
`NEEDS_CONFIRMATION` result; wait for the customer's version choice first. The script reports
`unknown_param` / `missing_required` /
`type_mismatch` / `enum_violation`. Cross-check its output manually against the **10 diff dimensions** in
[references/parameter-spec-lookup.md](references/parameter-spec-lookup.md) — the script does not judge
format-of-JSON-string, region-value, nested notation, or cross-parameter dependencies, so the agent must:
1. **Version** — action belongs to this version (Phase 3).
2. **Name & style** — CLI flags are lowercase-hyphen and the region flag is `--biz-region-id` (not
   `--region-id`); SDK/raw names are PascalCase (`RegionId`). A case/style typo → unknown flag or ignored param.
3. **Required present** — every `required:true` param is supplied.
4. **Type** — WAF 2.0 booleans are integers (`IsAccessProduct=1`, not `true`); integers vs lists vs strings.
5. **Enum value** — value within the documented set (`DefenseScene`, `DefenseType`, `AccessType`, ...).
6. **Format** — JSON-string params (`Rules`, `Template`, `conditions`), port/IP list strings, cert PEM, time.
7. **Region value** — `RegionId`/`--biz-region-id` ∈ {`cn-hangzhou`, `ap-southeast-1`} only.
8. **Nested / array notation** — SDK `Parent.N.Child`; CLI discrete flags vs a JSON blob.
9. **Cross-parameter dependency** — e.g. `HstsPreload=true` ⇒ `HstsIncludeSubDomain=true`.
10. **Well-formed but nonexistent** — correct shape, absent object → not a format bug (constraint 5).

**Evidence priority:** an error code/message that names a parameter and constraint outranks generic missing-field
findings from a partial pasted request. For example, `InvalidDomain.Format`, `InvalidListen.Json`, and
`InvalidLogStore.Format` must lead with `Domain`, `Listen`, and `LogStore` respectively and explicitly call the
problem a format defect. Report other diff findings separately; do not replace the server-named root cause with
the first required field omitted from the user's abbreviated prompt.

### Phase 5: Reproduce with `--cli-dry-run` (strict binary gate)

**[MUST] Inspect the customer's verification intent immediately before Phase 5:**
- Explicit request to verify/validate/run dry-run → invoke exactly one CLI command through the command tool.
  Merely printing or recommending the command does not satisfy the request. This local dry-run is allowed for
  write-named actions; `--cli-dry-run` must be present in the command actually invoked.
- Any explicit refusal, including "direct report", "no verification", or equivalent → skip Phase 5 completely.
  Do not invoke, propose, or mention a dry-run in the final report.
- No explicit preference → do not run it.

For the requested branch, execute the corrected shape with supplied values and clearly quoted placeholders for
other required values; report the actual local validation outcome without claiming a cloud write occurred:
```bash
aliyun waf-openapi <kebab-action> [--api-version 2019-09-10] <corrected flags> --cli-dry-run \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-openapi-error-diagnosis/{session-id} skill-version/{skill-version}"
```
For `CreateDomain` on WAF 3.0, the required command shape is:
```bash
aliyun waf-openapi create-domain --domain test.com --instance-id "<InstanceId>" --cli-dry-run
```
For `ModifyLogService`, begin with `aliyun waf-openapi modify-log-service` and include `--cli-dry-run`. Invoke the
requested dry-run even when values need quoted placeholders, metadata returned api-not-found, or CLI help is
unavailable; those conditions affect the reported outcome, but never justify skipping the command.
Only a `describe-*` read may ever be executed live (credentials configured outside the session, `--user-agent`
attached, `sleep 0.3` between calls). See [references/verification-method.md](references/verification-method.md).

### Phase 6: Deterministic output contract

For every completed in-scope diagnosis, repeat the exact Action and exact error code from the request. A code
ending in `.Format` or `.Json` must use the literal Chinese term `格式` when the ticket is Chinese. For a Chinese
ticket, use this structure and preserve the labels shown:
```text
Action：{exact Action}
错误码：{exact error code}
版本：{WAF 2.0（2019-09-10）or WAF 3.0（2021-10-01）}
根因：{exact parameter} 的{类型/取值/必填项/格式}不符合规范；期望{constraint}，实际为{safe value or 脱敏}。
修正：{same-channel corrected call; change only flagged items; placeholders for missing values}
验证：{only if requested: dry-run 验证已执行，结果为 <actual outcome>}
限制：{only when applicable: spec not retrieved, missing message, or redacted values and their impact}
```
Before sending, perform this **[MUST] literal-token gate** on the final answer:
- Every completed diagnosis contains the exact Action, the exact error code, and the literal label `修正`.
- `CreateDomain` + `InvalidDomain.Format` contains all three exact strings `CreateDomain`,
  `InvalidDomain.Format`, and `修正`; a Chinese report names `Domain` as a `格式` defect.
- Requested dry-run contains both exact strings `CreateDomain` (or the actual Action) and `dry-run` plus the
  command's actual outcome. Refused or unrequested verification contains no dry-run mention.
Do not send the answer until every applicable token is present. If a value was redacted, include this sentence
in `限制`:
```text
Certificate 的值已脱敏；这是非阻塞缺口。已继续执行参数 diff，但无法完整验证该值的内容和格式。
```
Substitute the actual parameter name. If verification was not explicitly requested, omit the entire verification
line and do not mention dry-run anywhere. If it was requested, include the exact Action plus both `dry-run` and
`验证`, and report what the invoked command actually returned. Keep the customer's language and channel; never
invent a successful result, spec, parameter value, or cloud write.

## Diagnosis Script

**After explicit version confirmation, use two canonical calls per diagnosis**, both with the literal env
prefix (`SKILL_SESSION_ID` + `SKILL_VERSION`, the version read from `references/manifest.json`), the relative
path `scripts/diagnose_openapi_error.py`, and the flag order `--version … --action …`. Copy these shapes exactly.
Do not use an unversioned script call except call #0 for the three cross-generation actions listed in Phase 3.

```bash
# Call #1 — spec fetch (NO --params)
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/diagnose_openapi_error.py --version 2021-10-01 --action CreateDefenseRule

# Call #2 — diff (--params immediately after --action)
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/diagnose_openapi_error.py --version 2019-09-10 --action CreateDomain --params '{"Domain":"www.example.com","InstanceId":"waf_x","IsAccessProduct":true}'

# Add --json for programmatic output (keep it AFTER --params)
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/diagnose_openapi_error.py --version 2021-10-01 --action DescribeInstance --params '{"RegionId":"cn-beijing"}' --json
```
Do **not** drop `--version` (the flow always passes it explicitly); do **not** insert other flags between
`--action <Action>` and `--params`. Exit codes:
- `0`: params match the documented spec (if the call still failed → not a format bug; check constraint 5 / re-classify)
- `1`: at least one parameter problem located (`findings[]` names param + kind)
- `2`: one of three version/spec conditions, each a distinct root cause — **action not in that version**
  (wrong version), **action in multiple versions** (ambiguous → ask), or **version has no public docs**
  (legacy WAF 2.0 → use `2019-09-10`); also a genuine spec fetch/network error

> Script output is **evidence, not judgement**: it flags name/required/type/enum mechanically. Format of a
> JSON-string param, region-value validity, nested notation, and cross-parameter dependencies are the agent's
> job (Phase 4, dimensions 6–9). Never read "no findings" as "the call is correct".

## Rate Limiting

WAF openapi throttling limit: **5 calls/second per uid** (only relevant to optional live read reproduction).
- Insert `sleep 0.3` (300ms) between every live `aliyun` API command.
- On throttling error (`Throttling.User` / HTTP 429): that is **out of scope** — advise backoff (2s → 4s → 8s),
  do not treat it as a parameter problem.

## Security Constraints

- Read-only diagnosis. A write-named CLI command is allowed only with `--cli-dry-run` when verification was
  explicitly requested. Never invoke a `Create*` / `Modify*` / `Delete*` WAF action without that flag.
- Never read, echo, print, or ask for AK/SK or STS tokens; only `aliyun configure list` to check status.
- Access resources in the customer's own account only; never query across accounts.
- Placeholders for user-specific values (InstanceId, domain, IPs, ports); never fabricate them.

## Cleanup

No cloud resources are created. Delete any temporary file the diagnosis produced (e.g. a saved `--params`
JSON or a dry-run dump). No WAF configuration is changed by this skill.

## Best Practices

1. Pin the version first, never from the year — WAF 2.0 spans six versions (`2021-07-27` is 2.0, not 3.0);
   a wrong-version call is a root cause, not a value typo, and an action in both generations must be confirmed.
2. Fetch the spec for the exact action + version; never diagnose from memory.
3. Classify the error code before touching parameters; route non-parameter errors out.
4. For CLI, remember flags are lowercase-hyphen and the region flag is `--biz-region-id`.
5. Watch the classic value traps: WAF 2.0 integer-booleans, JSON-list-string ports/IPs, WAF 3.0 JSON-string `Rules`,
   and the two-region `RegionId` limit.
6. Name the exact parameter + constraint; a server-named field outranks missing fields from a partial prompt.
7. Return the corrected call in the same channel and version, changing only what was flagged.
8. When explicitly requested, invoke `--cli-dry-run`; otherwise omit it entirely. Never send a live write.
9. A well-formed value referencing a nonexistent object is not a format bug — verify the ID/region.
10. Leave placeholders for unknown values; mark an unfetchable spec "not retrieved" with its impact.

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/scenario-description.md](references/scenario-description.md) | Scenario, workflow decomposition, and knowledge sources |
| [references/error-code-map.md](references/error-code-map.md) | Error code → parameter-class vs out-of-scope, and how to read the culprit from the message |
| [references/version-differences.md](references/version-differences.md) | WAF 2.0 vs 3.0: actions, `--api-version`, cross-channel parameter naming, value traps |
| [references/parameter-spec-lookup.md](references/parameter-spec-lookup.md) | Authoritative spec sources and the 10 diff dimensions |
| [references/corrected-call-templates.md](references/corrected-call-templates.md) | Corrected-call templates for CLI (both versions), SDK, and raw RPC |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification method and pass criteria |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria: correct / incorrect patterns |
| [references/ram-policies.md](references/ram-policies.md) | Read-only / credential-light RAM policy JSON |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and upgrade guide |
