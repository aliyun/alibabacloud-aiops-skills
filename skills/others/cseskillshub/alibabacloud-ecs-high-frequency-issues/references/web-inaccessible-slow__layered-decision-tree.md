# Layered decision tree, L0 to L8

The tree is keyed by **layer** plus the **customer-visible error string**. Symptom labels in
tickets overlap constantly, so labels are used for recall only; they never decide the next step.

Execution order is fixed: L0 gates, then L1 to L8 in order, and each layer terminates in one of
three verdicts - `CONFIRMED` (this layer fails, here is the reading), `EXCLUDED` (this layer is
proved good, here is the reading), or `INCONCLUSIVE` (what is missing and how to get it). A list
of causes for the customer to try at random is never an acceptable output.

```
L0  evidence gate
 |
L1  asset and account ownership ---- not a live ECS instance of this account --> stop, hand off
 |
L2  DNS ----------------------------- zone answer differs from the real address --> fix guidance, retest
 |
L3  public path and carriers --------- asymmetric by network / city / device --> L3, else continue
 |
L4  cloud access control ------------- no matching Accept, or a Drop that wins --> add rule (level C)
 |
L5  in-guest listeners and firewall -- no listener, or loopback bind, or host drop --> level B then L6
 |
L6  application and content ---------- status code attributed to origin --> app owner; to edge --> product owner
 |
L7  TLS and filing ------------------- handshake or certificate failure, or reset while IP works --> L7
 |
L8  capacity and attack ------------- saturated metrics or abnormal sources --> L8
```

## L0 - evidence gate

Collect, in one round trip if anything is missing:

- target (domain / full URL / public IP), port, protocol;
- **the error string the customer actually sees**, or the HTTP status;
- **the most recent change**: when, what, by whom, revertible or not. Engineers opened the
  locating question this way in 8 of the reviewed tickets, always immediately after the error
  string. A change that coincides with the onset outranks any statistical prior;
- impact breadth: all users, some users, some regions, some resources, some ports;
- client location, ISP, and whether the client network was switched (home, enterprise, campus,
  VDI, mobile data);
- instance id and region; incident time window.

## L1 - asset and account ownership

| Check | Root causes found here |
| --- | --- |
| Does the instance exist in this account and region? | Wrong account, wrong region, released instance, resource in another member account |
| Is it running? | Stopped, starting, expired and about to be released, locked for arrears (indirect signal only) |
| Which public address does it really have? | Fixed public IP versus EIP versus none; NAT gateway; the address the customer quotes is stale |
| Which security groups is it in? | Several groups merged; the customer edited only one |
| Is this asset even ECS? | Simple Application Server, JuShiTa/open-platform hosting, a domain parked elsewhere, an origin on another provider |

Arrears and expiry have no verified describe call here. Instance state is an indirect signal;
the billing centre is authoritative, and the report says so.

## L2 - DNS

`alidns:DescribeDomainRecords` is used for its list semantics on the customer's own zone, then the
`alidns:DescribeDomainNs` is read next, because a record set only matters if the service holding it
is authoritative for the domain. The answer is compared three ways: **published records <-> the
instance's real public address <-> the EIP binding state**. Six shapes are reported as faults:

1. missing `@` or missing `www` - one host name works, the other does not;
2. a private address (`10.`, `172.16-31.`, `192.168.`, `127.`, `169.254.`) published as a public
   record - works inside the LAN, fails for everybody else;
3. a stale record pointing at a released or reassigned address - common after an instance was
   rebuilt or the IP changed;
4. a CNAME into an edge product (CDN, DCDN, WAF, GA, or a third party such as Cloudflare) - the
   origin address is hidden **by design**, so every later layer must be tested against the
   origin, not against the published name;
5. the record and the EIP state disagree - the zone is right, the binding is not, or the reverse.
6. the delegation does not include this DNS service (`IncludeAliDns` false) while records exist
   here - the published answers are never served, so the record set proves nothing; the fix is a
   registrar-side NS change plus propagation, not a record edit. A partly-foreign NS set
   (`IncludeAliDns` true, `AllAliDns` false) is reported as evidence and a comparison instruction
   only: dual-provider DNS is a legitimate design and is never called a fault on its own.

Client-side effects stay invisible from the cloud: a local hosts override or a cached LocalDNS
answer makes a correct zone look broken. That is why the retest instruction is always "flush or
wait out the cache, then retest and report the new error string".

## L3 - public path and carriers

Not observable programmatically from inside the cloud, so it is closed out by comparison:

- domain versus direct IP; another network (mobile data) versus the current one; another city;
  another device;
- enterprise, campus and VDI egress - the customer's own outbound proxy or filter;
- interception and blocking by the carrier or by a compliance path, and blackhole state. Neither
  has a verified describe call; point to the Anti-DDoS console and ask for a public multi-region
  probe page to be run and pasted back, which is what engineers already do in tickets.

Verdict at L3 is usually `INCONCLUSIVE` with a concrete request. Saying so is correct; guessing
"isp problem" without the comparison evidence is not.

## L4 - cloud access control

Rules are read from `ecs:DescribeSecurityGroupAttribute` for **both** directions, and merged
across all groups the instance belongs to. The merge rule matters more than any single rule:

- a `Drop` at a better (lower) priority wins over an `Accept` at a worse priority, so an
  apparently correct rule can be shadowed by another group;
- the **authorisation object** must be checked, not just the port: a rule allowing a group id, a
  prefix list or a narrow CIDR does not serve an internet client;
- all groups on the instance are overlaid; the customer's mental model of "my security group" is
  often one group out of three;
- outbound rules are read too, because a restrictive egress policy breaks panels, licence servers
  and update mirrors from inside;
- full-open (`0.0.0.0/0` or `::/0`) rules on administration ports (`22`, `3389`, `1433`, `3306`,
  `6379`, `9200`, `27017`) are reported as a separate exposure finding, even when they are not
  the cause of this incident;
- the cloud firewall, if the account uses one, sits in front of the group and is not visible
  through these actions - say so when L4 looks clean but the traffic is still dropped.

Fix at L4 is a **level C** action: snapshot first when the change touches the guest, disclose the
exact rule text, its blast radius and how to revert, get agreement, and let the customer apply it
in the console (the skill never writes security group rules).

## L5 - in-guest listeners and host firewall

Nothing on the cloud side exposes what listens inside the guest. That is the whole reason level B
exists. The checks and their approval state are in `guest-read-checks.md`. Four distinct failures
are separated:

- no process listens on the tested port (service stopped, crashed, or never configured);
- it listens, but only on `127.0.0.1`/`::1`, so the public address is refused - the most common
  shape after a configuration rewrite or a panel change;
- it listens correctly and the host firewall drops (iptables/nftables/firewalld rules, a fail2ban
  chain, or a panel hardening module);
- routing or bridging swallows the packet - a Docker bridge subnet that overlaps the customer's
  network, an extra route, a `hosts.deny` entry, or a `hosts` file override.

Panel hardening modules are named as suspects inside L5 only; the panel page itself is another
scenario.

### Reading the reading

Collecting output is not a verdict. Whatever the source - a confirmed Cloud Assistant dispatch or
output the customer pasted back through `--guest-output` / `--guest-output-file` - the same
interpreter reads it and the layer is decided on what the text proves:

| Reading | Verdict |
| --- | --- |
| web service or IIS application pool shown stopped/failed | `CONFIRMED` - service not running |
| no socket on the tested port while other sockets are listed | `CONFIRMED` - nothing listening |
| the port bound to `127.0.0.1`/`::1` only | `CONFIRMED` - loopback-only bind |
| an `INPUT ... --dport <port> -j DROP/REJECT` rule, or a firewalld zone that admits neither the port nor `http`/`https` | `CONFIRMED` - guest packet filter |
| the port listening on a routable address and no block for it | `EXCLUDED` - next suspect is the application or the path outside the instance |
| no recognisable listener, service or filter line | `INCONCLUSIVE` - ask for the full output, never guess |

The paste-back channel dispatches nothing and widens no permission: it is the documented degraded
mode made executable. Once a reading is held, the answer stops asking for it again.

## L6 - application and content

An HTTP status code proves the path reached an application layer, so it is not evidence that the
cloud side is fine. Before anything else, **attribute the code to origin or edge** with the
comparison in `../SKILL.md` ("Proving whether an edge layer is involved"). Then:

| Code | Typical origin-side cause |
| --- | --- |
| 404 | Entry file or route missing, wrong document root, rewrite rules lost |
| 405 | Method policy at an edge or security layer |
| 500 | Application fault; read the error log tail |
| 502 | Reverse proxy cannot reach its backend: backend down, wrong port or socket, php-fpm not listening |
| 504 | Backend too slow: long query, slow upstream, timeout chain misordered |
| 521 | Edge could not reach the origin at all |
| blank page | Fatal application error, tamper-protection module, injected or truncated code |

Disk full and inode exhaustion appear here as a side observation and are then handed to the disk
capacity scenario; this skill does not take over cleanup.

## L7 - TLS and filing

- Certificate: validity window, chain completeness, hostname mismatch, expired or not yet valid
  (`err_cert_date_invalid`), wrong certificate on a multi-site host.
- TLS handshake: protocol version and cipher suite rejected by a modern browser, SNI missing,
  origin expecting a client certificate.
- **Filing (ICP / access filing):** on mainland regions, a domain without a valid filing can be
  reset rather than refused, which looks like `err_connection_reset` while a direct IP test
  behaves differently. There is **no verified describe call** for filing state. The skill may
  therefore only infer it - "the domain is reset while direct IP works and the origin passes its
  own loopback test" - and must label the sentence as an inference, then point to the filing
  console. Filing application and changes are handed off.

## L8 - capacity and attack

Three separate lines, each with its own verdict:

1. **capacity** - CPU, bandwidth, connection count. The monitoring read is implemented, but no
   namespace or metric name was verified for this tier, so the operator supplies them together
   with a saturation threshold; without a threshold the layer reports `INCONCLUSIVE` rather than
   guessing.
2. **application time** - which request segment is slow, static versus dynamic, one file type
   versus one directory.
3. **link quality** - retested from another network and another region.

Attack shows up here as a connection and source-range anomaly (a small number of source
addresses, or an unusual concentration) plus saturated bandwidth. Mitigation itself is out of
scope. Disk I/O as a root cause of slowness was **not** evidenced in this ticket batch, so there
is no branch for it, and the report says explicitly that it was not tested.

## Error string to first layer

| Customer-visible string | Family | Layer order |
| --- | --- | --- |
| `err_connection_timed_out`, `timed out`, spinning forever | DROP | L4 -> L5 -> L3 -> L8 |
| `Connection refused` | RST | L5 -> L7 -> L4 |
| `err_connection_reset`, `reset by peer` | RST | L5 -> L7 -> L4 |
| `err_connection_closed` | handshake | L7 -> L6 |
| `err_cert_date_invalid`, certificate warnings | certificate | L7 |
| `404`, `405`, `500`, `502`, `504`, `521`, blank page | application | L6 (after origin/edge attribution) |
| slow, takes several seconds, intermittently slow | performance | L8 + L6 + L3 in parallel |

The families are not interchangeable:

- **DROP = silence.** Something discards the packet: a security group rule, a host firewall, a
  cloud firewall, blackhole or carrier interception.
- **RST = an answer came back.** The packet arrived. The path is largely proved good, so search
  down-stack, not up.
- A reply to ping says nothing about TCP 80/443. ICMP passing while the web port times out is the
  single most common misunderstanding in this scenario.

## State transitions between layers

After any change, ask the customer to retest and report the **new** error string. The change of
the string is itself the evidence:

| Before | After | Meaning |
| --- | --- | --- |
| `err_connection_timed_out` | `Connection refused` | L4 is passed; the fault moved to L5. This is progress, not a new bug |
| `Connection refused` | a status code | L5 is passed; the listener answers. Work is now L6 |
| domain fails | direct IP fails identically | Not DNS; L2 is excluded for this symptom |
| domain fails | direct IP works | L2, L7 (filing) or an edge product; not the listener |
| all clients fail | only one network fails | L3 or the customer LAN; not the instance |

## Differential tests, each one halves the search

domain versus direct IP - port 80 versus 443 - `127.0.0.1` versus intranet IP versus public IP -
static page versus dynamic page - one file type versus one directory - another network, another
city, another device - this cloud versus the customer's own machine - before versus after the
reported change.
