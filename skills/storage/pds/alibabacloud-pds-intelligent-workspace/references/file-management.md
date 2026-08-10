# PDS File Management (list / rename / move / copy / create folder / tags)

**Scenario**: List and manage existing files and folders in a PDS drive — list a directory's contents, rename, move, copy, create folders, favorite, or add tags/remarks.

All operations need a `drive_id`. For a known absolute cloud path, pass the command's path option directly; the CLI resolves it internally. Resolve/search first only when the input is a bare name or an ambiguous relative path.

> **Scope note**: This skill does **not** support deleting files in any form — **neither** moving a file to the recycle bin **nor** permanent/physical deletion. It also does **not** support granting file/drive permissions to other users or teams. If the user asks for any of these, tell them it is not supported and stop — do not substitute another command (see the Capability boundary section in `SKILL.md`).

---

## Rename a file or folder

> **Uniqueness hard stop before renaming.** If the target was located by a search or name lookup and **more than one same-named candidate** came back (e.g. several `report.pdf`), you MUST NOT run `update-file` on any of them. First list the candidates' `path` / `file_id` / `size` / `updated_at` and **ask the user to pick the one intended target**; only rename after the user confirms a single `file_id`. Never bulk-rename every match, and never guess. This is disambiguation of **which file the user means** — a different problem from a name collision, and `--check-name-mode` does **not** solve it (see the note below). The rule holds even when the request is "just explain the safe approach" / explanation-only: the safe approach you describe must itself state this stop-and-ask step, not a bulk rename.

Use `aliyun pds update-file` with `--name`. This renames in place; it does **not** re-upload.

```bash
aliyun pds update-file \
  --drive-id <drive_id> \
  --path "/absolute/file" \
  --name "<new_name>" \
  [--check-name-mode auto_rename|ignore|refuse]
```

`--check-name-mode` controls what happens if a sibling already has the new name (`ignore` allow duplicate / `auto_rename` append timestamp / `refuse` reject; default `ignore`). This handles a **name collision** on the destination name only — it is **not** a substitute for the uniqueness hard stop above. Do not reach for `auto_rename` to push through a rename of multiple ambiguous matches; that turns a "which file?" question into an unwanted bulk rename.

`update-file` can also set other metadata on the same call: `--description "<remark>"`, `--starred true` (favorite), `--hidden true`.

---

## Move a file or folder

Use `aliyun pds move-file`. For known absolute paths, pass source `--path` and existing destination `--to-parent-path` directly.

```bash
aliyun pds move-file \
  --drive-id <drive_id> \
  --path "/absolute/source" \
  --to-parent-path "/absolute/destination" \
  [--check-name-mode auto_rename|ignore|refuse]
```

Moving many files = call `move-file` once per `file_id` with the same `--to-parent-file-id`.

> **403 `CheckRouterAccessFailed` / "User not authorized" on move-file**: the MoveFile OpenAPI is not authorized for the current credential/domain — it is not a command or parameter error, and retrying won't help. Stop, and tell the user the move could not be performed because their account lacks MoveFile authorization (suggest contacting the domain administrator). Do not fabricate a success or a workaround.

---

## Copy a file or folder

Use `aliyun pds copy-file`. `--to-parent-path` (or `--to-parent-file-id`) is the existing destination folder; add `--to-drive-id` only when copying across drives.

```bash
aliyun pds copy-file \
  --drive-id <drive_id> \
  --path "/absolute/source" \
  --to-parent-path "/absolute/destination" \
  [--to-drive-id <dest_drive_id>] \
  [--auto-rename true]
```

---

## Create a folder

For a **single** folder, use `aliyun pds create-file` with `--type folder`:

```bash
aliyun pds create-file \
  --drive-id <drive_id> \
  --name "<folder_name>" \
  --type folder \
  --parent-path "/absolute/parent" \
  [--check-name-mode refuse]
```

For a **multi-level** path (e.g. `/new-folder-test/2026/report`), prefer `resolve-path --create-missing` — it creates every missing intermediate folder in one call and returns the final `file_id`:

```bash
aliyun pds resolve-path \
  --drive-id <drive_id> \
  --path "/new-folder-test/2026/report" \
  --create-missing true
```

---

## List files in a directory (full reference)

> Basic listing (list a folder / subfolders / images, with `--cli-query` projection) is covered inline in `SKILL.md` — you usually don't need this section. Read on only for the **advanced** options: pagination, sorting, the full flag table, and the `list-file` vs `search-file` decision.

Use `aliyun pds list-file` to enumerate the direct children of a folder (or the drive root). This is the tool for requests like "the first 3 files in the root", "what's in this folder", "the images in this folder", or gathering `file_id`s to feed into archive-download / move / copy.

**`list-file` vs `search-file` — pick the right one:**
- `list-file` enumerates **one level only**. Provide exactly one of `--parent-path` and `--parent-file-id` (use ID `root` for the drive root). It does **not** recurse.
- `search-file` (see `references/search-file.md`) searches **recursively across the whole drive** (or a subtree), needs the query-prompt → build-search-query workflow, and is the right tool for content/attribute queries or "find X anywhere". Use it when the target folder is unknown or you need recursion.

```bash
aliyun pds list-file \
  --drive-id <drive_id> \
  --parent-path "/absolute/folder" \
  [--type file|folder] \
  [--category image|video|audio|doc|zip|app|others] \
  [--limit <1-100>] \
  [--order-by created_at|updated_at|name|size] \
  [--order-direction ASC|DESC] \
  [--marker <next_marker>]
```

| Flag | Description |
|------|-------------|
| `--parent-path` / `--parent-file-id` | Exactly one. Absolute folder path, `root`, or a folder ID. `list-file` always lists exactly this one directory level. |
| `--type` | Filter results: `file` (files only) or `folder` (folders only). Omit to return both. |
| `--category` | Filter files by category: `image`, `video`, `audio`, `doc`, `zip`, `app`, `others`. Omit to return all categories. Handy for "list the images/videos in this folder" **without** the search workflow — but still only within this one folder level (not recursive). |
| `--limit` | Page size, 1–100. |
| `--order-by` / `--order-direction` | Sort field (`created_at`/`updated_at`/`name`/`size`) and direction. |
| `--marker` | Pagination cursor. If the response has a non-empty `next_marker`, pass it as `--marker` to get the next page; repeat until it is empty. |

The response contains an `items` array of file objects (each with `file_id`, `name`, `type`, `size`, plus a verbose `action_list` of permissions, …) and an optional `next_marker`.

> **Save tokens:** each item is large (the `action_list` alone is ~14 entries). Project only what you need with `--cli-query`, e.g. `--cli-query "items[].name"` (names) or `--cli-query "items[].{name:name,file_id:file_id,type:type}"`. See the `--cli-query` guidance in `SKILL.md`.

**Example — "list the images in this folder":**

```bash
aliyun pds list-file --drive-id <drive_id> --parent-path "/Photos" --category image --limit 100
```

> If the user wants images anywhere in the drive (recursively), use `search-file` with a `category eq image` scalar condition instead — `list-file --category` only covers the one named folder.

**Example — "the first 3 files (not folders) in the root":** first list the root filtered to files, read the `file_id`s straight from the returned `items` JSON, then pass them to archive-download. (No scripting needed — read the ids from the JSON output and put them on the next command.)

```bash
# Step 1 — list the first 3 files and read their file_id values from items[]
aliyun pds list-file --drive-id <drive_id> --parent-file-id root --type file --limit 3

# Step 2 — pass the file_ids you just read to archive-download
aliyun pds archive-download --drive-id <drive_id> \
  --file-ids <id1> <id2> <id3> \
  --name my_files.zip --save-to ./my_files.zip
```

> Tip: to print just the ids, add `--cli-query 'items[].file_id'` to the `list-file` call — it returns a JSON array of the `file_id`s.

---

## Deleting files — not supported

Deleting files is **out of scope** for this skill: neither moving to the recycle bin (`trash-file`) nor permanent deletion (`delete-file` and similar) is offered. If the user asks to delete a file, tell them this skill does not support deletion and suggest handling it in the PDS console, and stop — do not run `trash-file`, `delete-file`, or any other command as a substitute.

---

## Add tags / remarks to a file

Use `aliyun pds file-put-user-tags`. `--user-tags` is a JSON array of `{key,value}` objects (1–1000 tags, no duplicate keys, no `#` in key/value). The key must not be empty; value is optional.

```bash
aliyun pds file-put-user-tags \
  --drive-id <drive_id> \
  --path "/absolute/file" \
  --user-tags '[{"key":"remark","value":"student8"}]'
```

To remove tags, use `aliyun pds file-delete-user-tags` with the same `--drive-id` and exactly one of `--path` / `--file-id`, plus the tag keys to remove.

---

## Common workflow

1. For a known absolute path, pass it directly to the management command. Do not call `resolve-path` first.
2. If a move/copy destination folder does not exist, create it once with `resolve-path --create-missing`; then pass its ID. Existing destination folders can use `--to-parent-path` directly.
3. Verify when useful: `aliyun pds get-file --drive-id <id> --file-id <id>` (confirm new name / parent), or `resolve-path` the new path.

## Error handling
- **ForbiddenNoPermission** (403): the user lacks permission on the file/folder — inform them and suggest contacting the administrator. Do not attempt to grant permission yourself (not supported).
- **NotFound.File** (404): the `file_id` is wrong or the file was already removed — re-resolve the path/name.
- **InvalidParameter** (400): fix the flagged parameter against this doc and retry; do not guess alternative flags.
