# Cross-border and overseas link quality: decision tree and wording

Companion to `SKILL.md`. Everything below is the reasoning the entry script automates
and the wording an operator sends. It is written for one symptom area: access quality
between Chinese mainland networks and overseas (or China Hong Kong) endpoints.

## 1. Facts this tier relies on

- A mainland user reaching an overseas or China Hong Kong instance is not a direct
  hop. The traffic traverses international egress points and carrier routing nodes
  whose congestion, packet loss, and per-port behaviour are outside both the customer's
  server configuration and Alibaba Cloud's control.
- The reverse holds as well: an overseas instance pushing data into mainland China
  rides the same non-direct path in the other direction.
- Instance-side settings cannot raise or lower that path's quality, and there is no
  per-instance "acceleration" switch to look for.
- Two instances in the same region can behave completely differently, because each
  public address is announced over different carrier paths and the return route differs.
  Different latency between two same-region addresses is an expected observation, not a
  configuration difference.
- Changing the public address does not change the path. A fault that reproduces on a
  new address is evidence *against* an address-side cause, not evidence for one.
- Carrier-side segments can also block or throttle a specific address for policy
  reasons. That is decided by the carrier of the affected clients, and only that carrier
  can confirm and lift it.
- Outbound access from a mainland instance to an overseas endpoint is additionally a
  regulated direction. It cannot simply be opened on request; the legitimate routes are
  an overseas instance near the target or an accelerated path product.
- Recovery time for carrier congestion cannot be forecast by anyone on the platform
  side. Saying so is part of the answer, not a failure of the answer.
- A meaningful share of "cross-border" reports turn out not to be cross-border at all.
  Ruling that out first is the highest-value step in this tier.

## 2. Direction first, always

Inbound and outbound look similar in a complaint and have opposite fixes.
Set `--direction` before anything else:

| Direction | Question answered | Typical shape |
|---|---|---|
| `inbound` | can users reach my server | mainland users cannot reach an overseas instance |
| `outbound` | can my server reach something else | a mainland instance cannot complete a TLS call to an overseas API; an overseas instance is slow uploading into mainland China |

Record the error text verbatim when it exists. Strings that belong to this tier
include `err_timed_out`, `Operation timed out`, `i/o timeout`, a handshake that closes
early, and a stated packet-loss percentage. They describe where the wait ended, not
why; never let them substitute for the geography and direction inputs.

Anchor the causal chain to the FIRST question (MANDATORY): a first question about an
overseas API timing out from a mainland instance (for example a Let's Encrypt ACME
call) is the regulated outbound direction above, and that cross-border chain leads
the verdict. Secondary context - an IP change, a website symptom, bandwidth worries -
never replaces it as the primary root cause; a fault that reproduces on a new address
is evidence against an address-side cause (section 1), so the IP-change story is ruled
out by the customer's own observation, not promoted to the root cause.

## 3. Decision tree

### D1 Ownership and geography
`ecs:DescribeInstances` (+ `vpc:DescribeEipAddresses` when an EIP is involved).

- Not found for this account and region -> cross-account wording, stop. This skill can
  only read what the querying account owns.
- Region known -> classify the instance side: mainland, overseas, or China Hong Kong
  (overseas for the purpose of the border test).
- Region not supplied -> stop with `STATUS: DEGRADED`. The region is never guessed.
- Instance state is not running -> stop and hand off to the instance-state tier; a
  stopped machine explains the connection failure without any path hypothesis.

### D2 Rule-outs, in one pass
Collect these together rather than one round at a time:

1. instance status and health check reading;
2. EIP status, provisioned bandwidth, and metering mode;
3. attached security group ids (the report lists ids; a human confirms the tested port
   in the console, because rule bodies are not read here);
4. guest-side self-checks run **by the customer**, listed in section 6;
5. whether an address change already reproduces the fault;
6. whether the same service is fine for users located near the instance.

If the customer has already proven that the request arrives and the response is
generated but never received, do not ask for security-group or service checks again.
That request has been answered already, and repeating it is the fastest way to lose
the conversation. Go to D4 escalation.

### D3 Probe evidence
- Multi-node dial test, mainland nodes **and** overseas nodes, same address, same port.
  Mainland failing while overseas succeeds is the congestion signature.
- Bidirectional raw MTR: client to server, and server to the client's carrier network.
  Raw screenshots or plain text only. A rewritten or AI-summarised report is not
  accepted by reviewers and must not be produced here.
- Bandwidth metering over the fault window, read by the customer in the console,
  compared against the provisioned limit. Pinned at the limit is a local capacity
  ceiling, which is a different tier.
- A ping-only test is not sufficient: the guest may ignore ICMP, which proves nothing
  about TCP reachability. Pair it with the per-port TCP test.

### D4 Attribution
The branch table in section 4 is the whole mapping. Two branches compete for the same
symptom and must be separated carefully:

- **congestion** - loss and timeouts vary with time, carrier, and city; the server side
  is clean; nearby users are unaffected; an address change does not help.
- **platform egress or return-path fault** - the request demonstrably arrives, the
  response demonstrably leaves the instance, and something in between drops it; several
  TCP ports time out together; the trace stops at a visible hop and the destination
  never appears; the fault is stable and reproducible rather than intermittent.

The second one does not belong to this tier's wording. It needs a human reviewer with
visibility of egress, address mapping, and announcement state, so it becomes an
escalation pack instead of an explanation.

### D5 Output
Verdict with direction, evidence with the source of each item, open items, options
matched to where the users are, the no-guarantee statement, and the re-test recipe.
Never promote a degraded result into a confident one.

## 4. Branch table

| Branch | Signature | What the report says | Options | What must not be said |
|---|---|---|---|---|
| cross-border congestion | mainland nodes fail, overseas nodes succeed, server side clean, nearby users fine | path crosses international egress and carrier routing; congestion and per-port loss are expected there; nothing is broken on the instance | move by user base, evaluate an accelerated path, stage transfers near the receiver | a recovery time; a promise that it will clear on its own |
| platform egress or return-path fault | response sent but not received; multiple TCP ports time out; trace dies at a visible hop; reproduces after an address change | the loss sits between the instance and the client's network and needs a reviewer with egress and mapping visibility | escalation pack, raw output attached, agreed test window | "please check your security group again" |
| carrier policy or local block | only certain cities or carriers affected, others clean | something on the carrier side of the affected clients treats this address specially | carrier report with address, cities, and timestamps; parallel escalation | a claim that the block is or is not in place before the carrier confirms |
| regulatory boundary | mainland instance reaching an overseas endpoint | this direction is regulated as well as congested, and is not something a support ticket can open | overseas endpoint near the target, or an accelerated path | implying a policy exception can be requested through this channel |
| local bandwidth ceiling | metering pinned at the provisioned limit | throughput is capped locally, the path is not the limiter | capacity decision by the customer; hand to the bandwidth tier | attributing it to cross-border loss |
| not cross-border | both endpoints on the same side | the border hypothesis is retired; work the layer where the symptom shows | handoff to the matching tier | continuing to probe a path that is not involved |
| cross-account | resource absent from the querying account | only resources of this account can be read here | the owning account opens the request | speculating about another account's configuration |
| other tier | filing, panel sign-in, transfer tool, disk or IO, SSH credentials, attack and blackhole, private-network egress, third-party reputation, a platform policy restriction, or a request to make a change rather than to diagnose | this is not a link-quality problem; handoff sentence | handoff target from the map | stretching the cross-border story to fit |
| insufficient | geography or probe data missing | no attribution is offered | the open-item list with the recipe for each item | a probable-sounding guess |

## 5. Attribution wording library

Use these as written; they exist because free-form phrasing of the same facts drifts
into promises.

**Congestion.** "Access between mainland China and your instance's region is not a
direct link. It crosses international egress points and carrier routing nodes, and
those segments can be congested, lose packets, or fail on individual ports while the
server itself stays healthy. Your instance configuration has no effect on this path."

**Why an address change does not help.** "The path and the carrier routing stay the
same when the address changes, so a new public address does not resolve this class of
issue. If the fault reproduced on a new address, that observation rules the address out."

**Why two same-region instances differ.** "There is no acceleration setting involved.
Each public address is announced over different carrier paths, so the return route -
and with it the latency and loss - differs between two machines in one region."

**Recovery time.** "This sits on public carrier networks. It is not controlled from the
platform side, and no recovery time can be estimated."

**Responsibility boundary.** "We can show you the measurement: mainland nodes fail on
this port while overseas nodes succeed, and the server-side checks are clean. That
combination locates the loss on the cross-border segment rather than on your instance."

**Third-party reputation.** "Nothing on the cloud side explains this result. The
judgement comes from the other platform's own risk model, so the review has to happen
there."

**Regulated direction.** "Outbound access from a mainland instance to an overseas
endpoint is a regulated direction, and it cannot be opened on request through a support
channel. The workable routes are an endpoint near the target, or an accelerated path
service."

## 6. Customer-side evidence collection, with nature labels

Every suggested command carries three labels in the report: what it touches, whether
the change it makes is reversible, and who runs it. This skill runs none of them.

| Item | Command or action | Nature | Who |
|---|---|---|---|
| client location and last hop | `tracert` (Windows) / `traceroute` (macOS, Linux) | read-only | customer |
| per-port reachability | `telnet <address> <port>`, `curl -v --max-time 15 http://<address>:<port>/` | read-only | customer |
| ICMP ignored by the guest? | `cat /proc/sys/net/ipv4/icmp_echo_ignore_all` | read-only, inside the guest | customer, or engineer after authorisation |
| temporarily accept ICMP for a cleaner test | `sysctl -w net.ipv4.icmp_echo_ignore_all=0` | **writing inside the guest, reversible, does not survive a reboot; the customer decides** | customer only |
| guest firewall state | `iptables -S`, `firewall-cmd --list-all` | read-only | customer, or engineer after authorisation |
| listening service | `ss -lntp` | read-only | customer, or engineer after authorisation |
| MTR from the server side | see the MTR guide in section 9 | read-only | customer, or engineer after authorisation |
| bandwidth over the fault window | console monitoring curves; pausing a competing workload is a separate customer decision | read-only console review; stopping a workload changes service behaviour | customer |
| engineer inspection of the machine | a human takes a system-disk snapshot first (billed separately) and removes it after the inspection | mutating and billable, performed by a human, never by this skill | customer decision plus human engineer |

## 7. MTR reading method

- Both directions are required. One-sided output answers only one question.
- A hop showing loss is not automatically the fault. Intermediate routers commonly
  rate-limit ICMP. Treat hop loss as informative only where it starts and then persists
  to the destination.
- The destination not appearing at all, while TCP tests to that address fail too, is a
  different and stronger observation than a lossy middle hop.
- Loss that appears only on one carrier in one city points at the carrier side, not at
  the instance.
- Include the raw output. Reviewers ask for screenshots precisely because a rewritten
  summary is not verifiable, and this skill must not produce the rewrite.

## 8. Escalation pack

Emitted automatically when the egress or return-path branch is hit, so a reviewer
receives one structured block instead of another round trip:

```
Resource / region / zone
Public address and its status and provisioned bandwidth
Instance status, attached security group ids
Symptom and direction, affected source, affected target
Verbatim error text, fault window
Reproduction facts, including whether an address change helped
Raw MTR both directions and dial-test links (attached, not summarised)
```

The pack stops short of an internal ticket submission: it produces the paste-ready
block. Confirm with the customer before repeating any self-check that is already
answered in it.

## 9. Permitted external links

These are the only links this tier may quote. They come from material already sent in
support conversations, so re-check that each one is live and applicable before quoting
it, and do not add a link that is not listed here.

| Purpose | Link |
|---|---|
| MTR usage guide | https://help.aliyun.com/zh/ecs/user-guide/use-mtr-tool-for-network-analysis |
| Public dial-test console | https://boce.aliyun.com/home |
| Accelerated path product scenarios | https://help.aliyun.com/zh/ga/product-overview/scenarios |
| Disk snapshot, human pre-check step | https://help.aliyun.com/document_detail/25455.html |
| Snapshot billing | https://help.aliyun.com/document_detail/56159.html |
| Snapshot removal after the inspection | https://help.aliyun.com/document_detail/128131.html |

Links that need a human to source them first, and are therefore **not** quoted to
customers by this skill: the premium carrier line for public addresses, the mainland
filing service-code lookup, and any trial-entry page. If one of these becomes necessary,
obtain a verified address first.

## 10. What stays manual

- The actual measurement: nothing in a read-only cloud API reports real loss or latency
  between two public endpoints. Every closed ticket in this tier was closed with a
  dial test or MTR, not with an API response.
- Guest readings: firewall state, service config, ICMP switch, live throughput tools.
- Carrier contact, and anything a carrier has to confirm or lift.
- Platform-side visibility into egress, address mapping, and announcement state, which
  is why that branch escalates rather than concludes.
- Any change at all: this tier diagnoses and explains. Migration, carrier reports,
  console reviews, and disk snapshot steps are human actions.
