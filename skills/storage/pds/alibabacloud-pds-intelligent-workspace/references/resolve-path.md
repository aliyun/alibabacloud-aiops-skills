# Resolve Between Cloud Path and file_id

**Scenario**: Convert a cloud path (e.g., `/Photos/2026/04/vacation.jpg`) to a `file_id`, a `file_id` back to its full path, or a bare name / partial path to the best-matching file or folder.

Use `aliyun pds resolve-path` — it does the whole traversal (including pagination and ambiguity checks) in one call. Do **not** hand-roll the `list-file` loop.

---

## Path → file_id (forward)

```bash
aliyun pds resolve-path \
  --drive-id <drive_id> \
  --path "/Photos/2026/04/vacation.jpg"
```

Returns `{ "drive_id": ..., "file_id": ..., "path": "<normalized>", "file": { ...file object... } }`.

- Errors if a segment does not exist, is ambiguous, or an intermediate segment is not a folder.
- Add `--create-missing` to create any missing folders along the path (upload scenarios). With it, missing intermediate segments are created as folders and the final `file_id` is returned.

```bash
aliyun pds resolve-path \
  --drive-id <drive_id> \
  --path "/Photos/2026/04" \
  --create-missing true
```

## file_id → path (reverse)

```bash
aliyun pds resolve-path \
  --drive-id <drive_id> \
  --file-id <file_id>
```

Returns the same shape, with `path` set to the full cloud path.

## name or partial / relative path → file_id (fuzzy, one call)

When you have only a **name** (`saved-images`) or a **partial / relative path** (`photo-edit/saved-images`, leading slash optional) — not a confirmed absolute path — use `--name`. The CLI runs one recursive search on the last segment, fetches each hit's full path, keeps only hits whose path ends with the given relative path, and ranks them (exact name > prefix > substring, newest `updated_at` as tie-break) — all server-side in one call, so a nested folder resolves without any `list-file` sweep:

```bash
aliyun pds resolve-path --drive-id <drive_id> --name "saved-images" --type folder
aliyun pds resolve-path --drive-id <drive_id> --name "photo-edit/saved-images"
```

- `--type folder|file` is optional; it restricts the search to that kind.
- **Unique** best match → same shape as `--path`: `{ drive_id, file_id, path, file }`.
- **Ambiguous** (2+ candidates tie at the top rank) → `{ "drive_id": ..., "ambiguous": true, "query_name": "<input>", "candidates": [ { file_id, path, type, size, updated_at }, ... ] }` — no top-level `file_id`. Present the candidates and let the user choose before any side effect.
- **No match** → the command errors with `no {file|folder|file or folder} matching "<name>" found`. That is a valid "not found"; never fall back to `list-file` enumeration.
- `resolve-path` takes a single `--drive-id`. To resolve a name across **multiple** drives (all of the user's spaces), use `search-file --drive-id-list` instead (`references/search-file.md`).

Exactly one of `--path`, `--file-id`, and `--name` must be provided.
