---
name: alibabacloud-pds-multimodal-search
description: |
  Implements exact filename search, fuzzy filename search, semantic file search, and image-based image search
  Triggers: "PDS drive file search", "PDS image search by image"
---

# PDS Multimodal Search

**Please read this entire skill document carefully**

### Features
- For getting drive/drive_id, querying enterprise space, team space, personal space -> read `references/drive.md`
- For uploading local files to enterprise space, team space, personal space → read `references/upload-file.md`
- For downloading files from enterprise space, team space, personal space to local → read `references/download-file.md`
- For searching or finding files → read `references/search-file.md`
- For document/audio/video analysis, quick view, summarization on cloud drive → read `references/multianalysis-file.md`
- For image search, similar image search, image-text hybrid retrieval → read `references/visual-similar-search.md`

## Agent Execution Guidelines
- **Must execute steps in order**: Do not skip any step, do not proceed to the next step before the previous one is completed.
- **Must follow documentation**: The aliyun pds cli commands and parameters must follow this document's guidance, do not fabricate commands.
- **Recommended parameter**: All `aliyun pds` commands should include `--user-agent AlibabaCloud-Agent-Skills` parameter to help server identify request source, track usage, and troubleshoot issues.
- **Must determine the target space before file operations**: Before search, upload, download, or analysis, first decide whether the user explicitly means enterprise space, team space, personal space, or all spaces.
- **Space scope must not be broadened silently**: If the user explicitly says "enterprise space", only use the enterprise space drive_id. If the user explicitly says "team space", only use the matching team space drive_id. If the user explicitly says "personal space", only use the personal space drive_id. Only search across multiple spaces when the user did not restrict the scope.
- **Enterprise space and team space are not interchangeable**: Even though both are returned by `list-my-group-drive`, `root_group_drive` is the enterprise space and `items` are team spaces. Never substitute one for the other.
- **If the requested space is missing, stop and explain**: For example, if the user asks for enterprise space but `root_group_drive` is empty, do not fall back to a team space search.

## Core Concepts:
- **Domain**: PDS instance with a unique domain_id, data is completely isolated between domains
- **User**: End user under a domain, has user_id
- **Group**: Team organization under a domain, divided into enterprise group and team group
- **Drive**: Storage space, can belong to a user (personal space) or group (enterprise space or team space)
- **File**: File or folder under a space, has file_id
- **Mountapp**: PDS mount app plugin, used to mount PDS space to local, allowing users to access and manage files in PDS space conveniently

## Space Selection Rules

Apply the following rules before choosing a `drive_id`:

| User wording | Allowed drive source | Forbidden fallback |
|------------|------|------|
| "企业空间" / "company space" / "enterprise space" | `root_group_drive` only | Any drive from `items` |
| "团队空间" / "某个团队空间" / "team space" | `items` only | `root_group_drive` |
| "个人空间" / "我的空间" / "personal space" | `list-my-drives.items` only | group drives |
| "网盘里" / "我的网盘" / no space specified | all relevant spaces | none |

Before continuing, perform a brief self-check:
1. Did the user explicitly name the target space type?
2. Does the selected `drive_id` come from the correct response field for that space type?
3. If multiple team spaces exist and the user only said "team space", do I need to disambiguate which team space?

If any answer is uncertain, do not guess.

---

## Installation Requirements

> **Prerequisites: Requires Aliyun CLI >= 3.3.1**
>
> Verify CLI version:
> ```bash
> aliyun version  # requires >= 3.3.1
> ```
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
aliyun version  # confirm >= 3.3.1

# Enable auto plugin installation
aliyun configure set --auto-plugin-install true

# Install Python dependencies (for multipart upload script)
pip3 install requests
```

## PDS-Specific Configuration

Before executing any PDS operations, you must first configure domain_id, user_id, and authentication type -> read `references/config.md`

> **Recommended parameter**: All `aliyun pds` commands should include `--user-agent AlibabaCloud-Agent-Skills` parameter
>
> Examples:
> ```bash
> aliyun pds get-user --user-agent AlibabaCloud-Agent-Skills
> aliyun pds list-my-drives --user-agent AlibabaCloud-Agent-Skills
> aliyun pds upload-file --drive-id <id> --local-path <path> --user-agent AlibabaCloud-Agent-Skills
> ```

## References

| Reference Document | Path |
|------------|------|
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| RAM Permission Policies | [references/ram-policies.md](references/ram-policies.md) |


## Error Handling
1. If file search fails, please read `references/search-file.md` and strictly follow the documented process to re-execute file search.
