### Shell Script Considerations
- **Avoid using `!=` in inline Python**: In shell inline Python scenarios such as `curl ... | python3 -c "..."`, `!=` gets escaped by the shell into `\!=`, causing a `SyntaxError`. Solution: write the Python script to a temporary file and then execute it

### Database Persistence
- **`mysql_store.py` INSERT uses named parameters**: The `insert_case_result` method uses `%(field)s` style named parameters and `{"run_id": run_id, **result}` dictionary unpacking. When adding a field, update all of the following together: the SQL column name list, the VALUES placeholders, and the result dictionary assignment
- **Table structure changes**: The `eval_case_result` table currently contains 23 columns (including `error_type VARCHAR(50) DEFAULT NULL`); adding a field requires an ALTER TABLE first

### Web API Structure
- **Cases API composite response**: `GET /api/runs/{id}/cases` returns both the `cases` list and the `stats` statistics object (including `error_type_distribution`); there is no separate stats endpoint
- **Stats query logic is in app.py**: The error type distribution statistics are implemented via `SELECT error_type, COUNT(*) ... WHERE status<>'pass' GROUP BY error_type`

### Evaluation Status Enums
- **case_result.status value domain**: `pass`, `db_mismatch`, `target_exec_error`, `source_exec_error`, `ddl_error`, `converter_error`, `converter_empty`, `timeout`
- **Secondary classification mechanism**: Errors in `target_exec_error` that contain specific keywords (`syntax error`, `does not exist`, `Feature not supported`, `must be type`, `cannot cast`) are re-labeled as `db_mismatch`; the error_classifier must recognize these accordingly
- **Difference between error_type and status**: status is the raw pipeline status, while error_type is the error_classifier's secondary classification result for non-pass cases (10 enum values + None)

### Frontend Template Development
- **run_detail.html follows a single-page application pattern**: It loads data via the fetch API and dynamically renders tables with JavaScript. When modifying the table header, update the `colspan` value accordingly
- **Bootstrap version**: Uses 5.3.2; the badge class format is `bg-xxx` (not `badge-xxx`)
- **Custom colors require extra CSS**: e.g. `.bg-purple` must be defined in `{% block extra_style %}`
