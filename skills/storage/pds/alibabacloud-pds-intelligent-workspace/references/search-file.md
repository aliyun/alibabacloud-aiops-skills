# PDS File Search

**Scenario**: When you have obtained the drive_id to search in and need to search for files under that drive
**Purpose**: Search for corresponding files and get file attributes such as file_id

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
3. Merge the modality from semantic query and category conditions from scalar query
4. Connect all parts with correct logical operators

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

2. **Combine conditions appropriately**: Semantic search can be combined with scalar conditions, e.g., "beach photos from this year" can use both time range and semantic description

3. **Note pagination limits**: limit maximum is 100, large result sets require pagination

4. **Time format specification**: Time conditions use UTC format `YYYY-MM-DDTHH:mm:ss`

5. **Language consistency in semantic search**: Semantic query text should maintain the same language as user input, do not translate
