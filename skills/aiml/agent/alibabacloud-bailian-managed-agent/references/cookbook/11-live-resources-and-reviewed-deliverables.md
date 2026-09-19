# 11 · Live resources, deliverable downloads, and tool approval

Scenario: order analysis is already underway when the user provides more data. The Agent reads the added file and updates its result; the business service downloads the deliverable. Controlled operations require main-Agent tool approval before execution resumes.

**Test scope**: 2026-09-18, cn-beijing, `qwen3.8-max`. Verified upload review, creation-time mounting, dependency import, artifact download, runtime file addition/removal, and one main-Agent approval. MultiAgent and manual Deployment were tested separately. Each capability has real-call evidence; arbitrary combinations are not implicitly verified.

## Run the example

See [09](09-working-memory-and-web-research.md#run-the-example) for dependencies and authentication.

```bash
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute --bl-config "$HOME/.bailian/config.json" \
  --scenarios files approval multiagent deployment vault \
  --output /tmp/ma-deliverable-check
```

Implementation: [cookbook_smoke.py](../../scripts/cookbook_smoke.py). Results go to `live-results.jsonl` and resource IDs to `ledger.json` in the output directory. By default, no recurring schedule or Webhook notification is created.

## From source file to deliverable

1. Create an Environment with `humanize` and an Agent with `bash/read/write`. Successful Environment creation does not establish dependency readiness; handle explicit not-ready errors as described in the [readiness guide](../tutorials/05-environment-packages.md). In this test, the first Session succeeded and imported `humanize` at runtime.
2. Upload three CSV rows. A `.csv` filename returned HTTP 415; the same content uploaded successfully as `.txt`. Keep the original source and change the multipart filename or use a `.txt` copy.
3. Poll file review until `available`; do not replace status checks with a fixed sleep.
4. Create a Session with `resources: [{"type":"file","file_id":"<id>","mount_path":"/uploads/audit.txt"}]`.
5. Reference `/mnt/session/uploads/audit.txt` in the prompt; request a total written to `/mnt/session/outputs/total.txt`.
6. Find `total.txt` with `downloadable: true` through `GET /files?scope_id={session_id}`, then download `GET /files/{file_id}/content`.

The downloaded content was exactly `350`. Uploaded source files and generated artifacts differ in `downloadable`; do not assume the uploaded source is a downloadable artifact.

## Add and remove resources at runtime

For an existing Session:

```text
POST /sessions/{id}/resources
{"type":"file","file_id":"<available_file_id>","mount_path":"/uploads/late.txt"}
```

Save the returned `sesrsc_...` **resource ID**. The returned `mount_path` is the full sandbox path; `file_id` may refer to a server-side copy.

- Read: have the Agent wait with a deadline for `/mnt/session/uploads/late.txt`, then read it. The test read the same three rows and computed 350.
- Unmount: `DELETE /sessions/{id}/resources/{resource_id}`; this is not deletion of the uploaded File.
- Verify: the resource list no longer contains the ID, and the Agent confirms the path has disappeared. Both checks passed.

Do not promise a fixed 35-second propagation delay; that was one historical observation. In this test, the path had appeared/disappeared by the first tool check. Use runtime checks with deadlines.

Memory Stores do not use this dynamic add/remove workflow; see [09](09-working-memory-and-web-research.md).

## Approval and resumption

Configure the main Agent's tool:

```json
{"name":"bash","enabled":true,"permission_policy":{"type":"always_ask"}}
```

The test requested only the synthetic command `printf AUDIT_APPROVED`. Inspect `tool_approval_request` and match the tool name, command arguments, `batch_id`, and `call_id` before approving. The test then received tool output and a final answer. **Approval covers this known command only**; test authorization does not permit automatically approving arbitrary pending calls.

Send:

```json
{"input":[{"role":"user","type":"tool_approval_response","content":[
  {"type":"data","data":{"batch_id":"<pending_batch_id>","call_id":"<pending_call_id>","result":"allow"}}
]}]}
```

For SSE, subscribe before approving. For polling, retain pre-send event IDs and wait for a new terminal event so an old `requires_action` is not mistaken for the post-approval outcome. HTTP 200 means queued; verify execution and a new `end_turn`. See [tutorial 06](../tutorials/06-tool-approval.md) for the complete example and human decision interface.

## MultiAgent and manual Deployment acceptance

- MultiAgent: create a math member and coordinator, pin the member version, and request delegation of `17×19`. Observed `thread_created` and `thread_message_sent/received`, a member result of 323, and coordinator output `COORDINATOR_RESULT=323`. The final answer alone does not prove delegation.
- Split frontend output by `thread_id`; do not append `sthr_` member drafts to the main answer.
- **Approval currently supports only the main Agent**. Targeted member messages do not establish member tool-approval support.
- Deployment: omit `schedule`, trigger `/run` once, query `/deployment_runs/{run_id}`, and verify `succeeded` plus `AUDIT_DEPLOYMENT_OK` in the corresponding Session. This does not test cron triggering.
- Vault: use synthetic dummy values, verify environment variables contain placeholders, and output only a boolean. Real external-service authentication was not tested; do not send secrets to echo services.

## Cleanup and coverage limits

The script cleans up only IDs recorded from its own creation responses, including after failures. Do not reuse an output directory and overwrite its ledger. Retry cleanup with:

```bash
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute --cleanup-only --bl-config "$HOME/.bailian/config.json" \
  --output /tmp/ma-deliverable-check
```

Agent, Deployment, and Memory Store are archived with history retained. Session, Environment, uploaded File, Vault credentials, and Vault are deleted. Do not claim that all historical records are physically removed.

Webhook is available, but end-to-end delivery and signature verification require a customer-controlled public receiver. None was available for this run; historical evidence in the [Webhook cookbook](06-webhook-event-notifications.md) does not count as current verification. ACTIVE Webhooks may deliver automatically; omitting `/test` does not prevent notifications.

Sources: [resource mounting API](https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/session/resource-create.md), [tools and approval](https://docs.agent.bailian.aliyun.com/zh/managed-agents/build-agent/tools.md), [MultiAgent](https://docs.agent.bailian.aliyun.com/zh/managed-agents/build-agent/multiagent.md).
