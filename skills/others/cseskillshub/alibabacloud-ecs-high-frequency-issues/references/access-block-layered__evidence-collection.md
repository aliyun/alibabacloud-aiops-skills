# Evidence Collection — what to ask for, from whom, in what format

Most unresolved interception tickets do not fail because the layers were
misunderstood; they fail because a needed reading never arrived. The recurring
shape in real dialogs: the customer is asked to run three commands and send
screenshots, sends none (or only a partial one), the session times out, and the
case closes inconclusive. So evidence is requested **one item at a time, with
the exact command or page, and with the reason stated**.

## Ask once, ask completely

Before requesting anything, state which layer the item decides. A request that
cannot change a verdict should not be sent.

| Evidence item | Who produces it | Exact form to ask for | Decides |
|---|---|---|---|
| Literal error text | customer | the message as shown, or a screenshot of the whole window; never a paraphrase | which layer family to walk first (see [symptom-error-strings.md](access-block-layered__symptom-error-strings.md)) |
| Flow coordinates | customer | direction (inbound, outbound, instance-to-instance), protocol, port, and the peer address | every layer; a wrong direction invalidates the whole walk |
| Client public egress IP | customer, on the client machine | the reading from one public lookup page (see below), plus the same reading from each failing colleague's machine | L0 and the L4 authorization-object match |
| Second-network comparison | customer | one test from a phone hotspot or another network, same command, same port | splits platform layers from client and path responsibility |
| Server-side arrival proof | customer, or a gated non-mutating check here | the listener reading and the recent-source-IP reading, pasted as text | whether traffic reached the guest at all |
| Request identifier from a block page | customer | the request ID shown on the interception page | whether a WAF or managed rule matched |
| Time window | customer | first failure time, and whether it is continuous or intermittent | correlation with policy changes and monitoring |
| Domain facts | customer | the resolved address of the domain and whether direct-IP access behaves differently | L1 compliance branch |
| Both-sides capture | customer, manually, on each side | a saved capture file per side, not pasted packet text, plus a reverse traceroute with packet test | L7 only, and only after L0-L6 are excluded |

## Egress IP: the most common trap

The IP the customer believes they use is frequently not the one that reaches
the instance. Ask for a live lookup page on the client machine
(`https://www.ip138.com/` or `https://cip.cc`) and treat these as the known
failure shapes:

* a modem or office NAT **LAN** address was typed into the authorization field;
* a dynamic home broadband IP changed since the rule was written;
* a VPN or corporate proxy replaces the source silently, so each colleague has
  a different egress IP;
* the customer cannot reach the lookup page either - then the server-side
  source-IP reading is the fallback truth.

Compare the collected IP against the bound groups' ingress rules with
`--source-ip`; do not eyeball it.

## Where the readings come from

1. **Cloud reads** (automatic): instance facts, bound groups, rule five-tuples,
   Cloud Firewall policy, WAF presence. Run these first - they need nothing
   from the customer and they narrow what to ask for.
2. **Gated guest reads** (confirmation required): firewall state and rules,
   listeners, kernel parameters, the source IP that actually reached the
   machine. One whitelisted command per confirmation, as defined in
   [guest-inspection-commands.md](access-block-layered__guest-inspection-commands.md).
3. **Customer-side reads** (always manual): egress IP lookup, second-network
   test, browser or client variations, captures.

## Format rules that prevent a stall

* One command per request, output pasted as text. Asking for "screenshots of
  the firewall settings" invites partial answers.
* Capture work is a saved file, produced by the customer, never by this skill;
  pasted packet lines are not analyzable and the capture itself is a
  mutating-on-disk, class-D activity that stays manual.
* Say what the reading will decide, so a refusing customer can opt out
  knowingly. If access is declined, record the layer as UNKNOWN and continue:
  a blocked layer is never reported as excluded.
* If the client channel to the instance is itself broken (remote port is the
  thing that fails), give the out-of-band console logon path before asking for
  any in-guest reading.

## Credential safety while collecting evidence

Never ask the customer to paste instance accounts or passwords into the
conversation, and never accept them if offered - point to the console
authorization flow instead, and recommend rotating any credential that was
already shared in the thread. Evidence requests carry no credentials: an
instance identifier, a region, an IP, a port, and a message.

## Closing an inconclusive case honestly

When the decisive reading cannot be obtained, the output is
`STATUS: DEGRADED` with: the layers excluded, the layers left UNKNOWN, the
single most likely remaining hypothesis with its confidence stated, and the
exact next human action (which console page, which command, which escalation).
Never convert a missing reading into a conclusion.
