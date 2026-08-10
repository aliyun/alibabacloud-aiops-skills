# PDS File Search

Use search only after applying the target-resolution order in `SKILL.md`. Do not search when explicit IDs, `scope.files`, or an exact cloud path already identify the target. Do not spawn a sub-agent for search planning.

## 1. Prefer the cheapest lookup

- Known cloud path → `resolve-path`, not search.
- Known folder + direct children → `list-file`, not search.
- Filename/content/metadata anywhere in one or more drives → the workflow below.
- A zero-result recursive search is a valid result. Never brute-force every folder with `list-file`.

## 2. Search with typed flags in one call

> **Mandatory**: Use `search-file` with typed flags. The command builds and validates the PDS query internally. Hand-writing `--query` strings (e.g. `file_extension in ['jpg', 'png'] AND type = 'file'`) is a **FAILURE** unless the user or another trusted system explicitly supplied an already validated query.

For common conditions, use typed flags. Combine as needed:

```bash
aliyun pds search-file \
  (--drive-id <drive_id> | --drive-id-list <drive_id_1> <drive_id_2> ...) \
  [--name "budget"] \
  [--file-type file|folder] \
  [--category image|video|audio|doc|zip|app|others] \
  [--file-extension pdf] \
  [--min-size <bytes>] [--max-size <bytes>] \
  [--created-after <RFC3339>] [--created-before <RFC3339>] \
  [--updated-after <RFC3339>] [--updated-before <RFC3339>] \
  [--semantic-text "sunset over the sea"] \
  [--semantic-modality image|video|audio|doc ...] \
  [--sort created_at|updated_at|name|size] [--order asc|desc] \
  [--marker <next_marker>] \
  --limit 100 --recursive true --return-total-count true
```

Examples:

```bash
# Filename-only fuzzy match
aliyun pds search-file --drive-id <drive_id> --name "report.docx" --limit 100 --recursive true

# Documents updated since a date, newest first
aliyun pds search-file --drive-id <drive_id> --category doc \
  --updated-after 2026-01-01T00:00:00Z --sort updated_at --order desc --limit 100 --recursive true

# Semantic image search
aliyun pds search-file --drive-id <drive_id> --semantic-text "sunset over the sea" --semantic-modality image --limit 100 --recursive true

# Semantic doc search by TOPIC (content), not filename — e.g. "documents about large language model technology"
aliyun pds search-file --drive-id <drive_id> --semantic-text "large language model technology" --semantic-modality doc \
  --created-after 2026-01-01T00:00:00Z --limit 100 --recursive true
```

The command returns normal SearchFile JSON through the standard CLI output pipeline. `--cli-query` remains available for field projection. For pagination, repeat the exact typed flags and add `--marker <next_marker>`; do not extract or reconstruct the internal query.

**Topic / subject queries use semantic search, not `--name`.** When the user asks for files **about / related to / on the subject of** something ("documents about large language model technology", "materials on X", "content involving X"), the match is on **content**, so use `--semantic-text "<topic>"` (with the right `--semantic-modality doc|image|video|audio`). Do **not** use `--name` for a topic — filenames rarely contain the topic words (e.g. an LLM paper named `2407.10671v4.pdf`), so `--name` silently misses them. Reserve `--name` for when the user names the file/keyword in the filename itself.

**Semantic + scalar hybrids are still the typed-flags path.** Combining `--semantic-text` with scalar flags (`--file-extension`, `--category`, `--updated-after`/`--created-after`, `--min-size`, …) in one `search-file` call is fully supported — e.g. `search-file --drive-id <id> --semantic-text "large language model technology" --semantic-modality doc --file-extension pdf --updated-after 2026-01-01T00:00:00Z`. Do **NOT** reach for `query-prompt` just because the request mixes a topic with time/type/size filters.

### Uncommon conditions

`query-prompt` is a **last resort**, only for a condition that the typed flags above genuinely cannot express (rare). If every part of the request maps to a typed flag — including `--semantic-text` for the topic — use the typed flags directly and do **not** call `query-prompt`. When typed flags truly cannot represent the request, keep planning in the current agent:

1. Run `aliyun pds query-prompt --type unified` and use the returned rubric locally. Do not spawn another agent.
2. Produce only the `{scalar, semantic}` structured plan described by that rubric, with the current ISO-8601 time included when interpreting relative dates.
3. Execute it through the same search command:

```bash
aliyun pds search-file --drive-id <drive_id> --unified-json '<structured-plan-json>' --limit 100 --recursive true
```

Never combine `--unified-json` with `--query` or typed flags. If validation fails, correct the structured plan; do not hand-write the final PDS query.

## 3. Scope and pagination

For several drives, use one request with at most 10 IDs:

```bash
aliyun pds search-file \
  --drive-id-list <drive_id_1> <drive_id_2> ... \
  --name "report" --file-extension pdf \
  --limit 100 --recursive true --return-total-count true
```

Reuse the single `list-all-drives` result when choosing drive IDs. If more than 10 drives are relevant, search deliberate batches rather than silently dropping drives.

Treat a successful multi-drive response as authoritative, including `items: []`. A batched `--drive-id-list` search already scans every listed drive recursively, so an empty result means those drives genuinely hold no match — it is a completed search, not a signal that the search was too narrow. When the result is empty, report the zero hit and stop; do **not** do any of the following to "try harder":

- re-running the same query as one `search-file --drive-id` call per drive (the batch already covered each drive — per-drive re-runs cannot surface a hit the batch missed);
- dropping or loosening a filter the user's request implied, e.g. removing `--file-type file`, `--category`, or a date bound (this answers a *different*, broader question and risks returning off-target files the user did not ask for);
- lowering precision in any other way merely because the count was zero.

Each of these wastes quota and, worse, can present results that don't match what was asked. Retry or diagnose per drive **only** when the batch command itself returns an error (not empty items), and make clear you are diagnosing an error rather than presenting the requested search.

## 4. Interpret results safely

- Read `items`, `total_count`, and `next_marker` from JSON.
- Fetch another page only when the user needs more results; pass `next_marker` as `--marker`.
- For a side effect, require exactly one intended target. If several matches remain, ask the user to choose.
- Keep semantic text in the user's language.
- Do not translate a filename into a content-semantic search unless the user asks to search by content.
