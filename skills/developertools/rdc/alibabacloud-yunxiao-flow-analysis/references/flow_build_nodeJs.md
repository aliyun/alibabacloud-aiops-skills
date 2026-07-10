# Node.js Build Issues
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


## npm/pnpm/cnpm Build Information
1. During `npm/pnpm/cnpm` build, it references `/root/.npmrc` by default. If there is an `npmrc` file in the current directory, the current directory's `npmrc` file takes priority.
2. The `Configure .npmrc File` pipeline step downloads the `npmrc` file from the pipeline global configuration. The file should be downloaded to `/root/.npmrc` (recommended), or to the directory where the build command is executed.
3. If the build fails, you can view the `.npmrc` used during the build via the `cat` command.

## Job Working Directory
Job workspace must be obtained from the `PROJECT_DIR` in the Pipeline Cache step

## terminalUrl
If the job has debug mode enabled (i.e., the debugPolicy field in the job's params object is not none), you can request the terminalUrl from the user to log into the build machine and execute shell commands to troubleshoot issues and verify solutions. Since the terminalUrl link has a time limit, use `webTerminal.py` to connect first before troubleshooting or solution verification.
**Note**: Executing any upload commands is prohibited. Every command executed and its results must be displayed. Execute `exit` to quit when troubleshooting is complete. Commands need a newline character \n  to trigger execution.


## Common Issues
### error An unexpected error occurred "xxxxxxxx" No module found
1. First ask if the dependencies are stored in a private repository. If they are private repository dependencies, you need to configure `/root/.npmrc`, or configure `.npmrc` in the directory where the build command is executed.


### Installing Node version reports specified version not found
1. The code root directory may have a `.nvmrc` file. If this file exists, the node version in this file takes precedence.


### changeset publish fails but .npmrc is configured locally
Before executing publish, changeset will inject environment variables to override the registry. Especially when the package name starts with @, it directly reads the publishConfig field in the package's package.json. If not configured, it defaults to the official npm registry. You can try using the `pnpm publish` command to publish instead.
