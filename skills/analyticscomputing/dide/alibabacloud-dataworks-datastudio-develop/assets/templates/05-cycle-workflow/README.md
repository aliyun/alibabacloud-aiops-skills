# Example 05: Scheduled Workflow

ETL workflow with 3 child nodes: extract (Shell) -> transform (SQL) -> load (SQL).

## File Structure

```
my_etl/
├── my_etl.spec.json           # Workflow definition
├── dataworks.properties
├── extract/
│   ├── extract.spec.json
│   ├── extract.sh
│   └── dataworks.properties
├── transform/
│   ├── transform.spec.json
│   ├── transform.sql
│   └── dataworks.properties
└── load/
    ├── load.spec.json
    ├── load.sql
    └── dataworks.properties
```

## Deployment Order

1. Create workflow -> obtain WorkflowId
2. Create extract node (ContainerId=WorkflowId)
3. Create transform node (ContainerId=WorkflowId)
4. Create load node (ContainerId=WorkflowId)
5. Publish and go live
