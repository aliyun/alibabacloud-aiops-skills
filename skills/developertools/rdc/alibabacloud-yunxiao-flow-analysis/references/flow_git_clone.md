# Code Clone
Call yunxiao_flow_get_job_step_log.py to get step logs. Based on the log information and knowledge base, further analyze the root cause and provide solutions. Before analyzing, make sure to clarify the following questions:
* What build cluster is the job using
* What build environment is the job using
* What is the job workspace
* Whether the current step has cloned code. Check the "Download Pipeline Source" option in the corresponding job: ["Download All Pipeline Sources", "Do Not Download Pipeline Sources", "Download Partial Pipeline Sources"]
* What branch and commit were used for code cloning


**Note**:
* Build cluster name must NOT be obtained from `params.buildNodeGroup`. It **MUST** be obtained from the "Request Runtime Environment" step logs.
* Job workspace must be obtained from the `PROJECT_DIR` in the Pipeline Cache step


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

## Common Issues
### spawn git ENOENT
The `git` command needs to be installed in the private build machine or private image.

### Default value 'xxxxx' does not satisfy the filter rule
The filter rule configured in the code source must include the default branch.

### fatal: unable to access 'xxxxxx': The requested URL returned error: 403
Check if the service connection for the pipeline code source is still valid, and whether the user who created the service connection has been removed from the organization. Try switching to a service connection with proper permissions, or create a new service connection.
