# Verification Method

## How to Verify Backup Success

### Step 1: Verify Manifest File

Check that `manifest.json` exists and is valid JSON:

```bash
cat {BACKUP_DIR}/manifest.json | python3 -m json.tool
```

Verify it contains:
- `backupTime` — timestamp of backup
- `regions` — object with entries for each scanned region
- `totalFiles` — count of all backup Excel files

### Step 2: Verify Excel Files Exist

Check that backup Excel files exist for detected instances:

```bash
find {BACKUP_DIR} -name "*.xlsx" | wc -l
```

Compare the file count against `totalFiles` in `manifest.json`.

### Step 3: WAF 3.0 Verification

For each region with WAF 3.0:

```bash
# Verify waf3-{region}.xlsx exists and list its sheets
python3 -c "
from openpyxl import load_workbook
wb = load_workbook('{BACKUP_DIR}/waf3-{region}.xlsx')
for name in wb.sheetnames:
    ws = wb[name]
    print(f'{name}: {ws.max_row - 1} data rows, {ws.max_column} columns')
"
```

Expected sheets: `instance`, `defense-resources`, `defense-resource-groups`, `defense-templates`, `defense-rules`, `template-resource-bindings`, `major-protection-black-ips`, `addresses`

### Step 4: WAF 2.0 Verification

For each region with WAF 2.0:

```bash
# Verify waf2-{region}.xlsx exists and list its sheets
python3 -c "
from openpyxl import load_workbook
wb = load_workbook('{BACKUP_DIR}/waf2-{region}.xlsx')
for name in wb.sheetnames:
    ws = wb[name]
    print(f'{name}: {ws.max_row - 1} data rows, {ws.max_column} columns')
"
```

Expected sheets: `instance-info`, `domain-names`, `protection-rules`, `protection-status`, `domain-rule-groups`

### Step 5: Spot-Check Sheet Content

Pick a sheet and verify it has proper headers and data:

```bash
# WAF 3.0 — check defense-templates sheet
python3 -c "
from openpyxl import load_workbook
wb = load_workbook('{BACKUP_DIR}/waf3-{region}.xlsx')
ws = wb['defense-templates']
for row in ws.iter_rows(max_row=3, values_only=False):
    print([cell.value for cell in row])
"

# WAF 2.0 — check protection-rules sheet
python3 -c "
from openpyxl import load_workbook
wb = load_workbook('{BACKUP_DIR}/waf2-{region}.xlsx')
ws = wb['protection-rules']
for row in ws.iter_rows(max_row=3, values_only=False):
    print([cell.value for cell in row])
"
```

### Step 6: Validate Excel Integrity

Verify all Excel files can be loaded without errors:

```bash
find {BACKUP_DIR} -name "*.xlsx" -exec python3 -c "
from openpyxl import load_workbook
import sys
try:
    wb = load_workbook(sys.argv[1])
    sheets = len(wb.sheetnames)
    total_rows = sum(wb[s].max_row - 1 for s in wb.sheetnames)
    print(f'{sys.argv[1]}: {sheets} sheets, {total_rows} total data rows')
except Exception as e:
    print(f'INVALID: {sys.argv[1]} - {e}')
" {} \;
```

## Success Criteria

- [ ] `manifest.json` exists and is valid
- [ ] Excel file count matches `totalFiles` in manifest
- [ ] WAF 3.0 `waf3-{region}.xlsx` contains "instance" sheet with instance data (if WAF 3.0 detected)
- [ ] WAF 3.0 `waf3-{region}.xlsx` contains "defense-resources" sheet with data rows (if WAF 3.0 detected)
- [ ] WAF 2.0 `waf2-{region}.xlsx` contains "domain-names" sheet with domains (if WAF 2.0 detected)
- [ ] All sheets have header rows and consistent column counts
- [ ] Excel files are openable in Excel/Numbers/WPS without issues
