# Key pair and credential guidance

Console guidance for the credential changes this skill never performs. Every step
here is executed by a human who has been told what it changes and how to recover.

## What this skill calls, and what it only explains

The five granted reads, the two gated calls and the refused actions are listed in
`ram-policies.md`. The practical rule: reads answer "what is true now"; a gated call
does one narrow thing, inside the guest or on one disk, only on that call's own
confirmation; and everything that changes a credential is a customer-executed console
step, described below, for which this package deliberately has no grant.

## Before any of it: the snapshot gate

`SNAPSHOT_FIRST_GATE` in `scripts/axes/keypair_login_config/_constants.py` states it in one line: before any
step that needs a restart, an offline reset, or a detached repair disk, a snapshot of
the system disk is created first and allowed to complete. A pure evidence review
needs none. Snapshots are billable storage, so note the snapshot id and delete it when
the change window closes; a snapshot is not a substitute for a verified backup on a
data-critical volume. This skill can create that snapshot itself, but only on a
confirmation naming that exact disk, and that confirmation is never permission to
restart: the gate is the same either way.

## Key pair naming and lifecycle facts

From `KEY_PAIR_NAMING_RULES`:

* 2 to 128 characters, starting with a letter or a Chinese character, using letters,
  digits, periods, underscores and hyphens;
* the private key file is offered for download exactly once, at create or import time;
* the platform keeps no copy of a private key, so a lost private key cannot be
  recovered. The recovery path is a new key pair, never a search;
* one instance carries one key pair binding at a time.

Region scope matters more than people expect: a key pair is a regional resource, so a
key pair created in one region cannot be bound to an instance in another. The console
region selector is the first thing to check when the list "is missing" a key pair.

## Create, import, bind, replace, unbind

Console entry: `ECS console > Storage & Images > Key Pairs`, region selected first,
and `ECS console > Instances > target instance > More > Password/Key Pair` for the
binding itself.

1. Create a key pair, or import an existing public key. On create, download the
   `.pem` immediately; the dialog will not offer it again.
2. Bind it to the target instance. Binding replaces the previous key pair rather than
   adding to it.
3. Restart the instance from the console so the binding takes effect.
4. Tighten the local file (`chmod 600`), then log on with the account that matches the
   image (`root` or `ecs-user`).

**Effect condition.** `KEY_PAIR_EFFECT_RULE` is the operative wording used in every
report: treat a key pair bound or replaced on a running instance as effective only
after the instance has been restarted from the ECS console, and ask whether that
restart happened before concluding anything else. The ticket corpus contains two
contradictory statements on this point (a restart is required, versus a replacement
taking effect immediately). Both cannot be unconditional, so this skill carries one
wording and it is flagged as pending sign-off rather than quoting either sentence.

**If the workload cannot be restarted now** (`NO_RESTART_ALTERNATIVE`): log on by
another working path, generate a key pair locally, and append the public key line to
the log-on account's `authorized_keys` file. That gives key logon without waiting for
the platform injection step. It is a guest file edit, so it is a human, approved
change.

## Passwordless logon for several users on one Linux instance

The console binding writes the public key of the bound key pair into one log-on
account. Multi-user key logon is therefore an in-guest file arrangement, not a
console feature, and no console list shows it.

1. Each person generates their own key pair locally and shares only the public half.
   Nobody sends a private key to anyone, in any channel.
2. An account that can already log on appends each public key as one complete line to
   that user's `~/.ssh/authorized_keys`.
3. Permissions on the chain decide whether it works: the user's home directory not
   group-writable, `~/.ssh` at `700`, `authorized_keys` at `600`, all owned by that
   user. This is the most common cause of "the key is there but logon still fails".
   The `stat -c` reading in `guest-evidence-commands.md` proves it.
4. A new user needs the account created first, plus a shell. `passwd -S` shows
   whether an account can authenticate at all.

Adding users is a guest change, so it is executed by a human after per-command
confirmation, and it is not on the approved inspection list:
`guest-evidence-commands.md`.

## Password logon and resets

From `CREDENTIAL_FACTS`:

* Instance passwords are never recorded and never queryable. The recovery path is a
  reset, never a lookup.
* An **online** reset runs inside the guest through Cloud Assistant and needs no
  restart. It is the step that fails with `create key pair failed`
  (`error-signatures.md`).
* An **offline** reset needs a console restart, so it needs the snapshot gate first.
* When a key pair is bound, password logon may stay refused even after a successful
  reset. Use the key path, or unbind the key pair, rather than resetting twice.
* Public images support console credential management. Community images flagged as
  *Others Linux* generally do not, after an image swap on an existing instance.

## After an operating system or image change

Credentials that stopped working at the moment of an image change are usually not a
credential fault. The new image has a different log-on account, a different
`authorized_keys` location, and possibly no console credential support at all
(*Others Linux*). Establish the sequence: what changed, when, and whether the old
path ever worked on the new system. Then either bind a key pair through the console
for the new account, or use the no-restart `authorized_keys` path. Where the image is
unsupported for console credential management, say so plainly and hand the customer to
the in-guest path instead of retrying console resets.

## Windows: sessions and lockouts

From `WINDOWS_LOGON_FACTS`: two concurrent Remote Desktop sessions by default, and the
same user name reconnects into one session instead of opening a second one. More
concurrent users need the Remote Desktop Session Host role plus RDS client access
licences, and a 120-day trial is the only vendor-supported path. Third-party
terminal-services activation scripts are an unlicensed path and this skill does not
help with them. Lockout behaviour, and the `0xd07` wording, is in
`error-signatures.md`.

## Never

* Never let a private key be pasted into a conversation, a ticket, or a log. If the
  customer already did, treat that key as compromised and replace it.
* Never edit `sshd_config`, never restart a service, never clear `authorized_keys`,
  never change a lockout policy from here.
* Never claim a key pair "should" work because it is listed. Ask about the restart.
