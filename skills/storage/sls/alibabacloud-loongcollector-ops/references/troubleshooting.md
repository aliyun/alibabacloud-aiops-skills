# Troubleshooting Playbooks (no-data, heartbeat)

> Source: `loongcollector-oncall/knowledge/troubleshooting/user/collection-playbooks.md`, `self-monitoring-metrics.md`. Covers no-data and heartbeat only. Delay, duplicate, parse-failure, container-filter, and data-loss are out of scope.

## 0. Fixed chain

`classify -> heartbeat & version -> config & binding -> alarm/metric -> business data -> minimal fix -> re-verify`

- Cloud visibility and collector-side evidence corroborate each other; neither substitutes the other.
- Resource-not-found errors never terminate the remaining independent read-only checks; record attempted command/error and continue. Permission failures still hard-stop.
- Every conclusion carries these exact field-complete evidence lines (canonical here; `SKILL.md` §10 points to this file). Use `N/A`/`unknown` and `Resource not found` rather than omitting unavailable fields:

  `[Heartbeat Evidence] [Evidence: heartbeat] lastHeartbeatTime: <value|N/A> | version: <value|N/A> | status: <online|offline|unknown> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`

  `[Alarm Evidence] [Evidence: alarm] alarm_type: <hit:type|miss|unknown> | alarm_message: <value|N/A> | query_result: <row_count|N/A> | time_range: <from-to> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`

  `[Collection Evidence] [Evidence: collection] data_count: <value|N/A> | time_range: <from-to> | status: <new_data|no_data|unknown> | reason: <explicit reason> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`

  `[Binding Evidence] [Evidence: binding] config_name: <value|N/A> | machine_group: <value|N/A> | status: <bound|unbound|unknown> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`

  `[Pipeline Evidence] [Evidence: pipeline] topic: <value|N/A> | data_count: <value|N/A> | time_range: <from-to> | progress: <Complete|Incomplete|unknown> | attempted: <command> | error: <code|none> | resource_status: <present|Resource not found>`
- Every troubleshooting output includes: symptom class, root-cause evidence, minimal fix, callback location, Lens context (project/logstore/topic/time-range). Write fixes route back to `config.modify` / `machine_group.manage` (diff + approval).

## 1. No data (no_collection / no_data) — <= 3 commands per round

- S1 base facts: `get-logtail-pipeline-config` (inputs Type/FilePaths, flushers Logstore/Region) + `list-machines` (lastHeartbeatTime, version; if group unknown, `list-machine-group` first).
- S2 quick alarm: `logtail_alarm and project:<project>` (first query includes `alarm_message`; add logstore only if too many).
- S3 minimal fix: change only fields strongly tied to root cause; follow config-diff + index-diff same-batch rule.
- S4 acceptance: 15s x up to 4 short polls on the business logstore; stop on first hit; on repeated empty -> root-cause analysis, do NOT extend the window with more sleep.
- Detailed causes:
  - config recently changed: check `lastModifyTime` on the config (a change may have broken collection).
  - invalid config patterns IC-001/002/003 (see `index-coupling.md` anti-patterns and knowledge base).
  - business-side: source not producing new logs (do not assume "config correct => data exists"); K8s daemonset node drift (target pod moved node -> different collector instance); ContainerFilters not matching.
- Output an "impact chain": source -> config -> heartbeat -> processing -> storage, marking the evidence at the failing hop.

Failure route map (from acceptance U-checks): U1/U2/U3 fail -> check API/CRD double-write; U4 fail -> heartbeat playbook; U5 fail while U4 passes -> check input path & filters too strict / source not producing; U6 fail -> processor output fields vs index mapping.

## 2. Heartbeat abnormal (heartbeat_abnormal)

Fixed check order:
1. Cloud visibility: `list-machines` contains the target machine?
2. Collector process running? (host-side — this skill guides the user, does not execute)
3. Region consistency: `ilogtail_config.json` region/endpoint matches the project's region.
4. User identity: `ALIYUN_LOGTAIL_USER_ID` or `/etc/ilogtail/users/{aliuid}`.
5. Group identity: `user_defined_id` matches the group's identifier.
6. Version (`binary`, if available; else Lens `logtail_status.version`).
7. Lens `logtail_status` continuously reporting?
8. 3.0 config field differences (`config_server_address`/`data_server_list` vs `config_servers`/`data_servers`).

Decision rules:
- HB-1 `list-machines` empty -> fix process + region first; do not enter processor diagnosis.
- HB-2 owner UID not in `aliUids` -> fix user_id, re-verify.
- HB-3 `user_defined_id` mismatch -> fix identity file, wait 1-2 min, re-verify.
- HB-4 `<3.0` agent using `>=3.0` fields -> revert to compatible field format.
- Note: one instance can belong to multiple groups (IP + identity); do not conclude "membership is mutually exclusive".

Group-type match (via Lens `logtail_status.machineIdentifyType`):
- `ip`: owner aliuid in `aliUids` and instance ip matches `ip`.
- `userdefined`: owner aliuid in `aliUids` and group identifiers match `user_defined_id`.

## 3. Plan-only mode (no live query requested)

When the user asks for a plan without live queries: output the "after (YAML)" change block first, then a short rationale. No `select *` (explicit fields). `machine-group` commands missing `-m`/`--machine-group` -> ask for `machine_group` first, then give the command with it. Provide an executable skeleton with placeholders when information is incomplete; do not just list what is missing.

## 4. Scope limits

No SSH/kubectl/docker exec. Host-side checks are described to the user in prose — what to verify, not shell commands to paste. If neither cloud resources nor Lens can resolve the root cause and only host evidence remains, state that host-side collector-agent inspection is required (controlled host access, out of scope), and stop with the single blocking next step.
