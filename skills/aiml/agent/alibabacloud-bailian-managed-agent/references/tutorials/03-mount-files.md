# Tutorial 03: Feeding a Local Data File to the Agent for Analysis and a Report

| Item | Value |
| --- | --- |
| **Goal** | Mount a local data file (`.txt`; the content can be CSV-formatted) into a session → the Agent reads and analyzes it → produces a report file → download it locally |
| **Capabilities involved** | File / Session resources (runtime mounting) / builtin tools (read, bash, write) / automatic artifact scanning and download / Event |
| **Difficulty** | Beginner |
| **Prerequisites** | [01-ai-native-quickstart.md](01-ai-native-quickstart.md) done (a working Agent and Environment); an API key and workspace ID |
| **Estimated time** | 15-20 minutes |
| **Source** | Official API docs (File / Session resources) + **full-chain field-test evidence** (extension matrix, mounting errors, deletion independence, artifact download) |

## Scenario

However smart the Agent is, it must see the data first. In real business, data almost never lives
in the cloud — it is on your machine, in reports exported from business databases. This step hands
the data into the sandbox: upload it as an independent File resource, mount it onto the session,
and the Agent works with it like a local file.

This tutorial's value concentrates in **three traps**:
**① the `.csv` extension simply will not upload** (an immediate HTTP 415 rejection; you must switch
to a whitelisted extension like `.txt`/`.xlsx`);
**② files must pass the scan before mounting** (mounting right after upload errors out);
**③ the mount path the Agent sees is not the value you fill in** (`mount_path` must start with
`/uploads/`, and the path the Agent sees gains an extra prefix).
Nearly every beginner hits the first two once; the first one dead-ends anyone copying a `.csv`
example at step one.

## Final artifacts

A successfully mounted data file + one session that read it and produced an analysis report + the
report file downloaded locally.

## Steps

### 1. Pick the route first

One job, two routes, different purposes — don't mix them:

| | CLI declarative | API runtime |
| --- | --- | --- |
| How | Declare `files:` at the top level of `agents.yaml` (uploaded at apply) and reference it in `deployments.<name>.resources` with a `mount_path` | `POST /files` to upload → create the session with `resources`, or `POST /sessions/{id}/resources` |
| Fits | Fixed reference data (price lists, rule tables), versioned together with the Deployment | Per-task data that differs every time (user-uploaded reports) |
| Takes effect | At `apply` | In real time; appendable while the session is running |

> **Archived CLI 1.18.1 observation: declarative file mounting had a validation deadlock**:
> `bl managed-agent validate` demands that `mount_path` start with `/mnt/` (filling `/uploads/`
> raises `Bailian file mount_path must start with '/mnt/'.`), but the runtime (Deployment triggers,
> Sessions API) accepts only `/uploads/` — fill per validate's demand and the runtime inevitably
> 400s. Also, there is **no** file-mounting field under `environments:` (filling one gets silently
> stripped while validate still passes).
> For a CLI trial, check current help and attempt one appropriate update before using this observation as a current limitation; see [routing](../workflows/cli-api-routing.md). Customer systems use the API runtime route directly; that is the route illustrated below.

For the CLI-side field syntax, see the skill `bailian-managed-agent` and
[../workflows/provision.md](../workflows/provision.md).
**This tutorial takes the API runtime route** — the one business-system integration uses.

### 2. Upload the file and get the file_id

**Check the extension whitelist first (trap ①, field-tested matrix)** — upload gatekeeping is by
**filename extension**, regardless of the MIME declaration or the file content (a `.csv` extension
is rejected even when declared `type=text/plain`):

| Extension | Upload result |
| --- | --- |
| `.txt` `.md` `.json` `.xlsx` `.pdf` `.png` | ✅ 200; the scan takes ~15 seconds (png as fast as 2) |
| `.csv` `.tsv` | ❌ **HTTP 415** `{"error":{"code":"11900014","message":"file type not allowed"}}` |

> What if the business data is CSV: **rename the extension to `.txt` (content stays untouched)**,
> or save as `.xlsx`. Inside the sandbox the Agent still parses it comma-delimited with
> `bash`/`read` — zero data loss.

```bash
export CMA_BASE="https://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"

FILE_ID=$(curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 120 -s -X POST "${CMA_BASE}/files" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -F "file=@./sales_q3.txt" | jq -r '.id')
echo "$FILE_ID"        # shaped like file_xxx
```

The upload is `multipart/form-data`, not JSON. Field-tested response (note `downloadable` is
`false` at this point — the uploaded source file was never meant for you to download; retrieving
artifacts goes through [section 6](#6-collect-artifacts)):

```json
{"id":"file_xxx","type":"file","filename":"sales_q3.txt","downloadable":false,
 "mime_type":"text/plain","size_bytes":189,"status":"checking","created_at":"..."}
```

**Expected result**: an ID shaped like `file_xxx`, with `status` as `checking`.
**How to verify**: `curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "${CMA_BASE}/files/${FILE_ID}" -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" | jq`

Note the quotas up front — exceeding them fails immediately (an oversized single file
field-tested returns `HTTP 413`, error code `RequestEntityTooLarge`):

| Limit | Value |
| --- | --- |
| Single file | ≤ 10 MB (over the limit: 413; the body states the 10485760-byte cap) |
| Per-workspace total | ≤ 100 GB |
| Retention | 30 days; expired files may be auto-cleaned (long-term use requires periodic re-upload) |

### 3. Wait for the scan to pass (trap ②)

Upload success does not mean the file is ready. A short asynchronous detection/security-scan period follows upload; **wait before creating a Session that attaches the file or mounting it into an existing Session**. Poll with a bounded timeout until `available`; stop on rejection and report a timeout rather than continuing with a pending file. Do not treat a fixed sleep as proof of readiness. The file must pass the security scan:

```
checking ──→ available        # mountable now
         └─→ rejected         # content failed
```

> `type_rejected` (type not supported) exists in the official enum but **cannot actually be
> triggered via the upload path**: extensions off the whitelist are rejected with HTTP 415 right at
> `POST /files`, never reaching the state machine. Type problems surface as 415, not as a status
> transition.

Mounting immediately after upload fails; business code must poll for `available`:

```python
def wait_file_available(file_id, timeout=120.0, interval=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        info = client.files.retrieve(file_id)
        if info.status == "available":
            return info
        if info.status in ("rejected", "type_rejected"):
            raise RuntimeError(f"file failed the security scan: {info.status}")
        time.sleep(interval)
    raise TimeoutError(f"file {file_id} scan timed out")
```

**How to verify**: the `status` field of `GET /files/{file_id}` becomes `available`.

### 4. Mount onto the session

Mount together with session creation (`mount_path` **must start with `/uploads/`** — see trap ③):

```bash
SESSION_ID=$(curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/sessions" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"agent\":\"agent_xxx\",\"environment_id\":\"env_xxx\",
       \"title\":\"Q3 sales analysis\",
       \"resources\":[{\"type\":\"file\",\"file_id\":\"${FILE_ID}\",
                       \"mount_path\":\"/uploads/workspace/sales_q3.txt\"}]}" | jq -r '.id')
```

The session is already running and you want to append a mount:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/sessions/${SESSION_ID}/resources" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"file\",\"file_id\":\"${FILE_ID}\",\"mount_path\":\"/uploads/extra.txt\"}"
```

No session restart needed; field-tested, appending to a **running** session works too, but landing
in the sandbox takes about **35 seconds** from the call — not instantaneous. Don't have the Agent
read right after appending; it won't find the file yet.

**How to verify**: `GET /sessions/{id}/resources` lists the resource; the ID prefix is `sesrsc_`.
Two field-tested details:

```json
{"data":[{"id":"sesrsc_01M...","type":"file",
          "file_id":"file_58q... (note: this is a new file_id copied by the server, not the one you uploaded)",
          "mount_path":"/mnt/session/uploads/workspace/sales_q3.txt",  // the returned value is already the full real path
          "created_at":"..."}]}
```

Mounting is **copy** semantics: the server duplicates a copy into the sandbox; in-session
modifications never touch the original file, and unmounting
(`DELETE /sessions/{id}/resources/{rid}`, field-tested working) cleans up only the in-session copy.
So the same master data file can be mounted into multiple analysis sessions simultaneously without
interference.

> **A sneaky timing trap (field-tested)**: "deleting the original file does not affect the mounted
> copy" holds only **after the file has materialized into the sandbox** (i.e. the Agent has accessed
> it, or the session has been running). If you delete the original after mounting but **before** the
> Agent's first access, the resource list looks fine, yet the sandbox **never sees the file**, with
> no error whatsoever. So don't rush to delete the source right after mounting — at least let the
> session run one turn.

### 5. Path conversion (trap ③, the most frequent)

`mount_path` has two layers of constraints; get either wrong and the Agent reports "file not found":

1. **Fill-in constraint**: must start with `/uploads/` (two field-tested error scenarios: wrong at
   session creation → `invalid_parameter: Invalid resource`; wrong at runtime append →
   `invalid_parameter: Field 'mount_path' must be an absolute path under /uploads/`);
2. **The real path** = `/mnt/session` + your filled-in `mount_path`:

| What you fill in (mount_path) | What the Agent actually sees |
| --- | --- |
| `/uploads/sales_q3.txt` | `/mnt/session/uploads/sales_q3.txt` |
| `/uploads/data/sales.xlsx` | `/mnt/session/uploads/data/sales.xlsx` |

**The prompt must state the real path.** Writing the fill-in value gets the Agent reporting
"file not found", and you'll burn half an hour suspecting a failed mount — the file is mounted
perfectly fine, just at a different location.

```bash
# ① Connect the event stream first (a separate SSE endpoint; POST /events always returns JSON — an Accept header won't make it streaming)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 300 -N -s "${CMA_BASE}/sessions/${SESSION_ID}/events/stream" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" &
sleep 2

# ② Then send the message
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/sessions/${SESSION_ID}/events" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input":[{"role":"user","type":"message","content":[{"type":"text",
       "text":"Read /mnt/session/uploads/workspace/sales_q3.txt, compute Q3 sales by region, identify the regions that declined quarter-over-quarter, and write the conclusions to report.md"}]}]}'
```

**Expected result**: the event stream shows `tool_call`s (`read` to read the file → possibly `bash`
to compute → `write` for the report), ending with `session_status` carrying
`stop_reason: {"type":"end_turn"}`.
**How to verify**: the `read` `tool_call_output` in the stream carries real data content
(field-tested: it includes `"file_path":"/mnt/session/uploads/workspace/sales_q3.txt"` and the
file's original text), not "file not found".

> Prefer assembling the path in code rather than hand-writing it. Changing the mount path and
> forgetting to sync the prompt is how this trap recurs.

### 6. Collect artifacts

There is exactly one main path, and it needs **no registration action of any kind**:

| Route | How | Fits |
| --- | --- | --- |
| **Automatic artifact scanning + Files API** (recommended) | The Agent writes the report into the sandbox's `/mnt/session/outputs/` (require this directory explicitly in the prompt) → files landing there are automatically scanned into downloadable artifacts → `GET /files?scope_id=${SESSION_ID}` to list and get the `file_id` (field-tested: every row `downloadable: true`, `scope` attached to this session) → `GET /files/{file_id}/content` to download | Automated retrieval by the business system |

```bash
# List this session's artifacts (field-tested: no registration tool called at any point, yet report.md appears)
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "${CMA_BASE}/files?scope_id=${SESSION_ID}" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" | jq '.data[] | {id, filename, size_bytes}'
# → {"id":"file_hd4y...","filename":"report.md","size_bytes":1652}

# Download
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 120 -s "${CMA_BASE}/files/${FILE_ID}/content" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" -o report.md
```

Where the two tools sit (use neither as the main path):

- **`mark_artifacts`**: **no configuration, no deliberate invocation needed** by default. Only when
  you wrap a conversational UI around your own business and need "which files did this turn
  produce" displayed against the matching turn do you have the Agent call it to tag (the tags
  appear in the event stream's `tool_call_output`, carrying `file_id` and `path`).
- **`download_file`**: **officially decommissioned**; stop relying on it (existing configs are not
  force-cleaned yet). Its field-tested semantics were: pass a `sandbox_path`, get an OSS signed URL
  expiring in 900 seconds — even before decommissioning it was unfit for business-system retrieval
  (short-lived link; must be re-stored immediately upon receipt). Retrieve artifacts uniformly via
  the Files API above.

> **Archiving vs. artifacts (field-tested)**: artifacts under `/mnt/session/outputs/` **remain
> downloadable** after the session is archived (field-tested: `GET /files/{file_id}/content`
> returns 200 with byte-identical content); what archiving actually reclaims is the sandbox itself —
> intermediate files that never entered the outputs directory or the Files system vanish with it.
> So writing everything worth keeping into `/mnt/session/outputs/` is the correct posture; no need
> to race the download before archiving.

### 7. Wrap-up

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/sessions/${SESSION_ID}/archive" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}"        # stops runtime billing; event history is retained
```

Files themselves **support deletion only, not archiving** (field-tested: `DELETE /files/{file_id}`
returns 200; `POST /files/{id}/archive` returns 404, no such endpoint). Copies already mounted into
a session are unaffected by deleting the original (but mind the timing trap in section 4: deleting
before materialization breaks it). Don't delete reference data — keep it for the next session's
reuse and save one upload and scan.

## FAQ

| Symptom | Cause | Fix |
| --- | --- | --- |
| Upload rejected outright with `HTTP 415` "file type not allowed" (code 11900014) | Extension off the whitelist (field-tested: `.csv`, `.tsv` both rejected) | Rename to `.txt` (content untouched) or save as `.xlsx`; the whitelist checks only the extension — changing the MIME declaration does nothing |
| Upload fails with `HTTP 413` `RequestEntityTooLarge` | Single file over 10 MB | Split the file |
| Mount fails with `Invalid resource` (session creation) / `Field 'mount_path' must be an absolute path under /uploads/` (append) | `mount_path` does not start with `/uploads/`, or the file is still `checking` | Fix the prefix in the former; poll for `available` in the latter |
| The Agent says the file does not exist | The prompt states the fill-in value, not the real path | Write the full real path `/mnt/session` + mount_path in the prompt |
| The Agent cannot read right after a runtime append | Landing in the sandbox takes ~35 seconds (field-tested) | Wait 30-60 seconds before reading, or poll until `GET /sessions/{id}/resources` returns and then wait a bit |
| Two files on the same path fail with `Resource mount path conflicts` | `mount_path` deduplication is by exact string | Give each file a distinct mount path. Note **no normalization happens**: `/uploads//a.txt` and `/uploads/a.txt` are two different mount points |
| Original deleted after mounting; the Agent cannot read it, no error | The source was deleted before the file materialized into the sandbox (the timing trap) | Keep the source at least until the session has run one turn |
| File changed in-session; the original is untouched | Mounting is copy semantics, by design | To persist changes, have the Agent produce a new file and retrieve that |
| `GET /files/{id}/content` returns 403 "file not downloadable" | The file has `downloadable: false` (true of your uploaded source files; never of artifacts) | To download artifacts: `GET /files?scope_id={session_id}` to list this session's artifacts, then download by `file_id` (see section 6) |

## Going further

- Want this analysis to run itself daily → [04-scheduled-deployment.md](04-scheduled-deployment.md)
- The sandbox lacks dependencies like pandas → [05-environment-packages.md](05-environment-packages.md)
- Turn it into business code (scan polling and path assembly included) → [../integration/code-python.md](../integration/code-python.md) Shape B
- Full File semantics and quotas → the File / Resource section of [../product/concepts.md](../product/concepts.md)
