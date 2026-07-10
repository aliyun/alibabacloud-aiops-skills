# VM Deployment Issues
Call yunxiao_flow_get_job_step_log.py to get step logs. Based on the log information and knowledge base, further analyze the root cause and provide solutions. Before analyzing, make sure to clarify the following questions:
* What build cluster is the job using
* What build environment is the job using
* What is the job workspace
* Whether the current step has cloned code. Check the "Download Pipeline Source" option in the corresponding job: ["Download All Pipeline Sources", "Do Not Download Pipeline Sources", "Download Partial Pipeline Sources"]
* Confirm whether artifacts are downloaded during deployment. Check needPackage under the deploy job's params. true means artifacts need to be downloaded.
* Confirm which user executes the deployment command on the host. Check execute_user under the deploy job's params.
* When artifacts need to be downloaded, confirm the storage path on the host. Check package_download_path under the deploy job's params.
* The user's deployment script can be found in execute_cmd under the deploy job's params.

**Note**:
- 1. Build cluster name must NOT be obtained from `params.buildNodeGroup`. It **MUST** be obtained from the "Request Runtime Environment" step logs.
- 2. Job workspace must be obtained from the `PROJECT_DIR` in the Pipeline Cache step
- 3. For variable-related issues, you **MUST** read the variable-related knowledge base.
- 4. Note that Yunxiao variables are rendered through templates. Each step performs rendering only once, so there are no self-referencing string issues.
- 5. The step related to variable substitution is exclusively "Replace Environment Variables in File". The "Replace Environment Variables in File" step cannot set variables; it can only use pipeline global variables (job.params).
- 6. Each job runs in a separate environment. Previous steps in a job can affect subsequent steps. For example, if a file is deleted in an earlier step, accessing that file in a later step will also report a file-not-found error.
- 7. Troubleshooting requires combining all step names and their order in the job, analyzing user intent, and then investigating.
- 8. Troubleshooting only needs to output the cause; fix recommendations are not required.

**Tips**:
Shell statements written in execute_cmd can directly reference pipeline variables using the `${xxxx}` format.


Yunxiao default build clusters are currently only available in three regions: Beijing, Hangzhou, and Hong Kong. Beijing and Hangzhou are in mainland China and cannot directly access overseas repositories. The Hong Kong region can access overseas repositories.
Build cluster sample logs:
```json
[Build Cluster Info]
>> Cluster Name    : Yunxiao China Hong Kong Build Cluster
```
VPC build cluster (managed build cluster), supports Shanghai, Beijing, Shenzhen, Hangzhou, Singapore (ap-southeast-1), sample log:
```json
[Build Cluster Info]
>> Cluster Name    : Hangzhou VPC Build Cluster
```
Private build cluster log:
```json
[Runner Group Info]:
>> RunnerGroupId   : xxxxx
>> RunnerGroupName : xxxxx
```

## Job Working Directory
Job workspace must be obtained from the `PROJECT_DIR` in the Pipeline Cache step

## terminalUrl
If the job has debug mode enabled (i.e., the debugPolicy field in the job's params object is not none), you can request the terminalUrl from the user to log into the build machine and execute shell commands to troubleshoot issues and verify solutions. Since the terminalUrl link has a time limit, use `webTerminal.py` to connect first before troubleshooting or solution verification.
**Note**: Executing any upload commands is prohibited. Every command executed and its results must be displayed. Execute `exit` to quit when troubleshooting is complete. Commands need a newline character \n  to trigger execution.

## Troubleshooting Steps
### Step 1: Get Deployment Order Details
Call `yunxiao_flow_get_vm_deploy_order.py` to get detailed information about the VM deployment order, including deployment status, batch progress, deployment machine list, etc.

```bash
python3 scripts/yunxiao_flow_get_vm_deploy_order.py \
  --org-id <org-id> \
  --pipeline-id <pipeline-id> \
  --deploy-order-id <deploy-order-id> \
  --domain <domain>
```

**Parameters**:
- `--org-id`: Organization ID (required for central edition)
- `--pipeline-id`: Pipeline ID
- `--deploy-order-id`: Deployment order ID
- `--domain`: Domain name (default: openapi-rdc.aliyuncs.com)

Token is read from environment variable `YUNXIAO_ACCESS_TOKEN`.


### Step 2: Get Deployment Logs
Find the machineSn of the corresponding machine from Step 1, then call `yunxiao_flow_get_vm_deploy_machine_log.py` to get VM deployment logs.

**Usage example**:
```bash
python3 scripts/yunxiao_flow_get_vm_deploy_machine_log.py \
  --org-id 5ebbc0228123212b59xxxxx \
  --pipeline-id 123 \
  --deploy-order-id 1111 \
  --machine-sn asssssssxsx
```

### Step 3: Analyze Based on Problem Description, Deployment Order Details, and Pipeline Run Status
Based on the problem description, prioritize analyzing deployment order details and deployment logs. For issues related to pipeline variables or build artifacts, analyze the pipeline run status.

## Common Issues
### Pipeline succeeds but application deployment fails
If the pipeline succeeds, it means no exit occurred during deployment. You need to check the specific deployment logs for any error messages.
