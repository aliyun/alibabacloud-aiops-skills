# Python Unit Test
Call yunxiao_flow_get_job_step_log.py to get step logs. Based on the detailed log information and knowledge base, further analyze the root cause and provide solutions. Before analyzing, make sure to clarify the following questions:
* What build cluster is the job using
* What build environment is the job using
* What is the job workspace
* Whether the current step has cloned code. Check the "Download Pipeline Source" option in the corresponding job: ["Download All Pipeline Sources", "Do Not Download Pipeline Sources", "Download Partial Pipeline Sources"]
* What branch and commit were used for code cloning
* What testing framework and test commands are used
* What Python version is installed. Note: for specified container environments, the Python environment needs to be installed through the `Install Python` step
* What is the file path of the unit test report. Whether "Stop pipeline when test cases fail" (FAIL_ON_ERROR) is enabled


**Note**:
- 1. Build cluster name must NOT be obtained from `params.buildNodeGroup`. It **MUST** be obtained from the "Request Runtime Environment" step logs.
- 2. Job workspace must be obtained from the `PROJECT_DIR` in the Pipeline Cache step
- 3. For variable-related issues, you **MUST** read the variable-related knowledge base.
- 4. Note that Yunxiao variables are rendered through templates. Each step performs rendering only once, so there are no self-referencing string issues.
- 5. The step related to variable substitution is exclusively "Replace Environment Variables in File". The "Replace Environment Variables in File" step cannot set variables; it can only use pipeline global variables (job.params).
- 6. Each job runs in a separate environment. Previous steps in a job can affect subsequent steps. For example, if a file is deleted in an earlier step, accessing that file in a later step will also report a file-not-found error.
- 7. Troubleshooting requires combining all step names and their order in the job, analyzing user intent, and then investigating.
- 8. Troubleshooting only needs to output the cause; fix recommendations are not required.

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
### pip: command not found
- Specified container environment: Check if the job includes a step to install Python, and ensure the Python installation is placed before the command execution.

### How to prevent pipeline from pausing after pytest unit test execution fails
When executing the pytest command, you can add `|| true` at the end of the command, for example: `pytest --ignore=Python --html=report/index.html || true`. Also uncheck the "Stop pipeline when test cases fail" option in the step.

### Unit test report: step failed because of failed test case(s)
This is generally caused by checking the "Stop pipeline when test cases fail" option in the step, and there are failing test cases during unit testing. If you don't want the pipeline to stop due to failing test cases, you can uncheck the "Stop pipeline when test cases fail" option in the step.

### Test command step fails
You need to determine from the logs whether there are failing test cases or assertion errors. If these errors don't need to be concerned, you can add `|| true` at the end of the original command to force the command to succeed.
