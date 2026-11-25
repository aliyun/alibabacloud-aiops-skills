# Logon decision tree

Routing knowledge for one question: **why can this customer not log on, and what
evidence proves the answer.** Symptoms come from the customer, root causes come
from a query or a reading, never from a guess.

## Step 1 - intake before anything else

Four elements, collected first, because each one silently changes which branch is
correct:

| Element | Why it decides the route |
|---|---|
| Instance id **and** region | A region mismatch looks exactly like a deleted instance or a broken key |
| Operating system, Linux or Windows | The whole failure vocabulary differs: sshd and authorized_keys versus an account lockout and a session ceiling |
| Which logon path was attempted | Passwordless in the console, console with a chosen key, local ssh, Remote Desktop, VNC. Each has its own dependency chain |
| The exact error text, verbatim | Localised console wording, ssh client output and Windows error codes each map to a distinct fix. A paraphrase loses the branch |

Also worth asking, because each has burned a whole round trip: whether the image
was changed recently and where the new image came from, which user name was used,
whether a console restart followed a key pair binding, and whether VNC works.

## Step 2 - the standing evidence group

Run every query, record every failure, and let the report show what is missing.
The commands live in `../scripts/keypair_login_diagnosis.py`; the actions and
their purpose are in `ram-policies.md`.

| Order | Read | Decides |
|---|---|---|
| 1 | Caller identity | Right account? Cross-account and wrong-region lookups are a recurring false "credentials are broken" |
| 2 | Instance facts | Exists, `Running`, OS, image, bound groups, locks, expiry, key pair name if returned |
| 3 | Instance health and scheduled events | Platform-side event rather than a credential fault |
| 4 | Cloud Assistant status | Whether the passwordless channel and the online password reset can work at all |
| 5 | Execution history, output suppressed | Whether a remote command recently failed inside the guest, which is evidence for drift and reset-failure branches |

A state other than `Running`, or an operation lock, ends the credential
discussion until it is resolved: no logon path works then.

## Step 3 - route on the logon path

### Console passwordless logon fails

The mechanism first, because it reorders the whole diagnosis: passwordless logon
delivers a **temporary SSH key pair inside the guest through Cloud Assistant**. It
does not use the instance password and does not depend on `PermitRootLogin`, so:

* agent not reporting or heartbeat stale, the passwordless path is dead while
  every other path may be fine;
* an instance deliberately locked down against root logon can still be reachable
  this way, which is the fast route back in;
* a colleague who can and you who cannot, with the same instance and the same
  agent, is a RAM permission gap: the sub-account needs ECS view and manage plus
  Cloud Assistant permission;
* agent online yet logon refused, suspect a wedged guest or an sshd that refuses
  the temporary key. Ask whether other things are slow at the same time. Memory
  pressure, then swap, then disk IO saturation, then a stopped agent: the logon
  failure is the last visible symptom of the first cause, and belongs to the IO
  tier, not here;
* nothing else works, VNC is the fallback that needs neither key nor password.

### Local ssh with a key pair fails

Work outward-in, cheapest checks first:

1. The exact client output: `error-signatures.md` maps each wording to a fix side.
2. User name: `root`, `ecs-user`, or the stock image user. A wrong user name and a
   wrong key are indistinguishable from the outside.
3. The local key file: existence, path, permissions.
4. The binding and its effect condition: see the single operative wording in
   `keypair-and-credential-guidance.md`.
5. Reachability: port 22 tested by the customer from their own network, and their
   own egress. Console-side rule review is human work.
6. In-guest readings, only when the cloud side is clean: that is the "all green in
   the console, VNC works, every key path refused" prototype. Pubkey
   authentication, the authorized keys file path, the home and `.ssh` permission
   chain, a host firewall blocking 22 independently of the cloud rules, and
   server-side log lines. Then, and only then, a conclusion.

### Password does not work, or a reset does not take

* An online reset runs inside the guest through the agent and needs no restart. A
  failure at its "creating a key pair" step is an in-guest execution failure, not
  a password problem.
* An offline reset needs a console restart, so a snapshot comes first, and it does
  not depend on the agent.
* With a key pair bound, password logon can stay refused after a perfectly
  successful reset. Check the binding before concluding the reset failed.
* Still reachable by some other path, changing the password from inside the system
  is shorter and avoids the restart entirely.
* Console credential controls greyed out after an image swap points at the image
  origin, not at a platform fault. See the Others Linux note in
  `keypair-and-credential-guidance.md`.

### Remote Desktop, lockouts and multiple users

* A lockout after repeated failures is the operating system's own anti-brute-force
  policy, commonly triggered by internet traffic against 3389 while the customer,
  who logs on without typing a password, is the last person to suspect it.
* One successful VNC logon releases the lock; the console send-command path is the
  alternative. Both are human actions.
* Two concurrent sessions by default, and the same user name reconnects into one
  session rather than opening a second. More needs the session-host role plus
  client access licences, with a 120-day trial as the only vendor-supported route.
* Third-party activation scripts are out of scope; the licensed path is the answer
  and the conversation ends there. See `handoff-boundaries.md`.

### VNC fails too

VNC needs no key and no password. When it fails as well, stop treating this as a
credential case: it is a system-layer problem (guest wedged, boot stuck, base
files gone) and belongs to another tier. Snapshot first, then hand off.

## Step 4 - what the report must contain

Conclusions, and the evidence each one stands on. Say plainly which steps did not
return, and mark anything depending on them unproven. Name the single unanswered
question instead of working around it. Print console paths for human steps. Close
with the contract tail, and never state a number that did not come back from a
query.

| Tail | Meaning |
|---|---|
| `STATUS: OK` | Every evidence step returned and the branch conclusion is supported |
| `STATUS: DEGRADED` | A step did not return, or the deciding fact is missing, so the conclusion is partial |
| `STATUS: FAIL` | Nothing meaningful could be established: wrong account or region, an unusable credential chain, or no matching instance |
| `NEXT_ACTION:` | The one action that moves this case forward, and who performs it |
