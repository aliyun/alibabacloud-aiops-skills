# External-Network Fallback Execution Manual (use only when intranet is unavailable)

> This document is **functionally equivalent** to the SKILL.md primary path. Use it **only** when the external environment cannot reach `cli.aliyun-inc.com`.
> **Do not** take this path while the primary plugin is functional.

---

## When to Enter This Path

Switch to this path if any of the following holds:

- §1.3 install command reports `lookup cli.aliyun-inc.com: no such host` / `connection timeout`
- The current environment is a public sandbox / external CI/CD / non-Alibaba-employee environment with confirmed inability to reach the Alibaba intranet or VPN
- `nslookup cli.aliyun-inc.com` returns nothing

---

## ⚠️ Required Constraints

| Item | Description |
|---|---|
| API status | `SubmitIntent` visibility in the Alibaba Cloud metadata center is still **private** |
| SLA | **Alibaba Cloud does not guarantee an SLA for this invocation pattern**; it may change at any time |
| Scope | Use as a fallback only; for production paths, restore the primary path (intranet access) first |
| Gateway | `dyvmsapi.aliyuncs.com` (resolvable on public DNS; no intranet required) |
| Authentication | Alibaba Cloud standard RPC v1.0 signature (HMAC-SHA1) |
| Plugin mutual exclusion | The public-release and intranet-online builds of `aliyun-cli-dyvmsapi` share the same name and are mutually exclusive — only one can be installed at a time. **Install the intranet-online build whenever possible** (it ships both SubmitIntent and QueryCallDetailByCallId); fall back to the public-release build only when the intranet-online install fails (loses SubmitIntent; the script fills the gap) |

---

## 0. Prerequisite Checks (one-shot)

```bash
# Note on --user-agent scope: only BUSINESS `aliyun ...` calls (e.g.
#   `aliyun dyvmsapi submit-intent ...`,
#   `aliyun dyvmsapi query-call-detail-by-call-id ...`)
# accept and MUST carry
#   --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
# System / tooling commands (`aliyun version`, `aliyun configure ...`,
# `aliyun plugin ...`, any `aliyun ... --help`) DO NOT accept this flag and MUST NOT
# carry it; passing it raises `unknown flag: --user-agent`. `python3 ...` is not an
# `aliyun` call and is not affected.

# 1) Python 3.6+ (preinstalled on macOS/Linux) — required by step 2 (script-based SubmitIntent)
python3 --version

# 2) Script available — used for SubmitIntent only
python3 scripts/dyvmsapi_rpc.py --help

# 3) Credential-injection helper available (auto-injects env from the aliyun CLI current profile)
python3 scripts/run_with_aliyun_creds.py --check
# Expected output: `OK profile=default mode=AK ready for auto-injection`
# If the helper reports an unsupported mode (exit 3), see §1 for alternatives.

# 4) aliyun CLI is available (read-only check; do NOT install plugins here — plugin install is performed in step 4 of §4)
aliyun version

# 5) Public-network reachability
curl -sS -o /dev/null -w "HTTP %{http_code}\n" https://dyvmsapi.aliyuncs.com/
# Expected: any HTTP 4xx (calling the gateway with no parameters; 4xx still confirms the gateway is reachable)
```

If any of the checks fails, the external fallback cannot be used; inform the user.

---

## 1. Credentials — Default Auto-Injected from the Current Profile

> **Design (consistent with SKILL.md §2.2)**: the external script path reuses the user's already-configured `aliyun configure` current profile. The helper `scripts/run_with_aliyun_creds.py` reads AK/SK from the current profile in `~/.aliyun/config.json` (also reading `sts_token` for `StsToken` mode), injects them as `ALIBABA_CLOUD_ACCESS_KEY_ID` / `_SECRET` / `_SECURITY_TOKEN`, then exec's the subcommand. The script `dyvmsapi_rpc.py` reads from env and signs with them as public parameters. Credential values are **never persisted**, **never appear in debug output**, and **never appear as subcommand arguments**.

**Supported modes**: `AK` / `StsToken`.

**Unsupported modes** (`RamRoleArn` / `EcsRamRole` / `OAuth` / `External` / `CredentialsURI` / `ChainableRamRoleArn`, etc.): the helper exits 3. Options:
- **Return to the primary path** (recommended): the aliyun CLI natively supports all modes.
- **Create a new AK profile**: `aliyun configure --profile call-by-tts --mode AK`, then specify `--profile call-by-tts`.
- **Manual AssumeRole**: have the user obtain temporary AK/SK/STS themselves, then `export ALIBABA_CLOUD_ACCESS_KEY_ID/_SECRET/_SECURITY_TOKEN` and invoke `dyvmsapi_rpc.py` directly (without the helper).

### 1.1 [MUST] Standard Invocation Pattern

```bash
# Step 1: Pre-check that the current profile is usable
python3 scripts/run_with_aliyun_creds.py --check
# Expected: `OK profile=<name> mode=<AK|StsToken> ready for auto-injection`

# Step 2: Tell the user which profile will be used (transparency; no credential values)
python3 scripts/run_with_aliyun_creds.py --print-profile
# Output e.g. `profile=default mode=AK region=cn-hangzhou`
# The agent MUST say explicitly: "I will call SubmitIntent using profile=<name> mode=<mode> region=<region> — proceed?"

# Step 3: Make the actual call (helper injects env into the subprocess)
python3 scripts/run_with_aliyun_creds.py -- \
  python3 scripts/dyvmsapi_rpc.py SubmitIntent -P UserMessage="<the user's intent>"
```

### 1.2 [MUST] Security Rules

- Strictly forbidden: `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` / `echo $ALIBABA_CLOUD_SECURITY_TOKEN` in the conversation
- Strictly forbidden: passing literal credential values on the command line (e.g. `--access-key-id LTAI...`) — they would be recorded in shell history
- Strictly forbidden: passing `SecurityToken` as a business parameter via `-P SecurityToken=...` — it is a public parameter; the script automatically reads it from env and includes it in the signature

### 1.3 [FORBIDDEN] Agent Red Lines

- **Strictly forbidden to bypass the helper and extract credentials by hand**: do not write agent code that does `cat ~/.aliyun/config.json` / `json.load(...)` / `subprocess.run(['python3','-c','...'])` to manually extract credentials and splice them into script arguments. Three common pitfalls follow:
  1. Hardcoding `profiles[0]` instead of reading `current` → wrong profile
  2. Missing `sts_token` for `StsToken` mode → `MissingSecurityToken`
  3. Splicing credentials into subcommand arguments leaks them into debug output / `ran_scripts` / `outputs` / accidental logs
  The helper handles all three for you.
- **Strictly forbidden to write credentials into any file**: AK/SK/STS values are not allowed in `ran_scripts/*.sh` / `outputs/*.md` / `*.log` / any git-visible file — placeholder comments such as `# --access-key-id <from-config>` / `# AK=<masked>` are also forbidden (they mislead readers). What you may record is the invocation form `python3 scripts/run_with_aliyun_creds.py -- python3 scripts/dyvmsapi_rpc.py ...`.
- **Strictly forbidden to revert to legacy patterns**: do not advise the user to run `read -s ALIBABA_CLOUD_ACCESS_KEY_ID && export ...`. Cross-process shell env cannot be propagated to an agent subprocess; this approach is technically infeasible.

### 1.4 Special Cases (helper may be skipped only here)

| Scenario | Handling |
|---|---|
| User explicitly says "do not use my default profile" | Ask which named profile to use; specify it via `--profile <name>` |
| Profile mode is `RamRoleArn` / `EcsRamRole` / etc. (unsupported by the helper) | The user manually performs AssumeRole / metadata-service exchange to obtain temporary AK/SK/STS, then `export ALIBABA_CLOUD_ACCESS_KEY_ID/_SECRET/_SECURITY_TOKEN` in the current shell, then invokes `python3 scripts/dyvmsapi_rpc.py ...` directly (without the helper). **This case requires the user to run the script in their own shell** — same-process env reads are fine; if the agent invokes the script via a subprocess instead, cross-process env still cannot propagate (same red line as §1.3 #3). For agent scenarios, return to the primary path or create a new AK profile |
| `~/.aliyun/config.json` does not exist in CI/CD or sandbox environments | The orchestrator injects `ALIBABA_CLOUD_ACCESS_KEY_ID/_SECRET/_SECURITY_TOKEN` env before launching the agent; the script reads them from env |

---

## 2. RAM Permissions

Identical to the primary path: requires `dyvms:SubmitIntent` and `dyvms:QueryCallDetailByCallId`. The full policy is in the reference document [ram-policies.md](./ram-policies.md).
Permission-error handling is identical to SKILL.md §3.

---

## 3. Address-Book Prerequisite

Identical to the primary path: the user must complete phone-number ownership verification and tag binding in the **Alibaba Cloud Voice Service console**. See SKILL.md §4 for details.

---

## 4. Core Workflow (External Edition)

> Step-for-step parity with SKILL.md §6. **The only difference is in step 2**: in the public-release CLI plugin `SubmitIntent` visibility=private and is not exposed, so it must go through the script `python3 scripts/dyvmsapi_rpc.py SubmitIntent`. Step 4 `QueryCallDetailByCallId` visibility=public, so it **still uses the CLI** (`aliyun dyvmsapi query-call-detail-by-call-id`).
> AI-Mode: enabled once at the start in SKILL.md §1.1.1 and **MUST** be disabled at every exit point of this Skill (success / failure / early STOP), regardless of whether the path uses the script or the CLI.

### Step 1: Extract User Intent

Extract who to call and what to convey from the user's message. If already clear, proceed directly — no confirmation needed. **Identical to the primary path** (see SKILL.md §6 Step 1 for full rules).

### Step 2: Initiate the Smart Call

```bash
python3 scripts/run_with_aliyun_creds.py -- \
  python3 scripts/dyvmsapi_rpc.py SubmitIntent \
    -P UserMessage="<user-confirmed natural-language intent>"
```

> **Notes**:
> - The parameter Key MUST be **PascalCase** (`UserMessage`, not `user-message`). This is the public gateway's native naming, distinct from the CLI subcommand's kebab-case.
> - `run_with_aliyun_creds.py` extracts AK/SK from the current profile (and `sts_token` for `StsToken` mode) and injects them into the subprocess env; the subprocess `dyvmsapi_rpc.py` reads from env and signs. See §1.
> - Strictly forbidden: invoking `python3 scripts/dyvmsapi_rpc.py ...` directly without the helper (it will report `[ERROR] AK/SK not provided`). Strictly forbidden: bypassing the helper to pass credentials via `--access-key-id` / `-P SecurityToken=...`. Special cases are listed in §1.4.

### Step 3: Parse the Response

The script outputs the raw gateway JSON; the structure is identical to the CLI's:

```json
{
  "Code": "OK",
  "Message": "OK",
  "Success": true,
  "RequestId": "...",
  "Model": {
    "Tag": "<matched contact tag>",
    "CallContent": "<AI-generated playback text>",
    "CallId": "1779786101083^9876543210"
  }
}
```

Decision rules are identical to the primary path:
- `Code == "OK"` and `Success == true` → the call has been initiated
- Show `Model.Tag` / `Model.CallContent` / `Model.CallId` to the user
- **The response does not return the dialed number** (phone-number safety constraint)

Exit codes: `0` = success; `2` = `Code` is not OK; `1` = network/HTTP error.

The full error-code table is in the reference document [related-commands.md](./related-commands.md).

### Step 4 (Optional): Query the Call Result

> **On the external path, this step still uses the CLI**. `QueryCallDetailByCallId` visibility in the metadata center is **public**; the public-release `aliyun-cli-dyvmsapi` plugin already includes the subcommand. The script handles SubmitIntent only; CDR queries still use the CLI (in practice the CLI and the script behave identically against this API; the issue is unrelated to the invocation method).

**Install the public-release plugin** (one-time; no `--source-base`. `plugin update` / `plugin install` / `--help` are CLI tooling / help-mode commands and DO NOT accept `--user-agent`):
```bash
aliyun plugin update
aliyun plugin install --names dyvmsapi
aliyun dyvmsapi query-call-detail-by-call-id --help   # Verify the subcommand exists
```

**Query the CDR** (parameter format identical to the primary path — `--query-date` is a **Unix-millisecond timestamp** of type `int`, not a yyyyMMdd string. The front segment of `CallId` is already the millisecond timestamp at which the call was accepted; reuse it directly via shell parameter expansion. **Do not** convert it via `datetime.strftime('%Y%m%d')`):
```bash
CALL_ID="<the Model.CallId from step 2's response>"
# CallId format: <ms-timestamp>^<call-sequence>; take the front segment as QueryDate.
QUERY_DATE="${CALL_ID%%^*}"

aliyun dyvmsapi query-call-detail-by-call-id \
  --call-id "$CALL_ID" \
  --prod-id 11000000300006 \
  --query-date "$QUERY_DATE" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
```

**Hard requirements** (identical to the primary path):
- `--prod-id` MUST be `11000000300006` (Voice Notification product ID)
- `--query-date` must be on the same day as `CallId` (millisecond timestamp)
- CDR write delay: for notification-style calls (typical duration 10–30s), the CDR is generally available **about 40s after the call ends**. If `Code: OK` returns with no `Data`, retry once after another 30–60s. **Do not blindly hard-wait 1–2 minutes**.

**Response fields** (`Data` is a JSON string requiring a second parse) — identical to the primary path; see SKILL.md step 4 for the full table.

**[MUST] Readable presentation**: render in the format defined in SKILL.md step 4. **Do not** dump the raw `Data` string. Mask the number, show the `stateDesc` next to the numeric `state`, and annotate relative time offsets — same as the primary path.

**Troubleshooting**:
- `Code: isp.GATEWAY_ERROR` / `Message: 网元处理调用失败` → common causes:
  1. The current AK is not authorized for `dyvms:QueryCallDetailByCallId`
  2. The account does not match `prod-id=11000000300006` (Voice Notification product not enabled)
  3. The CallId is not yet committed in the CDR system (retry shortly)
  Use the `RequestId` in the response and look it up in the console "CDR Query" page or at `https://api.aliyun.com/troubleshoot?q=isp.GATEWAY_ERROR&product=Dyvmsapi&requestId=<RequestId>` for the precise reason.
- `Code: OK` but no `Data` → CDR not yet committed; retry after another 30–60s.

---

## 5. Primary vs External Path Quick Comparison

| Dimension | Primary path (all CLI) | External fallback (SubmitIntent via script, Query via public CLI) |
|---|---|---|
| SubmitIntent entrypoint | `aliyun dyvmsapi submit-intent` (intranet-online plugin) | `python3 scripts/dyvmsapi_rpc.py SubmitIntent` |
| QueryCallDetailByCallId entrypoint | `aliyun dyvmsapi query-call-detail-by-call-id` (intranet-online plugin) | `aliyun dyvmsapi query-call-detail-by-call-id` (**public-release plugin; no `--source-base`**) |
| Plugin source | `https://cli.aliyun-inc.com/...` (intranet only) | Public-release only (default source) |
| Credentials | `~/.aliyun/config.json` or env vars | CLI part as on the left; the script part is auto-injected by helper `run_with_aliyun_creds.py` from the current profile (supported modes: AK / StsToken) |
| AI-Mode | Enabled in SKILL.md §1.1.1; MUST be disabled at every exit point | Same: enabled once in SKILL.md §1.1.1; MUST be disabled at every exit point |
| Network requirement | `cli.aliyun-inc.com` (intranet) + `dyvmsapi.aliyuncs.com` (public) | `dyvmsapi.aliyuncs.com` (public) only |
| Third-party deps | aliyun CLI + intranet-online plugin | aliyun CLI + public-release plugin + Python 3 |
| SLA | Intranet-online build released alongside Voice Service | SubmitIntent has **no SLA** (visibility=private); Query parity with primary path |

---

## 6. Troubleshooting

| Symptom | Root cause | Fix |
|---|---|---|
| `python3: command not found` | No Python 3 on the system | Install Python 3.6+ (macOS: `brew install python3`; Linux: `apt/yum install python3`) |
| Helper reports `~/.aliyun/config.json does not exist` (exit 1) | The user has never run `aliyun configure` | Have the user run `aliyun configure` first |
| Helper reports `profile '<name>' not found` (exit 2) | `current` field points to a name not present in `profiles` | `aliyun configure list` lists available profiles; specify with `--profile <name>` |
| Helper reports `mode='<X>' is not in the auto-injection supported set` (exit 3) | Profile mode is RamRoleArn / EcsRamRole / OAuth / External, etc. | See §1.4 special cases |
| Helper reports `mode=StsToken but the sts_token field is empty / expired` (exit 4) | STS temporary credential expired | Re-run `aliyun configure --profile <name>` to obtain a new STS |
| Script reports `[ERROR] AK/SK not provided` | `python3 scripts/dyvmsapi_rpc.py ...` was invoked directly without the helper | Switch to `python3 scripts/run_with_aliyun_creds.py -- python3 scripts/dyvmsapi_rpc.py ...` |
| HTTP error `IncompleteSignature` / `SignatureDoesNotMatch` | AK/SK is wrong or disabled; or StsToken expired | Verify / reset in the [RAM Console](https://ram.console.aliyun.com/manage/ak); re-issue STS if expired |
| HTTP body `Code: MissingSecurityToken` | StsToken mode but the script did not receive the token | Invoke through the helper; the helper auto-reads `sts_token` and signs it as a public parameter. **Strictly forbidden** to manually pass `-P SecurityToken=...` |
| HTTP error `InvalidAction.NotFound` | Action name misspelled | Must be PascalCase: `SubmitIntent` / `QueryCallDetailByCallId` |
| `Code` is not OK; business error code | Wrong business parameter | Check the error-code table in the reference document [related-commands.md](./related-commands.md) |
| Gateway returns 502/504 | Gateway transient unavailability | Add `--debug` and retry; if persistent, advise the user to retry later |

Catch-all diagnostics:
```bash
python3 scripts/run_with_aliyun_creds.py -- \
  python3 scripts/dyvmsapi_rpc.py SubmitIntent --debug -P UserMessage="test"
```
`--debug` prints `StringToSign` and the final HTTP method/URL (no AK/SK values), useful for verifying the signing string.

---

## 7. Wind-Down

AI-Mode was enabled once in SKILL.md §1.1.1 (immediately after the CLI was verified). **Always** disable it before exiting the Skill on the external path — success, failure, or early STOP, regardless of whether step 2 ran via the script or step 4 ran the CLI:

```bash
aliyun configure ai-mode disable
```

Verification rules are identical to the primary path; see the reference document [verification-method.md](./verification-method.md).

---

## 8. When to Switch Back to the Primary Path

As soon as access to `cli.aliyun-inc.com` is restored, switch back to the primary path immediately:

```bash
nslookup cli.aliyun-inc.com  # If it resolves, switch back
```

After switching back, reinstall the plugin per SKILL.md §1 and continue on the primary path. `CallId` values produced by the two paths are interoperable — initiate via the primary path and query via the external path, or vice versa, both work.
