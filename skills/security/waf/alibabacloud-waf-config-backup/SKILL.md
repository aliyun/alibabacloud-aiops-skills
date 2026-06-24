---
name: alibabacloud-waf-config-backup
description: |
  Full-configuration backup of Alibaba Cloud WAF 3.0 to a single multi-sheet Excel workbook.
  Covers all onboarding types (CNAME / cloud-product / hybrid-cloud), defense policies (11 rule types),
  and template-to-resource binding relationships.
  Auto-detects account topology (single UID vs. delegated administrator under WAF 3.0 multi-account
  unified management); under the delegated-administrator scenario each row is tagged with the
  resolved member-account OwnerUid and a dedicated member-account sheet is appended.
  Use when the user needs "WAF config backup", "WAF full export", "WAF disaster-recovery snapshot",
  "WAF config audit", "export WAF domains and rules", "WAF migration inventory", or
  "WAF multi-account / delegated-administrator backup".
---

# Alibaba Cloud WAF 3.0 Full Configuration Backup

One-command, full-configuration backup of all WAF 3.0 instances under an account into a single structured Excel workbook. Produces a complete snapshot covering three onboarding types, defense policies, and the binding relationships that link them — suitable for disaster-recovery snapshots, configuration audits, delivery documentation, and migration inventories.

Supports Chinese mainland site (aliyun.com) and International site (alibabacloud.com), merging both Chinese mainland and non-Chinese mainland instances under the same account.

Supports two account topologies under WAF 3.0 multi-account unified management:

- **Single UID** — the executing account directly owns the WAF instances and resources.
- **Delegated administrator** — the executing account is the WAF delegated administrator under a Resource Directory; each protected resource may belong to a different member account, and the workbook resolves and labels every row with its real owning UID.

The scenario is auto-detected at runtime and shown both in the filename (UID prefix) and in the Summary sheet.

> Scope: **backup / export only**. This skill never performs write operations (no create / modify / delete). It is safe to run against production.

### DR-grade backup principle

Every object is exported in two complementary forms so the snapshot is sufficient to **reconstruct** the configuration, not just inventory it:

1. **Human-readable parsed columns** — friendly views (ports, conditions, actions, timeouts, etc.) for audit and quick reading.
2. **Full untruncated raw JSON column** — each CNAME domain, defense rule, template, and binding row carries a complete `Raw JSON` column holding the exact API payload. Because rule `Config` structures differ per DefenseScene and may change across API versions, the raw column guarantees no field is ever silently dropped — it is the authoritative source for rebuild.

> **Reconstruction caveats (cannot be captured by any read-only API):** TLS certificate private keys are not exportable — the `Cert ID` / `Cert Name` are references; the certificate must already exist (or be re-uploaded) in the target account before rebuild. Likewise, cloud-product onboarding (ALB/CLB/ECS) depends on those product instances existing first.

## What Gets Exported

```
Account topology (probed once)
├── Caller identity           ← sts get-caller-identity                    (caller UID, used as filename prefix)
├── Delegated-admin status    ← DescribeAccountDelegatedStatus           (single-UID vs. delegated administrator)
└── Member accounts (delegated-admin only)
    ├── Member list           ← DescribeMemberAccounts                   (account ID / name / status + raw JSON)
    └── Resource → owner UID  ← DescribeDefenseResourceOwnerUid          (per-region OwnerUid map for row tagging)

WAF 3.0 Instance (per region)
├── Instance info               ← DescribeInstance                         (edition, paytype, expiry, quotas + raw JSON)
├── Onboarding config
│   ├── CNAME domains          ← DescribeDomains + DescribeDomainDetail   (full listen/redirect/cert + raw JSON)
│   ├── Cloud-product access   ← DescribeCloudResources                  (best-effort + raw JSON)
│   └── Hybrid-cloud access    ← DescribeHybridCloudResources            (best-effort + raw JSON)
├── Protected objects          ← DescribeDefenseResources (no template filter) (full standalone inventory + raw JSON)
├── Protected-object groups    ← DescribeDefenseResourceGroups            (group → members + raw JSON)
├── Defense templates          ← DescribeDefenseTemplates                (id/type/origin/status + raw JSON)
├── Defense policies
│   └── 11 DefenseScene types  ← DescribeDefenseRules                    (parsed + full untruncated Config JSON)
└── Binding relationships
    └── Template → protected objects ← DescribeDefenseResources (per template) (template id + pattern + detail + raw JSON)
```

Member-scoped sheets (CNAME / Cloud Resource / Hybrid Cloud / Protected Objects / Bindings) carry an `OwnerUid` first column. Under the single-UID scenario this column is hidden by default (value-redundant — every row equals the caller UID); under the delegated-administrator scenario it is shown and resolved from the per-region `ResourceName → OwnerUid` map (with caller UID as fallback). Admin-scoped sheets (Instance Info / Object Groups / Templates / Defense Rules) do **not** carry this column — these resources have no member-account ownership semantics.

### Excel Workbook Structure

| Sheet | Content |
|-------|---------|
| `Summary` | Dashboard: backup metadata + caller UID + scenario (single UID / delegated administrator + member count) + counts per region |
| `Instance Info` | WAF instance specification + full raw JSON |
| `Member Accounts` | Member account inventory (only present in the delegated-administrator scenario): account ID / name / status / description / join time |
| `Guide` | Embedded documentation for rebuilding |
| `CNAME (CN)` / `CNAME (Intl)` | CNAME onboarding: ports, backends, TLS, cert + raw JSON |
| `Cloud Resource (CN)` / `(Intl)` | Cloud-product onboarding + raw JSON (skipped if none) |
| `Hybrid Cloud (CN)` / `(Intl)` | Hybrid-cloud onboarding + raw JSON (skipped if none) |
| `Protected Objects (CN)` / `(Intl)` | Full object inventory + raw JSON |
| `Object Groups (CN)` / `(Intl)` | Object groups → members + raw JSON (skipped if none) |
| `Templates (CN)` / `(Intl)` | Defense templates + raw JSON |
| `{SceneLabel} (CN)` / `(Intl)` | Defense rules per type + full Config JSON (skipped if empty) |
| `Bindings (CN)` / `(Intl)` | Template → object mapping + raw JSON |
| `Changes (Diff)` | Rule-level diff vs the auto-discovered baseline (Added / Removed / Modified across RuleName / Status / Action / Conditions). Skipped when `--no-diff` is set or when no baseline is found |

> Region: `CN` = cn-hangzhou, `Intl` = ap-southeast-1. Empty combinations are skipped.
>
> Member-scoped sheets (CNAME, Cloud Resource, Hybrid Cloud, Protected Objects, Bindings) carry an `OwnerUid` first column; the column is hidden in single-UID runs and shown in delegated-administrator runs. Admin-scoped sheets (Instance Info, Object Groups, Templates, Defense Rules) have no such column.
>
> Diff is **on by default**: the script auto-discovers the most recent `waf_config_backup_<caller_uid>_*[_lang].xlsx` in the output directory (excluding the current run, matching language) and compares against it. The baseline filename is recorded in Summary Row 5. Use `--prev <path>` to override auto-discovery, or `--no-diff` to disable diff entirely.

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md).

```bash
aliyun version
```

**Pre-check: Aliyun CLI plugin update required**

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

Python dependency:

```bash
pip install "openpyxl>=3.1.2"
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

> International site users must configure a separate profile (e.g., `aliyun configure --profile intl`). Chinese mainland and International site AKs are NOT interchangeable.

## RAM Policy

The RAM user must have read-only WAF permissions. Recommended: attach `AliyunYundunWAFReadOnlyAccess`.

See [references/ram-policies.md](references/ram-policies.md) for the full permission list.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read [references/ram-policies.md](references/ram-policies.md) to get the full list of permissions required by this SKILL
> 2. Guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **Parameter Confirmation** — No user interaction needed. All parameters use sensible defaults.
> Directly proceed to Core Workflow.

| Parameter | Description | Default |
|-----------|-------------|---------|
| RegionId | Always query both regions (cn-hangzhou + ap-southeast-1) | Both |
| InstanceId | Auto-discovered | — |
| Dimensions | Export all dimensions | All |
| CLI Profile | Uses default profile; pass `--profile <name>` if user specifies | default |
| Output File | Filename embeds caller UID (auto-detected) and timestamp; bilingual mode appends `_zh` / `_en` | `waf_config_backup_<UID>_YYYYMMDD_HHMMSS.xlsx` (or `..._<lang>.xlsx` under `--lang all`); UID falls back to `unknown` only if `sts get-caller-identity` fails |

## Core Workflow

### Observability (MUST run before any command)

Generate a random session ID (32-char lowercase hex string) once per skill invocation:

```bash
SKILL_SESSION_ID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null | tr -d '-' || uuidgen | tr -d '-' | tr 'A-F' 'a-f')"
```

Every business API command (including `aliyun waf-openapi ...` and `aliyun sts ...`) MUST carry `--user-agent` with the session ID:

```bash
aliyun waf-openapi describe-instance --region cn-hangzhou --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-config-backup/${SKILL_SESSION_ID}"
```

UA template format:

```
AlibabaCloud-Agent-Skills/alibabacloud-waf-config-backup/${SKILL_SESSION_ID}
```

> **Rules:**
> - All business API commands (e.g., `aliyun waf-openapi describe-instance`, `aliyun sts get-caller-identity`) carry `--user-agent`.
> - System commands (`aliyun configure`, `aliyun version`, `aliyun plugin`) MUST NOT carry `--user-agent`.
> - Do not place PII in the user-agent string.
> - The bundled Python script handles `--user-agent` injection automatically.

### Step 1: Run the backup script

> **[MUST] Use the bundled script — DO NOT write your own.**
> The bundled `scripts/export_waf_config_backup.py` is the single supported entry point and already handles every scenario (single-UID, delegated administrator, unauthorized-fallback). It also injects `--user-agent`, builds the bilingual workbook, runs auto-discovery diff, and prints the contract success line `Backup complete!`. A custom replacement script (e.g. `export_waf_config.py`, `export_waf_final.py`, or any inline ad-hoc script) will miss these guarantees and is non-compliant. If the bundled script reports an error, fix the environment (CLI version / credentials / RAM policy) and rerun it — never replace it.

Run the bundled script from the skill directory:

```bash
# Default profile (Chinese mainland) — diff vs latest backup in cwd is on by default:
python3 scripts/export_waf_config_backup.py

# Specific profile (e.g., International site):
python3 scripts/export_waf_config_backup.py --profile intl

# Optional: custom output path
python3 scripts/export_waf_config_backup.py --profile intl --output /path/to/backup.xlsx

# Override auto-discovery with an explicit baseline:
python3 scripts/export_waf_config_backup.py --prev /path/to/previous_backup.xlsx

# Disable diff entirely (e.g., creating the very first baseline):
python3 scripts/export_waf_config_backup.py --no-diff
```

The script prints a per-dimension progress log and a final summary. It exits non-zero only if no WAF instance is found in either region.

### Step 2: Present the workbook

Report the output path and a one-line summary that includes:

- Detected scenario (`Single UID (<uid>)` or `Delegated Administrator (UID <uid>, N member accounts)`)
- Instance count, total domains / resources / rules / templates

Present the file with a `file://` link.

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

## Best Practices

1. Always query both regions to avoid missing dual-instance deployments.
2. DR-grade design: every row carries a full untruncated raw-JSON column as the authoritative source.
3. Certificate private keys and cloud-product instances cannot be exported — backup stores references only.
4. Empty Cloud Resource / Hybrid Cloud dimensions are normal — sheets are simply omitted.
5. The script enforces 200ms delay between calls to prevent throttling.
6. Config JSON differs across DefenseScene types — type-specific extractors plus full raw Config column.
7. IP blacklist/whitelist entries may contain internal IPs — review before sharing externally.
8. Schedule periodic runs for ongoing disaster-recovery coverage.
9. Account topology is probed once per run. The `OwnerUid` column lives only on member-scoped sheets (CNAME / Cloud Resource / Hybrid Cloud / Protected Objects / Bindings); admin-scoped sheets (Instance / Object Groups / Templates / Defense Rules) have no such column because these resources are admin-owned by definition.
10. For protected objects, the workbook keeps the API-native `OwnerUserId` column alongside the resolved `OwnerUid` first column; cross-checking the two helps detect inconsistencies in the upstream data. In single-UID runs the `OwnerUid` column is hidden by default — unhide column A to see it.
11. Diff comparison is enabled by default — the script picks the most recent `waf_config_backup_<caller_uid>_*[_lang].xlsx` in the output directory as baseline (per-language matching). Console prints `Diff vs <baseline>` (auto/explicit) or `Baseline mode: no previous backup found`; the resolved baseline is also recorded in Summary Row 5. Pass `--prev` to pin a specific baseline, or `--no-diff` to skip. Routine periodic backups need no extra flags — just rerun the script.
12. Always invoke `scripts/export_waf_config_backup.py` directly. Do not author or run a substitute backup script — the bundled script is the only one that satisfies the success-pattern contract (`Backup complete!`), the `--user-agent` rule, and the bilingual / diff / OwnerUid invariants required by this skill.

## Command Tables

See [references/related-commands.md](references/related-commands.md) for the full command reference.

## References

| Topic | Link |
|-------|------|
| RAM Policies | [references/ram-policies.md](references/ram-policies.md) |
| Related Commands | [references/related-commands.md](references/related-commands.md) |
| Verification Method | [references/verification-method.md](references/verification-method.md) |
| CLI Installation | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| API Overview | https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference/api-waf-openapi-2021-10-01-overview |
| WAF 3.0 Docs (Chinese) | https://help.aliyun.com/zh/waf/web-application-firewall-3-0/ |
| WAF 3.0 Docs (International) | https://www.alibabacloud.com/help/en/waf/web-application-firewall-3-0/ |
