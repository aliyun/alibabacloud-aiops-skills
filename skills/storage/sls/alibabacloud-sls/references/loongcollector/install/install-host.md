# Self-hosted Linux install

Same official script as ECS: [LoongCollector Linux installation](https://help.aliyun.com/zh/sls/loongcollector-installation-linux).
Use a user-configured SSH alias for self-hosted Linux.

## Required inputs

- `region`, SSH alias or reachable host
- usually cross-account: `user_id` (ALIUID) + `user_defined_id`
- collection path before onboarding

## Channel

```bash
ssh <alias> -- <literal-command>
```

Rules:

- Confirm the host fingerprint on first connect. Never `StrictHostKeyChecking=no`.
- Never accept or print an SSH private key in chat.
- **First channel check, before any SLS create/apply or install confirmation:** run `ssh <alias> -- true` once. If SSH is unusable because the alias is missing, name resolution fails, or authentication fails, ask the user for a working host/SSH alias and stop installation until it is available. Do **not** create/edit `~/.ssh/config`, `/etc/hosts`, or rewrite the alias to `127.0.0.1` / localhost. Do not create Project/Logstore/group/config, do not fall back to OOS, and do not invent a host. A prompt-supplied alias that does not work is still missing SSH. If the user explicitly ends the task, stop.
- No unbounded root shell; only the rendered install / identity / status commands.
- Execute one command, inspect its exit code, then `sudo /etc/init.d/loongcollectord status`.

Render: `python3 scripts/loongcollector/render_loongcollector_install_cmd.py --environment self_host --region <r> --account-relation cross --user-id <aliuid> --user-defined-id <id>`.

## Command selection

Use the same install/upgrade selection rules as ECS. Self-hosted systems almost always need:

```bash
sudo touch /etc/ilogtail/users/<aliuid>
printf '%s\n' '<id>' | sudo tee /etc/ilogtail/user_defined_id >/dev/null
./loongcollector.sh install ${region}-internet   # or intranet if the host can reach the region endpoint
```

Upgrade: `./loongcollector.sh upgrade` only.

## Installation acceptance and optional onboarding

`loongcollector is running` completes an installation-only request. When collection was requested, continue to create/reuse Project, Logstore, Index, a **userdefined** machine group and `input_file` (or the stated Docker scenario), then bind and perform U1–U6 and `query`.

## Authorization

Installation and collection changes require user authorization. Render installation commands with `render_loongcollector_install_cmd.py`; showing planned changes as a diff is recommended.
Only perform collection changes when they are within the user's requested and authorized scope.
