---
name: alibabacloud-ddoscoo-domain-configuration-backup
description: |
  Alibaba Cloud DDoS Pro (ddoscoo) domain-level (Layer 7 website) configuration full export and import. Use for disaster recovery backup, configuration audit, rollback after misconfiguration, or batch import of domain settings. Covers 20 configuration dimensions in YAML v2.0 format. Triggers: DDoS domain config export, domain config import, domain config backup, domain config audit. Does NOT cover Layer 4 port forwarding (TCP/UDP) -- handled by `alibabacloud-ddoscoo-port-config-migration`.
license: Apache-2.0
compatibility: Requires aliyun CLI >= 3.3.1
metadata:
  domain: aiops
  owner: Jiafei
  contact: jiafei.qiu@alibaba-inc.com
  architecture: DDoS Pro instances + domain access (HTTP/HTTPS/WebSocket) + YAML v2.0 four-segment structure (proxy/client/server/security)
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# DDoS Pro Domain Configuration Migration Skill

## Scenario Description

Export all **access configuration + advanced settings + security policies** for **website business (Layer 7 domains)** under DDoS Pro (ddoscoo) to a YAML file, or import a YAML file back into the same account for restoration. YAML v2.0 follows the console layout, divided into four segments -- **proxy / client / server / security** -- all domain-level, supporting single domain, multiple domains, per-instance, and full-account granularity.

> **Scope Limitation (Important)**: This skill **only covers domain-level (Layer 7 website) business**. **Non-website business (Layer 4 port forwarding: TCP/UDP)** -- including port forwarding rules, session persistence, health checks, Layer 4 access control, Layer 4 CC, etc. -- is handled by the sister skill `alibabacloud-ddoscoo-port-config-migration`. **Do NOT** use this skill for those.

**Architecture**: `DDoS Pro -> 16 describe APIs -> 20 config dimensions -> YAML v2.0 (proxy/client/server/security) <-> YAML -> 4-phase submission -> DDoS Pro`

**Typical Scenarios**:
- Disaster recovery backup: Export full configuration to local YAML for version control
- Configuration audit: Export and diff to reconcile online configuration changes
- Rollback after misconfiguration: Import a previous YAML version to restore
- Batch import: Import a standard template YAML to multiple domains

## Environment Setup

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
>
> **[MUST] CLI Environment Configuration:**
> ```bash
> aliyun configure set --auto-plugin-install true
> aliyun plugin update
> ```

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `<SESSION_ID>` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ddoscoo describe-web-rules --domain 'example.com' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

**Script / Terraform execution:** When running Python SDK scripts or Terraform commands or bash scripts, inject the session-id via inline environment variable so the code can read it at runtime:

```bash
# Python SDK script
SKILL_SESSION_ID=<SESSION_ID> python3 scripts/deploy.py

# Terraform
SKILL_SESSION_ID=<SESSION_ID> terraform apply
```

Scripts and Terraform configs should read `SKILL_SESSION_ID` from the environment (default to empty string if absent).

## Credential Verification

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (`echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is strictly forbidden)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```

## RAM Policy

Required RAM permissions are detailed in [references/ram-policies.md](references/ram-policies.md).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** -- Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, domain list, instance ID, output path,
> conflict strategy, etc.) MUST be confirmed with the user. Do NOT assume or use default values
> without explicit user approval.

| Parameter | Required/Optional | Description | Default |
| --------- | ----------------- | ----------- | ------- |
| Mode | Required | export / import | - |
| Region | Required | `cn-hangzhou` (mainland China) / `ap-southeast-1` (international) | - |
| Domain Scope | Required | Single domain / Multiple domains / Per instance / Full account | - |
| YAML File Path | Required | Input or output file path | - |
| Import Conflict Strategy | Required for import | skip / overwrite | skip |
| Target Instance | Optional for import | When the instance ID in the YAML does not exist in the target environment, guide the user to select; auto-pass if matched | Source instance ID from YAML |

> **Region Isolation Warning**: `cn-hangzhou` (mainland China DDoS Pro) and `ap-southeast-1` (international DDoS Pro) are **two completely independent regions**.
> Domain lists, instances, and configurations are not shared between them. The same account may have domains in both regions, but a single execution only covers one region.
>
> **Before execution, you MUST explicitly ask the user**:
> 1. Which region are the business domains deployed in? (cn-hangzhou / ap-southeast-1 / both)
> 2. If both, **the skill MUST be run twice separately**, each time specifying the region explicitly -- do NOT mix them
> 3. **NEVER default or guess** the region; if the user's answer is ambiguous, keep asking until it is clear
>
> The purpose of this rule is to prevent incidents where "the customer has business in both regions but only backed up one, and only discovers later that the overseas configuration was lost."

## Core Workflow

### Step 1: Mode Selection (**Must Use AskUserQuestion**)

```
Mode: [export / import]
```

### Step 2: Scope and File Path Confirmation

**Export Mode**:
- **Region (must confirm first)**: `cn-hangzhou` or `ap-southeast-1`; if the customer has domains in both regions, inform them that two separate runs are required -- this run only processes the region the user explicitly selects
- Domain scope (single domain / multiple domains / per instance / full account)
- Output path (default: one file per domain: `./{region}-{domain}-{YYYYMMDD}.yaml`)
- Whether to include security policies (CC/AI/precise access/area blocking/IP blacklist-whitelist/cache/CDN linkage)

**Import Mode**:
- **Region (must confirm first)**: Must match `exported_from.region` in the YAML; if mismatched, halt execution and raise an alert
- Input YAML file path
- Conflict strategy (skip / overwrite)

### Step 3: DDoS Pro Instance Pre-check (Shared by Export/Import)

```bash
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

- **Export**: Build the instance ID list
- **Import**: Verify target instance exists + DomainUsage capacity is sufficient + **instance mapping** (see below)

#### Step 3.5: Instance Mapping Confirmation (Import Only)

> **MUST**: Complete instance mapping before import to ensure instance IDs in the YAML correctly map to the target environment.

1. Read source instance ID list from YAML `exported_from.instance_ids`
2. Compare each against instance IDs returned by `describe-instances` in the target environment
3. **Full match** -> auto-pass, no user intervention needed
4. **Partial or full mismatch** -> Use **AskUserQuestion** to guide the user in selecting the target instance:

```
"Source instance <SOURCE_INSTANCE_ID> from the YAML does not exist in the target environment.
Please select the target instance to bind the domain to:
[A] ddoscoo-cn-xxx (used 3/50 domains, remaining capacity 47)
[B] ddoscoo-cn-yyy (used 10/50 domains, remaining capacity 40)
..."
```

5. Build mapping table: `{source instance ID -> user-selected target instance ID}`
6. Subsequent Phase 1 (`create-domain-resource --instance-ids`) uses the mapped instance IDs
7. If the target instance's remaining capacity is insufficient to accommodate the domains being imported, **alert and block execution in advance**

> **Note**: If the target environment has only one instance and its capacity is sufficient, it may be auto-selected with user notification (no prompt needed), but the mapping must still be recorded in the log.

### Step 4: Execute Export / Import

#### Export Workflow (see [references/export-workflow.md](references/export-workflow.md))

For each domain, call 16 describe APIs in order and assemble into YAML:

1. `describe-web-rules --domain <D>` -> Main access config + HTTPS/TLS/OCSP/Http2Enable/Http2HttpsEnable/Https2HttpEnable/GmCert/BlackList/WhiteList
2. `describe-l7-rs-policy --domain <D>` -> Back-to-origin policy
3. `describe-l7-us-keepalive --domain <D>` -> Persistent connections
4. `describe-headers --domain <D>` -> Back-to-origin headers
5. `describe-cname-reuses --domains <D>` -> CNAME reuse
6. `describe-web-cc-protect-switch --domains <D>` -> CC/AI switches + templates
7. `describe-web-cc-rules-v2 --domain <D>` -> CC custom rules (**filter out system AI policies prefixed with `smartcc_`**)
8. `describe-web-precise-access-rule --domains <D>` -> Precise access control
9. `describe-web-area-block-configs --domains <D>` -> Area blocking
10. `describe-web-cache-configs --domains <D>` -> Static page caching (**plural**)
11. `describe-cdn-linkage-rules --domain <D> --page-number 1 --page-size 10` -> CDN linkage
12. `aliyun ddoscoo describe-domain-security-profile --domain <D>` -> Global protection level and switches !! falls back to OpenAPI on `aliyun-cli-ddoscoo` 0.x (see edge case in [references/export-workflow.md](references/export-workflow.md#212-global-protection-level-and-switches))
13. `describe-l7-global-rule --domain <D>` -> Global protection rule details (full export)
14. `aliyun ddoscoo describe-l7cc-cookie --domain <D>` -> Cookie settings !! falls back to OpenAPI on `aliyun-cli-ddoscoo` 0.x (see edge case in [references/export-workflow.md](references/export-workflow.md#214-cookie-settings))
15. `aliyun ddoscoo describe-l7-mutual-auth-conf --domain <D>` -> Mutual authentication mTLS config !! falls back to OpenAPI on `aliyun-cli-ddoscoo` 0.x (see edge case in [references/export-workflow.md](references/export-workflow.md#215-mutual-authentication-mtls-configuration))
16. `aliyun ddoscoo describe-gm-cert-list --domain <D>` -> GM (GuoMi/SM2) certificate list (take the cert ID where `DomainMatchCert=true` and write it to `gm_cert.cert_id`) !! falls back to OpenAPI on `aliyun-cli-ddoscoo` 0.x (see edge case in [references/export-workflow.md](references/export-workflow.md#216-gm-sm2-certificate-list))

> **Plugin metadata gap & OpenAPI fallback**: APIs 12 / 14 / 15 / 16 above use the standard plugin-mode kebab-case form. When the installed `aliyun-cli-ddoscoo` plugin (0.x as of 2026-06-22) does not yet declare these actions, the plugin route rejects them with `unknown command` or `'<Action>' is not a valid api`. In that case, follow the per-API Edge case fallback block in [references/export-workflow.md](references/export-workflow.md) -- it bypasses the plugin and routes through the core CLI's built-in OpenAPI metadata. Switch back to the kebab-case primary form once a future plugin release declares these actions.

CLI parameter naming pitfalls are documented at the top of [references/export-workflow.md](references/export-workflow.md).

#### Import Workflow (see [references/import-workflow.md](references/import-workflow.md))

Submit in 4 phases; each domain is an independent transaction; if a preceding phase fails, subsequent phases for that domain are skipped:

| Phase | Content | Failure Handling |
| ----- | ------- | ---------------- |
| Phase 1: Domain entity | `create-domain-resource` or conflict detection | Fail -> skip this domain |
| Phase 2: HTTPS association | `associate-web-cert` (HTTPS domains only) + GM certificates `config-gm-cert` / `config-gm-cert-enable` / `config-gm-cert-only` !! fall back to OpenAPI on `aliyun-cli-ddoscoo` 0.x (see [import-workflow.md](references/import-workflow.md)) | Fail -> log but continue |
| Phase 3: Advanced config | `modify-ocsp-status` / `modify-tls-config` / `config-l7-mutual-authentication` (mTLS) !! / `config-l7cc-cookie-enable` (Cookie) !! / `config-l7-rs-policy` / `config-l7-us-keepalive` / `modify-headers` / `modify-cname-reuse` (!! entries fall back to OpenAPI on `aliyun-cli-ddoscoo` 0.x -- see [import-workflow.md](references/import-workflow.md)) | Fail -> log but continue |
| Phase 4: Security policies | `modify-web-cc-global-switch` / `enable-web-cc` / `enable-web-cc-rule` / `config-web-cc-template` / `config-web-cc-rule-v2` / `modify-web-ai-protect-mode` / `modify-web-ai-protect-switch` / `modify-web-precise-access-rule` / `modify-web-precise-access-switch` / `modify-web-area-block` / `modify-web-area-block-switch` / `config-web-ip-set` / `modify-web-ip-set-switch` / `modify-web-cache-switch` + `modify-web-cache-mode` + `modify-web-cache-custom-rule` / `create-scheduler-rule` + `modify-scheduler-rule` / `config-domain-security-profile` (global protection switches + level) / `config-l7-global-rule` | Fail -> log but continue |

### Step 5: Dry-run Diff (Required for Import)

Before importing, execute a dry-run and output a tri-color diff:

- Green (**new**): Domain does not currently exist
- Yellow (**override diff**): Domain exists but configuration differs (list differing fields)
- Red (**destructive**): Origin server IP / instance ID / certificate changes (requires secondary confirmation)

### Detailed Operation Steps

- Full export workflow: [references/export-workflow.md](references/export-workflow.md)
- Full import workflow: [references/import-workflow.md](references/import-workflow.md)
- YAML schema definition: [references/yaml-schema.md](references/yaml-schema.md)

## Success Verification

After import completes, run the following for each target domain:

```bash
aliyun ddoscoo describe-web-rules --domain '<DOMAIN>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Then diff against the YAML file, requiring the following key fields to match:
- `RealServers` / `ProxyTypes` (main access config)
- `OcspEnabled` / `SslProtocols` / `Ssl13Enabled` / `SslCiphers` / `Http2Enable` / `Http2HttpsEnable` / `Https2HttpEnable` (HTTPS)
- `CertName` (certificate)
- `BlackList` / `CcEnabled` (security policy baseline)

If any field mismatches, save the report to `./import-mismatch-{timestamp}.yaml` for the user to decide whether to roll back.

## Cleanup

This skill does not create cloud resources (export only reads configuration, import only modifies domain configuration), so no cloud resource cleanup is needed. Temporary files generated during execution:

- Export YAML files: Retained as backup, no cleanup needed
- `./import-result-{timestamp}.yaml`: Import result record, retained for auditing
- `./rollback-{timestamp}.yaml`: Rollback snapshot, retained for rollback purposes
- `./import-mismatch-{timestamp}.yaml`: Verification mismatch report, retained for troubleshooting

If cleanup is desired, the user may decide whether to delete these files.

## General Rules

- AK/SK must never be displayed in plaintext in the conversation; YAML files **must NEVER** contain any credential fields
- The CLI product name is `ddoscoo` (all lowercase); using `ddos` or `DDoSCoo` is strictly forbidden
- Every `aliyun` command **must** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>` (see Observability section)
- Region inference: User mentions "mainland China / China DDoS Pro" -> `cn-hangzhou`; "international / overseas" -> `ap-southeast-1`. When the region is already clear, only query that region
- **CLI parameter pitfalls**: `describe-domain-resource` uses `--domain`, but `describe-cname-reuses` / `describe-domain-cc-protect-switch` / `describe-web-cc-protect-switch` / `describe-web-precise-access-rule` / `describe-web-area-block-configs` / `describe-web-cache-configs` all use `--domains` (plural). See the pitfall table at the top of [references/export-workflow.md](references/export-workflow.md)
- Interaction principle: Mode selection, scope confirmation, conflict strategy, secondary confirmation **must use AskUserQuestion**. Never let the user hand-write JSON/API parameters
- **Import Safety Four Principles**:
  1. **Must dry-run first** with tri-color diff; execute only after user confirmation
  2. **Per-domain independent transaction**; single domain failure does not affect other domains
  3. **Phased submission**; earlier phase failure skips later phases, but security policy phase failure does not block
  4. **Failure list and rollback YAML** must be saved to disk; output file:// links to the user
- Exported YAML must not persist any sensitive information: account UID may be retained as a source marker only; AK/SK/Cert Key are strictly forbidden from export
- **Known Limitations**:
  - **IP Whitelist**: The `WhiteList` field from `describe-web-rules` only appears when the domain has a whitelist configured (not returned when the array is empty); check for field existence during export
  - **APIs not registered in CLI plugin metadata (use OpenAPI fallback)**: The following 9 ddoscoo actions are not declared in the installed `aliyun-cli-ddoscoo` plugin (0.x as of 2026-06-22). When invoked in plugin mode the plugin rejects them with `unknown command` or `'<Action>' is not a valid api`, and the skill falls back to the OpenAPI route documented per-API in `references/export-workflow.md` and `references/import-workflow.md`. The skill continues to default to the **kebab-case** primary form so that the moment a future plugin release declares these actions, no further skill changes are needed.
    - Read APIs (export): `describe-domain-security-profile`, `describe-l7cc-cookie`, `describe-l7-mutual-auth-conf`, `describe-gm-cert-list`
    - Write APIs (import): `config-gm-cert`, `config-gm-cert-enable`, `config-gm-cert-only`, `config-l7-mutual-authentication`, `config-l7cc-cookie-enable`
    - **GM (GuoMi/SM2) Certificates**: read via `describe-gm-cert-list`; write via `config-gm-cert` / `config-gm-cert-enable` / `config-gm-cert-only`. Parameters: `--domain`, `--cert-id`, `--enable`. Supports both export and import.
    - **Mutual Authentication (mTLS)**: read via `describe-l7-mutual-auth-conf`; write via `config-l7-mutual-authentication`. Full bidirectional coverage.
    - **Cookie Settings**: read via `describe-l7cc-cookie`; write via `config-l7cc-cookie-enable` (`--key` specifying `aliyungf_tc` / `cookie_secure`). Full bidirectional coverage.

## Reference Table

| File | Description |
| ---- | ----------- |
| [references/export-workflow.md](references/export-workflow.md) | Full export workflow (16 describe API orchestration + YAML generation) |
| [references/import-workflow.md](references/import-workflow.md) | Full import workflow (4-phase submission + failure handling) |
| [references/yaml-schema.md](references/yaml-schema.md) | YAML configuration file schema definition (v2.0: proxy/client/server/security four-segment structure) |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission list (see describe + write policy sections in the file) |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [references/related-commands.md](references/related-commands.md) | Full CLI command cheat sheet (16 export + 4-phase import) |
| [references/verification-method.md](references/verification-method.md) | Post-import verification steps and field mapping table |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria (correct vs. incorrect CLI command patterns) |
| [references/yaml-example.yaml](references/yaml-example.yaml) | Single domain full configuration example |
