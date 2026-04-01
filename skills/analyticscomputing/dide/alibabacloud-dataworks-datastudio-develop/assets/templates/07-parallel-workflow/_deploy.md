# Deployment Command Sequence

```bash
PROJECT_ID=123456

# 1. Create workflow
# Note: Workflow spec must include script.runtime.command="WORKFLOW"
aliyun dataworks-public CreateWorkflowDefinition \
  --ProjectId $PROJECT_ID \
  --Spec "$(cat /tmp/wf.json)"
# -> Record the returned WorkflowId
WF_ID="<returned WorkflowId>"

# 2. Create prepare_data node (root node, depends on project_root)
# Note: Dependencies are configured via spec.dependencies; ensure dependencies[*].nodeId exactly matches the node id
aliyun dataworks-public CreateNode \
  --ProjectId $PROJECT_ID \
  --Scene DATAWORKS_PROJECT \
  --ContainerId $WF_ID \
  --Spec "$(cat /tmp/n1.json)"

# 3. Create process_orders node (fan-out, depends on prepare_data)
aliyun dataworks-public CreateNode \
  --ProjectId $PROJECT_ID \
  --Scene DATAWORKS_PROJECT \
  --ContainerId $WF_ID \
  --Spec "$(cat /tmp/n2.json)"

# 4. Create process_users node (fan-out, depends on prepare_data)
aliyun dataworks-public CreateNode \
  --ProjectId $PROJECT_ID \
  --Scene DATAWORKS_PROJECT \
  --ContainerId $WF_ID \
  --Spec "$(cat /tmp/n3.json)"

# 5. Create merge_report node (fan-in, depends on process_orders + process_users)
# Note: Multiple upstream dependencies are listed as multiple entries in the spec.dependencies depends array
aliyun dataworks-public CreateNode \
  --ProjectId $PROJECT_ID \
  --Scene DATAWORKS_PROJECT \
  --ContainerId $WF_ID \
  --Spec "$(cat /tmp/n4.json)"

# 6. Publish and go live
aliyun dataworks-public CreatePipelineRun \
  --ProjectId $PROJECT_ID \
  --Type Online \
  --ObjectIds "[\"$WF_ID\"]"
```
