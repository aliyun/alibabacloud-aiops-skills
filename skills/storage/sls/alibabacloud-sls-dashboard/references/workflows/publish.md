# Publish and delete

Specify the destination region, project and dashboard name independently of query
sources. The following commands are relative to the skill root:

    python3 scripts/dashboard.py publish --mode create --input final.json --region REGION --project PROJECT --name NAME --execute
    python3 scripts/dashboard.py publish --mode update --input final.json --snapshot source.snapshot.json --region REGION --project PROJECT --name NAME --execute
    python3 scripts/dashboard.py delete --snapshot source.snapshot.json --region REGION --project PROJECT --name NAME --execute

Without `--execute`, these operations only prepare and check locally. The flag does not
establish user authorization. Use [--profile](../datasources/api.md#connection-options)
to select an existing CLI profile and --endpoint to override the SLS service endpoint.
Both options apply to preflight checks and writes; --region is still required.

Create requires explicit `attribute.type=grid` or `free` and submits a new dashboard;
do not use it to overwrite an existing one. Update
requires a [target-bound source snapshot](edit.md) and compares it to a fresh read before writing.
This check detects observed changes; it is not an atomic compare-and-swap.

A successful write returns `status=published`, the SLS console URL, the submitted
Dashboard JSON in `dashboard`, and its prepublication validation report in
`validation`. To verify the saved configuration, read it back separately:

    python3 scripts/sls.py dashboard-get --region REGION --project PROJECT --name NAME --output saved.json

Use the same `--profile`, `--endpoint`, and `--aliyun` options as the publish
command when supplied. The service may reorder `charts[]` on readback; match charts
by their stable `title` IDs and compare their configuration without requiring the
array order to match. Review the saved configuration and check the actual page
for rendering and interactions. `WRITE_UNCERTAIN` errors include `originalCode`
and `originalMessage` from the failed request. Inspect the remote result before
retrying.

Delete checks the snapshot before removal and confirms a Dashboard-not-found result.
Removing charts within a dashboard is an [edit](edit.md) followed by update, not whole-dashboard deletion.
Readback does not verify browser rendering.
