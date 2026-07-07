# Consumer Group — How It Works

Background knowledge to help the agent reason about Consumer Group behavior, configuration, and troubleshooting. This is not a per-SDK guide — see each SDK's `consume-logs.md` for code.

## Data Model

```
Logstore
 └─ Shard 0 … Shard N-1       (each shard is an ordered log stream)
     └─ Consumer Group A       (one Logstore can have multiple consumer groups; they are independent)
         ├─ Consumer 1         (holds Shard 0, 1)
         └─ Consumer 2         (holds Shard 2, 3)
     └─ Consumer Group B
         └─ Consumer X         (holds Shard 0 … N-1, consumes independently from Group A)
```

- Different consumer groups under the same Logstore are fully independent — each group tracks its own consumption progress.
- Within a consumer group, multiple consumers **cooperate** to consume the Logstore's shards.

## Shard Assignment & Load Balancing

- Each consumer periodically sends a **heartbeat** to the server, reporting its currently held shards. The server responds with the set of shards **assigned** to that consumer.
- The server discovers consumers through heartbeats and dynamically (re-)assigns shards across consumers to maintain load balance.
- A single consumer can be assigned **0 to many** shards. If a consumer holds no shards, it is idle (standby).
- Data consumption is per-shard and concurrent across shards: within a single shard, logs are linearly ordered and consumed strictly in write order using a **cursor**.

## Consumer Count

- Within a single process, at most **one consumer instance per consumer group** is needed — it can consume multiple shards concurrently.
- Total consumer count across all processes should be **≤ shard count**. Ideally the shard count is evenly divisible by the consumer count for balanced assignment.
- Excess consumers remain idle.

## Consumer Naming

- Consumer names must be **unique within the consumer group**.
- Use a deterministic name containing e.g. IP + PID or a persistent UUID, not a random value each restart.
- If a consumer restarts with the **same name**, it can quickly re-acquire its previous shard assignments (fast failover). A new random name causes a delay — the old assignment must first time out before the shards can be re-assigned by server.

## Checkpoint (Consumption Progress)

- After processing a batch of logs, the consumer can save a **checkpoint** (the cursor position) via API.
- Two modes:
  - **Local / memory** (`force=false`) — saves to local memory only; fast, you can always save checkpoints locally after each batch.
  - **Server-side** (`force=true`) — sends the checkpoint to the server immediately; slower (one API call per save).
- On failover or restart, the consumer reads the last **server-side** checkpoint and resumes from that position — logs are not lost, but may be redelivered from the last saved point (at-least-once).
- Recommendation: call `SaveCheckPoint(false)` after each batch in the process callback; let the SDK background timer handle the periodic `force=true` flush. Trigger an explicit `force=true` save on graceful shutdown.

## Cursor & Start Position

- The consumer group config specifies an initial cursor position: **BEGIN** (from the oldest data), **END** (from the newest / tail), or a **specific timestamp**.
- This start position is **only effective when the consumer group is first created**. On subsequent restarts, consumption resumes from the last saved checkpoint, regardless of the configured start position.
- The SDK automatically creates the consumer group on the server if it does not exist — no manual creation needed.

## Shard Splitting & Order

- When a shard A is split into shards B and C, the `order` config parameter controls behavior:
  - `order = true` — all data on shard A must be fully consumed before B and C start being consumed (strict order).
  - `order = false` — B and C can be consumed immediately, potentially in parallel with A's tail.

## Pull Model & Concurrency

- SDK consumption is **pull-based, per shard**: the SDK pulls a batch of data, hands it to the user-defined process function, waits for it to complete, then pulls the next batch. This means back-pressure is automatic — a slow processor simply slows the pull rate.
- The process function is invoked **concurrently across shards** — ensure your processing logic is **thread/goroutine-safe** if it touches shared state.

## Limits

- Max **30 consumer groups per Logstore**.
