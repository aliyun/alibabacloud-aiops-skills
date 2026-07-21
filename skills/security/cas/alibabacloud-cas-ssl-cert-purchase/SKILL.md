---
name: alibabacloud-cas-ssl-cert-purchase
description: >
  Purchase and apply SSL certificates via Alibaba Cloud CAS (V2.0 unified flow).
  Supports China site (ProductCode=cas) and International site (ProductCode=cas_intl).
  Automates instance acquisition via BSS API or reuses existing inactive instances.
  All certificate types follow: list-instances → update-instance → apply-certificate.
  OV/EV certificates require additional company info and contact IDs.
  Activate when user says "apply certificate", "purchase SSL", "buy certificate", "certificate order",
  "purchase certificate instance", "buy overseas certificate",
  "申请证书", "购买 SSL", "买证书", "证书下单", "购买证书实例", "买海外证书".
---

# Purchase and Apply SSL Certificate (V2.0)

Purchase and apply SSL certificates via Alibaba Cloud Certificate Authority Service (CAS). Supports DV/OV/EV certificates on both China and International sites, with instance acquisition via BSS API or reuse of existing inactive instances. **Architecture:** CAS (certificate instances + application) + BSS (instance purchase/billing)

## Triggers

Match this skill when the user expresses intents like: "apply SSL certificate", "purchase certificate", "buy certificate", "certificate order", "purchase certificate instance", "buy overseas certificate", or any scenario requiring a certificate application to Alibaba Cloud CAS.

## Intent Clarification (MUST do FIRST)

Before running **any** operational command (`list-instances`, `bss-purchase.sh`, `CreateInstance`, `update-instance`, `apply-certificate`), make sure you understand the user's **concrete goal**.

- If the request is **vague or ambiguous** — e.g. "帮我处理一下实例", "弄一下证书", "handle my cert", or it does not say *what* to do — you **MUST ask clarifying questions FIRST** and run **no** operational command yet.
- Ask which **operation** (buy a new instance / query existing instances / apply a certificate for a domain), which **site** (China / International), the **region**, and the **target** (domain or instance ID).
- **Never** guess the user's intent and place an order or apply a certificate when information is insufficient.
- A vague request is **not** permission to start querying or purchasing. **Clarify first, act second.** Only enter Phase 1 after the user states a concrete goal.

> **[INTERCEPTION RULE — HARD BLOCK]** When the request does not clearly specify the operation type (purchase / query / apply), site, region, or target resource, you **MUST** reply with clarifying questions and **end that turn immediately**. Do **NOT** call `list-instances`, `bss-purchase.sh`, `CreateInstance`, `update-instance`, or `apply-certificate` before the user answers. Append the marker `[WAIT_FOR_CLARIFICATION]` at the end of your clarifying reply to signal the flow is paused.

## Installation

> [MUST] Verify `aliyun version` >= 3.3.3 (full install/upgrade guide: `references/cli-installation-guide.md`; routine update via `aliyun upgrade` when >= 3.3.5).
> [MUST] Run `aliyun configure set --auto-plugin-install true` and `aliyun plugin update` to keep plugins up-to-date.

**Script Dependencies:** `scripts/bss-purchase.sh` requires: bash >= 4.0, aliyun CLI >= 3.3.3 with `aliyun-cli-bssopenapi` plugin (`aliyun plugin install --names aliyun-cli-bssopenapi`).

## Environment Variables

| Variable | Description | Source |
|----------|-------------|--------|
| `CERT_PROFILE` | CLI profile name | Identity Resolver or fallback below |
| `CERT_REGION` | Region for CAS API calls | User-provided or `cn-hangzhou` |
| `CERT_SESSION_ID` | 32-char hex session ID | Generated at skill entry |
| `CERT_INSTANCE_ID` | Instance ID (output) | After instance acquisition |
| `CERT_DOMAIN` | Domain name (output) | After certificate application |
| `CERT_VALIDATE_TYPE` | Validation DNS/HTTP (output) | After certificate application |
| `CERT_TYPE` | Cert type dv/ov/ev (output) | After certificate application |
| `CERT_CONTACT_ID` | Contact ID (output) | After certificate application |

**Identity Resolver Fallback:** If `$CERT_PROFILE` is not set, use `aliyun configure list` to identify the active profile name. Ask user to confirm which profile to use and what `$CERT_REGION` should be.

## Authentication

> **Pre-check: Credentials required.** **Security Rules:** **NEVER** read, echo, or print AK/SK values; **NEVER** ask the user to input AK/SK in the conversation or command line; **NEVER** use `aliyun configure set` with literal credential values; **ONLY** use `aliyun configure list` to check credential status.
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity). **If no valid profile exists, STOP here:** obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak), configure them **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile), then return and re-verify.

**BSS Plugin Check** (if purchasing via API):

```bash
bash scripts/bss-purchase.sh check-plugin --profile $CERT_PROFILE --region $CERT_REGION
```

- Command succeeds → BSS purchase available
- Command fails → Prompt to install: `aliyun plugin install --names aliyun-cli-bssopenapi` (non-blocking, can fall back to console purchase)

## RAM Policy

Required permissions are listed in `references/ram-policies.md`. Key actions: CAS (`ListInstances`, `GetInstanceDetail`, `UpdateInstance`, `ApplyCertificate`, `GetTaskAttribute`, `ListContact`) and BSS (`CreateInstance`, `QueryProductList`, `GetOrderDetail`).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT:** Before executing any command, ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval. Full parameter table: `references/api-commands.md` §Parameter Confirmation.

Key required parameters: **Domain**, **Certificate Type** (DV/OV/EV), **CA Brand** (MUST ask user), **Duration** (MUST ask user), **Contact ID**. Optional: Key Algorithm (default RSA_2048), Validation Method (default DNS), CSR Generation (default online). OV/EV also requires **Company ID**.

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex) once for the entire session: `export CERT_SESSION_ID="$(head -c 16 /dev/urandom | xxd -p)"`

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}`.** Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and are excluded. Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## Flow Overview

Two phases — **instance acquisition** and **certificate application** are independent operations:

```
Phase 1: Step 1 list-instances → user chooses reuse existing / purchase new via BSS
         → Ask "apply a certificate for a domain?" → No: output instance ID, flow ends
Phase 2: Step 2 collect domain → Step 3 details (algorithm/validation/CSR)
         → Step 3a contact (+company for OV/EV) → Step 4 update-instance
         → Step 5 apply-certificate → Step 6 poll get-task-attribute → Step 7 output + env vars
```

## Confirmation Gates (MANDATORY)

This skill has **2 confirmation gates**, both marked with 🚦. They protect money-spending / irreversible operations. These rules are **non-negotiable**:

- At a gate you **MUST** first print the parameter summary table, then **STOP** and wait for the user's explicit reply in a **separate conversation turn**.
- **NEVER** display the summary and execute the gated command in the same turn.
- Only proceed when the user explicitly replies `yes`/`y` (or Chinese "确认"/"继续"). If the user replies `no`/`n`, is ambiguous, or does not reply, you **MUST NOT** execute the gated command.
- **NEVER** auto-select defaults for paid parameters (CA brand, `period`/duration, spec). If any is missing, **STOP** and ask.
- An informational announcement (e.g. "没有空闲实例，需要购买" / "现在提交申请") is **NOT** a substitute for user confirmation.
- A status-check or log output (e.g. `get-instance-detail` showing `inactive`, or a "ready to submit" message) is **NOT** user confirmation either — after printing the summary you **MUST** stop generating and wait for the user's explicit reply in a new turn. Printing the summary and running the gated command in the same turn is a **violation**.
- Reusing an existing instance does **NOT** waive any later gate: the 🚦 Step 5 apply-certificate gate still applies in full, even when the purchase gate was skipped.
- When a status check reveals the instance is **NOT** in the expected state (e.g. not `inactive`, already `pending`), you MUST still present the finding to the user in a clear summary, then STOP and wait for explicit user instruction on how to proceed. Do **NOT** auto-decide to skip or continue the workflow — this status report also counts as a confirmation gate and requires a separate turn.
- **[EMPTY / NO REPLY = NOT CONFIRMED — HIGHEST PRIORITY]** If the user has not replied, replied with an empty message, or replied without an explicit `yes`/`y`/`确认`/`继续`, you MUST treat it as **NOT confirmed**. NEVER infer, assume, or hallucinate user confirmation. Reply with: "未收到明确确认，流程已暂停。请回复 确认/继续 以执行，或提供修改意见。" and generate **no** further commands in that turn. This rule overrides all auto-progression logic.

---

## Core Workflow

### Phase 1: Acquire Certificate Instance

#### Step 1: Query Available Instances

> **[MANDATORY PRE-STEP — NEVER SKIP]** Always run this `list-instances --status inactive` query **first**, even when the user has already provided a specific instance ID. Do **NOT** jump straight to `get-instance-detail`, `update-instance`, or purchase. If the user provided an instance ID, you must still confirm it appears in this list with `inactive` status before using it — verifying a single instance via `get-instance-detail` alone is **NOT** a substitute for this step.

```bash
aliyun cas list-instances --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION --status inactive --current-page 1 --show-size 50
```

> **Pagination:** If the response `TotalCount` exceeds `ShowSize`, fetch additional pages by incrementing `--current-page`. Present all inactive instances to the user across pages.

**When inactive instances exist, let the user choose:**

> Found {{count}} unused certificate instance(s). Present them in a table (Instance ID, Spec, Type). Please choose: 1. Use existing instance (enter number) 2. Purchase new instance

- Choose existing → Record `InstanceId`, skip to "Ask whether to apply certificate"
- Choose new → Go to **Instance Purchase** section below

> **[MANDATORY INTERACTION]** After presenting the inactive instances table, you MUST STOP and wait for the user's explicit choice. Do **NOT** call `get-instance-detail`, `update-instance`, or any subsequent command before the user selects an option. Even when the user pre-provided an instance ID, still present it in the table and ask for confirmation to use it before proceeding.

**No inactive instances → Go to Instance Purchase section.**

> **[INSTANCE NOT IN INACTIVE LIST — STATUS ANOMALY]** If the user-provided instance ID does **not** appear in the inactive list, run `get-instance-detail` to check its real status:
> - `pending` / `normal` / any non-`inactive` status → the instance already has an application in progress or is in use. **STOP the workflow**: report the status finding to the user in a clear summary and wait for their explicit instruction (pick another instance / purchase a new one / cancel the pending application in console first). Do **NOT** skip ahead to `update-instance` or `apply-certificate`, and do **NOT** treat this as the Step 4 auto-submit branch — that branch applies **only** immediately after a successful `update-instance` in the current session.
> - Proceed with `update-instance` **only** when the instance status is confirmed `inactive`.

> **Site selection:** Choose China or International based on user account type or explicit request. Default: China.

#### Ask Whether to Apply Certificate

Once the instance is ready, ask the user:

> Certificate instance is ready (`{{instance_id}}`).
> Do you want to apply a certificate for a domain?
>
> - Yes → Continue collecting domain and application details
> - No → Flow ends, output instance ID for later use

When the user chooses "No", output the instance ID and set `CERT_INSTANCE_ID`:

```bash
export CERT_INSTANCE_ID="{{instance_id}}"
```

---

### Phase 2: Apply Domain Certificate

#### Step 2: Collect Domain

> Please provide the domain for the certificate:
> - Single domain (e.g. `example.com`)
> - Wildcard domain (e.g. `*.example.com`)

Record the user's domain input, used as the `--domain` parameter later.

#### Step 3: Collect Application Details

The following information is written to the instance via `update-instance`.

> Please choose certificate parameters:
>
> | Parameter | Default | Options |
> |-----------|---------|---------|
> | Key Algorithm | RSA_2048 | RSA_3072 / RSA_4096 / ECC_256 / SM2 |
> | Validation Method | DNS | HTTP |
> | CSR Generation | online (system-generated) | upload (user-provided) |

If `upload`, generate CSR via OpenSSL or accept user-provided CSR. See `references/api-commands.md`.

#### Step 3a: Look Up Contact and Company Info

**Contact ID** (required for all certificate types):

If the user provides a contact name or keyword, look it up:
```bash
aliyun cas list-contact --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION --keyword "{{contact_keyword}}"
```
Present results and let the user select. If no keyword is provided, ask the user for their Contact ID or direct them to Console → Information Management → Contacts.

**Company ID** (OV/EV only):
The company must be pre-configured in Console → Information Management → Company Info. Ask the user for the Company ID. If they don't have one, guide them to create it in the console first.

#### Step 4: Fill Application Info (update-instance)

```bash
aliyun cas update-instance --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --instance-id "{{instance_id}}" --domain "{{domain}}" \
  --validation-method "{{validation_method}}" --key-algorithm "{{key_algorithm}}" \
  --generate-csr-method "{{generate_csr_method}}" \
  --contact-id-list.1 "{{contact_id}}" \
  --company-id "{{company_id}}" \
  --csr "{{csr_content}}"
```

> **Conditional flags:**
> - `--company-id` — OV/EV only; **omit for DV**.
> - `--csr` — required only when `--generate-csr-method upload`; **omit for online**.

> **OV/EV without company info — HARD STOP:** If the user does not have a Company ID (or says company info is not yet configured), STOP the **entire** flow immediately: do **NOT** run `update-instance`, do **NOT** run `apply-certificate`, and do **NOT** purchase a new instance. **NEVER** fabricate, guess, or placeholder a Company ID. Only explain the requirement, direct them to Console → Information Management → Company Info, and wait until they confirm configuration is complete.

> **TEST instance special handling:** If `update-instance` returns `DomainAndProductNotMatch`, the TEST instance is incompatible with this domain. Do NOT try other TEST instances. Offer: 1) Apply for new TEST instance in console; 2) Auto-switch to BUY (paid) DV instance.

> **⚠️ WORKFLOW BRANCH — `update-instance` may auto-submit (MANDATORY CHECK):** When `update-instance` fills in complete application info, the platform may **submit the application automatically** (observed on BUY DV instances) — the instance transitions straight to `pending` and DNS validation records are generated. A subsequent `apply-certificate` then fails with `OperationDenied.StatusNotSupport` ("当前状态不支持当前操作").
>
> **Immediately after EVERY `update-instance`, run `get-instance-detail` and branch on the real status:**
> ```bash
> aliyun cas get-instance-detail --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
>   --profile $CERT_PROFILE --region $CERT_REGION --instance-id "{{instance_id}}"
> ```
> - `Status` = `pending` → the platform auto-submitted the application. 1) Do **NOT** run `apply-certificate`. 2) Extract the DNS validation records from the response. 3) Output the explicit marker line `Platform auto-submitted application. Skipping apply-certificate as per SKILL.md auto-submit handling.` (so this branch is auditable), then skip directly to Step 7 (Output Result) and tell the user the application was auto-submitted and is pending DNS verification.
> - `Status` = `inactive` (still editable) → proceed to the 🚦 Step 5 confirmation gate below, then `apply-certificate`.

#### 🚦 CONFIRMATION GATE — Step 5: Confirm and Submit (apply-certificate)

Summarize all parameters for user confirmation:

```
About to submit certificate application:

| Item | Value |
|------|-------|
| Instance ID | {{instance_id}} |
| Domain | {{domain}} |
| Certificate Type | DV / OV / EV |
| Algorithm | {{key_algorithm}} |
| Validation | {{validation_method}} |
| CSR | System-generated / User-uploaded |
| Company ID | {{company_id}} (OV/EV only) |
| Contact | {{contact_ids}} |

OV/EV review typically takes 1-5 business days. DV usually takes minutes to hours.
Confirm submission? (Y/n)
```

> **STOP HERE.** Do NOT run the `apply-certificate` command below until the user explicitly replies `Y`. Announcing "现在提交申请" is NOT a substitute for waiting for the reply.
>
> **[HARD ENFORCEMENT]** After printing the confirmation summary, you MUST end your response immediately. Do **NOT** generate any bash command, API call, or execution step in the same turn. If you are about to write `aliyun cas apply-certificate` before the user has replied `Y`/`yes`/`确认` in a new conversation turn, STOP — that command may only appear after explicit user confirmation.

After user confirms:

```bash
aliyun cas apply-certificate --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION --instance-id "{{instance_id}}"
```

#### Step 6: Query Application Result

apply-certificate is asynchronous. Poll every 30 seconds, max 20 attempts (10 minutes total). DV certificates typically complete within 1-3 polls; OV/EV may remain PENDING for 1-5 business days (manual review).

```bash
aliyun cas get-task-attribute --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --task-id "{{instance_id}}" --task-type "ApplyCertificate"
```

> **[TODO verify]** `--task-id` currently reuses `instance_id`. Confirm against a real `apply-certificate` response whether the poll requires a distinct task id instead.

| TaskStatus | Action |
|------------|--------|
| `COMPLETED` | Proceed to Step 7 |
| `FAILED` | Show error message, guide troubleshooting |
| `PENDING` | Wait 30 seconds, retry (up to 20 attempts) |

> **Timeout:** If PENDING persists after 20 polls, inform the user that the application is still processing and provide the task ID for manual monitoring. For OV/EV, explain that manual review takes 1-5 business days and suggest checking status later via `get-instance-detail`.

#### Step 7: Output Result

Output a summary table that includes **Instance ID, Domain, Certificate Type, Key Algorithm, Validation Method, and Status** (Pending Verification / Under Review). Always echo the domain, key algorithm, and validation method in this final summary so the user can confirm exactly what was applied. For specific instance details, use `get-instance-detail` (see `references/verification-method.md`).

Set environment variables for downstream skills:

```bash
export CERT_INSTANCE_ID="{{instance_id}}"
export CERT_DOMAIN="{{domain}}"
export CERT_VALIDATE_TYPE="{{validation_method}}"
export CERT_TYPE="{{dv|ov|ev}}"
export CERT_CONTACT_ID="{{contact_id}}"
```

---

### Instance Purchase

Purchase certificate instances via the BSS `create-instance` API (plugin mode). See `references/api-commands.md` for full CA matrices, spec codes, duration tables, and complete BSS command examples.

#### Step 1: Select Certificate Mode

| Mode | Description |
|------|-------------|
| **Single Domain** | One domain (`example.com`) |
| **Wildcard** | Same-level subdomains (`*.example.com`) |
| **Multi-Domain** | Combined (`example.com` + `*.test.com`) |

Record `cert_mode` (`single` / `wildcard` / `multi`).

#### Step 2: Select Certificate Type and CA

Ask user for certificate type (DV/OV/EV) and CA brand. See `references/api-commands.md` for available combinations by mode and site.

> **MANDATORY:** CA brand and certificate type **MUST** be provided by the user. If the user has not specified them, **STOP and ask** — **NEVER** auto-select a brand (e.g. do not default to Alibaba/`ali.dv.f`).

> **[PARAM COMPATIBILITY — NO SILENT FALLBACK]** If the user-specified CA brand / cert type / spec is unavailable on the current site (determined by `--product-code`), you MUST: 1) tell the user this combination is not supported on the current site; 2) offer viable alternatives (e.g. switch to the International site `cas_intl` for DigiCert DV, or pick a China-site brand such as GeoTrust/Alibaba); 3) wait for the user's choice and re-run with the **new** parameters. **NEVER** silently fall back to previously rejected parameters, and **NEVER** switch sites without telling the user. When the user updates a parameter mid-flow, the **latest** value always wins — purchase summaries and purchase commands must use the latest user-confirmed values.

> **China site quick reference:**
> - DV Test Standard (free): spec `ss.dv.t`, product `testCert_product`, 3 months only
> - DV Test Pro (low-cost): spec `ss.dv.f`, product `testCert_product`, 6 months only
> - Regular DigiCert DV (paid): spec `ss.dv.f`, product `instance_product`, 6/12/24/36 months
> - Common paid CAs: Alibaba, GeoTrust, DigiCert, GlobalSign, CFCA, vTrus, WoTrus
>
> **CRITICAL DISTINCTION:** The spec code `ss.dv.f` is shared between DV Test Pro and regular DigiCert DV. They are distinguished ONLY by `--product-value`: `testCert_product` = Test Pro, `instance_product` = regular paid. Always confirm with the user whether they want a TEST or PAID certificate before selecting `--product-value`.
>
> **International site:** No TEST certificates. CAs: Alibaba, DigiCert, DigiCert Pro, GeoTrust, GlobalSign, Rapid.

Record `cert_type` (dv/ov/ev) and `ca_brand`.

#### Step 3: Select Duration

Duration depends on CA — see `references/api-commands.md` for per-CA duration matrix. Common: 6, 12, 24, 36 months. DV Test: fixed 3 or 6 months.

> **MANDATORY:** Duration (`period`) **MUST** be confirmed by the user. **NEVER** default to an arbitrary value such as 12 months.

Record `period`.

#### Step 4: Multi-Domain Count (multi mode only)

Ask the user for domain counts. These directly affect pricing.

> 1. How many single domains? (minimum 1):
> 2. How many wildcard domains? (minimum 0):

**Validation rules:**
- `full_count` + `wild_count` must be >= 1 (at least one domain)
- `full_count` must be >= 1 if `wild_count` is 0
- **MUST be confirmed by the user** — never auto-default these counts

Record `full_count` and `wild_count`.

#### 🚦 CONFIRMATION GATE — Step 5: Confirm Purchase (High-Risk, spends money)

```
⚠️ About to purchase certificate instance via API (auto-charge):

| Item | Value |
|------|-------|
| Mode | {{Single / Wildcard / Multi-Domain}} |
| CA | {{brand}} |
| Type | {{cert_type}} |
| Duration | {{period}} months |
| Estimated Cost | See pricing page (varies by CA/duration) |

Confirm purchase? (yes/no)
```

> **Note:** BSS `create-instance` does not return pricing before purchase. For cost estimation, direct users to: China site — https://www.aliyun.com/price/product?spm=5176.cncas.0.0#/cas/detail or International — https://www.alibabacloud.com/product/ssl-certificates/pricing

> **STOP HERE.** Do NOT run the purchase command below in this same turn. Wait for the user to explicitly reply `yes`. If any of CA / Type / Duration is still a placeholder or was not chosen by the user, STOP and ask first — **never auto-fill**.
>
> **[HARD ENFORCEMENT]** After printing the purchase summary, end your response immediately — do **NOT** run `bss-purchase.sh` or any purchase command in the same turn. The purchase command may only appear after the user's explicit `yes` in a new conversation turn.

#### Step 6: Execute Purchase (via Script)

> **Note:** All BSS billing calls go through `scripts/bss-purchase.sh`, which uses the `bssopenapi` plugin in plugin mode (`query-product-list` / `create-instance` / `get-order-detail`) and constructs `--parameter` pairs internally.

```bash
bash scripts/bss-purchase.sh create-instance \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --product-code {{product_code}} --product-type {{product_type}} \
  --period {{period}} --product-value {{product_value}} \
  --merge {{merge}} --cert-type {{cert_type}} \
  [--full-spec {{full_spec}}] [--full-count {{full_count}}] \
  [--wildcard-spec {{wildcard_spec}}] [--wildcard-count {{wildcard_count}}] \
  [--auto-issue]
```

**Site-specific values:**

| Parameter | China Site | International Site |
|-----------|-----------|-------------------|
| `--product-code` | `cas` | `cas_intl` |
| `--product-type` | `cas_dv_public_cn` | `cas_intl` |
| `--product-value` | `testCert_product` (DV Test) / `instance_product` (others) | Always `instance_product` |

**Conditional parameters by mode:**

| Mode | merge | Script flags |
|------|-------|-------------|
| Single Domain | `0` | `--full-spec {{spec}} --full-count 1` |
| Wildcard | `0` | `--wildcard-spec {{spec}} --wildcard-count 1` |
| Multi-Domain | `1` | Both `--full-spec`+`--wildcard-spec` with respective counts |

> **`--auto-issue` flag:** A **BSS purchase-time** flag that requests the platform to auto-issue the certificate after purchase. This is **different** from CAS `update-instance`'s `--auto-reissue` (managed hosting / auto-renewal). Ask the user whether they want auto-issue before adding this flag.
>
> **[TODO verify]** Confirm the exact behavior of `--auto-issue` (and any precondition such as the domain being hosted on Alibaba Cloud CDN/ALB) against the BSS API docs. See `references/api-commands.md` for full CA matrices and spec codes.

> **[PURCHASE FAILURE — `INSUFFICIENT.AVAILABLE.QUOTA` (MANDATORY)]** If the purchase fails with `INSUFFICIENT.AVAILABLE.QUOTA` — or the **user reports** they hit this error before the skill ran — STOP the purchase flow immediately: 1) explain the insufficient-balance cause to the user; 2) provide the top-up link https://usercenter2.aliyun.com/ ; 3) tell the user to reply `继续` after topping up so you can retry the purchase. Do **NOT** enter any purchase-confirmation or execution step before providing the link and waiting for the user's reply. This error handling takes priority over the normal purchase flow.

#### Step 7: Output

**Success:** Set `CERT_INSTANCE_ID={{instance_id}}`.

**Failure:** Prompt manual console purchase: https://yundun.console.aliyun.com/?p=cas

---

## Success Verification Method

After certificate application, verify via `get-instance-detail` (full status meanings and commands: `references/verification-method.md`). Key statuses: `pending` (under review, normal for OV/EV), `normal` (issued), `willExpire` (renewal needed).

## Cleanup

Console-only operations (not automated by this skill — guide users to the console): cancel pending application (SSL Certificates → Certificate Management, China: https://yundun.console.aliyun.com/?p=cas), refund unused instance (within 5 days of purchase, `inactive`/`closed` status), revoke issued certificate (irreversible). Remove env vars: `unset CERT_INSTANCE_ID CERT_DOMAIN CERT_VALIDATE_TYPE CERT_TYPE CERT_CONTACT_ID CERT_SESSION_ID CERT_PROFILE CERT_REGION`.

## Error Handling

| Error Scenario | Resolution |
|---------------|-----------|
| `$CERT_PROFILE` not set | `aliyun configure list` fallback |
| `DomainAndProductNotMatch` | TEST instance restriction → offer switch to paid DV |
| `Forbidden` | Follow Permission Failure Handling (RAM Policy section) |
| BSS `INSUFFICIENT.AVAILABLE.QUOTA` | Mandatory top-up flow — see Instance Purchase Step 6 |
| BSS `CreateInstance` timeout | **Do NOT auto-retry** (may double-charge); query `get-order-detail` first |

For the complete error handling table (16 scenarios including OV/EV rejection, BSS plugin issues, and empty result disambiguation), see `references/error-handling.md`.

## Skill Integration

- **Upstream:** `alibabacloud-cas-ssl-common-tools` Identity Resolver (provides `$CERT_PROFILE`, with fallback in Environment Variables section)
- **Downstream:** `alibabacloud-cas-ssl-common-tools` Domain Verify (uses `$CERT_INSTANCE_ID` and `$CERT_VALIDATE_TYPE`)

## Best Practices

1. **Always verify `$CERT_PROFILE` before any API call** — prevents auth errors mid-workflow
2. **Prefer DNS validation over HTTP** — works for wildcard domains and doesn't require web server access
3. **Check inactive instances first** — reuse existing instances before purchasing new ones
4. **Never auto-select CA brands or durations** — always ask the user, these affect cost and compatibility

## Reference Links

| Reference | Contents |
|-----------|----------|
| `references/api-commands.md` | CA matrices, spec codes, BSS command examples, duration tables, CSR handling |
| `references/ram-policies.md` | RAM permission policies for CAS and BSS |
| `references/related-commands.md` | Complete CLI command reference table |
| `references/verification-method.md` | Success verification commands and expected results |
| `references/cli-installation-guide.md` | CLI installation and configuration guide |
| `references/acceptance-criteria.md` | Correct/incorrect patterns for skill testing |
| `references/error-handling.md` | Complete error handling table (16 scenarios) |
