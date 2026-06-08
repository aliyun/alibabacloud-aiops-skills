# Acceptance Criteria: alibabacloud-aes-ack-pod-performance-profiling

**Scenario**: SysOM Pod-level performance profiling for ACK clusters (CPU throttling, OOM, memory distribution, network jitter, IO latency).
**Purpose**: Skill testing acceptance criteria.

---

## Correct CLI Command Patterns

### 1. Product — verify product name exists

#### CORRECT
```bash
aliyun sysom invoke-diagnosis ...
aliyun sysom get-diagnosis-result ...
aliyun sysom initial-sysom ...
aliyun cs GET /clusters/<cluster_id> ...
aliyun sts get-caller-identity ...
```

#### INCORRECT (described in prose to avoid being mistaken for runnable examples — PascalCase API tokens are PROHIBITED under SA-2.11)

- Wrong product casing: invoking the SysOM service through the uppercase product name `SysOM` instead of the lowercase plugin-mode product `sysom`.
- Wrong product alias: invoking SysOM through the non-existent product alias `ack` (e.g., `ack invoke-diagnosis ...`).
- Wrong action casing: invoking SysOM diagnosis through the traditional ROA-style PascalCase action name (e.g., `InvokeDiagnosis`) instead of the plugin-mode lowercase-hyphenated form `invoke-diagnosis`.

### 2. Command — verify action exists under the product

#### CORRECT
```bash
aliyun sysom invoke-diagnosis
aliyun sysom get-diagnosis-result
aliyun sysom initial-sysom --check-only false --source aes-skills
aliyun cs GET /clusters/<cluster_id>
```

#### INCORRECT (described in prose; PascalCase tokens are PROHIBITED under SA-2.11)

Wrong: traditional ROA-style PascalCase API names instead of plugin mode — invoking SysOM via the uppercase action names `InvokeDiagnosis`, `GetDiagnosisResult`, or `InitialSysom`. Always use the plugin-mode lowercase-hyphenated form `invoke-diagnosis`, `get-diagnosis-result`, `initial-sysom`.

### 3. Parameters — verify each parameter name exists

#### CORRECT
```bash
# invoke-diagnosis (params keys are snake_case; product MUST be "ACK"; instance MUST be ack-<cluster_id>)
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel ecs \
  --params '{"product":"ACK","region":"cn-hangzhou","instance":"ack-c0ee8f62dd10541c598af3627d5b6cda7","cluster_id":"c0ee8f62dd10541c598af3627d5b6cda7","namespace":"default","pod":"test-app-64cdcb7b98-gchks","description":"","start_time":0,"end_time":0,"enable_diagnosis":true}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling

# get-diagnosis-result
aliyun sysom get-diagnosis-result \
  --task-id <task_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling

# initial-sysom
aliyun sysom initial-sysom \
  --check-only false \
  --source aes-skills \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling

# Cluster lookup (CS uses ROA path)
aliyun cs GET /clusters/<cluster_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

#### INCORRECT
```bash
# Wrong: parameter names not correct
aliyun sysom invoke-diagnosis --serviceName ocd       # should be --service-name
aliyun sysom invoke-diagnosis --service-name ocd --channel ack  # channel MUST be ecs
aliyun sysom get-diagnosis-result --taskId <id>       # should be --task-id

# Wrong: invoke-diagnosis params use camelCase or miss product/instance
aliyun sysom invoke-diagnosis --params '{"clusterId":"cxxx","podName":"p"}'   # snake_case required
aliyun sysom invoke-diagnosis --params '{"product":"ack","instance":"cxxx"}'  # product MUST be uppercase "ACK"; instance MUST be ack-<cluster_id>

# Wrong: missing required base fields (product / region / instance / cluster_id / namespace / pod)
aliyun sysom invoke-diagnosis --params '{"namespace":"default","pod":"p"}'

# Wrong: instance contains characters outside ^[a-zA-Z0-9_-]*$ (e.g., raw cluster name with spaces or non-ASCII characters)
aliyun sysom invoke-diagnosis --params '{"instance":"my cluster name with spaces","...":"..."}'
```

### 4. VPC Endpoint Connection — verify SDK usage pattern

#### CORRECT
```bash
# SDK environment initialization (run once)
bash scripts/setup-sdk.sh

# Create cluster VPC endpoint connection (REQUIRED prerequisite for diagnosis)
.sysom-sdk-venv/bin/python scripts/create-cluster-vpc-endpoint-connection.py \
  --region "cn-hangzhou" \
  --cluster-id "c0ee8f62dd10541c598af3627d5b6cda7" \
  --dry-run "false"
```

#### INCORRECT (described in prose to avoid validator flagging the PascalCase token)

Wrong: trying to invoke the cluster VPC endpoint creation through the CLI by using the PascalCase action name `CreateClusterVpcEndpointConnection`. The CLI does NOT support this action; the only supported mechanism is the SDK script `scripts/create-cluster-vpc-endpoint-connection.py`.

```bash
# Wrong: using system python3 instead of the venv interpreter
python3 scripts/create-cluster-vpc-endpoint-connection.py ...

# Wrong: pip install instead of setup-sdk.sh (no venv created)
pip install alibabacloud_sysom20231230
```

### 5. --user-agent flag rule

#### CORRECT
```bash
# Business commands (cs / sysom / sts) MUST carry the request --user-agent flag
aliyun cs GET /clusters/<cluster_id>             --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
aliyun sysom invoke-diagnosis ... --user-agent   AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
aliyun sysom get-diagnosis-result ... --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
aliyun sts get-caller-identity --user-agent        AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling

# System / tooling commands MUST NOT carry --user-agent
aliyun configure list
aliyun configure set --auto-plugin-install true
aliyun version
aliyun plugin update

# ALLOWED-EXCEPTION: 'aliyun configure ai-mode set-user-agent --user-agent <value>' — here --user-agent
# is the REQUIRED ARGUMENT of the config-setter subcommand, not a request HTTP header
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling"  # ALLOWED-EXCEPTION: config-setter argument, not a request header
```

#### INCORRECT

Prohibited patterns (described in prose to avoid being mistaken for runnable examples):

- Missing the `--user-agent` request flag on business commands such as `aliyun sysom invoke-diagnosis`, `aliyun sysom get-diagnosis-result`, `aliyun cs GET /clusters/<cluster_id>`, or `aliyun sts get-caller-identity`.
- Attaching the `--user-agent` request flag to any system / tooling command. The following system commands MUST NOT carry `--user-agent`: `configure list`, `configure set`, `configure get`, `version`, `plugin update`, `plugin install`, `plugin list`, `help`, `upgrade`.
- Using an incomplete user-agent value where the `AlibabaCloud-Agent-Skills/` prefix is present but the `alibabacloud-aes-ack-pod-performance-profiling` skill-name suffix that must follow the trailing slash is missing.
- Using a user-agent whose skill-name suffix does not match this skill (for example, suffix `/alibabacloud-aes-sysom-ack-diagnosis` or `/alibabacloud-aes-sysom-os-diagnosis`).

---

## Credential Verification Pattern

#### CORRECT
```bash
aliyun configure list
```
Inspect the output for a valid profile (AK, STS, or OAuth identity). If absent, STOP and guide the user to configure credentials outside the session.

#### INCORRECT
```bash
# Wrong: print AK/SK values
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
aliyun configure list | grep -i secret

# Wrong: pass plaintext credentials on the command line
aliyun configure set --access-key-id LTAI5tXXXXXX --access-key-secret 8dXXXXXXXX

# Wrong: ask the user to paste AK/SK in the conversation
```

---

## Parameter Handling

#### CORRECT
- Confirm ALL user-customizable parameters with the user before execution: `cluster_id`, `region`, `namespace`, `pod`, `description`, `start_time`, `end_time`.
- After calling `describe-cluster-detail` (via `aliyun cs GET /clusters/<cluster_id>`), validate `profile == "Default"`. Only standard ACK clusters are supported.
- `description` MAY contain Chinese characters (ACK SysOM accepts non-ASCII description, unlike ECS OCD).
- `instance` is auto-derived as `ack-<cluster_id>`; never accept it as user input.
- When the user's request contains any temporal reference ("this morning", "yesterday afternoon", "around 3pm", "last night"), proactively ask for the specific time range and recommend historical diagnosis mode (`enable_diagnosis=false`, `start_time`/`end_time` set).

#### INCORRECT
- Assuming `region=cn-hangzhou` without asking or extracting from the cluster lookup response.
- Using the raw cluster `name` as `instance` (may contain Chinese / spaces, violating regex `^[a-zA-Z0-9_-]*$`).
- Silently defaulting to real-time diagnosis when the user clearly described a past event.
- Skipping the parameter-confirmation gate before invoking diagnosis.
- Proceeding with diagnosis when `profile != "Default"` (e.g., `acs`, `Serverless`, `Edge`) — these cluster types are not supported.

---

## Diagnosis Mode Decision

#### CORRECT
```
if enable_diagnosis == true:
    mode = real-time      # enable_diagnosis has highest priority
elif start_time != 0:
    mode = historical     # retrospective analysis on a time window
else:
    mode = real-time      # default
```

- Real-time: `start_time=0`, `end_time=0`, `enable_diagnosis=true`
- Historical: `start_time=<unix_ts>`, `end_time=<unix_ts>`, `enable_diagnosis=false`

#### INCORRECT
- Setting `enable_diagnosis=true` together with non-zero `start_time`/`end_time` (the engine ignores the time range).
- Submitting `start_time > end_time` or future timestamps.

---

## Write-Operation Confirmation Gate

#### CORRECT
Before running `scripts/create-cluster-vpc-endpoint-connection.py` with `--dry-run "false"`, the agent MUST display a write-operation banner showing `cluster_id`, `region`, and impact, then wait for explicit user confirmation (Y/N). Proceed only on Y.

#### INCORRECT
- Running the VPC endpoint creation silently without user confirmation.
- Treating it as a read-only step.
- Skipping the banner because "the diagnosis cannot proceed without it".

---

## Polling Behavior Lockdown

While polling `aliyun sysom get-diagnosis-result` (interval 10s, max 60 attempts), the following are STRICTLY FORBIDDEN — both executing and suggesting to the user:

#### FORBIDDEN
- Executing kubectl commands on the cluster.
- Calling ECS monitoring, CloudMonitor, or any other diagnostic API.
- Initiating a new `invoke-diagnosis` task or attempting "alternative diagnosis methods".
- Calling any command not listed in this skill's command tables.
- Suggesting any of the above to the user as "fallback options".

#### PERMITTED
- Continuing to call `aliyun sysom get-diagnosis-result` to poll.
- Stopping after the timeout and outputting the prescribed timeout template.

---

## CLI Plugin Mode Format

#### CORRECT
```bash
aliyun sysom invoke-diagnosis      # lower-case + hyphens
aliyun sysom get-diagnosis-result
aliyun sysom initial-sysom
```

#### INCORRECT (described in prose; PascalCase tokens are PROHIBITED under SA-2.11)

The following traditional ROA-style PascalCase API names MUST NOT appear on any `aliyun` CLI invocation line: `InvokeDiagnosis`, `GetDiagnosisResult`, `InitialSysom`. Always use the plugin-mode lowercase-hyphenated form (`invoke-diagnosis`, `get-diagnosis-result`, `initial-sysom`).

---

## Cleanup

#### CORRECT
```bash
# After all CLI operations complete, disable AI-Mode
aliyun configure ai-mode disable
```

#### INCORRECT
- Leaving AI-Mode enabled after the diagnosis session ends.
- Running cleanup commands while a polling loop is still in progress.

---

## Out-of-Scope Scenarios (MUST refuse or redirect)

- Windows-based container workloads.
- Serverless Kubernetes (ASK) clusters.
- Pods in `Pending` state (not yet scheduled to a node).
- Virtual nodes / Elastic Container Instance (ECI) Pods.
- ACS Serverless Container Pods.
