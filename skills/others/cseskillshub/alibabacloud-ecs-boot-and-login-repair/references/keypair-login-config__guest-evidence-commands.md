# In-guest evidence commands

## Execution status: guided by default, dispatchable on confirmation

Two things are true at once, and this package keeps them separate.

The commands below are published as a list a human can run. That is the default
path, and it is the path to prefer while the login-diagnostic command list is
still awaiting merge into the approved inspection whitelist — that approval is an
open sign-off item, tracked with the effect-condition question in
`keypair-and-credential-guidance.md`.

There is also a real execution path: `ecs:run-command` is declared in
`related_apis.yaml` and granted in `ram-policies.md`, so exactly one published
reading can be dispatched as a class B call.

```bash
python3 scripts/axes/keypair_login_config/keypair_login_diagnosis.py --instance-id i-2ze8example --region-id cn-beijing \
  --entry local-ssh --symptom keypair-not-effective \
  --run-inspection "sshd -T" --confirm-inspection "sshd -T"
```

That path is narrow by construction:

* the command must be one of the strings in the two tables below, which are the
  members of `EXECUTABLE_INSPECTION_COMMANDS` in `scripts/axes/keypair_login_config/_constants.py`;
* the run must repeat that exact command as its own confirmation, so
  `--confirm-inspection` has to carry the same string as `--run-inspection` —
  anything else ends in `unconfirmed` and nothing is dispatched;
* one command per call: a second reading needs a second announced and confirmed
  call, and a confirmation is never carried over from an earlier run;
* the result is read back with `ecs:DescribeInvocations`, masked by
  `mask_secrets()`, truncated to `GUEST_OUTPUT_MAX_CHARS`, and the gated call is
  attempted once rather than retried;
* anything outside the two tables is refused and degraded to a plain suggestion
  for the customer to weigh.

The report prints what actually happened under `GUEST INSPECTION` and
`CHANNEL STATE ON THIS RUN`, so no reader has to guess whether the guest was
touched.

## The per-command gate

Permission model B in this tier: nothing runs inside the guest without, for each
single command, a prior notice and an explicit confirmation.

1. Announce the command: what it reads, its scope, that it changes nothing, and
   how to recover if anything is unexpected.
2. Get confirmation for that command only. Approval for one never covers the next.
3. Run it, read the output, report it.

From `GUEST_READING_RULES`: never edit sshd configuration, never restart a
service, never clear `authorized_keys`, never change a lockout policy from this
skill — no confirmation makes those dispatchable; they are human, approved changes
with their own snapshot gate.

## Linux readings

Source of truth: `GUEST_READINGS_LINUX` in `scripts/axes/keypair_login_config/_constants.py`.

| Command | What the reading proves |
|---|---|
| `sshd -T` | the effective configuration the daemon is actually using |
| `cat /etc/ssh/sshd_config` | the file behind that configuration, includes and all |
| `sshd -T \| grep -i -E 'pubkeyauthentication\|passwordauthentication\|permitrootlogin\|authorizedkeysfile'` | the four options that decide key logon, password logon and where keys are read |
| `stat -c '%n %a %U:%G' ~ ~/.ssh ~/.ssh/authorized_keys` | the home directory and `.ssh` permission chain, the classic refusal cause |
| `systemctl status sshd --no-pager` | whether the service runs and when it last started |
| `iptables -L -n` | host firewall rules that block 22 even when the cloud rule is open |
| `firewall-cmd --list-all` | the firewalld equivalent of the same check |
| `last -n 20` | successful logons around the incident |
| `lastb -n 20` | failed logon attempts around the incident, and their source |
| `journalctl -u sshd --no-pager -n 100` | the server-side reason for each rejected attempt |

`sshd -T` first. It is the only reading that shows what the running daemon believes,
which is not the same as what the config file says when an `Include` or a drop-in
overrides it. Then the permission chain, which resolves most "the key is in the file
but logon still fails" cases without any further command.

## Windows readings

Source of truth: `GUEST_READINGS_WINDOWS` in `scripts/axes/keypair_login_config/_constants.py`.

| Command | What the reading proves |
|---|---|
| `query user` | current sessions and their state, in practice against the two-session ceiling |
| `net accounts` | the lockout threshold, its duration and the observation window |
| `net localgroup administrators` | which accounts may log on as administrators |
| `Get-Volume \| Format-Table` | free space per volume, a prerequisite for any agent work |

A dispatch on Windows uses the script type the Cloud Assistant expects, chosen
from the reported operating system unless the run states it: `--inspection-shell`
takes `auto`, `shell`, `bat` or `powershell`.

## Reading the result, not just the exit code

A denied permission on one command is an answer, not a failure to retry. An empty
`authorized_keys`, a `PubkeyAuthentication no`, a `0477` home directory, and a
`lastb` full of foreign source addresses are four different conclusions that all
look like "logon fails".

A dispatched reading that comes back `still running`, `unread` or `failed` is also
an answer: it says the in-guest fact is still missing, and the report stays
`DEGRADED` rather than claiming a reading that never arrived.

Anything that shows base files missing, or commands failing to start at all, ends the
credential branch: `error-signatures.md` and `handoff-boundaries.md`.

## If a customer offers to paste output

Accept pasted output from the customer; it is their machine and their choice. Never
ask for a private key, never ask them to paste command output that contains one, and
never write phone numbers, passwords or key material into a skill artifact. The report
scrubs credential-shaped values on the way out via `mask_secrets()` in
`scripts/axes/keypair_login_config/_cli.py`.
