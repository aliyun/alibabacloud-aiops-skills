# Checkpoint Resume Mechanism

## Principle

Agent-driven migrations do not use checkpoint files. The migration script initializes TeeWriter at startup to write all stdout output to both the console and a log file simultaneously. The log file name is determined by the Agent (e.g. `checkpoint.log`, `migrate.log`, etc.). After each batch write, the cursor and progress are printed; on interruption, the final cursor is printed. The Agent reads this information from the log file; when the user requests a resume, it passes the recovery cursor and count directly into the script parameters.

The log file ensures that checkpoint information can be reliably extracted regardless of whether the script runs in foreground, background, or is interrupted.

## Data Flow

```
Agent executes migration script
  │
  ├─ Script starts: initialize TeeWriter (stdout + log file)
  │
  ├─ After each batch write:
  │    [PROGRESS] cursor=<cursor_value> migrated=<n> total=<N> pct=<x.x>%
  │    → Written to both stdout and log file
  │
  ├─ On interruption:
  │    [INTERRUPTED] cursor=<cursor_value> migrated=<n> total=<N>
  │    → Written to both stdout and log file
  │
  ├─ Agent extracts cursor and migrated values from log file
  │    grep '[INTERRUPTED]' <log_file>
  │
  └─ When user requests resume
       Agent regenerates script, sets recovery cursor and count
```

## Cursor Types by Source

| Source | Cursor | Resume method |
|--------|--------|---------------|
| Milvus | Primary key value (int or str) | query_iterator constructs filter expression: primary key > cursor |
| Elasticsearch (PIT) | sort values (list) | search_after=cursor |
| Elasticsearch (Scroll) | `_id` string | scroll first query adds `_id > cursor` filter |
| Lindorm | `_id` string | scroll first query adds `_id > cursor` filter |
| Qdrant | Point ID (int or UUID str) | scroll(offset=cursor), offset is exclusive (returns Points after cursor) |
| CSV/OSS | Number of processed data rows (int, excluding header) | Re-pull stream then skip first cursor rows |

CSV/OSS source cursor is an integer row offset. Output protocol is the same as other sources; the `cursor` field value is an integer:

```
[PROGRESS] cursor=1000 migrated=1000 total=50000 pct=2.0%
[INTERRUPTED] cursor=2000 migrated=2000 total=50000
```

## Script-Side Implementation Key Points

1. **Log file initialization (execute first)**: Use TeeWriter to write stdout to both console and log file simultaneously (file name determined by Agent). TeeWriter's write/flush methods MUST catch `ValueError` (stream already closed when process exits), avoiding errors during cleanup
2. Parameter section declares recovery cursor (default None) and recovery count (default 0)
3. After connecting to source, construct recovery query based on recovery cursor
4. Print structured progress line after each batch write (`[PROGRESS]` prefix for Agent parsing)
5. Register SIGTERM + SIGINT signal handlers; on interruption, print `[INTERRUPTED]` line then exit
6. Print `[DONE]` line on successful completion
7. Close log file when script ends

### Output Protocol (must be strictly followed)

These three lines are the Agent's sole basis for parsing script status:

```
[PROGRESS] cursor=<cursor_value> migrated=<n> total=<N> pct=<x.x>%
[INTERRUPTED] cursor=<cursor_value> migrated=<n> total=<N>
[DONE] migrated=<n>
```

- `[PROGRESS]`: Print once after each successful batch write
- `[INTERRUPTED]`: Print on SIGINT or SIGTERM, including the last cursor and progress
- `[DONE]`: Print when all migration completes

### Signal Handling Requirements

The Bash tool timeout sends SIGTERM, not KeyboardInterrupt; both signals must be caught. The interruption handler must:
1. Print the last cursor, migrated count, and total as a `[INTERRUPTED]` line
2. **Attempt to clean up source resources**: Close ES PIT / scroll context / Qdrant scroll, etc. Silently ignore cleanup failures (resources auto-expire); do not affect checkpoint info output
3. Exit immediately (exit code 1)

```python
def signal_handler(sig, frame):
    print(f"[INTERRUPTED] cursor={cursor} migrated={migrated} total={total}")
    # Attempt to clean up source resources (best effort, silent on failure)
    try:
        if 'pit_id' in dir():
            es.close_point_in_time(body={"id": pit_id})
        elif 'scroll_id' in dir():
            es.clear_scroll(scroll_id=scroll_id)
    except Exception:
        pass
    _log_file.close()
    sys.exit(1)
```

## Agent-Side Operations

1. Execute migration script (foreground or background)
2. If script is interrupted (non-zero exit code), extract checkpoint info from log file. Prioritize the last `[INTERRUPTED]` line; fall back to the last `[PROGRESS]` line:
   ```bash
   grep '\[INTERRUPTED\]' <log_file> | tail -1 || grep '\[PROGRESS\]' <log_file> | tail -1
   ```
3. Parse using regex `cursor=(.+?)\s+migrated=(\d+)\s+total=(\d+)`. The cursor value must preserve its original type: integer (Milvus INT64 primary key, CSV row offset, Qdrant int ID), string (ES _id, Qdrant UUID), or JSON array (ES PIT sort values like `[1686700800000, "doc_5000"]`) — if cursor value starts with `[`, parse as JSON list
4. On parse failure, MUST inform user and display raw log line; MUST NOT silently restart from beginning
5. Inform user of migration progress and ask whether to resume
6. When user confirms resume, regenerate script with `RESUME_CURSOR` (preserve original type) and `RESUME_MIGRATED` filled into parameter section
7. Lindorm `_bulk` uses `_id` for upsert; duplicate writes do not produce duplicate data

## Key Notes

- On resume, cursor is passed to the source scan API; the source returns data starting after the cursor
- **Off-by-one defense**: On resume, MUST ensure no duplicate or missing data. Cursor semantics by source: Milvus primary key > cursor (exclusive), ES/Lindorm search_after/scroll is exclusive, Qdrant scroll offset is exclusive, CSV row offset skips first N rows (exclusive). The Agent MUST pass the source-provided cursor value as-is when generating the resume script; MUST NOT manually +1 or -1 adjust
- **`[INTERRUPTED]` line format requirement**: MUST contain `cursor`, `migrated`, and `total` fields; missing any one prevents the Agent from correctly extracting checkpoint info. Example: `[INTERRUPTED] cursor=abc123 migrated=50000 total=120000`
- Recovery count is only for progress display (percentage calculation base); does not affect actual data
- The log file is the Agent's sole reliable source for extracting checkpoint info; does not depend on stdout capture
- When running in background, stdout may be lost; the log file ensures checkpoint info is always extractable

## Checkpoint Precision with Concurrent Writes

When using concurrent writes (`num_workers >= 2`), multiple batches are in-flight simultaneously; cursor recording requires special attention:

**Principle**: The cursor MUST record the cursor value of the "last batch **confirmed as successfully written**," not the "last batch submitted to the thread pool."

**Implementation**:

1. The reading thread scans data from the source in order, assigning an incrementing sequence number `seq` to each batch
2. `[PROGRESS]` lines are only printed on batch write success callbacks, and MUST be output in `seq` order — i.e. even if seq=3's batch completes first, it must wait for seq=1 and seq=2 to complete before printing seq=3's cursor
3. Use an ordered dict `completed_batches` to buffer completed but not-yet-in-order batches; each time a batch completes, check from the beginning for consecutive completed sequence numbers and output
4. On interruption, the `[INTERRUPTED]` line prints the cursor of the last **in-order confirmed** cursor value (not the highest completed sequence number)

**Why in-order confirmation is needed**: If using the highest completed sequence number's cursor directly, when seq=2 fails but seq=3 succeeds, resuming would skip seq=2's data, causing data loss. In-order confirmation ensures all data before the cursor has been successfully written.

**Code key points**:

```python
import threading

cursor_lock = threading.Lock()
last_confirmed_seq = -1
last_confirmed_cursor = RESUME_CURSOR
completed = {}  # {seq: (cursor, batch_size)}

def on_batch_done(seq, batch_cursor, ok_count, err_count):
    global last_confirmed_seq, last_confirmed_cursor, migrated
    with cursor_lock:
        completed[seq] = (batch_cursor, ok_count)
        # In-order confirmation: check from last_confirmed_seq+1 for consecutive completed batches
        while last_confirmed_seq + 1 in completed:
            next_seq = last_confirmed_seq + 1
            c, n = completed.pop(next_seq)
            last_confirmed_seq = next_seq
            last_confirmed_cursor = c
            migrated += n
            pct = (migrated / total * 100) if total else 0
            print(f"[PROGRESS] cursor={last_confirmed_cursor} migrated={migrated} total={total} pct={pct:.1f}%")
```

> Lindorm `_bulk` uses `_id` for upsert; even if a few batches are written redundantly, no duplicate data is produced. Therefore the safe strategy for resuming is "better to re-write than to miss."
