# Acceptance Criteria: Yunxiao Flow Analysis

**Scenario**: Yunxiao Flow Pipeline Troubleshooting
**Purpose**: Skill testing acceptance criteria for pipeline failure diagnosis and solution recommendations

---

# Correct Script Usage Patterns

> **Authentication**: All scripts read the token exclusively from the environment variable `YUNXIAO_ACCESS_TOKEN`. Ensure it is set before running any command: `export YUNXIAO_ACCESS_TOKEN="pt-xxx"`

## 1. Pipeline Runs Retrieval

### ✅ CORRECT
```bash
python3 scripts/yunxiao_flow_get_pipeline_runs.py \
  --org-id ${org-id} \
  --pipeline-id ${pipeline-id} \
  --pipeline-runid ${pipeline-runid} \
  --domain ${domain}
```

**Validation:**
- All required parameters provided
- org-id is 32 characters (regional organization)
- Domain matches organization type
- Token format is correct (pt- prefix)

### ❌ INCORRECT
```bash
python3 scripts/yunxiao_flow_get_pipeline_runs.py \
  --org-id 123 \
  --pipeline-id ${pipeline-id} \
  --pipeline-runid ${pipeline-runid}
```

**Issues:**
- org-id length is incorrect (3 chars instead of 24 or 32)
- Missing token parameter
- Domain will default incorrectly for this org-id type

---

## 2. Job Step Log Retrieval

### ✅ CORRECT
```bash
python3 scripts/yunxiao_flow_get_job_step_log.py \
  --org-id ${org-id} \
  --pipeline-id ${pipeline-id} \
  --pipeline-runid ${pipeline-runid} \
  --job-id ${job-id} \
  --step-index ${step-index} \
  --domain openapi-rdc.aliyuncs.com \
  --full-log
```

**Validation:**
- All required parameters provided
- org-id is 24 characters (central organization)
- job-id and step-index are integers
- `--full-log` flag included for complete log

### ❌ INCORRECT
```bash
python3 scripts/yunxiao_flow_get_job_step_log.py \
  --org-id ${org-id} \
  --pipeline-id 'abc' \
  --pipeline-runid ${pipeline-runid} \
  --job-id abc \
  --step-index '0'
```

**Issues:**
- job-id is not an integer (string "abc")
- step-index is not an integer
- Missing domain (defaults to openapi-rdc.aliyuncs.com which is correct for central org, but should be explicit)

---

## 3. VM Deploy Order Retrieval

### ✅ CORRECT
```bash
python3 scripts/yunxiao_flow_get_vm_deploy_order.py \
  --org-id ${org-id} \
  --pipeline-id ${pipeline-id} \
  --deploy-order-id ${deploy-order-id} \
  --domain ${domain}
```

**Validation:**
- All required parameters provided
- org-id is 32 characters (regional organization)
- Domain is regional format (not default)
- deploy-order-id is integer

### ❌ INCORRECT
```bash
python3 scripts/yunxiao_flow_get_vm_deploy_order.py \
  --org-id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx \
  --pipeline-id ${pipeline-id} \
  --deploy-order-id ${deploy-order-id} \
  --domain openapi-rdc.aliyuncs.com
```

**Issues:**
- org-id is 32 characters (regional) but domain is central
- Will result in authentication/authorization errors

---

## 4. VM Deploy Machine Log Retrieval

### ✅ CORRECT
```bash
python3 scripts/yunxiao_flow_get_vm_deploy_machine_log.py \
  --org-id ${org-id} \
  --pipeline-id ${pipeline-id} \
  --pipeline-runid ${pipeline-runid} \
  --deploy-order-id ${deploy-order-id} \
  --machine-sn ${machine-sn} \
  --domain ${domain}
```

**Validation:**
- All required parameters provided
- machine-sn follows ECS instance ID format
- Domain matches regional organization

### ❌ INCORRECT
```bash
python3 scripts/yunxiao_flow_get_vm_deploy_machine_log.py \
  --org-id ${org-id} \
  --pipeline-id ${pipeline-id} \
  --pipeline-runid ${pipeline-runid} \
  --deploy-order-id ${deploy-order-id}
```

**Issues:**
- Missing machine-sn parameter (required)
- Without machine-sn, cannot retrieve specific machine logs

---

# Correct JSON Response Parsing Patterns

## 1. Status Extraction

### ✅ CORRECT
```python
data = json.loads(response_text)
status = data.get('status')
if status == 'SUCCESS':
    print("Pipeline succeeded")
elif status == 'FAIL':
    print("Pipeline failed")
```

### ❌ INCORRECT
```python
data = json.loads(response_text)
status = data['Status']  # Wrong case - field names are lowercase
```

---

## 2. Failure Location Finding

### ✅ CORRECT
```python
for stage in data['stages']:
    if stage['status'] == 'FAIL':
        for job in stage['jobs']:
            if job['status'] == 'FAIL':
                for step in job['steps']:
                    if step['status'] == 'fail':  # Step status is lowercase
                        return {
                            'stage': stage['name'],
                            'job': job['name'],
                            'job_id': job['id'],
                            'step': step['nodeName'],
                            'step_index': step['stepIndex']
                        }
```

### ❌ INCORRECT
```python
# Wrong: Using uppercase status field names
for stage in data['stages']:
    if stage['Status'] == 'FAIL':
        for job in stage['jobs']:
            if job['Status'] == 'FAIL':
                # Will fail to find failures
```

---

## 3. Build Cluster Identification

### ✅ CORRECT
```python
# Read log content from step log response
log_content = step_log_response['logs']

if '[Build Cluster Info] >> Cluster Name : Yunxiao China Hong Kong Build Cluster' in log_content:
    cluster_type = 'default'
elif '[Build Cluster Info] >> Cluster Name : Hangzhou VPC Build Cluster' in log_content:
    cluster_type = 'vpc'
elif '[Runner Group Info]: >> RunnerGroupName' in log_content:
    cluster_type = 'private'
```

### ❌ INCORRECT
```python
# Wrong: Reading from params instead of log content
cluster_name = job['params']['buildNodeGroup']  # This field may not exist or be accurate
```

---

# Correct Organization Type Detection

### ✅ CORRECT
```python
org_id = "${org-id}"
if len(org_id) == 24:
    org_type = "central"
    domain = "openapi-rdc.aliyuncs.com"
elif len(org_id) == 32:
    org_type = "regional"
    domain = "xxx-xxx.devops.aliyuncs.com"  # Would need specific domain
else:
    raise ValueError(f"Invalid org-id length: {len(org_id)}")
```

### ❌ INCORRECT
```python
# Wrong: Assuming all orgs use the same domain
domain = "openapi-rdc.aliyuncs.com"  # Will fail for regional orgs
```

---

# Correct Reference File Usage

### ✅ CORRECT
```python
# Select reference file based on failure scenario
failure_scenarios = {
    'DockerBuildPushACR_production': 'flow_build_docker.md',
    'DockerDeploy_production': 'flow_deploy_docker.md',
    'KubectlDeploy_production': 'flow_deploy_kubectl.md',
    'VmDeploy_production': 'flow_deploy_vm.md',
    'FcDeploy_production': 'flow_deploy_fc.md',
    'Command_production': 'flow_test_maven.md',  # Would need to determine language
}

step_type = failed_step['stepType']
reference_file = failure_scenarios.get(step_type)
if reference_file:
    read_reference(f"references/{reference_file}")
```

### ❌ INCORRECT
```python
# Wrong: Reading all reference files unnecessarily
for ref_file in os.listdir('references'):
    read_reference(f"references/{ref_file}")  # Inefficient and confusing
```

---

# Correct Output Format

### ✅ CORRECT
```python
output = """
## Pipeline Failure Analysis Report

### Basic Information
- Pipeline ID: ${pipeline-id}
- Run ID: ${pipeline-runid}
- Status: FAIL
- Failed Stage: Build Image
- Failed Job: Build and Push Image to ACR Personal Edition
- Build Cluster: Yunxiao China Hong Kong Build Cluster

### Failure Location
- Step Name: Image Build (15s)
- Step Index: 2
- Step Type: DockerBuildPushACR_production

### Error Log Summary
ERROR: failed to solve: executor failed running [/bin/sh -c pip install -r requirements.txt]: exit code 1

### Root Cause Analysis
The pip install command failed during the Docker build process. This could be due to:
1. Missing or invalid requirements.txt
2. Network connectivity issues to PyPI
3. Incompatible Python version in Docker image

### Solution Recommendations
1. Verify requirements.txt exists and is valid
2. Check network connectivity from build cluster
3. Consider using a Python base image with compatible version
"""
```

### ❌ INCORRECT
```python
# Wrong: Insufficient detail and structure
output = "Pipeline failed in step 2. Error: exit code 1. Fix requirements.txt."
```

---

# Security Best Practices

### ✅ CORRECT
```python
# Always pass token as parameter, never hardcode
def get_pipeline_runs(org_id, pipeline_id, pipeline_runid, token, domain):
    url = build_url(org_id, pipeline_id, pipeline_runid, domain)
    req = urllib.request.Request(url)
    req.add_header('x-yunxiao-token', token)  # Token passed as parameter
```

### ❌ INCORRECT
```python
# Wrong: Hardcoding token in code
TOKEN = "pt-hardcoded-token-${job-id}"  # NEVER do this
req.add_header('x-yunxiao-token', TOKEN)
```

### ❌ INCORRECT
```python
# Wrong: Printing or logging token
print(f"Using token: {token}")  # NEVER log or echo token
```

---

# Parameter Validation

### ✅ CORRECT
```python
def validate_parameters(org_id, pipeline_id, pipeline_runid, token):
    if not org_id or len(org_id) not in [24, 32]:
        raise ValueError("org-id must be 24 or 32 characters")
    if not pipeline_id or not pipeline_id.isdigit():
        raise ValueError("pipeline-id must be a positive integer")
    if not pipeline_runid or not pipeline_runid.isdigit():
        raise ValueError("pipeline-runid must be a positive integer")
    if not token or not token.startswith('pt-'):
        raise ValueError("token must start with 'pt-'")
    return True
```

### ❌ INCORRECT
```python
# Wrong: No parameter validation
def get_pipeline_runs(org_id, pipeline_id, pipeline_runid, token):
    # Will fail with cryptic errors if parameters are invalid
```

---

# Critical Success Criteria

1. **Parameter Confirmation**: Always confirm user-customizable parameters before execution
2. **Organization Type Detection**: Correctly identify org type by org-id length
3. **Domain Matching**: Use correct domain based on organization type
4. **Build Cluster Extraction**: Extract build cluster info from logs, not params
5. **Failure Location**: Traverse stages → jobs → steps correctly with proper status checking
6. **Reference Selection**: Read appropriate reference files based on failure scenario
7. **Output Format**: Provide comprehensive analysis with all required sections
8. **Security**: Never hardcode, print, or log tokens
9. **Error Handling**: Validate all parameters before making API calls
10. **Base Knowledge**: Always read `yunxiao_base.md` and `yunxiao_flow_get_pipeline_runs.md` first
