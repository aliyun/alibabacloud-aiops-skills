# Error signatures

Each row is a wording a customer can actually see, in SSH client output, in an ECS
console message, or in a Windows logon prompt. `scripts/axes/keypair_login_config/keypair_login_diagnosis.py`
matches `--error-text` against `ERROR_SIGNATURES` in `scripts/axes/keypair_login_config/_constants.py`
after lower-casing, so the customer's text can be pasted verbatim and mixed case.

Match on the string, not on the customer's paraphrase. When nothing matches, the
report says signature matching found nothing and routes on symptom and evidence
instead of inventing a cause.

## Index

| Signature | Source of the wording | Verdict | Fix side |
|---|---|---|---|
| [Unprotected private key file](#unprotected-private-key-file) | local SSH client | key file permissions too open | customer workstation |
| [Permission denied (publickey)](#permission-denied-publickey) | sshd on the instance | key path rejected end to end | cloud and guest |
| [Too many authentication failures](#too-many-authentication-failures) | client or sshd | too many keys offered before the right one | customer workstation |
| [Temporary SSH key](#temporary-ssh-key-cannot-connect) | ECS console | passwordless channel is broken | cloud side |
| [Create key pair failed](#create-key-pair-failed) | ECS console | online reset ran into the agent | cloud and guest |
| [0xd07 account locked out](#0xd07-the-account-is-currently-locked-out) | Windows logon prompt | lockout policy fired | guest and console |
| [No such file or directory: /bin/bash](#no-such-file-or-directory-bin-bash) | sshd or agent failure | base OS damage, not credentials | handoff |
| [Connection timed out / refused](#connection-timed-out-or-refused) | local SSH client | network or service failure before auth | customer and console |

## Unprotected private key file

Seen as `UNPROTECTED PRIVATE KEY FILE`, with `permissions 0644` or `permissions
0664` or `bad permissions` on the neighbouring lines.

The client refuses to use the key at all because the file is readable by others.
Nothing on the cloud side is involved, and no cloud query can fix it. The customer
tightens the file on their own machine: `chmod 600` on the `.pem`, or the `icacls`
equivalent on Windows, then retry. Confirm the key belongs to a key pair that is
actually bound before celebrating; this error commonly hides a second problem.

## Permission denied (publickey)

Public key authentication was rejected. Four causes, checked in this order, cheapest
first:

1. Wrong log-on user name. Public images use `root` or `ecs-user` depending on how
   the instance was created; the key lands in that account's file, not in every
   account.
2. The client never offered the intended key. See
   [Too many authentication failures](#too-many-authentication-failures) and have the
   customer pass `-i` explicitly with `-o IdentitiesOnly=yes`.
3. The console binding is missing, or is present but not effective. Read the key
   pair name from `ecs:DescribeInstances`, then apply the effect rule in
   `keypair-and-credential-guidance.md`.
4. The in-guest layer: daemon options, the home and `.ssh` permission chain, the
   host firewall. Those readings are listed in `guest-evidence-commands.md` and are
   executed by a human, not by this skill.

## Too many authentication failures

The client walked through its stored identities and the server closed the connection
before the intended key was reached. `ssh_msg_disconnect: 2` is the same event seen
from the other side. Pin one identity: `-i` with the intended key plus
`-o IdentitiesOnly=yes`, and clear unrelated identities from the local agent. If the
target is Windows, check whether a lockout fired underneath:
[0xd07](#0xd07-the-account-is-currently-locked-out).

## Temporary SSH key cannot connect

Console wording such as `cannot connect using a temporary ssh key`, alongside
`passwordless logon`. This is the passwordless path failing, which means the
temporary SSH key pair that Cloud Assistant delivers inside the guest never arrived
or never worked.

The important consequence: this channel is independent of the root password and of
`PermitRootLogin`. A locked-down instance can still be reachable through it, and a
failing password logon says nothing about it. Report the Cloud Assistant status
first. Offline or a stale heartbeat is the answer by itself. Online means the agent
is fine and the guest may be wedged, which is a disk IO problem wearing a credential
symptom: see `handoff-boundaries.md`.

## Create key pair failed

An online password reset works by building a temporary key pair and applying it
inside the guest through Cloud Assistant. So this message is an agent execution
failure, not a password failure. Report the agent status and the recent execution
history from `ecs:DescribeInvocations`, then describe the offline reset path. The
offline path restarts the instance, which means a snapshot first, which means a
customer-executed change with a service-interruption window.

## 0xd07 the account is currently locked out

Windows locked the account after repeated failed logon attempts. On an instance with
a public address on 3389, the usual cause is internet brute-force traffic, not the
customer's own typing. Two facts to say out loud: a passwordless logon attempt types
no password, so a lockout can look impossible to the customer while somebody else was
guessing one; and `net accounts` shows the threshold, the lockout duration and the
observation window.

Release it through one successful VNC logon or the console send-command path, both
customer-executed. Then point at tightening 3389 to the customer's own source address
in the security group. Editing that rule is outside this skill: `handoff-boundaries.md`.

## No such file or directory: /bin/bash

Missing base files, or `sshd` failing because the default shell is gone, or every
command failing with `No such file or directory`. This is not a credential problem.
More credential work is wasted effort, so stop this branch, take a snapshot first,
and hand off to `alibabacloud-ecs-linux-os-troubleshooting` or an offline disk-repair
engineer. `keypair_login_diagnosis.py` reports this as a handoff, not a fix.

## Connection timed out or refused

The network path or the listening service failed before any credential was exchanged.
`Connection refused` usually means nothing is listening on 22 inside the guest; a
timeout usually means the packet never came back. Confirm the instance is `Running`
from `ecs:DescribeInstances`, have the customer test reachability of port 22 and
their own egress, and read the security group rules in the console. This skill neither
reads nor writes security group rules.

Note on `connection refused`: the transport layer treats that marker as retryable in
API responses, which is unrelated to the customer-facing SSH message above.
