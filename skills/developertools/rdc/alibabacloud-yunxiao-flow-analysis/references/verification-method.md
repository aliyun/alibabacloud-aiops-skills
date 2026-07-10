# Verification Methods

This document provides step-by-step verification methods to ensure the Yunxiao Flow Analysis skill is working correctly at each stage of the troubleshooting workflow.

> **Authentication**: All scripts read the token exclusively from the environment variable `YUNXIAO_ACCESS_TOKEN`. Ensure it is set before running any command: `export YUNXIAO_ACCESS_TOKEN="pt-xxx"`

---

## Step 1: Pipeline Runs Retrieval Verification

### Verification Command

```bash
python3 scripts/yunxiao_flow_get_pipeline_runs.py \
  --org-id <org-id> \
  --pipeline-id <pipeline-id> \
  --pipeline-runid <pipeline-runid> \
  --domain <domain>
```

### Expected Output

**Valid JSON Response** with the following structure:

```json
{
  "org_id": "64c1c73fa4a9f6530c595e17",
  "pipelineId": 3734309,
  "pipelineRunId": 125,
  "status": "FAIL",
  "stageGroup": [["Group0-Stage0"], ["Group1-Stage0", "Group1-Stage1"]],
  "groups": [{"name": "默认", "id": 1}],
  "pipelineType": null,
  "stages": [...]
}
```

### Verification Checklist

- [ ] Command executes without errors
- [ ] Returns valid JSON (can be parsed with `json.loads()`)
- [ ] `status` field is one of: SUCCESS, FAIL, RUNNING, INIT
- [ ] `stages` array is not empty
- [ ] Each stage has `name`, `status`, `id`, `stage_index`, `jobs` fields
- [ ] Each job has `id`, `name`, `status`, `startTime`, `endTime`, `steps`, `params`, `result` fields
- [ ] Each step has `nodeName`, `stepIndex`, `status`, `stepType` fields

### Common Issues and Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| Invalid token | Returns 401 error | Verify token format and validity |
| Wrong org-id | Returns 403/404 error | Check org-id length (24 or 32 chars) |
| Wrong domain | Connection timeout | Match domain to org type (central vs regional) |

---

## Step 2: Job Step Log Retrieval Verification

### Verification Command

```bash
python3 scripts/yunxiao_flow_get_job_step_log.py \
  --org-id <org-id> \
  --pipeline-id <pipeline-id> \
  --pipeline-runid <pipeline-runid> \
  --job-id <job-id> \
  --step-index <step-index> \
  --domain <domain> \
  --full-log
```

### Expected Output

**Valid JSON Response** with the following structure:

```json
{
  "last": 150,
  "logs": "[2024-04-13 10:30:45] 申请运行环境\n[2024-04-13 10:30:46] 克隆代码\n[2024-04-13 10:30:50] 执行命令\n...",
  "more": false
}
```

### Verification Checklist

- [ ] Command executes without errors
- [ ] Returns valid JSON
- [ ] `last` field is a number indicating total log lines
- [ ] `logs` field is a string containing actual log content
- [ ] `more` field is a boolean indicating if more logs exist
- [ ] Log content is readable and contains expected step output
- [ ] For "申请运行环境" step, verify build cluster info is present
- [ ] For "克隆代码" step, verify git clone information is present

### Build Cluster Verification

Check for these patterns in logs:

```python
# Default cluster
if '[Build Cluster Info] >> Cluster Name : Yunxiao China Hong Kong Build Cluster' in logs:
    print("✓ Default build cluster detected")

# VPC cluster
elif '[Build Cluster Info] >> Cluster Name : Hangzhou VPC Build Cluster' in logs:
    print("✓ VPC build cluster detected")

# Private cluster
elif '[Runner Group Info]: >> RunnerGroupName' in logs:
    print("✓ Private build cluster detected")

else:
    print("✗ Build cluster info not found")
```

### Code Clone Verification

Check for git clone information:

```python
# Look for git clone patterns
if 'git clone' in logs or 'Cloning into' in logs:
    print("✓ Code clone detected")
    # Extract branch and commit
    import re
    branch_match = re.search(r'branch[\'\"]?\s*[:=]\s*[\'\"]?([^\'\"\s]+)', logs)
    commit_match = re.search(r'commit[\'\"]?\s*[:=]\s*[\'\"]?([a-f0-9]+)', logs)
    if branch_match:
        print(f"✓ Branch: {branch_match.group(1)}")
    if commit_match:
        print(f"✓ Commit: {commit_match.group(1)}")
else:
    print("✗ Code clone info not found")
```

---

## Step 3: VM Deploy Order Verification

### Verification Command

```bash
python3 scripts/yunxiao_flow_get_vm_deploy_order.py \
  --org-id <org-id> \
  --pipeline-id <pipeline-id> \
  --deploy-order-id <deploy-order-id> \
  --domain <domain>
```

### Expected Output

**Valid JSON Response** with the following structure:

```json
{
  "deployOrderId": 67890,
  "pipelineId": 3734309,
  "pipelineRunId": 125,
  "status": "FAIL",
  "machines": [
    {
      "machineSn": "i-bp1234567890abcdef",
      "ip": "192.168.1.100",
      "status": "FAIL"
    }
  ]
}
```

### Verification Checklist

- [ ] Command executes without errors
- [ ] Returns valid JSON
- [ ] `deployOrderId` matches input
- [ ] `machines` array is not empty (for deployment steps)
- [ ] Each machine has `machineSn`, `ip`, `status` fields
- [ ] Can extract `machineSn` for next step

---

## Step 4: VM Deploy Machine Log Verification

### Verification Command

```bash
python3 scripts/yunxiao_flow_get_vm_deploy_machine_log.py \
  --org-id <org-id> \
  --pipeline-id <pipeline-id> \
  --pipeline-runid <pipeline-runid> \
  --deploy-order-id <deploy-order-id> \
  --machine-sn <machine-sn> \
  --domain <domain>
```

### Expected Output

**Valid JSON Response** with deployment log content.

### Verification Checklist

- [ ] Command executes without errors
- [ ] Returns valid JSON with log content
- [ ] Logs contain deployment commands and their output
- [ ] Error messages (if any) are clearly visible in logs

---

## End-to-End Workflow Verification

### Complete Verification Script

```python
#!/usr/bin/env python3
"""
Complete workflow verification for Yunxiao Flow Analysis skill
"""

import json
import sys
import os

def verify_pipeline_runs(org_id, pipeline_id, pipeline_runid, domain):
    """Verify Step 1: Pipeline runs retrieval"""
    print("=" * 60)
    print("Step 1: Verifying Pipeline Runs Retrieval")
    print("=" * 60)
    
    cmd = f"""python3 scripts/yunxiao_flow_get_pipeline_runs.py \\
      --org-id {org_id} \\
      --pipeline-id {pipeline_id} \\
      --pipeline-runid {pipeline_runid} \\
      --domain {domain}"""
    
    result = os.popen(cmd).read()
    
    try:
        data = json.loads(result)
        print("✓ Valid JSON response received")
        print(f"  Status: {data.get('status')}")
        print(f"  Stages count: {len(data.get('stages', []))}")
        
        # Find failure location
        for stage in data.get('stages', []):
            if stage.get('status') == 'FAIL':
                print(f"  Failed Stage: {stage.get('name')}")
                for job in stage.get('jobs', []):
                    if job.get('status') == 'FAIL':
                        print(f"    Failed Job: {job.get('name')}")
                        print(f"    Job ID: {job.get('id')}")
                        for step in job.get('steps', []):
                            if step.get('status') == 'fail':
                                print(f"      Failed Step: {step.get('nodeName')}")
                                print(f"      Step Index: {step.get('stepIndex')}")
                                return {
                                    'job_id': job.get('id'),
                                    'step_index': step.get('stepIndex')
                                }
        
        print("✗ No failures found")
        return None
        
    except json.JSONDecodeError:
        print("✗ Invalid JSON response")
        print(f"  Raw output: {result[:200]}...")
        return None

def verify_job_step_log(org_id, pipeline_id, pipeline_runid, job_id, step_index, domain):
    """Verify Step 2: Job step log retrieval"""
    print("\n" + "=" * 60)
    print("Step 2: Verifying Job Step Log Retrieval")
    print("=" * 60)
    
    cmd = f"""python3 scripts/yunxiao_flow_get_job_step_log.py \\
      --org-id {org_id} \\
      --pipeline-id {pipeline_id} \\
      --pipeline-runid {pipeline_runid} \\
      --job-id {job_id} \\
      --step-index {step_index} \\
      --domain {domain} \\
      --full-log"""
    
    result = os.popen(cmd).read()
    
    try:
        data = json.loads(result)
        print("✓ Valid JSON response received")
        print(f"  Total log lines: {data.get('last')}")
        print(f"  Logs preview: {data.get('logs', '')[:100]}...")
        
        # Verify build cluster info
        logs = data.get('logs', '')
        if '[Build Cluster Info]' in logs:
            print("✓ Build cluster info found")
        elif '[Runner Group Info]' in logs:
            print("✓ Private build cluster info found")
        else:
            print("⚠ Build cluster info not found in this step")
        
        # Verify code clone info
        if 'git clone' in logs or 'Cloning into' in logs:
            print("✓ Code clone info found")
        
        return True
        
    except json.JSONDecodeError:
        print("✗ Invalid JSON response")
        print(f"  Raw output: {result[:200]}...")
        return False

def main():
    """Main verification workflow"""
    if len(sys.argv) < 5:
        print("Usage: python verify_workflow.py <org-id> <pipeline-id> <pipeline-runid> <domain>")
        print("Note: Token must be set via environment variable YUNXIAO_ACCESS_TOKEN")
        sys.exit(1)
    
    org_id = sys.argv[1]
    pipeline_id = sys.argv[2]
    pipeline_runid = sys.argv[3]
    domain = sys.argv[4]
    
    print("Starting Yunxiao Flow Analysis Skill Verification")
    print(f"  Org ID: {org_id}")
    print(f"  Pipeline ID: {pipeline_id}")
    print(f"  Pipeline Run ID: {pipeline_runid}")
    print(f"  Domain: {domain}")
    
    # Step 1: Get pipeline runs
    failure_info = verify_pipeline_runs(org_id, pipeline_id, pipeline_runid, domain)
    
    if failure_info:
        # Step 2: Get failed step log
        verify_job_step_log(
            org_id, pipeline_id, pipeline_runid,
            failure_info['job_id'],
            failure_info['step_index'],
            domain
        )
    
    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)

if __name__ == '__main__':
    main()
```

### Running Complete Verification

```bash
python3 verify_workflow.py \
  <org-id> \
  <pipeline-id> \
  <pipeline-runid> \
  <domain>
```

---

## Success Criteria

### Overall Skill Success

The skill is working correctly if:

1. **All API calls succeed** - No authentication or network errors
2. **Valid JSON responses** - All scripts return parseable JSON
3. **Correct data extraction** - Can find failure location and extract required information
4. **Build cluster identified** - Build cluster type correctly extracted from logs
5. **Code clone info found** - Branch and commit information extracted when applicable
6. **References accessible** - Can read and use reference files for analysis
7. **Comprehensive output** - Final analysis includes all required sections

### Minimal Working Example

```python
# Minimal verification that skill works
import json
import os

# Test pipeline runs
result = os.popen(f"""python3 scripts/yunxiao_flow_get_pipeline_runs.py \\
  --org-id {org_id} --pipeline-id {pipeline_id} --pipeline-runid {pipeline_runid} \\
  --domain {domain}""").read()

data = json.loads(result)
assert 'stages' in data
assert 'status' in data

print("✓ Skill is working correctly")
```

---

## Troubleshooting Verification Failures

### Issue: Script returns 401 error

**Cause:** Invalid or expired token

**Solution:**
1. Verify token format: `pt-xxxx`
2. Check token validity in Yunxiao Console
3. Generate new token if expired

### Issue: Script returns 403/404 error

**Cause:** Wrong org-id or domain

**Solution:**
1. Verify org-id length (24 for central, 32 for regional)
2. Match domain to org type:
   - Central: `openapi-rdc.aliyuncs.com`
   - Regional: `xxx-xxx.devops.aliyuncs.com`

### Issue: No failures found in pipeline

**Cause:** Pipeline succeeded or still running

**Solution:**
1. Verify pipeline status is `FAIL`
2. Wait for pipeline to complete if `RUNNING`
3. Check correct pipeline-runid

### Issue: Build cluster info not found

**Cause:** Wrong step analyzed or incomplete logs

**Solution:**
1. Always check "Request Runtime Environment" step for build cluster info
2. Use `--full-log` flag to get complete logs
3. Verify step log retrieval with correct step-index

---

## Reference File Verification

### Verify All References Are Accessible

```python
import os

reference_files = [
    'troubleshooting-guide.md',
    'yunxiao_base.md',
    'yunxiao_flow_get_pipeline_runs.md',
    'flow_build_docker.md',
    'flow_deploy_docker.md',
    'flow_deploy_kubectl.md',
    'flow_deploy_vm.md',
    'flow_deploy_fc.md',
    'flow_test_python.md',
    'flow_test_maven.md',
    'flow_test_nodeJS.md',
    'flow_test_golang.md',
    'flow_test_php.md',
    'flow_variables.md',
    'flow_workspace_runtime.md',
    'related-commands.md',
    'acceptance-criteria.md',
    'verification-method.md'
]

print("Verifying reference files...")
for ref_file in reference_files:
    path = f"references/{ref_file}"
    if os.path.exists(path):
        with open(path, 'r') as f:
            content = f.read()
        print(f"✓ {ref_file} ({len(content)} bytes)")
    else:
        print(f"✗ {ref_file} - NOT FOUND")
```