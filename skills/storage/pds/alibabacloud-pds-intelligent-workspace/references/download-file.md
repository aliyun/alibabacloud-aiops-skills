# PDS File Download Guide

> The common download (by cloud path or by `--file-id`, plus get-download-url and the folder→archive pointer) is covered inline in `SKILL.md` — you usually don't need this file. Read on for the full flag table and edge cases.

**Scenario**: Download a file from PDS to local — when the user explicitly wants the raw file saved locally, or as the fallback for analyzing a document extension that server-side analysis does not support.

> If the intent is to **analyze / summarize / close-read** a `pdf`/`ppt`/`pptx`/`doc`/`docx`, audio, or video, do **NOT** download it here and read it yourself. Use `aliyun pds analyze` — see `references/multianalysis-file.md`. Downloading for content understanding is allowed **only** for a document extension outside that set (e.g. `txt`, `md`, `csv`, `xlsx`), per the format gate in that file; in that case save to a temporary local path, read it yourself, and don't present the copy as a file you saved for the user.

`aliyun pds download-to-local` resolves the file, fetches the signed URL, downloads it, and verifies the size — all in one call. Provide **either** `--path` or `--file-id`.

```bash
# By cloud path
aliyun pds download-to-local \
  --drive-id <drive_id> \
  --path "/Photos/2026/04/vacation.jpg" \
  --save-to ./vacation.jpg

# By file_id
aliyun pds download-to-local \
  --drive-id <drive_id> \
  --file-id <file_id> \
  --save-to ./vacation.jpg
```

| Flag | Description |
|------|-------------|
| `--drive-id` | Drive of the file. |
| `--path` / `--file-id` | The file to download (exactly one). A `--path` pointing to a folder is rejected — use `references/archive-download.md`. |
| `--save-to` | Local output path. |
| `--expire-sec` | Signed URL TTL in seconds (default 3600, max 115200). |

Returns `{ "drive_id": ..., "file_id": ..., "local_path": ..., "size": <bytes> }`. The size is verified against the server; a mismatch fails the command. The command only saves the bytes locally — it does not resolve or return the file's cloud path, and you should not go look that path up afterwards.

---

## Finding the file first

- **Only a filename** (e.g., `apple1.jpg`) → use `references/search-file.md` to get the `file_id`, then download by `--file-id`.
- **Multiple files or a whole folder** → use `references/archive-download.md` to package and download a zip.

## Only need the URL (not the file)

If you just need the signed download URL rather than saving the file locally, call `aliyun pds get-download-url --drive-id <drive_id> --path "/absolute/file" --expire-sec 3600` (or use `--file-id` when already known). The path is resolved inside the command. It returns `{ "url": ..., "expiration": ..., "size": ... }`.
