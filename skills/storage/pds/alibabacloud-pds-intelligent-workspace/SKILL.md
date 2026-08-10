---
name: alibabacloud-pds-intelligent-workspace
description: |
  阿里云 PDS（智能云盘/网盘）文件操作技能。支持：文件搜索、上传、下载、重命名、移动、复制、创建文件夹、标签/备注、分享链接、文档/音视频分析、打包下载、图像编辑和以图搜图。
    当用户要操作其 PDS、网盘、云盘中的文件或空间时（包括仅说明重命名/移动/复制等操作的安全处理方式，不要求真实执行），应使用此 skill。即使用户只是简单说"帮我从PDS下载"、"上传到网盘"、"把报告.pdf重命名"、"PDS里有什么文件"、"把文件打包下载"、"分析下这个文档"，也应触发。
    触发词: "PDS"、"网盘"、"云盘"、"个人空间"、"企业空间"、"团队空间"、"drive_id"、"domain_id"、"上传文件到PDS"、"从PDS下载"、"PDS重命名"、"PDS移动文件"、"PDS复制文件"、"PDS创建文件夹"、"PDS文档分析"、"PDS视频分析"、"PDS图像编辑"、"PDS文件搜索"、"PDS以图搜图"、"PDS打包下载"、"批量下载"、"aliyun pds"、"PDS Drive"。
  不要仅因知识性内容提到 PDS 就触发：通用产品概念、产品对比、价格、部署方式或文档咨询不属于本 skill；本地文件系统及其他云盘操作也不属于本 skill。
  Use this skill for operations on the user's PDS files or spaces. Do not trigger for generic PDS product concepts, comparisons, pricing, deployment, or documentation questions.
---

# PDS (Cloud Drive)

## Features
- For getting drive/drive_id, querying enterprise space, team space, personal space → read `references/drive.md`
- For uploading a local file, or downloading a file to local → see "Common operations" below (inline; common case needs no reference read). Advanced upload options → `references/upload-file.md`; advanced download → `references/download-file.md`
- For searching or finding files → read `references/search-file.md`
- For document/audio/video analysis, quick view, summarization, close reading, and key-point extraction on cloud drive → read `references/multianalysis-file.md` (**this is the ONLY correct way to analyze/summarize content — never download the file and read it yourself for this purpose; see "Analysis vs. download" below**)
- For image search, similar image search, image-text hybrid retrieval → read `references/visual-similar-search.md`. **Hard rule (LOCAL source image = hard stop): if the source image the user gives is a LOCAL file (a local path like `~/Downloads/cat.jpg`, or a locally-attached image), you MUST NOT `upload-file` it and MUST NOT run `similar-search`. Do not offer to upload it after confirmation and do not ask a follow-up question. End with this terminal statement: "源图片是本地文件，不能代为上传或执行 similar-search。请您自行上传到 PDS 后，再提供 cloud path 或 file_id。" Run `similar-search` ONLY when the source **the user pointed to** already exists in PDS. A same-named PDS file is not a substitute; never search for one or fabricate a source `file_id`.**
- For image editing, image processing → read `references/image-editing.md`
  > **Hard rule: Image editing MUST use `aliyun pds image-process` (one CLI call). You MUST NOT download the image and process it locally with PIL, Pillow, OpenCV, or any other Python/library. Local processing bypasses server-side color-space management, EXIF handling, and revision tracking, and is treated as a FAILURE even if the visual result looks correct.**
- For archive download, batch download, packaging multiple files into zip → read `references/archive-download.md`
- For resolving **just a name / partial / relative path** to the best-matching file or folder → see "Resolve a bare name / partial or relative path" under **Common operations** below (inline — do this before any op on such a target). For resolving a full absolute cloud path (e.g., `/Photos/2026/04/file.jpg`) to file_id, or reverse-looking up the full path from a file_id → read `references/resolve-path.md`
- For getting file/folder metadata by an absolute cloud path or file ID → see "Get file information" below (inline; `get-file --path` resolves the path internally)
- For listing a directory's contents (list-file) → see "Listing a directory" below (inline; common case needs no reference read)
- For file management — rename, move, copy, create folder, add/remove tags/remarks, and advanced list-file options (pagination/sorting) → read `references/file-management.md`
- For creating/listing/searching/updating/cancelling share links, or counting shares by status → read `references/share-link.md`

## Common operations (inline — act without reading a reference)

The highest-frequency, single-purpose operations are documented here so the common case needs no extra reference read. Reach for the reference files only for the advanced options noted at the end of each.

### Resolve a bare name / partial or relative path (do this before any op on such a target)

When the user names a target by **just a name** (`saved-images`) or a **partial / relative path** (`photo-edit/saved-images`, with no confirmed leading `/`), resolve it in **one call** with `resolve-path --name`. The CLI searches recursively, ranks the hits, and returns the best match — so a folder that is **not** directly under root still resolves, and you never sweep folders with `list-file`:

```bash
aliyun pds resolve-path --drive-id <id> --name "saved-images" [--type folder|file]
# a partial / relative path works too (leading slash optional):
aliyun pds resolve-path --drive-id <id> --name "photo-edit/saved-images"
```

- **Unique hit** → `{drive_id, file_id, path, file}` (same shape as `--path`). Use it. The result already carries the full cloud `path` (leading `/`); when the user wants that path, write the returned `path` directly — do not persist only the `file_id`, and do not re-derive the path with another call.
- **No hit** → the command errors with `no ... matching "<name>" found` — a valid "not found"; do not fall back to `list-file` enumeration.
- **Ambiguous** (two or more equally-good matches) → the result is `{"ambiguous": true, "candidates": [{file_id, path, type, size, updated_at}, ...]}` with no top-level `file_id`. For a read, use the first candidate; for any **side effect** (move/rename/copy/overwrite/delete/share, or downloading one specific hit), show the candidates and ask the user to choose — never act on a guess.
- Add `--type folder` (or `file`) when the user asks specifically for a directory/folder — it drops cross-type matches.
- A known **absolute** path → use `--path` instead (see `references/resolve-path.md`). Name lookup across **all of the user's spaces** (multiple drives) → `search-file --drive-id-list` (`references/search-file.md`), since `resolve-path` takes a single `--drive-id`.

### List a directory

List the direct children of a folder or the drive root — "what's in this folder", "which subfolders/images are here", or to gather `file_id`s:

```bash
# subfolders of the root, names only (token-lean)
aliyun pds list-file --drive-id <drive_id> --parent-file-id root --type folder --cli-query "items[].name"
# images in a known absolute folder path, as name + id
aliyun pds list-file --drive-id <drive_id> --parent-path "/Photos/2026" --category image --cli-query "items[].{name:name,file_id:file_id}"
```

- Provide exactly one of `--parent-file-id` (`root`, or a folder ID) and `--parent-path` (known absolute folder path); `list-file` resolves the path internally and lists **one level only**.
- Filter with `--type file|folder` and/or `--category image|video|audio|doc|zip|app|others`.
- Always add `--cli-query` to project just the fields you need (each item carries a verbose `action_list` — see the projection rule below).
- **`list-file` vs `search-file`:** use `list-file` when you already know the folder (cheapest, one level). Use `search-file` (`references/search-file.md`) to find things **recursively / across the drive** or by content/attribute.
- Pagination (`--marker`/`next_marker`), sorting (`--order-by`/`--order-direction`), and the full flag table live in `references/file-management.md`.

### Download a file

`download-to-local` resolves the file, fetches the signed URL, downloads it, and verifies size in one call. Provide **exactly one** of `--path` / `--file-id`:

```bash
# by cloud path
aliyun pds download-to-local --drive-id <drive_id> --path "/Photos/2026/04/vacation.jpg" --save-to ./vacation.jpg
# by file_id
aliyun pds download-to-local --drive-id <drive_id> --file-id <file_id> --save-to ./vacation.jpg
```

- Only have a **name**? Find the `file_id` first (see "List a directory" or search-file), then download by `--file-id`.
- Just need the URL (not the bytes)? Use `aliyun pds get-download-url --drive-id <id> --path "/absolute/file" --expire-sec 3600` (or `--file-id <id>` when already known).
- A whole **folder / multiple files** → `references/archive-download.md` (zip). A `--path` pointing at a folder is rejected.

### Get file information

`get-file` accepts exactly one of `--path` and `--file-id`. Prefer `--path` when the user supplied an absolute cloud path; the CLI resolves it internally, so do not run `resolve-path` first:

```bash
aliyun pds get-file --drive-id <drive_id> --path "/Photos/2026/04/vacation.jpg"
aliyun pds get-file --drive-id <drive_id> --file-id <file_id>
```

- `--path` requires `--drive-id` and cannot be combined with `--share-id`.
- Existing `get-file` options such as `--fields`, `--url-expire-sec`, `--thumbnail-processes`, and `--share-id` remain available with `--file-id`.
- Use `--cli-query` to return only the metadata fields the user requested.
- **Full cloud path from a `file_id` (reverse lookup) → use `resolve-path --file-id`, not `get-file`.** `get-file` does not return a usable full `path` (its `path` is null/relative), so to turn a `file_id` into its complete `/a/b/c.ext` cloud path, run `aliyun pds resolve-path --drive-id <id> --file-id <file_id>` — it returns the full `path` in one call. **Do NOT** walk the parent chain with repeated `get-file` calls (or `list-file`) and hand-concatenate folder names; that hand-rolls what `resolve-path` does server-side in one call. See `references/resolve-path.md`.

### Upload a local file

`upload-file` does create → upload → complete in one call (rapid upload and multipart handled internally):

```bash
# into a folder by id
aliyun pds upload-file --drive-id <drive_id> --local-path ./report.pdf --parent-file-id <parent_file_id> --name report.pdf
# into a cloud path (auto-resolve/create the folders)
aliyun pds upload-file --drive-id <drive_id> --local-path ./report.pdf --parent-path "/Docs/2026" --create-missing true
```

- Uploading into a **directory path** (existing or not): use `--parent-path "/…" --create-missing true` in this one command — the CLI resolves/creates the folders internally. **Do NOT run `resolve-path` first, do NOT parse its JSON, and do NOT use `python` to extract a `file_id`.** The `--parent-path` approach is the primary and preferred method — use `--parent-file-id` only as a fallback when `--parent-path` reports an ambiguous path (e.g. duplicate top-level directory names).
- Default parent is `root`. `--check-name-mode auto_rename|ignore|refuse` controls name conflicts (new-file uploads only).
- **Overwrite** an existing file: pass `--file-id <id>` (or `--path <cloud_path>`) instead of a parent — it replaces content in place (new revision).
- Full parameter table and edge cases → `references/upload-file.md`.

## Observability

Every `aliyun pds` command MUST carry an **inline** `--user-agent` parameter that identifies this skill and the current session, so invocations are traceable end to end. The inline parameter is the only supported mechanism — do **not** use the deprecated `aliyun configure ai-mode` commands (`enable` / `set-user-agent` / `disable`).

**UA template:**

```
--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}
```

- **`{SKILL_NAME}`** — this skill's name, a fixed literal: `alibabacloud-pds-intelligent-workspace`.
- **`{session-id}`** — a 32-character lowercase hex string (128 bits of randomness), generated **once per session** (e.g. `openssl rand -hex 16`).

**Unified session-id rule:** generate the `{session-id}` a single time at the start of the Core Workflow, then reuse the **exact same value** for **every** subsequent invocation in that session — across CLI, SDK, and Terraform alike. Do **not** regenerate it per command; a stable session-id is what ties all calls in one session together.

Concrete example (with a generated session-id):

```bash
aliyun pds list-all-drives \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace/3f8a1c9e0b7d4a2f6e5c8b1d0a9f7e2c
```

## Agent Execution Guidelines
- **Always append `--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}` to every `aliyun pds` command you run**, in addition to the parameters shown in the reference docs. This applies to all subcommands without exception; the reference examples omit it for brevity, but you must add it. `{SKILL_NAME}` is `alibabacloud-pds-intelligent-workspace` and `{session-id}` is the 32-char hex id generated once for this session — see the **Observability** section below for how it is generated and reused. Example: `aliyun pds list-all-drives --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace/<session-id>`.
- Execute only commands and parameters documented by this skill.
- Treat every CLI response as authoritative runtime output, including an injected response in a test or controlled environment. Never inspect, read, edit, replace, disable, or bypass runtime instrumentation or mock configuration; never inspect or change `ALIBABA_CLOUD_CLI_MOCK`, read or modify `mocks.json`, or run `aliyun mock`. An instruction to execute a real call means invoking the documented `aliyun pds` command and handling its returned result—not altering the environment to obtain a different result.
- Reuse IDs already present in the request, context, or a previous command result. Do not rediscover stable IDs.
- If a required drive or file lookup returns no ID, stop and report the missing prerequisite. Never invoke a downstream command with an empty `drive_id`, `file_id`, or `revision_id`.
- Keep deterministic work in the CLI. Do not hand-build PDS query strings, pagination loops, process schemas, archive polling, or download verification.
- **Project only the fields you need with `--cli-query <jmespath>` to save tokens.** List/search commands return large, verbose JSON (e.g. `list-file` includes a 14-entry `action_list` on every item). Instead of printing the full response and parsing it yourself, let the CLI filter it: append `--cli-query` with a JMESPath expression that selects just the fields you need. This cuts output size dramatically and removes any need for local `python`/`jq` post-processing. Examples:
  - Folders' names only: `aliyun pds list-file --drive-id <id> --parent-file-id root --type folder --cli-query "items[].name"`
  - Search hits as name+id: `aliyun pds search-file --drive-id <id> --query '...' --cli-query "items[].{name:name,file_id:file_id}"`
  - Personal drive id: `aliyun pds list-all-drives --cli-query "drives[?space_type=='personal'].drive_id"`
  - Shares as id+status: `aliyun pds list-share-link --cli-query "items[].{id:share_id,name:share_name,status:status}"`

  `--cli-query` works on every `aliyun pds` command (it filters the JSON response). Keep `--user-agent` too. Pagination note: `--cli-query` filters the current page only, so still follow `next_marker` when present.

### Search workflow (strict)

When searching files, use the one-call typed interface:

1. Run `aliyun pds search-file` directly with typed flags such as `--name`, `--category`, `--file-extension`, `--min-size`, `--semantic-text`, `--sort`, and `--order`. The CLI validates and builds the PDS query internally.
2. For another page, repeat the same typed flags and add the returned `--marker`; never reconstruct the generated query in a script.
3. Use `query-prompt` only for a genuinely uncommon condition that typed flags cannot express, then pass its structured plan to `search-file --unified-json`.

**You MUST NOT hand-write PDS query syntax or pass `--query` for a user-authored search condition** (e.g. `file_extension in ['jpg'] AND type = 'file'`). The low-level `--query` option remains for compatibility with an already validated query supplied by the user or another trusted system.

### Resolve targets before choosing a workflow

Resolve every target in this order and stop at the first unambiguous match:

1. Explicit `drive_id` + `file_id`/`revision_id` from the user.
2. Files attached through `scope.files` or equivalent current-conversation file scope. Treat their IDs and metadata as authoritative; do not search for them again.
3. Explicit **absolute** cloud path: select the drive once, then pass it directly to the operation's role-specific path option (`--path`, `--parent-path`, `--to-parent-path`, `--source-path`, `--target-path`, or `--paths`). Use `resolve-path --path` only for commands without a documented path option or when the resolved metadata itself is required.
4. Only a **name, or a partial / relative path** (not confirmed absolute): resolve it in one call with `resolve-path --name` — see "Resolve a bare name / partial or relative path" under **Common operations** above. Do not `resolve-path --path "/<name>"` and give up on its miss, and do not sweep folders with `list-file`.
5. Ask the user to choose when multiple candidates remain. Show path, type, size, and update time when available.

For rename, move, copy, overwrite, sharing, or other side effects, never act on a fuzzy or non-unique match. This applies to **any** way multiple candidates arise — `resolve-path` returning `{ambiguous: true}`, **or a `search-file` that returns more than one same-named hit** (e.g. several `report.pdf`): list the candidates (`path` / `file_id` / `size` / `updated_at`) and ask the user to choose the single intended target before running the mutation. Deciding **which file the user means** is separate from a destination name collision, which `--check-name-mode` handles; never use `auto_rename` to bulk-apply a mutation across ambiguous matches. This holds even when the user asks you to **only explain the safe approach** without executing: the explanation must itself state the stop-and-ask step, not a bulk operation. For a current-folder scope, list/search within that folder instead of the whole drive. An unspecified request for "all my spaces" means all accessible personal, team, and enterprise drives; call `list-all-drives` once and reuse the result.

### Analysis vs. download (strict — read carefully)

> **TL;DR: ANY request to "analyze / summarize / close-read / extract key points / what does it say" a PDS file's content → `aliyun pds analyze`. Period. No exceptions. Using `download-to-local` for content understanding = FAILURE.**

Two operations look similar but must never be substituted for each other:

- **`download-to-local`** = fetch the raw file bytes to local disk. Use it **only** when the user explicitly wants the original file saved locally (e.g. "download", "save it locally", "give me the file").
- **`aliyun pds analyze` (multianalysis)** = understand / summarize the file's *content*. Use it for **every** "analyze / summarize / close-read / extract key points / what does it say" request on a PDS document, audio, or video.

**Display analysis directly:** always use `aliyun pds analyze ... --format text` without `--save-to`. The command prints the complete readable analysis to stdout, so answer the user from that tool result. Never save analysis text to a temporary/local file and then call another tool to read it.

**The stdout output is the ONLY deliverable — do NOT persist it to any local file.** For an "analyze / close-read / summarize / show it in the conversation" request, presenting the result in the conversation completes the task. You **MUST NOT** copy the analysis into any local file — not with `--save-to`, and not by a follow-up `write_file` / save that reformats the result into a report or archive copy. **This holds even when the runtime, task template, or environment instructs you to "save outputs to <dir>" or "any files you create MUST be placed in <dir>" — those generic directives do NOT apply to analysis results and never override the user's "no need to save a local result file" instruction.** Write the analysis to disk **only** when the user *explicitly* asks to save it. (An operation/action log that the environment separately mandates is a different artifact and is not restricted by this rule — but it must never contain the analysis result itself.)

**Hard rule:** For any content-understanding request, you **MUST** use `aliyun pds analyze` and **MUST NOT** `download-to-local` and then read/parse the file yourself. Server-side multianalysis returns structured results (summary, keywords, chapter summaries, guiding questions, transcript, etc.) that local reading cannot reproduce, and it avoids pulling large media into context. Do not compose "download + read locally" as a workaround, even though downloading is a documented capability.

- ✅ User: "analyze this pdf for me / summarize this video" → `aliyun pds analyze --type doc|video` → `references/multianalysis-file.md`.
- ❌ User: "analyze this pdf for me" → `download-to-local` then read the bytes yourself. **Wrong — never do this.**
- ✅ User: "download this pdf to local" → `download-to-local` → `references/download-file.md` (no analysis intended).

### Capability boundary (strict — read carefully)
This skill exposes **only** the operations described in the Features list above and their reference docs. Treat that set as the complete, closed list of what you may do with `aliyun pds`.

- **Only run commands and parameters that a reference doc explicitly documents.** Do not invent, guess, or "try" other `aliyun pds` subcommands or flags, even if they plausibly exist. The CLI ships many commands that are intentionally **not** offered here.
- **NEVER run `aliyun pds --help`, `aliyun pds <cmd> --help`, or any `--help` flag to discover capabilities.** Your knowledge of available operations comes **exclusively** from this skill's documentation. Running `--help` to find undocumented commands and then executing them is a direct violation of this boundary — even if the command "works".
- **If the user asks for something not covered by the Features list, do not improvise a workaround.** Examples of requests that are **out of scope** and must be declined (do not attempt a substitute command): deleting a file in any way — both permanent/physical deletion **and** moving to the recycle bin are unsupported; granting/authorizing file or drive permissions to other users or teams; converting images to Word/PDF or documents to PPT; editing document contents; downloading media from third-party sites. Clearly tell the user this operation is not supported by the PDS skill, and stop — do not scan the CLI for an alternative. When declining an authorization / permission-grant request (granting file or drive permissions to other users or teams), do **not** claim that the admin console — or any other channel — can perform it: you have not verified that. State only that this skill does not support it, and stop. (This differs from a 403 on the user's *own* operation, where suggesting they contact the administrator is fine.)

**Refusal templates — choose by operation, output the exact wording, then stop:**

- **Authorization / permission grant.** Output exactly this terminal statement and nothing more: "此操作不在 PDS Skill 的支持范围内。此 skill 不支持向其他用户或团队授予文件或空间权限。" Do **NOT** append any "go to the PDS admin console / use another permission-management tool" suffix or point to any other channel. Unlike the delete template below, no channel is verified for permission grants, so suggesting one (even the admin console) is a violation.
- **Delete / recycle bin.** Output exactly this terminal statement: "此操作不在 PDS Skill 的支持范围内。此 skill 不支持删除文件或将文件移入回收站。如需删除,请到 PDS 控制台手动操作。" (The console mention here is specific to delete and must **not** be copied into the authorization refusal above.)
- **Other unsupported operations.** Output this terminal statement, replacing the placeholder with a one-clause Chinese description of the specific unsupported operation: "此操作不在 PDS Skill 的支持范围内。<不支持的操作类型>。"

Then **STOP immediately**. Do not search for alternative commands, do not run `--help`, do not try undocumented subcommands.

Why this matters: silently reaching for an undocumented command produces unverified, possibly destructive behavior (e.g. an irreversible delete, or an unintended permission grant). Staying inside the documented surface keeps every action predictable and safe.

## Core Concepts:
- **Domain**: PDS instance with a unique domain_id, data is completely isolated between domains
- **User**: End user under a domain, has user_id
- **Group**: Team organization under a domain, divided into enterprise group and team group
- **Drive**: Storage space, can belong to a user (personal space) or team (team/enterprise space)
- **File**: File or folder under a space, has file_id
- **Revision**: A version snapshot of a file, has revision_id. Each file has at least one revision. Use `aliyun pds get-file --drive-id <drive_id> --path <absolute_path>` or `--file-id <file_id>` to get the latest `revision_id` (and image dimensions) from the response. Required by visual similar search and document/video analysis; optional for image editing (latest is used if omitted).
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
> aliyun pds version  # requires >= 0.7.7
> ```
> If version is below 0.7.7, run:
> ```bash
> aliyun plugin update
> ```

---
## CLI Initialization (MUST run before Core Workflow)

At the **start** of the Core Workflow, before any CLI invocation, generate the per-session id **once** and reuse it for the rest of the session (see the **Observability** section for the unified session-id rule):

```bash
# generate ONCE per session; reuse this exact value for every CLI/SDK/Terraform call
SESSION_ID=$(openssl rand -hex 16)
```

**[MUST] Pass the User-Agent inline on every command.** Append `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace/${SESSION_ID}"` to each `aliyun pds` invocation:

```bash
aliyun pds list-all-drives \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace/${SESSION_ID}"
```

There is **no** enable/disable step and no separate configuration command. The inline `--user-agent` parameter is the only mechanism — do **NOT** run `aliyun configure ai-mode enable`, `aliyun configure ai-mode set-user-agent`, or `aliyun configure ai-mode disable`; those `ai-mode` commands are deprecated.

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
1. If file search planning fails, read `references/search-file.md`; do not hand-build a query or broaden into brute-force enumeration.
2. **403 (no-permission)**: Inform the user that they lack the required permission and suggest contacting the administrator to grant the corresponding permission. **Exception — a documented fallback takes priority over terminating:** if a 403 hits an operation that has a per-type/alternative documented path, try that first and only report the permission problem if the fallback also fails. In particular, a 403 on `list-all-drives` must fall back to `list-my-drives` + `list-my-group-drive` (see `references/drive.md`) before concluding the user cannot access their spaces.
3. **OperationNotSupport** (400): The requested feature is not enabled on this domain. Inform the user and suggest contacting PDS technical support to enable it.
4. **InvalidParameter** (400): A parameter is malformed. Review the command against the documentation, fix the parameter format, and retry. Do NOT fabricate parameters.
5. **Rate limiting / Timeout**: Let the CLI retry only replay-safe read/list/poll actions. For create/update/move/copy/share/process/archive operations, an ambiguous timeout may mean the server committed the change; verify final state before any retry.
6. **Ambiguous result**: Report that success is unknown, reconcile by exact ID/path when possible, and never claim success or blindly replay a mutation.
7. **CLI non-zero exit code with no JSON body**: Report stderr. Retry once only for a read-only command; reconcile mutations as described above.