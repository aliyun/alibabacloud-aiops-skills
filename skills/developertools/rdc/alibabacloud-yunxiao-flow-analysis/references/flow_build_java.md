# Java Build Issues
Call yunxiao_flow_get_job_step_log.py to get step logs. Based on the log information and knowledge base, further analyze the root cause and provide solutions. Before analyzing, make sure to clarify the following questions:
* What build cluster is the job using
* What build environment is the job using
* What is the job workspace
* Whether the current step has cloned code. Check the "Download Pipeline Source" option in the corresponding job: ["Download All Pipeline Sources", "Do Not Download Pipeline Sources", "Download Partial Pipeline Sources"]
* What branch and commit were used for code cloning
* Java builds require Maven. Pay attention to the Maven version used, and what the mvn command and parameters are


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

## Maven Build Information
**Note**: It is settings.xml, NOT settings.yaml. Do NOT use YAML syntax.
**How to check the settings.xml used by mvn build**:
1. During `mvn` build, it references `/root/.m2/settings.xml` by default. If the build command specifies settings.xml via the `-s` parameter, the specified settings.xml takes priority.
2. The `Configure MavenSettings File` pipeline step downloads the Settings file from the pipeline global configuration, and it **must** be downloaded to `/root/.m2/settings.xml`. Other paths cannot be successfully referenced.
3. If the build fails, you can view the `settings.xml` used during the build via the `cat` command.


Note: **Ignore the `localRepository` in the settings.xml file**


## Common Issues
### Error: Could not resolve dependencies for project xxxxxx
1. The Maven settings.xml file does not have the repository for the corresponding dependency.
2. Check if activeProfiles in settings.xml has enabled the corresponding repository. That is, whether there is an activated `profile`, or whether a non-existent profile has been activated. Pay attention to the error `profile "xxxxx" could not be activated because it does not exist.`
3. Check if <snapshots> and <releases> in the <repository> in settings.xml/pom.xml are set to false
4. It is recommended to output the pom.xml file content via the `cat` command, and check if <repository> is configured in pom.xml. If <repository> configuration exists, further check if <snapshots> and <releases> are set to false
5. Check if the corresponding repository contains the required dependency.

### Dependency pull error: Could not resolve dependencies for project 401 Unauthorized and Not authorized
1. The `Configure MavenSettings File` pipeline step downloads the Settings file from the pipeline global configuration, and it **must** be downloaded to `/root/.m2/settings.xml`. Other paths cannot be successfully referenced.
2. Check if the settings.xml configuration file exists. By default, it references `/root/.m2/settings.xml` during build. **Note: downloading to other paths will not be referenced**. If the build command specifies settings.xml via the `-s` parameter, the specified settings.xml takes priority.
3. Check if there is an activeProfile in settings.xml, and find the corresponding repositories based on the activeProfile
4. Check if the repository id can find a corresponding `<server>` configuration with the same `<id>` under `<servers>`. If not found, the repository configuration has no authentication.
5. Check if there is an activated activeProfile. If not, add the `-P xxx` parameter during build to activate the corresponding profile.


### Dependency pull error: Authorization failed for 403 Forbidden and Access denied
1. It is recommended to check if the username and password for the corresponding `server` are correct
2. Check if the account has the required permissions. If it is a repository member role, it needs to be granted upload/download artifact permissions.

### deploy upload artifact error: Authorization failed for xxxxxxx 403 Forbidden and Access denied
1. It is recommended to check if the username and password for the corresponding `server` are correct
2. Check if the account has the required permissions. If it is a repository member role, it needs to be granted upload/download artifact permissions.

### deploy upload artifact error: Authorization failed for xxxxxxx 401 Forbidden and Not authorized
1. The `Configure MavenSettings File` pipeline step downloads the Settings file from the pipeline global configuration, and it must be downloaded to `/root/.m2/settings.xml`. Other paths cannot be successfully referenced.
2. Check if the settings.xml configuration file exists. By default, it references `/root/.m2/settings.xml` during build. **Note: downloading to other paths will not be referenced**. If the build command specifies settings.xml via the `-s` parameter, the specified settings.xml takes priority.
3. Check if there is an activeProfile in settings.xml, and find the corresponding repositories based on the activeProfile
4. Check if the repository id can find a corresponding `<server>` configuration with the same `<id>` under `<servers>`. If not found, the repository configuration has no authentication.
5. Check if there is an activated activeProfile. If not, add the `-P xxx` parameter during build to activate the corresponding profile.

### Error: xxxx is missing, no dependency information available
Further investigation is needed to determine if it is `Authorization failed`, `Unauthorized`, or `Could not resolve dependencies for project`
