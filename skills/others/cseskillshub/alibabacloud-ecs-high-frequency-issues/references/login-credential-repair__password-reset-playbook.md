# Password reset playbook (branches LC3 / LC7 / LC8)

Covers "I reset the password and still cannot log in", "I forgot the
password", "the reset failed or timed out", and the Windows built-in
administrator variants. Guided steps only; the skill never performs a reset.

## 1. Two facts to state first

- **A logon password can never be viewed, only reset.** There is no
  "retrieve my password" capability on the platform side, so no amount of
  escalation produces one. The answer to "where can I see the password" is
  always: the console reset, which produces a new value the customer stores
  themselves.
- **A successful reset is not the same as a successful logon.** In this tier's
  evidence the two were repeatedly conflated, which sent customers down
  in-guest investigation paths while the actual blocker was the client side.
  After every reset, walk section 6 before believing anything else.

Default logon user by OS family, because the second-most common cause is the
username, not the password:

| OS family | User to try | Notes from evidence |
| --- | --- | --- |
| Linux | `root`, or `ecs-user` | Many images forbid direct root logon; some marketplace images require `cloud-user` and say so in their own refusal message |
| Windows | `administrator` | Beware the client filling in `<local-computer-name>\administrator` instead |

## 2. Which reset path applies

The report's cloud reads decide, not the customer's memory of what they
clicked.

| Evidence | Path | Why |
| --- | --- | --- |
| Agent online, instance Running | Console **online** reset | The online route is delivered through the guest agent; with the agent online it is the fast, no-restart option |
| Agent offline or status unknown | Verify in a console session, then plan the **offline** reset | Retrying the online reset against an offline agent produces exactly the "task shows success, password unchanged" trap |
| Instance Stopped | Offline reset, then start it | One restart is required for the change to apply either way |
| Online reset reported `instruction execution failure` / timeout | Offline reset after snapshot | The delivery channel, not the password policy, is failing |
| Disk-full wording during the reset | Hand off to disk capacity first | The guest cannot write the change; see [handoff-scripts.md](login-credential-repair__handoff-scripts.md) |
| "The key pair has been removed", or a key-pair-bound Linux instance | Resolve the key-pair question first | A bound key pair can make the guest refuse password logon even when the password is right; see section 7 |

The value the reads add is turning "the agent is probably broken" (asserted in
this tier's tickets, never measured) into a yes/no field.

## 3. Console navigation for the reset

Text guidance only; this skill never generates console links:

```
ECS console > Instances & Images > Instances   (select the region that owns the instance first)
  > instance row > All Operations > Instance Settings > Reset Instance Password
```

The region selector is a real stumbling block: with the wrong region the
instance is simply not in the list and the customer concludes the tool is
broken. Echo the region back and ask them to confirm it against the instance
detail page.

Online versus offline is a choice inside that wizard. Offline means "requires
one restart to take effect".

## 4. Before any write: snapshot first

Mandatory ordering for every state-changing step in this playbook (password
write, in-guest configuration edit, lockout policy write, restart):

1. Create a manual snapshot that **covers the system disk**. A data-disk-only
   snapshot does not protect the account database or the SSH configuration; in
   this tier's evidence an engineer had to go back and ask for the system-disk
   snapshot a second time. For Windows instances where the policy is host
   local, snapshot every block-storage disk attached to the instance.
2. Say that snapshots are billable and give the billing and snapshot
   management pages listed in [help-docs.md](login-credential-repair__help-docs.md). Customers ask how
   much, how long, and what happens if they skip it; answer all three at the
   same time rather than one per round trip, and note the snapshot can be
   deleted by a human once the incident is closed.
3. Tell-and-confirm for the step itself: what runs, blast radius, reversibility,
   cost - one explicit yes per step, never a carried-over one.

Pure inspection and reading the console needs no snapshot.

## 5. Offline reset: the restart caveats to read out first

Offline reset works, and it is the reliable way to make a password take
effect. It also needs a restart, and customers repeatedly stall at exactly
this point while they ask their business owner. State the three cautions once,
up front, in this order:

1. The restart interrupts running workloads - schedule it in a low-traffic
   window and tell the business side first.
2. Data still in memory is lost: stop the applications that hold it (databases,
   caches) so buffers flush to disk before the restart.
3. Take the snapshot from section 4 first; the snapshot itself is billable.

If the customer will not accept a restart - for example because their own
backup tooling is unhealthy and they do not want to depend on a snapshot -
offer the no-restart alternative in section 6 below before pushing the offline
path.

## 6. The no-restart alternative, and the post-reset checklist

**No-restart alternative.** If the instance has a second enabled
administrator (Windows) or sudo-capable (Linux) account that the customer can
still use, changing the target account's password from inside the guest with
that account needs no restart and no console write. In this tier's evidence
this was the customer's own idea after three failed console routes; it should
be offered earlier, as a standard option, whenever a second working account
exists. Confirm the account exists with the customer-executed readings in
[guest-credential-checks.md](login-credential-repair__guest-credential-checks.md). The write itself is
the customer's action.

**Post-reset checklist.** Run all four; each one is a real case in the
evidence where "the reset did not work" was not a reset failure:

1. **Address.** Local RDP/SSH must target the public IP or an EIP. Dialing the
   private address produces a credentials-style failure, not a routing error.
   Workbench may legitimately use the private address; local clients may not.
2. **Port.** If the remote service was moved off 22 / 3389, the client must
   carry the port. Non-default ports in this tier's evidence included 9898.
   Nothing in this skill can read the configured remote port from the cloud
   API; it comes from the customer or an in-guest listening-socket reading.
3. **Stale client credentials.** A client or Workbench session that remembered
   the old password keeps failing with the same generic message after a
   successful reset. Close it and open a new connection, or switch instance;
   do not "try the password again" ten times and trip the lockout policy.
4. **Username pollution.** If the RDP username field arrived as
   `<local-computer-name>\administrator`, the client is authenticating against
   the laptop, not the server. Edit it to the bare account name and clear the
   remember-credentials option.

Then the tie-breaker: sign in through the console session manager with the same
credential. Success there proves the credential is good and the problem is the
client path; failure there proves the credential really did not change.

## 7. Key-pair interference (Linux)

- A bound key pair can go with key-only logon enforced in the guest, so the
  password is correct and still refused. Confirm the binding from instance
  facts; confirm the referenced key pair still exists in that region with the
  key-pair read, which turns "the key pair was removed" from a complaint into
  a checked fact either way.
- Console passwordless / Workbench routes rely on a temporary key-pair
  mechanism. When they report a removed key pair, stop chasing that route and
  use a console session or an explicit password logon.
- Operational note, low confidence and to verify in the current console:
  console key-pair binding is available for Linux images; a Windows customer
  asking to "log on with an SSH key instead" is asking for something the
  console does not offer, and self-installing an SSH server on Windows is
  outside this skill.

## 8. Sensitive handling, every time

- Never ask for, echo, store or transmit a password. The reset is performed by
  the customer in their own console session, and the new value goes from the
  console into their own password manager.
- If the customer has already pasted a plaintext password into the
  conversation, say **immediately** - not in the closing summary - that they
  must change that password as the first action once the instance is reachable
  again. This is the whole reason the skill refuses to accept one.
- The report masks secret-looking tokens in customer-supplied error text.

## 9. Where this stops

Anything requiring a restart, an in-guest edit, a disk expansion, a security
group change, or a snapshot rollback is guidance for a human. If the customer
wants the reset actually performed for them, that is an explicit grant decision
outside this skill's current authority; the answer is the console path plus the
risk statement, not a workaround.
