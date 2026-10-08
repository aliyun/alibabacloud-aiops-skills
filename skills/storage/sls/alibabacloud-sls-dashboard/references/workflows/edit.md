# Edit, append, and remove existing content

1. Fetch complete JSON with [sls.py dashboard-get](../datasources/api.md), or use a supplied local file.
   Keep source.json unchanged as the local baseline. When publishing an update,
   bind that baseline to the destination with dashboard.py snapshot --input source.json
   --region REGION --project PROJECT --name NAME --output source.snapshot.json.
2. Identify target charts by `title` and original content; resolve duplicate titles. Copy source.json to a working file.
3. Verify missing data facts. Pure [display edits](../features/appearance.md) do not require discovery.
4. Patch existing JSON directly. For additions, build an additions-only [Plan](../model/plan.md) and run
   dashboard.py merge-additions --base working.json --additions additions.json
   --output final.json. Preserve existing order and place new panels in [unoccupied layout space](../features/layout.md).
5. Review dashboard.py diff --before source.json --after final.json.
   Run dashboard.py validate --input final.json --baseline source.json.
6. [Publish](publish.md) once when authorized. Reconcile remote changes before updating.

Before removing charts, check [row children](../charts/dashboardrow.md), [variables](../features/variables.md)
and [links](../features/actions.md). Do not turn all existing JSON into a Plan.
See [copy/import](../integrations/copy-and-import.md).
