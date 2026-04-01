# Deployment Command Sequence

```bash
PROJECT_ID=123456

# 1. Create workflow
# Note: Workflow spec must include script.runtime.command="WORKFLOW"
# Build spec JSON and call API
aliyun dataworks-public CreateWorkflowDefinition \
  --ProjectId $PROJECT_ID \
  --Spec "$(cat /tmp/wf.json)"
# -> Record the returned WorkflowId
WF_ID="<returned WorkflowId>"

# 2. Create extract node (root node, no upstream dependency)
# Build spec JSON and call API
aliyun dataworks-public CreateNode \
  --ProjectId $PROJECT_ID \
  --Scene DATAWORKS_PROJECT \
  --ContainerId $WF_ID \
  --Spec "$(cat /tmp/n1.json)"

# 3. Create transform node (depends on extract)
# Note: Dependencies are configured via spec.dependencies; ensure dependencies[*].nodeId exactly matches the node id
# Build spec JSON and call API
aliyun dataworks-public CreateNode \
  --ProjectId $PROJECT_ID \
  --Scene DATAWORKS_PROJECT \
  --ContainerId $WF_ID \
  --Spec "$(cat /tmp/n2.json)"

# 4. Create load node (depends on transform)
# Build spec JSON and call API
aliyun dataworks-public CreateNode \
  --ProjectId $PROJECT_ID \
  --Scene DATAWORKS_PROJECT \
  --ContainerId $WF_ID \
  --Spec "$(cat /tmp/n3.json)"

# 5. Publish and go live
aliyun dataworks-public CreatePipelineRun \
  --ProjectId $PROJECT_ID \
  --Type Online \
  --ObjectIds "[\"$WF_ID\"]"
```
