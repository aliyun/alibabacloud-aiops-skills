# Self-hosted Linux install

Same official script as ECS: [LoongCollector Linux installation](https://help.aliyun.com/zh/sls/loongcollector-installation-linux).
Workbench cannot reach non-ECS hosts. Use a user-configured SSH alias.

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
- **First channel check, before any SLS create/apply or install confirmation:** run `ssh <alias> -- true` once. If SSH is unusable because the alias is missing, name resolution fails, or authentication fails, use the fixed Missing SSH subject from `SKILL.md` and end with `[AWAITING: SSH]`. Do **not** ask the self-host install approval question after a failed probe. Do **not** create/edit `~/.ssh/config`, `/etc/hosts`, or rewrite the alias to `127.0.0.1` / localhost. Do not create Project/Logstore/group/config, do not fall back to OOS, and do not invent a host. A prompt-supplied alias that does not work is still missing SSH. If the user explicitly ends the task, stop.
- No unbounded root shell; only the rendered install / identity / status commands.
- Shape matches Workbench: one command, inspect exit code, then `sudo /etc/init.d/loongcollectord status`.

Render: `python3 scripts/render_loongcollector_install_cmd.py --environment self_host --region <r> --account-relation cross --user-id <aliuid> --user-defined-id <id>`.

## Command selection

Use the same install/upgrade selection rules as ECS. Self-hosted systems almost always need:

```bash
sudo touch /etc/ilogtail/users/<aliuid>
printf '<id>\n' | sudo tee /etc/ilogtail/user_defined_id >/dev/null
./loongcollector.sh install ${region}-internet   # or intranet if the host can reach the region endpoint
```

Upgrade: `./loongcollector.sh upgrade` only.

## Stage gate then onboard

`loongcollector is running` → create/reuse Project, Logstore, Index, **userdefined** machine group, `input_file` (or stated Docker scenario), bind, U1–U6, `get-logs-v2`.

## HITL

Use the fixed self-host install approval subject from `SKILL.md`, followed by `[AWAITING: INSTALL_CONFIRMATION]`.
Then the standard create-and-bind question.
