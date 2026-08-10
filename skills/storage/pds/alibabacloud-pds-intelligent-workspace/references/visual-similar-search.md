# PDS Visual Similar Search Guide

**Scenario**: Find images in a drive that are visually similar to a source image (image search / similar-image search / image-text hybrid retrieval).

Searching is done in **one CLI call** — `aliyun pds similar-search`. The command renders the `x-pds-process` parameter (source `pds://` schema, semantic query, result type) and validates it locally, then calls the Process API. You do **not** build `x-pds-process` by hand or run any Python script.

---

## Two distinct resources

- **Source image** — referenced by `--source-drive-id` plus `--source-path` or `--source-file-id`.
- **Search scope** — `--drive-id` (whole drive) or `--drive-id` plus `--path` / `--file-id` (a folder).

They are independent (the source image need not live in the search scope).

---

## Command

```bash
aliyun pds similar-search \
  --source-drive-id <SRC_DRIVE_ID> \
  --source-path <SRC_PATH> \
  [--source-revision-id <SRC_REVISION_ID>] \
  --drive-id <SEARCH_DRIVE_ID> \
  [--path <SEARCH_FOLDER_PATH>] \
  [--query "<semantic text>"] \
  [--limit <N>] \
  [--dry-run true]
```

| Flag | Description |
|------|-------------|
| `--source-drive-id` + `--source-path` / `--source-file-id` | The query image. Provide exactly one path/ID. |
| `--source-revision-id` | Query image revision. **Optional — auto-fetched (latest) if omitted**, so you do not need a separate `get-file`. Required only with `--dry-run` (that mode does not call the API). |
| `--drive-id` | Search scope drive. Required unless `--dry-run`. |
| `--path` / `--file-id` | Restrict search to an existing folder by path or ID. Omit both to search the whole drive. |
| `--query` | Optional semantic text filter (raw text; CLI wraps and base64-encodes it). |
| `--limit` | Max results, 1–100. |
| `--dry-run` | Print the generated process without API calls. Path options are rejected; use source IDs plus `--source-revision-id`, and omit the path search scope. |

> **LOCAL source image = hard stop.** If the user's source image is a LOCAL file (e.g. `~/Downloads/cat.jpg`, a local path, or a locally-attached image), do **not** `upload-file` it and do **not** run `similar-search` — not even as a "first upload it, then search" convenience. Auto-uploading the local image on their behalf is a **failure**. Stop and tell the user to upload the image to their PDS drive themselves (see `references/upload-file.md`), then re-run once they give you its cloud path or `file_id`. Run `similar-search` **only** when the source **the user pointed to** already exists in PDS (they gave its drive/file id, cloud path, or a PDS-side name to resolve). If the user described the image as local, a same-named file that happens to exist in PDS is **NOT** their image — do not `search-file`/`resolve-path` for it, and do not substitute it. Never fabricate a source `file_id`.

---

## Locating the source image (do this efficiently — do NOT enumerate the whole domain)

The source image is almost always named or path-addressed (e.g. "cat3.jpeg in the enterprise space root", "/Photos/cat.png"). Locate it with **one targeted lookup**, then run `similar-search` directly:

1. **If an absolute path is given** → pass it directly as `--source-path`; do not call `resolve-path` first.
2. **If only a name is given** → identify the one relevant drive first (`aliyun pds list-all-drives`, then pick the space the user named — personal / a specific team / the enterprise space), and run `aliyun pds search-file --drive-id <that_drive> --query 'name match "cat3.jpeg"'` (or `--file-id <root>` + `list-file` for a single named folder). Follow `references/search-file.md` to build the query.
3. Run `similar-search` with `--source-path` or the found `--source-file-id`. **No `get-file` needed** — the latest source revision is auto-fetched when omitted.

If the named source or search space does not resolve to a non-empty `drive_id`, stop. Never call `search-file`, `list-file`, or `similar-search` with an empty ID.

**Hard rule — never brute-force.** Do **not** loop `list-file` over every drive to find the source. One or two targeted `search-file`/`resolve-path` calls are enough. If those calls turn up nothing:

- **Stop.** Do not fall back to scanning all spaces.
- Report clearly to the user that the source image (e.g. `cat3.jpeg`) was not found in the space they described, so similar-search cannot run — and, if a log/output file was requested, write that "not found" conclusion into it.

Blindly enumerating every space wastes dozens of calls and minutes for a result an exact-name search already settled — and a missing source is a real answer, not a reason to search harder.

---

## Response

```json
{
  "similar_files": [
    { "similarity": 0.95, "drive_id": "2", "file_id": "...", "name": "similar1.jpg", "thumbnail": "https://..." }
  ]
}
```

- The CLI promotes `name`, `file_id`, `drive_id`, and `thumbnail` from the service's nested `file` object onto each `similar_files[]` item while preserving the original nested object. Use these stable top-level fields in `--cli-query`, for example: `similar_files[].{similarity:similarity,name:name,file_id:file_id}`.
- `similarity`: 0–1, higher = more similar.
- `limit` is an upper bound; fewer may return (fewer matches, or permission-filtered).

---

## Examples

**Search a whole drive, top 20:**
```bash
aliyun pds similar-search \
  --source-drive-id 1 --source-path "/Photos/cat.jpg" \
  --drive-id 2 --limit 20
```

**Search within a folder, with a semantic filter:**
```bash
aliyun pds similar-search \
  --source-drive-id 1 --source-path "/Photos/cat.jpg" \
  --drive-id 2 --path "/Albums/Cats" --query "cat" --limit 50
```

**Preview the generated parameter only:**
```bash
aliyun pds similar-search \
  --source-drive-id 1 --source-file-id <SRC> --source-revision-id <REV> --dry-run true
```

---

## Best practices
- Prefer image-only retrieval (no `--query`) for best accuracy unless the user explicitly wants image-text hybrid retrieval.
- `--limit`: quick preview 10–20, regular 50, comprehensive 100 (max).
- Only similar **image** search is supported (not video/document).

## Error handling

| HTTP | Code | Fix |
|------|------|-----|
| 400 | OperationNotSupport | Ask PDS support to enable image search. |
| 403 | ForbiddenNoPermission.xxx | Need `FILE.LIST` on the search scope and `FILE.PREVIEW` on the source image. |
