# Blackhole, scrubbing, blocks and unblocking: what each one actually is

Customer-facing symptom in every case: "my server is down, I think we are under
attack." This file is the reading order. Only the first question separates the
areas; the rest are consequences.

## 1. The four areas, and why mixing them wastes days

| Area | Who acts | Direction affected | Can Alibaba Cloud lift it? | Where it is proven |
|---|---|---|---|---|
| DDoS blackhole (and traffic scrubbing) | The platform's own DDoS protection, automatically, when volume passes a threshold | Inbound public traffic to that IP is dropped or diverted; while blackholed, inbound and outbound public paths are both unusable, so remote sign-in and console-based restart both fail | Lifts **automatically** when the attack stops. There is no supported early removal by an operator | DDoS protection console: asset list and event detail, including the per-IP thresholds |
| Platform penalty block (outbound cut, URL shielded) | Platform enforcement, because **this** instance was observed attacking others, or a URL served from it broke the rules | Outbound to the reported port, or the reported URL only | Only after the customer remediates and an approval flow releases the penalty | The notice itself (SMS or internal message), plus the penalty list and its release page |
| External-party block | Somebody else's defence: the peer site's security system, a messaging platform, a domain registrar, an anti-spam listing, a carrier, or a regulator | Whatever that third party controls; the instance keeps working | No, and no certificate of innocence can be manufactured for it | Their own notice to the customer; your side proves only "our platform raised nothing" |
| Not an attack at all | Resource exhaustion, a disk full of logs, an unpaid pay-by-traffic band, a panel or host firewall that blacklisted the customer's own office IP, a missing or overriding security-group rule, an application that never bound the port, a version incompatibility in the web server | Anything | Configuration or capacity work, on the customer's side | The read-only queries in this skill plus guest-side readings taken by the customer |

**Order of work.** Rule out the two areas you can prove cheaply before discussing
mitigation products: security-group rule effects and instance state are answered
by the read-only queries; the "not an attack" causes are answered by configuration
and capacity readings. Then, and only then, look at blackhole or penalty events
in the console.

## 2. Blackhole and scrubbing: what may and may not be said

* Mechanism: scrubbing diverts traffic to a cleaning layer while the volume is
  manageable; once the volume passes the asset's blackhole threshold, the
  platform drops the public traffic to that address entirely. This is protective,
  not punitive, and it is not "Alibaba Cloud blocking the customer".
* Thresholds are per asset and are shown in the console. Do **not** quote a
  numeric threshold, a Gbps figure or a bandwidth floor from memory or from
  another customer's case; the customer's own asset page is the only source.
* Release window: not a fixed number. Across observed cases it ranges from tens
  of minutes to roughly a day, **and repeated attacks during the event extend it
  further**, in one documented case well beyond the usual window and still not
  restored days later. Say "the event detail in the DDoS console is the only
  authoritative timing" and quote no minutes.
* No operator can remove a blackhole early. If a customer insists it happened
  before, that is a claim to route to a human specialist, not a promise to make.
* Stopping or rebooting the instance does not stop an inbound flood and does not
  shorten the event; it only takes the service down further.
* Whether the flood targeted the IP or a domain name cannot be distinguished by
  the platform, so do not attempt to answer it.
* While blackholed, remote sign-in, reboot and any in-guest operation are all
  unavailable because the public path itself is dropped. Anything requiring guest
  access must be deferred, and the report must say so instead of pretending to
  have checked.

## 3. Recovery paths, each with its real precondition

1. **Wait it out.** Default and usually correct. Pair it with path 2 so visitors
   are not converging on the dead address.
2. **Pause DNS for the affected name.** In the DNS/console for the domain,
   suspend or re-point the record so traffic stops arriving at the blackholed
   address. Restoring it after release is the customer's step.
3. **Change the public address.** A fixed public IP cannot simply be swapped. The
   documented order is: change fixed-bandwidth billing to pay-by-traffic, then
   convert the VPC fixed public IP into an EIP, then unbind that EIP, then buy
   and bind a new one. Warn that changing bandwidth billing and buying an EIP
   can add cost, and that a fresh address can be flooded again - this is a
   mitigation of symptoms, not protection.
4. **Move in front of the traffic.** Anti-DDoS (native protection, or the
   proxied high-defence edition), CDN, or WAF with the origin hidden. Route the
   three tiers separately and never merge them into "you need a specialist":
   buying the product, activating it, onboarding the domain onto it and turning
   on the basic protection settings are **self-service** on the corresponding
   product page in the console - that is all that is needed before protection
   exists, so it must never be presented as work the customer cannot do; an
   **Enterprise-edition quote or a solution design** is a pre-sales
   conversation; **tuning complex custom rules** (rate-limit thresholds, bot
   policies, precise protection policies) is what a ticket or the product
   support team is for. If a WAF or CDN is already purchased,
   first verify it is actually in the path: an EIP that points straight at the
   instance while the defence product still references the old public address
   means **no traffic goes through the defence at all**, which is a common and
   invisible "the paid product did nothing" case.
5. **Restore an application-level cause** (web server version, panel setting,
   host firewall) only after path 1-4 are ruled out - and note the several
   documented cases where the customer "thought it was a blackhole" and the real
   fix was the web server, a full log volume, or an unpaid bandwidth bill.

Before any reboot, any engineer signing in, or any rollback: snapshot every disk
first, and say plainly that snapshots bill by capacity and that deleting them
afterwards is a separate manual step. Rollback is irreversible for the current
disk content, so snapshot the live disk before rolling back.

## 4. The notice text decides the branch

Ask the customer to paste the **verbatim** SMS or internal message. It usually
contains the port, the direction, and an expiry:

* "detected outbound attack, access to other servers' port TCP:xxxx has been
  blocked, expected to end before <time>" - this is a **penalty for this
  instance attacking others**, not a DDoS blackhole. The cause is inside the
  guest (an abused service, a weak-password database, a planted program). The
  cut lifts on its own at the announced time; the underlying abuse will not.
* "URL shielded due to illegal content" - a **content penalty**. Fixing the
  reported file, deleting the reported URL, and verifying it returns 404 is
  prerequisite; then apply on the penalty release page. Paying for a security
  product or clicking "fix" on a vulnerability does **not** lift a content
  penalty: those are unrelated mechanisms, and customers routinely conflate
  them. If the reported file no longer exists, there is nothing left to release,
  which is why a listed record can disappear on its own.
* "blocked by the carrier / regulator / peer platform / messaging platform" -
  external. Provide the appeal evidence list instead of an internal ticket.

## 5. Port 25 and SMTP

Outbound 25 is **closed by default** on newly purchased instances as an
anti-spam policy; it is not a fault and not an attack. Applying for unblocking
needs an ICP-filed mail domain and the requested attachments; the "associated
domain" field is mandatory and is the usual sticking point. Only **IPv4**
outbound 25 can be released - IPv6 to port 25 is not supported at all, so a
target that only listens on IPv6:25 cannot be fixed by unblocking. The practical
answer is port 465 or another submission port.
A duplicate application can come back with a misleading "not your asset" style
reply; check whether the earlier request already took effect before re-applying.

## 6. Account freeze and cost side effects

A security-related account freeze lifts on its announced date and cannot be
accelerated. Pay-as-you-go instances keep billing while frozen; stopping them by
hand reduces part of the charge but compute, memory and disk billing continue.
Attack traffic and abuse-driven egress show up as **outbound traffic cost**, and
pay-as-you-go security products (for example an hourly Security Center base
fee) add their own line; billing is issued T+1, so a switch turned off today
still appears in tomorrow's bill. Direct the customer to per-instance billing
detail, and route any reduction, refund or compensation claim to a human: this
skill never quotes, promises or negotiates money.

## 7. Application-layer floods (CC)

Do not certify "this is a CC attack". What can be done is quantitative: count
the top source addresses and request paths in the access log for the incident
hour, compare against a normal hour, and note the pattern (single UA, one URL,
many sources behind one netblock). Then point at WAF rate limiting and bot
management as directions the customer configures in the WAF console - the basic
rate-limit and bot rules are self-service, and only complex custom policy tuning
is raised as a ticket. There is no malicious-IP reputation
database exposed here, so any "block these N IPs" shortlist must carry an
explicit warning that a wrong block also shuts out legitimate crawlers and real
customers - and the shortlist is a suggestion, never an applied change.

## 8. Service boundaries to state once, clearly

No filing a police report on the customer's behalf (they call their local
authorities); no decrypting ransomware data (paid third-party recovery exists,
with no guarantee); no modifying application source code; no guarantee that a
third party will accept an appeal; no promise of compensation or fee waiver; no
promising that a clean-up will remove every trace once a site has been planted
with content. Evidence that the platform can provide is the **traffic evidence
package** downloadable from the DDoS console event detail.
