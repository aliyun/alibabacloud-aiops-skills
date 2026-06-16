# Python Build Issues
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
>> Cluster Name    : xxxxxx
```
Private build cluster log:
```json
[Runner Group Info]:
>> RunnerGroupId   : xxxxx
>> RunnerGroupName : xxxxx
```

## Common Issues
### pip install public dependency reports Read timed out
You can try switching to a different pip source using the -i parameter when installing dependencies, for example:
```
pip install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple/
```
