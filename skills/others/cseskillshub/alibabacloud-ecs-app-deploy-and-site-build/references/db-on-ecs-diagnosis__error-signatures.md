# Error signatures and how each one is handled

Two classes of strings appear on this tier, and the difference matters:

* **Tier-quotable strings** - the two error strings confirmed for this tier:
  `timed out` and `Connection refused`. These may be quoted directly to the
  customer and appear in the skill description as triggers.
* **Ticket-sample strings** - literals observed verbatim in customer logs on
  the source tickets. They are input-matching patterns for the classifier, not
  tier error codes: the report cites them as "the error you pasted", never as
  an official code list.

## Tier-quotable strings

| String | What it actually means | First branch |
| --- | --- | --- |
| `Connection refused` | A host on the path answered and actively rejected: no listener on that port, the service is down, the port number differs from what the client dials, or the server's grant layer rejects the source | Listener and bind layer, then the grant layer; a refused connection is NOT a security-group drop |
| `timed out` | Packets died quietly: security-group or guest-firewall drop, wrong route, instance stopped, a filter suite in the middle, or a rule that has not propagated yet | Allow-list layer, then guest filters; ask whether any rule changed minutes ago before deeper digging |

## Ticket-sample strings (classifier inputs)

| Strings matched by the classifier (`ERROR_SIGNATURES` in `scripts/axes/db_on_ecs_diagnosis/_constants.py`; matching is case-insensitive) | Signature id | Layer it routes to | Meaning and disposition |
| --- | --- | --- | --- |
| `connection refused`, `refused by`, `WSAECONNREFUSED`, `10061` | `SIG_REFUSED` | listener/bind, then authentication and grant | Nothing accepts the socket on that port; walk the listener layer, then the grant layer |
| `timed out`, `timeout`, `10060`, `ETIMEDOUT`, `couldn't connect`, `connection attempt failed` | `SIG_TIMEOUT` | cloud allow-list, then guest packet filters | Silent drop; walk the allow-list and filter layers |
| `getaddrinfo`, `Temporary failure in name resolution`, `Name or service not known` | `SIG_NAME_RESOLUTION` | client and DNS | Client side, not an instance fault; check the host the client dials |
| `Communications link failure` | `SIG_LINK_FAILURE` | availability, then capacity | Driver-level link dropped mid-session: check timeouts, service restarts, capacity stalls |
| `SQLSTATE[HY000] [2002]` | `SIG_HY000_2002` | same split as refused versus timeout | PHP cannot open the socket or pipe; classify the tail of the pasted line |
| `nf_conntrack: table full`, `dropping packet` | `SIG_CONNTRACK_FULL` | guest kernel network stack | Connection-tracking overflow; the human check is the kernel ring buffer, tuning is a manual change |
| `No space left on device` | `SIG_NO_SPACE` | capacity triage (`df -h` then `df -i`) | Byte-full or inode-full; snapshot first, then hand the cleanup off to the capacity tier |
| `too many connections` | `SIG_TOO_MANY_CONN` | database configuration, customer side | Server connection limit reached - manual engine step |
| `Access denied for user` | `SIG_ACCESS_DENIED` | authentication and grant | Credentials or host grants rejected; the network path already worked |
| `Login failed for user`, `Cannot open database requested by the login` | `SIG_SQLSERVER_LOGIN` | authentication mode, then restore target | Mixed-mode authentication, account enabled state, or a wrong default/target database |
| `OS Error 1067`, `process terminated abortively` | `SIG_SERVICE_CRASH` | service availability, then capacity | Windows service crash loop; the engine error log path is in the message tail |
| `killed process`, `Out of memory`, `oom-killer` | `SIG_OOM` | resource chain (memory), then capacity | Memory starvation; manual memory reading plus the upgrade path (console, manual) |
| `Deadlock found`, `lock wait timeout` | `SIG_LOCK_PRESSURE` | database business layer | Business SQL, not infrastructure - hand off to DBA work |
| ransom-note wording (`your databases ... backed up`, `.onion`) | `SIG_RANSOM_NOTE` | security incident | Preserve the scene with a gated snapshot, never pay, recovery goes to a specialist |

The classifier behind `explain` and `diagnose` scans pasted or quoted error
text for every pattern above and lists each match with its meaning, its layer
and a confidence label. `SIG_LOCK_PRESSURE` and similar business-layer matches
produce a hand-off, not an infrastructure verdict.

## Web-page and tool wordings customers paste

Customers paste their application's own failure text, not raw socket errors:
a web page saying "database connection failed", a panel showing a red dot on
the MySQL entry, an app wizard's "unable to connect". Treat those as symptom
aliases for `timed out` / `Connection refused` classification: ask for the
underlying error (the raw driver text, `telnet <ip> <port>` result, or the
database error log), because the alias alone does not pick a branch.

## Verdicts with deliberately NO error string

Capacity pressure and ransomware patterns are recognised from command output
and file names, not from connection errors - a full disk can make every layer
above look healthy while the database cannot open its files. Do not force a
connection error where none exists; report the resource finding on its own
evidence.
