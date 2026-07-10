# Function Compute Deployment Issues
Call yunxiao_flow_get_job_step_log.py to get step logs. Based on the log information and knowledge base, further analyze the root cause and provide solutions. Before analyzing, make sure to clarify the following questions:
* What build cluster is the job using
* What build environment is the job using
* What is the job workspace
* Whether the current step has cloned code. Check the "Download Pipeline Source" option in the corresponding job: ["Download All Pipeline Sources", "Do Not Download Pipeline Sources", "Download Partial Pipeline Sources"]
* What branch and commit were used for code cloning
* What is the build environment. The default environment only supports Function Compute 2.0. Specified container environment supports Function Compute 3.0. Function Compute 2.0 requires creating a service before creating a function. Function Compute 3.0 has no services.


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
### Error: InvalidArgument: code: 400, object 'xxxx' does not exist in 'xxxx'
**Important**: The standard approach for Yunxiao deploying FC 3.0 via OSS is to upload the deployment artifacts to the corresponding OSS bucket through the "OSS Upload" step after "Clone Code", and then the Function Compute deployment pulls the corresponding files from OSS.
- 1. Check if SOURCE_TYPE equals OSS_ZIP. This type means the function will pull a zip package of code from the OSS bucket for deployment.
- 2. Provide the configured OSS bucket, OSS file name (OSS_OBJECT_NAME), and function name (FUNC_NAME)

### Error: InvalidArgument: code: 400, Code should be only set when runtime is not custom-container
The function runtime does not match the deployment method. The function runtime uses a custom container, but the deployment selected OSS zip. Provide the configured function name (FUNC_NAME) and deployment method.

### InvalidArgument: code: 400, This function does not support third-party registry image. Please create a new function to use a third-party registry image
The function runtime does not match the deployment method. The function runtime is not using a custom container, but the step's source type selected "Custom Image". Provide the configured function name (FUNC_NAME), deployment method, and image.
