# Machine Group, Identity & Heartbeat

Executed via `aliyun sls machine-group create/get/list/update/delete`, `machine-group list-machines` (see `cli-contracts.yaml`).

## 1. Machine group types

- **IP machine group** (`machine-identify-type: ip`): defined by an IP list.
- **User-defined identity group** (`machine-identify-type: userdefined`): defined by identifiers written on the host:
  - Linux: `/etc/ilogtail/user_defined_id`
  - Windows: `C:\LogtailData\user_defined_id`
- After changing `user_defined_id`, it takes effect within ~1 minute (or on collector restart).
- Constraints: a group cannot mix Linux and Windows hosts; a host may carry multiple identifiers (newline-separated).
- Ownership is many-to-many: one collector instance can belong to multiple groups (IP + identity together). Do NOT use "group membership is mutually exclusive" as a conclusion.

## 1.1 Before any group write

Creating, updating or binding a machine group is R2 and requires user authorization.
Build the target object; showing the changes as a diff is recommended.
`scripts/loongcollector/normalize_diff.py --kind auto` compares the current and target
objects. Run dry-run before the actual write.

## 2. User identity (ALIUID)

- The collector decides which primary account a machine belongs to via the **primary account UserId** (ALIUID).
- Provided via env `ALIYUN_LOGTAIL_USER_ID` (takes priority) or files `/etc/ilogtail/users/{accountId}` (Linux) / `C:\LogtailData\users\{accountId}` (Windows).

## 3. Heartbeat

- Config is only delivered and collection only runs when heartbeat is OK. An abnormal heartbeat should be triaged first.
- `machine-group list-machines --project <p> --machine-group <g>` returns `machines[]` with identity, `lastHeartbeatTime`, and `binary` (the collector version, e.g. `3.3.4`) — this is the primary version source (see version discovery).
- ACK / self-k8s: reuse official `k8s-group-${cluster_id}`; do not create an extra IP group for DaemonSet collectors.
- Host-side heartbeat: cloud-only tasks describe checks in prose. `install.deploy` may re-use Cloud Assistant/SSH to read `loongcollectord status` and `/etc/ilogtail/user_defined_id` (read-only).
- `ilogtail_config.json` decides the report endpoint; wrong region => no heartbeat. Field names differ across 3.0:
  - `<3.0`: `config_server_address` + `data_server_list`.
  - `>=3.0`: `config_servers` + `data_servers`. A `<3.0` agent cannot read `>=3.0` fields (breaks heartbeat).

## 4. Create / manage examples

Create a user-defined identity group:
```bash
aliyun sls machine-group create \
  --project <p> --machine-group <g> \
  --machine-identify-type userdefined \
  --machine-list '["my-app-id-1","my-app-id-2"]' \
  --region <r> --format json
```

`--machine-list` accepts a JSON array of identifiers. Verify the stored `machineList`
with `machine-group get`, or list configured members with `machine-group list-members`.

For member-only changes, use `machine-group add-members` or `machine-group remove-members`
with `--project`, `--machine-group` and `--machine-list '<JSON array>'`. They preserve
the group's other configuration and skip the write when membership is unchanged.
These commands read the current group and update it; they are not server-side atomic
membership operations. Use `machine-group update` for full configuration replacement,
preserving `machine-identify-type`, `group-attribute` and `group-type`.

Bind / unbind a config: `logtail-pipeline-config apply-to-machine-group` / `logtail-pipeline-config remove-from-machine-group` (R2 / R3). Read back with `machine-group get-applied-configs` (group -> configs) and `logtail-pipeline-config get-applied-machine-groups` (config -> groups).

## 5. Heartbeat decision rules (also see troubleshooting.md)

- HB-1 `machine-group list-machines` empty -> fix process + region first; do not enter processor diagnosis.
- HB-2 owner UID not in machine's `aliUids` -> fix user_id, re-verify.
- HB-3 `user_defined_id` mismatch with group identity -> fix identity file, wait 1-2 min, re-verify.
- HB-4 `<3.0` agent using `>=3.0` config fields -> revert to compatible field format.
