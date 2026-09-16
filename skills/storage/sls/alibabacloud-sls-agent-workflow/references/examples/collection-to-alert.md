# Example: collection to alert

Goal: collect application log files with LoongCollector and notify the on-call group when the error count exceeds a threshold.

Reuse existing resources where available. The steps describe the sequence; use CLI help and the selected skills for operation details. Each stage names its owner, and its acceptance evidence gates the next stage.

1. **Prepare the source and goal.** Identify the host, log file path, alert condition, and notification recipients. For example, a fresh Linux ECS instance — no collector installed yet — runs an application that writes one JSON log per line to `/var/log/checkout/access.log`:

   ```jsonl
   {"request_id":"r1","service":"checkout","status":200,"latency_ms":20}
   {"request_id":"r2","service":"checkout","status":500,"latency_ms":120}
   {"request_id":"r3","service":"checkout","status":500,"latency_ms":160}
   ```

   Alert intent: evaluate every minute over the previous five minutes of data, and notify the on-call group when at least two HTTP errors with status exactly 500 occur.

2. **Prepare the destination.** Choose the region, Project, and Logstore. If needed, use `aliyun sls create-project` and `aliyun sls create-log-store` to create the resources.
3. **Install LoongCollector.** Hand to `alibabacloud-loongcollector-ops`, which owns host-side installation and upgrade. On a fresh host, installation is a required stage, not an assumption. Acceptance: the collector process is running and reports its version.
4. **Create the machine group and verify heartbeat.** Stay in `alibabacloud-loongcollector-ops`: create a machine group, add the host, and confirm its heartbeat appears. The heartbeat proves the installation end to end — process, network, and identity — and gates collection configuration.
5. **Configure collection and indexes.** Use `alibabacloud-loongcollector-ops` to configure log collection from the samples, select the destination Logstore, and bind the collection config to the machine group. Configure the corresponding indexes together with the collection fields.
6. **Verify collected logs and the alert query.** After the collection and index configurations take effect, generate fresh application logs. Use `alibabacloud-sls-query` to verify their arrival and query the error count that the alert will evaluate.

   ```sql
   service:checkout |
   SELECT count(*) AS errors FROM log WHERE status = 500
   ```

   With only the three sample logs in the query window, expect `errors = 2`. Use this result field for the alert threshold.

7. **Configure alerting.** Use `alibabacloud-sls-alerting` to create the alert rule from the verified query. Pass the evaluation schedule (every minute) and the query window (the previous five minutes) as two separate settings — how often the rule runs and which data each run reads are different things. Set the threshold to `errors >= 2`; a non-empty aggregate row alone does not mean the condition is met — the value must cross the threshold. Create or reuse notification objects for the on-call group.
8. **Verify the outcome and confirm the alert event.** Verify each layer separately: rule readback proves configuration only; notification delivery confirms the on-call group was reached. When the rule fires, use `alibabacloud-sls-alerting` to confirm the event from alert history — whether it fired, why, and how long it lasted — before reporting the loop as closed. Configuration success at any earlier stage does not prove delivery of the loop.
