# Acceptance Criteria: alibabacloud-bailian-videoanalysis

**Scenario**: Alibaba Cloud Bailian (Quanmiao) Video Analysis
**Purpose**: Skill testing acceptance criteria

---

# Correct Python Script Usage Patterns

## 1. Environment Check

#### ✅ CORRECT
```bash
python scripts/check_env.py
```
- Returns JSON with `ready: true/false`
- Checks Python packages and credentials via default credential chain
- Does NOT read or print AK/SK values

#### ❌ INCORRECT
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID   # NEVER print credentials
python scripts/check_env.py --ak xxx --sk xxx   # NEVER pass AK/SK as arguments
```
- Credentials are checked via the default credential chain only
- The script uses `CredentialClient` internally; no manual credential passing

## 2. Workspace Listing

#### ✅ CORRECT
```bash
python scripts/list_workspace.py
```
- Returns JSON array of available workspaces
- Auto-detects workspace_id; does NOT require user to know it in advance

#### ❌ INCORRECT
```bash
python scripts/list_workspace.py --workspace_id llm-xxx   # workspace_id is not an input parameter
```
- The script lists all workspaces; workspace_id is an output, not an input

## 3. File Upload to OSS

#### ✅ CORRECT
```bash
python scripts/quanmiao_upload_file_to_oss_and_get_file_url.py --localFilePath /path/to/video.mp4
```
- Uses auto-detected bucket and generated object key by default
- Optionally specifies `--ossBucket`, `--ossObjectKey`, `--expireSeconds`

#### ❌ INCORRECT
```bash
python scripts/quanmiao_upload_file_to_oss_and_get_file_url.py   # Missing --localFilePath (required)
python scripts/quanmiao_upload_file_to_oss_and_get_file_url.py --localFilePath /path/to/video.mp4 --ossBucket ""   # Empty bucket name
```
- `--localFilePath` is required and must point to an existing file

## 4. Submit Video Analysis Task

#### ✅ CORRECT
```bash
python scripts/quanmiao_submit_videoAnalysis_task.py --workspace_id llm-xxx --file_url "https://..."
```
- workspace_id must come from Step 2 (list_workspace.py output)
- file_url must come from Step 3 (upload script output tempUrl)

#### ❌ INCORRECT
```bash
python scripts/quanmiao_submit_videoAnalysis_task.py --workspace_id fake-id --file_url "invalid-url"   # Invalid workspace_id or URL
python scripts/quanmiao_submit_videoAnalysis_task.py   # Missing required parameters
```
- Both `--workspace_id` and `--file_url` are required
- file_url must be a valid temporary OSS URL

## 5. Get Task Result

#### ✅ CORRECT
```bash
python scripts/quanmiao_get_videoAnalysis_task_result.py --workspace_id llm-xxx --task_id abc123
```
- Poll every 10-15 seconds until status is `SUCCESSED` or `FAILED`
- Handle `RUNNING` status by displaying partial results

#### ❌ INCORRECT
```bash
python scripts/quanmiao_get_videoAnalysis_task_result.py --workspace_id llm-xxx --task_id abc123 --retry 1000   # No --retry parameter exists
```
- The script returns the current task status; polling logic is handled externally
- Max retries should be 180 (approximately 30 minutes)

## 6. Authentication

#### ✅ CORRECT
```bash
aliyun configure list   # Check credential status
```
- Uses `aliyun configure list` to verify credentials
- Relies on Alibaba Cloud default credential chain

#### ❌ INCORRECT
```bash
aliyun configure set --mode AK --access-key-id LTAI... --access-key-secret abc...   # NEVER set credentials within the session
echo $ALIBABA_CLOUD_ACCESS_KEY_ID   # NEVER print credential values
```
- Credentials must be configured outside of the session
- Never read, echo, or print AK/SK values

# Common Anti-Patterns

## Hardcoding User-Specific Parameters

#### ❌ INCORRECT
```bash
# Assuming a specific workspace_id without checking
python scripts/quanmiao_submit_videoAnalysis_task.py --workspace_id llm-known-good --file_url ...
```
- Always fetch workspaces via `list_workspace.py` first; default to the first result or present a selection list if the user explicitly asks to choose

## Skipping Environment Check

#### ❌ INCORRECT
```bash
# Jumping directly to upload without checking environment
python scripts/quanmiao_upload_file_to_oss_and_get_file_url.py --localFilePath /path/to/video.mp4
```
- Always run `check_env.py` first to ensure dependencies and credentials are ready

## Re-calling API After Success

#### ❌ INCORRECT
```bash
# Step 5 returned SUCCESSED, but calling get_result again in Step 6
python scripts/quanmiao_get_videoAnalysis_task_result.py --workspace_id llm-xxx --task_id abc123
```
- Use the result from Step 5 directly in Step 6; do NOT call the API again
