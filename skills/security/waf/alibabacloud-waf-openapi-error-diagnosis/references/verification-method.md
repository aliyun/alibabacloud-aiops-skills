# Verification Method: WAF OpenAPI parameter diagnosis

Step-by-step method and pass criteria. This skill is **read-only and credential-light**: the core diagnosis
(spec lookup + diff) uses the public metadata endpoint and needs no AK/SK. Only an optional live reproduction
of a *read* action touches the cloud API.

> Every `scripts/diagnose_openapi_error.py` invocation below carries the observability env vars
> `SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version}` (the version is supplied by the Agent — see the
> Observability section in SKILL.md); they are omitted from the examples for brevity. Every live `aliyun` command
> carries the matching `--user-agent ".../{session-id} skill-version/{skill-version}"`.

## Step 0: Capture the failing call

Classify the supplied error code before collecting missing inputs. For an in-scope parameter error, collect:
- Explicitly confirmed WAF version / generation (`2019-09-10` = 2.0, `2021-10-01` = 3.0); never silently infer it from the action.
- Action name, and the **channel** (CLI plugin / SDK / raw RPC / portal).
- The exact parameter names and supplied values; preserve redaction markers without requesting secret content.
- The exact error `Code`; a truncated/missing `Message` and absent `RequestId` are non-blocking.

**Pass criteria**: version, action, channel, params, and error code are known. If action or version is missing, ask
and wait before version-specific diagnosis. Missing message text or redacted values do not block the safe diff.

## Step 1: Classify the error

Map the `Code` to a class using the error-code map (linked from SKILL.md).

**Pass criteria**: parameter-class → continue. For `Throttling*`, give final rate-limit guidance without
asking for action/version or running tools. For `Forbidden*` / `NoPermission`, identify RAM/out-of-scope and
ask for both Action and version solely for least-privilege routing, then wait without running tools. Other
non-parameter classes → state the class, route, and stop.

## Step 2: Fetch the authoritative spec

```bash
python3 scripts/diagnose_openapi_error.py --version <2021-10-01|2019-09-10> --action <Action>
# CLI channel: also validate flag names
python3 scripts/diagnose_openapi_error.py --version <version> --action <Action> --channel cli
```

**Pass criteria**: a real parameter spec is returned. If the script exits `2` with `api not found`, the action
does not exist in that version → the root cause is the **wrong version**; retry the other version to confirm.

## Step 3: Diff the sent params against the spec

```bash
python3 scripts/diagnose_openapi_error.py --version <version> --action <Action> \
  --params '<the customer's params as a JSON object, PascalCase keys>'
```

**Verification points** (cross-check the script output manually against the 10 diff dimensions in the
parameter-spec lookup reference):
- exit `1` → the `findings` list names the offending parameter(s) and the kind
  (`unknown_param` / `missing_required` / `type_mismatch` / `enum_violation`);
- exit `0` → params match the documented spec; if the call still failed, the value is semantically wrong
  (a nonexistent ID) or the error is not parameter-class — re-check Step 1 and dimension 10;
- the region flag/name and the version are confirmed correct for the channel.

## Step 4: Reproduce safely (strictly conditional, CLI only)

Only when the customer explicitly requests verification, invoke the corrected shape with `--cli-dry-run`.
A write-named command is safe in this local mode; never invoke it without the dry-run flag. If verification is
refused or not requested, skip this step and omit any dry-run mention from the final answer.
```bash
aliyun waf-openapi <kebab-action> [--api-version 2019-09-10] <corrected flags> --cli-dry-run \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-openapi-error-diagnosis/<session-id> skill-version/<skill-version>"
```
For a genuine live check, only a **read** action (`describe-*`) may be executed, with credentials configured
outside the session and `--user-agent` attached.

**Pass criteria**: `--cli-dry-run` prints the request (endpoint + params) with no `unknown flag` /
`InvalidParameter` client-side error.

## Step 5: Emit the corrected call + explanation

**Pass criteria**:
- One sentence names the exact offending parameter and the exact constraint it violated.
- The corrected call is in the **same channel and version** the customer used, changing only flagged items.
- Placeholders remain for values not supplied; nothing is fabricated.
- Response is in the customer's language.

## Overall success criteria

| Result | Ruling |
|--------|--------|
| Offending parameter located + corrected call accepted (error gone) | Success |
| Action not found in the given version | Root cause = wrong version; corrected call adds/switches `--api-version` / SDK `version` |
| Params match spec but call still errors | Not a format bug: verify the referenced ID/region exists, or re-classify the error code |
| Error is auth / RAM / throttling / not-purchased / server-side | Out of scope: name the class and route; do not alter parameters |
| Version or offending parameter cannot be determined | Ask for the missing input; never invent a root cause |
