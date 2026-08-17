# Common Scenario Examples

The following are end-to-end scenarios, each containing: Intent classification → Product mapping → Parameter confirmation → Tool call → Success verification.

> **General conventions:**
> - All `aliyun devops` commands **must** include `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-devops/{session-id}"` where `{session-id}` is a 32-char lowercase hex string generated once per skill session, consistent across all channels. Shown explicitly in the first example of Scenario 1; omitted in subsequent commands for brevity.
> - CLI authentication uses Personal Access Token via environment variables (`ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN`, `ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID` or `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`) or command-line parameters (`--yunxiao-access-token`, `--organization-id` or `--api-base-url`). Examples below assume env vars are configured.
> - Central site (default) uses `--organization-id <ORG_ID>` (or env var) and needs no API base URL; Region site uses `--api-base-url <URL>` (or env var)
> - If unsure about CLI command names, run `aliyun devops --help | grep '<prefix>'` or `aliyun devops <command> --help`; prefix mapping:
>
> | Product | CLI prefix |
> |---------|-----------|
> | Flow | `flow-` |
> | Codeup | `codeup-` |
> | Packages | `packages-` |
> | Projex | `projex-` |
> | Testhub | `test-hub-` |
> | AppStack | `app-stack-` |
> | Organization/Base | `base-` |

---

## Scenario 1: Create a Java Maven Build Pipeline

**User instruction:** "Create a Java Maven build pipeline for me"

### 1. Intent Classification
- Verb: **create** → `create_*`
- Object: pipeline → Flow (`pipeline-management`)

### 2. Parameter Confirmation (must confirm with user first)
- Pipeline name (e.g., `java-maven-build`)
- Code repository (URL or `repositoryId`)
- Build branch (default `master`)
- Organization ID (obtain via `get_current_organization_info`)

### 3. [MUST] Preflight: collect the three environment-specific YAML values

> The pipeline YAML cannot be written from memory. Three values are **organization-specific** and every one of them is rejected server-side if guessed. Collect all three **before** composing the YAML — this costs 3 read-only calls and saves an unbounded retry loop.

**3.1 Repository clone URL → `sources.<key>.endpoint`**

```bash
# codeup-list-repositories already returns httpUrlToRepo — no extra get call needed
aliyun devops codeup-list-repositories --search <repo-name> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-devops/${SESSION_ID}"

# Or, if you already have the repository ID
aliyun devops codeup-get-repository --repository-id <REPO_ID> --user-agent "..."
```

Use the **`httpUrlToRepo`** field verbatim. **Do NOT derive the endpoint from `webUrl`** — `webUrl` carries a namespace segment that the clone URL does not, so a hand-built URL fails validation with `codeup代码仓库不存在或者无权限`:

| Field | Example value | Usable as `endpoint`? |
|-------|---------------|----------------------|
| `webUrl` | `https://<org>-<region>.devops.aliyuncs.com/codeup/<org>/backend-api` | ❌ has `/<org>/`, no `.git` |
| `httpUrlToRepo` | `https://<org>-<region>.devops.aliyuncs.com/codeup/backend-api.git` | ✅ use this |

**3.2 Codeup service connection uuid → `sources.<key>.certificate.serviceConnection`**

```bash
aliyun devops flow-list-service-connections --service-connection-type codeup \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-devops/${SESSION_ID}"
```

Use the **`uuid`** (e.g. `ndnnci57twyfjs69`), **not** the numeric `id`.

> **[MUST] `--service-connection-type` is case sensitive and the Codeup value is lowercase `codeup`.** Verified on 2026-08-13: `--service-connection-type Codeup` — the spelling the CLI `--help` documents, and the value the response reports back in its own `type` field — returns `[]`, while `codeup` returns the connection. An empty list therefore does **not** prove the organization has none. Re-run with the lowercase value before concluding anything, and never substitute a placeholder uuid: a placeholder fails validation with `服务连接[...]不存在`. If lowercase also returns `[]`, stop and tell the user to create a Codeup service connection — a pipeline cannot bind a Codeup source without one.

**3.3 Build cluster → `stages.*.jobs.*.runsOn.group`**

> **[MUST] There is no API that lists build clusters** (no CLI command, no MCP tool). `runsOn` is mandatory and cannot be omitted (`RunsOn 不允许为空`). Do **NOT** assume a `public/<region>` hosted cluster exists — many organizations have none, and the error is the same opaque `runsOn {} 不存在` whether the region is wrong or hosted clusters are simply unavailable.
>
> **The only reliable source is an existing pipeline in the same organization.** Harvest its `runsOn` block:

```bash
# Pick any existing pipeline, then read its YAML out of pipelineConfig.flow
aliyun devops flow-list-pipelines --user-agent "..."
aliyun devops flow-get-pipeline --pipeline-id <ANY_EXISTING_ID> --user-agent "..." \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['pipelineConfig']['flow'])"
```

Copy the `runsOn` block **as a whole** (both `group` and its `vm` / `container` companion key — they are not interchangeable):

| Cluster kind | Required companion key |
|-------------|------------------------|
| `private/<uuid>` (self-hosted VM group) | `vm: true` |
| `public/<region>` (hosted, only if the org actually has one) | `container: <image>` — omitting it fails with `公共构建集群必须指定 container` |

> If the harvested YAML itself contains a placeholder such as `private/<your-build-group-uuid>` (Yunxiao's own console templates ship with these), that pipeline is a template stub — harvest from a different, real pipeline instead.

### 4. Verified YAML template (build-only)

> Verified working end-to-end via `flow-create-pipeline` (returned a pipeline ID). Replace the three `<...>` slots with the values collected in Step 3; leave everything else as-is.

```yaml
sources:
  backend_api_repo:
    type: codeup
    name: backend-api
    endpoint: <httpUrlToRepo from Step 3.1>
    branch: master
    certificate:
      type: serviceConnection
      serviceConnection: <service connection uuid from Step 3.2>
stages:
  build_stage:
    name: Build
    jobs:
      maven_build_job:
        name: Maven Build
        runsOn:
          group: <runsOn group from Step 3.3>
          vm: true
        steps:
          setup_java_step:
            step: SetupJava
            name: Setup Java
            with:
              jdkVersion: "1.8"
              mavenVersion: "3.5.2"
          maven_build_step:
            step: Command
            name: Maven Build
            with:
              run: mvn -B clean package -Dmaven.test.skip=true
```

**Two schema details that are the most common cause of `yaml校验失败`:**

| Rule | Wrong | Right |
|------|-------|-------|
| The Codeup source credential is a nested **`certificate`** object | `serviceConnection: <uuid>` directly under the source → `未填写[certificate]字段` | `certificate: {type: serviceConnection, serviceConnection: <uuid>}` |
| A **build-only** pipeline must not upload artifacts | An `ArtifactUpload` step drags in a **Packages** service connection, which generators fill with a placeholder → `服务连接[your-packages-service-connection-id]不存在` | Omit the `ArtifactUpload` step entirely unless the user asked to publish artifacts |

### 5. Invocation Methods

**Alibaba Cloud CLI (preferred — you control the exact YAML):**
```bash
# Generate session-id once per session (32-char hex, consistent across all channels)
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex)")

# Get current organization info (--user-agent shown explicitly here; implicit in later examples)
aliyun devops base-get-user-by-token \
  --organization-id <ORG_ID> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-devops/${SESSION_ID}"

# Create pipeline (requires YAML content prepared in advance)
aliyun devops flow-create-pipeline \
  --organization-id <ORG_ID> \
  --name java-maven-build \
  --content "$(cat pipeline.yaml)" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-devops/${SESSION_ID}"
```

> On success this prints **only the pipeline ID** as a bare integer (e.g. `1404809`) — that is the success signal, not an error.
> Write the YAML to a file and pass `--content "$(cat pipeline.yaml)"`; inlining multi-line YAML in the shell mangles indentation.

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "get_current_organization_info", arguments: {})
```

```
use_mcp_tool(
  server_name: "yunxiao",
  tool_name: "create_pipeline_from_description",
  arguments: {
    "organizationId": "<ORG_ID>",
    "name": "java-maven-build",
    "description": "Java Maven build pipeline"
  }
)
```

> **[MUST] `create_pipeline_from_description` generates its YAML internally — you cannot correct it.** It routinely emits placeholder service connections and a hardcoded `public/cn-beijing` cluster, both of which fail validation. **The moment it returns a `yaml校验失败` / `服务连接[...]不存在` error, do not retry it and do not reword the description** — the generator will make the same substitutions again. Switch immediately to the CLI `flow-create-pipeline --content` path (or `generate_pipeline_yaml` → fix the three slots → `flow-create-pipeline --content`), which is the only path where you control the final YAML.

### 6. Success Verification

**Alibaba Cloud CLI:**
```bash
# By ID
aliyun devops flow-get-pipeline \
  --organization-id <ORG_ID> \
  --pipeline-id <RET_PIPELINE_ID>

# Or by name (verified: returns pipelineId + pipelineName)
aliyun devops flow-list-pipelines --pipeline-name <PIPELINE_NAME>
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "get_pipeline",
  arguments: { "organizationId": "<ORG_ID>", "pipelineId": "<RET_PIPELINE_ID>" })
```
Expected: Returns pipeline details with `name == java-maven-build`.

### 7. Cleanup

```bash
aliyun devops flow-delete-pipeline --pipeline-id <RET_PIPELINE_ID>   # returns true
```

---

## Scenario 2: Create a Change Request (Merge Request) from Feature Branch to Main

**User instruction:** "Create a merge request from feature/login to main"

### 1. Intent Classification
- Verb: **create** → `create_*`
- Object: change request (MR) → Codeup (`code-management`)

### 2. Parameter Confirmation
- Repository name or `repositoryId`
- `sourceBranch`: `feature/login`
- `targetBranch`: `main`
- MR title (ask user)

### 3. Invocation Methods

**Alibaba Cloud CLI:**
```bash
# Find repository
aliyun devops codeup-list-repositories \
  --organization-id <ORG_ID> \
  --search <repo-name>

# Create merge request
aliyun devops codeup-create-change-request \
  --organization-id <ORG_ID> \
  --repository-id <REPO_ID> \
  --source-project-id <REPO_ID> \
  --target-project-id <REPO_ID> \
  --source-branch feature/login \
  --target-branch main \
  --title "Feature: User login"
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "list_repositories",
  arguments: { "organizationId": "<ORG_ID>", "search": "<repo-name>" })

use_mcp_tool(server_name: "yunxiao", tool_name: "create_change_request",
  arguments: {
    "organizationId": "<ORG_ID>",
    "repositoryId": "<REPO_ID>",
    "sourceBranch": "feature/login",
    "targetBranch": "main",
    "title": "Feature: User login"
  })
```

### 4. Success Verification

**Alibaba Cloud CLI:**
```bash
aliyun devops codeup-get-change-request \
  --organization-id <ORG_ID> \
  --repository-id <REPO_ID> \
  --local-id <RET_LOCAL_ID>
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "get_change_request",
  arguments: { "organizationId": "<ORG_ID>", "repositoryId": "<REPO_ID>", "localId": "<RET_LOCAL_ID>" })
```
Expected: `state == OPENED`, `sourceBranch / targetBranch` match.

---

## Scenario 3: Create Sprint and Add Requirement Work Item

**User instruction:** "Create Sprint 5 in project XXX and add a requirement"

### 1. Intent Classification
- Verb: **create** → `create_*`
- Object: sprint + work item → Projex (`project-management`)

### 2. Parameter Confirmation
- Project name (→ `projectId`)
- Sprint start/end dates
- Work item title, type, assignee

### 3. Invocation Methods

**Alibaba Cloud CLI:**
```bash
# Search projects
aliyun devops projex-search-projects \
  --organization-id <ORG_ID>

# Create sprint
aliyun devops projex-create-sprint \
  --organization-id <ORG_ID> \
  --id <PROJECT_ID> \
  --name "Sprint 5" \
  --start-date 2026-05-12 \
  --end-date 2026-05-26 \
  --owners <USER_ID>

# List work item types (must explicitly specify category, e.g., Req / Bug / Task)
aliyun devops projex-list-workitem-types \
  --organization-id <ORG_ID> \
  --id <PROJECT_ID> \
  --category Req

# Create work item
aliyun devops projex-create-workitem \
  --organization-id <ORG_ID> \
  --space-id <PROJECT_ID> \
  --workitem-type-id <REQUIREMENT_TYPE_ID> \
  --sprint <SPRINT_ID> \
  --subject "User login feature requirement" \
  --assigned-to <USER_ID> \
  --description "Implement user login (username/password + OAuth)"
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "search_projects",
  arguments: { "organizationId": "<ORG_ID>", "keyword": "XXX" })

use_mcp_tool(server_name: "yunxiao", tool_name: "create_sprint",
  arguments: {
    "organizationId": "<ORG_ID>", "projectId": "<PROJECT_ID>",
    "name": "Sprint 5", "startDate": "2026-05-12", "endDate": "2026-05-26"
  })

use_mcp_tool(server_name: "yunxiao", tool_name: "list_work_item_types",
  arguments: { "organizationId": "<ORG_ID>", "projectId": "<PROJECT_ID>" })

use_mcp_tool(server_name: "yunxiao", tool_name: "create_work_item",
  arguments: {
    "organizationId": "<ORG_ID>", "projectId": "<PROJECT_ID>",
    "sprint": "<SPRINT_ID>",
    "workitemTypeId": "<REQUIREMENT_TYPE_ID>",
    "subject": "User login feature requirement",
    "description": "Implement user login (username/password + OAuth)"
  })
```

### 4. Success Verification

**Alibaba Cloud CLI:**
```bash
aliyun devops projex-get-sprint \ --organization-id <ORG_ID> \
  --id <PROJECT_ID> --sprint-id <SPRINT_ID>

aliyun devops projex-get-workitem \ --organization-id <ORG_ID> \
  --workitem-id <WORKITEM_ID>
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "get_sprint", arguments: {...})
use_mcp_tool(server_name: "yunxiao", tool_name: "get_work_item", arguments: {...})
```

---

## Scenario 4: Run Pipeline and View Execution Logs

**User instruction:** "Run pipeline XYZ and tell me why if it fails"

### 1. Intent Classification
- Verb: **run** → `create_pipeline_run`
- Object: pipeline → Flow

### 2. Parameter Confirmation
- Pipeline name or `pipelineId`
- Trigger branch (default: pipeline configured branch)

> **[MUST] Verified flag facts for this flow** (Flow API 2026-05-25, plugin v0.7.2). Guessing these costs a
> failed call each time:
> - `flow-create-pipeline-run` has **no** `--branch` flag. The branch goes into the `--params` JSON under
>   the key `branchModeBranchs`. A wrong key (e.g. `branch`) is **not** rejected: the run is created and
>   silently uses the pipeline's default branch, so verify the branch in the run detail afterwards.
>   Other `--params` keys: `envs` (run variables), `runningBranchs` / `runningTags` (keyed by repo URL).
> - The run id flag is `--pipeline-run-id`, not `--run-id`.
> - `flow-get-pipeline-job-run-log --job-id` takes the job id from `stages[].stageInfo.jobs[].id` in the
>   run detail. Do **not** use the `jobId` embedded in that job's `actions[].data` log URLs
>   (`/execution-component/log?jobId=...`) - it is a different, log-service id and returns
>   `404 InvalidPipelineRun.JobIdNotFound`.

### 3. Invocation Methods

**Alibaba Cloud CLI:**
```bash
# Filter pipelines by name
aliyun devops flow-list-pipelines \
  --organization-id <ORG_ID> \
  --pipeline-name XYZ

# Pre-validation: confirm pipeline exists (skip when the user already gave you the pipeline id)
aliyun devops flow-get-pipeline \
  --organization-id <ORG_ID> \
  --pipeline-id <PIPELINE_ID>

# Trigger run (on the pipeline's default branch)
aliyun devops flow-create-pipeline-run \
  --organization-id <ORG_ID> \
  --pipeline-id <PIPELINE_ID>

# Trigger run on a specific branch - branch mode pipelines only accept it inside --params
aliyun devops flow-create-pipeline-run \
  --organization-id <ORG_ID> \
  --pipeline-id <PIPELINE_ID> \
  --params '{"branchModeBranchs":"feature/new-ui"}'

# Query a specific run (flag is --pipeline-run-id) - read stages[].stageInfo.jobs[] for job ids
aliyun devops flow-get-pipeline-run \
  --organization-id <ORG_ID> \
  --pipeline-id <PIPELINE_ID> \
  --pipeline-run-id <RUN_ID>

# Query latest run
aliyun devops flow-get-latest-pipeline-run \
  --organization-id <ORG_ID> \
  --pipeline-id <PIPELINE_ID>

# Failed job logs - <JOB_ID> is stages[].stageInfo.jobs[].id of the job whose status is FAIL
aliyun devops flow-get-pipeline-job-run-log \
  --organization-id <ORG_ID> \
  --pipeline-id <PIPELINE_ID> \
  --pipeline-run-id <RUN_ID> \
  --job-id <JOB_ID>
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "list_pipelines",
  arguments: { "organizationId": "<ORG_ID>", "keyword": "XYZ" })

// Pre-validation: confirm pipeline exists and is in normal state
use_mcp_tool(server_name: "yunxiao", tool_name: "get_pipeline",
  arguments: { "organizationId": "<ORG_ID>", "pipelineId": "<PIPELINE_ID>" })

use_mcp_tool(server_name: "yunxiao", tool_name: "create_pipeline_run",
  arguments: { "organizationId": "<ORG_ID>", "pipelineId": "<PIPELINE_ID>" })

use_mcp_tool(server_name: "yunxiao", tool_name: "get_latest_pipeline_run",
  arguments: { "organizationId": "<ORG_ID>", "pipelineId": "<PIPELINE_ID>" })
```

If a job failed:
```
use_mcp_tool(server_name: "yunxiao", tool_name: "get_pipeline_job_run_log",
  arguments: { "organizationId": "<ORG_ID>", "pipelineId": "<PIPELINE_ID>",
               "pipelineRunId": "<RUN_ID>", "jobId": "<JOB_ID>" })
```

### 4. Success Verification
- `get_latest_pipeline_run.status` is `RUNNING` → `SUCCESS`
- `FAIL`: Read failed job logs and summarize failure reason

---

## Scenario 5: Code Review Workflow

**User instruction:** "Show me pending MRs and add an LGTM comment to MR #123"

### Invocation Methods

**Alibaba Cloud CLI:**
```bash
# List pending MRs
aliyun devops codeup-list-change-requests \
  --organization-id <ORG_ID> \
  --repository-id <REPO_ID> \
  --state OPENED

# Get specific MR details
aliyun devops codeup-get-change-request \
  --organization-id <ORG_ID> \
  --repository-id <REPO_ID> \
  --local-id 123

# [MUST] Get the patchset biz id first - the comment API requires it, even for a global comment
aliyun devops codeup-list-change-request-patch-sets \
  --organization-id <ORG_ID> \
  --repository-id <REPO_ID> \
  --local-id 123

# Create global comment
# All of --comment-type, --content, --draft, --local-id, --patchset-biz-id, --repository-id and
# --resolved are REQUIRED. Omitting --patchset-biz-id / --draft / --resolved fails client-side with
# "Error: --<name> is required" before any request is sent.
aliyun devops codeup-create-change-request-comment \
  --organization-id <ORG_ID> \
  --repository-id <REPO_ID> \
  --local-id 123 \
  --comment-type GLOBAL_COMMENT \
  --patchset-biz-id <PATCHSET_BIZ_ID> \
  --draft false \
  --resolved false \
  --content "LGTM! Code looks good."
```

> For an `INLINE_COMMENT`, additionally pass `--file-path`, `--line-number`, `--from-patchset-biz-id` and `--to-patchset-biz-id`.

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "list_change_requests",
  arguments: { "organizationId": "<ORG_ID>", "repositoryId": "<REPO_ID>", "state": "OPENED" })

use_mcp_tool(server_name: "yunxiao", tool_name: "get_change_request",
  arguments: { "organizationId": "<ORG_ID>", "repositoryId": "<REPO_ID>", "localId": "123" })

use_mcp_tool(server_name: "yunxiao", tool_name: "list_change_request_patch_sets",
  arguments: { "organizationId": "<ORG_ID>", "repositoryId": "<REPO_ID>", "localId": "123" })

use_mcp_tool(server_name: "yunxiao", tool_name: "create_change_request_comment",
  arguments: {
    "organizationId": "<ORG_ID>", "repositoryId": "<REPO_ID>", "localId": "123",
    "commentType": "GLOBAL_COMMENT", "content": "LGTM! Code looks good.",
    "patchSetBizId": "<PATCHSET_BIZ_ID>", "draft": false, "resolved": false
  })
```

---

## Scenario 6: Batch Create Test Cases

**User instruction:** "Create 5 test cases under the login module"

### 1. Intent Classification
- Verb: **create** → `create_*`
- Object: test cases → Testhub (`test-management`)

### 2. Parameter Confirmation
- Test repository ID (`testRepoId` — note: Testhub test repos are independent from Projex projects)
- Directory ID (`directoryId`) — **mandatory**; omitting it returns `400 目录id不能为空`
- Case title (`subject`), assignee (`assignedTo`) — `assignedTo` is marked **required** by the field config and must be an account **UUID** (from `base-get-user-by-token`), not a display name

> **Note**: `create_testcase` key parameters are `subject` (title) and `assignedTo` (user ID), not `title` / `ownerId`. Call `get_testcase_field_config` first to confirm field definitions.

> **[MUST] `--id` means different things on different Testhub commands.** Getting this wrong produces `Error: --test-repo-id is required` or an empty result:
>
> | Command | `--id` refers to | Library passed as |
> |---------|------------------|-------------------|
> | `test-hub-create-testcase` | the **library** | `--id` |
> | `test-hub-list-directories` / `test-hub-get-testcase-field-config` / `test-hub-search-testcases` | the **library** | `--id` |
> | `test-hub-get-testcase` / `test-hub-delete-testcase` | the **test case** | `--test-repo-id` |

### 3. Invocation Methods

**Alibaba Cloud CLI:**
```bash
# Get current user ID (for assignedTo - must be the UUID from the `id` field)
aliyun devops base-get-user-by-token \
  --organization-id <ORG_ID>

# Pre-validation: confirm directory exists (Testhub uses --id for testRepoId)
aliyun devops test-hub-list-directories \
  --organization-id <ORG_ID> \
  --id <TEST_REPO_ID>

# Get field configuration - also yields the option IDs for priority (see Notes)
aliyun devops test-hub-get-testcase-field-config \
  --organization-id <ORG_ID> \
  --id <TEST_REPO_ID>

# Create test case
aliyun devops test-hub-create-testcase \
  --organization-id <ORG_ID> \
  --id <TEST_REPO_ID> \
  --directory-id <DIR_ID> \
  --subject "Normal login - correct username and password" \
  --assigned-to <USER_UUID> \
  --custom-field-values '{"tc.priority":"<P1_OPTION_ID>"}' \
  --test-steps '{"contentType":"TEXT","content":[{"step":"Enter correct username and password, click login","expected":"Successfully redirected to home page"}]}'
```

> On success this returns just `{"id": "<testcaseId>"}`.

**MCP Server:**
```
// Get current user ID (for assignedTo)
use_mcp_tool(server_name: "yunxiao", tool_name: "get_current_user", arguments: {})

// Pre-validation: confirm directory exists
use_mcp_tool(server_name: "yunxiao", tool_name: "list_testcase_directories",
  arguments: { "organizationId": "<ORG_ID>", "testRepoId": "<TEST_REPO_ID>" })

// Get field configuration (confirm required fields and parameter names)
use_mcp_tool(server_name: "yunxiao", tool_name: "get_testcase_field_config",
  arguments: { "organizationId": "<ORG_ID>", "testRepoId": "<TEST_REPO_ID>" })

// Create test case (note: subject not title, assignedTo not ownerId)
use_mcp_tool(server_name: "yunxiao", tool_name: "create_testcase",
  arguments: {
    "organizationId": "<ORG_ID>",
    "testRepoId": "<TEST_REPO_ID>",
    "directoryId": "<DIR_ID>",
    "subject": "Normal login - correct username and password",
    "assignedTo": "<USER_UUID>",
    "customFieldValues": { "tc.priority": "<P1_OPTION_ID>" },
    "testSteps": {
      "contentType": "TEXT",
      "content": [
        {
          "step": "Enter correct username and password, click login",
          "expected": "Successfully redirected to home page"
        }
      ]
    }
  })
```

### 4. Success Verification

**Alibaba Cloud CLI:**
```bash
# Note the flag inversion: --id is the TEST CASE here, the library is --test-repo-id
aliyun devops test-hub-get-testcase \
  --organization-id <ORG_ID> \
  --test-repo-id <TEST_REPO_ID> \
  --id <RET_TESTCASE_ID>

# To confirm a batch in one call, filter by title instead of paging through the directory
# (shared directories accumulate hundreds of cases, so page 1 is not a reliable check)
aliyun devops test-hub-search-testcases \
  --id <TEST_REPO_ID> \
  --directory-id <DIR_ID> \
  --conditions '{"conditionGroups":[[{"fieldIdentifier":"subject","operator":"CONTAINS","value":["<RUN_ID>"],"className":"string","format":"input"}]]}'
```

> **Search can lag creation by a few seconds.** Observed once in repeated trials: three cases created back to back, but the title filter returned only two immediately afterwards, while all three existed. If the count comes up short, **wait a few seconds and search again before concluding anything failed** — and remember that `test-hub-get-testcase` on the returned IDs is authoritative, since it reads the record directly rather than an index. A create call that returned `{"id": ...}` did succeed; treat a short search result as a stale index, not a failed write.

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "get_testcase",
  arguments: { "organizationId": "<ORG_ID>", "testRepoId": "<TEST_REPO_ID>", "testcaseId": "<RET_TESTCASE_ID>" })
```
Expected: `subject` matches, `assignedTo` correct, directory assignment correct.

### 5. Notes: the two payload shapes that cause opaque failures

> **[MUST] `testSteps` must carry a `content[]` array. This is the single most common cause of `500 unknown exception`.**
>
> The trap: the **write** shape and the **read-back** shape are different, and the read-back shape looks like a valid write payload. `get_testcase` returns `stepContent` / `expectedResult` (as RICHTEXT-wrapped JSON strings) with `content: null` — the server converts `content[]` into those fields on the way in. Copying that read shape into a create call is silently accepted by the CLI and then explodes server-side with a message that names nothing:
>
> ```bash
> # WRONG -> 500 {"errorCode":"InvaildData.Failed","errorMessage":"unknown exception"}
> --test-steps '{"contentType":"TEXT","stepContent":"...","expectedResult":"..."}'
>
> # RIGHT -> {"id": "..."}
> --test-steps '{"contentType":"TEXT","content":[{"step":"...","expected":"..."}]}'
> ```
>
> `contentType` accepts only `TEXT` or `TABLE`; anything else fails fast and clearly with `400 contentType值错误，只支持TABLE,或是 TEXT`. Both accept the same `content[]` array. If you hit `unknown exception`, the fault is almost always `content[]` being absent — do not retry the same payload or start permuting unrelated parameters.

> **[MUST] `customFieldValues` on write is a key-value map whose values are option IDs**, never display labels and never an array:
>
> ```json
> // Correct: object keyed by field id, valued by the OPTION id from get_testcase_field_config
> "customFieldValues": { "tc.priority": "9bc5b756def8156c69b1609987" }
>
> // Wrong: display label as the value -> 400 invalid value for the priority field
> "customFieldValues": { "tc.priority": "P1" }
>
> // Wrong: bare field name instead of the qualified id (priority vs tc.priority)
> "customFieldValues": { "priority": "..." }
>
> // Wrong: array format
> "customFieldValues": [{ "fieldId": "priority", "value": "P1" }]
> ```
>
> Priority option IDs are **per library** — always read them from `get_testcase_field_config` (field `tc.priority`, each option carries `value` such as `P1` plus the `id` you must send). Never hardcode them. Sending a display label verbatim is rejected with `400 字段【优先级】所填值无效`.
>
> **Read-back is asymmetric by design** (this is not a failure): `customFieldValues` comes back as an *array* of field descriptors, e.g.
> `[{"fieldId":"tc.priority","fieldName":"优先级","values":[{"displayValue":"P1","identifier":"9bc5..."}]}]`.
> Priority **does** persist and is verifiable — assert on `values[].displayValue`, and do not assume the field was dropped just because the shape changed.

---

## Scenario 7: Artifact Repository Query

**User instruction:** "Check the latest artifacts in the Docker image repository"

**Alibaba Cloud CLI:**
```bash
# List artifact repositories
aliyun devops packages-list-repositories \
  --organization-id <ORG_ID>

# List artifacts in repository
aliyun devops packages-list-artifacts \
  --organization-id <ORG_ID> \
  --repository-id <DOCKER_REPO_ID> \
  --per-page 20
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "list_package_repositories",
  arguments: { "organizationId": "<ORG_ID>" })

use_mcp_tool(server_name: "yunxiao", tool_name: "list_artifacts",
  arguments: { "organizationId": "<ORG_ID>", "repositoryId": "<DOCKER_REPO_ID>", "perPage": 20 })
```

---

## Scenario 8: Application Release Workflow Progression

**User instruction:** "Promote app-x to the staging environment"

**Alibaba Cloud CLI:**
```bash
# Query release workflows
aliyun devops app-stack-list-all-release-workflow-briefs \
  --organization-id <ORG_ID> \
  --app-name app-x

# Query release stage summaries
aliyun devops app-stack-list-all-release-stage-briefs \
  --organization-id <ORG_ID> \
  --app-name app-x \
  --release-workflow-sn <WF_SN>

# Execute staging pipeline
aliyun devops app-stack-execute-change-request-release-stage \
  --organization-id <ORG_ID> \
  --app-name app-x \
  --release-workflow-sn <WF_SN> \
  --release-stage-sn <STAGE_SN_PREPROD>
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "list_app_release_workflows",
  arguments: { "organizationId": "<ORG_ID>", "appName": "app-x" })

use_mcp_tool(server_name: "yunxiao", tool_name: "list_app_release_stage_briefs",
  arguments: { "organizationId": "<ORG_ID>", "appName": "app-x", "workflowSn": "<WF_SN>" })

use_mcp_tool(server_name: "yunxiao", tool_name: "execute_app_release_stage",
  arguments: { "organizationId": "<ORG_ID>", "appName": "app-x",
               "workflowSn": "<WF_SN>", "stageSn": "<STAGE_SN_PREPROD>" })
```

Verification:

**Alibaba Cloud CLI:**
```bash
aliyun devops app-stack-list-app-release-stage-runs \
  --organization-id <ORG_ID> \
  --app-name app-x \
  --release-workflow-sn <WF_SN> \
  --release-stage-sn <STAGE_SN_PREPROD>
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "list_app_release_stage_runs",
  arguments: { "organizationId": "<ORG_ID>", "appName": "app-x",
               "workflowSn": "<WF_SN>", "stageSn": "<STAGE_SN_PREPROD>" })
```

---

## Scenario 9: Smart Time-Range Pipeline Query

**User instruction:** "What pipelines have run in the last week?"

**Alibaba Cloud CLI:**
```bash
# CLI does not support natural-language time; convert "last week" to millisecond timestamps
aliyun devops flow-list-pipelines \
  --organization-id <ORG_ID> \
  --execute-start-time $(($(date +%s) * 1000 - 7 * 24 * 3600 * 1000)) \
  --execute-end-time $(($(date +%s) * 1000))
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "smart_list_pipelines",
  arguments: { "organizationId": "<ORG_ID>", "timeRange": "last week" })
```
`smart_list_pipelines` supports natural-language time expressions ("today", "this week", "last month").

---

## Scenario 10: Application Variable Group Query

**User instruction:** "Check the variable groups for app-x in the production environment"

**Alibaba Cloud CLI:**
```bash
aliyun devops app-stack-get-app-variable-groups \
  --organization-id <ORG_ID> \
  --app-name app-x \
  --env-name prod
```

**MCP Server:**
```
use_mcp_tool(server_name: "yunxiao", tool_name: "get_app_variable_groups",
  arguments: { "organizationId": "<ORG_ID>", "appName": "app-x", "envName": "prod" })
```
