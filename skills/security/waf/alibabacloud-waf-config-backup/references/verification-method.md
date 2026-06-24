# Verification Method

After running the backup script, verify the output workbook using the following steps.

## Automated Verification (Script Exit Code)

The script exits with code 0 on success, non-zero if no WAF instance is found. A successful run prints:

```
✓ Backup complete!
  Scenario: Single UID (<uid>)            # or: Delegated Administrator (UID <uid>, N member accounts)
  Instances: X | Domains: Y | Rules: Z | Templates: W
  Output: waf_config_backup_<uid>_YYYYMMDD_HHMMSS.xlsx
```

The filename embeds the caller UID (probed via `sts get-caller-identity`); under `--lang all` two files are produced with `_zh` / `_en` suffix.

## Manual Verification Steps

### 1. Summary Sheet

- Open the workbook and verify the `Summary` sheet exists
- **Row 4 must contain the caller UID and the detected scenario**, e.g.:
  - `Caller UID: <uid> (Scenario: Single UID)` or
  - `Caller UID: <uid> (Scenario: Delegated Administrator (managing N member accounts))`
- **Row 5 must contain the diff baseline line**. The English workbook (`*_en.xlsx`) uses one of:
  - `Diff baseline: <prev_filename>` (auto-discovered or explicit `--prev`)
  - `Diff baseline: none (baseline mode — no previous backup found)`
  - `Diff baseline: disabled via --no-diff`
- The Chinese workbook (`*_zh.xlsx`) uses analogous strings prefixed with the localized label; the exact strings written by the script are:

  ```
  比对基线: <prev_filename>
  比对基线: 无（基线模式 — 未发现历史备份）
  比对基线: 已通过 --no-diff 禁用
  ```
- Check backup metadata: timestamp, profile, region info
- Verify dimension counts (domains, resources, rules, templates, bindings) per region
- Counts should match what you see in the WAF console

### 2. Member Accounts Sheet (delegated-administrator scenario only)

- Present **only** when the caller is the WAF delegated administrator (single-UID runs must NOT contain this sheet)
- Columns: `Account ID / Account Name / Status / Description / Join Time`
- Account count matches the value shown in Summary Row 4
- Each member account ID also appears as the `OwnerUid` value of at least one resource in the data sheets (cross-check)

### 3. Instance Info Sheet

- Verify `Instance Info` sheet shows edition, pay type, start/end time
- Key quotas (CNAME/object/template limits) should be populated
- Full raw JSON column at the end should contain valid JSON

### 4. CNAME Sheets

- `CNAME (CN)` and/or `CNAME (Intl)` sheets present for regions with CNAME domains
- Domain count matches WAF console
- Per-port origin protocol map is populated
- Certificate metadata (CertId, CertName) present for HTTPS domains
- Raw JSON column contains complete DescribeDomainDetail payload

### 5. Cloud Resource / Hybrid Cloud Sheets

- Present only if those onboarding types exist (absence is expected, not an error)
- If present, verify resource instance IDs and product types match console

### 6. Protected Objects Sheets

- `Protected Objects (CN/Intl)` list the full standalone object inventory
- Count ≥ the number of bound objects in `Bindings` sheets
- Each row has pattern, product, target, region, status flags + raw JSON
- The `OwnerUid` first column matches the API-native `OwnerUserId` column (delegated-admin runs may show different UIDs across rows; single-UID runs show one UID throughout — column A is hidden by default in this case)

### 7. Object Groups Sheets

- Present only if object groups exist
- Group → member mapping matches console

### 8. Templates Sheets

- `Templates (CN/Intl)` list every defense template
- Verify TemplateId, type, origin, status columns
- Raw JSON contains full template metadata

### 9. Defense Rule Sheets

- One sheet per DefenseScene per region: `{SceneLabel} (CN/Intl)`
- Rule count per scene matches console
- Each row carries TemplateId, DefenseScene, parsed columns
- Full untruncated `Config (Raw JSON)` column present
- **Spot-check**: open 2–3 `custom_acl` rules — verify match-condition operator (e.g., `not-contain`) is present, not blank

### 10. Bindings Sheet

- `Bindings (CN/Intl)` links each template to protected objects
- TemplateId cross-references with Templates sheet
- Enables onboarding↔policy traceability

### 11. Raw JSON Integrity

- Every data sheet has an untruncated Raw JSON column as the last column
- Open a few cells — verify value is valid JSON (not clipped at 800 characters)
- JSON should parse without errors

### 12. OwnerUid Column (member-scoped sheets only)

The `OwnerUid` first column appears **only** on these 5 sheet families:
`CNAME`, `Cloud Resource`, `Hybrid Cloud`, `Protected Objects`, `Bindings`.
Admin-scoped sheets (`Instance Info`, `Object Groups`, `Templates`, `Defense Rules`) have no such column.

- Single-UID runs: column A is **hidden by default** (value-redundant — every row equals the caller UID). Right-click the sheet header to unhide if needed.
- Delegated-administrator runs: column A is visible; values are resolved per resource (member UID), falling back to caller UID only when `DescribeDefenseResourceOwnerUid` cannot resolve a name.
- No row should be blank in this column when other columns have data.

### 13. Idempotency

- Re-running produces a new timestamped file without overwriting prior backups
- Filename format: `waf_config_backup_<UID>_YYYYMMDD_HHMMSS.xlsx` (or `..._<lang>.xlsx` under `--lang all`)
- The UID prefix lets you co-locate snapshots of multiple accounts in the same directory without filename collisions

### 14. Changes (Diff) Sheet

Diff is **on by default**. Verification depends on the baseline state recorded in Summary Row 5:

- **Auto-discovered or explicit `--prev`**: a `Changes (Diff)` (Chinese: `变更对比`) sheet is appended; columns are `Change Type / Region / Scene / RuleId / Rule Name / Details`
  - `Added` rows (green) for rules present in the current backup but not the baseline
  - `Removed` rows (red) for rules present in the baseline but not the current backup
  - `Modified` rows (amber) for same-RuleId rules whose `Name`, `Status`, `Action`, or `Conditions` changed; the `Details` cell shows `<field>: '<prev>' → '<current>'` (values are quoted)
  - When nothing changed, the sheet contains a single ✅ row stating `No changes - rules match previous backup`
  - Console output should print `[<LANG>] Diff vs <basename> (auto)` or `(explicit)`
- **Baseline mode (no previous backup found)**: no `Changes (Diff)` sheet; console output prints `[<LANG>] Baseline mode: no previous backup found`; Summary Row 5 records the baseline-mode line
- **`--no-diff` set**: no `Changes (Diff)` sheet; console output prints `[<LANG>] Diff disabled via --no-diff`; Summary Row 5 records the disabled line

Legacy baselines (per-scene rule sheets without structured `Status` / `Action` / `Conditions` columns) still produce `Added` / `Removed` rows, plus `Modified` rows for `Name` changes; `Modified` detection on `Status` / `Action` / `Conditions` requires a baseline that already uses the merged `Defense Rules` layout (legacy baselines have empty values for those fields and are deliberately skipped to avoid noisy `'' → '<value>'` false positives).

## Quick Verification Command

```bash
# Check file exists and is non-trivial size
ls -lh waf_config_backup_*.xlsx

# Python quick check (requires openpyxl)
python3 -c "
from openpyxl import load_workbook
import sys, glob
files = sorted(glob.glob('waf_config_backup_*.xlsx'))
if not files:
    print('ERROR: No backup file found'); sys.exit(1)
wb = load_workbook(files[-1], read_only=True)
print(f'File: {files[-1]}')
print(f'Sheets ({len(wb.sheetnames)}): {wb.sheetnames}')
assert 'Summary' in wb.sheetnames, 'Missing Summary sheet'
assert 'Instance Info' in wb.sheetnames, 'Missing Instance Info sheet'
# Member Accounts sheet must appear only in delegated-admin runs
# (cross-check with Summary Row 4 scenario string)
print('✓ Basic structure verified')
"
```
