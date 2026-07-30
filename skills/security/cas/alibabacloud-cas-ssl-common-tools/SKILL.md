---
name: alibabacloud-cas-ssl-common-tools
description: >
  SSL certificate toolkit for Alibaba Cloud CAS. Includes identity configuration, domain verification,
  certificate download, certificate upload, CSR generation, format conversion, and certificate matching.
  Activate when user says "verify domain", "download certificate", "upload certificate", "generate CSR",
  "convert certificate format", "configure identity", "match certificate", "check key cert match",
  "验证域名", "下载证书", "上传证书", "生成 CSR", "转换证书格式", "配置身份", "检查证书匹配", "是否匹配", "是不是一对".
---

# SSL Certificate Toolkit

Unified toolkit for Alibaba Cloud CAS SSL certificate lifecycle management. Covers identity configuration, domain verification, certificate download/upload, CSR generation, format conversion, and certificate matching.

**Architecture:** `CAS API + STS Identity + Alidns DNS + OpenSSL local tools + Shell scripts`

## Triggers

| English | Chinese | Section | Status |
|---------|---------|---------|--------|
| "configure identity", "set credentials" | `"配置身份"` | [Identity Resolver](#identity-resolver) | ✅ Active |
| "verify domain", "DNS verification" | `"验证域名"` | [Domain Verify](#domain-verify) | ✅ Active |
| "download certificate", "export certificate" | `"下载证书"` | [Certificate Download](#certificate-download) | ✅ Active |
| "upload certificate", "import third-party cert" | `"上传证书"` | [Certificate Upload](#certificate-upload) | ✅ Active |
| "generate CSR", "create certificate request" | `"生成 CSR"` | [CSR Generation](#csr-generation) | ✅ Active |
| "convert format", "PEM to PFX" | `"转换格式"` | [Format Conversion](#format-conversion) | ✅ Active |
| "match certificate", "check key cert match", "key mismatch", "check if they match", "are they a pair" | `"证书匹配"`, `"检查密钥匹配"`, `"不匹配"`, `"是否匹配"`, `"是不是一对"`, `"是否不匹配"`, `"是不是配套"` | [Certificate Matching](#certificate-matching) | ✅ Active |

> **[MUST] Intent Clarification:** If user input does NOT match any trigger keyword above, or is too vague (e.g., "帮我处理一下ram", "配置证书", "搞一下SSL"), **STOP immediately**. Ask the user to clarify which specific operation they need (configure identity / verify domain / download / upload / CSR / format conversion / matching). Do **NOT** call any CAS, RAM, STS, or Alidns API until the user provides a clear intent.
> **[MUST] HITL Blocking:** When any instruction requires asking the user (clarification, name conflict, parameter confirmation), you MUST halt ALL subsequent actions and **WAIT for the user's explicit reply**. Never auto-advance, auto-retry, assume consent, or proceed to the next step without receiving a non-empty user response. **An empty, blank, or silent user response is NOT consent — re-prompt with the exact same question and continue waiting; never treat emptiness as a signal to auto-retry (e.g., re-issuing `upload-user-certificate` with a different name). You are strictly FORBIDDEN from calling `upload-user-certificate` or any retry API until a non-empty, explicit user reply is received.**
## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **First install or major upgrade:** Follow the verified steps in `references/cli-installation-guide.md` — download the installer first, review/verify its content, then execute the local copy. Never pipe remote content directly into a shell.
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade` — prefer this built-in self-update over re-running the install script.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**Local tools:**

| Tool | Required | Used By |
|------|----------|---------|
| `openssl` | **Required** | Format conversion, modulus check, chain split, CSR generation |
| `keytool` (Java JDK/JRE) | Required for JKS | `scripts/convert-format.sh` (pem-to-jks / jks-to-pem) |

Install: macOS `brew install openssl openjdk` / Linux `apt install openssl default-jdk`
## Environment Variables

| Variable | Source | Purpose |
|----------|--------|---------|
| `$ALIYUN_CMD` | Identity Resolver | Full path to aliyun CLI |
| `$CERT_PROFILE` | Identity Resolver | Credential profile for all API operations |
| `$CERT_REGION` | Identity Resolver | Region (default `cn-hangzhou`) |
| `$CERT_INSTANCE_ID` | Purchase / Domain Verify | Certificate instance ID |
| `$CERT_CERT_ID` | Domain Verify / Upload | Certificate ID (numeric) |
| `$CERT_DOMAIN` | User input or upstream | Target domain |

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

After credentials are verified, the Identity Resolver in Core Workflow handles full profile detection, identity verification, and branch configuration.
## RAM Policy

| Product | Key Actions | Coverage |
|---------|-------------|----------|
| CAS | `ListInstances`, `GetInstanceDetail`, `UploadUserCertificate`, `GetTaskAttribute` | Certificate CRUD |
| RAM | `GetRole`, `CreateRole`, `AttachPolicyToRole` | Role auto-configuration |
| Alidns | `AddDomainRecord`, `DescribeDomainRecords` | DNS verification |
| STS | `GetCallerIdentity` | Identity verification |

**Recommended (least privilege):** use the fine-grained custom policy in `references/ram-policies.md`. The system policies `AliyunYundunCertFullAccess` / `AliyunDNSFullAccess` grant broad `cas:*` / `alidns:*` access — accept them only as a quick-trial convenience, never for production.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

Full RAM policy JSON and fine-grained custom policy in `references/ram-policies.md`.
## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call, ALL user-customizable parameters (RegionId, instance names, passwords, domain names, etc.) MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.
> **[MUST] Payment parameters (ProductCode, PurchaseStatus):** Always confirm verbally with user before any paid operation. Display exact parameter names and ask user to provide values. NEVER assume or derive defaults for payment parameters.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `RegionId` | Required | Alibaba Cloud region | `cn-hangzhou` |
| `InstanceId` | Required | CAS certificate instance ID | User must provide |
| `Domain` | Required | Target domain name | User must provide |
| `Certificate Name` | Required (upload) | Unique name for uploaded cert | User must provide |
| `Output Directory` | Optional | Directory for output files | `/tmp/cert-output` |
| `Password` | Required (PFX/JKS) | Export password for PFX/JKS | **MUST ask user** |
| `Key Algorithm` | Optional | RSA-2048 or ECC P-256 | RSA-2048 |
| `Profile Name` | Optional | CLI credential profile name | `cert-operator` |

> **[MUST] If user specifies a profile name, it MUST be used exactly. Auto-fallback to `default` or other profiles is FORBIDDEN without explicit user approval.**

### Forbidden CLI Parameters

> **[FORBIDDEN] NEVER include the following in any `aliyun cas` command:**
> - `--product-name` (any value) — not a valid CAS API parameter; its presence indicates incorrect command construction
> - `--product-code` as CLI flag — ProductCode is a verbal confirmation parameter, not a CLI flag

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

Example: `aliyun cas list-instances --current-page 1 --show-size 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}`

**Script execution:** Inject the session-id via inline environment variable:
```bash
SKILL_SESSION_ID={session-id} bash scripts/split-chain.sh fullchain.pem /output
```

## Core Workflow

> **[MUST] Entry Gate — Intent First:** Before entering ANY subsection below, confirm user intent matches a specific Trigger (§ Triggers table). If input is vague (e.g., "帮我处理一下ram", "配置证书", "搞一下SSL"), **STOP — ZERO API calls** (no STS, RAM, CAS, Alidns). Ask which operation the user needs. Do NOT generate execution plans or invoke any cloud API until intent is explicit.

### CAS Dual API Systems

CAS has two interface systems. **Always prefer the new API:**

| Dimension | Old API (PascalCase) | New API (kebab-case) |
|-----------|---------------------|---------------------|
| Instance list | `ListUserCertificateOrder` | `list-instances` |
| Instance details | `GetUserCertificateDetail` (CertId, numeric) | `get-instance-detail` (InstanceId, string) |
| Coverage | **Only** old-format `cas-ivauto-xxxxx` | **Both** old and new formats |

### Scripts

| Script | Usage |
|--------|-------|
| `scripts/split-chain.sh` | `./split-chain.sh <fullchain.pem> <output_dir>` |
| `scripts/convert-format.sh` | `./convert-format.sh <command> [options]` |
| `scripts/modulus-check.sh` | `./modulus-check.sh <type> <file1> <file2> [file3]` |

### Domain Pre-check

When user provides a domain but intent is unclear:
```bash
aliyun cas list-instances --profile $CERT_PROFILE --region $CERT_REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id} \
  --keyword "{{domain}}" --current-page 1 --show-size 100
```
> **[MUST] Domain matching:** When user provides a domain for upload or deployment **without an InstanceId**, always run the above `list-instances --keyword` first to verify domain coverage. Skip this step if user already provided an InstanceId.

| Instance Status | Suggested Route |
|----------------|----------------|
| `issued` and not expired | Deploy or Download |
| Only `inactive` instances | Continue application via Purchase |
| No matching instances | Purchase new certificate |
---

### Identity Resolver

Auto-detect runtime environment and configure credentials. See `references/identity-resolver-commands.md` for detailed CLI detection and role creation commands.

**Step 1: Detect Credentials** — Check in order:
1. **Environment variables** (`$ALIBABA_CLOUD_ACCESS_KEY_ID`) → Create temp profile
2. **Local CLI profile** (`$ALIYUN_CMD configure list`) → Use existing profile
3. **None found** → Enter Step 3

**Step 2: Verify Identity**
```bash
$ALIYUN_CMD sts get-caller-identity --profile {{profile_name}} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```
- **AccountId returned** → Identity confirmed. If first-time Branch A → Step 3.5
- **Error** → Enter Step 3

**Step 3: Branch Configuration**

| Condition | Branch |
|-----------|--------|
| `$ALIBABA_CLOUD_SERVICE_ACCESS_KEY_ID` set + AccountId available | **Branch B: Role Assumption** |
| Service AK not set | **Branch A: Local Profile** |
| Service AK set but no AccountId | **Ask user for AccountId** |

**Branch A:** `$ALIYUN_CMD configure --profile cert-operator`
**Branch B:** `$ALIYUN_CMD configure --profile cert-operator --mode RamRoleArn` (auto-fill from service AK + `acs:ram::{{account_id}}:role/cert-operator`)

**Step 3.5: Role Auto-Configuration (First Branch A Only)** — Offer to create `cert-operator` role with trust policy for `aideepsign.aliyuncs.com` and attach `AliyunYundunCertFullAccess`, `AliyunDNSFullAccess`. Full commands in `references/identity-resolver-commands.md`.

> **[FORBIDDEN] If the requested profile (e.g., `cert-operator`) does not exist, you MUST NOT silently fall back to any other profile (including `default`). STOP and inform the user that the specified profile is missing. Offer to create the profile or ask the user for an alternative. Do NOT proceed with API calls until a valid, explicitly confirmed profile is set.**

**Step 4: Verify CAS Access**
```bash
$ALIYUN_CMD cas list-instances --profile {{profile_name}} --region cn-hangzhou --current-page 1 --show-size 1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

**Step 5: Output**
```bash
export ALIYUN_CMD="{{aliyun_path}}"
export CERT_PROFILE="{{profile_name}}"
export CERT_ACCOUNT_ID="{{account_id}}"
export CERT_REGION="{{region}}"
```

---

### Domain Verify

Domain verification helper. See `references/domain-verify-commands.md` for detailed API fields and DNS/HTTP commands.

**Step 1: Locate Instance**
- **Has InstanceId** → `aliyun cas get-instance-detail --instance-id "{{id}}"`
- **Has domain only** → `aliyun cas list-instances --keyword "{{domain}}"` → Extract InstanceId
- **Neither** → Ask user

**Step 2: Query Status**
```bash
aliyun cas get-instance-detail --profile $CERT_PROFILE --region $CERT_REGION --instance-id "{{id}}" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

| Status | Action |
|--------|--------|
| `CertificateStatus = issued` | Done — extract CertId |
| `checking` / `pending` | Continue to Step 3 |
| `failed` / `closed` | Show error |

**Step 3: Execute Verification** — Find `ValidationMethod` in response:
- **DNS:** Extract `DnsHost` + `DnsValue`. If Alibaba Cloud DNS, auto-add via `aliyun alidns add-domain-record`; otherwise provide manual TXT record guidance.
- **HTTP:** Extract `FilePath` + `FileContent`. Guide user to create file at web server root, or auto-upload via SSH/SCP.

**Step 4: Poll Result** — Poll `get-instance-detail` every 30-60s until `CertificateStatus → issued` or timeout (>30 min).

**Step 5: Output**
```bash
export CERT_CERT_ID="{{cert_id}}"
export CERT_DOMAIN="{{domain}}"
export CERT_STATUS="verified"
```

---

### Certificate Download

Query issuance status, extract certificate content, split chain, convert format, verify integrity.

**Step 1: Query Issuance**
```bash
aliyun cas get-instance-detail --profile $CERT_PROFILE --region $CERT_REGION --instance-id "{{id}}" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```
Must have `CertificateStatus = issued` before proceeding.

**Step 2: Extract Certificate Content** — Parse `Cert` (server PEM) and `Key` (private key PEM) from response. Write to secure temp directory:
```bash
CERT_TMPDIR=$(mktemp -d /tmp/cert-XXXXXX)
chmod 700 "$CERT_TMPDIR"
echo "{{cert_content}}" > "$CERT_TMPDIR/server.pem"
echo "{{key_content}}" > "$CERT_TMPDIR/server.key"
chmod 600 "$CERT_TMPDIR/server.key"
```

**Step 3: Split Chain**
```bash
bash scripts/split-chain.sh "$CERT_TMPDIR/server.pem" "{{output_dir}}"
```
Outputs: `server_only.pem`, `chain.pem`, `fullchain.pem`.

**Step 4: Convert Format (if needed)** — Default is Nginx PEM. For other formats:
> **[MUST] Before running `convert-format.sh pem-to-pfx` or `pem-to-jks`, ask the user for the export password via `ask_user_question`. [NEVER] hardcode, auto-generate, or assume a default password.**

```bash
# PFX (for IIS/Windows)
bash scripts/convert-format.sh pem-to-pfx "{{output_dir}}/server_only.pem" "{{output_dir}}/server.key" "{{output_dir}}/{{domain}}.pfx" "{{output_dir}}/chain.pem" "{{password}}"

# JKS (for Tomcat)
bash scripts/convert-format.sh pem-to-jks "{{output_dir}}/server_only.pem" "{{output_dir}}/server.key" "{{output_dir}}/{{domain}}.jks" myalias "{{password}}"

# DER
bash scripts/convert-format.sh pem-to-der "{{output_dir}}/server_only.pem" "{{output_dir}}/{{domain}}.crt"
```

For Nginx: `cp "{{output_dir}}/fullchain.pem" "{{output_dir}}/{{domain}}.fullchain.pem"` and `cp "{{output_dir}}/server.key" "{{output_dir}}/{{domain}}.key"`

> **[MUST] Before deploying, verify key-cert match using `bash scripts/modulus-check.sh key-cert`. [NEVER] use inline `openssl` modulus commands for this verification.**

**Step 6: Output**
```bash
export CERT_CERT_ID="{{cert_id}}"
export CERT_PATH="{{output_dir}}/{{domain}}.fullchain.pem"
export CERT_KEY="{{output_dir}}/{{domain}}.key"
```

---

### Certificate Upload

Upload third-party certificates (PEM/PFX/SM2) to Alibaba Cloud CAS.

**Step 1: Read and Parse Certificate**
- **PEM:** Read cert and key files directly.
- **PFX:** Extract first: `bash scripts/convert-format.sh pfx-to-pem "{{cert.pfx}}" /tmp/cert-upload "{{password}}"`

Parse certificate info: `openssl x509 -in "{{cert_file}}" -text -noout | grep -E "Subject:|Issuer:|Not Before:|Not After:"`

Verify key matches: `bash scripts/modulus-check.sh key-cert "{{key_file}}" "{{cert_file}}"`

**Step 2: Upload**
```bash
aliyun cas upload-user-certificate --profile $CERT_PROFILE --region $CERT_REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id} \
  --Name "{{cert_name}}" --Cert "$(cat {{cert_file}})" --Key "$(cat {{key_file}})"
```
> Name must be unique. Check first: `aliyun cas list-instances --keyword "{{cert_name}}"`
>
> **[MUST] Name Conflict HITL:** If the upload returns `NameAlreadyExist` or `NameRepeat`, **STOP and ask the user** to confirm a new certificate name. Suggest alternatives (e.g., append `-02`, `-backup`, or date suffix). Do **NOT** auto-retry with a modified name without explicit user approval. **WAIT for the user's explicit reply before any retry.**
> **[MUST NOT] NEVER auto-retry `upload-user-certificate` with any system-generated or AI-derived name. After a name conflict, STOP immediately and WAIT for user input. Only proceed with a retry AFTER receiving the user's explicit new name in a non-empty reply — auto-retry without user input is strictly prohibited.**

**Success:** `{"CertId": 12345}`

**Step 3: Output**
```bash
export CERT_CERT_ID="{{cert_id}}"
export CERT_DOMAIN="{{common_name}}"
```

> **[MUST] Final Answer Verification (Upload):** Before outputting the final summary for any upload operation, cross-check Certificate Name, CertId, and Domain against the most recent API response JSON. Fix any character-level discrepancies (truncation, digit transposition, missing zeros). NEVER generate the summary from memory.

---

### CSR Generation

Generate and inspect Certificate Signing Requests. Supports RSA/ECC, single/multi-domain/wildcard.

**Single domain (RSA-2048):**
```bash
openssl req -new -newkey rsa:2048 -nodes -keyout "{{domain}}.key" -out "{{domain}}.csr" -subj "/CN={{domain}}"
```

**Multi-domain SAN:** Create `san.cnf` config with `[alt_names]` section, then:
```bash
openssl req -new -newkey rsa:2048 -nodes -keyout "{{domain}}.key" -out "{{domain}}.csr" -config san.cnf -extensions v3_req
```

**Wildcard:** Same as single domain with `CN=*.example.com`.

**ECC (P-256):**
```bash
openssl ecparam -genkey -name prime256v1 -out "{{domain}}.key"
openssl req -new -key "{{domain}}.key" -out "{{domain}}.csr" -subj "/CN={{domain}}"
```

**Inspect CSR:** `openssl req -in "{{csr_file}}" -text -noout`

---

### Format Conversion

All conversions use `scripts/convert-format.sh`. Available commands:

| Command | Usage |
|---------|-------|
| `pem-to-pfx` | `<cert.pem> <key.pem> <output.pfx> [chain.pem] [password]` |
| `pfx-to-pem` | `<input.pfx> <output_prefix> [password]` |
| `pem-to-jks` | `<cert.pem> <key.pem> <output.jks> [alias] [password]` |
| `jks-to-pem` | `<input.jks> <output_prefix> [jks_pass] [pem_pass]` |
| `pem-to-der` | `<cert.pem> <output.der>` |
| `der-to-pem` | `<input.der> <output.pem>` |
| `pfx-to-jks` | `<input.pfx> <output.jks> [pfx_pass] [jks_pass] [alias]` |

Example: `bash scripts/convert-format.sh pfx-to-pem cert.pfx /output/cert "mypassword"` → `/output/cert.crt` + `/output/cert.key`

---

### Certificate Matching

Verify key/cert/CSR matching, chain integrity, and domain coverage.
> **[MUST] Use `scripts/modulus-check.sh` for ALL key/cert/CSR matching verification. [NEVER] substitute with inline `openssl x509 -modulus`, `openssl rsa -modulus`, or any equivalent inline command.**

```bash
bash scripts/modulus-check.sh key-cert "{{key.pem}}" "{{cert.pem}}"
bash scripts/modulus-check.sh key-csr "{{key.pem}}" "{{csr.pem}}"
bash scripts/modulus-check.sh all "{{key.pem}}" "{{cert.pem}}" "{{csr.pem}}"
bash scripts/split-chain.sh fullchain.pem /tmp/cert-verify
openssl x509 -in "{{cert}}" -text -noout | awk '/X509v3 Subject Alternative Name/{getline; print}'
openssl x509 -in "{{cert}}" -noout -dates
```

---

### Revoke and Delete — DISABLED

> **This feature is currently disabled. API execution is not permitted.** Redirect to console: https://yundun.console.aliyun.com/?p=cas

---

### Orchestration Logic

This skill is a **toolkit** — the Agent routes to specific sub-sections based on user intent. Entry points are dynamic:

| Entry Point | Trigger | Call Order |
|-------------|---------|------------|
| Identity Resolver | First-time / no `$CERT_PROFILE` | Detect → Resolve → output env vars |
| Domain Verify | After purchase or standalone | Query → Validate → Execute → Poll |
| Certificate Download | Cert issued | Query → Download → Split chain |
| Certificate Upload | Third-party cert | Upload → output `$CERT_CERT_ID` |
| CSR Generation | Before purchase | Generate CSR → output CSR file |
| Format Conversion | User has cert files | Run `convert-format.sh` |
| Certificate Matching | Troubleshooting | Run `modulus-check.sh` → report |

**Upstream:** `alibabacloud-cas-ssl-cert-purchase` (provides `$CERT_INSTANCE_ID`, `$CERT_DOMAIN`) | **Downstream:** `alibabacloud-cas-ssl-cert-deploy` (uses `$CERT_CERT_ID`)

## Success Verification Method

| Function | Verification Command | Success Indicator |
|----------|---------------------|-------------------|
| Identity Resolver | `aliyun sts get-caller-identity` | `AccountId` returned |
| Domain Verify | `get-instance-detail` → `CertificateStatus` | Equals `issued` |
| Certificate Download | `openssl verify -CAfile chain.pem server_only.pem` | Outputs `OK` |
| Certificate Upload | Upload API response | `CertId` returned |
| CSR Generation | `openssl req -in <csr> -text -noout` | Correct Subject/SAN |
| Format Conversion | Parse output file with openssl/keytool | Valid certificate data |
| Certificate Matching | `scripts/modulus-check.sh` | Reports `MATCH` |

## Cleanup

```bash
# [MUST] Validate CERT_TMPDIR matches the /tmp/cert-* mktemp pattern — never rm -rf an unvalidated variable.
case "${CERT_TMPDIR:-}" in
  /tmp/cert-?*) rm -rf "$CERT_TMPDIR" ;;
  *) echo "Skipped: CERT_TMPDIR is unset or not an expected /tmp/cert-* path" ;;
esac
rm -rf /tmp/cert-*.pfx /tmp/cert-output /tmp/cert-verify /tmp/cert-upload
unset CERT_PROFILE CERT_REGION CERT_INSTANCE_ID CERT_CERT_ID CERT_DOMAIN CERT_SESSION_ID CERT_TMPDIR
```

> **Security:** Never leave private key files in world-readable locations. Always clean up temp files containing private keys after use.
## Command Tables

Key commands (full list in `references/related-commands.md`): `list-instances`, `get-instance-detail`, `upload-user-certificate`, `add-domain-record`, `get-caller-identity`, plus `scripts/` utilities.
## Best Practices

1. **Always prefer new CAS API** (kebab-case `list-instances`) over old API (PascalCase `ListUserCertificateOrder`)
2. **[MUST] Use `scripts/` for deterministic operations** — [NEVER] rewrite format conversion, modulus check, or chain split inline (no `openssl x509 -modulus`, no manual `openssl pkcs12`, etc.)
3. **[MUST] Always verify key-cert match** before uploading — run `bash scripts/modulus-check.sh key-cert`, [NEVER] skip or use inline alternatives
4. **Split certificate chain** before deploying to CDN/SLB (many services require separate server cert and chain)
5. **Use `--user-agent`** on every `aliyun` API command for observability
6. **Never print or log private key content** — treat all `.key` files as secrets
7. **Prefer ECC P-256** over RSA-2048 for new certificates (smaller, faster, equivalent security)
8. **Confirm all parameters** with user before execution
9. **Use RAM roles** (Branch B) over direct AK/SK (Branch A) for production environments

## Reference Links

| Reference | Description |
|-----------|-------------|
| `references/cli-installation-guide.md` | Full CLI installation and configuration guide |
| `references/identity-resolver-commands.md` | Identity detection, role creation, and trust policy commands |
| `references/domain-verify-commands.md` | DNS/HTTP verification API fields and commands |
| `references/cert-download-commands.md` | Certificate download API fields and chain split details |
| `references/cert-upload-commands.md` | Certificate upload API parameters and error codes |
| `references/ram-policies.md` | RAM permission policies and fine-grained custom policy JSON |
| `references/related-commands.md` | Consolidated CLI command reference table |
| `references/verification-method.md` | Detailed success verification steps per toolkit function |

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| `$CERT_PROFILE` not set | Run Identity Resolver |
| `$ALIYUN_CMD` not set | Run Identity Resolver |
| `InvalidInstanceId.NotFound` | Check InstanceId format |
| `Forbidden.RAM` | Add `AliyunYundunCertFullAccess` — see RAM Policy section |
| `NameAlreadyExist` (upload) | Use different certificate name |
| `KeyNotMatchCert` (upload) | Run `scripts/modulus-check.sh key-cert` |
| `Cert` field empty (download) | Try `CertFilter=false` or check SM2 |
| `keytool` missing (JKS) | Install JDK or use PEM/PFX |
| Chain verification failed | Check intermediate chain completeness |
