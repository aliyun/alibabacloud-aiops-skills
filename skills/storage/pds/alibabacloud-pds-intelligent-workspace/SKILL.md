---
name: alibabacloud-pds-intelligent-workspace
description: |
  Implements PDS file upload, download, search, document/audio/video analysis, image editing, visual search, mount app access, and file sharing features. 
  Triggers: "upload file to PDS drive", "download file from PDS drive", "PDS drive document analysis", "PDS drive video analysis", "PDS image editing", "PDS image processing", "mount PDS drive", "install mount app", "uninstall mount app", "PDS drive mount access", "stop mount app", "PDS Drive create share", "PDS Drive cancel share", "PDS Drive search share", "PDS Drive share-link"
---

# PDS (Cloud Drive)

**Please read this entire skill document carefully**

### Features
- For getting drive/drive_id, querying enterprise space, team space, personal space -> read `references/drive.md`
- For uploading local files to enterprise space, team space, personal space → read `references/upload-file.md`
- For downloading files from enterprise space, team space, personal space to local → read `references/download-file.md`
- For searching or finding files → read `references/search-file.md`
- For document/audio/video analysis, quick view, summarization on cloud drive → read `references/multianalysis-file.md`
- For image search, similar image search, image-text hybrid retrieval → read `references/visual-similar-search.md`
- For mount app, install mount app, uninstall mount app, stop mount app → read `references/mountapp.md`
- For image editing, image processing → read `references/image-editing.md`
- For PDS file sharing, share, share-link, share link, shared link, external sharing, create/cancel/update/search share links, or share permission control → read `references/share-link.md`

## Agent Execution Guidelines
- **Must execute steps in order**: Do not skip any step, do not proceed to the next step before the previous one is completed.
- **Must follow documentation**: The aliyun pds cli commands and parameters must follow this document's guidance, do not fabricate commands.
- **[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
  `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace`

## Core Concepts:
- **Domain**: PDS instance with a unique domain_id, data is completely isolated between domains
- **User**: End user under a domain, has user_id
- **Group**: Team organization under a domain, divided into enterprise group and team group
- **Drive**: Storage space, can belong to a user (personal space) or team (team/enterprise space)
- **File**: File or folder under a space, has file_id
- **Mountapp**: PDS mount app plugin, used to mount PDS space to local, allowing users to access and manage files in PDS space conveniently
- **Share / Share Link**:: PDS file sharing for files, folders, or an entire drive. In this skill, "share", "share-link", "share link", "shared link", and "external sharing" all refer to PDS file Sharing.
---

## Installation Requirements

> **Prerequisites: Requires Aliyun CLI >= 3.3.3**
>
> Verify CLI version:
> ```bash
> aliyun version  # requires >= 3.3.3
> ```
>
> If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.
>
> Verify PDS plugin version:
> ```bash
> aliyun pds version  # requires >= 0.1.4
> ```
>
> If version requirements are not met, refer to `references/cli-installation-guide.md` for installation or upgrade.
>
> After installation, **must** enable auto plugin installation:
> ```bash
> aliyun configure set --auto-plugin-install true
> ```
>
> Then [MUST] run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

---
## CLI Initialization (MUST run before Core Workflow)

At the **start** of the Core Workflow (before any CLI invocation):

**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace"
```

**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

---

## Authentication Configuration

> **Prerequisites: Alibaba Cloud credentials must be configured**
>
> **Security Rules:**
> - **Forbidden** to read, output, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is forbidden)
> - **Forbidden** to ask users to input AK/SK directly in conversation or command line
> - **Forbidden** to use `aliyun configure set` to set plaintext credentials
> - **Only allowed** to use `aliyun configure list` to check credential status
>
> Check credential configuration:
> ```bash
> aliyun configure list
> ```
>
> Confirm the output shows a valid profile (AK, STS, or OAuth identity).
>
> **If no valid configuration exists, stop first.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside this session** (run `aliyun configure` in terminal or set environment variables)
> 3. Run `aliyun configure list` to verify after configuration is complete

```bash
# Install Aliyun CLI (if not installed)
curl -fsSL --max-time 10 https://aliyuncli.alicdn.com/install.sh | bash
aliyun version  # confirm >= 3.3.3

# Enable auto plugin installation
aliyun configure set --auto-plugin-install true

# Install Python dependencies (for multipart upload script)
pip3 install requests
```

## PDS-Specific Configuration

Before executing any PDS operations, you must first configure domain_id, user_id, and authentication type -> read `references/config.md`

> **[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace`
> 
> Examples:
> ```bash
> aliyun pds get-user --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
> aliyun pds list-my-drives --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
> aliyun pds upload-file --drive-id <id> --local-path <path> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
> ```

## References

| Reference Document | Path |
|------------|------|
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| RAM Permission Policies | [references/ram-policies.md](references/ram-policies.md) |


## Error Handling
1. If file search fails, please read `references/search-file.md` and strictly follow the documented process to re-execute file search.
