# kubectl Deployment Issues
Call yunxiao_flow_get_job_step_log.py to get step logs. Based on the log information and knowledge base, further analyze the root cause and provide solutions. Before analyzing, make sure to clarify the following questions:
* What build cluster is the job using
* What build environment is the job using
* What is the job workspace
* Whether the current step has cloned code. Check the "Download Pipeline Source" option in the corresponding job: ["Download All Pipeline Sources", "Do Not Download Pipeline Sources", "Download Partial Pipeline Sources"]
* What branch and commit were used for code cloning

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
There are two variables in the YAML to be published: ${appname} and ${image}. If you need to keep certain variables unsubstituted after executing "Replace Environment Variables in File", you can define them as self-referencing in the pipeline global variables. For example, if the file uses ${image}, define image=${image} in the pipeline variables. After one rendering pass, the variable remains as itself.


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
### File not found
The build machine does not pre-store the user's k8s files to be deployed; they need to be downloaded first. When encountering file-not-found issues, follow these steps to troubleshoot:
- 1. Check if there is a code clone step. Generally, the corresponding files need to be downloaded to the build machine through code cloning or OSS download.

### Undefined variables exist
**Important**: This step only checks for undefined variable issues, not empty variable value issues.
- 1. Based on the file content in the error message, find the variable names defined in the file, such as ${image}
- 2. Check the IMAGES in the corresponding step. Ensure that all variables in the file can be found in IMAGES. If the value of a variable in IMAGES is still another variable, then the corresponding variable must be defined in the pipeline variables, i.e., in the job's params. For example, if ${image} is defined in the file and IMAGES:{"image":"${test_image}"}, then the test_image variable must be defined in the job's params.
Fix for this type of issue:
- 1. Define the relevant variables in the corresponding step
- 2. Do not use variables in the file

### Variable is empty
**Important**: This issue does not require any fix recommendations; only identify the cause.
- 1. Check the IMAGES in the corresponding step, and look for "invisible" values such as spaces.
- 2. **Note: Variables in IMAGES will not substitute each other**. If the value of a variable in IMAGES is still another variable, then the corresponding variable must be defined in the pipeline variables, i.e., in the job's params. For example, if ${image} is defined in the file and IMAGES:{"image":"${test_image}"}, then the test_image variable must be defined in the job's params. Variables not defined in params will be replaced with empty values.
- 3. If all the above checks are normal, it means the file no longer has variables when the job reaches the deployment step. The following checks are needed:
  * a. Check if the source file defines variables. After file download (code clone), check if variables are defined at the error position in the file. If no variables are defined, the subsequent error is expected. If you cannot check directly, ask the user through conversation whether the corresponding error position in the original file has variables defined, and if so, what the variable names are.
  * b. If variables were defined at the error position after file download (code clone), it may be because other steps between the file download and the deployment step performed variable substitution on the file. You need to read the logs of every intermediate step to check if there was variable substitution in the file. **Note**: When substituting variables in the file, undefined variables will be replaced with empty values.


### Cluster connection issues
#### Cannot connect or connection timeout
- 1. Check if the address that cannot be connected is an internal network address. Yunxiao default build clusters (public build clusters) cannot access Kubernetes `api server` from the internal network. VPC build clusters and private build clusters have the network conditions to access `api server` from the internal network, but actual accessibility depends on whether the security group allows it, whether the VPCs are the same, and whether the VPC network connectivity is established.
