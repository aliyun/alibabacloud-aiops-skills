# Machine Group, Identity & Heartbeat

> Source: `loongcollector-oncall/knowledge/base/loongcollector/machine-group-and-heartbeat.md`. Executed via `aliyun sls create/get/list/update/delete-machine-group`, `list-machines` (see `cli-contracts.yaml`).

## 1. Machine group types

- **IP machine group** (`machine-identify-type: ip`): defined by an IP list.
- **User-defined identity group** (`machine-identify-type: userdefined`): defined by identifiers written on the host:
  - Linux: `/etc/ilogtail/user_defined_id`
  - Windows: `C:\LogtailData\user_defined_id`
- After changing `user_defined_id`, it takes effect within ~1 minute (or on collector restart).
- Constraints: a group cannot mix Linux and Windows hosts; a host may carry multiple identifiers (newline-separated).
- Ownership is many-to-many: one collector instance can belong to multiple groups (IP + identity together). Do NOT use "group membership is mutually exclusive" as a conclusion.

## 1.1 Before any group write

Creating, updating, or binding a machine group is R2: build the target object, run `scripts/normalize_diff.py --kind auto` on current vs target, show that normalized diff, and get explicit confirmation before the dry-run and the write. A group written without an executed normalize_diff result is a gate failure, the same as for config/index changes.

## 2. User identity (ALIUID)

- The collector decides which primary account a machine belongs to via the **primary account UserId** (ALIUID).
- Provided via env `ALIYUN_LOGTAIL_USER_ID` (takes priority) or files `/etc/ilogtail/users/{accountId}` (Linux) / `C:\LogtailData\users\{accountId}` (Windows).

## 3. Heartbeat

- Config is only delivered and collection only runs when heartbeat is OK. Heartbeat-not-OK must be triaged first.
- `list-machines --project <p> --machine-group <g>` returns `machines[]` with identity, `lastHeartbeatTime`, and `binary` (the collector version, e.g. `3.3.4`) — this is the primary version source (see version discovery).
- General host-side heartbeat checks: describe them to the user in prose — collector process running, `user_defined_id` matching the group identity, ALIUID matching the account, reporting region correct. Do not emit host shell commands; this skill cannot see the host layout and never executes there.
- `ilogtail_config.json` decides the report endpoint; wrong region => no heartbeat. Field names differ across 3.0:
  - `<3.0`: `config_server_address` + `data_server_list`.
  - `>=3.0`: `config_servers` + `data_servers`. A `<3.0` agent cannot read `>=3.0` fields (breaks heartbeat).

## 4. Create / manage examples

Create a user-defined identity group:
```bash
aliyun sls create-machine-group \
  --project <p> --group-name <g> \
  --machine-identify-type userdefined \
  --machine-list my-app-id-1 my-app-id-2 \
  --region <r> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops/<session-id>
```

> **`--machine-list` takes space-separated values, NOT a JSON array.** Passing
> `'["id"]'` gets double-encoded by the CLI (stored as the literal string `["id"]`)
> and the collector will never match the group. Verify with `get-machine-group`:
> `machineList` must show clean values like `["my-app-id-1"]`, not `["[\"my-app-id-1\"]"]`.

Incremental member add/remove (CLI-003 gap: no `update-machine-group-machine` subcommand):
1. `get-machine-group --project <p> --machine-group <g>` (snapshot; re-read just before write).
2. Merge the new identifiers/IPs into `machine-list`.
3. `update-machine-group` with the full body (overwrite). Preserve `machine-identify-type`, `group-attribute`, `group-type`.

Bind / unbind a config: `apply-config-to-machine-group` / `remove-config-from-machine-group` (R2 / R3). Read back with `get-applied-configs` (group -> configs) and `get-applied-machine-groups` (config -> groups).

## 5. Heartbeat decision rules (also see troubleshooting.md)

- HB-1 `list-machines` empty -> fix process + region first; do not enter processor diagnosis.
- HB-2 owner UID not in machine's `aliUids` -> fix user_id, re-verify.
- HB-3 `user_defined_id` mismatch with group identity -> fix identity file, wait 1-2 min, re-verify.
- HB-4 `<3.0` agent using `>=3.0` config fields -> revert to compatible field format.
