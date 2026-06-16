# Pipeline Custom Environment Build (CustomEnvironmentBuild)
Call yunxiao_flow_get_job_step_log.py to get step logs. Based on the log information and knowledge base, further analyze the root cause and provide solutions. Before analyzing, make sure to clarify the following questions:
* What build cluster is the job using
* What build environment is the job using
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


## Common Issues
### Step runs timeout with no log output
**Symptom**: The step's runtime exceeded the timeout (timeoutMinutes, in minutes), causing failure.
**Solution**: This is generally caused by the container image missing the `root` user or not having `jq` installed.
