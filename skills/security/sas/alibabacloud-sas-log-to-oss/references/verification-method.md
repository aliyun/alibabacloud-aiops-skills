# Success Verification Method

## Scenario Goal Verification

**Expected Outcome**: SLS logs are successfully exported to the OSS Bucket, and the export task status is `RUNNING`

### Verification Steps

#### 1. Verify export task is created and running

```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py list-exports \
  --project <your-sls-project>
```

**Success Indicator**: The target task appears in the output list with status `[RUNNING]`

#### 2. Verify export task details

```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py get-export \
  --project <your-sls-project> \
  --name export-<logstore-name>-to-oss
```

**Success Indicator**: Task details output is correct, including:
- `Status: RUNNING`
- Correct LogStore name
- Correct OSS Bucket name
- Correct OSS prefix path

#### 3. Verify OSS data has been generated

After waiting for the buffer interval (default 300 seconds), check whether data files have been generated in the OSS Bucket:

```bash
# Check using ossutil or OSS console
ossutil ls oss://<your-oss-bucket>/sls-export/<logstore-name>/
```

**Success Indicator**: Data files exist in the OSS Bucket with partition-format naming, for example:
```
oss://<bucket>/sls-export/<logstore>/2024/01/15/10/30_<random-id>.json
```

#### 4. Verify batch creation results

Check the summary output after batch creation:

**Success Indicator**:
- Output shows `Success: N` and `Failed: 0`
- Existing tasks show as `[SKIPPED]`

## Data Integrity Rules

1. **Never modify API output**: Do NOT alter, rename, or transliterate any field values returned by the API or script (e.g., LogStore names, Bucket names, task names, status values). Always output original values verbatim. Copy values programmatically (e.g., via JSON parsing or shell pipes) instead of retyping them by hand — manual retyping introduces typos (e.g., `RUNING` instead of `RUNNING`) or wrongly "corrected" names.
2. **Post-operation verification**: After executing `delete-export` or `create-export`, you MUST run `list-exports` or `get-export` to verify the operation took effect. If the verification result contradicts the operation result (e.g., task still shows `RUNNING` after deletion), report the discrepancy to the user.
3. **Accurate counting**: When summarizing or counting results (e.g., task distribution by Bucket, number of tasks), you MUST parse the raw API or script output line by line and count exact occurrences. Do NOT use words like "approximately", "about", "~", "约", or round numbers. If the output is truncated or incomplete, explicitly state "Output truncated — exact count unavailable" and request the user to rerun the command with pagination or full output enabled.

## Common Issue Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Task status is `STOPPED` | Task was manually stopped | Run `start-export` to start it |
| No data in OSS | Buffer interval not yet reached | Wait for `buffer-interval` seconds and check again |
| Creation failed: already exist | Task name already exists | Use the existing task or choose a different name |
| Creation failed: WORM | Bucket has WORM policy enabled | Use a different Bucket or disable WORM |
| Creation failed: cross-region | SLS and OSS are in different regions | Ensure they are in the same region |
