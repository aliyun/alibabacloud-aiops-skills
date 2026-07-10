# Pipeline Variable Description
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


## Variable Usage Tips
- 1. Note that Yunxiao variables are rendered through templates. Each step performs rendering only once, so there are no self-referencing string issues.
- 2. The step related to variable substitution is exclusively "Replace Environment Variables in File". The "Replace Environment Variables in File" step cannot set variables; it can only use pipeline global variables (job.params).
- 3. Each job runs in a separate environment. Previous steps in a job can affect subsequent steps. For example, if a file is deleted in an earlier step, accessing that file in a later step will also report a file-not-found error.
- 4. Troubleshooting requires combining all step names and their order in the job, analyzing user intent, and then investigating.
- 5. Since variables have no self-referencing issues, when a variable contains another variable, multiple rounds of substitution are needed. One substitution only resolves one level of nesting. For example, if the pipeline has 3 variables: variable image has value nginx:${env}, variable env has value ${name}, variable name has value dev. After substitution, the value of image becomes nginx:${name}, not nginx:dev. When variable A contains variable B, and B's value also contains a variable, multiple rounds of substitution are needed.

**Variable Substitution Tip**:
There are three variables in the YAML to be published: ${appname}, ${image}, and ${env}. If you need to keep certain variables unsubstituted after executing "Replace Environment Variables in File", you can define them as self-referencing in the pipeline global variables. For example, if the file uses ${image}, define image=${image} in the pipeline variables. After one rendering pass, the variable remains as itself.


## Environment Variable Categories
Variables have three categories:
1. **System Variables (Built-in)** - Automatically provided by Yunxiao
2. **Pipeline User Variables (Custom)** - Defined by users in the pipeline
3. **Common Variable Groups** - Variables managed uniformly by the enterprise

---

## System Environment Variables (Built-in)

| Variable | Description | Example |
|----------|-------------|---------|
| PIPELINE_ID | Pipeline ID | 3734309 |
| BUILD_NUMBER | Pipeline run number, starting from 1, auto-incrementing | 125 |
| PIPELINE_NAME | Pipeline name | golang project build ACK deployment |
| BUILD_REMARK | Pipeline run remark | - |
| BUILD_EXECUTOR | Pipeline trigger user | xxx |
| BUILD_MESSAGE | Pipeline trigger message | xxx-Page manual trigger |
| PROJECT_DIR | Working directory for running commands | /root/workspace/1084-abc_docker-08191_b0wE |
| DATETIME | Current time | 2026-03-24-09-44-46 |
| TIMESTAMP | Current timestamp | 1774316686926 |
| CI_SOURCE_NAME | Code source name | goFlow |
| CI_COMMIT_REF_NAME | Code source branch name or Tag name (based on user selection at runtime) | master |
| CI_COMMIT_TITLE | Last commit message | Update DockerfileCache |
| CI_COMMIT_SHA | Last commit's commit ID | c02481cxxxxxxxxxx71ba |
| CI_COMMIT_ID | Last commit's 8-character commit ID (Git scenario) | c02481c1 |
| CI_COMMIT_AUTHOR | Last commit author | xxxx <xxxxxx@xxxxxxxx.com> |
| CI_COMMIT_BEFORE_SHA | Previous commit's commit ID | c02481c1f4d0d02564cea91445ba1bb00e5b71ba |
| CI_SOURCE_TYPE | Code source type | codeup |

### Multi-Code Source Variables

When multiple code sources are configured in the pipeline, the `_n` suffix is used to distinguish them:

| Variable | Description |
|----------|-------------|
| CI_SOURCE_NAME_n | nth code source name |
| CI_COMMIT_REF_NAME_n | nth code source branch name |
| CI_COMMIT_TITLE_n | nth code source commit message |
| CI_COMMIT_SHA_n | nth code source commit ID |
| CI_COMMIT_ID_n | nth code source 8-character commit ID |
| CI_COMMIT_AUTHOR_n | nth code source author |

---

## Pipeline Environment Variable Usage

### Reference Format

Variables are referenced using `${variable_name}` in the pipeline:

```bash
# Use in command steps
echo "Pipeline ID: ${PIPELINE_ID}"
echo "Branch: ${CI_COMMIT_REF_NAME}"
echo "Committer: ${CI_COMMIT_AUTHOR}"
```

### Variable Priority

```
Step output variables > Pipeline runtime input variables > Pipeline variables > Common variable groups
```

---

## Cross-Step Environment Variable Passing

### Specified Container Environment / Default VM Environment

#### Intra-task Environment Variable Passing
Environment variables shared within a single task node:
```bash
# Step 1: Generate variable
echo "yaojia_Test=myParam" >> "$FLOW_ENV"
# Step 2: Use variable
echo "Variable value: ${yaojia_Test}"
```

#### Inter-task Environment Variable Passing
Environment variables shared between multiple task nodes:
1. **Step 1**: Output environment variable to `$FLOW_ENV`
   ```bash
   echo "yaojia_Test=myParam" >> "$FLOW_ENV"
   ```
2. **Step 2**: Add "Batch Set Variables" step to set the environment variable at the pipeline level
3. **Task 2**: Use the environment variable via `${yaojia_Test}`

---

### Default Environment

#### Intra-task Environment Variable Passing
```bash
# Step 1: Generate variable (must start with USER_)
echo 'USER_abc=123' > .env
# Step 2: Use variable
echo "Variable value: ${USER_abc}"
```

**Note**: Environment variables in the `.env` file must start with `USER_`.

#### Inter-task Environment Variable Passing
1. **Step 1**: Output environment variable to `.env`
   ```bash
   echo 'USER_abc=123' > .env
   ```
2. **Step 2**: Add "Set Variable" step to set the environment variable at the pipeline level
3. **Task 2**: Use the environment variable via `${USER_abc}`


---
## Secret Variables

### Configuration Method
1. In the pipeline variable configuration, check "Secret Mode"
2. Secret variable values are hidden in logs

### Use Cases

- Usernames, passwords
- API Keys, Tokens
- Database connection strings

### Notes

- Once set, secret variable values cannot be viewed in plaintext in the console
- Secret variables are displayed as `***` in logs
- Secret variables can still be used normally in commands

---

## Common Issue Troubleshooting
### Issue 1: Variable ${xxxxx} is replaced with empty string
1. Check if the variable is defined in preceding steps/pipeline variables, and if the value is empty
2. Check if the correct passing method is used (`$FLOW_ENV` or `.env`)
3. Check if the variable name is correct (case-sensitive)


### Issue 2: Variable value contains special characters
**Symptom**: Variable values containing spaces, quotes, etc. cause command execution failures

**Solution**:
```bash
# Wrap variables in quotes
echo "${MY_VAR}"
```

### Issue 3: Inter-task variable passing fails

**Symptom**: Variables defined in Task 1 cannot be used in Task 2

**Troubleshooting Steps**:
1. Confirm whether `$FLOW_ENV` (container environment) or `.env` (default environment) is used
2. Confirm whether the "Set Variable" step was added to promote the variable to pipeline level
3. Check if the variable name follows naming conventions (cannot contain special characters like `-`)


### Issue 4: After variable substitution, $xxxx, ${xxxx}, {xxxx} format variables still remain
1. Check if the variable value contains other variables. For example, if the pipeline has 3 variables: variable image has value nginx:${env}, variable env has value ${name}, variable name has value dev. After substitution, the value of image becomes nginx:${name}, not nginx:dev. When variable A contains variable B, and B's value is also a variable, multiple rounds of substitution are needed.
2. Check if the remaining variables are wrapped in `${}`. Only variables wrapped in `${}` will be substituted. Variables with just `$xxxx` or `{xxxxx}` will not be substituted.
