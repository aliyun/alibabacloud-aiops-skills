# PDS File Search

**Scenario**: When you already have the `drive_id` to search in and need to search for files under that drive
**Purpose**: Find the target files and retrieve attributes such as `file_id`. Supports scalar search based on metadata such as filename, type, size, and time, as well as multimodal semantic search based on content understanding.

## Core Workflow

### Step 1: Semantic Query Analysis

Run the script `python scripts/get_semantic_query_prompt.py`, get the prompt from standard output (stdout), then use this prompt as the system prompt and the user's natural language query as user input, spawn a sub-agent to think and output JSON result, and report back to the main agent.

### Step 2: Scalar Query Analysis

Run the script `python scripts/get_scalar_query_prompt.py`, get the prompt from standard output (stdout), then use this prompt as the system prompt and the user's natural language query as user input, spawn a sub-agent to think and output JSON result, and report back to the main agent.

**Important**: You need to prepend current time information `UserQueryDatetime: {current time in ISO format}` to the user input, because the scalar query prompt contains time-related examples that need to reference the current time.

### Step 3: Build Query String

Pass the JSON outputs from Step 1 and Step 2 to `scripts/build_query.py`:

```bash
python scripts/build_query.py \
  --scalar-json '{JSON output from Step 2}' \
  --semantic-json '{JSON output from Step 1}'
```

The script will:
1. Recursively parse the Query object from scalar query into a query string
2. Convert semantic query to `semantic_text = "..."` format
3. Merge the modality from semantic query and the category conditions from scalar query according to the retrieval mode
4. Connect all parts with correct logical operators

**Modality merge rules (important)**

1. Pure scalar retrieval supports multi-modal filtering, for example images or videos.
2. Pure semantic retrieval supports only a single modality and must converge to exactly one of `document`, `image`, `video`, or `audio`.
3. Mixed retrieval must converge to the single modality selected by semantic retrieval.
   - If the scalar `category` includes that semantic modality, use the semantic modality as the final modality.
   - If the scalar `category` conflicts with the semantic modality, do not continue the search. Instead, tell the user to adjust the conditions and try again.

**Important**: If the script execution fails, it is strictly forbidden to construct `query` and `order_by` on your own understanding for the next step, as this will very easily produce syntax errors. You should go back to step one and restart the query process from the beginning.

If the output `has_query` is `false`, do not execute the search, and kindly inform the user of the `message` content.

If `has_query` is `true`, use the output `query` and `order_by` for the next step.


### Step 4: Execute Search

Use the `query` and `order_by` output from build_query.py to call the `aliyun` CLI tool:

```bash
aliyun pds search-file \
  --drive-id "drive_id" \
  --query "{query from build_query output}" \
  --order-by "{order_by from build_query output}" \
  --limit 50 \
  --recursive true \
  --return-total-count true \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Pagination**: If the response contains `next_marker`, you can pass it via `--marker` parameter in subsequent requests to get the next page. Add `--return-total-count` to get the total count of matches.

### Step 5: Display Search Results

Parse the JSON output returned by the CLI tool and format the search results for display. The response structure contains an `items` array and optional `next_marker`, `total_count` fields. If there is a `next_marker`, it means there are more results available for pagination.

Output error messages to stderr on failure.

## Best Practices

1. **Prefer semantic search**: When users describe file content or scenarios, semantic search is more accurate than keyword matching

2. **Combine conditions appropriately**: Semantic search can be combined with scalar conditions, for example "beach photos from this year" can use both a time range and a semantic description

3. **Distinguish pure scalar multi-modal filtering from mixed-query single-modality convergence**:
   - Pure scalar example: `images or videos larger than 10 MB`
   - Mixed, convergent example: `beach photos taken this year`
   - Mixed, conflicting example: `find sunset photos inside video files`

4. **Note pagination limits**: `limit` has a maximum value of 100, and large result sets require pagination

5. **Time format specification**: Time conditions use UTC format `YYYY-MM-DDTHH:mm:ss`

6. **Language consistency in semantic search**: The semantic query text must stay in the same language as the user's input. Do not translate it.
