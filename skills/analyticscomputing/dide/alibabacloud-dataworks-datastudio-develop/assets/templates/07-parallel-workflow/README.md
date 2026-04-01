# Example 07: Parallel Workflow (Fan-out + Fan-in)

Parallel ETL workflow with 4 child nodes, demonstrating fan-out and fan-in dependency patterns:

```
prepare_data (Shell)
    ├──→ process_orders (SQL)  ──┐
    └──→ process_users  (SQL)  ──┴──→ merge_report (SQL)
```

Dependency scenarios covered:
- Root node dependency (prepare_data <- project_root)
- Fan-out: multiple nodes depend on the same upstream (process_orders, process_users <- prepare_data)
- Fan-in: one node depends on multiple upstreams (merge_report <- process_orders + process_users)

## File Structure

```
parallel_etl/
├── parallel_etl.spec.json         # Workflow definition
├── dataworks.properties
├── prepare_data/
│   ├── prepare_data.spec.json
│   ├── prepare_data.sh
│   └── dataworks.properties
├── process_orders/
│   ├── process_orders.spec.json
│   ├── process_orders.sql
│   └── dataworks.properties
├── process_users/
│   ├── process_users.spec.json
│   ├── process_users.sql
│   └── dataworks.properties
└── merge_report/
    ├── merge_report.spec.json
    ├── merge_report.sql
    └── dataworks.properties
```

## Dependency Configuration Key Points

When creating nodes inside a workflow using CreateNode + ContainerId, dependencies are configured via `spec.dependencies` -- there is no need to dual-write `inputs.nodeOutputs`. Note: `spec.dependencies[*].nodeId` MUST exactly match the corresponding node's `id`, otherwise the dependency information will not be recognized.

Multi-upstream dependency (fan-in) example (merge_report depends on both process_orders and process_users):

```json
"inputs": {
  "nodeOutputs": [
    {"data": "${projectIdentifier}.process_orders", "artifactType": "NodeOutput"},
    {"data": "${projectIdentifier}.process_users", "artifactType": "NodeOutput"}
  ]
}
```

## Deployment Order

1. Create workflow -> obtain WorkflowId
2. Create prepare_data node (ContainerId=WorkflowId)
3. Create process_orders node (ContainerId=WorkflowId)
4. Create process_users node (ContainerId=WorkflowId)
5. Create merge_report node (ContainerId=WorkflowId)
6. Publish and go live

## API Verification Status

This template has been verified through CreateNode + ContainerId API testing (cn-beijing, 2026-03-28). All dependency relationships were saved correctly.
