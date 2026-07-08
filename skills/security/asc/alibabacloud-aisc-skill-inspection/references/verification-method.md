# Verification Methods

## 1. Submission Stage Verification

Confirm the `CreateSkillFileCheck` API call succeeded:

- `success_count > 0`: At least one file was successfully submitted
- `root_task_id` is non-empty: The main task ID has been returned
- Check that each file's `success` field in `upload_results` is `true`

## 2. Polling Stage Verification

Confirm all sub-tasks have completed:

- All sub-tasks have `task_status` of `completed` or `success`
- `poll.status` is `completed` (not `timeout`)
- No API call errors occurred

## 3. Report Verification

Confirm the output report is complete:

```bash
# Verify report file exists and is valid JSON
python3 -c "import json; data=json.load(open('check-report.json')); print(f'Status: {data[\"poll\"][\"status\"]}'); print(f'Tasks: {len(data[\"poll\"][\"tasks\"])}')"
```

## 4. Verification Command Reference

```bash
# Check if report file exists
test -f ./check-report.json && echo "Report exists" || echo "Report not found"

# Validate JSON format
python3 -m json.tool ./check-report.json > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Check detection status
python3 -c "
import json
r = json.load(open('./check-report.json'))
print(f'Status: {r[\"poll\"][\"status\"]}')
print(f'Sub-tasks: {len(r[\"poll\"][\"tasks\"])}')
for t in r['poll']['tasks']:
    risks = sum(len(ri.get('ext', {})) for ri in t.get('risk_info', []))
    print(f'  - Task {t[\"id\"]}: status={t[\"task_status\"]}, risks={risks}')
"
```
