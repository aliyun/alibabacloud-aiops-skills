---
name: alibabacloud-pds-intelligent-workspace
description: |
  阿里云 PDS（智能云盘/网盘）文件操作技能。支持：文件搜索、文件上传、文件下载、文档/音视频分析、打包下载、图像编辑（缩放、裁剪、旋转、分割、移除、水印等）、以图搜图、挂载网盘、文件分享链接管理。
  当用户提到 PDS、网盘、云盘、个人空间、企业空间、团队空间，或需要对 PDS 中的文件进行任何操作时（上传、下载、搜索、分析、打包、编辑图片、分享），都应使用此 skill。即使用户只是简单说"帮我从PDS下载"、"上传到网盘"、"PDS里有什么文件"、"把文件打包下载"、"分析下这个文档"，也应触发。
  触发词: "PDS"、"网盘"、"云盘"、"个人空间"、"企业空间"、"团队空间"、"drive_id"、"domain_id"、"上传文件到PDS"、"从PDS下载"、"PDS文档分析"、"PDS视频分析"、"PDS图像编辑"、"PDS文件搜索"、"PDS以图搜图"、"PDS打包下载"、"批量下载"、"aliyun pds"、"PDS分享链接"、"创建PDS分享"、"挂载PDS网盘"、"mount PDS drive"、"PDS Drive"。
  Use this skill whenever the user mentions PDS, 网盘, 云盘, PDS Drive, or asks to upload/download/share/analyze/search/archive files in PDS, even if they don't use the exact trigger phrases above.
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
- For archive download, batch download, packaging multiple files into zip → read `references/archive-download.md`
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
- **Share / Share Link**: PDS file sharing for files, folders, or an entire drive. In this skill, "share", "share-link", "share link", "shared link", and "external sharing" all refer to PDS file Sharing.
---

## Installation Requirements

> **Step 1: Verify Aliyun CLI version**
> ```bash
> aliyun version  # requires >= 3.3.16
> ```
> If not installed or version is below 3.3.16, refer to `references/cli-installation-guide.md` for installation or upgrade.
>
> **Step 2: Enable auto plugin installation** (after CLI version is satisfied)
> ```bash
> aliyun configure set --auto-plugin-install true
> ```
>
> **Step 3: Verify PDS plugin version**
> ```bash
> aliyun pds version  # requires >= 0.3.1
> ```
> If version is below 0.3.1, run:
> ```bash
> aliyun plugin update
> ```

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

**Quick Setup (only if prerequisites above are not met):**
```bash
# Install Aliyun CLI (if not installed)
curl -fsSL --max-time 10 https://aliyuncli.alicdn.com/install.sh | bash
aliyun version  # confirm >= 3.3.16

# Enable auto plugin installation
aliyun configure set --auto-plugin-install true

# Install Python dependencies (for multipart upload script)
pip3 install requests
```

## PDS-Specific Configuration

Before executing any PDS operations, you must first configure domain_id, user_id, and authentication type -> read `references/config.md`

## References

| Reference Document | Path |
|------------|------|
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| RAM Permission Policies | [references/ram-policies.md](references/ram-policies.md) |


## Error Handling
1. If file search fails, please read `references/search-file.md` and strictly follow the documented process to re-execute file search.
