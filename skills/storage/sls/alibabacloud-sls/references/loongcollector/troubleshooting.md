# Troubleshooting Playbooks (no-data, heartbeat)

Covers no-data and heartbeat only. Delay, duplicate, parse-failure, container-filter, and data-loss are out of scope.

## 0. Check sequence

Checks should follow:
`classify -> heartbeat & version -> config & binding -> alarm/metric -> business data -> minimal fix -> re-verify`

Heartbeat or binding failures can prevent the collector from receiving the new
configuration; check these first so an unapplied configuration is not mistaken
for a parsing or sending failure.

- Cloud visibility and collector-side evidence corroborate each other; neither substitutes the other.
- Resource-not-found errors never terminate the remaining independent read-only checks; record attempted command/error and continue. Permission failures still hard-stop.

You may use the following evidence templates. `N/A`, `unknown` and
`Resource not found` identify unavailable values or absent resources:

  `[Heartbeat Evidence] [Evidence: heartbeat] lastHeartbeatTime: <value|N/A> | version: <value|N/A> | status: <online|offline|unknown> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`

  `[Alarm Evidence] [Evidence: alarm] alarm_type: <hit:type|miss|unknown> | alarm_message: <value|N/A> | query_result: <row_count|N/A> | time_range: <from-to> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`

  `[Collection Evidence] [Evidence: collection] data_count: <value|N/A> | time_range: <from-to> | status: <new_data|no_data|unknown> | reason: <explicit reason> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`

  `[Binding Evidence] [Evidence: binding] config_name: <value|N/A> | machine_group: <value|N/A> | status: <bound|unbound|unknown> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`

  `[Pipeline Evidence] [Evidence: pipeline] topic: <value|N/A> | data_count: <value|N/A> | time_range: <from-to> | progress: <Complete|Incomplete|unknown> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`

The report can include symptom class, root-cause evidence, the proposed fix,
callback location and Lens context (Project/Store/topic/time range). Write fixes
route to `config.modify` / `machine_group.manage` and require user authorization;
showing changes as a diff is recommended.

## 1. No data (no_collection / no_data) — <= 3 commands per round

Checks should follow S1–S4:

- S1 base facts: `logtail-pipeline-config get` (inputs Type/FilePaths, flushers Logstore/Region) + `machine-group list-machines` (lastHeartbeatTime, version; if group unknown, `machine-group list` first).
- S2 quick alarm: `logtail_alarm and project:<project>` (first query includes `alarm_message`; add logstore only if too many).
- S3 minimal fix: change only fields strongly tied to root cause; follow config-diff + index-diff same-batch rule.
- S4 acceptance: 15s x up to 4 short polls on the business logstore; stop on first hit; on repeated empty -> root-cause analysis, do NOT extend the window with more sleep.
- Detailed causes:
  - config recently changed: check `lastModifyTime` on the config (a change may have broken collection).
  - invalid config patterns IC-001/002/003 (see `index-coupling.md` anti-patterns and knowledge base).
  - business-side: source not producing new logs (do not assume "config correct => data exists"); K8s daemonset node drift (target pod moved node -> different collector instance); ContainerFilters not matching.
- You may summarize the evidence as an "impact chain": source -> config -> heartbeat -> processing -> storage, marking the evidence at the failing hop.

Failure route map (from acceptance U-checks): U1/U2/U3 fail -> check API/CRD double-write; U4 fail -> heartbeat playbook; U5 fail while U4 passes -> check input path & filters too strict / source not producing; U6 fail -> processor output fields vs index mapping.

## 2. Heartbeat abnormal (heartbeat_abnormal)

Heartbeat checks should follow this order:

1. Cloud visibility: `machine-group list-machines` contains the target machine?
2. Collector process running? (host-side — this skill guides the user, does not execute)
3. Region consistency: `ilogtail_config.json` region/endpoint matches the project's region.
4. User identity: `ALIYUN_LOGTAIL_USER_ID` or `/etc/ilogtail/users/{aliuid}`.
5. Group identity: `user_defined_id` matches the group's identifier.
6. Version (`binary`, if available; else Lens `logtail_status.version`).
7. Lens `logtail_status` continuously reporting?
8. 3.0 config field differences (`config_server_address`/`data_server_list` vs `config_servers`/`data_servers`).

Decision rules:
- HB-1 `machine-group list-machines` empty -> fix process + region first; do not enter processor diagnosis.
- HB-2 owner UID not in `aliUids` -> fix user_id, re-verify.
- HB-3 `user_defined_id` mismatch -> fix identity file, wait 1-2 min, re-verify.
- HB-4 `<3.0` agent using `>=3.0` fields -> revert to compatible field format.
- Note: one instance can belong to multiple groups (IP + identity); do not conclude "membership is mutually exclusive".

Group-type match (via Lens `logtail_status.machineIdentifyType`):
- `ip`: owner aliuid in `aliUids` and instance ip matches `ip`.
- `userdefined`: owner aliuid in `aliUids` and group identifiers match `user_defined_id`.

## 3. Plan-only mode (no live query requested)

When the user asks for a plan without live queries, you may present the "after (YAML)" change block and a short rationale. No `select *` (explicit fields). `machine-group` commands missing `-m`/`--machine-group` -> ask for `machine_group` first, then give the command with it. Provide an executable skeleton with placeholders when information is incomplete; do not just list what is missing.

## 4. Scope limits

`docker exec` and `kubectl exec` are forbidden. Cloud-only troubleshooting stays on `aliyun sls` + Lens.

If this session already used `install.deploy` (or the user has the same Cloud Assistant/SSH/kubectl access), a **read-only** collector status check is allowed on that same channel: `loongcollectord status`, identity file content, `kubectl get/describe` for DS/controller/CR. No unbounded root shell.

If neither cloud, Lens, nor that read-only channel can resolve the cause, state the single blocking next step and stop.
