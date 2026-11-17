# Guest evidence commands

## Why this file exists

No cloud API can report what a running instance is actually doing: which port the
SSH daemon really serves, whether password login is enabled inside the guest, or
whether a host firewall drops the packet. The instance metadata says the instance
is healthy while all three are wrong. Cloud Assistant is therefore used to run a
command **inside** the instance - which is why this skill holds one write-class
action (`ecs:run-command`, dispatched as the API operation `RunCommand`) and why the
rules on this page are strict.

## The confirmation gate

Before any command on this page is delivered, all four of these must happen, in
this order, inside the conversation:

1. Tell the user **which single command** will run, verbatim.
2. Tell them **what it reads** and which phase question it answers.
3. Tell them **it changes nothing** on the instance, and that output travels back
   through Cloud Assistant.
4. Get their agreement, then run with `--guest-command <key>
   --guest-confirmed-by <name>`.

Without `--guest-confirmed-by` the script refuses to execute, prints the proposed
command as a human step, and marks the run `STATUS: DEGRADED`. This is not a
warning to talk around: it is the boundary of the skill.

One command per call. Confirmation applies to that command only - the next command
needs a fresh round.

## Allowed commands

The table is the complete whitelist, mirrored by `GUEST_COMMAND_WHITELIST` in
[`../scripts/areas/ssh_connection/_constants.py`](../scripts/areas/ssh_connection/_constants.py).

| Key | Command | Category | What it answers |
| --- | --- | --- | --- |
| `listening-sockets` | `ss -tlnp` | port | Which TCP ports have a listener, and which process owns them |
| `sshd-config` | `cat /etc/ssh/sshd_config` | sshd | `Port`, `PasswordAuthentication`, `PubkeyAuthentication`, `PermitRootLogin`, keepalive |
| `ssh-dir-listing` | `ls -l /etc/ssh /etc/ssh/sshd_config.d` | sshd | Whether drop-in files exist, plus owners and modes |
| `authorized-keys-mode` | `ls -ld /root/.ssh /root/.ssh/authorized_keys` | file | Whether key login can be ignored because of the path mode |
| `login-binary-presence` | `ls -l /bin/bash /usr/sbin/sshd /usr/lib64/linux-x86-64.so.2` | file | Whether a clean-up removed a file the login path needs |
| `firewalld-state` | `firewall-cmd --state` | firewall | Is firewalld running at all |
| `firewalld-ports` | `firewall-cmd --list-all` | firewall | Which services and ports firewalld allows |
| `ufw-status` | `ufw status` | firewall | Ubuntu inbound rule state |
| `nftables-ruleset` | `nft list ruleset` | firewall | Active nftables ruleset covering the SSH port |
| `iptables-rules` | `iptables -S` | firewall | Active iptables rules covering the SSH port |

Each command is delivered as a single literal string with `Type=RunShellScript`.
The literal itself is re-checked against the mutating-fragment guard before
delivery, so a mistake in the table cannot turn into a mutation on an instance.

## Refusal rule

A command that is not in the table above is **never** executed. The script refuses
it, and the skill answers with the command as a written step for the customer to run
in a session they control:

> That command is outside the evidence set this skill is allowed to deliver, so I
> will not run it. Run `<command>` yourself over a VNC or SSH session and paste the
> output back; I will interpret it.

## Deliberately excluded, with the reason

| Excluded | Reason |
| --- | --- |
| `systemctl status sshd`, `service sshd status` | `systemctl` is blocked by the mutating-fragment guard in this batch. Service liveness is derived from `ss -tlnp` instead: a listening socket owned by `sshd` is stronger evidence of a live daemon than a status line. |
| `journalctl -k \| grep -i oom`, `dmesg` | Not covered by the write-class contract of this tier, which authorises SSH daemon, port and firewall inspection only. The customer runs it and pastes the output. |
| `atop` log readers, `top`, `ps aux --sort` | Same reason: process history and live load are outside the authorised categories. |
| `sshd -T` | Prints effective configuration including privileged host key material; `cat` of the plain file plus interpretation keeps the same conclusions without that surface. |
| `hostkey`, `ssh-keygen`, anything writing a file, anything with `sed -i`, redirection, pipes or command chaining | Mutating, therefore out of scope by definition. |
| Any Windows in-guest command | The authorised delivery path here is Linux shell scripts. Windows conclusions stay at the metadata level and are labelled low confidence. |

## Output handling

`ecs:DescribeInvocations` returns guest output base64 encoded. It is decoded,
masked for anything resembling a credential, length-capped, and quoted into the
report as verbatim guest data with its exit code. Empty output is reported as a
gap, never filled in with an assumed value: an absent tool (`ss` without `iproute2`,
`firewall-cmd` without firewalld) is exactly as informative as a rule.
