# Java Integration Implementation (Three Shapes, Plain REST)

Companion tutorial: [../tutorials/02-integrate-to-your-system.md](../tutorials/02-integrate-to-your-system.md)

> **Why plain REST instead of the SDK**: every endpoint, request body, and event field on this page
> was verified against the real server. An official Java SDK exists (dashscope, v2.22.24+) — for its
> class names and method signatures, defer to the docs of the version you actually import —
> this page does not guess SDK signatures.
>
> **The event contract is field-tested** (see [code-python.md](code-python.md)): the server pushes
> at least 23 event types (22 in the SDK enum + `tool_approval_request` outside it), the client can
> send 6 kinds, sessions have four statuses including `rescheduling`, and `stop_reason` is an object
> living in the event's `content[*].data` (`GET /sessions/{id}` also returns a copy at the root).
> These facts apply equally to plain REST; the event dispatching below is implemented accordingly.

Dependencies (Maven):

```xml
<dependency>
  <groupId>com.squareup.okhttp3</groupId>
  <artifactId>okhttp</artifactId>
  <version>4.12.0</version>
</dependency>
<dependency>
  <groupId>com.squareup.okhttp3</groupId>
  <artifactId>okhttp-sse</artifactId>
  <version>4.12.0</version>
</dependency>
<dependency>
  <groupId>com.fasterxml.jackson.core</groupId>
  <artifactId>jackson-databind</artifactId>
  <version>2.17.2</version>
</dependency>
```

## Shared client

```java
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import okhttp3.*;

import java.io.File;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

// Initialize UA per workflows/user-agent.md before starting this application.
public class CmaClient {

    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final String baseUrl;
    private final String apiKey;
    private final OkHttpClient http;
    private final OkHttpClient sseHttp;

    public CmaClient(String apiKey, String workspaceId, String region) {
        this.apiKey = apiKey;
        this.baseUrl = String.format(
                "https://%s.%s.maas.aliyuncs.com/api/v1/agentstudio", workspaceId, region);
        String skillUa = System.getenv("BAILIAN_MANAGED_AGENT_SKILL_UA");
        if (skillUa == null || skillUa.isBlank()) {
            throw new IllegalStateException("Initialize the per-run skill User-Agent first");
        }
        this.http = new OkHttpClient.Builder()
                .addInterceptor(chain -> chain.proceed(chain.request().newBuilder()
                        .header("User-Agent", skillUa).build()))
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .callTimeout(60, TimeUnit.SECONDS)
                .build();
        this.sseHttp = http.newBuilder()
                .readTimeout(0, TimeUnit.MILLISECONDS)
                .callTimeout(0, TimeUnit.MILLISECONDS)
                .build(); // caller still enforces a total business deadline and cancels the EventSource
    }

    public static CmaClient fromEnv() {
        return new CmaClient(System.getenv("DASHSCOPE_API_KEY"),
                System.getenv("BAILIAN_WORKSPACE_ID"), "cn-beijing");
    }

    private Request.Builder authed(String path) {
        return new Request.Builder()
                .url(baseUrl + path)
                .header("Authorization", "Bearer " + apiKey);
    }

    private JsonNode execute(Request request) throws IOException {
        try (Response resp = http.newCall(request).execute()) {
            String requestId = resp.header("x-request-id");   // always log this; support tickets resolve instantly with it
            String body = resp.body() == null ? "" : resp.body().string();
            if (!resp.isSuccessful()) {
                throw new CmaException(resp.code(), body, requestId);
            }
            return MAPPER.readTree(body);
        }
    }

    // --- resources ---
    public JsonNode listAgents() throws IOException {
        return execute(authed("/agents").get().build()).path("data");
    }

    public JsonNode listEnvironments() throws IOException {
        return execute(authed("/environments").get().build()).path("data");
    }

    public JsonNode uploadFile(File file) throws IOException {
        RequestBody body = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", file.getName(),
                        RequestBody.create(file, MediaType.parse("application/octet-stream")))
                .build();
        return execute(authed("/files").post(body).build());
    }

    /** After upload, wait for the security scan to pass (status becomes available) before mounting. */
    public JsonNode waitFileAvailable(String fileId, long timeoutMs) throws IOException {
        long deadline = System.currentTimeMillis() + timeoutMs;
        while (System.currentTimeMillis() < deadline) {
            JsonNode info = execute(authed("/files/" + fileId).get().build());
            String status = info.path("status").asText();
            if ("available".equals(status)) {
                return info;
            }
            if ("rejected".equals(status) || "type_rejected".equals(status)) {
                throw new IllegalStateException("File failed the security scan: " + status);
            }
            sleep(2000);
        }
        throw new IllegalStateException("File scan timed out: " + fileId);
    }

    // --- sessions ---
    public JsonNode getSession(String sessionId) throws IOException {
        return execute(authed("/sessions/" + sessionId).get().build());
    }

    public JsonNode createSession(String agentId, String environmentId, String title,
                                  List<Map<String, Object>> resources,
                                  Map<String, String> metadata) throws IOException {
        return createSession(agentId, environmentId, title, resources, null, metadata);
    }

    /** environmentVariables: non-sensitive config injected into the sandbox in plaintext (the agent reads
     *  real values via os.environ directly); high-sensitivity secrets go through a Vault. */
    public JsonNode createSession(String agentId, String environmentId, String title,
                                  List<Map<String, Object>> resources,
                                  Map<String, String> environmentVariables,
                                  Map<String, String> metadata) throws IOException {
        ObjectNode body = MAPPER.createObjectNode();
        body.put("agent", agentId);
        body.put("environment_id", environmentId);
        if (title != null) {
            body.put("title", title);
        }
        if (resources != null && !resources.isEmpty()) {
            body.set("resources", MAPPER.valueToTree(resources));
        }
        if (environmentVariables != null && !environmentVariables.isEmpty()) {
            body.set("environment_variables", MAPPER.valueToTree(environmentVariables));
        }
        if (metadata != null && !metadata.isEmpty()) {
            body.set("metadata", MAPPER.valueToTree(metadata));  // business correlation key; does not affect model behavior
        }
        return execute(authed("/sessions").post(RequestBody.create(body.toString(), JSON)).build());
    }

    /** Archiving flips the session to terminated — runtime billing stops, event history is retained. */
    public JsonNode archiveSession(String sessionId) throws IOException {
        return execute(authed("/sessions/" + sessionId + "/archive")
                .post(RequestBody.create("", JSON)).build());
    }

    // --- events ---
    public static String userMessagePayload(String text) {
        ObjectNode content = MAPPER.createObjectNode().put("type", "text").put("text", text);
        ObjectNode event = MAPPER.createObjectNode();
        event.put("role", "user");
        event.put("type", "message");
        event.set("content", MAPPER.createArrayNode().add(content));
        ObjectNode root = MAPPER.createObjectNode();
        root.set("input", MAPPER.createArrayNode().add(event));
        return root.toString();
    }

    /** Non-streaming send; returns immediately — fits the async shapes. POST /events always returns
     *  a JSON echo — adding an Accept: text/event-stream header does **not** turn it into SSE
     *  (field-tested: 200 application/json). */
    public JsonNode sendEvent(String sessionId, String text) throws IOException {
        return execute(authed("/sessions/" + sessionId + "/events")
                .post(RequestBody.create(userMessagePayload(text), JSON)).build());
    }

    /**
     * Send and receive the event stream over SSE; the listener gets each event as a JsonNode.
     * The live stream is a **separate GET endpoint** /sessions/{id}/events/stream (field-tested
     * 200 text/event-stream, with a :keepalive comment frame every 30 seconds). This method
     * opens the stream first, then POSTs the message in onOpen, so the first frames of the turn
     * are never lost — SSE has no history replay; POST-then-open misses the beginning.
     */
    public okhttp3.sse.EventSource sendAndStream(String sessionId, String text,
                                                 EventHandler handler) {
        Request sseRequest = authed("/sessions/" + sessionId + "/events/stream")
                .header("Accept", "text/event-stream")
                .get()
                .build();

        return okhttp3.sse.EventSources.createFactory(sseHttp)
                .newEventSource(sseRequest, new okhttp3.sse.EventSourceListener() {
                    @Override
                    public void onOpen(okhttp3.sse.EventSource source, Response response) {
                        try {
                            sendEvent(sessionId, text);      // stream established; now the message triggers this turn
                        } catch (IOException e) {
                            source.cancel();
                            handler.onFailure(e, null);
                        }
                    }

                    @Override
                    public void onEvent(okhttp3.sse.EventSource source, String id,
                                        String type, String data) {
                        if (data == null || data.isBlank() || "[DONE]".equals(data)) {
                            return;
                        }
                        try {
                            handler.onEvent(MAPPER.readTree(data));
                        } catch (Exception e) {
                            // log the raw payload for troubleshooting; never break the whole stream on a parse failure
                            handler.onParseError(data, e);
                        }
                    }

                    @Override
                    public void onFailure(okhttp3.sse.EventSource source, Throwable t,
                                          Response resp) {
                        handler.onFailure(t, resp);   // on disconnect, reconnect or degrade to polling
                    }
                });
    }

    /** Poll incremental events: pass the previous response's next_page as page; null on the first call. */
    public JsonNode listEvents(String sessionId, String page, int limit) throws IOException {
        HttpUrl.Builder url = HttpUrl.parse(baseUrl + "/sessions/" + sessionId + "/events")
                .newBuilder().addQueryParameter("limit", String.valueOf(limit))
                .addQueryParameter("order", "asc");
        if (page != null) {
            url.addQueryParameter("page", page);
        }
        return execute(new Request.Builder().url(url.build())
                .header("Authorization", "Bearer " + apiKey).get().build());
    }

    public JsonNode post(String path, String jsonBody) throws IOException {
        return execute(authed(path).post(RequestBody.create(jsonBody, JSON)).build());
    }

    public JsonNode get(String path) throws IOException {
        return execute(authed(path).get().build());
    }

    private static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    public interface EventHandler {
        void onEvent(JsonNode event);

        default void onParseError(String rawPayload, Exception e) { }

        default void onFailure(Throwable t, Response resp) { }
    }

    public static class CmaException extends IOException {
        public final int statusCode;
        public final String requestId;

        public CmaException(int statusCode, String body, String requestId) {
            super("[" + statusCode + "] " + body + " (x-request-id=" + requestId + ")");
            this.statusCode = statusCode;
            this.requestId = requestId;
        }
    }
}
```

## Event dispatching (shared by all three shapes)

```java
public final class EventDispatcher {

    /** The server pushes at least 23 types (22 in the SDK enum + tool_approval_request outside it);
     *  only the tool ones are listed here — safely ignore everything unlisted. */
    private static final java.util.Set<String> TOOL_EVENTS = java.util.Set.of(
            "tool_call", "tool_call_output", "function_call", "function_call_output",
            "mcp_call", "mcp_call_output", "tool_approval_request");

    /** Only idle / terminated count as terminal. rescheduling is an intermediate state — treating it
     *  as terminal closes the stream early and truncates the result. */
    private static final java.util.Set<String> TERMINAL_STATUSES =
            java.util.Set.of("idle", "terminated");

    /** Only multi-agent formations push these 5. */
    private static final java.util.Set<String> THREAD_EVENTS = java.util.Set.of(
            "thread_created", "thread_status", "thread_message_sent",
            "thread_message_received", "thread_context_compacted");

    /** Returning the type of stop_reason signals the turn ended; returning null means continue. */
    public static String handle(JsonNode ev, StringBuilder textBuffer) {
        String type = ev.path("type").asText();
        // In formations one stream mixes every member's output: the server event's thread field
        // is thread_id (main thread thrd_ prefix, member sub-threads sthr_); missing means the
        // coordinator's main thread. Mind the direction: the top-level field is named
        // session_thread_id only when the client sends targeted events
        String threadKey = ev.path("thread_id").asText("main");

        if ("message".equals(type) && "assistant".equals(ev.path("role").asText())) {
            for (JsonNode block : ev.path("content")) {
                if ("text".equals(block.path("type").asText())) {
                    textBuffer.append(block.path("text").asText());
                }
            }
        } else if ("reasoning".equals(type)) {
            // reasoning trace; render here if you show it
        } else if (TOOL_EVENTS.contains(type)) {
            log.info("tool event: {}", type);          // render here if you show the execution trace
        } else if (THREAD_EVENTS.contains(type)) {
            // formations: route by threadKey into per-member records; don't mix them into one textBuffer
            log.info("formation thread event {} thread={}", type, threadKey);
        } else if ("error".equals(type)) {
            log.error("server error event: code={} message={}",
                    ev.path("code").asText(null), ev.path("message").asText(null));
        } else if ("session_status".equals(type)) {
            String status = dataField(ev, "session_status").asText(null);
            if (status != null && TERMINAL_STATUSES.contains(status)) {
                // stop_reason is an object, not a string — shaped like {"type": "end_turn"}
                String reason = dataField(ev, "stop_reason").path("type").asText(null);
                return reason != null ? reason : status;
            }
        } else {
            log.debug("ignoring event type: {}", type);   // most of the 23 types don't matter to business logic — ignore, don't crash
        }
        return null;
    }

    /**
     * session_status and stop_reason live in the event's content[*].data, not at the event root.
     * GET /sessions/{id} also returns a copy of stop_reason at the root — the weak-interaction
     * polling shape reads it directly instead of digging through the event stream (both paths
     * field-tested working).
     */
    private static JsonNode dataField(JsonNode ev, String key) {
        for (JsonNode block : ev.path("content")) {
            JsonNode data = block.path("data");
            if (data.hasNonNull(key)) {
                return data.get(key);
            }
        }
        return com.fasterxml.jackson.databind.node.MissingNode.getInstance();
    }

    /** All three stop_reason.type branches must be handled; checking only idle silently deadlocks the task. */
    public static void assertSuccess(String stopReason, String sessionId) {
        if ("end_turn".equals(stopReason)) {
            return;
        }
        if ("requires_action".equals(stopReason)) {
            throw new NeedsActionException(
                    "Session " + sessionId + " is waiting for tool approval: read pending_call_ids/"
                    + "pending_batch_id from stop_reason and send back a tool_approval_response (see tutorials/06)");
        }
        if ("retries_exhausted".equals(stopReason)) {
            throw new IllegalStateException(
                    "Session " + sessionId + " exhausted retries; treat as failure and alert");
        }
        throw new IllegalStateException("Session " + sessionId + " ended abnormally: " + stopReason);
    }

    public static class NeedsActionException extends RuntimeException {
        public NeedsActionException(String msg) {
            super(msg);
        }
    }
}
```

## Completing a customer deliverable

The Spring and task-store snippets below are application adapters, not a complete standalone project. A runnable deliverable must supply the store interfaces/implementations, dependencies, imports and entry point. In streaming adapters, retain the returned `EventSource`, cancel it on completion/error/client disconnect, and enforce a total business deadline. Reconnect by subscribing and backfilling history, **not** by calling `sendAndStream` again (that resends the message). Preserve waiting-for-approval Sessions; a waiting state must not be archived or converted into success.

## Shape A: synchronous / streaming conversation (**strong-interaction** scenario)

Spring WebFlux / SSE scenario; the business service acts as the proxy layer, and **the key never
ships to the frontend**.

```java
public Flux<String> chatStream(String userId, String text) {
    String sessionId = sessionStore.getOrCreate(userId, () -> {
        try {
            // one Session per user, never shared across users; the server carries the context — no need to replay history
            return client.createSession(AGENT_ID, ENV_ID, "Session of user " + userId,
                    null, Map.of("user_id", userId)).path("id").asText();
        } catch (IOException e) {
            throw new IllegalStateException("Failed to create session", e);
        }
    });

    return Flux.create(sink -> {
        StringBuilder buffer = new StringBuilder();
        okhttp3.sse.EventSource source = client.sendAndStream(sessionId, text, new CmaClient.EventHandler() {
            @Override
            public void onEvent(JsonNode ev) {
                int before = buffer.length();
                String stopReason = EventDispatcher.handle(ev, buffer);
                if (buffer.length() > before) {
                    sink.next(buffer.substring(before));      // incremental pass-through to the frontend
                }
                if (stopReason != null) {
                    try {
                        EventDispatcher.assertSuccess(stopReason, sessionId);
                        sink.complete();
                    } catch (EventDispatcher.NeedsActionException pending) {
                        // The application maps this typed signal to an approval card, not task success.
                        sink.error(pending);
                    } catch (RuntimeException failure) {
                        sink.error(failure);
                    }
                }
            }

            @Override
            public void onFailure(Throwable t, Response resp) {
                sink.error(t != null ? t : new IOException("SSE connection failed"));
            }
        });
        sink.onDispose(source::cancel); // complete, error, deadline or client disconnect releases SSE
    });
}
```

**Gateway note**: Nginx needs `proxy_buffering off;`, or SSE gets buffered into one lump response.

## Shape B: async tasks (submit-then-query, **weak-interaction** scenario)

```java
/** Submit and return immediately; do not wait for the result. */
public String submitTask(String bizOrderNo, String prompt, File input) throws IOException {
    List<Map<String, Object>> resources = null;
    if (input != null) {
        JsonNode uploaded = client.uploadFile(input);
        String fileId = uploaded.path("id").asText();
        client.waitFileAvailable(fileId, 120_000);            // only mountable after the scan passes
        resources = List.of(Map.of("type", "file", "file_id", fileId,
                "mount_path", "/uploads/input.txt"));
        // mount_path must start with /uploads/; the sandbox path = /mnt/session + mount_path —
        // in the example above the agent actually sees /mnt/session/uploads/input.txt, and the
        // prompt must state the real path (.csv is rejected at upload; the whitelist is
        // .txt/.md/.json/.xlsx/.pdf/.png only — rename CSV to .txt first)
        prompt += "\nInput file path: /mnt/session/uploads/input.txt";
    }

    JsonNode session = client.createSession(AGENT_ID, ENV_ID, "Task " + bizOrderNo,
            resources, Map.of("biz_order_no", bizOrderNo));
    String sessionId = session.path("id").asText();

    taskRepo.save(bizOrderNo, sessionId, "submitting");       // persist before the first message
    client.sendEvent(sessionId, prompt);                      // reconcile this Session on ambiguous timeout
    taskRepo.update(bizOrderNo, "running", null);
    return sessionId;
}

/** One fresh Session per task; query current status, then collect history once. */
public void pollTask(String bizOrderNo, long maxWaitMs) throws IOException, InterruptedException {
    Task task = taskRepo.get(bizOrderNo);
    String sessionId = task.sessionId();
    long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.MILLISECONDS.toNanos(maxWaitMs);
    String stopReason = null;
    while (System.nanoTime() < deadline) {
        JsonNode info = client.getSession(sessionId);
        String status = info.path("status").asText();
        if ("idle".equals(status) || "terminated".equals(status)) {
            stopReason = info.path("stop_reason").path("type").asText(null);
            if (stopReason != null) break;
            if ("terminated".equals(status)) {
                taskRepo.update(bizOrderNo, "failed", null);
                return;
            }
        }
        long remainingMs = java.util.concurrent.TimeUnit.NANOSECONDS.toMillis(deadline - System.nanoTime());
        Thread.sleep(Math.max(0, Math.min(5000, remainingMs)));
    }
    if (stopReason == null) {
        taskRepo.update(bizOrderNo, "timeout", null);
        return;
    }
    if ("requires_action".equals(stopReason)) {
        taskRepo.update(bizOrderNo, "needs_action", null);
        return; // keep the Session alive for human approval
    }
    if (!"end_turn".equals(stopReason)) {
        taskRepo.update(bizOrderNo, "failed", null);
        return;
    }
    StringBuilder result = new StringBuilder();
    String cursor = null;
    java.util.Set<String> seenCursors = new java.util.HashSet<>();
    do {
        if (System.nanoTime() >= deadline) {
            taskRepo.update(bizOrderNo, "timeout", null);
            return;
        }
        JsonNode page = client.listEvents(sessionId, cursor, 100);
        for (JsonNode ev : page.path("data")) EventDispatcher.handle(ev, result);
        cursor = page.path("next_page").asText(null);
        if (cursor != null && !seenCursors.add(cursor)) throw new IOException("Repeated page cursor");
    } while (cursor != null); // no next_page ends this pass; do not restart at the first page
    taskRepo.update(bizOrderNo, "success", result.toString());
    // Archive only after all required results/artifacts are collected, under the retention policy.
    // An unconditional finally/archive would terminate a Session waiting for approval.
}

```

## Shape C: scheduled unattended runs (Deployment, **weak-interaction** scenario)

```java
public String createDailyDeployment(int agentVersion) throws IOException {
    String body = """
        {
          "name": "Daily order summary",
          "agent": {"id": "%s", "version": %d},
          "environment_id": "%s",
          "schedule": {"type": "cron", "expression": "0 9 * * 1-5",
                       "timezone": "Asia/Shanghai"},
          "initial_events": [{"type":"message","role":"user",
            "content":[{"type":"text","text":"Summarize yesterday's order data"}]}]
        }
        """.formatted(AGENT_ID, agentVersion, ENV_ID);   // pin the version in production to prevent behavior drift
    // with a schedule, timezone is required (missing → 400 PARAMS_MISSING); initial_events takes 1-50 entries
    return client.post("/deployments", body).path("id").asText();
}

/** For integration testing: trigger once manually, without waiting for the schedule. */
public void triggerNow(String deploymentId) throws IOException {
    client.post("/deployments/" + deploymentId + "/run", "{}");
}

/** The business side periodically pulls run records for artifacts; run_id is the idempotency key
 *  against double processing. */
public void collectRuns(String deploymentId, Set<String> processedRunIds) throws IOException {
    for (JsonNode run : client.get("/deployments/" + deploymentId + "/runs").path("data")) {
        String runId = run.path("id").asText();
        if (processedRunIds.contains(runId)) {
            continue;
        }
        // Single-run query is the global path GET /deployment_runs/{runId};
        // the nested path /deployments/{id}/runs/{runId} 404s (field-tested)
        JsonNode detail = client.get("/deployment_runs/" + runId);
        handleRunResult(detail);
        processedRunIds.add(runId);
    }
}
```

Pause the schedule with `POST /deployments/{id}/pause`, resume with `/unpause` — don't delete-and-recreate.

## Related

- Full endpoint table and fields → [api-endpoints.md](api-endpoints.md)
- Shape selection and more shapes → [patterns.md](patterns.md)
- Python implementation → [code-python.md](code-python.md)
